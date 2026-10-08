"""Services and state-machine transitions for vulnerability reports."""

import nh3
from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import log_audit_event
from apps.companies.models import MemberRole, OrganizationMember, OrganizationStatus
from apps.notifications.services import notify_user
from apps.programs.models import Program, ProgramScope, ProgramStatus, ProgramVisibility

from .models import (
    CommentVisibility,
    Report,
    ReportComment,
    ReportStatus,
    ReportStatusHistory,
)


def sanitize_markdown_text(raw_text: str) -> str:
    """Sanitize user markdown/text input using nh3 (Rust-backed Ammonia HTML sanitizer).

    Allows only safe formatting tags, stripping all script, iframe, object, SVG,
    event handlers, and unsafe URI schemes.
    """
    if not raw_text:
        return ""
    # Permitted tags for restricted markdown formatting
    allowed_tags = {
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
    }
    # Clean using nh3 with strict safe tag allowlist and no dangerous attributes/protocols
    cleaned = nh3.clean(
        raw_text,
        tags=allowed_tags,
        attributes={},
        url_schemes={"http", "https"},
    )
    return cleaned.strip()


def sanitize_plain_text(raw_text: str) -> str:
    """Strictly escape plain text fields (like titles) using nh3 text cleaning."""
    if not raw_text:
        return ""
    # Clean with empty tag set to strip all HTML tags entirely
    return nh3.clean(raw_text, tags=set(), attributes={}).strip()


def submit_report(
    program: Program,
    hunter_user,
    target_asset: ProgramScope,
    title: str,
    vulnerability_type: str,
    description: str,
    steps_to_reproduce: str,
    impact: str,
    severity: str,
    cvss_vector: str = "",
    cvss_score: float | None = None,
    request=None,
) -> Report:
    """Submit a vulnerability report to an active program."""
    if not hunter_user.is_hunter:
        raise PermissionDenied(
            "Only registered security researchers can submit reports."
        )

    # 1. Program must be ACTIVE
    if program.status != ProgramStatus.ACTIVE:
        raise ValidationError(
            {"program": ["Reports can only be submitted to active programs."]}
        )

    # 2. Organization must be VERIFIED
    if program.organization.status != OrganizationStatus.VERIFIED:
        raise ValidationError(
            {
                "program": [
                    "Cannot submit reports to an unverified or suspended organization."
                ]
            }
        )

    # 3. If program is private, hunter must hold an invitation
    if program.visibility == ProgramVisibility.PRIVATE:
        if not program.invites.filter(hunter=hunter_user).exists():
            raise PermissionDenied(
                "You do not have an active invitation to this private program."
            )

    # 4. Target asset must belong to this program and be marked IN_SCOPE
    if target_asset.program_id != program.id or not target_asset.in_scope:
        raise ValidationError(
            {
                "target_asset": [
                    "Target asset must be an in-scope asset defined for this program."
                ]
            }
        )

    # Sanitize user inputs
    clean_title = sanitize_plain_text(title)
    clean_desc = sanitize_markdown_text(description)
    clean_steps = sanitize_markdown_text(steps_to_reproduce)
    clean_impact = sanitize_markdown_text(impact)

    with transaction.atomic():
        report = Report.objects.create(
            program=program,
            hunter=hunter_user,
            target_asset=target_asset,
            title=clean_title,
            vulnerability_type=vulnerability_type,
            description=clean_desc,
            steps_to_reproduce=clean_steps,
            impact=clean_impact,
            severity=severity,
            cvss_vector=cvss_vector.strip(),
            cvss_score=cvss_score,
            status=ReportStatus.NEW,
        )

        ReportStatusHistory.objects.create(
            report=report,
            from_status=ReportStatus.NEW,
            to_status=ReportStatus.NEW,
            changed_by=hunter_user,
            reason="Report submitted by researcher",
        )

    log_audit_event(
        actor=hunter_user,
        action="report.submitted",
        target=report,
        metadata={"program_slug": program.slug, "severity": severity},
        request=request,
    )

    # Generic notification to company admins/triagers
    notify_user(
        recipient=program.organization,
        subject="New vulnerability report received",
        message="A new vulnerability report was submitted to your program on Cyber Eco.",
        link=f"/dashboard/company/reports/{report.id}",
    )

    return report


# State Machine Allowed Transitions
ALLOWED_TRANSITIONS = {
    ReportStatus.NEW: [ReportStatus.TRIAGED, ReportStatus.WITHDRAWN],
    ReportStatus.TRIAGED: [
        ReportStatus.NEEDS_INFO,
        ReportStatus.ACCEPTED,
        ReportStatus.DUPLICATE,
        ReportStatus.REJECTED,
        ReportStatus.INFORMATIVE,
        ReportStatus.WITHDRAWN,
    ],
    ReportStatus.NEEDS_INFO: [ReportStatus.TRIAGED, ReportStatus.WITHDRAWN],
    ReportStatus.ACCEPTED: [ReportStatus.FIXED],
    ReportStatus.FIXED: [ReportStatus.REWARDED, ReportStatus.CLOSED],
    ReportStatus.REWARDED: [ReportStatus.CLOSED],
    ReportStatus.DUPLICATE: [],
    ReportStatus.REJECTED: [],
    ReportStatus.INFORMATIVE: [],
    ReportStatus.CLOSED: [],
    ReportStatus.WITHDRAWN: [],
}


def transition_report_status(
    report: Report,
    target_status: str,
    actor_user,
    reason: str = "",
    duplicate_of_report: Report | None = None,
    triaged_severity: str | None = None,
    request=None,
) -> Report:
    """Execute status transition on a report according to the centralized state machine."""
    current_status = report.status

    if current_status == target_status:
        return report

    # Check state machine legality
    allowed = ALLOWED_TRANSITIONS.get(current_status, [])
    if target_status not in allowed:
        raise ValidationError(
            {
                "status": [
                    f"Invalid transition from '{current_status}' to '{target_status}'."
                ]
            }
        )

    # Actor permission checks
    is_hunter = actor_user.id == report.hunter_id
    org_membership = OrganizationMember.objects.filter(
        organization=report.program.organization,
        user=actor_user,
    ).first()
    is_company_triage = org_membership and org_membership.role in [
        MemberRole.COMPANY_ADMIN,
        MemberRole.COMPANY_TRIAGER,
    ]
    is_platform_admin = getattr(actor_user, "is_platform_admin", False)

    # Hunter can ONLY withdraw
    if is_hunter and not is_platform_admin:
        if target_status != ReportStatus.WITHDRAWN:
            raise PermissionDenied(
                "Researchers are only permitted to withdraw their reports."
            )
        if current_status not in [
            ReportStatus.NEW,
            ReportStatus.TRIAGED,
            ReportStatus.NEEDS_INFO,
        ]:
            raise PermissionDenied(
                "Reports cannot be withdrawn after triage decision has been reached."
            )

    # Company viewer cannot alter status
    if (
        org_membership
        and org_membership.role == MemberRole.COMPANY_VIEWER
        and not is_platform_admin
    ):
        raise PermissionDenied("Company viewers have read-only permissions.")

    # Company triagers / admins / platform admins can transition non-withdrawn states
    if not is_hunter and not is_company_triage and not is_platform_admin:
        raise PermissionDenied(
            "You do not have permission to modify this report's status."
        )

    # Handle duplicate linking
    if target_status == ReportStatus.DUPLICATE:
        if not duplicate_of_report:
            raise ValidationError(
                {
                    "duplicate_of": [
                        "Original report must be specified when marking as duplicate."
                    ]
                }
            )
        if duplicate_of_report.program_id != report.program_id:
            raise ValidationError(
                {"duplicate_of": ["Original report must belong to the same program."]}
            )
        if duplicate_of_report.id == report.id:
            raise ValidationError(
                {
                    "duplicate_of": [
                        "A report cannot be marked as a duplicate of itself."
                    ]
                }
            )
        report.duplicate_of = duplicate_of_report

    with transaction.atomic():
        old_status = report.status
        report.status = target_status
        if triaged_severity:
            report.triaged_severity = triaged_severity
        if reason:
            report.closed_reason = reason[:255]
        report.save(
            update_fields=[
                "status",
                "triaged_severity",
                "closed_reason",
                "duplicate_of",
                "updated_at",
            ]
        )

        ReportStatusHistory.objects.create(
            report=report,
            from_status=old_status,
            to_status=target_status,
            changed_by=actor_user,
            reason=reason.strip(),
        )

    log_audit_event(
        actor=actor_user,
        action=f"report.status_changed.{target_status}",
        target=report,
        metadata={
            "from_status": old_status,
            "to_status": target_status,
            "reason": reason.strip(),
        },
        request=request,
    )

    # Send generic notifications
    notify_user(
        recipient=report.hunter,
        subject="Report status updated",
        message="Your vulnerability report status has been updated on Cyber Eco.",
        link=f"/reports/{report.id}",
    )

    return report


def add_report_comment(
    report: Report,
    author_user,
    content: str,
    visibility: str = CommentVisibility.SHARED,
    request=None,
) -> ReportComment:
    """Add a comment to a report with strict visibility access checks."""
    is_hunter = author_user.id == report.hunter_id
    org_membership = OrganizationMember.objects.filter(
        organization=report.program.organization,
        user=author_user,
    ).first()
    is_platform_admin = getattr(author_user, "is_platform_admin", False)

    # Hunters can NEVER author internal comments
    if is_hunter and visibility == CommentVisibility.INTERNAL:
        raise PermissionDenied("Researchers cannot post company-internal comments.")

    if not is_hunter and not org_membership and not is_platform_admin:
        raise PermissionDenied("You do not have access to comment on this report.")

    if (
        org_membership
        and org_membership.role == MemberRole.COMPANY_VIEWER
        and not is_platform_admin
    ):
        raise PermissionDenied("Company viewers have read-only access.")

    clean_content = sanitize_markdown_text(content)
    if not clean_content:
        raise ValidationError({"content": ["Comment content cannot be empty."]})

    comment = ReportComment.objects.create(
        report=report,
        author=author_user,
        content=clean_content,
        visibility=visibility,
    )

    log_audit_event(
        actor=author_user,
        action="report.comment_added",
        target=report,
        metadata={"comment_id": str(comment.id), "visibility": visibility},
        request=request,
    )

    # Notify parties if comment is SHARED
    if visibility == CommentVisibility.SHARED:
        notify_target = report.program.organization if is_hunter else report.hunter
        notify_user(
            recipient=notify_target,
            subject="New comment on report",
            message="A new comment was posted on a vulnerability report on Cyber Eco.",
            link=(
                f"/reports/{report.id}"
                if not is_hunter
                else f"/dashboard/company/reports/{report.id}"
            ),
        )

    return comment

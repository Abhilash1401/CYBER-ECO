"""Services and SSRF-safe validators for bug bounty programs, scopes, and rewards."""

import ipaddress
import urllib.parse

from django.utils.text import slugify
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import log_audit_event
from apps.companies.models import OrganizationStatus, OrganizationVerifiedDomain

from .models import (
    AssetType,
    Program,
    ProgramInvite,
    ProgramStatus,
    ProgramVisibility,
)

# RFC 1918, RFC 3927 link-local, loopback, cloud metadata
FORBIDDEN_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("10.0.0.0/8"),  # Private RFC1918
    ipaddress.ip_network("172.16.0.0/12"),  # Private RFC1918
    ipaddress.ip_network("192.168.0.0/16"),  # Private RFC1918
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / Cloud metadata
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 Unique local
    ipaddress.ip_network("fe80::/10"),  # IPv6 Link-local
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
]


def validate_scope_asset_data(
    org, asset_type: str, asset_value: str, in_scope: bool
) -> str:
    """Validate scope target values as PURE DATA ONLY.

    Never resolves hostnames, opens network sockets, or performs HTTP fetches.
    Strictly forbids loopback, link-local, cloud metadata, RFC1918 private IPs,
    dangerous schemes, and unverified domains.
    """
    clean_val = asset_value.strip()
    if not clean_val:
        raise ValidationError({"asset_value": ["Asset value cannot be empty."]})

    if asset_type == AssetType.IP_CIDR:
        # Validate as IP address or CIDR range
        try:
            if "/" in clean_val:
                net = ipaddress.ip_network(clean_val, strict=False)
            else:
                ip = ipaddress.ip_address(clean_val)
                net = ipaddress.ip_network(f"{ip}/{ip.max_prefixlen}")
        except ValueError:
            raise ValidationError(
                {"asset_value": ["Invalid IP address or CIDR notation."]}
            )

        # Reject private, loopback, link-local, cloud metadata
        for forbidden in FORBIDDEN_NETWORKS:
            if net.overlaps(forbidden):
                raise ValidationError(
                    {
                        "asset_value": [
                            f"IP/CIDR range '{clean_val}' contains forbidden private, loopback, or metadata addresses."
                        ]
                    }
                )

    elif asset_type == AssetType.URL:
        # Validate URL scheme (must strictly be http or https)
        parsed = urllib.parse.urlparse(clean_val)
        if parsed.scheme.lower() not in ["http", "https"]:
            raise ValidationError(
                {
                    "asset_value": [
                        "URL asset must strictly use http:// or https:// protocol."
                    ]
                }
            )
        hostname = parsed.hostname or ""
        if not hostname:
            raise ValidationError({"asset_value": ["Invalid URL hostname."]})

        # Disallow loopback / metadata names
        if hostname.lower() in ["localhost", "127.0.0.1", "169.254.169.254", "::1"]:
            raise ValidationError(
                {
                    "asset_value": [
                        "URL cannot target loopback or cloud metadata addresses."
                    ]
                }
            )

        # If in-scope, verify the host domain belongs to the organization's verified domains
        if in_scope:
            verified_domains = OrganizationVerifiedDomain.objects.filter(
                organization=org,
                is_verified=True,
            ).values_list("domain", flat=True)
            matched = any(
                hostname.lower() == vd.lower()
                or hostname.lower().endswith(f".{vd.lower()}")
                for vd in verified_domains
            )
            if not matched:
                raise ValidationError(
                    {
                        "asset_value": [
                            f"Host '{hostname}' does not match any of the organization's verified domains."
                        ]
                    }
                )

    elif asset_type == AssetType.DOMAIN:
        clean_domain = clean_val.lower().lstrip(".").split(":")[0]  # remove port if any
        if clean_domain in ["localhost", "127.0.0.1", "169.254.169.254"]:
            raise ValidationError(
                {
                    "asset_value": [
                        "Domain cannot target loopback or cloud metadata addresses."
                    ]
                }
            )

        # If in-scope, ensure domain matches verified domains
        if in_scope:
            verified_domains = OrganizationVerifiedDomain.objects.filter(
                organization=org,
                is_verified=True,
            ).values_list("domain", flat=True)
            matched = any(
                clean_domain == vd.lower() or clean_domain.endswith(f".{vd.lower()}")
                for vd in verified_domains
            )
            if not matched:
                raise ValidationError(
                    {
                        "asset_value": [
                            f"Domain '{clean_domain}' is not in the organization's verified domain list."
                        ]
                    }
                )

    return clean_val


def create_program(
    org, title: str, description: str, visibility: str, actor, request=None
) -> Program:
    """Create a new bug bounty program in DRAFT status."""
    base_slug = slugify(title)
    slug = base_slug
    counter = 1
    while Program.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    program = Program.objects.create(
        organization=org,
        title=title,
        slug=slug,
        description=description,
        visibility=visibility,
        status=ProgramStatus.DRAFT,
    )

    log_audit_event(
        actor=actor,
        action="program.created",
        target=program,
        metadata={"title": program.title, "visibility": program.visibility},
        request=request,
    )
    return program


def submit_program_for_review(program: Program, actor, request=None) -> Program:
    """Company admin submits program for review: draft -> in_review.

    Validation requirements:
    1. Organization must be VERIFIED.
    2. Program must have at least one in-scope asset.
    3. Program must have at least one reward tier.
    4. Rules of engagement must not be empty.
    """
    if program.status != ProgramStatus.DRAFT:
        raise ValidationError(
            {
                "detail": f"Cannot submit program for review from status '{program.status}'."
            }
        )

    if program.organization.status != OrganizationStatus.VERIFIED:
        raise ValidationError(
            {
                "detail": "Cannot submit program: Organization must be verified by platform admin first."
            }
        )

    if not program.scopes.filter(in_scope=True).exists():
        raise ValidationError(
            {
                "detail": "Cannot submit program: At least one in-scope asset is required."
            }
        )

    if not program.rewards.exists():
        raise ValidationError(
            {"detail": "Cannot submit program: At least one reward tier is required."}
        )

    if not program.rules_of_engagement or not program.rules_of_engagement.strip():
        raise ValidationError(
            {"detail": "Cannot submit program: Rules of engagement are required."}
        )

    program.status = ProgramStatus.IN_REVIEW
    program.save(update_fields=["status", "updated_at"])

    log_audit_event(
        actor=actor,
        action="program.submitted_for_review",
        target=program,
        metadata={"status": program.status},
        request=request,
    )
    return program


def approve_program_to_active(
    program: Program, reason: str, platform_admin_user, request=None
) -> Program:
    """Only platform_admin can approve and move program from IN_REVIEW -> ACTIVE with audited reason."""
    if not platform_admin_user.is_platform_admin:
        raise PermissionDenied(
            "Only platform administrators can approve programs to active status."
        )

    if program.status != ProgramStatus.IN_REVIEW:
        raise ValidationError(
            {
                "detail": f"Only programs in 'in_review' status can be approved. Current status: '{program.status}'."
            }
        )

    if not reason or not reason.strip():
        raise ValidationError({"reason": ["An audited approval reason is required."]})

    program.status = ProgramStatus.ACTIVE
    program.save(update_fields=["status", "updated_at"])

    log_audit_event(
        actor=platform_admin_user,
        action="program.approved_active",
        target=program,
        metadata={"reason": reason.strip(), "new_status": ProgramStatus.ACTIVE},
        request=request,
    )
    return program


def transition_program_status(
    program: Program, target_status: str, actor, request=None
) -> Program:
    """Transition program lifecycle state:

    Company Admin can:
    - active -> paused
    - paused -> active
    - active / paused -> closed
    Cannot transition out of closed.
    Cannot move to active from draft/in_review directly (must go through review and platform admin approval).
    """
    current = program.status

    if current == ProgramStatus.CLOSED:
        raise ValidationError(
            {"detail": "Closed programs cannot be reopened or transitioned."}
        )

    if target_status == ProgramStatus.ACTIVE and current in [
        ProgramStatus.DRAFT,
        ProgramStatus.IN_REVIEW,
    ]:
        raise PermissionDenied(
            "Programs must be submitted for review and approved by a platform administrator."
        )

    valid_transitions = {
        ProgramStatus.ACTIVE: [ProgramStatus.PAUSED, ProgramStatus.CLOSED],
        ProgramStatus.PAUSED: [ProgramStatus.ACTIVE, ProgramStatus.CLOSED],
    }

    if target_status not in valid_transitions.get(current, []):
        raise ValidationError(
            {
                "detail": f"Invalid status transition from '{current}' to '{target_status}'."
            }
        )

    program.status = target_status
    program.save(update_fields=["status", "updated_at"])

    log_audit_event(
        actor=actor,
        action=f"program.status_changed.{target_status}",
        target=program,
        metadata={"old_status": current, "new_status": target_status},
        request=request,
    )
    return program


def invite_hunter_to_private_program(
    program: Program, hunter_user, actor, request=None
) -> ProgramInvite:
    """Invite a security researcher (hunter) to a private bug bounty program."""
    if program.visibility != ProgramVisibility.PRIVATE:
        raise ValidationError(
            {"detail": "Invitations are only applicable to private programs."}
        )

    if not hunter_user.is_hunter:
        raise ValidationError({"detail": "User is not a security researcher (hunter)."})

    invite, created = ProgramInvite.objects.get_or_create(
        program=program,
        hunter=hunter_user,
        defaults={"invited_by": actor},
    )
    if not created:
        raise ValidationError(
            {"detail": "Researcher is already invited to this program."}
        )

    log_audit_event(
        actor=actor,
        action="program.hunter_invited",
        target=program,
        metadata={"hunter_id": str(hunter_user.id), "hunter_email": hunter_user.email},
        request=request,
    )
    return invite

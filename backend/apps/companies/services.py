"""Services for Organizations, Member Management, and DNS TXT verification."""

import hashlib
import secrets
from datetime import timedelta

import dns.resolver
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.audit.services import log_audit_event

from .models import (
    MemberRole,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
    OrganizationStatus,
    OrganizationVerifiedDomain,
)


def create_organization(
    name: str, website: str, domains: list[str], creator_user, request=None
) -> Organization:
    """Create a new organization in 'pending' status and assign creator as company_admin."""
    # Enforce: one user can belong to only one organization
    if OrganizationMember.objects.filter(user=creator_user).exists():
        raise ValidationError({"detail": "User already belongs to an organization."})

    if Organization.objects.filter(name__iexact=name).exists():
        raise ValidationError({"name": ["Organization with this name already exists."]})

    org = Organization.objects.create(
        name=name,
        website=website,
        status=OrganizationStatus.PENDING,
    )

    OrganizationMember.objects.create(
        organization=org,
        user=creator_user,
        role=MemberRole.COMPANY_ADMIN,
    )

    for domain_str in domains:
        clean_domain = domain_str.strip().lower()
        if clean_domain:
            OrganizationVerifiedDomain.objects.create(
                organization=org,
                domain=clean_domain,
                verification_token=secrets.token_hex(16),
            )

    log_audit_event(
        action="organization.created",
        actor=creator_user,
        metadata={"name": org.name, "website": org.website, "org_id": str(org.id)},
        request=request,
    )
    return org


def review_organization(
    org: Organization, new_status: str, reason: str, reviewer_user, request=None
) -> Organization:
    """Platform admin review to verify, reject, or suspend an organization."""
    if not reviewer_user.is_platform_admin:
        raise PermissionDenied("Only platform administrators can review organizations.")

    # A company admin can NEVER verify their own organization
    if OrganizationMember.objects.filter(organization=org, user=reviewer_user).exists():
        raise PermissionDenied(
            "Company administrators cannot verify or review their own organization."
        )

    if new_status not in [
        OrganizationStatus.VERIFIED,
        OrganizationStatus.REJECTED,
        OrganizationStatus.SUSPENDED,
    ]:
        raise ValidationError({"status": ["Invalid status for review."]})

    if not reason or not reason.strip():
        raise ValidationError(
            {"reason": ["An audited reason is required for status changes."]}
        )

    org.status = new_status
    org.verification_reason = reason.strip()
    org.verified_at = (
        timezone.now() if new_status == OrganizationStatus.VERIFIED else None
    )
    org.verified_by = (
        reviewer_user if new_status == OrganizationStatus.VERIFIED else None
    )
    org.save(
        update_fields=[
            "status",
            "verification_reason",
            "verified_at",
            "verified_by",
            "updated_at",
        ]
    )

    log_audit_event(
        actor=reviewer_user,
        action=f"organization.review.{new_status}",
        target=org,
        metadata={"new_status": new_status, "reason": reason.strip()},
        request=request,
    )
    return org


def verify_domain_dns_txt(
    domain_obj: OrganizationVerifiedDomain, actor=None, request=None
) -> bool:
    """Verify domain using DNS TXT record lookup ONLY.

    Looks for TXT record containing: 'cybereco-verification=<token>'
    Strict DNS timeouts and never leaks external response text.
    """
    expected_token = f"cybereco-verification={domain_obj.verification_token}"
    resolver = dns.resolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 3.0

    verified = False
    try:
        answers = resolver.resolve(domain_obj.domain, "TXT")
        for rdata in answers:
            for txt_string in rdata.strings:
                if expected_token.encode("utf-8") in txt_string:
                    verified = True
                    break
            if verified:
                break
    except Exception:
        verified = False

    if verified:
        domain_obj.is_verified = True
        domain_obj.verified_at = timezone.now()
        domain_obj.save(update_fields=["is_verified", "verified_at"])

        log_audit_event(
            actor=actor,
            action="organization.domain_verified",
            target=domain_obj.organization,
            metadata={"domain": domain_obj.domain, "method": "dns_txt"},
            request=request,
        )

    return verified


def manual_verify_domain(
    domain_obj: OrganizationVerifiedDomain, admin_user, request=None
) -> OrganizationVerifiedDomain:
    """Platform admin fallback to manually verify an organization domain."""
    if not admin_user.is_platform_admin:
        raise PermissionDenied(
            "Only platform administrators can manually verify domains."
        )

    domain_obj.is_verified = True
    domain_obj.verified_at = timezone.now()
    domain_obj.verified_by = admin_user
    domain_obj.save(update_fields=["is_verified", "verified_at", "verified_by"])

    log_audit_event(
        actor=admin_user,
        action="organization.domain_manually_verified",
        target=domain_obj.organization,
        metadata={"domain": domain_obj.domain},
        request=request,
    )
    return domain_obj


def invite_member(
    org: Organization, email: str, role: str, inviter_user, request=None
) -> OrganizationInvitation:
    """Create a hashed, single-use, 7-day expiring invitation."""
    clean_email = email.strip().lower()

    # Check if already a member of this or another org
    from apps.accounts.models import User

    existing_user = User.objects.filter(email=clean_email).first()
    if existing_user and OrganizationMember.objects.filter(user=existing_user).exists():
        raise ValidationError(
            {"email": ["User is already a member of an organization."]}
        )

    if role not in MemberRole.values:
        raise ValidationError(
            {"role": [f"Invalid role. Choices are: {MemberRole.values}"]}
        )

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    expires_at = timezone.now() + timedelta(days=7)

    invitation = OrganizationInvitation.objects.create(
        organization=org,
        email=clean_email,
        role=role,
        token_hash=token_hash,
        invited_by=inviter_user,
        expires_at=expires_at,
    )

    invite_url = f"{settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'http://127.0.0.1:3000'}/invitations/accept?token={raw_token}"
    send_mail(
        subject=f"Invitation to join {org.name} on Cyber Eco",
        message=f"You have been invited to join {org.name} as {role}.\nAccept link: {invite_url}\nThis link expires in 7 days.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[clean_email],
        fail_silently=True,
    )

    log_audit_event(
        actor=inviter_user,
        action="organization.member_invited",
        target=org,
        metadata={"email": clean_email, "role": role},
        request=request,
    )
    return invitation


def accept_invitation(
    raw_token: str, accepting_user, request=None
) -> OrganizationMember:
    """Accept an invitation token, assigning the user to the organization."""
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = OrganizationInvitation.objects.filter(token_hash=token_hash).first()

    if not invitation:
        raise ValidationError({"detail": "Invalid or expired invitation token."})

    if invitation.is_used:
        raise ValidationError({"detail": "This invitation has already been used."})

    if invitation.expires_at < timezone.now():
        raise ValidationError({"detail": "This invitation has expired."})

    if invitation.email.lower() != accepting_user.email.lower():
        raise ValidationError(
            {"detail": "This invitation was issued to a different email address."}
        )

    if OrganizationMember.objects.filter(user=accepting_user).exists():
        raise ValidationError({"detail": "You already belong to an organization."})

    member = OrganizationMember.objects.create(
        organization=invitation.organization,
        user=accepting_user,
        role=invitation.role,
    )

    invitation.is_used = True
    invitation.save(update_fields=["is_used"])

    # Update user role to company role if applicable
    accepting_user.role = invitation.role
    accepting_user.save(update_fields=["role"])

    log_audit_event(
        actor=accepting_user,
        action="organization.invitation_accepted",
        target=invitation.organization,
        metadata={"role": invitation.role},
        request=request,
    )
    return member


def update_member_role(
    org: Organization, member_id: str, new_role: str, actor, request=None
) -> OrganizationMember:
    """Update role of an organization member with last-admin defense."""
    member = OrganizationMember.objects.filter(organization=org, id=member_id).first()
    if not member:
        raise ValidationError({"detail": "Member not found in organization."})

    # Cannot change your own role
    if member.user == actor:
        raise ValidationError({"detail": "You cannot change your own role."})

    if new_role not in MemberRole.values:
        raise ValidationError(
            {"role": [f"Invalid role. Choices are: {MemberRole.values}"]}
        )

    # Last admin protection
    if member.role == MemberRole.COMPANY_ADMIN and new_role != MemberRole.COMPANY_ADMIN:
        admin_count = OrganizationMember.objects.filter(
            organization=org,
            role=MemberRole.COMPANY_ADMIN,
        ).count()
        if admin_count <= 1:
            raise ValidationError(
                {"detail": "Cannot demote the last organization administrator."}
            )

    old_role = member.role
    member.role = new_role
    member.save(update_fields=["role"])

    # Synchronize user model role
    member.user.role = new_role
    member.user.save(update_fields=["role"])

    log_audit_event(
        actor=actor,
        action="organization.member_role_updated",
        target=org,
        metadata={
            "member_user_id": str(member.user.id),
            "old_role": old_role,
            "new_role": new_role,
        },
        request=request,
    )
    return member


def remove_member(org: Organization, member_id: str, actor, request=None) -> None:
    """Remove member from organization with last-admin defense."""
    from rest_framework.exceptions import NotFound

    member = OrganizationMember.objects.filter(organization=org, id=member_id).first()
    if not member:
        raise NotFound("Member not found in organization.")

    # Last admin protection
    if member.role == MemberRole.COMPANY_ADMIN:
        admin_count = OrganizationMember.objects.filter(
            organization=org,
            role=MemberRole.COMPANY_ADMIN,
        ).count()
        if admin_count <= 1:
            raise ValidationError(
                {"detail": "Cannot remove the last organization administrator."}
            )

    user_removed = member.user
    member.delete()

    log_audit_event(
        actor=actor,
        action="organization.member_removed",
        target=org,
        metadata={"removed_user_id": str(user_removed.id)},
        request=request,
    )

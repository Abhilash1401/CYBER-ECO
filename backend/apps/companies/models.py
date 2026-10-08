"""Models for Organizations, Members, Verified Domains, and Invitations."""

import secrets
import uuid

from django.conf import settings
from django.db import models


class OrganizationStatus(models.TextChoices):
    PENDING = "pending", "Pending Verification"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"
    SUSPENDED = "suspended", "Suspended"


class MemberRole(models.TextChoices):
    COMPANY_ADMIN = "company_admin", "Company Admin"
    COMPANY_TRIAGER = "company_triager", "Company Triager"
    COMPANY_VIEWER = "company_viewer", "Company Viewer"


class Organization(models.Model):
    """Organization entity representing a company running bug bounties."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    website = models.URLField()
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.PENDING,
        db_index=True,
    )
    verification_reason = models.TextField(blank=True, default="")
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_organizations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def is_verified(self):
        return self.status == OrganizationStatus.VERIFIED


class OrganizationVerifiedDomain(models.Model):
    """Domain verified by DNS TXT record or platform admin approval."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="verified_domains",
    )
    domain = models.CharField(max_length=255, db_index=True)
    verification_token = models.CharField(max_length=64, default=secrets.token_hex)
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="manually_verified_domains",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "domain")
        ordering = ["domain"]

    def __str__(self):
        return f"{self.domain} ({'verified' if self.is_verified else 'pending'})"


class OrganizationMember(models.Model):
    """Membership mapping user to an organization with a specific role."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )
    role = models.CharField(
        max_length=20,
        choices=MemberRole.choices,
        default=MemberRole.COMPANY_VIEWER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("organization", "user")
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.role})"


class OrganizationInvitation(models.Model):
    """Expiring, single-use invitation sent to a user by email."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(max_length=20, choices=MemberRole.choices)
    token_hash = models.CharField(max_length=64, unique=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_org_invitations",
    )
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invite {self.email} -> {self.organization.name} ({self.role})"

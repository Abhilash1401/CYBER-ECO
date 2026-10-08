"""Models for Programs, Scopes, Rewards, and Private Program Invites."""

import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ProgramStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_REVIEW = "in_review", "In Review"
    ACTIVE = "active", "Active"
    PAUSED = "paused", "Paused"
    CLOSED = "closed", "Closed"


class ProgramVisibility(models.TextChoices):
    PUBLIC = "public", "Public"
    PRIVATE = "private", "Private"


class AssetType(models.TextChoices):
    DOMAIN = "domain", "Domain / Subdomain"
    URL = "url", "Web Application / URL"
    IP_CIDR = "ip_cidr", "IP Address / CIDR Range"
    MOBILE_APP = "mobile_app", "Mobile Application"
    OTHER = "other", "Other Asset"


class Severity(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"
    CRITICAL = "critical", "Critical"


class Program(models.Model):
    """Bug bounty program run by a verified organization."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "companies.Organization",
        on_delete=models.PROTECT,
        related_name="programs",
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    description = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=ProgramStatus.choices,
        default=ProgramStatus.DRAFT,
        db_index=True,
    )
    visibility = models.CharField(
        max_length=20,
        choices=ProgramVisibility.choices,
        default=ProgramVisibility.PUBLIC,
        db_index=True,
    )
    rules_of_engagement = models.TextField(blank=True, default="")
    safe_harbor = models.TextField(
        blank=True,
        default="Activities conducted in accordance with this policy will be considered authorized conduct.",
    )
    disclosure_policy = models.TextField(
        blank=True,
        default="Coordinated vulnerability disclosure: 90 days standard remediation window.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"


class ProgramScope(models.Model):
    """Scope target definition. Stored and handled as DATA ONLY."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="scopes",
    )
    asset_type = models.CharField(max_length=20, choices=AssetType.choices)
    asset_value = models.CharField(max_length=512)
    in_scope = models.BooleanField(default=True)
    notes = models.TextField(blank=True, default="")
    max_severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-in_scope", "asset_type", "asset_value"]

    def __str__(self):
        scope_str = "In-Scope" if self.in_scope else "Out-of-Scope"
        return f"[{scope_str}] {self.asset_type}: {self.asset_value}"


class ProgramReward(models.Model):
    """Reward tier payout structure per vulnerability severity level."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="rewards",
    )
    severity = models.CharField(max_length=20, choices=Severity.choices)
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    currency = models.CharField(max_length=3, default="USD")

    class Meta:
        unique_together = ("program", "severity")
        ordering = ["severity"]

    def __str__(self):
        return f"{self.program.title} - {self.severity.upper()}: ${self.min_amount}-${self.max_amount}"


class ProgramInvite(models.Model):
    """Invitation granting a security researcher access to a private bounty program."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        Program,
        on_delete=models.CASCADE,
        related_name="invites",
    )
    hunter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="program_invites",
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="sent_program_invites",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("program", "hunter")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.hunter.email} -> {self.program.title}"

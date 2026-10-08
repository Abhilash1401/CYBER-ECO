"""Vulnerability report models, status history, comments, and evidence."""

import uuid

from django.conf import settings
from django.db import models

from apps.programs.models import Severity


class ReportStatus(models.TextChoices):
    NEW = "new", "New"
    TRIAGED = "triaged", "Triaged"
    NEEDS_INFO = "needs_info", "Needs More Info"
    ACCEPTED = "accepted", "Accepted"
    DUPLICATE = "duplicate", "Duplicate"
    REJECTED = "rejected", "Rejected"
    INFORMATIVE = "informative", "Informative"
    FIXED = "fixed", "Fixed"
    REWARDED = "rewarded", "Rewarded"
    CLOSED = "closed", "Closed"
    WITHDRAWN = "withdrawn", "Withdrawn"


class VulnerabilityType(models.TextChoices):
    RCE = "rce", "Remote Code Execution (RCE)"
    SQLI = "sqli", "SQL Injection"
    XSS = "xss", "Cross-Site Scripting (XSS)"
    SSRF = "ssrf", "Server-Side Request Forgery (SSRF)"
    IDOR = "idor", "Insecure Direct Object Reference (IDOR)"
    BAC = "bac", "Broken Access Control"
    AUTH_BYPASS = "auth_bypass", "Authentication Bypass"
    CSRF = "csrf", "Cross-Site Request Forgery (CSRF)"
    INFO_DISCLOSURE = "info_disclosure", "Information Disclosure"
    OPEN_REDIRECT = "open_redirect", "Open Redirect"
    BUSINESS_LOGIC = "business_logic", "Business Logic Vulnerability"
    OTHER = "other", "Other Vulnerability"


class CommentVisibility(models.TextChoices):
    SHARED = "shared", "Shared with Hunter"
    INTERNAL = "internal", "Company Internal Only"


class ScanStatus(models.TextChoices):
    PENDING = "pending", "Pending Scan"
    CLEAN = "clean", "Clean"
    INFECTED = "infected", "Infected"


class Report(models.Model):
    """Vulnerability report submitted by a security researcher to a program."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    program = models.ForeignKey(
        "programs.Program",
        on_delete=models.CASCADE,
        related_name="reports",
    )
    hunter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_reports",
    )
    target_asset = models.ForeignKey(
        "programs.ProgramScope",
        on_delete=models.PROTECT,
        related_name="reports",
    )
    title = models.CharField(max_length=255)
    vulnerability_type = models.CharField(
        max_length=64,
        choices=VulnerabilityType.choices,
        default=VulnerabilityType.OTHER,
    )
    description = models.TextField()
    steps_to_reproduce = models.TextField()
    impact = models.TextField()
    severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        help_text="Hunter-suggested initial severity",
    )
    triaged_severity = models.CharField(
        max_length=20,
        choices=Severity.choices,
        null=True,
        blank=True,
        help_text="Company-assigned triaged severity",
    )
    cvss_vector = models.CharField(max_length=128, blank=True)
    cvss_score = models.DecimalField(
        max_digits=3,
        decimal_places=1,
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=32,
        choices=ReportStatus.choices,
        default=ReportStatus.NEW,
        db_index=True,
    )
    duplicate_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="duplicates",
        help_text="Original report if marked as duplicate",
    )
    closed_reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.status.upper()}] {self.title} (#{str(self.id)[:8]})"


class ReportStatusHistory(models.Model):
    """Audit trail of status transitions for a report."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=32, choices=ReportStatus.choices)
    to_status = models.CharField(max_length=32, choices=ReportStatus.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="status_changes",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.report_id}: {self.from_status} -> {self.to_status}"


class ReportComment(models.Model):
    """Comment on a vulnerability report (Shared vs. Company Internal)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="report_comments",
    )
    visibility = models.CharField(
        max_length=20,
        choices=CommentVisibility.choices,
        default=CommentVisibility.SHARED,
        db_index=True,
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author.email} on Report {self.report_id} ({self.visibility})"


class ReportEvidence(models.Model):
    """Uploaded PoC evidence attachment stored in private object storage."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name="evidence",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="uploaded_evidence",
    )
    file_key = models.CharField(max_length=255, unique=True)
    original_filename = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=128)
    sha256_hash = models.CharField(max_length=64)
    scan_status = models.CharField(
        max_length=20,
        choices=ScanStatus.choices,
        default=ScanStatus.PENDING,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.original_filename} ({self.scan_status}) for Report {self.report_id}"
        )

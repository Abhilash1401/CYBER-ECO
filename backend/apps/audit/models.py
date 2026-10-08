"""Append-only audit log model.

Security rules:
- Append-only: updates and deletions are prevented in Python.
- TODO (Phase 7): Add PostgreSQL-level trigger/rule to prevent UPDATE/DELETE at the DB level.
- Never log passwords, tokens, or MFA codes.
"""

import uuid

from django.core.exceptions import PermissionDenied
from django.db import models


class AuditLog(models.Model):
    """Immutable audit trail for security events."""

    ACTION_CHOICES = (
        ("LOGIN_SUCCESS", "Login Success"),
        ("LOGIN_FAILURE", "Login Failure"),
        ("LOGOUT", "Logout"),
        ("REGISTER", "Register"),
        ("EMAIL_VERIFIED", "Email Verified"),
        ("MFA_SETUP", "MFA Setup"),
        ("MFA_VERIFIED", "MFA Verified"),
        ("MFA_DISABLED", "MFA Disabled"),
        ("RECOVERY_CODES_REGENERATED", "Recovery Codes Regenerated"),
        ("PASSWORD_CHANGED", "Password Changed"),
        ("PASSWORD_RESET_REQUESTED", "Password Reset Requested"),
        ("PASSWORD_RESET_CONFIRMED", "Password Reset Confirmed"),
        ("ROLE_CHANGED", "Role Changed"),
        ("PROFILE_UPDATED", "Profile Updated"),
    )

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    action = models.CharField(max_length=64, choices=ACTION_CHOICES, db_index=True)
    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_actions",
    )
    target_user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="target_audit_logs",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "audit_log"
        ordering = ["-timestamp"]
        verbose_name = "audit log"
        verbose_name_plural = "audit logs"

    def __str__(self):
        actor_email = self.actor.email if self.actor else "Anonymous"
        return f"[{self.timestamp}] {self.action} by {actor_email}"

    def save(self, *args, **kwargs):
        """Enforce append-only in Python."""
        if self.pk and AuditLog.objects.filter(pk=self.pk).exists():
            raise PermissionDenied(
                "Audit log entries are immutable and cannot be updated."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Enforce deletion prevention in Python."""
        raise PermissionDenied("Audit log entries cannot be deleted.")

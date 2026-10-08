"""Notification models for user and company alerts."""

import uuid

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app notification with generic text and link only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    subject = models.CharField(max_length=255)
    message = models.TextField(help_text="Generic text only, no report contents")
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification to {self.user.email}: {self.subject}"

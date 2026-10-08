"""Tests for AuditLog immutability, safe IP logging, and sensitive data sanitization."""

import pytest
from apps.accounts.models import User
from apps.audit.services import get_client_ip, log_audit_event
from django.core.exceptions import PermissionDenied


@pytest.mark.django_db
class TestAuditLog:
    def test_audit_log_entries_created_and_immutable(self, rf):
        """AuditLog entries cannot be modified or deleted via model methods."""
        user = User.objects.create_user(
            email="audited@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        request = rf.post("/api/v1/auth/login/", REMOTE_ADDR="192.168.1.100")

        log = log_audit_event(
            "LOGIN_SUCCESS",
            request=request,
            actor=user,
            target_user=user,
            metadata={"source": "test_suite"},
        )
        assert log.pk is not None
        assert log.action == "LOGIN_SUCCESS"
        assert log.ip_address == "192.168.1.100"

        # Immutability: attempting to update raises PermissionDenied
        log.action = "MODIFIED_ACTION"
        with pytest.raises(PermissionDenied):
            log.save()

        # Immutability: attempting to delete raises PermissionDenied
        with pytest.raises(PermissionDenied):
            log.delete()

    def test_safe_ip_extraction_does_not_blindly_trust_forwarded_for(self, rf):
        """Untrusted X-Forwarded-For is ignored, falling back to REMOTE_ADDR."""
        # Spoofed X-Forwarded-For header from client
        request = rf.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.1.1.1, 10.0.0.1",
            REMOTE_ADDR="127.0.0.1",
        )
        ip = get_client_ip(request)
        # Without SECURE_PROXY_SSL_HEADER / trusted proxies configured, defaults safely to REMOTE_ADDR
        assert ip == "127.0.0.1"

    def test_sensitive_fields_stripped_from_audit_metadata(self, rf):
        """Passwords, tokens, TOTP codes, and secrets are strictly stripped from audit metadata."""
        user = User.objects.create_user(
            email="sanitized@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        request = rf.post("/", REMOTE_ADDR="127.0.0.1")

        dirty_metadata = {
            "password": "SuperSecretPassword!",
            "token": "raw-secret-token",
            "totp_code": "123456",
            "mfa_secret": "JBSWY3DPEHPK3PXP",
            "safe_action": "profile_update",
        }

        log = log_audit_event(
            "TEST_ACTION",
            request=request,
            actor=user,
            metadata=dirty_metadata,
        )

        assert "password" not in log.metadata
        assert "token" not in log.metadata
        assert "totp_code" not in log.metadata
        assert "mfa_secret" not in log.metadata
        assert log.metadata["safe_action"] == "profile_update"

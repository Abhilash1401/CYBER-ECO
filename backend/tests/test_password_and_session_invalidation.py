"""Tests for password reset, password change, and session invalidation."""

import pytest
from apps.accounts.models import PasswordResetToken, User
from django.contrib.sessions.models import Session


@pytest.mark.django_db
class TestPasswordAndSessions:
    def test_password_reset_flow(self, api_client):
        """Requesting password reset creates hashed token; confirming resets password and invalidates sessions."""
        user = User.objects.create_user(
            email="reset_target@example.com",
            password="OldPassword123!",
            role="hunter",
            is_verified=True,
        )

        # 1. Request reset
        req_resp = api_client.post(
            "/api/v1/auth/password/reset/",
            {"email": "reset_target@example.com"},
            format="json",
        )
        assert req_resp.status_code == 200
        assert "password reset link has been sent" in req_resp.data["detail"]

        token_obj = PasswordResetToken.objects.filter(user=user, is_used=False).first()
        assert token_obj is not None
        assert len(token_obj.token_hash) == 64

        # Generate fresh raw token for confirmation test
        raw_token = PasswordResetToken.create_for_user(user)

        # 2. Confirm reset
        confirm_resp = api_client.post(
            "/api/v1/auth/password/reset/confirm/",
            {"token": raw_token, "new_password": "BrandNewPassword123!"},
            format="json",
        )
        assert confirm_resp.status_code == 200
        assert "Password successfully reset" in confirm_resp.data["detail"]

        # Old password no longer works
        old_login = api_client.post(
            "/api/v1/auth/login/",
            {"email": "reset_target@example.com", "password": "OldPassword123!"},
            format="json",
        )
        assert old_login.status_code == 400

        # New password works
        new_login = api_client.post(
            "/api/v1/auth/login/",
            {"email": "reset_target@example.com", "password": "BrandNewPassword123!"},
            format="json",
        )
        assert new_login.status_code == 200

        # Single-use: using same reset token again fails
        reused_resp = api_client.post(
            "/api/v1/auth/password/reset/confirm/",
            {"token": raw_token, "new_password": "YetAnotherPassword123!"},
            format="json",
        )
        assert reused_resp.status_code == 400

    def test_expired_password_reset_token_rejected(self, api_client):
        """Expired password reset token is rejected."""
        from datetime import timedelta

        from django.utils import timezone

        user = User.objects.create_user(
            email="expired_reset@example.com",
            password="OldPassword123!",
            role="hunter",
            is_verified=True,
        )
        raw_token = PasswordResetToken.create_for_user(user)

        # Backdate expiration
        tok = PasswordResetToken.objects.get(user=user)
        tok.expires_at = timezone.now() - timedelta(minutes=10)
        tok.save(update_fields=["expires_at"])

        resp = api_client.post(
            "/api/v1/auth/password/reset/confirm/",
            {"token": raw_token, "new_password": "NewExpiredPassword123!"},
            format="json",
        )
        assert resp.status_code == 400

    def test_change_password_invalidates_other_sessions(self, api_client):
        """Changing password updates credentials and invalidates all other active sessions."""
        user = User.objects.create_user(
            email="session_kill@example.com",
            password="CurrentPassword123!",
            role="hunter",
            is_verified=True,
        )

        # Simulate another active session in database
        from django.contrib.sessions.backends.db import SessionStore

        other_session = SessionStore()
        other_session["_auth_user_id"] = str(user.id)
        other_session.save()
        other_key = other_session.session_key
        assert Session.objects.filter(session_key=other_key).exists()

        # Log in current client
        api_client.force_login(user)

        # Change password
        resp = api_client.post(
            "/api/v1/auth/password/change/",
            {
                "current_password": "CurrentPassword123!",
                "new_password": "UpgradedPassword123!",
            },
            format="json",
        )
        assert resp.status_code == 200

        # Other session should now be purged
        assert not Session.objects.filter(session_key=other_key).exists()

        # Old password no longer authenticates
        api_client.logout()
        fail_login = api_client.post(
            "/api/v1/auth/login/",
            {"email": "session_kill@example.com", "password": "CurrentPassword123!"},
            format="json",
        )
        assert fail_login.status_code == 400

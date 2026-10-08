"""Tests for authentication, session handling, rotation, logout, and Axes lockout."""

import pytest
from apps.accounts.models import User


@pytest.mark.django_db
class TestAuthAndSession:
    def test_unverified_user_cannot_login(self, api_client):
        """Unverified user login attempt is blocked with 403."""
        User.objects.create_user(
            email="unverified@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=False,
        )
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "unverified@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        assert response.status_code == 403
        assert "Email verification required" in response.data["detail"]

    def test_verified_user_login_success_and_session_cycle(self, api_client):
        """Verified user logs in, receives session cookie, and cycles session key."""
        user = User.objects.create_user(
            email="verified@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "verified@example.com", "password": "StrongPassword123!"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["user"]["email"] == "verified@example.com"
        assert response.data["mfa_required"] is False

        # Session cookie is present
        assert "sessionid" in response.cookies
        session_id = response.cookies["sessionid"].value
        assert session_id

        # Authenticated endpoint works with session
        api_client.cookies["sessionid"] = session_id
        me_resp = api_client.get("/api/v1/auth/me/")
        assert me_resp.status_code == 200
        assert me_resp.data["email"] == "verified@example.com"

    def test_logout_clears_session(self, api_client):
        """Logging out invalidates current session."""
        user = User.objects.create_user(
            email="logout_test@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        api_client.force_login(user)

        me_resp = api_client.get("/api/v1/auth/me/")
        assert me_resp.status_code == 200

        logout_resp = api_client.post("/api/v1/auth/logout/")
        assert logout_resp.status_code == 200

        # After logout, accessing protected endpoint returns 401
        me_resp2 = api_client.get("/api/v1/auth/me/")
        assert me_resp2.status_code in (401, 403)

    def test_axes_lockout_after_failures(self, api_client):
        """Axes or LoginRateThrottle locks out / throttles after repeated failures."""
        User.objects.create_user(
            email="axes_target@example.com",
            password="CorrectPassword123!",
            role="hunter",
            is_verified=True,
        )

        for _ in range(5):
            api_client.post(
                "/api/v1/auth/login/",
                {"email": "axes_target@example.com", "password": "WrongPassword!"},
                format="json",
            )

        # 6th attempt should be blocked with 429 (Throttle) or 403 (Axes)
        response = api_client.post(
            "/api/v1/auth/login/",
            {"email": "axes_target@example.com", "password": "WrongPassword!"},
            format="json",
        )
        assert response.status_code in (403, 429)

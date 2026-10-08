"""Tests for registration, email verification, and anti-enumeration."""

import pytest
from apps.accounts.models import EmailVerificationToken, User
from django.core import mail


@pytest.mark.django_db
class TestRegistration:
    def test_hunter_registration_success(self, api_client):
        """Standard hunter registration generates unverified user and sends email with token."""
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "hunter1@example.com",
                "password": "StrongPassword123!",
                "role": "hunter",
            },
            format="json",
        )
        assert response.status_code == 201
        assert "Registration received" in response.data["detail"]

        user = User.objects.get(email="hunter1@example.com")
        assert user.role == "hunter"
        assert not user.is_verified
        assert not user.mfa_enabled

        # Verify token created in DB is hashed
        token_obj = EmailVerificationToken.objects.get(user=user)
        assert len(token_obj.token_hash) == 64  # SHA-256 hash length

        # Mail was sent
        assert len(mail.outbox) == 1
        assert "Verify your Cyber Eco" in mail.outbox[0].subject

    def test_company_admin_registration_success(self, api_client):
        """Company admin registration succeeds."""
        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "admin1@corp.example",
                "password": "StrongPassword123!",
                "role": "company_admin",
            },
            format="json",
        )
        assert response.status_code == 201
        user = User.objects.get(email="admin1@corp.example")
        assert user.role == "company_admin"
        assert not user.is_verified

    def test_privileged_roles_rejected_at_registration(self, api_client):
        """Privileged roles (platform_admin, company_triager, company_viewer) cannot be self-registered."""
        for disallowed in [
            "platform_admin",
            "company_triager",
            "company_viewer",
            "superadmin",
        ]:
            response = api_client.post(
                "/api/v1/auth/register/",
                {
                    "email": f"bad_{disallowed}@example.com",
                    "password": "StrongPassword123!",
                    "role": disallowed,
                },
                format="json",
            )
            assert response.status_code == 400
            assert "role" in response.data
            assert not User.objects.filter(
                email=f"bad_{disallowed}@example.com"
            ).exists()

    def test_anti_enumeration_on_duplicate_email(self, api_client):
        """Registering with an already existing email returns identical 201 and doesn't reveal existence."""
        User.objects.create_user(
            email="existing@example.com", password="Password123!", role="hunter"
        )
        mail.outbox.clear()

        response = api_client.post(
            "/api/v1/auth/register/",
            {
                "email": "existing@example.com",
                "password": "StrongPassword123!",
                "role": "hunter",
            },
            format="json",
        )
        assert response.status_code == 201
        assert "Registration received" in response.data["detail"]
        # No extra verification email sent to existing user
        assert len(mail.outbox) == 0

    def test_email_verification_flow(self, api_client):
        """Verifying with valid token sets is_verified=True; token is single-use."""
        user = User.objects.create_user(
            email="verify_me@example.com",
            password="Password123!",
            role="hunter",
            is_verified=False,
        )
        raw_token = EmailVerificationToken.create_for_user(user)

        # Successful verification
        response = api_client.post(
            "/api/v1/auth/verify-email/",
            {"token": raw_token},
            format="json",
        )
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.is_verified

        # Single-use check: second attempt with same token fails
        response2 = api_client.post(
            "/api/v1/auth/verify-email/",
            {"token": raw_token},
            format="json",
        )
        assert response2.status_code == 400

    def test_expired_email_token_rejected(self, api_client):
        """Expired verification token is rejected."""
        from datetime import timedelta

        from django.utils import timezone

        user = User.objects.create_user(
            email="expired_tok@example.com",
            password="Password123!",
            role="hunter",
            is_verified=False,
        )
        raw_token = EmailVerificationToken.create_for_user(user)

        # Backdate expiration
        tok = EmailVerificationToken.objects.get(user=user)
        tok.expires_at = timezone.now() - timedelta(hours=2)
        tok.save(update_fields=["expires_at"])

        resp = api_client.post(
            "/api/v1/auth/verify-email/",
            {"token": raw_token},
            format="json",
        )
        assert resp.status_code == 400
        user.refresh_from_db()
        assert not user.is_verified

    def test_resend_verification_anti_enumeration(self, api_client):
        """Resend verification always returns identical response whether email exists or not."""
        response = api_client.post(
            "/api/v1/auth/resend-verification/",
            {"email": "unknown@example.com"},
            format="json",
        )
        assert response.status_code == 200
        assert "If the account exists" in response.data["detail"]

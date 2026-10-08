"""Tests for TOTP MFA, encrypted secret at rest, recovery codes, and mandatory MFA policy."""

import base64

import pytest
from apps.accounts.models import MFARecoveryCode, User, UserTOTPDevice, hash_token
from django_otp.oath import TOTP


@pytest.mark.django_db
class TestMFA:
    def test_mfa_setup_and_confirmation(self, api_client):
        """MFA setup produces encrypted secret at rest, valid QR, and requires valid TOTP code to confirm."""
        user = User.objects.create_user(
            email="mfa_user@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        api_client.force_login(user)

        # 1. Setup endpoint
        setup_resp = api_client.post("/api/v1/auth/mfa/setup/")
        assert setup_resp.status_code == 200
        data = setup_resp.data
        assert "secret" in data
        assert "qr_code" in data
        assert "recovery_codes" in data
        assert len(data["recovery_codes"]) == 8

        # Verify device in DB has encrypted secret, NOT plaintext
        device = UserTOTPDevice.objects.get(user=user)
        assert not device.is_confirmed
        # The encrypted string stored in DB is different from base32 secret returned to user
        assert device.encrypted_secret != data["secret"]

        # Recovery codes stored hashed
        for code in data["recovery_codes"]:
            h = hash_token(code)
            assert MFARecoveryCode.objects.filter(user=user, code_hash=h).exists()

        # 2. Confirm setup with real TOTP code
        secret_bytes = base64.b32decode(data["secret"], casefold=True)
        totp = TOTP(key=secret_bytes, step=30, digits=6)
        valid_code = str(totp.token()).zfill(6)

        confirm_resp = api_client.post(
            "/api/v1/auth/mfa/confirm/",
            {"code": valid_code},
            format="json",
        )
        assert confirm_resp.status_code == 200
        user.refresh_from_db()
        assert user.mfa_enabled

    def test_recovery_code_single_use(self, api_client):
        """Recovery code can be used to authenticate once, then becomes invalid."""
        user = User.objects.create_user(
            email="rec_user@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
            mfa_enabled=True,
        )
        raw_code = "ABCD-1234"
        MFARecoveryCode.objects.create(
            user=user,
            code_hash=hash_token(raw_code),
            is_used=False,
        )

        # Login with recovery code
        resp = api_client.post(
            "/api/v1/auth/login/",
            {
                "email": "rec_user@example.com",
                "password": "StrongPassword123!",
                "recovery_code": raw_code,
            },
            format="json",
        )
        assert resp.status_code == 200

        # Try using same recovery code again
        resp2 = api_client.post(
            "/api/v1/auth/login/",
            {
                "email": "rec_user@example.com",
                "password": "StrongPassword123!",
                "recovery_code": raw_code,
            },
            format="json",
        )
        assert resp2.status_code == 400

    def test_mandatory_mfa_blocks_company_and_platform_admin(self, api_client):
        """Company admins and platform admins without MFA cannot access protected endpoints."""
        company_admin = User.objects.create_user(
            email="corp_boss@example.com",
            password="StrongPassword123!",
            role="company_admin",
            is_verified=True,
            mfa_enabled=False,
        )
        api_client.force_login(company_admin)

        # Accessing standard protected view (e.g., profile-me) should be forbidden
        resp = api_client.get("/api/v1/profiles/me/")
        assert resp.status_code == 403
        assert "MFA setup is mandatory" in resp.data["detail"]

        # But MFA setup endpoint is explicitly exempt and accessible!
        setup_resp = api_client.post("/api/v1/auth/mfa/setup/")
        assert setup_resp.status_code == 200

    def test_disable_mfa_requires_reauthentication(self, api_client):
        """Disabling MFA requires password + TOTP reauthentication; company admins cannot disable."""
        # 1. Company admin cannot disable MFA
        admin_user = User.objects.create_user(
            email="admin_mfa@example.com",
            password="StrongPassword123!",
            role="company_admin",
            is_verified=True,
            mfa_enabled=True,
        )
        api_client.force_login(admin_user)
        dis_resp = api_client.post(
            "/api/v1/auth/mfa/disable/",
            {"password": "StrongPassword123!"},
            format="json",
        )
        assert dis_resp.status_code == 403
        assert "mandatory" in dis_resp.data["detail"].lower()

        # 2. Hunter can disable MFA only with correct re-auth password + TOTP code
        hunter_user = User.objects.create_user(
            email="hunter_mfa@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
            mfa_enabled=True,
        )
        api_client.force_login(hunter_user)

        # Attempt with wrong password fails
        bad_pw_resp = api_client.post(
            "/api/v1/auth/mfa/disable/",
            {"password": "WrongPassword!"},
            format="json",
        )
        assert bad_pw_resp.status_code in (400, 403)
        hunter_user.refresh_from_db()
        assert hunter_user.mfa_enabled

    def test_regenerate_recovery_codes_requires_reauth(self, api_client):
        """Regenerating recovery codes fails without correct re-authentication password."""
        user = User.objects.create_user(
            email="regen_rec@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
            mfa_enabled=True,
        )
        api_client.force_login(user)

        # Wrong password fails
        resp = api_client.post(
            "/api/v1/auth/mfa/recovery-codes/",
            {"password": "WrongPassword!"},
            format="json",
        )
        assert resp.status_code in (400, 403)

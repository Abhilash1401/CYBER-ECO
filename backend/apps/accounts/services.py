"""Authentication, registration, TOTP MFA, and account lifecycle services."""

import base64
import io
import logging
import secrets
import urllib.parse
from typing import Any

import qrcode
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.hashers import check_password
from django.contrib.sessions.models import Session
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.utils import timezone
from django_otp.oath import TOTP
from rest_framework.exceptions import ValidationError

from apps.audit.services import log_audit_event

from .models import (
    EmailVerificationToken,
    HunterProfile,
    MFARecoveryCode,
    PasswordResetToken,
    User,
    UserRole,
    UserTOTPDevice,
    hash_token,
)

logger = logging.getLogger(__name__)

DUMMY_ARGON2_HASH = "argon2$argon2id$v=19$m=102400,t=2,p=8$dGtTSmFRaVZoRHVKSmVQV3BXR0Fwdg$ufGEnXUw6rHFh5av43nC8UQG1/g80yurEQ9pxS+V5/o"


def register_user(
    email: str,
    password: str,
    role: str = UserRole.HUNTER,
    request=None,
) -> tuple[User | None, bool]:
    """Register a new user with email and password.

    Allowed self-registration roles: 'hunter' or 'company_admin'.
    Returns (user, created). If user already exists, simulates timing and returns (None, False).
    """
    if role not in (UserRole.HUNTER, UserRole.COMPANY_ADMIN):
        raise ValidationError({"role": f"Cannot self-register as '{role}'."})

    # Anti-enumeration: if email already exists, perform simulated password hash to prevent timing difference
    existing = User.objects.filter(email__iexact=email).first()
    if existing:
        check_password(password, DUMMY_ARGON2_HASH)
        # Do not expose user exists, do not send email
        return None, False

    user = User.objects.create_user(
        email=email,
        password=password,
        role=role,
        is_verified=False,
        mfa_enabled=False,
    )

    # Auto-create HunterProfile if role is hunter
    if role == UserRole.HUNTER:
        base_username = email.split("@")[0].lower()
        cleaned_username = "".join(c for c in base_username if c.isalnum() or c == "_")[
            :20
        ]
        if not cleaned_username or len(cleaned_username) < 3:
            cleaned_username = "hunter"
        username = cleaned_username
        counter = 1
        while HunterProfile.objects.filter(username=username).exists():
            username = f"{cleaned_username}_{counter}"
            counter += 1

        HunterProfile.objects.create(
            user=user,
            username=username,
            display_name=cleaned_username.title(),
        )

    # Generate verification token
    raw_token = EmailVerificationToken.create_for_user(user)
    send_verification_email(user, raw_token)

    log_audit_event("REGISTER", request=request, actor=user, target_user=user)
    return user, True


def send_verification_email(user: User, raw_token: str) -> None:
    """Send verification link with single-use token."""
    verify_url = f"{settings.CORS_ALLOWED_ORIGINS[0]}/verify-email?token={raw_token}"
    subject = "Verify your Cyber Eco account"
    message = (
        f"Welcome to Cyber Eco!\n\n"
        f"Please verify your email address by visiting this link:\n"
        f"{verify_url}\n\n"
        f"This link expires in 24 hours. If you did not create this account, please ignore this email."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=True,
    )


def verify_email_token(raw_token: str, request=None) -> User:
    """Verify single-use email verification token."""
    token_hash = hash_token(raw_token)
    token_obj = (
        EmailVerificationToken.objects.select_related("user")
        .filter(token_hash=token_hash)
        .first()
    )

    if not token_obj or not token_obj.is_valid():
        raise ValidationError({"token": "Invalid or expired verification token."})

    token_obj.is_used = True
    token_obj.save(update_fields=["is_used"])

    user = token_obj.user
    user.is_verified = True
    user.save(update_fields=["is_verified"])

    log_audit_event("EMAIL_VERIFIED", request=request, actor=user, target_user=user)
    return user


def resend_verification_email(email: str, request=None) -> None:
    """Resend email verification token (uniform response for enumeration safety)."""
    user = User.objects.filter(email__iexact=email).first()
    if user and not user.is_verified:
        raw_token = EmailVerificationToken.create_for_user(user)
        send_verification_email(user, raw_token)
    else:
        # Simulate constant time
        check_password("dummy", DUMMY_ARGON2_HASH)


def authenticate_and_login_user(
    request,
    email: str,
    password: str,
    totp_code: str = "",
    recovery_code: str = "",
) -> User:
    """Authenticate credentials, check verification, check MFA if enabled, rotate session, and log audit."""
    user = authenticate(request, username=email, password=password)

    if not user:
        # Check if user exists for audit log (without revealing to client)
        target = User.objects.filter(email__iexact=email).first()
        log_audit_event(
            "LOGIN_FAILURE",
            request=request,
            target_user=target,
            metadata={"email": email},
        )
        raise ValidationError({"detail": "Invalid email or password."})

    if not user.is_verified:
        log_audit_event(
            "LOGIN_FAILURE",
            request=request,
            actor=user,
            target_user=user,
            metadata={"reason": "email_unverified"},
        )
        raise PermissionDenied("Email verification required before login.")

    # If MFA is enabled on user's account, verify code or recovery code
    if user.mfa_enabled:
        mfa_input = totp_code or recovery_code
        if not mfa_input or not verify_user_totp(user, mfa_input):
            log_audit_event(
                "MFA_VERIFY_FAILURE",
                request=request,
                actor=user,
                target_user=user,
            )
            raise ValidationError(
                {"detail": "Invalid or missing two-factor authentication code."}
            )

    login(request, user)
    # Session key rotation on login (prevent session fixation)
    request.session.cycle_key()

    log_audit_event("LOGIN_SUCCESS", request=request, actor=user, target_user=user)
    return user


def invalidate_user_sessions(
    user: User, current_session_key: str | None = None
) -> None:
    """Invalidate all sessions for the given user, optionally keeping the current one."""
    for session in Session.objects.all():
        try:
            data = session.get_decoded()
            if str(data.get("_auth_user_id")) == str(user.id):
                if current_session_key and session.session_key == current_session_key:
                    continue
                session.delete()
        except Exception as exc:
            logger.debug(
                "Failed decoding or deleting session %s: %s",
                getattr(session, "session_key", None),
                exc,
            )


def request_password_reset(email: str, request=None) -> None:
    """Request password reset link. Anti-enumeration: identical response always."""
    user = User.objects.filter(email__iexact=email).first()
    if user and user.is_active:
        raw_token = PasswordResetToken.create_for_user(user)
        reset_url = (
            f"{settings.CORS_ALLOWED_ORIGINS[0]}/reset-password?token={raw_token}"
        )
        subject = "Reset your Cyber Eco password"
        message = (
            f"You requested a password reset for your Cyber Eco account.\n\n"
            f"Click here to choose a new password:\n"
            f"{reset_url}\n\n"
            f"This link expires in 1 hour. If you did not request this, please ignore this email."
        )
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=True,
        )
        log_audit_event(
            "PASSWORD_RESET_REQUESTED", request=request, actor=user, target_user=user
        )
    else:
        check_password("dummy", DUMMY_ARGON2_HASH)


def confirm_password_reset(raw_token: str, new_password: str, request=None) -> User:
    """Confirm password reset with unexpired single-use token and invalidate all sessions."""
    token_hash = hash_token(raw_token)
    token_obj = (
        PasswordResetToken.objects.select_related("user")
        .filter(token_hash=token_hash)
        .first()
    )

    if not token_obj or not token_obj.is_valid():
        raise ValidationError({"token": "Invalid or expired password reset token."})

    token_obj.is_used = True
    token_obj.save(update_fields=["is_used"])

    user = token_obj.user
    user.set_password(new_password)
    user.save(update_fields=["password"])

    # Invalidate all active sessions for this user
    invalidate_user_sessions(user)

    log_audit_event(
        "PASSWORD_RESET_CONFIRMED", request=request, actor=user, target_user=user
    )
    return user


def change_password(
    user: User, current_password: str, new_password: str, request=None
) -> None:
    """Change user password, verifying current password and invalidating other sessions."""
    if not user.check_password(current_password):
        raise ValidationError({"current_password": "Incorrect current password."})

    user.set_password(new_password)
    user.save(update_fields=["password"])

    # Invalidate all OTHER sessions except the caller's current session
    current_key = (
        request.session.session_key if request and hasattr(request, "session") else None
    )
    invalidate_user_sessions(user, current_session_key=current_key)

    log_audit_event("PASSWORD_CHANGED", request=request, actor=user, target_user=user)


def require_reauthentication(
    user: User, password: str, totp_code: str | None = None
) -> bool:
    """Verify password and MFA (if enabled) for sensitive operations."""
    if not user.check_password(password):
        raise ValidationError({"password": "Password verification failed."})

    if user.mfa_enabled:
        if not totp_code:
            raise ValidationError(
                {"totp_code": "MFA code is required for this action."}
            )
        if not verify_user_totp(user, totp_code):
            raise ValidationError({"totp_code": "Invalid MFA code."})

    return True


def setup_totp_device(user: User) -> dict[str, Any]:
    """Generate TOTP secret (encrypted at rest), QR code, and recovery codes."""
    raw_key_bytes = secrets.token_bytes(20)
    raw_b32_secret = base64.b32encode(raw_key_bytes).decode("utf-8").replace("=", "")

    device, _ = UserTOTPDevice.objects.get_or_create(user=user)
    device.set_secret(raw_b32_secret)
    device.is_confirmed = False
    device.save()

    recovery_codes = MFARecoveryCode.generate_codes_for_user(user, count=8)

    # Format otpauth URL
    issuer = "Cyber Eco"
    label = urllib.parse.quote(f"{issuer}:{user.email}")
    otpauth_url = (
        f"otpauth://totp/{label}?"
        f"secret={raw_b32_secret}&"
        f"issuer={urllib.parse.quote(issuer)}&"
        f"algorithm=SHA1&digits=6&period=30"
    )

    # Generate QR Code as base64 image data URI
    qr = qrcode.QRCode(
        version=1,
        box_size=6,
        border=2,
    )
    qr.add_data(otpauth_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer)
    qr_data_uri = (
        f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode('utf-8')}"
    )

    return {
        "secret": raw_b32_secret,
        "otpauth_url": otpauth_url,
        "qr_code": qr_data_uri,
        "recovery_codes": recovery_codes,
    }


def verify_user_totp(user: User, code_or_recovery: str) -> bool:
    """Verify either a 6-digit TOTP code or a single-use recovery code."""
    clean_code = code_or_recovery.strip().replace(" ", "").upper()

    # 1. Try TOTP code if device exists
    device = UserTOTPDevice.objects.filter(user=user).first()
    if device and len(clean_code) == 6 and clean_code.isdigit():
        try:
            b32_secret = device.get_secret()
            # Pad base32 string to multiple of 8 if needed
            padded = b32_secret + "=" * ((8 - len(b32_secret) % 8) % 8)
            key_bytes = base64.b32decode(padded, casefold=True)
            totp = TOTP(key=key_bytes, step=30, digits=6)
            if totp.verify(int(clean_code), tolerance=1):
                if not device.is_confirmed:
                    device.is_confirmed = True
                    device.save(update_fields=["is_confirmed"])
                return True
        except Exception as exc:
            logger.debug("Failed verifying TOTP code: %s", exc)

    # 2. Try single-use recovery code
    code_h = hash_token(clean_code)
    rec = MFARecoveryCode.objects.filter(
        user=user, code_hash=code_h, is_used=False
    ).first()
    if rec:
        rec.is_used = True
        rec.used_at = timezone.now()
        rec.save(update_fields=["is_used", "used_at"])
        return True

    return False


def confirm_totp_setup(user: User, code: str, request=None) -> bool:
    """Confirm and enable TOTP MFA for user."""
    if not verify_user_totp(user, code):
        raise ValidationError({"code": "Invalid verification code."})

    user.mfa_enabled = True
    user.save(update_fields=["mfa_enabled"])

    log_audit_event("MFA_SETUP", request=request, actor=user, target_user=user)
    return True


def disable_totp_mfa(user: User, password: str, totp_code: str, request=None) -> None:
    """Disable TOTP MFA with mandatory re-authentication."""
    require_reauthentication(user, password, totp_code)

    user.mfa_enabled = False
    user.save(update_fields=["mfa_enabled"])

    UserTOTPDevice.objects.filter(user=user).delete()
    MFARecoveryCode.objects.filter(user=user).delete()

    log_audit_event("MFA_DISABLED", request=request, actor=user, target_user=user)


def regenerate_recovery_codes(
    user: User, password: str, totp_code: str, request=None
) -> list[str]:
    """Regenerate single-use recovery codes with mandatory re-authentication."""
    require_reauthentication(user, password, totp_code)

    codes = MFARecoveryCode.generate_codes_for_user(user, count=8)
    log_audit_event(
        "RECOVERY_CODES_REGENERATED", request=request, actor=user, target_user=user
    )
    return codes

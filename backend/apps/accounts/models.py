"""Custom User model, security tokens, MFA devices, and HunterProfile."""

import hashlib
import secrets
import uuid
from datetime import timedelta

from cryptography.fernet import Fernet
from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from .managers import UserManager


class UserRole(models.TextChoices):
    """User roles for Cyber Eco platform."""

    HUNTER = "hunter", "Security Researcher"
    COMPANY_ADMIN = "company_admin", "Company Administrator"
    COMPANY_TRIAGER = "company_triager", "Company Triager"
    COMPANY_VIEWER = "company_viewer", "Company Viewer"
    PLATFORM_ADMIN = "platform_admin", "Platform Administrator"


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with UUID PK, email login, and strict RBAC."""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    email = models.EmailField(
        unique=True,
        max_length=255,
        verbose_name="email address",
    )
    role = models.CharField(
        max_length=32,
        choices=UserRole.choices,
        default=UserRole.HUNTER,
        db_index=True,
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Designates whether the user's email has been verified.",
    )
    mfa_enabled = models.BooleanField(
        default=False,
        help_text="Designates whether the user has active TOTP MFA.",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_hunter(self) -> bool:
        return self.role == UserRole.HUNTER

    @property
    def is_company_admin(self) -> bool:
        return self.role == UserRole.COMPANY_ADMIN

    @property
    def is_company_user(self) -> bool:
        return self.role in {
            UserRole.COMPANY_ADMIN,
            UserRole.COMPANY_TRIAGER,
            UserRole.COMPANY_VIEWER,
        }

    @property
    def is_platform_admin(self) -> bool:
        return self.role == UserRole.PLATFORM_ADMIN

    @property
    def requires_mfa(self) -> bool:
        """Company roles and platform_admin require mandatory MFA."""
        return self.is_company_user or self.is_platform_admin


def hash_token(raw_token: str) -> str:
    """Generate SHA-256 hash of a raw token for secure storage at rest."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class EmailVerificationToken(models.Model):
    """Expiring, single-use email verification token stored as hash only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="verification_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_email_verification_token"

    @classmethod
    def create_for_user(cls, user: User, hours_valid: int = 24) -> str:
        """Create a token and return the raw secret string (hash is stored)."""
        # Invalidate previous unused tokens for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        raw_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=hours_valid)
        cls.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
        return raw_token

    def is_valid(self) -> bool:
        """Check if token is unexpired and unused."""
        return not self.is_used and timezone.now() <= self.expires_at


class PasswordResetToken(models.Model):
    """Expiring, single-use password reset token stored as hash only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="password_reset_tokens"
    )
    token_hash = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_password_reset_token"

    @classmethod
    def create_for_user(cls, user: User, hours_valid: int = 1) -> str:
        """Create a token and return the raw secret string (hash is stored)."""
        # Invalidate previous unused tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        raw_token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=hours_valid)
        cls.objects.create(
            user=user,
            token_hash=hash_token(raw_token),
            expires_at=expires_at,
        )
        return raw_token

    def is_valid(self) -> bool:
        return not self.is_used and timezone.now() <= self.expires_at


class UserTOTPDevice(models.Model):
    """TOTP secret stored encrypted at rest using AES-GCM/Fernet."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="totp_device"
    )
    encrypted_secret = models.BinaryField()
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_totp_device"

    @staticmethod
    def _get_fernet() -> Fernet:
        key = getattr(settings, "MFA_ENCRYPTION_KEY", None)
        if not key:
            raise ValueError("MFA_ENCRYPTION_KEY is required in settings")
        if isinstance(key, str):
            key = key.encode("utf-8")
        return Fernet(key)

    def set_secret(self, raw_secret: str) -> None:
        fernet = self._get_fernet()
        self.encrypted_secret = fernet.encrypt(raw_secret.encode("utf-8"))

    def get_secret(self) -> str:
        fernet = self._get_fernet()
        return fernet.decrypt(bytes(self.encrypted_secret)).decode("utf-8")


class MFARecoveryCode(models.Model):
    """Single-use recovery codes stored as hashes only."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="recovery_codes"
    )
    code_hash = models.CharField(max_length=64, db_index=True)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "accounts_mfa_recovery_code"

    @classmethod
    def generate_codes_for_user(cls, user: User, count: int = 8) -> list[str]:
        """Generate new batch of recovery codes, deleting any existing ones."""
        cls.objects.filter(user=user).delete()
        raw_codes = []
        for _ in range(count):
            raw = f"{secrets.token_hex(4)}-{secrets.token_hex(4)}".upper()
            raw_codes.append(raw)
            cls.objects.create(
                user=user,
                code_hash=hash_token(raw),
            )
        return raw_codes


class HunterProfile(models.Model):
    """Profile for security researchers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="hunter_profile"
    )
    username = models.CharField(
        max_length=30,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z0-9_]{3,30}$",
                message="Username must be 3-30 characters containing only letters, numbers, and underscores.",
            )
        ],
        db_index=True,
    )
    display_name = models.CharField(max_length=64, blank=True)
    bio = models.TextField(blank=True, max_length=1000)
    country = models.CharField(
        max_length=2, blank=True, help_text="ISO 3166-1 alpha-2 country code"
    )
    is_public = models.BooleanField(
        default=True, help_text="Whether profile is visible to public visitors"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "accounts_hunter_profile"

    def __str__(self):
        return f"@{self.username} ({self.display_name or self.user.email})"

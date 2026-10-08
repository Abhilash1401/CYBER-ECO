"""Serializers for authentication, MFA, and profile management."""

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import HunterProfile, User, UserRole


class RegisterSerializer(serializers.Serializer):
    """User registration serializer.

    Enforces that public users may only self-assign 'hunter' or 'company_admin'.
    Privileged roles (triager, viewer, platform_admin) are strictly forbidden.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    role = serializers.ChoiceField(
        choices=[UserRole.HUNTER, UserRole.COMPANY_ADMIN],
        default=UserRole.HUNTER,
    )

    def validate_password(self, value):
        validate_password(value)
        return value


class LoginSerializer(serializers.Serializer):
    """Credentials login serializer (supports optional MFA code or recovery code)."""

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, allow_blank=True, default="")
    recovery_code = serializers.CharField(required=False, allow_blank=True, default="")


class VerifyEmailSerializer(serializers.Serializer):
    """Email verification token serializer."""

    token = serializers.CharField()


class ResendVerificationSerializer(serializers.Serializer):
    """Resend email verification serializer."""

    email = serializers.EmailField()


class PasswordResetRequestSerializer(serializers.Serializer):
    """Request password reset link serializer."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Confirm password reset serializer."""

    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class ChangePasswordSerializer(serializers.Serializer):
    """Change password serializer (requires current password)."""

    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value


class ChangeEmailSerializer(serializers.Serializer):
    """Change email serializer (requires password + MFA re-authentication)."""

    new_email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, allow_blank=True)


class ConfirmMFASetupSerializer(serializers.Serializer):
    """Confirm TOTP MFA setup serializer."""

    code = serializers.CharField(min_length=6, max_length=6)


class VerifyMFASerializer(serializers.Serializer):
    """Verify TOTP code or recovery code."""

    code = serializers.CharField(min_length=6, max_length=32)


class ReauthActionSerializer(serializers.Serializer):
    """Serializer for sensitive actions requiring re-authentication."""

    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, allow_blank=True)


class UserSerializer(serializers.ModelSerializer):
    """Current authenticated user details serializer (role is strictly read-only)."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "role",
            "is_verified",
            "mfa_enabled",
            "date_joined",
        )
        read_only_fields = (
            "id",
            "email",
            "role",
            "is_verified",
            "mfa_enabled",
            "date_joined",
        )


class HunterProfileSerializer(serializers.ModelSerializer):
    """Private HunterProfile serializer for researcher settings."""

    class Meta:
        model = HunterProfile
        fields = (
            "id",
            "username",
            "display_name",
            "bio",
            "country",
            "is_public",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class HunterPublicProfileSerializer(serializers.ModelSerializer):
    """Public HunterProfile serializer exposing only safe public fields."""

    class Meta:
        model = HunterProfile
        fields = (
            "username",
            "display_name",
            "bio",
            "country",
            "created_at",
        )
        read_only_fields = (
            "username",
            "display_name",
            "bio",
            "country",
            "created_at",
        )

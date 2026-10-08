"""Views for authentication, MFA, and profile management."""

from django.contrib.auth import logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsAuthenticatedAndVerified
from apps.common.throttles import (
    EmailVerificationResendThrottle,
    LoginRateThrottle,
    MFAVerifyThrottle,
    PasswordResetThrottle,
    RegisterRateThrottle,
)

from .models import HunterProfile, User
from .serializers import (
    ChangeEmailSerializer,
    ChangePasswordSerializer,
    ConfirmMFASetupSerializer,
    HunterProfileSerializer,
    HunterPublicProfileSerializer,
    LoginSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    ReauthActionSerializer,
    RegisterSerializer,
    UserSerializer,
    VerifyEmailSerializer,
)
from .services import (
    authenticate_and_login_user,
    change_password,
    confirm_password_reset,
    confirm_totp_setup,
    disable_totp_mfa,
    regenerate_recovery_codes,
    require_reauthentication,
    resend_verification_email,
    setup_totp_device,
    verify_email_token,
)


class CSRFTokenView(APIView):
    """Ensure CSRF cookie is set for client application."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        csrf_token = get_token(request)
        return Response({"csrfToken": csrf_token})


class RegisterView(APIView):
    """User registration endpoint. Anti-enumeration: returns identical message."""

    permission_classes = [AllowAny]
    throttle_classes = [RegisterRateThrottle]

    @extend_schema(request=RegisterSerializer, responses={201: dict})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import register_user

        register_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            role=serializer.validated_data["role"],
            request=request,
        )

        return Response(
            {
                "detail": "Registration received. If this email is eligible, a verification link has been sent."
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    """Verify email address with single-use token."""

    permission_classes = [AllowAny]

    @extend_schema(request=VerifyEmailSerializer, responses={200: dict})
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        verify_email_token(serializer.validated_data["token"], request=request)
        return Response(
            {"detail": "Email address successfully verified. You may now log in."}
        )


class ResendVerificationView(APIView):
    """Resend email verification token. Anti-enumeration: identical response always."""

    permission_classes = [AllowAny]
    throttle_classes = [EmailVerificationResendThrottle]

    @extend_schema(request=RegisterSerializer, responses={200: dict})
    def post(self, request):
        email = request.data.get("email", "")
        if email:
            resend_verification_email(email, request=request)
        return Response(
            {
                "detail": "If the account exists and is unverified, a new verification link has been sent."
            }
        )


class LoginView(APIView):
    """Session login with key rotation and verification checks."""

    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    @extend_schema(request=LoginSerializer, responses={200: UserSerializer})
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate_and_login_user(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            totp_code=serializer.validated_data.get("totp_code", ""),
            recovery_code=serializer.validated_data.get("recovery_code", ""),
        )

        user_data = UserSerializer(user).data
        return Response(
            {
                "user": user_data,
                "mfa_required": user.requires_mfa and not user.mfa_enabled,
            }
        )


class LogoutView(APIView):
    """Session logout endpoint."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"detail": "Successfully logged out."})


class CurrentUserView(APIView):
    """Get current authenticated user info."""

    permission_classes = [IsAuthenticated]
    mfa_exempt = True  # Allows user to check own profile status during MFA setup

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class PasswordResetRequestView(APIView):
    """Request password reset link. Anti-enumeration: identical response always."""

    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetThrottle]

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .services import request_password_reset

        request_password_reset(serializer.validated_data["email"], request=request)

        return Response(
            {
                "detail": "If an account matches that email, a password reset link has been sent."
            }
        )


class PasswordResetConfirmView(APIView):
    """Confirm password reset with single-use token and invalidate existing sessions."""

    permission_classes = [AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: dict})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirm_password_reset(
            raw_token=serializer.validated_data["token"],
            new_password=serializer.validated_data["new_password"],
            request=request,
        )
        return Response(
            {
                "detail": "Password successfully reset. Please log in with your new password."
            }
        )


class ChangePasswordView(APIView):
    """Change password (invalidates all other active sessions)."""

    permission_classes = [IsAuthenticatedAndVerified]

    @extend_schema(request=ChangePasswordSerializer, responses={200: dict})
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        change_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
            request=request,
        )
        return Response(
            {
                "detail": "Password updated successfully. Other sessions have been terminated."
            }
        )


class ChangeEmailView(APIView):
    """Change email address (requires password + MFA re-authentication)."""

    permission_classes = [IsAuthenticatedAndVerified]

    @extend_schema(request=ChangeEmailSerializer, responses={200: dict})
    def post(self, request):
        serializer = ChangeEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        require_reauthentication(
            user=request.user,
            password=serializer.validated_data["password"],
            totp_code=serializer.validated_data.get("totp_code"),
        )

        new_email = serializer.validated_data["new_email"]
        if (
            User.objects.filter(email__iexact=new_email)
            .exclude(pk=request.user.pk)
            .exists()
        ):
            return Response(
                {"detail": "Email already in use."}, status=status.HTTP_400_BAD_REQUEST
            )

        request.user.email = new_email
        request.user.is_verified = False
        request.user.save(update_fields=["email", "is_verified"])

        from .models import EmailVerificationToken
        from .services import send_verification_email

        raw_token = EmailVerificationToken.create_for_user(request.user)
        send_verification_email(request.user, raw_token)

        logout(request)
        return Response(
            {
                "detail": "Email changed. Please verify your new email address before logging in."
            }
        )


class MFASetupView(APIView):
    """Generate TOTP secret, QR code data URI, and 8 single-use recovery codes."""

    permission_classes = [IsAuthenticated]
    mfa_exempt = True  # Must be reachable so users can setup mandatory MFA

    def post(self, request):
        data = setup_totp_device(request.user)
        return Response(data)


class MFAConfirmSetupView(APIView):
    """Verify code and activate TOTP MFA on account."""

    permission_classes = [IsAuthenticated]
    throttle_classes = [MFAVerifyThrottle]
    mfa_exempt = True

    @extend_schema(request=ConfirmMFASetupSerializer, responses={200: dict})
    def post(self, request):
        serializer = ConfirmMFASetupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirm_totp_setup(
            request.user, serializer.validated_data["code"], request=request
        )
        return Response({"detail": "Two-factor authentication has been enabled."})


class MFADisableView(APIView):
    """Disable TOTP MFA (requires password and MFA re-authentication)."""

    permission_classes = [IsAuthenticatedAndVerified]

    @extend_schema(request=ReauthActionSerializer, responses={200: dict})
    def post(self, request):
        if request.user.requires_mfa:
            return Response(
                {"detail": "MFA is mandatory for your role and cannot be disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReauthActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        disable_totp_mfa(
            user=request.user,
            password=serializer.validated_data["password"],
            totp_code=serializer.validated_data.get("totp_code", ""),
            request=request,
        )
        return Response({"detail": "Two-factor authentication has been disabled."})


class MFARegenerateRecoveryCodesView(APIView):
    """Regenerate single-use recovery codes (requires re-authentication)."""

    permission_classes = [IsAuthenticatedAndVerified]

    @extend_schema(request=ReauthActionSerializer, responses={200: dict})
    def post(self, request):
        serializer = ReauthActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        codes = regenerate_recovery_codes(
            user=request.user,
            password=serializer.validated_data["password"],
            totp_code=serializer.validated_data.get("totp_code", ""),
            request=request,
        )
        return Response({"recovery_codes": codes})


class HunterProfileMeView(generics.RetrieveUpdateAPIView):
    """Get and update current user's researcher profile."""

    serializer_class = HunterProfileSerializer
    permission_classes = [IsAuthenticatedAndVerified]

    def get_object(self):
        profile, _ = HunterProfile.objects.get_or_create(
            user=self.request.user,
            defaults={"username": f"hunter_{self.request.user.id.hex[:8]}"},
        )
        return profile


class HunterPublicProfileView(generics.RetrieveAPIView):
    """Public profile view (exposes only safe public fields; returns 404 if private)."""

    serializer_class = HunterPublicProfileSerializer
    permission_classes = [AllowAny]
    lookup_field = "username"

    def get_queryset(self):
        return HunterProfile.objects.filter(is_public=True)

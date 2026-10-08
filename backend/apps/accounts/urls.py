"""URLs for accounts app (auth, MFA, hunter profiles)."""

from django.urls import path

from .views import (
    ChangeEmailView,
    ChangePasswordView,
    CSRFTokenView,
    CurrentUserView,
    HunterProfileMeView,
    HunterPublicProfileView,
    LoginView,
    LogoutView,
    MFAConfirmSetupView,
    MFADisableView,
    MFARegenerateRecoveryCodesView,
    MFASetupView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
    ResendVerificationView,
    VerifyEmailView,
)

auth_urlpatterns = [
    path("csrf/", CSRFTokenView.as_view(), name="auth-csrf"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("verify-email/", VerifyEmailView.as_view(), name="auth-verify-email"),
    path(
        "resend-verification/",
        ResendVerificationView.as_view(),
        name="auth-resend-verification",
    ),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
    path(
        "password/reset/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset-request",
    ),
    path(
        "password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    path("email/change/", ChangeEmailView.as_view(), name="auth-email-change"),
    # MFA endpoints
    path("mfa/setup/", MFASetupView.as_view(), name="auth-mfa-setup"),
    path("mfa/confirm/", MFAConfirmSetupView.as_view(), name="auth-mfa-confirm"),
    path("mfa/disable/", MFADisableView.as_view(), name="auth-mfa-disable"),
    path(
        "mfa/recovery-codes/",
        MFARegenerateRecoveryCodesView.as_view(),
        name="auth-mfa-recovery-codes",
    ),
]

profile_urlpatterns = [
    path("me/", HunterProfileMeView.as_view(), name="profile-me"),
    path("<str:username>/", HunterPublicProfileView.as_view(), name="profile-public"),
]

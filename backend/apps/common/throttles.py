"""Custom throttle classes for rate limiting security-sensitive actions."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginRateThrottle(AnonRateThrottle):
    """Strict throttle for login attempts to prevent brute force."""

    rate = "5/minute"


class RegisterRateThrottle(AnonRateThrottle):
    """Throttle for registration attempts."""

    rate = "10/hour"


class PasswordResetThrottle(AnonRateThrottle):
    """Throttle for password reset requests to mitigate spam/abuse."""

    rate = "5/hour"


class EmailVerificationResendThrottle(AnonRateThrottle):
    """Throttle for resending verification emails."""

    rate = "5/hour"


class MFAVerifyThrottle(UserRateThrottle):
    """Throttle for MFA verification attempts to prevent brute-forcing codes."""

    rate = "10/minute"


class ReportSubmissionThrottle(UserRateThrottle):
    """Throttle for report submissions."""

    rate = "10/hour"


class UploadThrottle(UserRateThrottle):
    """Throttle for file uploads."""

    rate = "20/hour"


class CommentThrottle(UserRateThrottle):
    """Throttle for comment submissions."""

    rate = "30/hour"

"""Audit logging service functions.

Never logs passwords, tokens, or MFA codes.
Extracts client IP safely without blindly trusting headers.
"""

from typing import Any

from django.conf import settings

from .models import AuditLog

# Sensitive keys that must NEVER appear in audit metadata
SENSITIVE_METADATA_KEYS = {
    "password",
    "password1",
    "password2",
    "old_password",
    "new_password",
    "token",
    "code",
    "otp",
    "totp_code",
    "recovery_code",
    "recovery_codes",
    "secret",
    "key",
}


def get_client_ip(request) -> str | None:
    """Extract client IP address safely.

    Only trusts X-Forwarded-For if USE_X_FORWARDED_FOR is True and behind trusted proxy.
    Otherwise defaults to request.META['REMOTE_ADDR'].
    """
    if not request:
        return None

    use_forwarded = getattr(settings, "USE_X_FORWARDED_FOR", False)
    if use_forwarded:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            # First IP in comma-separated list
            return forwarded.split(",")[0].strip()

    return request.META.get("REMOTE_ADDR")


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Strip any sensitive keys from audit metadata."""
    if not metadata:
        return {}
    sanitized = {}
    for k, v in metadata.items():
        key_lower = k.lower()
        if key_lower in SENSITIVE_METADATA_KEYS or any(
            s in key_lower
            for s in (
                "password",
                "secret",
                "token",
                "recovery_code",
                "totp",
                "otp",
                "auth_key",
            )
        ):
            continue
        sanitized[k] = v
    return sanitized


def log_audit_event(
    action: str,
    request=None,
    actor=None,
    target_user=None,
    target=None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Create an append-only audit log entry."""
    ip_address = get_client_ip(request) if request else None
    user_agent = ""
    if request:
        user_agent = request.META.get("HTTP_USER_AGENT", "")[:512]
        if not actor and request.user and request.user.is_authenticated:
            actor = request.user

    clean_metadata = sanitize_metadata(metadata)
    if target is not None:
        clean_metadata["target"] = str(getattr(target, "id", target))

    return AuditLog.objects.create(
        action=action,
        actor=actor,
        target_user=target_user,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=clean_metadata,
    )

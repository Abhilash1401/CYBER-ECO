"""Centralized 3-tier permission layer for Cyber Eco.

Rules:
1. Deny by default.
2. Every request checks Role (RBAC) + Object relationship (tenant isolation) + Visibility.
3. MFA is mandatory for company roles and platform_admin: if mfa_enabled is False,
   they can ONLY access MFA setup/verify endpoints.
4. Prevent IDOR: use scoped querysets; return 404 for objects the user cannot see.
"""

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied


class DenyByDefault(permissions.BasePermission):
    """Deny by default base permission."""

    def has_permission(self, request, view):
        return False

    def has_object_permission(self, request, view, obj):
        return False


class IsAuthenticatedAndVerified(permissions.BasePermission):
    """Allows access only to authenticated users with verified email addresses.

    Also enforces mandatory MFA check for company roles and platform_admin.
    """

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        if not request.user.is_verified:
            raise PermissionDenied(
                "Email verification required before accessing this endpoint."
            )

        # Check mandatory MFA enforcement
        if (
            getattr(request.user, "requires_mfa", False)
            and not request.user.mfa_enabled
        ):
            # Exempt only MFA endpoints from the mandatory MFA block
            exempt_views = getattr(view, "mfa_exempt", False)
            if not exempt_views:
                raise PermissionDenied(
                    "MFA setup is mandatory for your role. Please configure TOTP MFA to continue."
                )

        return True


class IsHunter(IsAuthenticatedAndVerified):
    """Allows access only to Security Researchers ('hunter')."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_hunter


class IsCompanyAdmin(IsAuthenticatedAndVerified):
    """Allows access only to Company Administrators."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_company_admin


class IsCompanyMember(IsAuthenticatedAndVerified):
    """Allows access to any company role (admin, triager, viewer)."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_company_user


class IsPlatformAdmin(IsAuthenticatedAndVerified):
    """Allows access only to Platform Administrators."""

    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.is_platform_admin


class IsSelf(IsAuthenticatedAndVerified):
    """Allows a user to only access their own user object or related profile."""

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, "user"):
            return obj.user == request.user
        return obj == request.user


class ScopedQuerySetMixin:
    """Enforces tenant isolation by scoping querysets to the requesting user/tenant.

    Returns 404 (not 403) when an object does not exist in the user's scoped queryset.
    """

    def get_scoped_queryset(self):
        """Override in views to return querysets strictly scoped to the tenant/user."""
        raise NotImplementedError(
            "Views using ScopedQuerySetMixin must implement get_scoped_queryset()"
        )

    def get_queryset(self):
        return self.get_scoped_queryset()

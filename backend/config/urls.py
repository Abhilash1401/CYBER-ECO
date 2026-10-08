"""Root URL configuration for Cyber Eco."""

from apps.accounts.urls import auth_urlpatterns, profile_urlpatterns
from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django_otp.admin import OTPAdminSite
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Enforce OTP MFA for Django Admin (replace default admin site)
admin.site.__class__ = OTPAdminSite


@api_view(["GET"])
@permission_classes([AllowAny])
def health_check(request):
    """Simple health check endpoint. Returns only status."""
    return Response({"status": "ok"})


admin_url_path = getattr(settings, "ADMIN_URL", "admin/")

urlpatterns = [
    # Redirect root to OpenAPI docs
    path(
        "",
        RedirectView.as_view(url="/api/v1/docs/", permanent=False),
        name="root-redirect",
    ),
    path(admin_url_path, admin.site.urls),
    # API v1
    path("api/v1/health/", health_check, name="health-check"),
    path("api/v1/auth/", include(auth_urlpatterns)),
    path("api/v1/profiles/", include(profile_urlpatterns)),
    path("api/v1/companies/", include("apps.companies.urls")),
    path("api/v1/programs/", include("apps.programs.urls")),
    path("api/v1/reports/", include("apps.reports.urls")),
    # OpenAPI docs
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

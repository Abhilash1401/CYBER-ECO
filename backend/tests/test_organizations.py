"""Tests for Organization management, platform admin review, and domains."""

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationStatus,
)
from django.core.management import CommandError, call_command
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestSeedCommandProdProtection:
    """Requirement 1: Test seed command fails under non-local / prod settings."""

    def test_seed_dev_users_fails_under_prod_settings(self, settings):
        settings.DEBUG = False
        settings.SETTINGS_MODULE = "config.settings.prod"
        with pytest.raises(
            CommandError,
            match="Security Guard: seed_dev_users can only be run in local",
        ):
            call_command("seed_dev_users")


@pytest.mark.django_db
class TestOrganizations:
    """Test organization lifecycle, creation, and platform admin reviews."""

    def test_company_admin_can_create_organization(self, db):
        user = User.objects.create_user(
            email="founder@company.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        res = client.post(
            "/api/v1/companies/",
            {
                "name": "Acme Corp",
                "website": "https://acme.com",
                "domains": ["acme.com", "api.acme.com"],
            },
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED
        assert res.data["name"] == "Acme Corp"
        assert res.data["status"] == OrganizationStatus.PENDING
        assert len(res.data["verified_domains"]) == 2

        # Check membership assigned
        membership = OrganizationMember.objects.get(user=user)
        assert membership.role == MemberRole.COMPANY_ADMIN

    def test_one_user_cannot_create_multiple_organizations(self, db):
        user = User.objects.create_user(
            email="boss@company.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=user)

        client.post(
            "/api/v1/companies/",
            {"name": "Org 1", "website": "https://org1.com"},
            format="json",
        )
        res2 = client.post(
            "/api/v1/companies/",
            {"name": "Org 2", "website": "https://org2.com"},
            format="json",
        )
        assert res2.status_code == status.HTTP_400_BAD_REQUEST
        assert "User already belongs to an organization" in str(res2.data)

    def test_company_admin_cannot_self_verify_organization(self, db):
        admin_user = User.objects.create_user(
            email="admin@acme.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(name="Acme", website="https://acme.com")
        OrganizationMember.objects.create(
            organization=org, user=admin_user, role=MemberRole.COMPANY_ADMIN
        )

        client = APIClient()
        client.force_authenticate(user=admin_user)

        res = client.post(
            f"/api/v1/companies/{org.id}/review/",
            {"status": "verified", "reason": "I verify myself"},
            format="json",
        )
        # Blocked: only platform_admin can access review endpoint
        assert res.status_code == status.HTTP_403_FORBIDDEN

    def test_platform_admin_can_verify_organization_with_audited_reason(self, db):
        platform_admin = User.objects.create_user(
            email="admin@cybereco.platform",
            password="SecurePassword123!",
            role=UserRole.PLATFORM_ADMIN,
            is_verified=True,
            mfa_enabled=True,
            is_staff=True,
        )
        org = Organization.objects.create(
            name="Stark Corp", website="https://stark.com"
        )

        client = APIClient()
        client.force_authenticate(user=platform_admin)

        # Missing reason must fail
        res_fail = client.post(
            f"/api/v1/companies/{org.id}/review/",
            {"status": "verified", "reason": "   "},
            format="json",
        )
        assert res_fail.status_code == status.HTTP_400_BAD_REQUEST

        # Successful verification
        res_ok = client.post(
            f"/api/v1/companies/{org.id}/review/",
            {
                "status": "verified",
                "reason": "Reviewed business registration and authorized",
            },
            format="json",
        )
        assert res_ok.status_code == status.HTTP_200_OK
        org.refresh_from_db()
        assert org.status == OrganizationStatus.VERIFIED
        assert (
            org.verification_reason == "Reviewed business registration and authorized"
        )
        assert org.verified_by == platform_admin

"""Tests for SSRF prevention, scope validation, and asset restrictions."""

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationStatus,
    OrganizationVerifiedDomain,
)
from apps.programs.models import AssetType, Program
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestProgramScopeSSRFProtection:

    @pytest.fixture
    def setup_company(self):
        user = User.objects.create_user(
            email="secops@target.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(
            name="Target Corp",
            website="https://target.com",
            status=OrganizationStatus.VERIFIED,
        )
        OrganizationMember.objects.create(
            organization=org,
            user=user,
            role=MemberRole.COMPANY_ADMIN,
        )
        OrganizationVerifiedDomain.objects.create(
            organization=org,
            domain="target.com",
            is_verified=True,
        )
        program = Program.objects.create(
            organization=org,
            title="Target Bug Bounty",
            slug="target-bounty",
            description="Testing scope",
        )
        return user, org, program

    def test_ssrf_rejects_loopback_and_metadata_ip_addresses(self, setup_company):
        user, _, program = setup_company
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Reject AWS metadata endpoint (169.254.169.254)
        res_meta = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.IP_CIDR,
                "asset_value": "169.254.169.254/32",
                "in_scope": True,
            },
            format="json",
        )
        assert res_meta.status_code == status.HTTP_400_BAD_REQUEST
        assert "forbidden private, loopback, or metadata" in str(res_meta.data)

        # 2. Reject Localhost loopback (127.0.0.1)
        res_loop = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.IP_CIDR,
                "asset_value": "127.0.0.1",
                "in_scope": True,
            },
            format="json",
        )
        assert res_loop.status_code == status.HTTP_400_BAD_REQUEST

        # 3. Reject RFC1918 Private range (10.0.0.0/8, 192.168.1.1)
        res_priv = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.IP_CIDR,
                "asset_value": "192.168.1.1/24",
                "in_scope": True,
            },
            format="json",
        )
        assert res_priv.status_code == status.HTTP_400_BAD_REQUEST

    def test_ssrf_rejects_invalid_url_schemes(self, setup_company):
        user, _, program = setup_company
        client = APIClient()
        client.force_authenticate(user=user)

        res_file = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.URL,
                "asset_value": "file:///etc/passwd",
                "in_scope": True,
            },
            format="json",
        )
        assert res_file.status_code == status.HTTP_400_BAD_REQUEST
        assert "http:// or https://" in str(res_file.data)

    def test_in_scope_domain_must_match_verified_domains(self, setup_company):
        user, _, program = setup_company
        client = APIClient()
        client.force_authenticate(user=user)

        # 1. Unverified domain must fail
        res_unverified = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.DOMAIN,
                "asset_value": "google.com",
                "in_scope": True,
            },
            format="json",
        )
        assert res_unverified.status_code == status.HTTP_400_BAD_REQUEST
        assert "verified domain list" in str(res_unverified.data)

        # 2. Verified domain and its subdomain must succeed
        res_sub = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.DOMAIN,
                "asset_value": "api.target.com",
                "in_scope": True,
            },
            format="json",
        )
        assert res_sub.status_code == status.HTTP_201_CREATED

        res_apex = client.post(
            f"/api/v1/programs/manage/{program.slug}/scopes/",
            {
                "asset_type": AssetType.DOMAIN,
                "asset_value": "target.com",
                "in_scope": True,
            },
            format="json",
        )
        assert res_apex.status_code == status.HTTP_201_CREATED

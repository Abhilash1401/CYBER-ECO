"""Tests for Multi-Tenant Isolation, IDOR protection, and Private Program Access."""

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationStatus,
)
from apps.programs.models import (
    AssetType,
    Program,
    ProgramInvite,
    ProgramScope,
    ProgramStatus,
    ProgramVisibility,
)
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestTenantIsolationAndIDOR:

    @pytest.fixture
    def setup_tenants(self):
        # Tenant 1: Alpha Corp
        alpha_admin = User.objects.create_user(
            email="admin@alpha.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        alpha_org = Organization.objects.create(
            name="Alpha Corp",
            website="https://alpha.com",
            status=OrganizationStatus.VERIFIED,
        )
        OrganizationMember.objects.create(
            organization=alpha_org, user=alpha_admin, role=MemberRole.COMPANY_ADMIN
        )
        alpha_program = Program.objects.create(
            organization=alpha_org,
            title="Alpha Bounty",
            slug="alpha-bounty",
            description="Alpha program details",
            status=ProgramStatus.ACTIVE,
            visibility=ProgramVisibility.PUBLIC,
        )
        ProgramScope.objects.create(
            program=alpha_program,
            asset_type=AssetType.DOMAIN,
            asset_value="alpha.com",
            in_scope=True,
            notes="Confidential internal triager notes - DO NOT LEAK",
        )

        # Tenant 2: Beta Corp
        beta_admin = User.objects.create_user(
            email="admin@beta.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        beta_org = Organization.objects.create(
            name="Beta Corp",
            website="https://beta.com",
            status=OrganizationStatus.VERIFIED,
        )
        beta_member = OrganizationMember.objects.create(
            organization=beta_org, user=beta_admin, role=MemberRole.COMPANY_ADMIN
        )
        beta_program = Program.objects.create(
            organization=beta_org,
            title="Beta Bounty",
            slug="beta-bounty",
            description="Beta program details",
            status=ProgramStatus.DRAFT,
            visibility=ProgramVisibility.PRIVATE,
        )

        # Hunter 1
        hunter = User.objects.create_user(
            email="researcher@bounty.org",
            password="SecurePassword123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )

        return (
            alpha_admin,
            alpha_org,
            alpha_program,
            beta_admin,
            beta_org,
            beta_member,
            beta_program,
            hunter,
        )

    def test_cross_tenant_access_returns_404_not_found(self, setup_tenants):
        alpha_admin, _, alpha_program, beta_admin, _, beta_member, beta_program, _ = (
            setup_tenants
        )
        client = APIClient()
        client.force_authenticate(user=alpha_admin)

        # Alpha admin attempts to view Beta's program manage view -> 404
        res_view = client.get(f"/api/v1/programs/manage/{beta_program.slug}/")
        assert res_view.status_code == status.HTTP_404_NOT_FOUND

        # Alpha admin attempts to modify Beta's program -> 404
        res_patch = client.patch(
            f"/api/v1/programs/manage/{beta_program.slug}/", {"title": "Hacked"}
        )
        assert res_patch.status_code == status.HTTP_404_NOT_FOUND

        # Alpha admin attempts to delete Beta's member -> 404
        res_del = client.delete(f"/api/v1/companies/me/members/{beta_member.id}/")
        assert res_del.status_code == status.HTTP_404_NOT_FOUND

    def test_hunter_cannot_view_draft_or_uninvited_private_programs(
        self, setup_tenants
    ):
        _, _, _, _, _, _, beta_program, hunter = setup_tenants
        client = APIClient()
        client.force_authenticate(user=hunter)

        # Beta program is DRAFT and PRIVATE -> Hunter gets 404
        res_public = client.get(f"/api/v1/programs/{beta_program.slug}/")
        assert res_public.status_code == status.HTTP_404_NOT_FOUND

        # Beta program appears in neither public list nor detail
        res_list = client.get("/api/v1/programs/")
        slugs = [p["slug"] for p in res_list.data["results"]]
        assert beta_program.slug not in slugs

        # Now activate beta program as private and invite hunter
        beta_program.status = ProgramStatus.ACTIVE
        beta_program.save()
        ProgramInvite.objects.create(program=beta_program, hunter=hunter)

        # Now hunter CAN see it
        res_invited = client.get(f"/api/v1/programs/{beta_program.slug}/")
        assert res_invited.status_code == status.HTTP_200_OK
        assert res_invited.data["title"] == beta_program.title

    def test_public_program_endpoint_does_not_leak_internal_notes(self, setup_tenants):
        _, _, alpha_program, _, _, _, _, hunter = setup_tenants
        client = APIClient()
        client.force_authenticate(user=hunter)

        res = client.get(f"/api/v1/programs/{alpha_program.slug}/")
        assert res.status_code == status.HTTP_200_OK

        scopes = res.data["scopes"]
        assert len(scopes) > 0
        for scope in scopes:
            # Internal notes must NEVER be serialized in public response
            assert "notes" not in scope
            assert "DO NOT LEAK" not in str(scope)

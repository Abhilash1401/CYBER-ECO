"""Tests for Phase 4: Tenant isolation and cross-hunter access controls."""

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
    ProgramScope,
    ProgramStatus,
    Severity,
)
from apps.reports.models import Report
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestReportsTenantIsolation:

    @pytest.fixture
    def setup_entities(self):
        # Hunter A
        hunter_a = User.objects.create_user(
            email="hunter_a@security.org",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )
        # Hunter B
        hunter_b = User.objects.create_user(
            email="hunter_b@security.org",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )

        # Company 1
        comp1_admin = User.objects.create_user(
            email="admin@comp1.com",
            password="Password123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org1 = Organization.objects.create(
            name="Company 1", status=OrganizationStatus.VERIFIED
        )
        OrganizationMember.objects.create(
            organization=org1, user=comp1_admin, role=MemberRole.COMPANY_ADMIN
        )
        prog1 = Program.objects.create(
            organization=org1,
            title="Prog 1",
            slug="prog-1",
            status=ProgramStatus.ACTIVE,
        )
        scope1 = ProgramScope.objects.create(
            program=prog1,
            asset_type=AssetType.DOMAIN,
            asset_value="comp1.com",
            in_scope=True,
        )

        # Company 2
        comp2_admin = User.objects.create_user(
            email="admin@comp2.com",
            password="Password123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org2 = Organization.objects.create(
            name="Company 2", status=OrganizationStatus.VERIFIED
        )
        OrganizationMember.objects.create(
            organization=org2, user=comp2_admin, role=MemberRole.COMPANY_ADMIN
        )
        prog2 = Program.objects.create(
            organization=org2,
            title="Prog 2",
            slug="prog-2",
            status=ProgramStatus.ACTIVE,
        )
        scope2 = ProgramScope.objects.create(
            program=prog2,
            asset_type=AssetType.DOMAIN,
            asset_value="comp2.com",
            in_scope=True,
        )

        # Report by Hunter A in Company 1
        report_a = Report.objects.create(
            program=prog1,
            hunter=hunter_a,
            target_asset=scope1,
            title="XSS in Comp 1",
            description="Steps to reproduce",
            steps_to_reproduce="Steps",
            impact="Impact",
            severity=Severity.HIGH,
        )

        return hunter_a, hunter_b, comp1_admin, comp2_admin, report_a

    def test_hunter_b_cannot_view_or_withdraw_hunter_a_report(self, setup_entities):
        _, hunter_b, _, _, report_a = setup_entities
        client = APIClient()
        client.force_authenticate(user=hunter_b)

        # Detail view must return 404 (not 403, preventing existence disclosure)
        res_get = client.get(f"/api/v1/reports/{report_a.id}/")
        assert res_get.status_code == status.HTTP_404_NOT_FOUND

        # Patch (withdraw) must return 404
        res_patch = client.patch(
            f"/api/v1/reports/{report_a.id}/", {"status": "withdrawn"}
        )
        assert res_patch.status_code == status.HTTP_404_NOT_FOUND

        # List must not contain report_a
        res_list = client.get("/api/v1/reports/")
        assert res_list.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in res_list.data]
        assert str(report_a.id) not in ids

    def test_company_2_cannot_access_company_1_report(self, setup_entities):
        _, _, _, comp2_admin, report_a = setup_entities
        client = APIClient()
        client.force_authenticate(user=comp2_admin)

        # Detail must return 404
        res_get = client.get(f"/api/v1/reports/manage/{report_a.id}/")
        assert res_get.status_code == status.HTTP_404_NOT_FOUND

        # Status transition must return 404
        res_post = client.post(
            f"/api/v1/reports/manage/{report_a.id}/", {"status": "triaged"}
        )
        assert res_post.status_code == status.HTTP_404_NOT_FOUND

        # Manage list must not show report_a
        res_list = client.get("/api/v1/reports/manage/list/")
        assert res_list.status_code == status.HTTP_200_OK
        ids = [r["id"] for r in res_list.data]
        assert str(report_a.id) not in ids

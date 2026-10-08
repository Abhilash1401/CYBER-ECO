"""Tests for Report Lifecycle, Scope validation, and State Machine."""

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
from apps.reports.models import ReportStatus
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestReportsScopeAndLifecycle:

    @pytest.fixture
    def setup_data(self):
        hunter = User.objects.create_user(
            email="hunter1@bounty.org",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )
        company_admin = User.objects.create_user(
            email="admin@cyber.com",
            password="Password123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(
            name="Cyber Inc", status=OrganizationStatus.VERIFIED
        )
        OrganizationMember.objects.create(
            organization=org, user=company_admin, role=MemberRole.COMPANY_ADMIN
        )

        prog = Program.objects.create(
            organization=org,
            title="Cyber Bounty",
            slug="cyber-bounty",
            status=ProgramStatus.ACTIVE,
        )
        in_scope = ProgramScope.objects.create(
            program=prog,
            asset_type=AssetType.DOMAIN,
            asset_value="cyber.com",
            in_scope=True,
        )
        out_scope = ProgramScope.objects.create(
            program=prog,
            asset_type=AssetType.DOMAIN,
            asset_value="blog.cyber.com",
            in_scope=False,
        )

        return hunter, company_admin, org, prog, in_scope, out_scope

    def test_out_of_scope_asset_submission_rejected(self, setup_data):
        hunter, _, _, prog, _, out_scope = setup_data
        client = APIClient()
        client.force_authenticate(user=hunter)

        res = client.post(
            "/api/v1/reports/",
            {
                "program_slug": prog.slug,
                "target_asset_id": str(out_scope.id),
                "title": "Bug on blog",
                "vulnerability_type": "xss",
                "description": "Details",
                "steps_to_reproduce": "Steps",
                "impact": "Impact",
                "severity": Severity.MEDIUM,
            },
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "in-scope asset" in str(res.data).lower()

    def test_inactive_program_submission_rejected(self, setup_data):
        hunter, _, _, prog, in_scope, _ = setup_data
        prog.status = ProgramStatus.PAUSED
        prog.save()

        client = APIClient()
        client.force_authenticate(user=hunter)

        res = client.post(
            "/api/v1/reports/",
            {
                "program_slug": prog.slug,
                "target_asset_id": str(in_scope.id),
                "title": "Bug",
                "vulnerability_type": "xss",
                "description": "Details",
                "steps_to_reproduce": "Steps",
                "impact": "Impact",
                "severity": Severity.MEDIUM,
            },
            format="json",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "active programs" in str(res.data).lower()

    def test_complete_report_state_machine_lifecycle(self, setup_data):
        hunter, company_admin, _, prog, in_scope, _ = setup_data
        client = APIClient()
        client.force_authenticate(user=hunter)

        # 1. Submit report -> NEW
        res_submit = client.post(
            "/api/v1/reports/",
            {
                "program_slug": prog.slug,
                "target_asset_id": str(in_scope.id),
                "title": "RCE in API",
                "vulnerability_type": "rce",
                "description": "PoC",
                "steps_to_reproduce": "Steps",
                "impact": "RCE",
                "severity": Severity.CRITICAL,
            },
            format="json",
        )
        assert res_submit.status_code == status.HTTP_201_CREATED
        report_id = res_submit.data["id"]

        # 2. Company triages: NEW -> TRIAGED
        client.force_authenticate(user=company_admin)
        res_triage = client.post(
            f"/api/v1/reports/manage/{report_id}/",
            {"status": ReportStatus.TRIAGED, "triaged_severity": Severity.CRITICAL},
            format="json",
        )
        assert res_triage.status_code == status.HTTP_200_OK

        # 3. Company transitions: TRIAGED -> ACCEPTED
        res_accept = client.post(
            f"/api/v1/reports/manage/{report_id}/",
            {"status": ReportStatus.ACCEPTED},
            format="json",
        )
        assert res_accept.status_code == status.HTTP_200_OK

        # 4. Company transitions: ACCEPTED -> FIXED
        res_fix = client.post(
            f"/api/v1/reports/manage/{report_id}/",
            {"status": ReportStatus.FIXED},
            format="json",
        )
        assert res_fix.status_code == status.HTTP_200_OK

        # 5. Company transitions: FIXED -> REWARDED
        res_rew = client.post(
            f"/api/v1/reports/manage/{report_id}/",
            {"status": ReportStatus.REWARDED},
            format="json",
        )
        assert res_rew.status_code == status.HTTP_200_OK

        # 6. Company transitions: REWARDED -> CLOSED
        res_close = client.post(
            f"/api/v1/reports/manage/{report_id}/",
            {"status": ReportStatus.CLOSED, "reason": "Bounty paid and patch deployed"},
            format="json",
        )
        assert res_close.status_code == status.HTTP_200_OK

        # 7. Invalid transition out of CLOSED must fail
        res_reopen = client.post(
            f"/api/v1/reports/manage/{report_id}/",
            {"status": ReportStatus.NEW},
            format="json",
        )
        assert res_reopen.status_code == status.HTTP_400_BAD_REQUEST

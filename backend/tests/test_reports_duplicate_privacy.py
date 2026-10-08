"""Tests for duplicate linking and privacy guarantees."""

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
from apps.reports.models import Report, ReportStatus
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestReportsDuplicatePrivacy:

    @pytest.fixture
    def setup_duplicate_reports(self):
        hunter_original = User.objects.create_user(
            email="original_finder@bounty.org",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )
        hunter_dupe = User.objects.create_user(
            email="second_finder@bounty.org",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )
        company_admin = User.objects.create_user(
            email="admin@app.com",
            password="Password123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )

        org = Organization.objects.create(
            name="App Corp", status=OrganizationStatus.VERIFIED
        )
        OrganizationMember.objects.create(
            organization=org, user=company_admin, role=MemberRole.COMPANY_ADMIN
        )

        prog = Program.objects.create(
            organization=org,
            title="App Bounty",
            slug="app-bounty",
            status=ProgramStatus.ACTIVE,
        )
        scope = ProgramScope.objects.create(
            program=prog,
            asset_type=AssetType.DOMAIN,
            asset_value="app.com",
            in_scope=True,
        )

        report_original = Report.objects.create(
            program=prog,
            hunter=hunter_original,
            target_asset=scope,
            title="Original Report: Secret SSRF",
            description="Detailed SSRF exploit",
            steps_to_reproduce="Steps",
            impact="Internal network pivoting",
            severity=Severity.HIGH,
            status=ReportStatus.ACCEPTED,
        )

        report_second = Report.objects.create(
            program=prog,
            hunter=hunter_dupe,
            target_asset=scope,
            title="Later Report: Same SSRF",
            description="Later duplicate submission",
            steps_to_reproduce="Steps",
            impact="SSRF",
            severity=Severity.HIGH,
            status=ReportStatus.TRIAGED,
        )

        return (
            hunter_original,
            hunter_dupe,
            company_admin,
            report_original,
            report_second,
        )

    def test_duplicate_linking_does_not_leak_original_hunter_info(
        self, setup_duplicate_reports
    ):
        _, hunter_dupe, company_admin, report_original, report_second = (
            setup_duplicate_reports
        )
        client = APIClient()

        # 1. Company marks second report as DUPLICATE of original
        client.force_authenticate(user=company_admin)
        res_mark = client.post(
            f"/api/v1/reports/manage/{report_second.id}/",
            {
                "status": ReportStatus.DUPLICATE,
                "duplicate_of_id": str(report_original.id),
                "reason": "Vulnerability was previously reported",
            },
            format="json",
        )
        assert res_mark.status_code == status.HTTP_200_OK

        # 2. Second hunter views their duplicate report
        client.force_authenticate(user=hunter_dupe)
        res_view = client.get(f"/api/v1/reports/{report_second.id}/")
        assert res_view.status_code == status.HTTP_200_OK

        # Verify status is duplicate
        assert res_view.data["status"] == ReportStatus.DUPLICATE

        # Verify ZERO info about original finder is present in hunter payload
        assert "original_finder" not in str(res_view.data)
        assert "Secret SSRF" not in str(res_view.data)
        assert str(report_original.id) not in str(res_view.data)
        assert "duplicate_of_id" not in res_view.data

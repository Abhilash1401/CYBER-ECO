"""Tests for strict dual-serializer separation preventing internal field and comment leakage."""

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
from apps.reports.models import CommentVisibility, Report, ReportComment
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestReportsSerializerSeparation:

    @pytest.fixture
    def setup_report_with_comments(self):
        hunter = User.objects.create_user(
            email="researcher@pentest.org",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )
        company_admin = User.objects.create_user(
            email="secops@target.com",
            password="Password123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(
            name="Target Corp", status=OrganizationStatus.VERIFIED
        )
        OrganizationMember.objects.create(
            organization=org, user=company_admin, role=MemberRole.COMPANY_ADMIN
        )

        prog = Program.objects.create(
            organization=org,
            title="Target Bounty",
            slug="target-bounty",
            status=ProgramStatus.ACTIVE,
        )
        scope = ProgramScope.objects.create(
            program=prog,
            asset_type=AssetType.DOMAIN,
            asset_value="target.com",
            in_scope=True,
        )

        report = Report.objects.create(
            program=prog,
            hunter=hunter,
            target_asset=scope,
            title="SQLi in Login",
            description="Exploit details",
            steps_to_reproduce="Steps",
            impact="Database takeover",
            severity=Severity.CRITICAL,
        )

        # 1 shared comment
        ReportComment.objects.create(
            report=report,
            author=hunter,
            content="Here is the PoC string",
            visibility=CommentVisibility.SHARED,
        )

        # 1 internal comment with confidential triager deliberations
        ReportComment.objects.create(
            report=report,
            author=company_admin,
            content="CONFIDENTIAL_TRIAGE_NOTE: Impact confirmed on production customer DB.",
            visibility=CommentVisibility.INTERNAL,
        )

        return hunter, company_admin, report

    def test_hunter_never_receives_internal_comments_or_fields(
        self, setup_report_with_comments
    ):
        hunter, _, report = setup_report_with_comments
        client = APIClient()
        client.force_authenticate(user=hunter)

        res = client.get(f"/api/v1/reports/{report.id}/")
        assert res.status_code == status.HTTP_200_OK

        # Hunter must only see shared comments
        comments = res.data["comments"]
        assert len(comments) == 1
        assert comments[0]["content"] == "Here is the PoC string"
        assert "CONFIDENTIAL_TRIAGE_NOTE" not in str(res.data)

        # Hunter must not receive internal fields
        assert "duplicate_of_id" not in res.data
        assert "closed_reason" not in res.data

    def test_company_receives_internal_comments_and_fields(
        self, setup_report_with_comments
    ):
        _, company_admin, report = setup_report_with_comments
        client = APIClient()
        client.force_authenticate(user=company_admin)

        res = client.get(f"/api/v1/reports/manage/{report.id}/")
        assert res.status_code == status.HTTP_200_OK

        comments = res.data["comments"]
        assert len(comments) == 2
        contents = [c["content"] for c in comments]
        assert (
            "CONFIDENTIAL_TRIAGE_NOTE: Impact confirmed on production customer DB."
            in contents
        )
        assert "duplicate_of_id" in res.data

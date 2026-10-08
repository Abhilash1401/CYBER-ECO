"""Tests for Program Lifecycle, Publishing Validation, and State Machine."""

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationStatus,
    OrganizationVerifiedDomain,
)
from apps.programs.models import (
    AssetType,
    Program,
    ProgramReward,
    ProgramScope,
    ProgramStatus,
    Severity,
)
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestProgramsLifecycle:

    @pytest.fixture
    def setup_data(self):
        platform_admin = User.objects.create_user(
            email="platform@cybereco.com",
            password="SecurePassword123!",
            role=UserRole.PLATFORM_ADMIN,
            is_verified=True,
            mfa_enabled=True,
            is_staff=True,
        )
        company_admin = User.objects.create_user(
            email="admin@cybersec.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(
            name="CyberSec Global",
            website="https://cybersec.com",
            status=OrganizationStatus.PENDING,
        )
        OrganizationMember.objects.create(
            organization=org,
            user=company_admin,
            role=MemberRole.COMPANY_ADMIN,
        )
        domain = OrganizationVerifiedDomain.objects.create(
            organization=org,
            domain="cybersec.com",
            is_verified=True,
        )
        return platform_admin, company_admin, org, domain

    def test_unverified_org_cannot_submit_program_for_review(self, setup_data):
        _, company_admin, org, _ = setup_data
        program = Program.objects.create(
            organization=org,
            title="CyberSec Bounty",
            slug="cybersec-bounty",
            description="Testing scope",
            rules_of_engagement="Be ethical",
        )
        ProgramScope.objects.create(
            program=program,
            asset_type=AssetType.DOMAIN,
            asset_value="cybersec.com",
            in_scope=True,
        )
        ProgramReward.objects.create(
            program=program,
            severity=Severity.HIGH,
            min_amount=500,
            max_amount=1000,
        )

        client = APIClient()
        client.force_authenticate(user=company_admin)

        # Org is PENDING -> cannot submit
        res = client.post(f"/api/v1/programs/manage/{program.slug}/submit-review/")
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "Organization must be verified" in str(res.data)

    def test_complete_program_review_and_platform_admin_approval_lifecycle(
        self, setup_data
    ):
        platform_admin, company_admin, org, _ = setup_data
        org.status = OrganizationStatus.VERIFIED
        org.save()

        program = Program.objects.create(
            organization=org,
            title="CyberSec Bounty",
            slug="cybersec-bounty",
            description="Testing scope",
            rules_of_engagement="Standard rules apply",
        )
        ProgramScope.objects.create(
            program=program,
            asset_type=AssetType.DOMAIN,
            asset_value="cybersec.com",
            in_scope=True,
        )
        ProgramReward.objects.create(
            program=program,
            severity=Severity.HIGH,
            min_amount=500,
            max_amount=1000,
        )

        client = APIClient()
        client.force_authenticate(user=company_admin)

        # 1. Company submits draft -> in_review
        res_submit = client.post(
            f"/api/v1/programs/manage/{program.slug}/submit-review/"
        )
        assert res_submit.status_code == status.HTTP_200_OK
        program.refresh_from_db()
        assert program.status == ProgramStatus.IN_REVIEW

        # 2. Company admin cannot move program directly to active (must be approved by platform admin)
        res_direct = client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": ProgramStatus.ACTIVE},
            format="json",
        )
        assert res_direct.status_code == status.HTTP_403_FORBIDDEN

        # 3. Platform admin approves program: in_review -> active
        client.force_authenticate(user=platform_admin)
        res_approve = client.post(
            f"/api/v1/programs/manage/{program.slug}/approve-active/",
            {"reason": "Program scope and reward verified"},
            format="json",
        )
        assert res_approve.status_code == status.HTTP_200_OK
        program.refresh_from_db()
        assert program.status == ProgramStatus.ACTIVE

        # 4. Company admin pauses active program
        client.force_authenticate(user=company_admin)
        res_pause = client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": ProgramStatus.PAUSED},
            format="json",
        )
        assert res_pause.status_code == status.HTTP_200_OK
        program.refresh_from_db()
        assert program.status == ProgramStatus.PAUSED

        # 5. Company admin closes program
        res_close = client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": ProgramStatus.CLOSED},
            format="json",
        )
        assert res_close.status_code == status.HTTP_200_OK
        program.refresh_from_db()
        assert program.status == ProgramStatus.CLOSED

        # 6. Cannot transition out of closed
        res_reopen = client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": ProgramStatus.ACTIVE},
            format="json",
        )
        assert res_reopen.status_code == status.HTTP_400_BAD_REQUEST

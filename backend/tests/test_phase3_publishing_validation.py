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
    ProgramReward,
    ProgramScope,
    Severity,
)
from rest_framework import status


@pytest.fixture
def org_admin(db):
    user = User.objects.create_user(
        email="admin@test.com",
        password="password",
        role=UserRole.COMPANY_ADMIN,
        is_verified=True,
        mfa_enabled=True,
    )
    return user


@pytest.fixture
def org(db, org_admin):
    org = Organization.objects.create(
        name="Test Org", status=OrganizationStatus.VERIFIED
    )
    OrganizationMember.objects.create(
        organization=org, user=org_admin, role=MemberRole.COMPANY_ADMIN
    )
    return org


@pytest.fixture
def program(db, org):
    return Program.objects.create(
        organization=org,
        title="Valid Program",
        slug="valid-program",
        rules_of_engagement="These are the rules.",
    )


@pytest.mark.django_db
class TestPhase3PublishingValidation:

    def test_submit_program_no_in_scope_asset(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)
        ProgramReward.objects.create(
            program=program, severity=Severity.CRITICAL, min_amount=100, max_amount=200
        )

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/submit-review/"
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
        assert (
            "asset" in str(response.data).lower()
            or "scope" in str(response.data).lower()
        )

    def test_submit_program_no_reward_tier(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)
        ProgramScope.objects.create(
            program=program, asset_type=AssetType.URL, asset_value="test.com"
        )

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/submit-review/"
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
        assert "reward" in str(response.data).lower()

    def test_submit_program_empty_rules(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)
        ProgramScope.objects.create(
            program=program, asset_type=AssetType.URL, asset_value="test.com"
        )
        ProgramReward.objects.create(
            program=program, severity=Severity.CRITICAL, min_amount=100, max_amount=200
        )

        program.rules_of_engagement = ""
        program.save()

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/submit-review/"
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
        assert (
            "rules of engagement" in str(response.data).lower()
            or "rules" in str(response.data).lower()
        )

    def test_submit_program_org_rejected(self, api_client, org_admin, org, program):
        api_client.force_authenticate(user=org_admin)
        ProgramScope.objects.create(
            program=program, asset_type=AssetType.URL, asset_value="test.com"
        )
        ProgramReward.objects.create(
            program=program, severity=Severity.CRITICAL, min_amount=100, max_amount=200
        )

        org.status = OrganizationStatus.REJECTED
        org.save()

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/submit-review/"
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_submit_program_org_suspended(self, api_client, org_admin, org, program):
        api_client.force_authenticate(user=org_admin)
        ProgramScope.objects.create(
            program=program, asset_type=AssetType.URL, asset_value="test.com"
        )
        ProgramReward.objects.create(
            program=program, severity=Severity.CRITICAL, min_amount=100, max_amount=200
        )

        org.status = OrganizationStatus.SUSPENDED
        org.save()

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/submit-review/"
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

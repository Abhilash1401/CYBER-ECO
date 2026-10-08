import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import MemberRole, Organization, OrganizationMember
from apps.programs.models import Program, ProgramStatus
from rest_framework import status


@pytest.fixture
def org_admin(db):
    user = User.objects.create_user(
        email="admin@test.com",
        password="password",
        role=UserRole.COMPANY_ADMIN,
        is_verified=True,
    )
    return user


@pytest.fixture
def org(db, org_admin):
    org = Organization.objects.create(name="Test Org")
    OrganizationMember.objects.create(
        organization=org, user=org_admin, role=MemberRole.COMPANY_ADMIN
    )
    return org


@pytest.fixture
def program(db, org):
    return Program.objects.create(
        organization=org, title="Program", slug="prog", status=ProgramStatus.DRAFT
    )


@pytest.mark.django_db
class TestPhase3StateTransitions:

    def test_draft_transitions(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)

        # draft -> paused
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "paused"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # draft -> closed
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "closed"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # draft -> active
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/approve-active/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "active"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_in_review_transitions(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)
        program.status = ProgramStatus.IN_REVIEW
        program.save()

        # in_review -> paused
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "paused"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # in_review -> closed
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "closed"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # in_review -> active (by org admin)
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/approve-active/"
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "active"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_active_transitions(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)
        program.status = ProgramStatus.ACTIVE
        program.save()

        # active -> draft
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "draft"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # active -> in_review
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "in_review"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

    def test_closed_transitions(self, api_client, org_admin, program):
        api_client.force_authenticate(user=org_admin)
        program.status = ProgramStatus.CLOSED
        program.save()

        # closed -> active
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "active"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # closed -> paused
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "paused"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # closed -> draft
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "draft"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

        # closed -> in_review
        response = api_client.post(
            f"/api/v1/programs/manage/{program.slug}/transition-status/",
            {"status": "in_review"},
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]

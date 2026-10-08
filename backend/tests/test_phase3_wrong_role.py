import uuid

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import MemberRole, Organization, OrganizationMember
from rest_framework import status


@pytest.fixture
def hunter_user(db):
    user = User.objects.create_user(
        email="hunter@test.com", password="password", is_verified=True
    )
    user.role = UserRole.HUNTER
    user.save()
    return user


@pytest.fixture
def company_admin(db):
    user = User.objects.create_user(
        email="admin@company.com", password="password", is_verified=True
    )
    user.role = UserRole.COMPANY_ADMIN
    user.save()
    return user


@pytest.fixture
def company_viewer(db):
    user = User.objects.create_user(
        email="viewer@company.com", password="password", is_verified=True
    )
    user.role = UserRole.COMPANY_VIEWER
    user.save()
    return user


@pytest.fixture
def company_triager(db):
    user = User.objects.create_user(
        email="triager@company.com", password="password", is_verified=True
    )
    user.role = UserRole.COMPANY_TRIAGER
    user.save()
    return user


@pytest.fixture
def test_org(db, company_admin, company_viewer, company_triager):
    org = Organization.objects.create(name="Test Org")
    OrganizationMember.objects.create(
        organization=org, user=company_admin, role=MemberRole.COMPANY_ADMIN
    )
    OrganizationMember.objects.create(
        organization=org, user=company_viewer, role=MemberRole.COMPANY_VIEWER
    )
    OrganizationMember.objects.create(
        organization=org, user=company_triager, role=MemberRole.COMPANY_TRIAGER
    )
    return org


@pytest.mark.django_db
class TestPhase3WrongRole:

    def test_hunter_cannot_access_company_endpoints(self, api_client, hunter_user):
        api_client.force_authenticate(user=hunter_user)
        fake_uuid = str(uuid.uuid4())

        # create org
        assert (
            api_client.post("/api/v1/companies/", {"name": "Test"}).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # manage programs
        assert (
            api_client.post(
                "/api/v1/programs/manage/list/",
                {"title": "Test", "visibility": "public"},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # members
        assert (
            api_client.get("/api/v1/companies/me/members/").status_code
            == status.HTTP_403_FORBIDDEN
        )

        # scopes, rewards, invites
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/scopes/", {"asset_type": "url"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/rewards/", {"severity": "critical"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/invites/", {"email": "test@test.com"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_company_viewer_cannot_access_admin_actions(
        self, api_client, test_org, company_viewer
    ):
        api_client.force_authenticate(user=company_viewer)
        fake_uuid = str(uuid.uuid4())

        # create program
        assert (
            api_client.post(
                "/api/v1/programs/manage/list/",
                {"title": "Test", "visibility": "public"},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # update program
        assert (
            api_client.patch(
                "/api/v1/programs/manage/test-slug/", {"title": "Update"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # add scope
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/scopes/", {"asset_type": "url"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # add reward
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/rewards/", {"severity": "critical"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # invite member
        assert (
            api_client.post(
                "/api/v1/companies/me/members/",
                {"email": "new@company.com", "role": "viewer"},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # delete member
        assert (
            api_client.delete(f"/api/v1/companies/me/members/{fake_uuid}/").status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_company_triager_cannot_access_admin_actions(
        self, api_client, test_org, company_triager
    ):
        api_client.force_authenticate(user=company_triager)
        fake_uuid = str(uuid.uuid4())

        # create program
        assert (
            api_client.post(
                "/api/v1/programs/manage/list/",
                {"title": "Test", "visibility": "public"},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # update program
        assert (
            api_client.patch(
                "/api/v1/programs/manage/test-slug/", {"title": "Update"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # add scope
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/scopes/", {"asset_type": "url"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # add reward
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/rewards/", {"severity": "critical"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # invite member
        assert (
            api_client.post(
                "/api/v1/companies/me/members/",
                {"email": "new@company.com", "role": "viewer"},
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # delete member
        assert (
            api_client.delete(f"/api/v1/companies/me/members/{fake_uuid}/").status_code
            == status.HTTP_403_FORBIDDEN
        )

    def test_company_admin_cannot_access_platform_admin_actions(
        self, api_client, test_org, company_admin
    ):
        api_client.force_authenticate(user=company_admin)

        # approve-active
        assert (
            api_client.post(
                "/api/v1/programs/manage/test-slug/approve-active/"
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

        # review org
        assert (
            api_client.post(
                f"/api/v1/companies/{test_org.id}/review/", {"action": "verify"}
            ).status_code
            == status.HTTP_403_FORBIDDEN
        )

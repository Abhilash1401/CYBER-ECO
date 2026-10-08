import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import MemberRole, Organization, OrganizationMember
from apps.programs.models import (
    AssetType,
    Program,
    ProgramInvite,
    ProgramReward,
    ProgramScope,
    Severity,
)
from rest_framework import status


@pytest.fixture
def alpha_admin(db):
    user = User.objects.create_user(
        email="alpha_admin@test.com",
        password="password",
        role=UserRole.COMPANY_ADMIN,
        is_verified=True,
        mfa_enabled=True,
    )
    return user


@pytest.fixture
def alpha_org(db, alpha_admin):
    org = Organization.objects.create(name="Alpha Org")
    OrganizationMember.objects.create(
        organization=org, user=alpha_admin, role=MemberRole.COMPANY_ADMIN
    )
    return org


@pytest.fixture
def beta_admin(db):
    user = User.objects.create_user(
        email="beta_admin@test.com",
        password="password",
        role=UserRole.COMPANY_ADMIN,
        is_verified=True,
        mfa_enabled=True,
    )
    return user


@pytest.fixture
def beta_org(db, beta_admin):
    org = Organization.objects.create(name="Beta Org")
    OrganizationMember.objects.create(
        organization=org, user=beta_admin, role=MemberRole.COMPANY_ADMIN
    )
    return org


@pytest.fixture
def beta_program(db, beta_org):
    return Program.objects.create(
        organization=beta_org, title="Beta Program", slug="beta-program"
    )


@pytest.fixture
def beta_scope(db, beta_program):
    return ProgramScope.objects.create(
        program=beta_program, asset_type=AssetType.URL, asset_value="beta.com"
    )


@pytest.fixture
def beta_reward(db, beta_program):
    return ProgramReward.objects.create(
        program=beta_program, severity=Severity.CRITICAL, min_amount=100, max_amount=200
    )


@pytest.fixture
def hunter_user(db):
    return User.objects.create_user(
        email="hunter2@test.com",
        password="password",
        role=UserRole.HUNTER,
        is_verified=True,
    )


@pytest.fixture
def beta_invite(db, beta_program, hunter_user):
    return ProgramInvite.objects.create(program=beta_program, hunter=hunter_user)


@pytest.mark.django_db
class TestPhase3CrossTenantFull:
    def test_alpha_admin_cross_tenant_access_to_beta(
        self,
        api_client,
        alpha_admin,
        alpha_org,
        beta_program,
        beta_scope,
        beta_reward,
        beta_invite,
    ):
        api_client.force_authenticate(user=alpha_admin)
        slug = beta_program.slug

        # Alpha admin reading Beta's scopes
        assert (
            api_client.get(f"/api/v1/programs/manage/{slug}/scopes/").status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin modifying Beta's scopes
        assert (
            api_client.post(
                f"/api/v1/programs/manage/{slug}/scopes/",
                {"asset_type": "url", "asset_value": "alpha.com"},
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin deleting Beta's scope
        assert (
            api_client.delete(
                f"/api/v1/programs/manage/{slug}/scopes/{beta_scope.id}/"
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin reading Beta's rewards
        assert (
            api_client.get(f"/api/v1/programs/manage/{slug}/rewards/").status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin modifying Beta's rewards
        assert (
            api_client.post(
                f"/api/v1/programs/manage/{slug}/rewards/", {"severity": "critical"}
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin deleting Beta's reward
        assert (
            api_client.delete(
                f"/api/v1/programs/manage/{slug}/rewards/{beta_reward.id}/"
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin reading Beta's invites
        assert (
            api_client.get(f"/api/v1/programs/manage/{slug}/invites/").status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin modifying Beta's invites
        assert (
            api_client.post(
                f"/api/v1/programs/manage/{slug}/invites/", {"email": "test@test.com"}
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin deleting Beta's invite
        assert (
            api_client.delete(
                f"/api/v1/programs/manage/{slug}/invites/{beta_invite.id}/"
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin submitting Beta's program for review
        assert (
            api_client.post(
                f"/api/v1/programs/manage/{slug}/submit-review/"
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

        # Alpha admin transitioning Beta's program status
        assert (
            api_client.post(
                f"/api/v1/programs/manage/{slug}/transition-status/",
                {"status": "paused"},
            ).status_code
            == status.HTTP_404_NOT_FOUND
        )

from datetime import timedelta

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import (
    Organization,
    OrganizationStatus,
)
from apps.programs.models import Program, ProgramStatus, ProgramVisibility
from django.utils import timezone
from rest_framework import status


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="test@test.com",
        password="password",
        role=UserRole.COMPANY_ADMIN,
        is_verified=True,
        mfa_enabled=True,
    )


@pytest.fixture
def org(db):
    return Organization.objects.create(
        name="Test Org", status=OrganizationStatus.VERIFIED
    )


import secrets

from apps.companies.services import invite_member


@pytest.fixture
def mock_send_mail(monkeypatch):
    monkeypatch.setattr(
        "apps.companies.services.send_mail", lambda *args, **kwargs: None
    )


@pytest.mark.django_db
class TestInvitationExpiry:

    def test_invitation_expiry(
        self, api_client, org, test_user, mock_send_mail, monkeypatch
    ):
        api_client.force_authenticate(user=test_user)
        monkeypatch.setattr(secrets, "token_urlsafe", lambda x: "test_token_abc")
        invite = invite_member(org, test_user.email, "company_viewer", test_user)
        # Manually expire it
        invite.expires_at = timezone.now() - timedelta(days=1)
        invite.save()

        response = api_client.post(
            "/api/v1/companies/invitations/accept/", {"token": "test_token_abc"}
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
        assert "expired" in str(response.data).lower()

    def test_invitation_already_used(
        self, api_client, org, test_user, mock_send_mail, monkeypatch
    ):
        api_client.force_authenticate(user=test_user)
        monkeypatch.setattr(secrets, "token_urlsafe", lambda x: "test_token_def")
        invite = invite_member(org, test_user.email, "company_viewer", test_user)

        response = api_client.post(
            "/api/v1/companies/invitations/accept/", {"token": "test_token_def"}
        )
        assert response.status_code == status.HTTP_200_OK

        response = api_client.post(
            "/api/v1/companies/invitations/accept/", {"token": "test_token_def"}
        )
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_403_FORBIDDEN,
        ]
        assert "already been used" in str(response.data).lower()


@pytest.mark.django_db
class TestSuspendedOrgHidden:

    def test_suspended_org_hidden_from_public(self, api_client, org):
        program = Program.objects.create(
            organization=org,
            title="Public Program",
            slug="public-program",
            status=ProgramStatus.ACTIVE,
            visibility=ProgramVisibility.PUBLIC,
        )

        # Verify it's visible initially
        response = api_client.get("/api/v1/programs/")
        assert response.status_code == status.HTTP_200_OK
        results = (
            response.data.get("results", response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        assert len(results) > 0
        assert results[0]["slug"] == "public-program"

        response = api_client.get("/api/v1/programs/public-program/")
        assert response.status_code == status.HTTP_200_OK

        # Suspend org
        org.status = OrganizationStatus.SUSPENDED
        org.save()

        # Verify it's hidden from list
        response = api_client.get("/api/v1/programs/")
        assert response.status_code == status.HTTP_200_OK
        results2 = (
            response.data.get("results", response.data)
            if isinstance(response.data, dict)
            else response.data
        )
        assert len(results2) == 0

        # Verify detail returns 404
        response = api_client.get("/api/v1/programs/public-program/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

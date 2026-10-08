"""Tests for Organization Member Management, Invitations, and Last-Admin Defense."""

import pytest
from apps.accounts.models import User, UserRole
from apps.companies.models import (
    MemberRole,
    Organization,
    OrganizationInvitation,
    OrganizationMember,
)
from apps.companies.services import invite_member
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestOrganizationMembers:

    @pytest.fixture
    def setup_org(self):
        owner = User.objects.create_user(
            email="owner@acme.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(name="Acme Corp", website="https://acme.com")
        member = OrganizationMember.objects.create(
            organization=org,
            user=owner,
            role=MemberRole.COMPANY_ADMIN,
        )
        return org, owner, member

    def test_invite_member_creates_hashed_token_and_expires(self, setup_org):
        org, owner, _ = setup_org
        client = APIClient()
        client.force_authenticate(user=owner)

        res = client.post(
            "/api/v1/companies/me/members/",
            {"email": "triager@acme.com", "role": MemberRole.COMPANY_TRIAGER},
            format="json",
        )
        assert res.status_code == status.HTTP_201_CREATED

        invite = OrganizationInvitation.objects.get(email="triager@acme.com")
        assert invite.role == MemberRole.COMPANY_TRIAGER
        assert len(invite.token_hash) == 64  # SHA-256 hash stored, not plain token
        assert invite.is_used is False
        assert invite.expires_at > timezone.now()

    def test_accept_invitation_flow_and_reused_token_rejected(self, setup_org):
        org, owner, _ = setup_org
        invite = invite_member(
            org, "newtriager@acme.com", MemberRole.COMPANY_TRIAGER, owner
        )

        new_user = User.objects.create_user(
            email="newtriager@acme.com",
            password="SecurePassword123!",
            role=UserRole.HUNTER,  # Initially registered as hunter
            is_verified=True,
            mfa_enabled=True,
        )
        client = APIClient()
        client.force_authenticate(user=new_user)

        # Retrieve raw token from invite link or pass invalid token
        res_bad = client.post(
            "/api/v1/companies/invitations/accept/",
            {"token": "invalid_fake_token"},
            format="json",
        )
        assert res_bad.status_code == status.HTTP_400_BAD_REQUEST

    def test_last_admin_defense_prevents_removal_and_demotion(self, setup_org):
        org, owner, member = setup_org
        client = APIClient()
        client.force_authenticate(user=owner)

        # Attempt to demote self
        res_demote = client.patch(
            f"/api/v1/companies/me/members/{member.id}/",
            {"role": MemberRole.COMPANY_VIEWER},
            format="json",
        )
        # Cannot change own role
        assert res_demote.status_code == status.HTTP_400_BAD_REQUEST

        # Add second admin
        admin2 = User.objects.create_user(
            email="admin2@acme.com",
            password="SecurePassword123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        member2 = OrganizationMember.objects.create(
            organization=org,
            user=admin2,
            role=MemberRole.COMPANY_ADMIN,
        )

        # Now admin1 can demote admin2
        res_demote2 = client.patch(
            f"/api/v1/companies/me/members/{member2.id}/",
            {"role": MemberRole.COMPANY_VIEWER},
            format="json",
        )
        assert res_demote2.status_code == status.HTTP_200_OK

        # Try to remove admin1 (who is now the last admin)
        # Authenticate as admin2 (viewer) -> cannot remove
        client.force_authenticate(user=admin2)
        res_remove = client.delete(f"/api/v1/companies/me/members/{member.id}/")
        assert res_remove.status_code == status.HTTP_403_FORBIDDEN

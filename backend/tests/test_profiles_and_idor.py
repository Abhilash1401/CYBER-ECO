"""Tests for profile retrieval, self-updates, IDOR prevention, and public profiles."""

import pytest
from apps.accounts.models import HunterProfile, User


@pytest.mark.django_db
class TestProfilesAndIDOR:
    def test_hunter_can_view_and_update_own_profile(self, api_client):
        """User can access and update their own researcher profile."""
        user = User.objects.create_user(
            email="hunter_profile@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        api_client.force_login(user)

        # GET own profile (auto creates if missing)
        get_resp = api_client.get("/api/v1/profiles/me/")
        assert get_resp.status_code == 200
        assert "username" in get_resp.data

        # PATCH own profile
        patch_resp = api_client.patch(
            "/api/v1/profiles/me/",
            {
                "username": "bug_ninja",
                "bio": "Security researcher focused on web applications",
                "website": "https://ninja.example",
                "is_public": True,
            },
            format="json",
        )
        assert patch_resp.status_code == 200
        assert patch_resp.data["username"] == "bug_ninja"
        assert (
            patch_resp.data["bio"] == "Security researcher focused on web applications"
        )

    def test_public_profile_endpoint_only_exposes_public_profiles(self, api_client):
        """Public profile returns 200 for public profile and 404 for private profile."""
        user1 = User.objects.create_user(
            email="public_hunter@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        HunterProfile.objects.create(
            user=user1,
            username="public_hero",
            bio="Public bio",
            is_public=True,
        )

        user2 = User.objects.create_user(
            email="private_hunter@example.com",
            password="StrongPassword123!",
            role="hunter",
            is_verified=True,
        )
        HunterProfile.objects.create(
            user=user2,
            username="stealth_ninja",
            bio="Secret bio",
            is_public=False,
        )

        # Anonymous request for public profile succeeds
        pub_resp = api_client.get("/api/v1/profiles/public_hero/")
        assert pub_resp.status_code == 200
        assert pub_resp.data["username"] == "public_hero"
        # Email and private IDs must NOT be present in public profile
        assert "email" not in pub_resp.data
        assert "user" not in pub_resp.data

        # Anonymous request for private profile returns 404
        priv_resp = api_client.get("/api/v1/profiles/stealth_ninja/")
        assert priv_resp.status_code == 404

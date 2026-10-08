import uuid

import pytest
from rest_framework import status


@pytest.mark.django_db
class TestPhase3Unauthenticated:
    """Tests that unauthenticated clients cannot access protected Phase 3 endpoints, but CAN access public ones."""

    def test_unauthenticated_company_endpoints(self, api_client):
        fake_uuid = str(uuid.uuid4())

        # POST /api/v1/companies/
        assert api_client.post("/api/v1/companies/", {"name": "Test"}).status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # GET /api/v1/companies/me/
        assert api_client.get("/api/v1/companies/me/").status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # GET /api/v1/companies/me/members/
        assert api_client.get("/api/v1/companies/me/members/").status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # POST /api/v1/companies/me/members/
        assert api_client.post(
            "/api/v1/companies/me/members/", {"email": "a@b.com"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # PATCH /api/v1/companies/me/members/{uuid}/
        assert api_client.patch(
            f"/api/v1/companies/me/members/{fake_uuid}/", {"role": "company_viewer"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # DELETE /api/v1/companies/me/members/{uuid}/
        assert api_client.delete(
            f"/api/v1/companies/me/members/{fake_uuid}/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/companies/me/domains/{uuid}/verify-dns/
        assert api_client.post(
            f"/api/v1/companies/me/domains/{fake_uuid}/verify-dns/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/companies/invitations/accept/
        assert api_client.post(
            "/api/v1/companies/invitations/accept/", {"token": "123"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/companies/{uuid}/review/
        assert api_client.post(
            f"/api/v1/companies/{fake_uuid}/review/", {"action": "verify"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_unauthenticated_program_endpoints(self, api_client):
        fake_uuid = str(uuid.uuid4())
        slug = "dummy-slug"

        # GET /api/v1/programs/manage/list/
        assert api_client.get("/api/v1/programs/manage/list/").status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # POST /api/v1/programs/manage/list/
        assert api_client.post(
            "/api/v1/programs/manage/list/", {"title": "Test"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # GET /api/v1/programs/manage/{slug}/
        assert api_client.get(f"/api/v1/programs/manage/{slug}/").status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        ]

        # PATCH /api/v1/programs/manage/{slug}/
        assert api_client.patch(
            f"/api/v1/programs/manage/{slug}/", {"title": "Update"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/programs/manage/{slug}/submit-review/
        assert api_client.post(
            f"/api/v1/programs/manage/{slug}/submit-review/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/programs/manage/{slug}/approve-active/
        assert api_client.post(
            f"/api/v1/programs/manage/{slug}/approve-active/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/programs/manage/{slug}/transition-status/
        assert api_client.post(
            f"/api/v1/programs/manage/{slug}/transition-status/", {"status": "paused"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # GET /api/v1/programs/manage/{slug}/scopes/
        assert api_client.get(
            f"/api/v1/programs/manage/{slug}/scopes/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/programs/manage/{slug}/scopes/
        assert api_client.post(
            f"/api/v1/programs/manage/{slug}/scopes/", {"asset_type": "url"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # DELETE /api/v1/programs/manage/{slug}/scopes/{uuid}/
        assert api_client.delete(
            f"/api/v1/programs/manage/{slug}/scopes/{fake_uuid}/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # GET /api/v1/programs/manage/{slug}/rewards/
        assert api_client.get(
            f"/api/v1/programs/manage/{slug}/rewards/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/programs/manage/{slug}/rewards/
        assert api_client.post(
            f"/api/v1/programs/manage/{slug}/rewards/", {"severity": "critical"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # DELETE /api/v1/programs/manage/{slug}/rewards/{uuid}/
        assert api_client.delete(
            f"/api/v1/programs/manage/{slug}/rewards/{fake_uuid}/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # GET /api/v1/programs/manage/{slug}/invites/
        assert api_client.get(
            f"/api/v1/programs/manage/{slug}/invites/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # POST /api/v1/programs/manage/{slug}/invites/
        assert api_client.post(
            f"/api/v1/programs/manage/{slug}/invites/", {"email": "test@test.com"}
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

        # DELETE /api/v1/programs/manage/{slug}/invites/{uuid}/
        assert api_client.delete(
            f"/api/v1/programs/manage/{slug}/invites/{fake_uuid}/"
        ).status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_public_program_endpoints(self, api_client):
        # GET /api/v1/programs/
        response = api_client.get("/api/v1/programs/")
        assert response.status_code == status.HTTP_200_OK

        # GET /api/v1/programs/{slug}/
        # For a non-existent slug it should return 404, but not 401/403
        response = api_client.get("/api/v1/programs/dummy-slug/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

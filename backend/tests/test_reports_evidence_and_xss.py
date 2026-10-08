"""Tests for evidence validation, magic bytes verification, and XSS sanitization."""

import io

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
from apps.reports.models import Report, ReportEvidence, ScanStatus
from apps.reports.services import sanitize_plain_text
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestReportsEvidenceAndXSS:

    @pytest.fixture
    def setup_data(self):
        hunter = User.objects.create_user(
            email="hunter@audit.com",
            password="Password123!",
            role=UserRole.HUNTER,
            is_verified=True,
            mfa_enabled=True,
        )
        company_admin = User.objects.create_user(
            email="admin@target.com",
            password="Password123!",
            role=UserRole.COMPANY_ADMIN,
            is_verified=True,
            mfa_enabled=True,
        )
        org = Organization.objects.create(
            name="Target Org", status=OrganizationStatus.VERIFIED
        )
        OrganizationMember.objects.create(
            organization=org, user=company_admin, role=MemberRole.COMPANY_ADMIN
        )

        prog = Program.objects.create(
            organization=org, title="Bounty", slug="bounty", status=ProgramStatus.ACTIVE
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
            title="Clean Title",
            description="Clean Desc",
            steps_to_reproduce="Clean Steps",
            impact="Clean Impact",
            severity=Severity.HIGH,
        )
        return hunter, company_admin, report

    def test_upload_magic_byte_spoofing_rejected(self, setup_data):
        hunter, _, report = setup_data
        client = APIClient()
        client.force_authenticate(user=hunter)

        # Upload an executable/fake script named evil.png without valid PNG magic bytes
        fake_png = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00This is an executable")
        fake_png.name = "payload.png"

        res = client.post(
            f"/api/v1/reports/{report.id}/evidence/upload/",
            {"file": fake_png},
            format="multipart",
        )
        assert res.status_code == status.HTTP_400_BAD_REQUEST
        assert "spoofed file detected" in str(res.data).lower()

    def test_valid_evidence_upload_and_download_flow(self, setup_data):
        hunter, _, report = setup_data
        client = APIClient()
        client.force_authenticate(user=hunter)

        # Upload valid PNG (starts with standard PNG signature)
        valid_png = io.BytesIO(
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        )
        valid_png.name = "screenshot.png"

        res_upload = client.post(
            f"/api/v1/reports/{report.id}/evidence/upload/",
            {"file": valid_png},
            format="multipart",
        )
        # Newly uploaded file has scan_status=pending by default
        assert res_upload.data["scan_status"] == ScanStatus.PENDING
        evidence_id = res_upload.data["id"]

        # Request download URL while PENDING -> must return 403 Forbidden
        res_dl_pending = client.get(
            f"/api/v1/reports/{report.id}/evidence/{evidence_id}/download/"
        )
        assert res_dl_pending.status_code == status.HTTP_403_FORBIDDEN
        assert "unavailable for download" in str(res_dl_pending.data).lower()

        # Mark evidence scan_status as clean (simulating completed ClamAV scan)
        evidence = ReportEvidence.objects.get(id=evidence_id)
        evidence.scan_status = ScanStatus.CLEAN
        evidence.save()

        # Now download succeeds and returns signed URL expiring in 60s
        res_dl = client.get(
            f"/api/v1/reports/{report.id}/evidence/{evidence_id}/download/"
        )
        assert res_dl.status_code == status.HTTP_200_OK
        assert "download_url" in res_dl.data
        assert res_dl.data["expires_in_seconds"] == 60

    def test_unscanned_or_infected_evidence_cannot_be_downloaded(self, setup_data):
        hunter, _, report = setup_data
        evidence = ReportEvidence.objects.create(
            report=report,
            uploaded_by=hunter,
            file_key="evidence/test.png",
            original_filename="test.png",
            file_size=1024,
            mime_type="image/png",
            sha256_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            scan_status=ScanStatus.PENDING,
        )

        client = APIClient()
        client.force_authenticate(user=hunter)

        res = client.get(
            f"/api/v1/reports/{report.id}/evidence/{evidence.id}/download/"
        )
        assert res.status_code == status.HTTP_403_FORBIDDEN
        assert "unavailable for download" in str(res.data).lower()

    def test_stored_xss_payloads_neutralized(self, setup_data):
        hunter, _, _ = setup_data
        report = setup_data[2]
        client = APIClient()
        client.force_authenticate(user=hunter)

        # Test Payload 1: script tags and inline image event handler
        xss_payload_1 = "<script>alert('XSS')</script><img src=x onerror=alert(1)>**Safe Bold Text**"
        res1 = client.post(
            f"/api/v1/reports/{report.id}/comments/",
            {"content": xss_payload_1, "visibility": "shared"},
            format="json",
        )
        assert res1.status_code == status.HTTP_201_CREATED
        content_1 = res1.data["content"]
        assert "<script>" not in content_1
        assert "onerror" not in content_1
        assert "Safe Bold Text" in content_1

        # Test Payload 2: SVG onload and iframe injection embedded in legitimate comment text
        xss_payload_2 = "Analysis: <svg onload=\"alert('SVG_XSS')\"><iframe src=\"javascript:alert('IFRAME')\"></iframe>Confirmed reproducible vulnerability."
        res2 = client.post(
            f"/api/v1/reports/{report.id}/comments/",
            {"content": xss_payload_2, "visibility": "shared"},
            format="json",
        )
        assert res2.status_code == status.HTTP_201_CREATED
        content_2 = res2.data["content"]
        assert "<svg" not in content_2
        assert "<iframe" not in content_2
        assert "javascript:" not in content_2
        assert "alert(" not in content_2
        assert "Analysis:" in content_2
        assert "Confirmed reproducible vulnerability." in content_2

        # Test Payload 3: Pure XSS tag without content is stripped completely to empty and correctly rejected
        pure_xss = "<script>alert('PURE_EVIL')</script>"
        res3 = client.post(
            f"/api/v1/reports/{report.id}/comments/",
            {"content": pure_xss, "visibility": "shared"},
            format="json",
        )
        assert res3.status_code == status.HTTP_400_BAD_REQUEST
        assert "empty" in str(res3.data).lower()

        # Test Payload 3: Report title plain-text tag stripping
        clean_title = sanitize_plain_text(
            "Critical Bug <script>alert('TITLE')</script>"
        )
        assert clean_title == "Critical Bug"
        assert "<script>" not in clean_title

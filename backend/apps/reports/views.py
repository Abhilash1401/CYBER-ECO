"""Views for Vulnerability Reports, Triage desk, Comments, and Evidence."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.services import log_audit_event
from apps.common.permissions import (
    IsAuthenticatedAndVerified,
    IsCompanyMember,
    IsHunter,
)
from apps.companies.models import MemberRole, OrganizationMember
from apps.programs.models import Program, ProgramScope

from .models import (
    CommentVisibility,
    Report,
    ReportEvidence,
    ReportStatus,
    ScanStatus,
)
from .serializers import (
    CompanyReportDetailSerializer,
    CompanyReportListSerializer,
    HunterReportCreateSerializer,
    HunterReportDetailSerializer,
    HunterReportListSerializer,
    InternalReportCommentSerializer,
    ReportCommentCreateSerializer,
    ReportEvidenceSerializer,
    ReportStatusTransitionSerializer,
    SharedReportCommentSerializer,
)
from .services import (
    add_report_comment,
    submit_report,
    transition_report_status,
)
from .storage import (
    generate_presigned_download_url,
    validate_evidence_file,
)

# ==========================================
# HUNTER ENDPOINTS (Tenant-Isolated)
# ==========================================


class HunterReportListCreateView(APIView):
    """List submitted reports for the authenticated researcher or submit a new report."""

    permission_classes = [IsHunter]

    def get(self, request):
        reports = Report.objects.filter(hunter=request.user).select_related(
            "program", "target_asset"
        )
        return Response(HunterReportListSerializer(reports, many=True).data)

    def post(self, request):
        serializer = HunterReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        program = get_object_or_404(Program, slug=data["program_slug"])
        target_asset = get_object_or_404(
            ProgramScope, id=data["target_asset_id"], program=program
        )

        report = submit_report(
            program=program,
            hunter_user=request.user,
            target_asset=target_asset,
            title=data["title"],
            vulnerability_type=data["vulnerability_type"],
            description=data["description"],
            steps_to_reproduce=data["steps_to_reproduce"],
            impact=data["impact"],
            severity=data["severity"],
            cvss_vector=data.get("cvss_vector", ""),
            cvss_score=data.get("cvss_score"),
            request=request,
        )
        return Response(
            HunterReportDetailSerializer(report).data, status=status.HTTP_201_CREATED
        )


class HunterReportDetailView(APIView):
    """Retrieve or withdraw an individual report owned by the researcher."""

    permission_classes = [IsHunter]

    def _get_report(self, request, report_id):
        return Report.objects.filter(id=report_id, hunter=request.user).first()

    def get(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(HunterReportDetailSerializer(report).data)

    def patch(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )

        target_status = request.data.get("status")
        if target_status != ReportStatus.WITHDRAWN:
            return Response(
                {"detail": "Researchers may only transition reports to 'withdrawn'."},
                status=status.HTTP_403_FORBIDDEN,
            )

        updated = transition_report_status(
            report=report,
            target_status=ReportStatus.WITHDRAWN,
            actor_user=request.user,
            reason=request.data.get("reason", "Withdrawn by researcher"),
            request=request,
        )
        return Response(HunterReportDetailSerializer(updated).data)


# ==========================================
# COMPANY TRIAGE ENDPOINTS
# ==========================================


class CompanyReportListView(APIView):
    """List reports belonging to the user's organization with status, severity, and program filters."""

    permission_classes = [IsCompanyMember]

    def get(self, request):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(
                {"detail": "No organization found."}, status=status.HTTP_404_NOT_FOUND
            )

        queryset = Report.objects.filter(
            program__organization=membership.organization
        ).select_related("program", "target_asset", "hunter")

        # Filters
        program_slug = request.query_params.get("program")
        if program_slug:
            queryset = queryset.filter(program__slug=program_slug)

        report_status = request.query_params.get("status")
        if report_status:
            queryset = queryset.filter(status=report_status)

        severity = request.query_params.get("severity")
        if severity:
            queryset = queryset.filter(
                Q(triaged_severity=severity) | Q(severity=severity)
            )

        return Response(CompanyReportListSerializer(queryset, many=True).data)


class CompanyReportDetailView(APIView):
    """Retrieve report details or transition status and assign severity for company users."""

    permission_classes = [IsCompanyMember]

    def _get_report(self, request, report_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return None
        return Report.objects.filter(
            id=report_id, program__organization=membership.organization
        ).first()

    def get(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )

        log_audit_event(
            actor=request.user,
            action="report.viewed_by_company",
            target=report,
            request=request,
        )
        return Response(CompanyReportDetailSerializer(report).data)

    def post(self, request, report_id):
        report = self._get_report(request, report_id)
        if not report:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )

        membership = OrganizationMember.objects.filter(user=request.user).first()
        if membership.role == MemberRole.COMPANY_VIEWER:
            return Response(
                {"detail": "Company viewers have read-only access."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ReportStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        duplicate_report = None
        if data.get("duplicate_of_id"):
            duplicate_report = Report.objects.filter(
                id=data["duplicate_of_id"],
                program__organization=membership.organization,
            ).first()
            if not duplicate_report:
                return Response(
                    {
                        "duplicate_of": [
                            "Referenced duplicate report not found in this organization."
                        ]
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

        updated = transition_report_status(
            report=report,
            target_status=data["status"],
            actor_user=request.user,
            reason=data.get("reason", ""),
            duplicate_of_report=duplicate_report,
            triaged_severity=data.get("triaged_severity"),
            request=request,
        )
        return Response(CompanyReportDetailSerializer(updated).data)


# ==========================================
# COMMENT MANAGEMENT
# ==========================================


class ReportCommentListCreateView(APIView):
    """Add a comment or list comments on a report (respecting role boundaries)."""

    permission_classes = [IsAuthenticatedAndVerified]

    def _get_accessible_report(self, request, report_id):
        user = request.user
        report = Report.objects.filter(id=report_id).first()
        if not report:
            return None

        # Check access: Hunter of report OR member of company OR platform admin
        if report.hunter_id == user.id:
            return report, True, False

        membership = OrganizationMember.objects.filter(
            organization=report.program.organization,
            user=user,
        ).first()
        if membership:
            return report, False, True

        if getattr(user, "is_platform_admin", False):
            return report, False, True

        return None

    def post(self, request, report_id):
        access = self._get_accessible_report(request, report_id)
        if not access:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )

        report, is_hunter, is_company = access
        serializer = ReportCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        visibility = serializer.validated_data.get(
            "visibility", CommentVisibility.SHARED
        )
        if is_hunter and visibility == CommentVisibility.INTERNAL:
            return Response(
                {"detail": "Researchers cannot post internal comments."},
                status=status.HTTP_403_FORBIDDEN,
            )

        comment = add_report_comment(
            report=report,
            author_user=request.user,
            content=serializer.validated_data["content"],
            visibility=visibility,
            request=request,
        )

        serializer_class = (
            SharedReportCommentSerializer
            if is_hunter
            else InternalReportCommentSerializer
        )
        return Response(serializer_class(comment).data, status=status.HTTP_201_CREATED)


# ==========================================
# EVIDENCE UPLOAD & DOWNLOAD
# ==========================================


class ReportEvidenceUploadView(APIView):
    """Upload PoC evidence to a report with magic-byte validation and SHA-256 calculation."""

    permission_classes = [IsAuthenticatedAndVerified]
    parser_classes = [MultiPartParser]

    def _get_accessible_report(self, request, report_id):
        user = request.user
        report = Report.objects.filter(id=report_id).first()
        if not report:
            return None
        if report.hunter_id == user.id:
            return report
        membership = OrganizationMember.objects.filter(
            organization=report.program.organization,
            user=user,
        ).first()
        if membership:
            return report
        return None

    def post(self, request, report_id):
        report = self._get_accessible_report(request, report_id)
        if not report:
            return Response(
                {"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND
            )

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response(
                {"file": ["No file provided."]}, status=status.HTTP_400_BAD_REQUEST
            )

        file_bytes = file_obj.read()
        safe_name, verified_mime, sha256_hash, file_key = validate_evidence_file(
            file_bytes, file_obj.name
        )

        # Create record strictly with ScanStatus.PENDING (files cannot be downloaded until scanned or verified clean)
        evidence = ReportEvidence.objects.create(
            report=report,
            uploaded_by=request.user,
            file_key=file_key,
            original_filename=safe_name,
            file_size=len(file_bytes),
            mime_type=verified_mime,
            sha256_hash=sha256_hash,
            scan_status=ScanStatus.PENDING,
        )

        log_audit_event(
            actor=request.user,
            action="report.evidence_uploaded",
            target=report,
            metadata={"evidence_id": str(evidence.id), "sha256": sha256_hash},
            request=request,
        )
        return Response(
            ReportEvidenceSerializer(evidence).data, status=status.HTTP_201_CREATED
        )


class ReportEvidenceDownloadView(APIView):
    """Provide secure presigned download link with attachment and nosniff protection."""

    permission_classes = [IsAuthenticatedAndVerified]

    def get(self, request, report_id, evidence_id):
        user = request.user
        evidence = (
            ReportEvidence.objects.filter(id=evidence_id, report_id=report_id)
            .select_related("report")
            .first()
        )
        if not evidence:
            return Response(
                {"detail": "Evidence attachment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        report = evidence.report
        # Access check
        has_access = (
            report.hunter_id == user.id
            or OrganizationMember.objects.filter(
                organization=report.program.organization, user=user
            ).exists()
            or getattr(user, "is_platform_admin", False)
        )
        if not has_access:
            return Response(
                {"detail": "Evidence attachment not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Unscanned / infected files are not downloadable
        if evidence.scan_status != ScanStatus.CLEAN:
            return Response(
                {
                    "detail": f"File is currently unavailable for download (scan status: {evidence.scan_status})."
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        download_url = generate_presigned_download_url(
            evidence.file_key, evidence.original_filename
        )

        log_audit_event(
            actor=user,
            action="report.evidence_downloaded",
            target=report,
            metadata={"evidence_id": str(evidence.id)},
            request=request,
        )
        return Response(
            {
                "download_url": download_url,
                "filename": evidence.original_filename,
                "mime_type": evidence.mime_type,
                "expires_in_seconds": 60,
            }
        )

"""Serializers for reports, triage, comments, and evidence.

Strict dual-serializer architecture:
- Hunters NEVER receive internal comments, internal fields, or duplicate identity details.
- Company users receive full triage controls, internal comments, and duplicate linkage.
"""

from rest_framework import serializers

from apps.programs.models import Severity

from .models import (
    CommentVisibility,
    Report,
    ReportComment,
    ReportEvidence,
    ReportStatus,
    ReportStatusHistory,
    VulnerabilityType,
)

# ==========================================
# COMMENTS SERIALIZERS (Strict Separation)
# ==========================================


class SharedReportCommentSerializer(serializers.ModelSerializer):
    """Comment serializer for researchers (hunters). ONLY presents shared comments."""

    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = ReportComment
        fields = [
            "id",
            "author_email",
            "content",
            "visibility",
            "created_at",
        ]
        read_only_fields = ["id", "author_email", "visibility", "created_at"]


class InternalReportCommentSerializer(serializers.ModelSerializer):
    """Comment serializer for company users and platform admins (includes internal comments)."""

    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta:
        model = ReportComment
        fields = [
            "id",
            "author_email",
            "content",
            "visibility",
            "created_at",
        ]
        read_only_fields = ["id", "author_email", "created_at"]


# ==========================================
# STATUS HISTORY & EVIDENCE SERIALIZERS
# ==========================================


class ReportStatusHistorySerializer(serializers.ModelSerializer):
    """Audit history of status transitions."""

    changed_by_email = serializers.EmailField(source="changed_by.email", read_only=True)

    class Meta:
        model = ReportStatusHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "changed_by_email",
            "reason",
            "created_at",
        ]
        read_only_fields = fields


class ReportEvidenceSerializer(serializers.ModelSerializer):
    """Evidence file attachment metadata."""

    uploaded_by_email = serializers.EmailField(
        source="uploaded_by.email", read_only=True
    )

    class Meta:
        model = ReportEvidence
        fields = [
            "id",
            "original_filename",
            "file_size",
            "mime_type",
            "sha256_hash",
            "scan_status",
            "uploaded_by_email",
            "created_at",
        ]
        read_only_fields = fields


# ==========================================
# HUNTER SERIALIZERS (Zero Internal Leakage)
# ==========================================


class HunterReportCreateSerializer(serializers.Serializer):
    """Submission payload for researchers."""

    program_slug = serializers.SlugField()
    target_asset_id = serializers.UUIDField()
    title = serializers.CharField(max_length=255)
    vulnerability_type = serializers.ChoiceField(choices=VulnerabilityType.choices)
    description = serializers.CharField()
    steps_to_reproduce = serializers.CharField()
    impact = serializers.CharField()
    severity = serializers.ChoiceField(choices=Severity.choices)
    cvss_vector = serializers.CharField(
        max_length=128, required=False, allow_blank=True, default=""
    )
    cvss_score = serializers.DecimalField(
        max_digits=3, decimal_places=1, required=False, allow_null=True, default=None
    )


class HunterReportListSerializer(serializers.ModelSerializer):
    """List serializer for researchers to view their submitted reports."""

    program_title = serializers.CharField(source="program.title", read_only=True)
    program_slug = serializers.CharField(source="program.slug", read_only=True)
    target_asset_value = serializers.CharField(
        source="target_asset.asset_value", read_only=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "program_title",
            "program_slug",
            "target_asset_value",
            "title",
            "vulnerability_type",
            "severity",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class HunterReportDetailSerializer(serializers.ModelSerializer):
    """Detailed view for researchers. Strictly excludes internal notes, duplicate target info, and internal comments."""

    program_title = serializers.CharField(source="program.title", read_only=True)
    program_slug = serializers.CharField(source="program.slug", read_only=True)
    target_asset_value = serializers.CharField(
        source="target_asset.asset_value", read_only=True
    )
    target_asset_type = serializers.CharField(
        source="target_asset.asset_type", read_only=True
    )
    comments = serializers.SerializerMethodField()
    evidence = ReportEvidenceSerializer(many=True, read_only=True)
    status_history = ReportStatusHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "program_title",
            "program_slug",
            "target_asset_value",
            "target_asset_type",
            "title",
            "vulnerability_type",
            "description",
            "steps_to_reproduce",
            "impact",
            "severity",
            "cvss_vector",
            "cvss_score",
            "status",
            "created_at",
            "updated_at",
            "comments",
            "evidence",
            "status_history",
        ]
        read_only_fields = fields

    def get_comments(self, obj):
        # Strictly return SHARED comments only
        shared = obj.comments.filter(visibility=CommentVisibility.SHARED)
        return SharedReportCommentSerializer(shared, many=True).data


# ==========================================
# COMPANY & PLATFORM ADMIN SERIALIZERS
# ==========================================


class CompanyReportListSerializer(serializers.ModelSerializer):
    """List serializer for company triagers & admins."""

    hunter_email = serializers.EmailField(source="hunter.email", read_only=True)
    program_title = serializers.CharField(source="program.title", read_only=True)
    program_slug = serializers.CharField(source="program.slug", read_only=True)
    target_asset_value = serializers.CharField(
        source="target_asset.asset_value", read_only=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "hunter_email",
            "program_title",
            "program_slug",
            "target_asset_value",
            "title",
            "vulnerability_type",
            "severity",
            "triaged_severity",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CompanyReportDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer for company triagers and admins, including internal comments."""

    hunter_email = serializers.EmailField(source="hunter.email", read_only=True)
    program_title = serializers.CharField(source="program.title", read_only=True)
    program_slug = serializers.CharField(source="program.slug", read_only=True)
    target_asset_value = serializers.CharField(
        source="target_asset.asset_value", read_only=True
    )
    target_asset_type = serializers.CharField(
        source="target_asset.asset_type", read_only=True
    )
    comments = InternalReportCommentSerializer(many=True, read_only=True)
    evidence = ReportEvidenceSerializer(many=True, read_only=True)
    status_history = ReportStatusHistorySerializer(many=True, read_only=True)
    duplicate_of_id = serializers.UUIDField(
        source="duplicate_of.id", read_only=True, allow_null=True
    )

    class Meta:
        model = Report
        fields = [
            "id",
            "hunter_email",
            "program_title",
            "program_slug",
            "target_asset_value",
            "target_asset_type",
            "title",
            "vulnerability_type",
            "description",
            "steps_to_reproduce",
            "impact",
            "severity",
            "triaged_severity",
            "cvss_vector",
            "cvss_score",
            "status",
            "duplicate_of_id",
            "closed_reason",
            "created_at",
            "updated_at",
            "comments",
            "evidence",
            "status_history",
        ]
        read_only_fields = [
            "id",
            "hunter_email",
            "program_title",
            "program_slug",
            "target_asset_value",
            "target_asset_type",
            "duplicate_of_id",
            "created_at",
            "updated_at",
            "comments",
            "evidence",
            "status_history",
        ]


class ReportStatusTransitionSerializer(serializers.Serializer):
    """Payload to transition report state machine."""

    status = serializers.ChoiceField(choices=ReportStatus.choices)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    duplicate_of_id = serializers.UUIDField(
        required=False, allow_null=True, default=None
    )
    triaged_severity = serializers.ChoiceField(
        choices=Severity.choices, required=False, allow_null=True, default=None
    )


class ReportCommentCreateSerializer(serializers.Serializer):
    """Payload to post a comment."""

    content = serializers.CharField()
    visibility = serializers.ChoiceField(
        choices=CommentVisibility.choices, default=CommentVisibility.SHARED
    )

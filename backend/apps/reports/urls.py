"""URLs for the reports application."""

from django.urls import path

from .views import (
    CompanyReportDetailView,
    CompanyReportListView,
    HunterReportDetailView,
    HunterReportListCreateView,
    ReportCommentListCreateView,
    ReportEvidenceDownloadView,
    ReportEvidenceUploadView,
)

urlpatterns = [
    # Researcher (Hunter) endpoints
    path("", HunterReportListCreateView.as_view(), name="report-hunter-list-create"),
    path(
        "<uuid:report_id>/",
        HunterReportDetailView.as_view(),
        name="report-hunter-detail",
    ),
    # Company triage endpoints
    path("manage/list/", CompanyReportListView.as_view(), name="report-company-list"),
    path(
        "manage/<uuid:report_id>/",
        CompanyReportDetailView.as_view(),
        name="report-company-detail",
    ),
    # Comments and Discussions
    path(
        "<uuid:report_id>/comments/",
        ReportCommentListCreateView.as_view(),
        name="report-comments",
    ),
    # Evidence Uploads & Downloads
    path(
        "<uuid:report_id>/evidence/upload/",
        ReportEvidenceUploadView.as_view(),
        name="report-evidence-upload",
    ),
    path(
        "<uuid:report_id>/evidence/<uuid:evidence_id>/download/",
        ReportEvidenceDownloadView.as_view(),
        name="report-evidence-download",
    ),
]

"""URLs for programs application."""

from django.urls import path

from .views import (
    CompanyProgramDetailManageView,
    CompanyProgramListCreateView,
    ProgramApproveActiveView,
    ProgramInviteDetailView,
    ProgramInvitesManageView,
    ProgramRewardDetailView,
    ProgramRewardsManageView,
    ProgramScopeDetailView,
    ProgramScopesManageView,
    ProgramSubmitReviewView,
    ProgramTransitionStatusView,
    PublicProgramDetailView,
    PublicProgramListView,
)

urlpatterns = [
    # Public & Hunter discovery endpoints
    path("", PublicProgramListView.as_view(), name="program-list"),
    path("<slug:slug>/", PublicProgramDetailView.as_view(), name="program-detail"),
    # Company program management endpoints
    path(
        "manage/list/",
        CompanyProgramListCreateView.as_view(),
        name="program-manage-list",
    ),
    path(
        "manage/<slug:slug>/",
        CompanyProgramDetailManageView.as_view(),
        name="program-manage-detail",
    ),
    path(
        "manage/<slug:slug>/submit-review/",
        ProgramSubmitReviewView.as_view(),
        name="program-submit-review",
    ),
    path(
        "manage/<slug:slug>/approve-active/",
        ProgramApproveActiveView.as_view(),
        name="program-approve-active",
    ),
    path(
        "manage/<slug:slug>/transition-status/",
        ProgramTransitionStatusView.as_view(),
        name="program-transition-status",
    ),
    # Sub-resource managers
    path(
        "manage/<slug:slug>/scopes/",
        ProgramScopesManageView.as_view(),
        name="program-scopes-manage",
    ),
    path(
        "manage/<slug:slug>/scopes/<uuid:scope_id>/",
        ProgramScopeDetailView.as_view(),
        name="program-scope-delete",
    ),
    path(
        "manage/<slug:slug>/rewards/",
        ProgramRewardsManageView.as_view(),
        name="program-rewards-manage",
    ),
    path(
        "manage/<slug:slug>/rewards/<uuid:reward_id>/",
        ProgramRewardDetailView.as_view(),
        name="program-reward-delete",
    ),
    path(
        "manage/<slug:slug>/invites/",
        ProgramInvitesManageView.as_view(),
        name="program-invites-manage",
    ),
    path(
        "manage/<slug:slug>/invites/<uuid:invite_id>/",
        ProgramInviteDetailView.as_view(),
        name="program-invite-delete",
    ),
]

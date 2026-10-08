"""URLs for companies application."""

from django.urls import path

from .views import (
    AcceptInvitationView,
    OrganizationCreateView,
    OrganizationMemberDetailView,
    OrganizationMembersView,
    OrganizationMeView,
    ReviewOrganizationView,
    VerifyDomainDNSView,
)

urlpatterns = [
    path("", OrganizationCreateView.as_view(), name="org-create"),
    path("me/", OrganizationMeView.as_view(), name="org-me"),
    path("me/members/", OrganizationMembersView.as_view(), name="org-members"),
    path(
        "me/members/<uuid:member_id>/",
        OrganizationMemberDetailView.as_view(),
        name="org-member-detail",
    ),
    path(
        "me/domains/<uuid:domain_id>/verify-dns/",
        VerifyDomainDNSView.as_view(),
        name="org-domain-verify-dns",
    ),
    path(
        "invitations/accept/", AcceptInvitationView.as_view(), name="org-accept-invite"
    ),
    path("<uuid:org_id>/review/", ReviewOrganizationView.as_view(), name="org-review"),
]

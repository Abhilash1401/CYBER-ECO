"""Views for Organizations, Team Members, Domains, and Review."""

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import (
    IsAuthenticatedAndVerified,
    IsCompanyAdmin,
    IsCompanyMember,
    IsPlatformAdmin,
)

from .models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationVerifiedDomain,
)
from .serializers import (
    AcceptInvitationSerializer,
    CreateOrganizationSerializer,
    InviteMemberSerializer,
    OrganizationMemberSerializer,
    OrganizationSerializer,
    ReviewOrganizationSerializer,
    UpdateMemberRoleSerializer,
)
from .services import (
    accept_invitation,
    create_organization,
    invite_member,
    remove_member,
    review_organization,
    update_member_role,
    verify_domain_dns_txt,
)


class OrganizationCreateView(APIView):
    """Create a new organization (company_admin only)."""

    permission_classes = [IsCompanyAdmin]

    def post(self, request):
        serializer = CreateOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        org = create_organization(
            name=serializer.validated_data["name"],
            website=serializer.validated_data["website"],
            domains=serializer.validated_data.get("domains", []),
            creator_user=request.user,
            request=request,
        )
        return Response(
            OrganizationSerializer(org).data, status=status.HTTP_201_CREATED
        )


class OrganizationMeView(APIView):
    """Retrieve current user's organization."""

    permission_classes = [IsCompanyMember]

    def get(self, request):
        membership = (
            OrganizationMember.objects.filter(user=request.user)
            .select_related("organization")
            .first()
        )
        if not membership:
            return Response(
                {"detail": "No organization associated with this account."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(OrganizationSerializer(membership.organization).data)


class OrganizationMembersView(APIView):
    """List members and invite new team members."""

    permission_classes = [IsCompanyMember]

    def get(self, request):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(
                {"detail": "No organization found."}, status=status.HTTP_404_NOT_FOUND
            )
        members = OrganizationMember.objects.filter(
            organization=membership.organization
        )
        return Response(OrganizationMemberSerializer(members, many=True).data)

    def post(self, request):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response(
                {"detail": "No organization found."}, status=status.HTTP_404_NOT_FOUND
            )
        if membership.role != MemberRole.COMPANY_ADMIN:
            return Response(
                {"detail": "Only company administrators can invite members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invite_member(
            org=membership.organization,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            inviter_user=request.user,
            request=request,
        )
        return Response(
            {"detail": "Invitation sent successfully."}, status=status.HTTP_201_CREATED
        )


class OrganizationMemberDetailView(APIView):
    """Update member role or remove member (company_admin only, last-admin protected)."""

    permission_classes = [IsCompanyAdmin]

    def patch(self, request, member_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if membership.role != MemberRole.COMPANY_ADMIN:
            return Response(
                {"detail": "Only company administrators can update member roles."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = update_member_role(
            org=membership.organization,
            member_id=member_id,
            new_role=serializer.validated_data["role"],
            actor=request.user,
            request=request,
        )
        return Response(OrganizationMemberSerializer(updated).data)

    def delete(self, request, member_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if membership.role != MemberRole.COMPANY_ADMIN:
            return Response(
                {"detail": "Only company administrators can remove members."},
                status=status.HTTP_403_FORBIDDEN,
            )

        remove_member(
            org=membership.organization,
            member_id=member_id,
            actor=request.user,
            request=request,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AcceptInvitationView(APIView):
    """Accept an organization invitation token."""

    permission_classes = [IsAuthenticatedAndVerified]

    def post(self, request):
        serializer = AcceptInvitationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member = accept_invitation(
            raw_token=serializer.validated_data["token"],
            accepting_user=request.user,
            request=request,
        )
        return Response(
            OrganizationMemberSerializer(member).data, status=status.HTTP_200_OK
        )


class VerifyDomainDNSView(APIView):
    """Trigger DNS TXT record check for a domain."""

    permission_classes = [IsCompanyAdmin]

    def post(self, request, domain_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        domain_obj = get_object_or_404(
            OrganizationVerifiedDomain,
            id=domain_id,
            organization=membership.organization,
        )

        is_verified = verify_domain_dns_txt(
            domain_obj, actor=request.user, request=request
        )
        return Response(
            {
                "domain": domain_obj.domain,
                "is_verified": is_verified,
                "detail": (
                    "Domain verified successfully."
                    if is_verified
                    else "Verification failed: DNS TXT record not found or does not match."
                ),
            }
        )


class ReviewOrganizationView(APIView):
    """Platform admin review to verify, reject, or suspend an organization."""

    permission_classes = [IsPlatformAdmin]

    def post(self, request, org_id):
        org = get_object_or_404(Organization, id=org_id)
        serializer = ReviewOrganizationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        reviewed = review_organization(
            org=org,
            new_status=serializer.validated_data["status"],
            reason=serializer.validated_data["reason"],
            reviewer_user=request.user,
            request=request,
        )
        return Response(OrganizationSerializer(reviewed).data)

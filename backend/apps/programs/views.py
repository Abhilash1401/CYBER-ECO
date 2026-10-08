"""Views for Programs, Scope Management, Rewards, and Public Discovery."""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.common.permissions import (
    IsCompanyAdmin,
    IsCompanyMember,
    IsPlatformAdmin,
)
from apps.companies.models import OrganizationMember, OrganizationStatus

from .models import (
    Program,
    ProgramStatus,
    ProgramVisibility,
)
from .serializers import (
    ApproveProgramSerializer,
    CreateProgramSerializer,
    InviteHunterSerializer,
    ProgramDetailSerializer,
    ProgramInviteSerializer,
    ProgramPublicSerializer,
    ProgramRewardSerializer,
    ProgramScopeSerializer,
    StatusTransitionSerializer,
)
from .services import (
    approve_program_to_active,
    create_program,
    invite_hunter_to_private_program,
    submit_program_for_review,
    transition_program_status,
)


class PublicProgramListView(generics.ListAPIView):
    """Public discovery endpoint for bug bounty programs.

    Returns:
    - Active public programs
    - Active private programs the authenticated hunter is explicitly invited to
    """

    permission_classes = [AllowAny]
    serializer_class = ProgramPublicSerializer

    def get_queryset(self):
        user = self.request.user
        base_query = Q(
            status=ProgramStatus.ACTIVE,
            visibility=ProgramVisibility.PUBLIC,
            organization__status=OrganizationStatus.VERIFIED,
        )

        if user.is_authenticated and hasattr(user, "is_hunter") and user.is_hunter:
            # Include private programs the user is invited to
            base_query |= Q(
                status=ProgramStatus.ACTIVE,
                visibility=ProgramVisibility.PRIVATE,
                organization__status=OrganizationStatus.VERIFIED,
                invites__hunter=user,
            )

        queryset = (
            Program.objects.filter(base_query)
            .select_related("organization")
            .prefetch_related("scopes", "rewards")
            .distinct()
        )

        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(organization__name__icontains=search)
            )

        return queryset


class PublicProgramDetailView(APIView):
    """Public program detail view by slug (safe public fields only, leaks no notes)."""

    permission_classes = [AllowAny]

    def get(self, request, slug):
        user = request.user
        base_query = Q(
            status=ProgramStatus.ACTIVE,
            visibility=ProgramVisibility.PUBLIC,
            organization__status=OrganizationStatus.VERIFIED,
            slug=slug,
        )

        if user.is_authenticated and getattr(user, "is_hunter", False):
            base_query |= Q(
                status=ProgramStatus.ACTIVE,
                visibility=ProgramVisibility.PRIVATE,
                organization__status=OrganizationStatus.VERIFIED,
                slug=slug,
                invites__hunter=user,
            )

        program = (
            Program.objects.filter(base_query)
            .select_related("organization")
            .prefetch_related("scopes", "rewards")
            .first()
        )
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        return Response(ProgramPublicSerializer(program).data)


class CompanyProgramListCreateView(APIView):
    """List all programs belonging to user's organization or create a new draft program."""

    permission_classes = [IsCompanyMember]

    def get(self, request):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        programs = Program.objects.filter(
            organization=membership.organization
        ).prefetch_related("scopes", "rewards", "invites")
        return Response(ProgramDetailSerializer(programs, many=True).data)

    def post(self, request):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        if membership.role != "company_admin":
            return Response(
                {"detail": "Only company administrators can create programs."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = CreateProgramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        program = create_program(
            org=membership.organization,
            title=serializer.validated_data["title"],
            description=serializer.validated_data["description"],
            visibility=serializer.validated_data["visibility"],
            actor=request.user,
            request=request,
        )
        return Response(
            ProgramDetailSerializer(program).data, status=status.HTTP_201_CREATED
        )


class CompanyProgramDetailManageView(APIView):
    """Retrieve or update a company program (tenant-isolated, returns 404 for other orgs)."""

    permission_classes = [IsCompanyMember]

    def _get_program(self, request, slug):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return None
        return Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()

    def get(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )
        return Response(ProgramDetailSerializer(program).data)

    def patch(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        membership = OrganizationMember.objects.filter(user=request.user).first()
        if membership.role != "company_admin":
            return Response(
                {"detail": "Only company administrators can update program settings."},
                status=status.HTTP_403_FORBIDDEN,
            )

        allowed_fields = [
            "title",
            "description",
            "visibility",
            "rules_of_engagement",
            "safe_harbor",
            "disclosure_policy",
        ]
        for field in allowed_fields:
            if field in request.data:
                setattr(program, field, request.data[field])
        program.save()
        return Response(ProgramDetailSerializer(program).data)


class ProgramSubmitReviewView(APIView):
    """Submit draft program for platform admin review (draft -> in_review)."""

    permission_classes = [IsCompanyAdmin]

    def post(self, request, slug):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        program = Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        submitted = submit_program_for_review(
            program, actor=request.user, request=request
        )
        return Response(ProgramDetailSerializer(submitted).data)


class ProgramApproveActiveView(APIView):
    """Platform admin approves in_review program into active status."""

    permission_classes = [IsPlatformAdmin]

    def post(self, request, slug):
        program = get_object_or_404(Program, slug=slug)
        serializer = ApproveProgramSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        approved = approve_program_to_active(
            program,
            reason=serializer.validated_data["reason"],
            platform_admin_user=request.user,
            request=request,
        )
        return Response(ProgramDetailSerializer(approved).data)


class ProgramTransitionStatusView(APIView):
    """Company admin transitions program status (pause or close)."""

    permission_classes = [IsCompanyAdmin]

    def post(self, request, slug):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        program = Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        serializer = StatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = transition_program_status(
            program,
            target_status=serializer.validated_data["status"],
            actor=request.user,
            request=request,
        )
        return Response(ProgramDetailSerializer(updated).data)


class ProgramScopesManageView(APIView):
    """Manage scopes for a company program."""

    permission_classes = [IsCompanyMember]

    def _get_program(self, request, slug):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return None
        return Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()

    def get(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )
        scopes = program.scopes.all()
        return Response(ProgramScopeSerializer(scopes, many=True).data)

    def post(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        membership = OrganizationMember.objects.filter(user=request.user).first()
        if membership.role != "company_admin":
            return Response(
                {"detail": "Only company admins can modify scope."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProgramScopeSerializer(
            data=request.data, context={"program": program}
        )
        serializer.is_valid(raise_exception=True)
        scope = serializer.save(program=program)
        return Response(
            ProgramScopeSerializer(scope).data, status=status.HTTP_201_CREATED
        )


class ProgramScopeDetailView(APIView):
    """Delete a scope target."""

    permission_classes = [IsCompanyAdmin]

    def delete(self, request, slug, scope_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        program = Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        scope = program.scopes.filter(id=scope_id).first()
        if not scope:
            return Response(
                {"detail": "Scope not found."}, status=status.HTTP_404_NOT_FOUND
            )

        scope.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProgramRewardsManageView(APIView):
    """Manage reward tiers for a company program."""

    permission_classes = [IsCompanyMember]

    def _get_program(self, request, slug):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return None
        return Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()

    def get(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )
        rewards = program.rewards.all()
        return Response(ProgramRewardSerializer(rewards, many=True).data)

    def post(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        membership = OrganizationMember.objects.filter(user=request.user).first()
        if membership.role != "company_admin":
            return Response(
                {"detail": "Only company admins can modify rewards."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = ProgramRewardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward = serializer.save(program=program)
        return Response(
            ProgramRewardSerializer(reward).data, status=status.HTTP_201_CREATED
        )


class ProgramRewardDetailView(APIView):
    """Delete a reward tier."""

    permission_classes = [IsCompanyAdmin]

    def delete(self, request, slug, reward_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        program = Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        reward = program.rewards.filter(id=reward_id).first()
        if not reward:
            return Response(
                {"detail": "Reward tier not found."}, status=status.HTTP_404_NOT_FOUND
            )

        reward.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProgramInvitesManageView(APIView):
    """Manage researcher invitations for a private program."""

    permission_classes = [IsCompanyMember]

    def _get_program(self, request, slug):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return None
        return Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()

    def get(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )
        invites = program.invites.all()
        return Response(ProgramInviteSerializer(invites, many=True).data)

    def post(self, request, slug):
        program = self._get_program(request, slug)
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        membership = OrganizationMember.objects.filter(user=request.user).first()
        if membership.role != "company_admin":
            return Response(
                {"detail": "Only company admins can invite researchers."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = InviteHunterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        hunter = User.objects.filter(
            email__iexact=serializer.validated_data["email"].strip()
        ).first()
        if not hunter:
            return Response(
                {"detail": "No registered researcher found with that email address."},
                status=status.HTTP_404_NOT_FOUND,
            )

        invite = invite_hunter_to_private_program(
            program, hunter_user=hunter, actor=request.user, request=request
        )
        return Response(
            ProgramInviteSerializer(invite).data, status=status.HTTP_201_CREATED
        )


class ProgramInviteDetailView(APIView):
    """Delete a researcher invitation from a private program."""

    permission_classes = [IsCompanyAdmin]

    def delete(self, request, slug, invite_id):
        membership = OrganizationMember.objects.filter(user=request.user).first()
        if not membership:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        program = Program.objects.filter(
            organization=membership.organization, slug=slug
        ).first()
        if not program:
            return Response(
                {"detail": "Program not found."}, status=status.HTTP_404_NOT_FOUND
            )

        invite = program.invites.filter(id=invite_id).first()
        if not invite:
            return Response(
                {"detail": "Invite not found."}, status=status.HTTP_404_NOT_FOUND
            )

        invite.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

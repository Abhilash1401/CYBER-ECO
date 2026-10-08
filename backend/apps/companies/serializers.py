"""Serializers for Organizations, Members, Domains, and Invitations."""

from rest_framework import serializers

from .models import (
    MemberRole,
    Organization,
    OrganizationMember,
    OrganizationStatus,
    OrganizationVerifiedDomain,
)


class OrganizationVerifiedDomainSerializer(serializers.ModelSerializer):
    """Domain serializer including the DNS TXT verification token for proof setup."""

    class Meta:
        model = OrganizationVerifiedDomain
        fields = [
            "id",
            "domain",
            "verification_token",
            "is_verified",
            "verified_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "verification_token",
            "is_verified",
            "verified_at",
            "created_at",
        ]


class OrganizationMemberSerializer(serializers.ModelSerializer):
    """Organization member serializer."""

    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = OrganizationMember
        fields = ["id", "user_id", "user_email", "role", "created_at"]
        read_only_fields = ["id", "user_id", "user_email", "created_at"]


class OrganizationSerializer(serializers.ModelSerializer):
    """Full organization details for authorized members."""

    verified_domains = OrganizationVerifiedDomainSerializer(many=True, read_only=True)
    members = OrganizationMemberSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "name",
            "website",
            "status",
            "verification_reason",
            "verified_at",
            "created_at",
            "verified_domains",
            "members",
        ]
        read_only_fields = [
            "id",
            "status",
            "verification_reason",
            "verified_at",
            "created_at",
        ]


class CreateOrganizationSerializer(serializers.Serializer):
    """Serializer for initial organization creation."""

    name = serializers.CharField(max_length=255)
    website = serializers.URLField()
    domains = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list,
    )


class ReviewOrganizationSerializer(serializers.Serializer):
    """Serializer for platform admin review of organization."""

    status = serializers.ChoiceField(
        choices=[
            OrganizationStatus.VERIFIED,
            OrganizationStatus.REJECTED,
            OrganizationStatus.SUSPENDED,
        ]
    )
    reason = serializers.CharField(min_length=3)


class InviteMemberSerializer(serializers.Serializer):
    """Serializer for inviting an organization team member."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=MemberRole.choices)


class AcceptInvitationSerializer(serializers.Serializer):
    """Serializer for accepting an invitation via raw token."""

    token = serializers.CharField()


class UpdateMemberRoleSerializer(serializers.Serializer):
    """Serializer for updating a member's role."""

    role = serializers.ChoiceField(choices=MemberRole.choices)

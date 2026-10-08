"""Serializers for Programs, Scopes, Rewards, and Invites."""

from rest_framework import serializers

from .models import (
    Program,
    ProgramInvite,
    ProgramReward,
    ProgramScope,
    ProgramStatus,
    ProgramVisibility,
)
from .services import validate_scope_asset_data


class ProgramScopeSerializer(serializers.ModelSerializer):
    """Scope target serializer with data-only SSRF validation."""

    class Meta:
        model = ProgramScope
        fields = [
            "id",
            "asset_type",
            "asset_value",
            "in_scope",
            "notes",
            "max_severity",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate(self, attrs):
        program = self.context.get("program")
        asset_type = attrs.get("asset_type", getattr(self.instance, "asset_type", None))
        asset_value = attrs.get(
            "asset_value", getattr(self.instance, "asset_value", None)
        )
        in_scope = attrs.get("in_scope", getattr(self.instance, "in_scope", True))

        if program:
            clean_value = validate_scope_asset_data(
                org=program.organization,
                asset_type=asset_type,
                asset_value=asset_value,
                in_scope=in_scope,
            )
            attrs["asset_value"] = clean_value
        return attrs


class ProgramPublicScopeSerializer(serializers.ModelSerializer):
    """Scope target serializer for public consumers (leaks no internal notes)."""

    class Meta:
        model = ProgramScope
        fields = ["id", "asset_type", "asset_value", "in_scope", "max_severity"]


class ProgramRewardSerializer(serializers.ModelSerializer):
    """Reward tier payout serializer."""

    class Meta:
        model = ProgramReward
        fields = ["id", "severity", "min_amount", "max_amount", "currency"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        min_amt = attrs.get("min_amount")
        max_amt = attrs.get("max_amount")
        if min_amt is not None and max_amt is not None and min_amt > max_amt:
            raise serializers.ValidationError(
                {"min_amount": "Minimum reward cannot exceed maximum reward."}
            )
        return attrs


class ProgramInviteSerializer(serializers.ModelSerializer):
    """Private program invitation serializer."""

    hunter_email = serializers.EmailField(source="hunter.email", read_only=True)
    hunter_username = serializers.CharField(
        source="hunter.hunter_profile.username", read_only=True
    )

    class Meta:
        model = ProgramInvite
        fields = ["id", "hunter_email", "hunter_username", "created_at"]
        read_only_fields = ["id", "hunter_email", "hunter_username", "created_at"]


class ProgramDetailSerializer(serializers.ModelSerializer):
    """Complete program details for company management."""

    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    organization_status = serializers.CharField(
        source="organization.status", read_only=True
    )
    scopes = ProgramScopeSerializer(many=True, read_only=True)
    rewards = ProgramRewardSerializer(many=True, read_only=True)
    invites = ProgramInviteSerializer(many=True, read_only=True)

    class Meta:
        model = Program
        fields = [
            "id",
            "organization_name",
            "organization_status",
            "title",
            "slug",
            "description",
            "status",
            "visibility",
            "rules_of_engagement",
            "safe_harbor",
            "disclosure_policy",
            "scopes",
            "rewards",
            "invites",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "status", "created_at", "updated_at"]


class ProgramPublicSerializer(serializers.ModelSerializer):
    """Public discovery program serializer (safe for public listing and hunters)."""

    organization_name = serializers.CharField(
        source="organization.name", read_only=True
    )
    scopes = ProgramPublicScopeSerializer(many=True, read_only=True)
    rewards = ProgramRewardSerializer(many=True, read_only=True)

    class Meta:
        model = Program
        fields = [
            "id",
            "organization_name",
            "title",
            "slug",
            "description",
            "status",
            "visibility",
            "rules_of_engagement",
            "safe_harbor",
            "disclosure_policy",
            "scopes",
            "rewards",
            "created_at",
        ]


class CreateProgramSerializer(serializers.Serializer):
    """Serializer for initial program creation."""

    title = serializers.CharField(max_length=255)
    description = serializers.CharField()
    visibility = serializers.ChoiceField(
        choices=ProgramVisibility.choices, default=ProgramVisibility.PUBLIC
    )


class StatusTransitionSerializer(serializers.Serializer):
    """Serializer for company transitioning program status (pause/close)."""

    status = serializers.ChoiceField(
        choices=[ProgramStatus.ACTIVE, ProgramStatus.PAUSED, ProgramStatus.CLOSED]
    )


class ApproveProgramSerializer(serializers.Serializer):
    """Serializer for platform admin approving a program to active."""

    reason = serializers.CharField(min_length=3)


class InviteHunterSerializer(serializers.Serializer):
    """Serializer for inviting a researcher to a private program."""

    email = serializers.EmailField()

from django.contrib.auth import get_user_model
from rest_framework import serializers
from snippets.models import Snippet, AuditLog, LANGUAGE_CHOICES, STYLE_CHOICES

User = get_user_model()


class SnippetSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source="owner.username")
    highlight = serializers.HyperlinkedIdentityField(
        view_name="snippet-highlight", format="html"
    )

    class Meta:
        model = Snippet
        fields = (
            "url",
            "id",
            "highlight",
            "title",
            "code",
            "linenos",
            "language",
            "style",
            "owner",
        )


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = [
            "url",
            "id",
            "username",
            "email",
            "is_staff",
            "is_active",
            "is_deleted",
            "deleted_at",
        ]
        extra_kwargs = {"url": {"view_name": "user-detail"}}


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = ["id", "user", "model_name", "object_id", "action", "timestamp"]
        read_only_fields = fields

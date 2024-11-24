from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, renderers
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import status

from .models import AuditLog, Snippet
from .permissions import IsOwnerOrReadOnly
from .serializers import AuditLogSerializer, SnippetSerializer, UserSerializer
from .mixins import AuditLogMixin

User = get_user_model()


class SnippetHighlight(AuditLogMixin, generics.GenericAPIView):
    queryset = Snippet.objects.all()
    renderer_classes = (renderers.StaticHTMLRenderer,)

    def get(self, request, *args, **kwargs):
        snippet = self.get_object()
        return Response(snippet.highlighted)


@api_view(["GET"])
def api_root(request, format=None):
    return Response(
        {
            "users": reverse("user-list", request=request, format=format),
            "snippets": reverse("snippet-list", request=request, format=format),
        }
    )


class SnippetList(AuditLogMixin, generics.ListCreateAPIView):
    serializer_class = SnippetSerializer
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def get_queryset(self):
        return Snippet.objects.all()

    def perform_create(self, serializer):
        # Save instance with owner and log the action via the mixin
        serializer.save(owner=self.request.user)
        super().perform_create(serializer)


class SnippetDetail(AuditLogMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )

    def perform_update(self, serializer):
        # Save instance and log the action via the mixin
        serializer.save()
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        # Log the action via the mixin
        super().perform_destroy(instance)


class UserList(generics.ListAPIView):
    """
    List all users. Non-staff users cannot see soft-deleted users.
    Staff users can see deleted users by passing ?include_deleted=true in query params.
    """

    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        include_deleted = self.request.query_params.get("include_deleted", False)

        if user.is_staff and include_deleted:
            return User.objects.all()
        return User.objects.filter(is_deleted=False)


class UserDetail(AuditLogMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or soft delete a user.
    Only staff users can soft delete.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Staff users can optionally include deleted users
        include_deleted = (
            self.request.query_params.get("include_deleted", "false").lower() == "true"
        )

        if self.request.user.is_staff and include_deleted:
            return User.objects.all()
        return User.objects.filter(is_deleted=False)

    def perform_update(self, serializer):
        # Save instance and log the action via the mixin
        serializer.save()
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        """
        Soft delete the user by setting is_deleted=True.
        Only staff users can perform this action.
        """
        if not self.request.user.is_staff:
            raise PermissionDenied("You do not have permission to delete this user.")
        if instance.is_deleted:
            raise PermissionDenied("This user is already soft-deleted.")

        instance.is_deleted = True
        instance.save()
        self.log_action(self.request.user, instance, "destroy")


class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

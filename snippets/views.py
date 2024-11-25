import logging
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, renderers
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.pagination import PageNumberPagination

from .models import AuditLog, Snippet
from .permissions import IsOwnerOrReadOnly, IsStaffOrReadOnly
from .serializers import AuditLogSerializer, SnippetSerializer, UserSerializer
from .mixins import AuditLogMixin

User = get_user_model()
logger = logging.getLogger(__name__)


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
        try:
            instance = serializer.save(owner=self.request.user)
            super().log_action(
                user=self.request.user, instance=instance, action="create"
            )
        except Exception as e:
            logger.error(f"Error creating snippet: {str(e)}")
            raise ValidationError(
                f"An error occurred while creating the snippet: {str(e)}"
            )


class SnippetDetail(AuditLogMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsOwnerOrReadOnly,
    )

    def get_object(self):
        return get_object_or_404(Snippet, pk=self.kwargs["pk"])

    def perform_update(self, serializer):
        try:
            super().perform_update(serializer)
        except Exception as e:
            logger.error(f"Error updating snippet: {str(e)}")
            raise ValidationError(
                f"An error occurred while updating the snippet: {str(e)}"
            )

    def perform_destroy(self, instance):
        try:
            super().perform_destroy(instance)
        except Exception as e:
            logger.error(f"Error deleting snippet: {str(e)}")
            raise ValidationError(
                f"An error occurred while deleting the snippet: {str(e)}"
            )


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class UserList(AuditLogMixin, generics.ListCreateAPIView):
    """
    List all users or create a new user.
    Non-staff users cannot see soft-deleted users.
    Staff users can see deleted users by passing ?include_deleted=true in query params.
    Only staff users can create a new user.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, permissions.IsAdminUser]
    pagination_class = UserPagination

    def get_queryset(self):
        logger.info(
            f"Current user: {self.request.user}, is_staff: {self.request.user.is_staff}"
        )
        logger.info(f"Permission classes applied: {self.permission_classes}")

        include_deleted = self.request.query_params.get(
            "include_deleted", "false"
        ).lower()
        if include_deleted not in ["true", "false"]:
            raise ValidationError(
                "Invalid value for include_deleted. Must be 'true' or 'false'."
            )

        include_deleted = include_deleted == "true"

        if self.request.user.is_staff and include_deleted:
            return User.objects.all()
        return User.objects.filter(is_deleted=False)

    def perform_create(self, serializer):
        logger.info(
            f"Current user: {self.request.user}, is_staff: {self.request.user.is_staff}"
        )
        if not self.request.user.is_staff:
            raise PermissionDenied("You do not have permission to create a new user.")
        try:
            serializer.save()
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise ValidationError(
                f"An error occurred while creating the user: {str(e)}"
            )


class UserDetail(AuditLogMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or soft delete a user.
    Only staff users can soft delete.
    """

    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsStaffOrReadOnly]

    def get_queryset(self):
        try:
            include_deleted = (
                self.request.query_params.get("include_deleted", "false").lower()
                == "true"
                if self.request.user.is_staff
                else False
            )

            if include_deleted:
                return User.objects.all()
            return User.objects.filter(is_deleted=False)

        except Exception as e:
            logger.error(f"Error retrieving users: {str(e)}")
            raise ValidationError(f"Invalid query parameter: {str(e)}")

    def perform_update(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("You do not have permission to update this user.")
        try:
            super().perform_update(serializer)
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise ValidationError(f"An unexpected error occurred: {str(e)}")

    def perform_destroy(self, instance):
        """
        Soft delete the user by setting is_deleted=True.
        Only staff users can perform this action.
        """
        try:
            if not self.request.user.is_staff:
                raise PermissionDenied(
                    "You do not have permission to delete this user."
                )
            if instance.is_deleted:
                raise PermissionDenied("This user is already soft-deleted.")

            instance.is_deleted = True
            instance.save()
            self.log_action(self.request.user, instance, "destroy")
        except PermissionDenied as e:
            logger.error(f"Permission denied: {str(e)}")
            raise PermissionDenied(str(e))
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise ValidationError(f"An unexpected error occurred: {str(e)}")


class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        try:
            return super().get_queryset()
        except Exception as e:
            logger.error(f"Error retrieving audit logs: {str(e)}")
            raise ValidationError(
                f"An error occurred while retrieving audit logs: {str(e)}"
            )

import logging
from snippets.models import AuditLog
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class AuditLogMixin:
    def log_action(self, user, instance, action):
        """
        Log the given action for the instance.
        """
        try:
            AuditLog.objects.create(
                user=user,
                model_name=instance.__class__.__name__,
                object_id=instance.pk,
                action=action,
            )
        except Exception as e:
            logger.error(f"Error logging action: {str(e)}")
            raise ValidationError(
                f"An error occurred while logging the action: {str(e)}"
            )

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle logging.
        """
        action = "create" if obj.pk is None else "update"
        try:
            super().save_model(request, obj, form, change)
            self.log_action(user=request.user, instance=obj, action=action)
        except Exception as e:
            logger.error(f"Error saving model ({action}): {str(e)}")
            raise ValidationError(f"An error occurred while saving the model: {str(e)}")

    def delete_model(self, request, obj):
        """
        Override delete_model to handle logging.
        """
        try:
            self.log_action(user=request.user, instance=obj, action="destroy")
            super().delete_model(request, obj)
        except Exception as e:
            logger.error(f"Error deleting model: {str(e)}")
            raise ValidationError(
                f"An error occurred while deleting the model: {str(e)}"
            )

    def perform_create(self, serializer):
        """
        Override to log create action.
        """
        try:
            instance = serializer.save()
            self.log_action(user=self.request.user, instance=instance, action="create")
            return instance
        except Exception as e:
            logger.error(f"Error creating instance: {str(e)}")
            raise ValidationError(
                f"An error occurred while creating the instance: {str(e)}"
            )

    def perform_update(self, serializer):
        """
        Override to log update action.
        """
        try:
            instance = serializer.save()
            self.log_action(user=self.request.user, instance=instance, action="update")
            return instance
        except Exception as e:
            logger.error(f"Error updating instance: {str(e)}")
            raise ValidationError(
                f"An error occurred while updating the instance: {str(e)}"
            )

    def perform_destroy(self, instance):
        """
        Override to log destroy action.
        """
        try:
            self.log_action(user=self.request.user, instance=instance, action="destroy")
            instance.delete()
        except Exception as e:
            logger.error(f"Error destroying instance: {str(e)}")
            raise ValidationError(
                f"An error occurred while destroying the instance: {str(e)}"
            )

from snippets.models import AuditLog


class AuditLogMixin:
    def log_action(self, user, instance, action):
        """
        Log the given action for the instance.
        """
        print(f"Logging {action} action for {instance} user {user} pk {instance.pk}")
        AuditLog.objects.create(
            user=user,
            model_name=instance.__class__.__name__,
            object_id=instance.pk,
            action=action,
        )

    def save_model(self, request, obj, form, change):
        """
        Override save_model to handle logging.
        """
        action = "create" if obj.pk is None else "update"
        super().save_model(request, obj, form, change)
        self.log_action(user=request.user, instance=obj, action=action)

    def delete_model(self, request, obj):
        """
        Override delete_model to handle logging.
        """
        super().delete_model(request, obj)
        self.log_action(user=request.user, instance=obj, action="destroy")

    def perform_create(self, serializer):
        """
        Override to log create action.
        """
        instance = serializer.save()
        self.log_action(user=self.request.user, instance=instance, action="create")
        return instance

    def perform_update(self, serializer):
        """
        Override to log update action.
        """
        instance = serializer.save()
        self.log_action(user=self.request.user, instance=instance, action="update")
        return instance

    def perform_destroy(self, instance):
        """
        Override to log destroy action.
        """
        self.log_action(user=self.request.user, instance=instance, action="destroy")
        instance.delete()

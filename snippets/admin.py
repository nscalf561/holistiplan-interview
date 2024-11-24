from django.contrib import admin
from .models import AuditLog, Snippet, SoftDeleteUser
from .mixins import AuditLogMixin


class SnippetAdmin(AuditLogMixin, admin.ModelAdmin):
    readonly_fields = ("highlighted",)

    def save_model(self, request, obj, form, change):
        """
        Call the mixin's save_model to handle saving and logging.
        """
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Call the mixin's delete_model to handle deletion and logging.
        """
        super().delete_model(request, obj)


@admin.register(SoftDeleteUser)
class CustomUserAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = ("username", "email", "is_staff", "is_active", "is_deleted")
    list_filter = ("is_staff", "is_active", "is_deleted")
    search_fields = ("username", "email")
    actions = ["soft_delete_users"]

    def save_model(self, request, obj, form, change):
        """
        Use the mixin's save_model logic to handle auditing.
        """
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        """
        Use the mixin's delete_model logic to handle auditing.
        """
        obj.is_deleted = True  # Soft delete instead of hard delete
        obj.save()
        self.log_action(user=request.user, instance=obj, action="destroy")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "model_name", "object_id", "action", "timestamp")
    list_filter = ("model_name", "action", "user")
    search_fields = ("model_name", "object_id", "user__username")


admin.site.register(Snippet, SnippetAdmin)

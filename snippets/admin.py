import logging
from django.contrib import admin
from .models import AuditLog, Snippet, SoftDeleteUser
from .mixins import AuditLogMixin

# Set up logging
logger = logging.getLogger(__name__)


# Snippet Admin Configuration
class SnippetAdmin(AuditLogMixin, admin.ModelAdmin):
    readonly_fields = ("highlighted",)

    def save_model(self, request, obj, form, change):
        """
        Save a snippet and log the action.
        """
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            logger.error(f"Error saving snippet ({obj}): {str(e)}")
            raise

    def delete_model(self, request, obj):
        """
        Delete a snippet and log the action.
        """
        try:
            super().delete_model(request, obj)
        except Exception as e:
            logger.error(f"Error deleting snippet ({obj}): {str(e)}")
            raise


# SoftDeleteUser Admin Configuration
@admin.register(SoftDeleteUser)
class CustomUserAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = ("username", "email", "is_staff", "is_active", "is_deleted")
    list_filter = ("is_staff", "is_active", "is_deleted")
    search_fields = ("username", "email")
    actions = ["soft_delete_users"]

    def save_model(self, request, obj, form, change):
        """
        Save a user and log the action.
        """
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            logger.error(f"Error saving user ({obj}): {str(e)}")
            raise

    def delete_model(self, request, obj):
        """
        Soft delete a user instead of performing a hard delete.
        """
        try:
            obj.is_deleted = True  # Soft delete instead of hard delete
            obj.save()
            self.log_action(user=request.user, instance=obj, action="destroy")
        except Exception as e:
            logger.error(f"Error soft-deleting user ({obj}): {str(e)}")
            raise

    def soft_delete_users(self, request, queryset):
        """
        Admin action to soft delete selected users.
        """
        for user in queryset:
            if not user.is_deleted:
                user.is_deleted = True
                user.save()
                self.log_action(user=request.user, instance=user, action="destroy")

    soft_delete_users.short_description = "Soft delete selected users"


# AuditLog Admin Configuration
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "model_name", "object_id", "action", "timestamp")
    list_filter = ("model_name", "action", "user")
    search_fields = ("model_name", "object_id", "user__username")


# Register Snippet Admin
admin.site.register(Snippet, SnippetAdmin)

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Client, Maintenance, User


# 1. Admin configuration for CLIENT
class ClientInline(admin.StackedInline):
    model = Client
    can_delete = False
    verbose_name_plural = "Client Profile"


# 2. Admin configuration for custom USER
class CustomUserAdmin(UserAdmin):
    # Add Client profile directly on the User page
    inlines = (ClientInline,)

    # Columns displayed in the admin list
    list_display = ("username", "email", "role", "is_staff")

    # Add the `role` field to the edit form
    fieldsets = UserAdmin.fieldsets + (
        ("Additional information", {"fields": ("role",)}),
    )

    # Add the `role` field to the create form
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("role",)}),
    )


# 3. Register models
# Note: Do not call admin.site.unregister(User) here.
admin.site.register(User, CustomUserAdmin)
admin.site.register(Client)
admin.site.register(Maintenance)

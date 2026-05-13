from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Client, Document, Maintenance, Payment, User


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


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("client", "document_type", "uploaded_at")
    list_filter = ("document_type", "uploaded_at")
    search_fields = ("client__first_name", "client__last_name", "client__email")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("reservation", "amount", "method", "payment_date", "reference")
    search_fields = ("reference", "reservation__client__first_name", "reservation__client__last_name")

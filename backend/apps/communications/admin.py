from django.contrib import admin

from .models import Delivery, DeviceRegistration, Notification, PushTest

admin.site.register([Notification, Delivery])


@admin.register(DeviceRegistration)
class DeviceRegistrationAdmin(admin.ModelAdmin):
    # El token push es una credencial de entrega: no se muestra ni se edita.
    exclude = ["push_token"]
    list_display = ["installation_id", "account", "platform", "permission", "is_active", "last_receipt_at"]
    list_filter = ["platform", "permission", "is_active"]
    readonly_fields = ["token_updated_at", "token_invalidated_at", "last_receipt_at", "last_seen_at", "revoked_at"]


@admin.register(PushTest)
class PushTestAdmin(admin.ModelAdmin):
    list_display = ["id", "account", "device", "status", "provider_error_code", "created_at", "confirmed_at"]
    list_filter = ["status"]
    readonly_fields = [field.name for field in PushTest._meta.fields]

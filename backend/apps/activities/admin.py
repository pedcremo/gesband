from django.contrib import admin

from .models import Activity, ActivityPayment, Attendance, Invitation, InvitationResponseEvent, ProgrammeItem

admin.site.register([Activity, ProgrammeItem, Invitation, InvitationResponseEvent, Attendance])


@admin.register(ActivityPayment)
class ActivityPaymentAdmin(admin.ModelAdmin):
    """Solo lectura: los pagos se marcan y anulan desde el panel, que aplica las reglas."""

    list_display = ["invitation", "amount", "paid_at", "paid_by", "voided_at", "voided_by"]
    list_filter = ["voided_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin

from .models import ImportBatch, Instrument, Member, MemberInstrument, Section


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    """Catálogo fijo: se consulta aquí y solo se cambia con una migración."""

    list_display = ["code", "name", "name_ca", "name_en", "order"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ["name", "name_ca", "name_en", "section", "code", "association"]
    list_filter = ["section", "association"]


admin.site.register([Member, MemberInstrument, ImportBatch])

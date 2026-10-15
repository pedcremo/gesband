from django.contrib import admin

from .models import Association, AssociationAccess, AssociationRole


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            # Una banda nueva parte de los instrumentos predefinidos (decisión 0012).
            from apps.members.services import seed_default_instruments

            seed_default_instruments(obj)


admin.site.register([AssociationAccess, AssociationRole])

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class AssociationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.associations"
    verbose_name = _("Asociaciones")

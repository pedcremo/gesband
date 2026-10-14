"""Importes y permisos de pago para las plantillas del panel (decisión 0011)."""

from django import template
from django.utils.formats import number_format
from django.utils.translation import gettext as _

from apps.activities.payments import can_manage_payments as _can_manage_payments

register = template.Library()


@register.filter
def euros(value):
    """Importe con dos decimales y el separador del idioma: «25,00 €» en es/ca.

    La posición del símbolo es traducible («€%(amount)s» en inglés).
    """
    if value in (None, ""):
        return ""
    amount = number_format(value, decimal_pos=2, use_l10n=True)
    return _("%(amount)s €") % {"amount": amount}


@register.simple_tag(takes_context=True)
def can_manage_payments(context, association=None):
    request = context.get("request")
    # Algunas plantillas (403, acceso) no traen una asociación real.
    if not request or not getattr(association, "pk", None):
        return False
    return _can_manage_payments(request.user, association)

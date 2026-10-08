"""Marca y navegación del panel (decisión 0010)."""

from django import template
from django.utils.html import format_html, format_html_join

from apps.associations.branding import brand_tokens
from apps.associations.permissions import permissions_for

register = template.Library()

_CSS_VARIABLES = [
    ("--brand", "brand"),
    ("--brand-ink", "brand_ink"),
    ("--brand-text-light", "brand_text_light"),
    ("--brand-text-dark", "brand_text_dark"),
    ("--brand-edge-light", "brand_edge_light"),
    ("--brand-edge-dark", "brand_edge_dark"),
    ("--accent", "accent"),
    ("--accent-ink", "accent_ink"),
    ("--accent-text-light", "accent_text_light"),
    ("--accent-text-dark", "accent_text_dark"),
]


@register.simple_tag
def brand_attributes(association=None):
    """Atributos de <html>: estilo, modo y colores de la banda, ya legibles."""
    tokens = brand_tokens(association)
    style = format_html_join("", "{}:{};", ((name, tokens[key]) for name, key in _CSS_VARIABLES))
    return format_html(
        'data-style="{}" data-mode="{}" style="{}"', tokens["style"], tokens["mode"], style
    )


@register.simple_tag(takes_context=True)
def panel_permissions(context, association=None):
    """Permisos de quien mira, para mostrar solo las secciones que puede abrir."""
    request = context.get("request")
    if not association or not request or not request.user.is_authenticated:
        return set()
    return set(permissions_for(request.user, association))


@register.filter
def initials(name):
    words = [word for word in str(name or "").replace("-", " ").split() if word[:1].isalpha() and word[:1].isupper()]
    letters = "".join(word[0] for word in words[:2]) or str(name or "G")[:1]
    return letters.upper()

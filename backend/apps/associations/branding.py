"""Colores de marca listos para pintar el panel con cualquier color que elija una banda.

`ANALISIS.md` 3.1 pide colores configurables "con límites que mantengan legibilidad".
Como en la app (decisión 0005), el límite se aplica al pintar y no al elegir: el color
se usa tal cual para fondos, y para texto solo una versión corregida que contraste
4.5:1 con el fondo claro y con el oscuro.
"""

from .models import Association

MIN_TEXT_CONTRAST = 4.5

# Las superficies más exigentes de cada modo: el texto de marca se lee sobre ellas.
LIGHT_SURFACE = "#F4F4F2"
DARK_SURFACE = "#1B1D21"
INK_ON_LIGHT = "#111214"
INK_ON_DARK = "#FFFFFF"


def _rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#" + "".join(f"{round(v):02X}" for v in rgb)


def luminance(color):
    """Luminancia relativa WCAG 2.x."""

    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in _rgb(color))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def ink_on(color):
    """Tinta legible encima de un fondo del color dado."""
    return INK_ON_LIGHT if contrast(color, INK_ON_LIGHT) >= contrast(color, INK_ON_DARK) else INK_ON_DARK


def readable_on(color, background):
    """El color, acercado a negro o a blanco lo justo para leerse sobre `background`."""
    rgb = _rgb(color)
    target = (0, 0, 0) if luminance(background) > 0.5 else (255, 255, 255)
    for step in range(21):
        mixed = tuple(c + (t - c) * step / 20 for c, t in zip(rgb, target))
        candidate = _hex(mixed)
        if contrast(candidate, background) >= MIN_TEXT_CONTRAST:
            return candidate
    return _hex(target)


# Por debajo de este contraste, un relleno de marca se confunde con el fondo (p. ej. una
# banda negra en modo oscuro) y necesita un borde que lo separe.
MIN_SURFACE_CONTRAST = 1.5
DARK_BACKGROUND = "#0F1012"
LIGHT_BACKGROUND = "#F4F4F2"


def edge_for(color, accent, background, line):
    """Borde para un relleno de marca: nada si se distingue del fondo; si no, el acento o la línea."""
    if contrast(color, background) >= MIN_SURFACE_CONTRAST:
        return "transparent"
    return accent if contrast(accent, background) >= MIN_SURFACE_CONTRAST else line


def brand_tokens(association=None):
    """Variables de marca y estilo para el panel; sin asociación, la marca de Gesband."""
    primary = getattr(association, "primary_color", None) or "#1B4965"
    secondary = getattr(association, "secondary_color", None) or "#CAE9FF"
    style = getattr(association, "visual_style", None) or Association.VisualStyle.ESCENARIO
    mode = getattr(association, "color_mode", None) or Association.ColorMode.SYSTEM
    return {
        "style": style,
        "mode": mode,
        "brand": primary.upper(),
        "brand_ink": ink_on(primary),
        "brand_text_light": readable_on(primary, LIGHT_SURFACE),
        "brand_text_dark": readable_on(primary, DARK_SURFACE),
        "accent": secondary.upper(),
        "accent_ink": ink_on(secondary),
        "accent_text_light": readable_on(secondary, LIGHT_SURFACE),
        "accent_text_dark": readable_on(secondary, DARK_SURFACE),
        "brand_edge_light": edge_for(primary, secondary, LIGHT_BACKGROUND, "#DADBD8"),
        "brand_edge_dark": edge_for(primary, secondary, DARK_BACKGROUND, "#2C2F35"),
    }

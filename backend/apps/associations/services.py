"""Imagen de la banda: logo, colores, lema, estilo visual y modo de color (decisión 0010).

La cambian `admin` y `board` (`branding.manage`). La regla vive aquí para que el
panel y una futura API compartan la comprobación.
"""

import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils.translation import gettext as _
from PIL import Image, ImageOps, UnidentifiedImageError

from .models import Association
from .permissions import ensure_permission

LOGO_MAX_BYTES = 2 * 1024 * 1024
LOGO_MAX_PIXELS = 16_000_000
LOGO_MAX_SIDE = 1024
BRANDING_FIELDS = ["motto", "primary_color", "secondary_color", "visual_style", "color_mode"]


def sanitize_logo(upload):
    """Logo verificado por su contenido, sin metadatos, con nombre interno y transparencia."""
    if upload.size > LOGO_MAX_BYTES:
        raise ValidationError(_("El logo supera 2 MB."))
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
        if image.width * image.height > LOGO_MAX_PIXELS:
            raise ValidationError(_("La imagen tiene demasiados píxeles."))
        image = ImageOps.exif_transpose(image).convert("RGBA")
        image.thumbnail((LOGO_MAX_SIDE, LOGO_MAX_SIDE))
        output = io.BytesIO()
        image.save(output, format="WEBP", lossless=True, method=6)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError(_("El fichero no es una imagen válida.")) from exc
    return ContentFile(output.getvalue(), name="logo.webp")


@transaction.atomic
def update_branding(*, actor, association, data, logo=None, remove_logo=False):
    """Guarda la imagen de la banda. `data` trae los campos de `BRANDING_FIELDS` ya limpios."""
    ensure_permission(actor, association, "branding.manage")
    locked = Association.objects.select_for_update().get(pk=association.pk)
    for field in BRANDING_FIELDS:
        if field in data:
            value = data[field]
            setattr(locked, field, value.upper() if field.endswith("_color") else value)
    locked.full_clean(exclude=["logo"])
    old_logo = locked.logo.name
    storage = locked.logo.storage
    if logo is not None:
        locked.logo.save("logo.webp", sanitize_logo(logo), save=False)
    elif remove_logo:
        locked.logo = ""
    locked.save()
    if old_logo and old_logo != locked.logo.name:
        transaction.on_commit(lambda: storage.delete(old_logo))
    return locked

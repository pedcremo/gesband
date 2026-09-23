import io

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.translation import gettext as _
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 20_000_000


def sanitize_member_photo(upload):
    if upload.size > MAX_BYTES:
        raise ValidationError(_("La foto supera 5 MB."))
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
        if image.width * image.height > MAX_PIXELS:
            raise ValidationError(_("La imagen tiene demasiados píxeles."))
        image = ImageOps.exif_transpose(image).convert("RGB")
        image.thumbnail((1600, 1600))
        output = io.BytesIO()
        image.save(output, format="WEBP", quality=88, method=6)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError(_("El fichero no es una imagen válida.")) from exc
    return ContentFile(output.getvalue(), name="photo.webp")

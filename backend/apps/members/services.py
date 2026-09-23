import csv
import hashlib
import io
import re
import unicodedata
from pathlib import Path
from zipfile import BadZipFile

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from .models import ImportBatch, Member

MODEL_COLUMNS = {"external_id", "first_name", "last_name", "national_id", "address", "phone", "email", "kind"}
SURNAME_COLUMNS = {"first_surname", "second_surname"}
ALLOWED_COLUMNS = MODEL_COLUMNS | SURNAME_COLUMNS
MAX_IMPORT_ROWS = 1000
MAX_IMPORT_BYTES = 5 * 1024 * 1024

HEADER_ALIASES = {
    "external_id": {"external id", "id externo", "identificador externo", "codigo", "codi", "numero socio"},
    "first_name": {"first name", "nombre", "nom"},
    "last_name": {"last name", "apellidos", "cognoms"},
    "first_surname": {"first surname", "surname 1", "apellido 1", "primer apellido", "cognom 1", "primer cognom"},
    "second_surname": {"second surname", "surname 2", "apellido 2", "segundo apellido", "cognom 2", "segon cognom"},
    "national_id": {"national id", "dni", "nie", "dni nie", "nif"},
    "address": {"address", "direccion", "adreca"},
    "phone": {"phone", "telefono", "telefon", "movil", "mobil"},
    "email": {"email", "correo", "correo electronico", "correu", "correu electronic"},
    "kind": {"kind", "tipo", "tipo de miembro", "tipus", "tipus de membre"},
}


def _normalize_header(value):
    ascii_value = "".join(
        character
        for character in unicodedata.normalize("NFKD", str(value))
        if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def suggest_import_mapping(headers):
    """Return a conservative mapping for known template and human-readable headers."""
    normalized_aliases = {
        alias: target
        for target, aliases in HEADER_ALIASES.items()
        for alias in aliases | {_normalize_header(target)}
    }
    suggestions = {}
    claimed_targets = set()
    for header in headers:
        target = normalized_aliases.get(_normalize_header(header))
        if target and target not in claimed_targets:
            suggestions[header] = target
            claimed_targets.add(target)
    if "first_surname" in claimed_targets and "last_name" in claimed_targets:
        suggestions = {header: target for header, target in suggestions.items() if target != "last_name"}
    return suggestions


def inspect_import(upload):
    content = upload.read()
    if len(content) > MAX_IMPORT_BYTES:
        raise ValidationError(_("El fichero supera 5 MB."))
    extension = Path(upload.name).suffix.lower()
    if extension == ".csv":
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError(_("El CSV debe estar codificado en UTF-8.")) from exc
        reader = csv.reader(io.StringIO(text))
        headers = [str(value or "").strip() for value in next(reader, [])]
        rows = [dict(zip(headers, values)) for values in reader]
    elif extension == ".xlsx":
        try:
            workbook = load_workbook(io.BytesIO(content), read_only=True, data_only=True, keep_links=False)
            sheet = workbook.active
            iterator = sheet.iter_rows(values_only=True)
            headers = [str(value or "").strip() for value in next(iterator, [])]
            rows = [dict(zip(headers, values)) for values in iterator]
            workbook.close()
        except (BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as exc:
            raise ValidationError(_("El fichero XLSX no es válido.")) from exc
    else:
        raise ValidationError(_("Solo se admiten ficheros CSV o XLSX."))
    if not headers or any(not header for header in headers):
        raise ValidationError(_("Todas las columnas deben tener un nombre."))
    if len(set(headers)) != len(headers):
        raise ValidationError(_("Los nombres de columna no pueden repetirse."))
    if not rows:
        raise ValidationError(_("El fichero no contiene filas de datos."))
    if len(rows) > MAX_IMPORT_ROWS:
        raise ValidationError(_("El fichero supera el límite de %(limit)s filas.") % {"limit": MAX_IMPORT_ROWS})
    return content, hashlib.sha256(content).hexdigest(), headers, rows


def parse_import(upload, mapping):
    content, content_hash, headers, rows = inspect_import(upload)

    invalid_targets = set(mapping.values()) - ALLOWED_COLUMNS
    if invalid_targets:
        raise ValidationError(
            _("Campos de destino no permitidos: %(fields)s.") % {"fields": ", ".join(sorted(invalid_targets))}
        )
    unknown_sources = set(mapping) - set(headers)
    if unknown_sources:
        raise ValidationError(
            _("Columnas de origen desconocidas: %(fields)s.") % {"fields": ", ".join(sorted(unknown_sources))}
        )
    targets = list(mapping.values())
    if len(targets) != len(set(targets)):
        raise ValidationError(_("Cada campo de destino solo puede asignarse una vez."))
    if "first_name" not in targets:
        raise ValidationError(_("Asigna una columna al campo Nombre."))
    uses_combined_surnames = "last_name" in targets
    uses_split_surnames = bool(SURNAME_COLUMNS.intersection(targets))
    if not uses_combined_surnames and "first_surname" not in targets:
        raise ValidationError(_("Asigna Apellidos (juntos) o Primer apellido."))
    if uses_combined_surnames and uses_split_surnames:
        raise ValidationError(_("Usa Apellidos (juntos) o los apellidos separados, pero no ambos."))
    if "second_surname" in targets and "first_surname" not in targets:
        raise ValidationError(_("El Segundo apellido requiere asignar también el Primer apellido."))
    normalized = []
    external_ids = {}
    for row_number, source in enumerate(rows, start=2):
        data = {target: str(source.get(origin) or "").strip() for origin, target in mapping.items()}
        errors = []
        if not data.get("first_name"):
            errors.append(_("Falta el nombre."))
        if uses_split_surnames:
            first_surname = data.pop("first_surname", "")
            second_surname = data.pop("second_surname", "")
            data["last_name"] = " ".join(part for part in (first_surname, second_surname) if part)
            if not first_surname:
                errors.append(_("Falta el primer apellido."))
        elif not data.get("last_name"):
            errors.append(_("Faltan los apellidos."))
        if data.get("kind") and data["kind"] not in Member.Kind.values:
            errors.append(_("Tipo de miembro no válido."))
        external_id = data.get("external_id")
        if external_id:
            if external_id in external_ids:
                errors.append(_("Identificador externo duplicado en el fichero."))
            else:
                external_ids[external_id] = row_number
        normalized.append({"row": row_number, "data": data, "errors": errors})
    return content, content_hash, normalized


@transaction.atomic
def confirm_import(batch):
    locked = ImportBatch.objects.select_for_update().get(pk=batch.pk)
    if locked.status == ImportBatch.Status.CONFIRMED:
        return locked.result
    if locked.status != ImportBatch.Status.PREVIEW:
        raise ValidationError(_("Genera la previsualización antes de confirmar."))
    if not any(not item["errors"] for item in locked.preview):
        raise ValidationError(_("No hay filas válidas que confirmar. Corrige el mapeo o el fichero."))
    created = 0
    updated = 0
    rejected = 0
    report = []
    for item in locked.preview:
        report_item = {**item}
        if item["errors"]:
            rejected += 1
            report_item["action"] = "rejected"
            report.append(report_item)
            continue
        data = item["data"].copy()
        external_id = data.pop("external_id", "")
        defaults = {**data, "kind": data.get("kind") or Member.Kind.MUSICIAN}
        if external_id:
            _member, was_created = Member.objects.update_or_create(
                association=locked.association, external_id=external_id, defaults=defaults
            )
        else:
            Member.objects.create(association=locked.association, **defaults)
            was_created = True
        created += int(was_created)
        updated += int(not was_created)
        report_item["action"] = "created" if was_created else "updated"
        report.append(report_item)
    locked.status = ImportBatch.Status.CONFIRMED
    locked.confirmed_at = timezone.now()
    locked.preview = report
    locked.result = {"created": created, "updated": updated, "rejected": rejected}
    source_name = locked.source_file.name
    source_storage = locked.source_file.storage
    locked.source_file = ""
    locked.save(update_fields=["status", "confirmed_at", "preview", "result", "source_file"])
    if source_name:
        transaction.on_commit(lambda: source_storage.delete(source_name))
    return locked.result

import csv
import hashlib
import io
import logging
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

logger = logging.getLogger(__name__)

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


# --- Mantenimiento de fichas desde el panel y la API (decision 0009) ---------
#
# Las reglas viven aqui y no en las vistas: el panel y la API llaman a estas
# funciones, que comprueban permiso, asociacion y coherencia de las entidades
# relacionadas antes de escribir nada.

MEMBER_EDITABLE_FIELDS = (
    "external_id",
    "first_name",
    "last_name",
    "national_id",
    "address",
    "phone",
    "email",
    "kind",
)


def _ensure_manager(actor, association):
    from apps.associations.permissions import ensure_permission

    ensure_permission(actor, association, "members.manage")


def _clean_instruments(association, instruments, primary_instrument):
    """Instrumentos de la propia asociacion; uno ajeno invalida la peticion."""
    from .models import Instrument

    instruments = list(instruments or [])
    if any(item.association_id != association.id for item in instruments):
        raise ValidationError({"instruments": _("El instrumento pertenece a otra asociación.")})
    if primary_instrument is not None:
        if primary_instrument.association_id != association.id:
            raise ValidationError({"primary_instrument": _("El instrumento pertenece a otra asociación.")})
        if primary_instrument not in instruments:
            instruments.append(primary_instrument)
    # Se vuelven a leer de la base para no fiarse de objetos construidos fuera.
    ids = {item.pk for item in instruments}
    if Instrument.objects.filter(association=association, pk__in=ids).count() != len(ids):
        raise ValidationError({"instruments": _("El instrumento pertenece a otra asociación.")})
    return instruments


def _clean_positions(positions):
    from .models import MemberPosition

    positions = set(positions or [])
    unknown = positions - set(MemberPosition.Position.values)
    if unknown:
        raise ValidationError({"positions": _("Cargo no válido.")})
    return positions


def _check_external_id(association, external_id, exclude_pk=None):
    if not external_id:
        return
    duplicates = Member.objects.filter(association=association, external_id=external_id)
    if exclude_pk:
        duplicates = duplicates.exclude(pk=exclude_pk)
    if duplicates.exists():
        raise ValidationError({"external_id": _("Ya hay otra ficha con este identificador externo en la asociación.")})


def _sync_instruments(member, instruments, primary_instrument):
    from .models import MemberInstrument

    wanted = {item.pk for item in instruments}
    member.member_instruments.exclude(instrument_id__in=wanted).delete()
    # Primero se quita la marca de principal para no chocar con la restriccion
    # de un solo instrumento principal por ficha.
    member.member_instruments.update(is_primary=False)
    existing = set(member.member_instruments.values_list("instrument_id", flat=True))
    MemberInstrument.objects.bulk_create(
        [MemberInstrument(member=member, instrument_id=pk) for pk in wanted - existing]
    )
    if primary_instrument is not None:
        member.member_instruments.filter(instrument=primary_instrument).update(is_primary=True)


def _sync_positions(member, positions):
    from .models import MemberPosition

    member.positions.exclude(position__in=positions).delete()
    existing = set(member.positions.values_list("position", flat=True))
    MemberPosition.objects.bulk_create(
        [MemberPosition(member=member, position=position) for position in positions - existing]
    )


@transaction.atomic
def create_member(*, association, actor, data, instruments=None, primary_instrument=None, positions=None):
    """Alta de una ficha. Nace activa salvo que se indique otro estado."""
    _ensure_manager(actor, association)
    instruments = _clean_instruments(association, instruments, primary_instrument)
    positions = _clean_positions(positions)
    values = {field: data[field] for field in MEMBER_EDITABLE_FIELDS if field in data}
    _check_external_id(association, values.get("external_id"))
    status = data.get("status") or Member.Status.ACTIVE
    member = Member(association=association, created_by=actor, updated_by=actor, status=status, **values)
    if status != Member.Status.ACTIVE:
        member.status_changed_at = timezone.now()
        member.status_changed_by = actor
    member.full_clean(exclude=["photo"])
    member.save()
    _sync_instruments(member, instruments, primary_instrument)
    _sync_positions(member, positions)
    return member


@transaction.atomic
def update_member(*, member, actor, data, instruments=None, primary_instrument=None, positions=None):
    """Edita los datos de la ficha y, si se indican, instrumentos y cargos.

    `instruments` y `positions` en `None` significan «no tocar»; una lista vacía
    los deja vacíos. El estado pasa por `set_member_status` para dejar rastro.
    """
    locked = Member.objects.select_for_update().select_related("association").get(pk=member.pk)
    association = locked.association
    _ensure_manager(actor, association)
    values = {field: data[field] for field in MEMBER_EDITABLE_FIELDS if field in data}
    _check_external_id(association, values.get("external_id"), exclude_pk=locked.pk)
    if instruments is not None or primary_instrument is not None:
        instruments = _clean_instruments(association, instruments, primary_instrument)
    if positions is not None:
        positions = _clean_positions(positions)
    for field, value in values.items():
        setattr(locked, field, value)
    locked.updated_by = actor
    locked.full_clean(exclude=["photo"])
    locked.save()
    if instruments is not None:
        _sync_instruments(locked, instruments, primary_instrument)
    if positions is not None:
        _sync_positions(locked, positions)
    if "status" in data and data["status"] and data["status"] != locked.status:
        locked = set_member_status(member=locked, actor=actor, status=data["status"])
    return locked


@transaction.atomic
def set_member_status(*, member, actor, status):
    """Baja (inactivo) o reactivación. No borra convocatorias ni asistencias.

    Una ficha inactiva deja de aparecer al convocar y al invitar, pero su
    historial sigue consultable. La cuenta vinculada, si la hay, no se toca:
    su acceso se gestiona aparte (`apps.accounts.services`).
    """
    if status not in Member.Status.values:
        raise ValidationError({"status": _("Estado no válido.")})
    locked = Member.objects.select_for_update().select_related("association").get(pk=member.pk)
    _ensure_manager(actor, locked.association)
    if locked.status != status:
        locked.status = status
        locked.status_changed_at = timezone.now()
        locked.status_changed_by = actor
        locked.updated_by = actor
        locked.save(update_fields=["status", "status_changed_at", "status_changed_by", "updated_by", "updated_at"])
    return locked


def member_history(member):
    """Lo que impide borrar una ficha sin perder historial, con su recuento."""
    from apps.activities.models import Invitation
    from apps.polls.models import PollRecipient
    from apps.transport.models import Transport, TransportAssignment

    return {
        "invitations": Invitation.objects.filter(member=member).count(),
        "poll_recipients": PollRecipient.objects.filter(member=member).count(),
        "transport_assignments": TransportAssignment.objects.filter(member=member).count(),
        "driven_transports": Transport.objects.filter(driver=member).count(),
    }


def member_deletion_blockers(member):
    """Motivos por los que la ficha no se puede borrar; vacío si se puede.

    Regla de la decisión 0009: solo se borra una ficha que no ha dejado rastro
    (sin convocatorias ni asistencia, sin encuestas, sin transporte) y que no
    tiene una cuenta vinculada. En los demás casos, la baja es la vía.
    """
    blockers = []
    history = member_history(member)
    if history["invitations"]:
        blockers.append(_("Tiene convocatorias o asistencia registradas."))
    if history["poll_recipients"]:
        blockers.append(_("Ha sido destinataria de encuestas."))
    if history["transport_assignments"] or history["driven_transports"]:
        blockers.append(_("Tiene transporte asignado."))
    if member.account_id:
        blockers.append(_("Tiene una cuenta de acceso vinculada."))
    return blockers


@transaction.atomic
def delete_member(*, member, actor):
    """Borrado físico: solo `admin` y solo si no rompe ningún historial."""
    from apps.associations.permissions import ensure_permission

    locked = Member.objects.select_for_update().select_related("association").get(pk=member.pk)
    ensure_permission(actor, locked.association, "members.delete")
    blockers = member_deletion_blockers(locked)
    if blockers:
        raise ValidationError(
            [_("No se puede borrar esta ficha sin perder su historial. Dala de baja en su lugar.")] + blockers
        )
    photo_name = locked.photo.name
    photo_storage = locked.photo.storage
    member_id = locked.pk
    # Las invitaciones de acceso no aceptadas caen con la ficha (CASCADE).
    locked.delete()
    if photo_name:
        transaction.on_commit(lambda: photo_storage.delete(photo_name))
    logger.info("Ficha %s borrada por la cuenta %s", member_id, getattr(actor, "pk", None))
    return member_id


def _ensure_photo_manager(actor, member):
    """La propia persona o quien gestiona el censo de su asociación."""
    if actor and actor.is_authenticated and member.account_id and member.account_id == actor.pk:
        return
    _ensure_manager(actor, member.association)


@transaction.atomic
def replace_member_photo(*, member, actor, upload):
    from .images import sanitize_member_photo

    locked = Member.objects.select_for_update().select_related("association").get(pk=member.pk)
    _ensure_photo_manager(actor, locked)
    sanitized = sanitize_member_photo(upload)
    old_name = locked.photo.name
    storage = locked.photo.storage
    locked.photo.save("photo.webp", sanitized, save=False)
    locked.updated_by = actor
    locked.save(update_fields=["photo", "updated_by", "updated_at"])
    if old_name:
        transaction.on_commit(lambda: storage.delete(old_name))
    return locked


@transaction.atomic
def delete_member_photo(*, member, actor):
    locked = Member.objects.select_for_update().select_related("association").get(pk=member.pk)
    _ensure_photo_manager(actor, locked)
    if locked.photo:
        locked.photo.delete(save=False)
        locked.updated_by = actor
        locked.save(update_fields=["photo", "updated_by", "updated_at"])
    return locked

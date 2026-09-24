"""Reglas de las encuestas, compartidas por la API y el panel.

El voto unico y el anonimato se comprueban aqui, en el servidor. Ver
`apps/polls/models.py` para la separacion entre participacion y papeletas.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import APIException, ValidationError

from apps.communications.models import Notification
from apps.members.models import Member

from .models import Ballot, Poll, PollOption, PollRecipient

MIN_OPTIONS = 2
MAX_OPTIONS = 20


class AlreadyVoted(APIException):
    """409 con `{"detail": ...}`, como el resto de errores que no son de un campo."""

    status_code = 409
    default_code = "already_voted"


def clean_options(labels):
    """Textos de las opciones sin huecos ni repetidos, en el orden recibido."""
    if not isinstance(labels, (list, tuple)):
        raise ValidationError({"options": _("Las opciones deben ser una lista de textos.")})
    cleaned = []
    for label in labels:
        text = str(label if not isinstance(label, dict) else label.get("label", "")).strip()
        if not text:
            continue
        if len(text) > 200:
            raise ValidationError({"options": _("Cada opción puede tener como mucho 200 caracteres.")})
        if text.casefold() in {existing.casefold() for existing in cleaned}:
            raise ValidationError({"options": _("Hay opciones repetidas.")})
        cleaned.append(text)
    if len(cleaned) < MIN_OPTIONS:
        raise ValidationError({"options": _("Una encuesta necesita al menos dos opciones.")})
    if len(cleaned) > MAX_OPTIONS:
        raise ValidationError({"options": _("Una encuesta puede tener como mucho 20 opciones.")})
    return cleaned


def _clean_text_fields(question, description):
    question = (question or "").strip()
    if not question:
        raise ValidationError({"question": _("Escribe el enunciado de la encuesta.")})
    if len(question) > 300:
        raise ValidationError({"question": _("El enunciado puede tener como mucho 300 caracteres.")})
    return question, (description or "").strip()


def _replace_options(poll, labels):
    poll.options.all().delete()
    PollOption.objects.bulk_create(
        [PollOption(poll=poll, label=label, order=index) for index, label in enumerate(labels)]
    )


@transaction.atomic
def create_poll(*, association, account, question, closes_at, options, description=""):
    question, description = _clean_text_fields(question, description)
    labels = clean_options(options)
    if not closes_at:
        raise ValidationError({"closes_at": _("Indica cuándo se cierra la votación.")})
    poll = Poll.objects.create(
        association=association,
        created_by=account,
        question=question,
        description=description,
        closes_at=closes_at,
    )
    _replace_options(poll, labels)
    return poll


def _lock(poll):
    return Poll.objects.select_for_update().get(pk=poll.pk)


def _require_draft(poll):
    if poll.status != Poll.Status.DRAFT:
        raise ValidationError(_("Solo se puede corregir una encuesta en borrador."))


@transaction.atomic
def update_draft(poll, *, question=None, description=None, closes_at=None, options=None):
    """Corrige un borrador. Una vez abierta, cambiarla alteraria lo ya votado."""
    locked = _lock(poll)
    _require_draft(locked)
    if question is not None or description is not None:
        locked.question, locked.description = _clean_text_fields(
            locked.question if question is None else question,
            locked.description if description is None else description,
        )
    if closes_at is not None:
        locked.closes_at = closes_at
    locked.save()
    if options is not None:
        _replace_options(locked, clean_options(options))
    return locked


@transaction.atomic
def delete_draft(poll):
    """Solo se borra un borrador: una encuesta abierta ya se anuncio y se anula."""
    locked = _lock(poll)
    if locked.status != Poll.Status.DRAFT:
        raise ValidationError(_("Solo se borra un borrador; una encuesta abierta se anula."))
    locked.delete()


BIGINT_MAX = 2**63 - 1


def clean_ids(model, values):
    """Identificadores validos para la clave de `model`; el resto se descarta.

    Un valor mal formado o fuera del rango de la columna no debe llegar a la
    consulta: PostgreSQL responderia con un error en lugar de no encontrar nada.
    """
    pk_field = model._meta.pk
    if isinstance(values, (str, int)):
        values = [values]
    cleaned = set()
    for value in values or ():
        try:
            parsed = pk_field.to_python(value)
        except (DjangoValidationError, TypeError, ValueError):
            continue
        if parsed is None or (isinstance(parsed, int) and not -BIGINT_MAX <= parsed <= BIGINT_MAX):
            continue
        cleaned.add(parsed)
    return cleaned


def eligible_members(association, *, member_ids=(), instrument_ids=(), section_ids=(), all_active_musicians=False):
    """Destinatarios elegidos como en una convocatoria: personas, instrumentos o cuerdas.

    Solo fichas activas de la propia asociacion; un identificador ajeno se
    ignora en lugar de colarse por el filtro.
    """
    from apps.members.models import Instrument, Section

    members = Member.objects.filter(association=association, status=Member.Status.ACTIVE)
    if all_active_musicians:
        return members.filter(kind=Member.Kind.MUSICIAN)
    member_ids = clean_ids(Member, member_ids)
    instrument_ids = clean_ids(Instrument, instrument_ids)
    section_ids = clean_ids(Section, section_ids)
    selection = Q()
    if member_ids:
        selection |= Q(id__in=member_ids)
    if instrument_ids:
        selection |= Q(
            member_instruments__instrument_id__in=instrument_ids,
            member_instruments__instrument__association=association,
        )
    if section_ids:
        selection |= Q(
            member_instruments__instrument__section_id__in=section_ids,
            member_instruments__instrument__section__association=association,
        )
    if not selection:
        return members.none()
    return members.filter(selection).distinct()


@transaction.atomic
def set_recipients(poll, members):
    """Sustituye los destinatarios de un borrador."""
    locked = _lock(poll)
    _require_draft(locked)
    chosen = list(members.filter(association_id=locked.association_id).values_list("id", flat=True))
    locked.recipients.exclude(member_id__in=chosen).delete()
    PollRecipient.objects.bulk_create(
        [PollRecipient(poll=locked, member_id=member_id) for member_id in chosen],
        ignore_conflicts=True,
    )
    return len(chosen)


def notify_poll(poll, event, title, body):
    """Un aviso por destinatario con cuenta; encola solo los que no existian.

    La clave incluye el suceso (`open`, `published`, `cancelled`) para que
    repetir la operacion no vuelva a avisar.
    """
    from apps.communications.tasks import queue_notification_task

    intended = {}
    for recipient in poll.recipients.select_related("member__account"):
        account = recipient.member.account
        if not account:
            continue
        key = f"poll:{poll.pk}:{event}:{account.pk}"
        intended[key] = Notification(
            association_id=poll.association_id,
            account=account,
            poll=poll,
            title=title,
            body=body,
            deep_link=f"gesband://polls/{poll.pk}",
            deduplication_key=key,
        )
    already_sent = set(
        Notification.objects.filter(deduplication_key__in=list(intended)).values_list("deduplication_key", flat=True)
    )
    fresh = [notification for key, notification in intended.items() if key not in already_sent]
    Notification.objects.bulk_create(fresh, ignore_conflicts=True)
    for notification in fresh:
        transaction.on_commit(
            lambda notification_id=notification.id: queue_notification_task.delay(notification_id)
        )
    return len(fresh)


def _closing_line(poll):
    label = _("Se puede votar hasta")
    shown = formats.date_format(timezone.localtime(poll.closes_at), "SHORT_DATETIME_FORMAT")
    return f"{label}: {shown}"


@transaction.atomic
def open_poll(poll, account):
    locked = _lock(poll)
    _require_draft(locked)
    if locked.closes_at <= timezone.now():
        raise ValidationError({"closes_at": _("El cierre de la votación tiene que ser posterior a ahora.")})
    if locked.options.count() < MIN_OPTIONS:
        raise ValidationError({"options": _("Una encuesta necesita al menos dos opciones.")})
    if not locked.recipients.exists():
        raise ValidationError({"recipients": _("Elige a quién se consulta antes de abrir la encuesta.")})
    locked.status = Poll.Status.OPEN
    locked.opened_at = timezone.now()
    locked.save(update_fields=["status", "opened_at", "updated_at"])
    notified = notify_poll(
        locked, "open", _("Nueva encuesta"), f"{locked.question}\n{_closing_line(locked)}"
    )
    return {"poll": locked, "notified": notified}


@transaction.atomic
def cast_vote(poll, account, option_id):
    """Registra un voto y marca la participacion en la misma transaccion.

    El bloqueo sobre la fila de participacion serializa dos intentos
    simultaneos de la misma persona: el segundo encuentra `has_voted` ya cierto.
    Nada de lo que se guarda relaciona la papeleta con quien la emite.
    """
    locked = Poll.objects.select_for_update().get(pk=poll.pk)
    if not locked.is_voting_open:
        raise ValidationError(_("La votación no está abierta."))
    try:
        recipient = PollRecipient.objects.select_for_update().get(poll=locked, member__account=account)
    except PollRecipient.DoesNotExist as exc:
        raise ValidationError(_("No estás entre las personas consultadas.")) from exc
    if recipient.has_voted:
        raise AlreadyVoted(_("Ya has votado en esta encuesta. El voto es anónimo y no se puede cambiar."))
    try:
        option = locked.options.get(pk=option_id)
    except (PollOption.DoesNotExist, ValueError, TypeError, DjangoValidationError) as exc:
        raise ValidationError({"option_id": _("Opción no válida.")}) from exc
    Ballot.objects.create(poll=locked, option=option)
    recipient.has_voted = True
    recipient.save(update_fields=["has_voted"])
    return locked


@transaction.atomic
def publish_results(poll, account):
    """Da por bueno el recuento. Es una accion de la junta, no del reloj."""
    locked = _lock(poll)
    if locked.status == Poll.Status.PUBLISHED:
        raise ValidationError(_("El resultado ya está publicado."))
    if not locked.is_awaiting_publication:
        raise ValidationError(_("Solo se publica el resultado cuando ha terminado el plazo de votación."))
    locked.status = Poll.Status.PUBLISHED
    locked.published_at = timezone.now()
    locked.save(update_fields=["status", "published_at", "updated_at"])
    summary = tally(locked)
    lines = [f"{row['label']}: {row['votes']}" for row in summary["options"]]
    participation = _("Votos emitidos: %(cast)s de %(recipients)s") % {
        "cast": summary["votes_cast"],
        "recipients": summary["recipients"],
    }
    body = "\n".join([locked.question, *lines, participation])
    notified = notify_poll(locked, "published", _("Resultado de la encuesta"), body)
    return {"poll": locked, "notified": notified}


@transaction.atomic
def cancel_poll(poll, account, reason):
    """Anula un borrador o una encuesta abierta.

    Se conservan participacion y papeletas, pero el recuento ya no se muestra a
    nadie: una encuesta anulada no tiene resultado.
    """
    locked = _lock(poll)
    if locked.status == Poll.Status.CANCELLED:
        raise ValidationError(_("La encuesta ya está anulada."))
    if locked.status == Poll.Status.PUBLISHED:
        raise ValidationError(_("Un resultado publicado no se puede anular."))
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": _("Indica el motivo de la anulación.")})
    if len(reason) > 500:
        raise ValidationError({"reason": _("El motivo no puede pasar de 500 caracteres.")})
    was_open = locked.status == Poll.Status.OPEN
    locked.status = Poll.Status.CANCELLED
    locked.cancelled_at = timezone.now()
    locked.cancel_reason = reason
    locked.save(update_fields=["status", "cancelled_at", "cancel_reason", "updated_at"])
    notified = 0
    if was_open:
        reason_label = _("Motivo")
        notified = notify_poll(
            locked, "cancelled", _("Encuesta anulada"), f"{locked.question}\n{reason_label}: {reason}"
        )
    return {"poll": locked, "notified": notified}


def tally(poll):
    """Totales por opcion y participacion. Nunca dice quien eligio que."""
    counts = dict(
        Ballot.objects.filter(poll=poll).values("option_id").annotate(votes=Count("id")).values_list("option_id", "votes")
    )
    options = [
        {"id": option.id, "label": option.label, "votes": counts.get(option.id, 0)}
        for option in poll.options.all()
    ]
    return {
        "options": options,
        "votes_cast": sum(counts.values()),
        "recipients": poll.recipients.count(),
        "voted": poll.recipients.filter(has_voted=True).count(),
    }


def result_visibility(poll, *, is_manager):
    """Que recuento puede verse ahora: `provisional`, `final` o ninguno.

    - Abierta y en plazo: todos ven el provisional, junta y destinatarios.
    - Plazo vencido sin publicar: solo la junta, para revisarlo antes de darlo
      por bueno.
    - Publicada: todos ven el definitivo.
    - Borrador o anulada: nadie.
    """
    if poll.status == Poll.Status.PUBLISHED:
        return "final"
    if poll.is_voting_open:
        return "provisional"
    if poll.is_awaiting_publication and is_manager:
        return "provisional"
    return None

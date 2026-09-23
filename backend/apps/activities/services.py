from django.db import transaction
from django.utils import formats, timezone
from django.utils.translation import gettext as _
from rest_framework.exceptions import ValidationError

from apps.communications.models import Notification

from .models import Activity, Attendance, Invitation, InvitationResponseEvent


@transaction.atomic
def invite_members(activity, members, mandatory=None):
    locked_activity = Activity.objects.select_for_update().get(pk=activity.pk)
    if mandatory is not None and locked_activity.is_mandatory != mandatory:
        locked_activity.is_mandatory = mandatory
        locked_activity.version += 1
        locked_activity.save(update_fields=["is_mandatory", "version", "updated_at"])

    eligible_members = list(
        members.filter(
            association_id=locked_activity.association_id,
            status=members.model.Status.ACTIVE,
            kind=members.model.Kind.MUSICIAN,
        )
    )
    existing_member_ids = set(
        locked_activity.invitations.filter(member__in=eligible_members).values_list("member_id", flat=True)
    )
    new_invitations = [
        Invitation(
            activity=locked_activity,
            member=member,
            activity_version=locked_activity.version,
        )
        for member in eligible_members
        if member.id not in existing_member_ids
    ]
    Invitation.objects.bulk_create(new_invitations, ignore_conflicts=True)
    return {
        "activity": locked_activity,
        "eligible": len(eligible_members),
        "created": len(new_invitations),
        "existing": len(eligible_members) - len(new_invitations),
    }


@transaction.atomic
def respond(invitation, account, response, note=""):
    invitation = Invitation.objects.select_for_update().select_related("member", "activity").get(pk=invitation.pk)
    if invitation.member.account_id != account.id:
        raise ValidationError(_("Solo la persona convocada puede responder."))
    if invitation.activity.status != invitation.activity.Status.PUBLISHED:
        raise ValidationError(_("La actividad no admite respuestas."))
    if invitation.activity.response_deadline and timezone.now() > invitation.activity.response_deadline:
        raise ValidationError(_("El plazo de respuesta ha terminado."))
    if response not in Invitation.Response.values:
        raise ValidationError(_("Respuesta no válida."))
    note = note.strip()
    if invitation.activity.is_mandatory and response == Invitation.Response.DECLINED and not note:
        raise ValidationError(_("Indica el motivo de la ausencia en una actividad obligatoria."))
    invitation.response = response
    invitation.response_note = note
    invitation.responded_at = timezone.now()
    invitation.activity_version = invitation.activity.version
    invitation.save(update_fields=["response", "response_note", "responded_at", "activity_version"])
    InvitationResponseEvent.objects.create(invitation=invitation, response=response, note=note, changed_by=account)
    return invitation


@transaction.atomic
def record_attendance(invitation, account, status, note=""):
    if status not in Attendance.Status.values:
        raise ValidationError(_("Estado de asistencia no válido."))
    attendance, _ = Attendance.objects.select_for_update().get_or_create(invitation=invitation)
    attendance.status = status
    attendance.note = note
    attendance.recorded_by = account
    attendance.recorded_at = timezone.now()
    attendance.save()
    return attendance


def create_activity_notifications(activity, title, body):
    """Crea un aviso por convocatoria y devuelve solo los que no existian ya.

    La clave de deduplicacion incluye la version de la actividad, de modo que un
    mismo cambio no se avisa dos veces aunque la operacion se repita.
    """
    intended = {}
    for invitation in activity.invitations.select_related("member__account"):
        if not invitation.member.account_id:
            continue
        key = f"activity:{activity.pk}:v{activity.version}:{invitation.member.account_id}:{title}"
        intended[key] = Notification(
            association=activity.association,
            account=invitation.member.account,
            activity=activity,
            title=title,
            body=body,
            deduplication_key=key,
        )
    already_sent = set(
        Notification.objects.filter(deduplication_key__in=list(intended)).values_list("deduplication_key", flat=True)
    )
    fresh = [notification for key, notification in intended.items() if key not in already_sent]
    Notification.objects.bulk_create(fresh, ignore_conflicts=True)
    return fresh


def notify_activity(activity, title, body):
    """Avisa a quien esta convocado y encola solo las entregas nuevas.

    Encolar todos los avisos de la actividad volveria a entregar los de cambios
    anteriores: la restriccion de unicidad de `Delivery` no distingue dos filas
    de correo, porque su `device` es nulo.
    """
    from apps.communications.tasks import queue_notification_task

    fresh = create_activity_notifications(activity, title, body)
    for notification in fresh:
        transaction.on_commit(
            lambda notification_id=notification.id: queue_notification_task.delay(notification_id)
        )
    return len(fresh)


# Cambios que se avisan a quien ya esta convocado.
NOTIFIABLE_FIELDS = {
    "title",
    "starts_at",
    "ends_at",
    "meeting_at",
    "location",
    "uniform",
    "response_deadline",
    "is_mandatory",
}

# Cambios que invalidan una respuesta ya dada: quien acepto o rechazo lo hizo
# contando con otra fecha, otra hora de concentracion u otro lugar.
RECONFIRM_FIELDS = {"starts_at", "meeting_at", "location"}


def changed_activity_fields(activity, new_values):
    """Campos de `new_values` cuyo valor difiere del que tiene la actividad."""
    return {field for field, value in new_values.items() if getattr(activity, field) != value}


def describe_activity_changes(activity, fields):
    """Texto con el valor vigente de cada campo cambiado, en el orden de la ficha."""
    labels = [
        ("title", _("Título")),
        ("starts_at", _("Inicio")),
        ("ends_at", _("Final")),
        ("meeting_at", _("Concentración")),
        ("location", _("Lugar")),
        ("uniform", _("Uniforme")),
        ("response_deadline", _("Plazo de respuesta")),
        ("is_mandatory", _("Asistencia obligatoria")),
    ]
    lines = []
    for field, label in labels:
        if field not in fields:
            continue
        value = getattr(activity, field)
        if field == "is_mandatory":
            shown = _("sí") if value else _("no")
        elif value in (None, ""):
            shown = _("sin indicar")
        elif hasattr(value, "tzinfo"):
            shown = formats.date_format(timezone.localtime(value), "SHORT_DATETIME_FORMAT")
        else:
            shown = str(value)
        lines.append(f"{label}: {shown}")
    return "\n".join(lines)


@transaction.atomic
def reset_responses_for_reconfirmation(activity, account):
    """Devuelve a pendiente las respuestas ya dadas, conservando su historial.

    Cada respuesta anulada queda registrada en `InvitationResponseEvent`, que es
    donde vive el historial; la convocatoria solo guarda la respuesta vigente.
    """
    invitations = list(
        activity.invitations.select_for_update().exclude(response=Invitation.Response.PENDING)
    )
    for invitation in invitations:
        InvitationResponseEvent.objects.create(
            invitation=invitation,
            response=Invitation.Response.PENDING,
            note=_("Anulada por un cambio de fecha o lugar."),
            changed_by=account,
        )
        invitation.response = Invitation.Response.PENDING
        invitation.response_note = ""
        invitation.responded_at = None
        invitation.activity_version = activity.version
        invitation.save(
            update_fields=["response", "response_note", "responded_at", "activity_version"]
        )
    return len(invitations)


@transaction.atomic
def announce_activity_change(activity, changed_fields, account):
    """Avisa de un cambio y, si toca fecha o lugar, pide reconfirmar.

    Una actividad que no esta publicada no genera aviso: nadie ha sido convocado
    todavia, asi que no hay nada que rectificar.
    """
    relevant = set(changed_fields) & NOTIFIABLE_FIELDS
    result = {"notified": 0, "reset": 0, "deadline_passed": False, "fields": sorted(relevant)}
    if activity.status != Activity.Status.PUBLISHED or not relevant:
        return result

    if relevant & RECONFIRM_FIELDS:
        result["reset"] = reset_responses_for_reconfirmation(activity, account)
        title = _("Cambio importante: vuelve a confirmar")
        result["deadline_passed"] = bool(
            activity.response_deadline and timezone.now() > activity.response_deadline
        )
    else:
        title = _("Cambio en la convocatoria")

    body = f"{activity.title}\n{describe_activity_changes(activity, relevant)}"
    result["notified"] = notify_activity(activity, title, body)
    return result


@transaction.atomic
def cancel_activity(activity, account, reason):
    """Cancela la actividad y avisa a quien estuviera convocado.

    El motivo es obligatorio: quien tenia la fecha apartada merece saber por que
    deja de estarlo.
    """
    locked = Activity.objects.select_for_update().get(pk=activity.pk)
    if locked.status == Activity.Status.CANCELLED:
        raise ValidationError(_("La actividad ya está cancelada."))
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError({"reason": _("Indica el motivo de la cancelación.")})
    if len(reason) > 500:
        raise ValidationError({"reason": _("El motivo no puede pasar de 500 caracteres.")})
    was_published = locked.status == Activity.Status.PUBLISHED
    locked.status = Activity.Status.CANCELLED
    locked.version += 1
    locked.save(update_fields=["status", "version", "updated_at"])

    notified = 0
    if was_published:
        # La llamada va fuera de la f-string: xgettext no extrae dentro.
        reason_label = _("Motivo")
        body = (
            f"{locked.title}\n"
            f"{describe_activity_changes(locked, {'starts_at'})}\n"
            f"{reason_label}: {reason}"
        )
        notified = notify_activity(locked, _("Actividad cancelada"), body)
    return {"activity": locked, "notified": notified}


@transaction.atomic
def publish_activity(activity, account):
    """Publica la actividad y avisa a quien ya estuviera convocado."""
    locked = Activity.objects.select_for_update().get(pk=activity.pk)
    if locked.status == Activity.Status.CANCELLED:
        raise ValidationError(_("Una actividad cancelada no se puede publicar."))
    locked.status = Activity.Status.PUBLISHED
    locked.version += 1
    locked.save(update_fields=["status", "version", "updated_at"])
    notified = notify_activity(locked, _("Nueva convocatoria"), locked.title)
    return {"activity": locked, "notified": notified}

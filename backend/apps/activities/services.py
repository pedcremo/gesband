from django.db import transaction
from django.utils import timezone
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
    invitations = activity.invitations.select_related("member__account")
    notifications = [
        Notification(
            association=activity.association,
            account=invitation.member.account,
            activity=activity,
            title=title,
            body=body,
            deduplication_key=f"activity:{activity.pk}:v{activity.version}:{invitation.member.account_id}:{title}",
        )
        for invitation in invitations
        if invitation.member.account_id
    ]
    Notification.objects.bulk_create(notifications, ignore_conflicts=True)

"""Lo que se adeuda y se paga a cada músico por las actividades remuneradas.

Reglas de la decisión 0011, reutilizadas por la API, el panel y el admin:

- Devenga el importe una actividad remunerada no cancelada en la que la
  asistencia real de la persona es `present`. La respuesta previa no cuenta.
- Un pago guarda el importe del momento; anularlo no lo borra. Como máximo hay un
  pago vigente por convocatoria (restricción condicional en la base de datos).
- Adeudado = devengado sin pago vigente, con el importe actual de la actividad.
  Un pago vigente que ya no corresponde a un devengo es una incidencia: se
  conserva y se señala, sin restar del adeudado.
- Marcar y anular pagos, y ver lo de todos, corresponde a `admin` y `board`.
"""

from dataclasses import dataclass, field
from decimal import Decimal

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from apps.associations.models import AssociationAccess, AssociationRole

from .models import Activity, ActivityPayment, Attendance, Invitation

# Los cargos de junta (tesorería, etc.) no conceden permisos: solo los roles.
PAYMENT_MANAGER_ROLES = {AssociationRole.Role.ADMIN, AssociationRole.Role.BOARD}

ZERO = Decimal("0.00")


def can_manage_payments(account, association):
    """Si la cuenta puede marcar y anular pagos y ver lo adeudado a todos."""
    if not account or not account.is_authenticated or association is None:
        return False
    if account.is_superuser:
        return True
    return AssociationAccess.objects.filter(
        account=account,
        association=association,
        is_active=True,
        association__is_active=True,
        role_assignments__role__in=PAYMENT_MANAGER_ROLES,
    ).exists()


def ensure_payment_manager(account, association):
    if not can_manage_payments(account, association):
        raise PermissionDenied(_("Solo la administración y la junta pueden gestionar los pagos a músicos."))


def active_payments_prefetch():
    """Prefetch del pago vigente de cada convocatoria en `invitation.active_payments`."""
    return Prefetch(
        "payments",
        queryset=ActivityPayment.objects.filter(voided_at__isnull=True).select_related("paid_by"),
        to_attr="active_payments",
    )


def attendance_status(invitation):
    try:
        return invitation.attendance.status
    except Attendance.DoesNotExist:
        return Attendance.Status.UNRECORDED


def accrues(invitation):
    """Si la convocatoria devenga el importe de la actividad (asistencia real `present`)."""
    activity = invitation.activity
    return (
        activity.is_paid
        and activity.fee_amount is not None
        and activity.status != Activity.Status.CANCELLED
        and attendance_status(invitation) == Attendance.Status.PRESENT
    )


def active_payment(invitation):
    prefetched = getattr(invitation, "active_payments", None)
    if prefetched is not None:
        return prefetched[0] if prefetched else None
    return invitation.payments.filter(voided_at__isnull=True).first()


@dataclass
class PaymentState:
    """Situación económica de una convocatoria.

    `status` es `owed`, `paid` o `None` (no devenga ni tiene pago). `incident`
    señala un pago vigente que ya no corresponde a un devengo.
    """

    invitation: Invitation
    status: str | None
    amount: Decimal | None
    payment: ActivityPayment | None
    incident: bool

    @property
    def can_mark_paid(self):
        return self.status == "owed"


def payment_state(invitation):
    payment = active_payment(invitation)
    accrued = accrues(invitation)
    if payment:
        return PaymentState(invitation, "paid", payment.amount, payment, incident=not accrued)
    if accrued:
        return PaymentState(invitation, "owed", invitation.activity.fee_amount, None, incident=False)
    return PaymentState(invitation, None, None, None, incident=False)


def _check_invitation_scope(invitation, association):
    """La convocatoria debe pertenecer a la asociación desde la que se actúa."""
    if invitation.activity.association_id != association.id:
        raise PermissionDenied(_("La convocatoria pertenece a otra asociación."))


@transaction.atomic
def mark_paid(invitation, account, association):
    """Registra el pago de una convocatoria; devuelve `(pago, creado)`.

    Es idempotente: si ya hay un pago vigente (doble clic, dos personas a la vez)
    devuelve ese pago sin crear otro. El bloqueo de la convocatoria serializa las
    peticiones concurrentes; la restricción de la base de datos es la última red.
    """
    ensure_payment_manager(account, association)
    locked = (
        Invitation.objects.select_for_update(of=("self",))
        .select_related("activity", "attendance")
        .get(pk=invitation.pk)
    )
    _check_invitation_scope(locked, association)
    existing = locked.payments.filter(voided_at__isnull=True).first()
    if existing:
        return existing, False
    if not accrues(locked):
        raise ValidationError(
            _("Solo se puede pagar a quien consta como presente en una actividad remunerada no cancelada.")
        )
    try:
        with transaction.atomic():
            payment = ActivityPayment.objects.create(
                invitation=locked,
                amount=locked.activity.fee_amount,
                paid_at=timezone.now(),
                paid_by=account,
            )
    except IntegrityError:
        return locked.payments.get(voided_at__isnull=True), False
    return payment, True


@transaction.atomic
def mark_all_present_paid(activity, account, association):
    """Paga a todos los presentes de la actividad que aún no tengan pago vigente.

    Devuelve cuántos pagos se han creado. Repetirlo no duplica pagos.
    """
    ensure_payment_manager(account, association)
    if activity.association_id != association.id:
        raise PermissionDenied(_("La actividad pertenece a otra asociación."))
    invitations = list(
        Invitation.objects.select_for_update(of=("self",))
        .filter(activity_id=activity.pk)
        .select_related("activity", "attendance")
        .prefetch_related(active_payments_prefetch())
    )
    created = 0
    for invitation in invitations:
        if invitation.active_payments or not accrues(invitation):
            continue
        _payment, was_created = mark_paid(invitation, account, association)
        created += was_created
    return created


@transaction.atomic
def void_payment(payment, account, association):
    """Anula un pago conservándolo en el historial; devuelve `(pago, anulado_ahora)`."""
    ensure_payment_manager(account, association)
    locked = ActivityPayment.objects.select_for_update(of=("self",)).select_related(
        "invitation__activity"
    ).get(pk=payment.pk)
    _check_invitation_scope(locked.invitation, association)
    if locked.voided_at is not None:
        return locked, False
    locked.voided_at = timezone.now()
    locked.voided_by = account
    locked.save(update_fields=["voided_at", "voided_by"])
    return locked, True


@dataclass
class MemberEarnings:
    owed_total: Decimal = ZERO
    paid_total: Decimal = ZERO
    incidents: int = 0
    items: list = field(default_factory=list)

    @property
    def owed_count(self):
        return sum(1 for item in self.items if item.status == "owed")


def _economic_invitations():
    """Convocatorias con algo que contar: actividad remunerada o algún pago vigente."""
    has_active_payment = Exists(
        ActivityPayment.objects.filter(invitation=OuterRef("pk"), voided_at__isnull=True)
    )
    return (
        Invitation.objects.filter(Q(activity__is_paid=True) | Q(has_active_payment))
        .select_related("activity", "attendance", "member")
        .prefetch_related(active_payments_prefetch())
        .order_by("-activity__starts_at", "activity__title", "id")
    )


def _summarise(states):
    summary = MemberEarnings()
    for state in states:
        if state.status is None:
            continue
        summary.items.append(state)
        if state.status == "owed":
            summary.owed_total += state.amount
        else:
            summary.paid_total += state.amount
        summary.incidents += state.incident
    return summary


def member_earnings(member):
    """Lo devengado, pagado y adeudado a una ficha, de la actividad más reciente a la más antigua."""
    invitations = _economic_invitations().filter(
        member=member,
        activity__association_id=member.association_id,
    )
    return _summarise(payment_state(invitation) for invitation in invitations)


def association_earnings(association):
    """Resumen por ficha de toda la asociación: `[(miembro, MemberEarnings)]`.

    Solo incluye a quien tiene algo adeudado, pagado o una incidencia. Ordena por
    adeudado descendente y después por nombre.
    """
    invitations = _economic_invitations().filter(
        activity__association=association,
        member__association=association,
    )
    by_member = {}
    members = {}
    for invitation in invitations:
        members[invitation.member_id] = invitation.member
        by_member.setdefault(invitation.member_id, []).append(payment_state(invitation))
    rows = []
    for member_id, states in by_member.items():
        summary = _summarise(states)
        if summary.items:
            rows.append((members[member_id], summary))
    rows.sort(key=lambda row: (-row[1].owed_total, row[0].last_name, row[0].first_name))
    return rows


def activity_payment_states(activity):
    """Estado económico de cada convocatoria de la actividad, para el panel."""
    invitations = (
        Invitation.objects.filter(activity=activity)
        .select_related("activity", "attendance", "member")
        .prefetch_related(active_payments_prefetch())
        .order_by("member__last_name", "member__first_name", "id")
    )
    return [payment_state(invitation) for invitation in invitations]

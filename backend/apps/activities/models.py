import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.associations.models import Association
from apps.members.models import Member


class Activity(models.Model):
    class Kind(models.TextChoices):
        REHEARSAL = "rehearsal", _("Ensayo")
        PERFORMANCE = "performance", _("Actuación")

    class Status(models.TextChoices):
        DRAFT = "draft", _("Borrador")
        PUBLISHED = "published", _("Publicada")
        CANCELLED = "cancelled", _("Cancelada")
        COMPLETED = "completed", _("Completada")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="activities", verbose_name=_("asociación")
    )
    kind = models.CharField(_("tipo"), max_length=16, choices=Kind.choices)
    status = models.CharField(_("estado"), max_length=16, choices=Status.choices, default=Status.DRAFT)
    title = models.CharField(_("título"), max_length=180)
    description = models.TextField(_("descripción"), blank=True)
    location = models.CharField(_("lugar"), max_length=255, blank=True)
    starts_at = models.DateTimeField(_("inicio"))
    ends_at = models.DateTimeField(_("final"), null=True, blank=True)
    meeting_at = models.DateTimeField(_("hora de concentración"), null=True, blank=True)
    response_deadline = models.DateTimeField(_("plazo de respuesta"), null=True, blank=True)
    uniform = models.CharField(_("uniforme"), max_length=255, blank=True)
    is_mandatory = models.BooleanField(_("asistencia obligatoria"), default=False)
    # Remuneracion (decision 0011): un importe unico por musico presente.
    is_paid = models.BooleanField(_("remunerada"), default=False)
    fee_amount = models.DecimalField(
        _("importe por músico"), max_digits=8, decimal_places=2, null=True, blank=True
    )
    version = models.PositiveIntegerField(_("versión"), default=1)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_activities",
        verbose_name=_("creada por"),
    )
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("fecha de actualización"), auto_now=True)

    class Meta:
        ordering = ["starts_at", "title"]
        indexes = [models.Index(fields=["association", "starts_at"])]
        constraints = [
            # Remunerada con importe positivo, o no remunerada y sin importe. El
            # `isnull=False` explicito evita que un NULL deje pasar el CHECK.
            models.CheckConstraint(
                condition=(
                    Q(is_paid=True, fee_amount__isnull=False, fee_amount__gt=0)
                    | Q(is_paid=False, fee_amount__isnull=True)
                ),
                name="activity_fee_matches_is_paid",
            )
        ]
        verbose_name = _("actividad")
        verbose_name_plural = _("actividades")

    def clean(self):
        errors = {}
        if self.ends_at and self.ends_at < self.starts_at:
            errors["ends_at"] = _("El final no puede ser anterior al inicio.")
        if self.meeting_at and self.meeting_at > self.starts_at:
            errors["meeting_at"] = _("La concentración no puede ser posterior al inicio.")
        if self.response_deadline and self.response_deadline > self.starts_at:
            errors["response_deadline"] = _("El plazo debe terminar antes de la actividad.")
        fee_error = remuneration_error(self.is_paid, self.fee_amount)
        if fee_error:
            errors["fee_amount"] = fee_error
        elif not self.is_paid:
            # Desmarcar «remunerada» descarta el importe que quedara escrito.
            self.fee_amount = None
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


def remuneration_error(is_paid, fee_amount):
    """Motivo por el que la remuneracion no es valida, o `None`.

    Lo usan el modelo, el formulario del panel y el serializador de la API, para
    que las tres entradas apliquen la misma regla.
    """
    if not is_paid:
        return None
    try:
        positive = fee_amount is not None and Decimal(str(fee_amount)) > 0
    except ArithmeticError:
        positive = False
    if not positive:
        return _("Indica un importe mayor que cero para una actividad remunerada.")
    return None


class ProgrammeItem(models.Model):
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="programme", verbose_name=_("actividad")
    )
    title = models.CharField(_("título"), max_length=180)
    notes = models.TextField(_("notas"), blank=True)
    order = models.PositiveSmallIntegerField(_("orden"), default=0)

    class Meta:
        ordering = ["order", "id"]
        verbose_name = _("elemento de repertorio")
        verbose_name_plural = _("elementos de repertorio")


class Invitation(models.Model):
    class Response(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        ACCEPTED = "accepted", _("Aceptada")
        DECLINED = "declined", _("Rechazada")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="invitations", verbose_name=_("actividad")
    )
    member = models.ForeignKey(
        Member, on_delete=models.PROTECT, related_name="invitations", verbose_name=_("miembro")
    )
    response = models.CharField(
        _("respuesta"), max_length=16, choices=Response.choices, default=Response.PENDING
    )
    response_note = models.CharField(_("nota de respuesta"), max_length=500, blank=True)
    responded_at = models.DateTimeField(_("fecha de respuesta"), null=True, blank=True)
    activity_version = models.PositiveIntegerField(_("versión de la actividad"), default=1)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["activity", "member"], name="unique_activity_invitation")]
        verbose_name = _("convocatoria")
        verbose_name_plural = _("convocatorias")

    def clean(self):
        if self.activity.association_id != self.member.association_id:
            raise ValidationError({"member": _("El miembro pertenece a otra asociación.")})


class InvitationResponseEvent(models.Model):
    invitation = models.ForeignKey(
        Invitation,
        on_delete=models.CASCADE,
        related_name="response_history",
        verbose_name=_("convocatoria"),
    )
    response = models.CharField(_("respuesta"), max_length=16, choices=Invitation.Response.choices)
    note = models.CharField(_("nota"), max_length=500, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="invitation_response_events",
        verbose_name=_("modificada por"),
    )
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("cambio de respuesta")
        verbose_name_plural = _("cambios de respuesta")


class Attendance(models.Model):
    class Status(models.TextChoices):
        UNRECORDED = "unrecorded", _("Sin registrar")
        PRESENT = "present", _("Presente")
        ABSENT = "absent", _("Ausente")
        EXCUSED = "excused", _("Ausencia justificada")

    invitation = models.OneToOneField(
        Invitation, on_delete=models.CASCADE, related_name="attendance", verbose_name=_("convocatoria")
    )
    status = models.CharField(_("estado"), max_length=16, choices=Status.choices, default=Status.UNRECORDED)
    note = models.CharField(_("nota"), max_length=500, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="attendance_records",
        null=True,
        blank=True,
        verbose_name=_("registrada por"),
    )
    recorded_at = models.DateTimeField(_("fecha de registro"), null=True, blank=True)
    updated_at = models.DateTimeField(_("fecha de actualización"), auto_now=True)

    class Meta:
        verbose_name = _("asistencia")
        verbose_name_plural = _("asistencias")


class ActivityPayment(models.Model):
    """Pago registrado por la junta a un musico por una convocatoria.

    No mueve dinero: deja constancia de que se ha pagado. Guarda el importe del
    momento, de modo que cambiar despues el de la actividad no lo altera. Anular
    un pago no lo borra; como maximo hay un pago vigente por convocatoria.
    """

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    invitation = models.ForeignKey(
        Invitation, on_delete=models.PROTECT, related_name="payments", verbose_name=_("convocatoria")
    )
    amount = models.DecimalField(_("importe pagado"), max_digits=8, decimal_places=2)
    paid_at = models.DateTimeField(_("fecha de pago"))
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="activity_payments_recorded",
        verbose_name=_("registrado por"),
    )
    voided_at = models.DateTimeField(_("fecha de anulación"), null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="activity_payments_voided",
        null=True,
        blank=True,
        verbose_name=_("anulado por"),
    )

    class Meta:
        ordering = ["paid_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["invitation"],
                condition=Q(voided_at__isnull=True),
                name="unique_active_payment_per_invitation",
            ),
            models.CheckConstraint(condition=Q(amount__gt=0), name="activity_payment_amount_positive"),
            models.CheckConstraint(
                condition=(
                    Q(voided_at__isnull=True, voided_by__isnull=True)
                    | Q(voided_at__isnull=False, voided_by__isnull=False)
                ),
                name="activity_payment_void_is_complete",
            ),
        ]
        verbose_name = _("pago a músico")
        verbose_name_plural = _("pagos a músicos")

    @property
    def is_active(self):
        return self.voided_at is None

    def __str__(self):
        return f"{self.invitation_id} · {self.amount}"

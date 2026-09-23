import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
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
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return self.title


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

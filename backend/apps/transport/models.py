import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.activities.models import Activity
from apps.members.models import Member


class Transport(models.Model):
    class Kind(models.TextChoices):
        CAR = "car", _("Coche")
        BUS = "bus", _("Autobús")
        OTHER = "other", _("Otro")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    activity = models.ForeignKey(
        Activity, on_delete=models.CASCADE, related_name="transports", verbose_name=_("actividad")
    )
    kind = models.CharField(_("tipo"), max_length=12, choices=Kind.choices)
    label = models.CharField(_("nombre"), max_length=120)
    meeting_point = models.CharField(_("punto de encuentro"), max_length=255, blank=True)
    departure_at = models.DateTimeField(_("hora de salida"), null=True, blank=True)
    capacity = models.PositiveSmallIntegerField(_("plazas"))
    driver = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="driven_transports",
        null=True,
        blank=True,
        verbose_name=_("conductor"),
    )

    class Meta:
        verbose_name = _("transporte")
        verbose_name_plural = _("transportes")

    def clean(self):
        if self.capacity < 1:
            raise ValidationError({"capacity": _("Debe haber al menos una plaza.")})
        if self.driver_id and self.driver.association_id != self.activity.association_id:
            raise ValidationError({"driver": _("El conductor pertenece a otra asociación.")})

    def __str__(self):
        return self.label


class TransportAssignment(models.Model):
    transport = models.ForeignKey(
        Transport, on_delete=models.CASCADE, related_name="assignments", verbose_name=_("transporte")
    )
    member = models.ForeignKey(
        Member,
        on_delete=models.PROTECT,
        related_name="transport_assignments",
        verbose_name=_("miembro"),
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["transport", "member"], name="unique_transport_member"),
            models.UniqueConstraint(fields=["member", "transport"], name="unique_member_transport_pair"),
        ]
        verbose_name = _("asignación de transporte")
        verbose_name_plural = _("asignaciones de transporte")

    def clean(self):
        if self.member.association_id != self.transport.activity.association_id:
            raise ValidationError({"member": _("El miembro pertenece a otra asociación.")})
        other = TransportAssignment.objects.filter(
            member=self.member, transport__activity=self.transport.activity
        ).exclude(pk=self.pk)
        if other.exists():
            raise ValidationError({"member": _("El miembro ya tiene transporte para esta actividad.")})
        if self.transport_id and self.transport.assignments.exclude(pk=self.pk).count() >= self.transport.capacity:
            raise ValidationError({"transport": _("No quedan plazas disponibles.")})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

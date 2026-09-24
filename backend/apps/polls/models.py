"""Encuestas a los miembros (ANALISIS.md 3.7).

El anonimato se sostiene en el esquema, no en la disciplina de quien consulta:
`PollRecipient` dice quien ha votado y `Ballot` que se ha votado, y ninguna
columna permite ir de una tabla a la otra. Por eso `Ballot` no tiene cuenta,
miembro, fecha ni identificador correlativo: con una fecha o un entero
creciente bastaria ordenar ambas tablas para emparejarlas.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.associations.models import Association
from apps.members.models import Member


class Poll(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Borrador")
        OPEN = "open", _("Abierta")
        PUBLISHED = "published", _("Resultado publicado")
        CANCELLED = "cancelled", _("Anulada")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="polls", verbose_name=_("asociación")
    )
    question = models.CharField(_("enunciado"), max_length=300)
    description = models.TextField(_("descripción"), blank=True)
    status = models.CharField(_("estado"), max_length=16, choices=Status.choices, default=Status.DRAFT)
    closes_at = models.DateTimeField(_("cierre de la votación"))
    opened_at = models.DateTimeField(_("fecha de apertura"), null=True, blank=True)
    published_at = models.DateTimeField(_("fecha de publicación"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("fecha de anulación"), null=True, blank=True)
    cancel_reason = models.CharField(_("motivo de la anulación"), max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_polls",
        verbose_name=_("creada por"),
    )
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    updated_at = models.DateTimeField(_("fecha de actualización"), auto_now=True)

    class Meta:
        ordering = ["-closes_at", "question"]
        indexes = [models.Index(fields=["association", "status", "closes_at"])]
        verbose_name = _("encuesta")
        verbose_name_plural = _("encuestas")

    def __str__(self):
        return self.question

    @property
    def is_voting_open(self):
        return self.status == self.Status.OPEN and timezone.now() < self.closes_at

    @property
    def is_awaiting_publication(self):
        """Abierta y con el plazo vencido: ya no se vota y el recuento espera a la junta."""
        return self.status == self.Status.OPEN and timezone.now() >= self.closes_at


class PollOption(models.Model):
    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options", verbose_name=_("encuesta"))
    label = models.CharField(_("texto"), max_length=200)
    order = models.PositiveSmallIntegerField(_("orden"), default=0)

    class Meta:
        ordering = ["order", "label"]
        constraints = [models.UniqueConstraint(fields=["poll", "label"], name="unique_poll_option_label")]
        verbose_name = _("opción")
        verbose_name_plural = _("opciones")

    def __str__(self):
        return self.label


class PollRecipient(models.Model):
    """Registro de participacion: a quien se consulta y si ya ha votado.

    Solo un booleano. La hora del voto permitiria cruzarla con el orden en que
    se insertan las papeletas.
    """

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="recipients", verbose_name=_("encuesta"))
    member = models.ForeignKey(
        Member, on_delete=models.PROTECT, related_name="poll_recipients", verbose_name=_("miembro")
    )
    has_voted = models.BooleanField(_("ha votado"), default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["poll", "member"], name="unique_poll_recipient")]
        verbose_name = _("destinatario de encuesta")
        verbose_name_plural = _("destinatarios de encuesta")


class Ballot(models.Model):
    """Papeleta. Sin votante, sin fecha y con una clave aleatoria."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="ballots", verbose_name=_("encuesta"))
    # CASCADE: las opciones solo se sustituyen en borrador, cuando aun no hay
    # papeletas; con PROTECT, borrar una encuesta votada o su asociacion fallaria.
    option = models.ForeignKey(
        PollOption, on_delete=models.CASCADE, related_name="ballots", verbose_name=_("opción")
    )

    class Meta:
        verbose_name = _("papeleta")
        verbose_name_plural = _("papeletas")

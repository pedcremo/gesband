import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.activities.models import Activity
from apps.associations.models import Association


class Notification(models.Model):
    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="notifications", verbose_name=_("asociación")
    )
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("cuenta"),
    )
    activity = models.ForeignKey(
        Activity,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("actividad"),
    )
    poll = models.ForeignKey(
        "polls.Poll",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("encuesta"),
    )
    title = models.CharField(_("título"), max_length=180)
    body = models.TextField(_("contenido"))
    deep_link = models.CharField(_("enlace interno"), max_length=255, blank=True)
    deduplication_key = models.CharField(_("clave de deduplicación"), max_length=255, unique=True)
    read_at = models.DateTimeField(_("fecha de lectura"), null=True, blank=True)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["account", "read_at", "created_at"])]
        verbose_name = _("aviso")
        verbose_name_plural = _("avisos")


class DeviceRegistration(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "android", _("Android")
        IOS = "ios", _("iOS")

    class Permission(models.TextChoices):
        UNKNOWN = "unknown", _("Desconocido")
        GRANTED = "granted", _("Concedido")
        DENIED = "denied", _("Denegado")
        PROVISIONAL = "provisional", _("Provisional")
        DISABLED = "disabled", _("Desactivado")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name=_("cuenta"),
    )
    installation_id = models.UUIDField(_("identificador de instalación"), default=uuid.uuid4, unique=True)
    platform = models.CharField(_("plataforma"), max_length=12, choices=Platform.choices)
    push_token = models.CharField(_("token push"), max_length=512)
    permission = models.CharField(
        _("permiso"), max_length=16, choices=Permission.choices, default=Permission.UNKNOWN
    )
    last_receipt_at = models.DateTimeField(_("última recepción"), null=True, blank=True)
    last_seen_at = models.DateTimeField(_("última conexión"), auto_now=True)
    is_active = models.BooleanField(_("activo"), default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["account", "push_token"], name="unique_account_push_token")]
        verbose_name = _("dispositivo registrado")
        verbose_name_plural = _("dispositivos registrados")


class Delivery(models.Model):
    class Channel(models.TextChoices):
        PUSH = "push", _("Push")
        EMAIL = "email", _("Correo")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pendiente")
        SENT = "sent", _("Enviada")
        FAILED = "failed", _("Fallida")

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="deliveries", verbose_name=_("aviso")
    )
    device = models.ForeignKey(
        DeviceRegistration,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deliveries",
        verbose_name=_("dispositivo"),
    )
    channel = models.CharField(_("canal"), max_length=12, choices=Channel.choices)
    status = models.CharField(_("estado"), max_length=12, choices=Status.choices, default=Status.PENDING)
    provider_id = models.CharField(_("identificador del proveedor"), max_length=255, blank=True)
    error = models.TextField(_("error"), blank=True)
    attempts = models.PositiveSmallIntegerField(_("intentos"), default=0)
    last_attempt_at = models.DateTimeField(_("último intento"), null=True, blank=True)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["notification", "device", "channel"], name="unique_notification_device_channel")]
        verbose_name = _("entrega de aviso")
        verbose_name_plural = _("entregas de avisos")

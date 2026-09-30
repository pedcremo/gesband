import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
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
    """Una instalacion de la app vinculada a una cuenta.

    Permiso, token y recepcion son tres hechos distintos (MUST-NOTIF-01): el
    permiso lo observa la app, el token vigente lo guarda el servidor y la
    recepcion solo la demuestra una prueba confirmada despues del ultimo cambio
    de token.
    """

    class Platform(models.TextChoices):
        ANDROID = "android", _("Android")
        IOS = "ios", _("iOS")

    class Permission(models.TextChoices):
        NOT_DETERMINED = "not_determined", _("Sin decidir")
        PROVISIONAL = "provisional", _("Provisional")
        GRANTED = "granted", _("Concedido")
        DENIED = "denied", _("Denegado")
        RESTRICTED = "restricted", _("Restringido")
        UNKNOWN = "unknown", _("Desconocido")

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="devices",
        verbose_name=_("cuenta"),
    )
    installation_id = models.UUIDField(_("identificador de instalación"), default=uuid.uuid4, unique=True)
    platform = models.CharField(_("plataforma"), max_length=12, choices=Platform.choices)
    push_token = models.CharField(_("token push"), max_length=4096)
    permission = models.CharField(
        _("permiso"), max_length=16, choices=Permission.choices, default=Permission.UNKNOWN
    )
    app_version = models.CharField(_("versión de la app"), max_length=50, blank=True)
    locale = models.CharField(_("idioma"), max_length=35, blank=True)
    token_updated_at = models.DateTimeField(_("último cambio de token"), default=timezone.now)
    token_invalidated_at = models.DateTimeField(_("token rechazado por el proveedor"), null=True, blank=True)
    last_receipt_at = models.DateTimeField(_("última recepción confirmada"), null=True, blank=True)
    last_seen_at = models.DateTimeField(_("última conexión"), auto_now=True)
    is_active = models.BooleanField(_("activo"), default=True)
    revoked_at = models.DateTimeField(_("fecha de revocación"), null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["account", "push_token"], name="unique_account_push_token")]
        verbose_name = _("dispositivo registrado")
        verbose_name_plural = _("dispositivos registrados")

    def __str__(self):
        return f"{self.get_platform_display()} {self.installation_id}"

    @property
    def token_registered(self):
        return self.is_active and bool(self.push_token) and self.token_invalidated_at is None

    @property
    def receipt_confirmed(self):
        return self.last_receipt_at is not None and self.last_receipt_at >= self.token_updated_at

    @property
    def can_receive_push(self):
        return self.token_registered and self.permission in {self.Permission.GRANTED, self.Permission.PROVISIONAL}


class PushTest(models.Model):
    """Un envio de prueba a una instalacion concreta y lo que se sabe de el."""

    class Presentation(models.TextChoices):
        FOREGROUND = "foreground", _("Primer plano")
        BACKGROUND = "background", _("Segundo plano")

    class Status(models.TextChoices):
        QUEUED = "queued", _("En cola")
        PROVIDER_ACCEPTED = "provider_accepted", _("Aceptada por el proveedor")
        PROVIDER_FAILED = "provider_failed", _("Rechazada por el proveedor")
        RECEIVED_FOREGROUND = "received_foreground", _("Recibida en primer plano")
        OPENED_FROM_BACKGROUND = "opened_from_background", _("Abierta desde segundo plano")
        EXPIRED = "expired", _("Caducada")

    CONFIRMED = {Status.RECEIVED_FOREGROUND, Status.OPENED_FROM_BACKGROUND}

    id = models.UUIDField(_("identificador"), primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        DeviceRegistration, on_delete=models.CASCADE, related_name="push_tests", verbose_name=_("dispositivo")
    )
    # La cuenta que la pidio: la instalacion puede pasar despues a otra cuenta.
    account = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_tests", verbose_name=_("cuenta")
    )
    expected_presentation = models.CharField(
        _("presentación esperada"), max_length=12, choices=Presentation.choices
    )
    status = models.CharField(_("estado"), max_length=24, choices=Status.choices, default=Status.QUEUED)
    provider_message_id = models.CharField(_("identificador del proveedor"), max_length=255, blank=True)
    provider_error_code = models.CharField(_("código de error del proveedor"), max_length=64, blank=True)
    reported_at = models.DateTimeField(_("momento indicado por la app"), null=True, blank=True)
    confirmed_at = models.DateTimeField(_("fecha de confirmación"), null=True, blank=True)
    created_at = models.DateTimeField(_("fecha de creación"), auto_now_add=True)
    expires_at = models.DateTimeField(_("caducidad"))

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("prueba de aviso")
        verbose_name_plural = _("pruebas de avisos")


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

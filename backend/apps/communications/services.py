from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from .models import Delivery, DeviceRegistration, Notification, PushTest
from .push import InvalidTokenError, PushError, PushMessage, TemporaryPushError, get_push_provider

Permission = DeviceRegistration.Permission


class PushTestConflict(Exception):
    """La prueba no se puede pedir o confirmar en el estado actual."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


@transaction.atomic
def register_device(*, account, installation_id, platform, push_token, permission, app_version="", locale=""):
    """Registra o actualiza una instalacion y la deja vinculada solo a `account`.

    Si la instalacion o su token estaban vinculados a otra cuenta, ese vinculo
    desaparece: tras un cambio de cuenta no pueden llegar avisos de la anterior.
    Devuelve `(device, created)`.
    """
    stale = DeviceRegistration.objects.filter(push_token=push_token).exclude(installation_id=installation_id)
    stale.delete()
    device = DeviceRegistration.objects.select_for_update().filter(installation_id=installation_id).first()
    created = device is None
    if created:
        device = DeviceRegistration(installation_id=installation_id)
    token_changed = created or device.push_token != push_token or device.account_id != account.pk
    device.account = account
    device.platform = platform
    device.push_token = push_token
    device.permission = permission
    device.app_version = app_version
    device.locale = locale
    device.is_active = True
    device.revoked_at = None
    if token_changed:
        _renew_token(device)
    device.save()
    return device, created


@transaction.atomic
def update_device(device, *, push_token=None, permission=None, app_version=None, locale=None):
    if push_token is not None and push_token != device.push_token:
        DeviceRegistration.objects.filter(push_token=push_token).exclude(pk=device.pk).delete()
        device.push_token = push_token
        _renew_token(device)
    if permission is not None:
        device.permission = permission
    if app_version is not None:
        device.app_version = app_version
    if locale is not None:
        device.locale = locale
    device.save()
    return device


def _renew_token(device):
    # Un token nuevo no esta demostrado: la recepcion confirmada deja de valer.
    device.token_updated_at = timezone.now()
    device.token_invalidated_at = None


def revoke_device(device):
    if device.is_active:
        device.is_active = False
        device.revoked_at = timezone.now()
        device.save(update_fields=["is_active", "revoked_at", "last_seen_at"])
    return device


def revoke_account_devices(account):
    return DeviceRegistration.objects.filter(account=account, is_active=True).update(
        is_active=False, revoked_at=timezone.now()
    )


def notification_capability(device):
    """Estado de MUST-NOTIF-01 y el siguiente paso que debe proponer la app.

    Permiso, registro y recepcion se informan por separado; ninguno se deduce
    de los otros.
    """
    if device.permission in {Permission.NOT_DETERMINED, Permission.UNKNOWN}:
        action = "request_system_permission"
    elif device.permission in {Permission.DENIED, Permission.RESTRICTED}:
        # El sistema ya no vuelve a mostrar la solicitud: solo queda ajustes.
        action = "open_system_settings"
    elif not device.token_registered:
        action = "register_token"
    elif not device.receipt_confirmed:
        action = "run_receive_test"
    elif device.permission == Permission.PROVISIONAL:
        # Llega, pero en silencio: se propone pedir el permiso pleno.
        action = "request_system_permission"
    else:
        action = "none"
    return {
        "device_id": device.pk,
        "permission_state": device.permission,
        "token_registered": device.token_registered,
        "receipt_confirmed": device.receipt_confirmed,
        "last_receipt_confirmed_at": device.last_receipt_at if device.receipt_confirmed else None,
        "action_required": action,
        "checked_at": timezone.now(),
    }


@transaction.atomic
def request_push_test(device, *, account, expected_presentation):
    if not device.is_active:
        raise PushTestConflict("device_revoked", _("Este dispositivo ya no está registrado."))
    if not device.can_receive_push:
        raise PushTestConflict(
            "push_not_available",
            _("Activa las notificaciones y registra el dispositivo antes de probar."),
        )
    test = PushTest.objects.create(
        device=device,
        account=account,
        expected_presentation=expected_presentation,
        expires_at=timezone.now() + timedelta(minutes=settings.PUSH_TEST_TTL_MINUTES),
    )
    from .tasks import send_push_test_task

    transaction.on_commit(lambda: send_push_test_task.delay(str(test.pk)))
    return test


def expire_if_due(test):
    open_statuses = {PushTest.Status.QUEUED, PushTest.Status.PROVIDER_ACCEPTED}
    if test.status in open_statuses and timezone.now() >= test.expires_at:
        test.status = PushTest.Status.EXPIRED
        test.save(update_fields=["status"])
    return test


def send_push_test(test):
    device = test.device
    if test.status != PushTest.Status.QUEUED:
        return test.status
    if device.account_id != test.account_id or not device.can_receive_push:
        return _fail_test(test, "device_revoked")
    with translation.override(_language_for(device)):
        message = PushMessage(
            token=device.push_token,
            title=_("Prueba de avisos de Gesband"),
            body=_("Si ves este aviso, las notificaciones funcionan en este dispositivo."),
            data={"kind": "notification_test", "push_test_id": str(test.pk)},
        )
    try:
        test.provider_message_id = get_push_provider().send(message)[:255]
    except PushError as exc:
        _handle_token_error(device, exc)
        return _fail_test(test, exc.code)
    test.status = PushTest.Status.PROVIDER_ACCEPTED
    test.save(update_fields=["status", "provider_message_id"])
    return test.status


def _fail_test(test, code):
    test.status = PushTest.Status.PROVIDER_FAILED
    test.provider_error_code = code[:64]
    test.save(update_fields=["status", "provider_error_code"])
    return test.status


@transaction.atomic
def confirm_push_test(test, *, event, occurred_at):
    test = PushTest.objects.select_for_update().select_related("device").get(pk=test.pk)
    if test.status in PushTest.CONFIRMED:
        # Repetir la confirmacion (primer plano y luego al abrir) no la cambia.
        return test
    expire_if_due(test)
    if test.status == PushTest.Status.EXPIRED:
        raise PushTestConflict("push_test_expired", _("La prueba ha caducado; pide otra."))
    if test.device.account_id != test.account_id or not test.device.is_active:
        raise PushTestConflict("device_revoked", _("Este dispositivo ya no está registrado."))
    now = timezone.now()
    test.status = event
    test.reported_at = occurred_at
    test.confirmed_at = now
    test.save(update_fields=["status", "reported_at", "confirmed_at"])
    DeviceRegistration.objects.filter(pk=test.device_id).update(last_receipt_at=now, last_seen_at=now)
    return test


@transaction.atomic
def queue_notification_deliveries(notification):
    devices = DeviceRegistration.objects.filter(
        account=notification.account,
        is_active=True,
        token_invalidated_at__isnull=True,
        permission__in=[Permission.GRANTED, Permission.PROVISIONAL],
    )
    deliveries = [Delivery(notification=notification, device=device, channel=Delivery.Channel.PUSH) for device in devices]
    if notification.account.email:
        deliveries.append(Delivery(notification=notification, channel=Delivery.Channel.EMAIL))
    Delivery.objects.bulk_create(deliveries, ignore_conflicts=True)
    _dispatch_pending(notification)
    return len(deliveries)


def _dispatch_pending(notification):
    """Encola el envio de las entregas que siguen pendientes.

    `bulk_create` con `ignore_conflicts` no devuelve las claves, asi que se
    releen; quedarse con las pendientes evita reenviar una entrega ya resuelta.
    """
    from .tasks import deliver_email_task, deliver_push_task

    tasks = {Delivery.Channel.EMAIL: deliver_email_task, Delivery.Channel.PUSH: deliver_push_task}
    pending = Delivery.objects.filter(notification=notification, status=Delivery.Status.PENDING)
    rows = list(pending.values_list("id", "channel"))
    for delivery_id, channel in rows:
        task = tasks[channel]
        transaction.on_commit(lambda task=task, delivery_id=delivery_id: task.delay(delivery_id))
    return len(rows)


def deliver_email(delivery):
    if delivery.status == Delivery.Status.SENT:
        return delivery.status
    notification = delivery.notification
    try:
        send_mail(notification.title, notification.body, settings.DEFAULT_FROM_EMAIL, [notification.account.email], fail_silently=False)
        delivery.status = Delivery.Status.SENT
        delivery.error = ""
    except Exception as exc:
        delivery.status = Delivery.Status.FAILED
        delivery.error = str(exc)[:2000]
    delivery.attempts += 1
    delivery.last_attempt_at = timezone.now()
    delivery.save(update_fields=["status", "error", "attempts", "last_attempt_at"])
    return delivery.status


def push_data(notification):
    """Datos del aviso push: identificadores para abrir la pantalla, nada privado."""
    if notification.poll_id:
        kind, deep_link = "poll", notification.deep_link or f"gesband://polls/{notification.poll_id}"
    elif notification.activity_id:
        kind, deep_link = "activity", notification.deep_link or f"gesband://activities/{notification.activity_id}"
    else:
        kind, deep_link = "notification", notification.deep_link
    data = {
        "kind": kind,
        "notification_id": str(notification.pk),
        "association_id": str(notification.association_id),
        "activity_id": str(notification.activity_id) if notification.activity_id else None,
        "poll_id": str(notification.poll_id) if notification.poll_id else None,
        "deep_link": deep_link or None,
    }
    return {key: value for key, value in data.items() if value}


def deliver_push(delivery, *, final_attempt=True):
    """Envia una entrega push. Lanza `TemporaryPushError` si conviene reintentar.

    Con `final_attempt` el fallo temporal queda registrado como definitivo en
    vez de relanzarse.
    """
    if delivery.status == Delivery.Status.SENT:
        return delivery.status
    notification = delivery.notification
    device = delivery.device
    delivery.attempts += 1
    delivery.last_attempt_at = timezone.now()
    fields = ["status", "error", "attempts", "last_attempt_at", "provider_id"]
    # El dispositivo pudo cambiar de cuenta o revocarse despues de crear la entrega.
    if device is None or device.account_id != notification.account_id or not device.can_receive_push:
        delivery.status = Delivery.Status.FAILED
        delivery.error = "device_revoked"
        delivery.save(update_fields=fields)
        return delivery.status
    message = PushMessage(token=device.push_token, title=notification.title, body=notification.body, data=push_data(notification))
    try:
        delivery.provider_id = get_push_provider().send(message)[:255]
    except PushError as exc:
        _handle_token_error(device, exc)
        delivery.status = Delivery.Status.FAILED
        delivery.error = exc.code
        delivery.save(update_fields=fields)
        if isinstance(exc, TemporaryPushError) and not final_attempt:
            raise
        return delivery.status
    delivery.status = Delivery.Status.SENT
    delivery.error = ""
    delivery.save(update_fields=fields)
    return delivery.status


def _handle_token_error(device, exc):
    if isinstance(exc, InvalidTokenError):
        DeviceRegistration.objects.filter(pk=device.pk, push_token=device.push_token).update(
            token_invalidated_at=timezone.now()
        )


def _language_code(locale):
    code = (locale or "").split("-")[0].lower()
    available = {language for language, _name in settings.LANGUAGES}
    return code if code in available else settings.LANGUAGE_CODE


def _language_for(device):
    return _language_code(device.locale)


def recipient_languages(account_ids):
    """Idioma de cada cuenta: el de su instalacion activa mas reciente.

    Es el unico idioma que la persona ha elegido de forma explicita (en la app).
    Sin instalacion se usa el idioma por omision de la plataforma.
    """
    languages = {}
    devices = (
        DeviceRegistration.objects.filter(account_id__in=set(account_ids), is_active=True)
        .exclude(locale="")
        .order_by("account_id", "-last_seen_at")
        .values_list("account_id", "locale")
    )
    for account_id, locale in devices:
        languages.setdefault(account_id, _language_code(locale))
    return {account_id: languages.get(account_id, settings.LANGUAGE_CODE) for account_id in account_ids}


def compose_in(language, compose, cache):
    """Titulo y cuerpo de un aviso en `language`, compuestos una vez por idioma."""
    if language not in cache:
        with translation.override(language):
            title, body = compose()
            cache[language] = (str(title)[:180], str(body))
    return cache[language]


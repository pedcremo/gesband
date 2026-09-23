from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from .models import Delivery, DeviceRegistration, Notification


def register_device(*, account, installation_id, platform, push_token, permission):
    device, _ = DeviceRegistration.objects.update_or_create(
        installation_id=installation_id,
        defaults={"account": account, "platform": platform, "push_token": push_token, "permission": permission, "is_active": True},
    )
    return device


def mark_receipt(*, account, installation_id):
    return DeviceRegistration.objects.filter(account=account, installation_id=installation_id, is_active=True).update(
        last_receipt_at=timezone.now(), last_seen_at=timezone.now()
    )


@transaction.atomic
def queue_notification_deliveries(notification):
    devices = DeviceRegistration.objects.filter(account=notification.account, is_active=True)
    deliveries = [
        Delivery(notification=notification, device=device, channel=Delivery.Channel.PUSH)
        for device in devices
        if device.permission in {DeviceRegistration.Permission.GRANTED, DeviceRegistration.Permission.PROVISIONAL}
    ]
    if notification.account.email:
        deliveries.append(Delivery(notification=notification, channel=Delivery.Channel.EMAIL))
    Delivery.objects.bulk_create(deliveries, ignore_conflicts=True)
    _dispatch_pending_emails(notification)
    return len(deliveries)


def _dispatch_pending_emails(notification):
    """Encola el envio de los correos que siguen pendientes.

    `bulk_create` con `ignore_conflicts` no devuelve las claves, asi que se
    releen; quedarse con las pendientes evita reenviar una entrega ya resuelta.
    """
    from .tasks import deliver_email_task

    delivery_ids = list(
        Delivery.objects.filter(
            notification=notification,
            channel=Delivery.Channel.EMAIL,
            status=Delivery.Status.PENDING,
        ).values_list("id", flat=True)
    )
    for delivery_id in delivery_ids:
        transaction.on_commit(lambda delivery_id=delivery_id: deliver_email_task.delay(delivery_id))
    return len(delivery_ids)


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

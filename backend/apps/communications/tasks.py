from celery import shared_task

from .models import Delivery, PushTest
from .push import TemporaryPushError
from .services import deliver_email, deliver_push, queue_notification_deliveries, send_push_test

PUSH_MAX_RETRIES = 5


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def queue_notification_task(self, notification_id):
    from .models import Notification

    return queue_notification_deliveries(Notification.objects.get(pk=notification_id))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def deliver_email_task(self, delivery_id):
    delivery = Delivery.objects.select_related("notification", "notification__account").get(pk=delivery_id)
    return deliver_email(delivery)


@shared_task(bind=True, autoretry_for=(TemporaryPushError,), retry_backoff=True, retry_backoff_max=600, max_retries=PUSH_MAX_RETRIES)
def deliver_push_task(self, delivery_id):
    """Solo se reintenta el fallo temporal del proveedor; un token invalido no."""
    delivery = Delivery.objects.select_related("notification", "device").get(pk=delivery_id)
    return deliver_push(delivery, final_attempt=self.request.retries >= PUSH_MAX_RETRIES)


@shared_task
def send_push_test_task(push_test_id):
    return send_push_test(PushTest.objects.select_related("device").get(pk=push_test_id))

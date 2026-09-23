from celery import shared_task

from .models import Delivery
from .services import deliver_email, queue_notification_deliveries


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def queue_notification_task(self, notification_id):
    from .models import Notification

    return queue_notification_deliveries(Notification.objects.get(pk=notification_id))


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def deliver_email_task(self, delivery_id):
    delivery = Delivery.objects.select_related("notification", "notification__account").get(pk=delivery_id)
    return deliver_email(delivery)

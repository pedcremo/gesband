"""MUST-NOTIF-01 en el servidor: dispositivos, pruebas de recepcion y entrega push.

Todo corre contra `FakePushProvider`: ningun mensaje sale de la maquina.
"""

from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.activities.models import Activity, Invitation
from apps.activities.services import notify_activity
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.communications.models import Delivery, DeviceRegistration, Notification, PushTest
from apps.communications.push import FakePushProvider, InvalidTokenError, TemporaryPushError
from apps.communications.services import deliver_push, queue_notification_deliveries
from apps.members.models import Member

INSTALLATION = "4a5b4c5d-1111-4111-8111-111111111111"
TOKEN = "synthetic-push-token-0000000001"


def _account(email):
    return get_user_model().objects.create_user(username=email, email=email, password="secret-password")


def _client_for(account):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=account).key}")
    return client


@override_settings(PUSH_PROVIDER="fake", CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class PushTestCase(TestCase):
    def setUp(self):
        FakePushProvider.reset()
        self.addCleanup(FakePushProvider.reset)
        self.account = _account("musica@example.invalid")
        self.client = _client_for(self.account)

    def register(self, client=None, installation=INSTALLATION, token=TOKEN, permission="granted"):
        return (client or self.client).post(
            "/api/v1/devices",
            {
                "installation_id": installation,
                "platform": "android",
                "push_token": token,
                "permission_state": permission,
                "app_version": "0.1.0",
                "locale": "ca-ES-valencia",
            },
            format="json",
        )

    def capability(self, device_id, client=None):
        return (client or self.client).get(f"/api/v1/devices/{device_id}/notification-capability").json()

    def run_test(self, device_id, client=None):
        with self.captureOnCommitCallbacks(execute=True):
            return (client or self.client).post(
                f"/api/v1/devices/{device_id}/push-tests", {"expected_presentation": "foreground"}, format="json"
            )

    def confirm(self, push_test_id, event="received_foreground", client=None):
        return (client or self.client).post(
            f"/api/v1/push-tests/{push_test_id}/confirm",
            {"event": event, "occurred_at": timezone.now().isoformat()},
            format="json",
        )


class DeviceRegistrationTests(PushTestCase):
    def test_registering_twice_updates_the_same_installation_and_never_returns_the_token(self):
        first = self.register()
        again = self.register(permission="denied")

        self.assertEqual(first.status_code, 201)
        self.assertEqual(again.status_code, 200)
        self.assertEqual(first.json()["id"], again.json()["id"])
        self.assertEqual(again.json()["permission_state"], "denied")
        self.assertNotIn("push_token", again.json())
        self.assertNotIn(TOKEN, str(self.client.get("/api/v1/devices").json()))

    def test_another_account_cannot_touch_the_device(self):
        device_id = self.register().json()["id"]
        intruder = _client_for(_account("intrusa@example.invalid"))

        self.assertEqual(intruder.patch(f"/api/v1/devices/{device_id}", {"permission_state": "denied"}, format="json").status_code, 404)
        self.assertEqual(intruder.get(f"/api/v1/devices/{device_id}/notification-capability").status_code, 404)
        self.assertEqual(self.run_test(device_id, client=intruder).status_code, 404)
        intruder.delete(f"/api/v1/devices/{device_id}")
        self.assertTrue(DeviceRegistration.objects.get(pk=device_id).is_active)

    def test_changing_account_on_the_same_phone_stops_the_previous_persons_notices(self):
        """Mismo telefono, otra persona: los avisos de la primera no pueden llegarle."""
        self.register()
        other = _account("germana@example.invalid")
        self.register(client=_client_for(other), installation="4a5b4c5d-2222-4222-8222-222222222222")

        self.assertFalse(DeviceRegistration.objects.filter(account=self.account).exists())
        notification = Notification.objects.create(
            association=Association.objects.create(name="Banda", slug="banda"),
            account=self.account,
            title="Ensayo",
            body="Cambio de hora",
            deduplication_key="switch",
        )
        with self.captureOnCommitCallbacks(execute=True):
            queue_notification_deliveries(notification)
        self.assertFalse(notification.deliveries.filter(channel=Delivery.Channel.PUSH).exists())
        self.assertEqual(FakePushProvider.outbox, [])

    def test_logout_revokes_the_device(self):
        device_id = self.register().json()["id"]

        self.client.post("/api/v1/auth/logout")

        device = DeviceRegistration.objects.get(pk=device_id)
        self.assertFalse(device.is_active)
        self.assertIsNotNone(device.revoked_at)


class NotificationCapabilityTests(PushTestCase):
    def test_permission_registration_and_receipt_are_reported_separately(self):
        device_id = self.register(permission="not_determined").json()["id"]
        self.assertEqual(self.capability(device_id)["action_required"], "request_system_permission")

        self.client.patch(f"/api/v1/devices/{device_id}", {"permission_state": "denied"}, format="json")
        denied = self.capability(device_id)
        self.assertEqual(denied["action_required"], "open_system_settings")
        self.assertTrue(denied["token_registered"], "tener token no implica permiso")

        self.client.patch(f"/api/v1/devices/{device_id}", {"permission_state": "granted"}, format="json")
        granted = self.capability(device_id)
        self.assertEqual(granted["action_required"], "run_receive_test")
        self.assertFalse(granted["receipt_confirmed"], "permiso y token no demuestran recepcion")

        push_test = self.run_test(device_id).json()
        self.confirm(push_test["id"])
        confirmed = self.capability(device_id)
        self.assertEqual(confirmed["action_required"], "none")
        self.assertTrue(confirmed["receipt_confirmed"])

    def test_a_renewed_token_has_to_be_proved_again(self):
        device_id = self.register().json()["id"]
        self.confirm(self.run_test(device_id).json()["id"])

        self.client.patch(f"/api/v1/devices/{device_id}", {"push_token": "synthetic-push-token-0000000002"}, format="json")

        capability = self.capability(device_id)
        self.assertFalse(capability["receipt_confirmed"])
        self.assertEqual(capability["action_required"], "run_receive_test")

    def test_provisional_is_not_shown_as_fully_enabled(self):
        device_id = self.register(permission="provisional").json()["id"]
        self.confirm(self.run_test(device_id).json()["id"])

        self.assertEqual(self.capability(device_id)["action_required"], "request_system_permission")


class PushTestFlowTests(PushTestCase):
    def test_the_test_message_carries_only_its_identifier_and_is_confirmed_once(self):
        device_id = self.register().json()["id"]

        response = self.run_test(device_id)

        self.assertEqual(response.status_code, 202)
        push_test = self.client.get(f"/api/v1/push-tests/{response.json()['id']}").json()
        self.assertEqual(push_test["status"], "provider_accepted")
        [message] = FakePushProvider.outbox
        self.assertEqual(message.data, {"kind": "notification_test", "push_test_id": push_test["id"]})
        self.assertEqual(message.title, "Prova d'avisos de Gesband", "en l'idioma del dispositiu")

        first = self.confirm(push_test["id"])
        second = self.confirm(push_test["id"], event="opened_from_background")
        self.assertEqual(first.json()["status"], "received_foreground")
        self.assertEqual(second.json()["status"], "received_foreground")

    def test_a_denied_device_cannot_run_a_test(self):
        device_id = self.register(permission="denied").json()["id"]

        response = self.run_test(device_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "push_not_available")
        self.assertEqual(FakePushProvider.outbox, [])

    def test_another_account_cannot_confirm_someone_elses_test(self):
        push_test_id = self.run_test(self.register().json()["id"]).json()["id"]
        intruder = _client_for(_account("intrusa@example.invalid"))

        self.assertEqual(self.confirm(push_test_id, client=intruder).status_code, 404)
        self.assertEqual(PushTest.objects.get(pk=push_test_id).status, "provider_accepted")

    def test_an_expired_test_cannot_be_confirmed(self):
        push_test_id = self.run_test(self.register().json()["id"]).json()["id"]
        PushTest.objects.filter(pk=push_test_id).update(expires_at=timezone.now() - timedelta(seconds=1))

        response = self.confirm(push_test_id)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get(f"/api/v1/push-tests/{push_test_id}").json()["status"], "expired")

    def test_a_rejected_token_asks_for_a_new_registration(self):
        device_id = self.register().json()["id"]
        FakePushProvider.scripted_failures.append(InvalidTokenError("unregistered"))

        push_test = self.run_test(device_id).json()

        stored = PushTest.objects.get(pk=push_test["id"])
        self.assertEqual(stored.status, "provider_failed")
        self.assertEqual(stored.provider_error_code, "unregistered")
        self.assertEqual(self.capability(device_id)["action_required"], "register_token")
        self.client.patch(f"/api/v1/devices/{device_id}", {"push_token": "synthetic-push-token-0000000003"}, format="json")
        self.assertEqual(self.capability(device_id)["action_required"], "run_receive_test")


class PushDeliveryTests(PushTestCase):
    def setUp(self):
        super().setUp()
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        access = AssociationAccess.objects.create(association=self.association, account=self.account)
        AssociationRole.objects.create(access=access, role=AssociationRole.Role.MEMBER)
        member = Member.objects.create(association=self.association, first_name="Musica", last_name="Prova", account=self.account)
        start = timezone.now() + timedelta(days=3)
        self.activity = Activity.objects.create(
            association=self.association,
            created_by=self.account,
            kind=Activity.Kind.REHEARSAL,
            title="Ensayo general",
            starts_at=start,
            ends_at=start + timedelta(hours=2),
            status=Activity.Status.PUBLISHED,
        )
        Invitation.objects.create(activity=self.activity, member=member)
        self.device_id = self.register().json()["id"]

    def notify(self):
        with self.captureOnCommitCallbacks(execute=True):
            notify_activity(self.activity, "Ensayo general", "Cambia la hora")
        return Delivery.objects.get(channel=Delivery.Channel.PUSH, device_id=self.device_id)

    def test_an_activity_notice_reaches_the_device_and_opens_the_activity(self):
        delivery = self.notify()

        self.assertEqual(delivery.status, Delivery.Status.SENT)
        [message] = FakePushProvider.outbox
        self.assertEqual(message.data["kind"], "activity")
        self.assertEqual(message.data["activity_id"], str(self.activity.pk))
        self.assertEqual(message.data["deep_link"], f"gesband://activities/{self.activity.pk}")
        self.assertNotIn("poll_id", message.data)

    def pending_delivery(self):
        with mock.patch("apps.communications.tasks.deliver_push_task.delay"):
            return self.notify()

    def test_a_provider_outage_is_retried_without_duplicating_the_notice(self):
        delivery = self.pending_delivery()
        FakePushProvider.scripted_failures.append(TemporaryPushError("unavailable"))

        with self.assertRaises(TemporaryPushError):
            deliver_push(delivery, final_attempt=False)
        deliver_push(delivery, final_attempt=False)
        deliver_push(delivery, final_attempt=False)

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.SENT)
        self.assertEqual(delivery.attempts, 2, "una entrega enviada no se vuelve a enviar")
        self.assertEqual(len(FakePushProvider.outbox), 1)

    def test_a_persistent_outage_leaves_the_notice_in_the_inbox_and_the_failure_visible(self):
        delivery = self.pending_delivery()
        FakePushProvider.scripted_failures.append(TemporaryPushError("unavailable"))

        deliver_push(delivery, final_attempt=True)

        delivery.refresh_from_db()
        self.assertEqual(delivery.status, Delivery.Status.FAILED)
        self.assertEqual(delivery.error, "unavailable")
        self.assertTrue(Notification.objects.filter(account=self.account, activity=self.activity).exists())

    def test_a_denied_device_gets_no_push_but_keeps_the_inbox(self):
        self.client.patch(f"/api/v1/devices/{self.device_id}", {"permission_state": "denied"}, format="json")

        with self.captureOnCommitCallbacks(execute=True):
            notify_activity(self.activity, "Ensayo general", "Cambia la hora")

        self.assertFalse(Delivery.objects.filter(channel=Delivery.Channel.PUSH).exists())
        self.assertEqual(Notification.objects.filter(account=self.account).count(), 1)


class FcmProviderTests(TestCase):
    """Traduccion de los errores de FCM sin salir a la red."""

    def send_raising(self, exc):
        from apps.communications.push import FcmPushProvider, PushMessage

        provider = FcmPushProvider()
        with mock.patch.object(FcmPushProvider, "_firebase_app", return_value=object()), mock.patch(
            "firebase_admin.messaging.send", side_effect=exc
        ):
            provider.send(PushMessage(token=TOKEN, title="t", body="b", data={"kind": "activity"}))

    def test_an_unregistered_token_is_permanent_and_the_error_hides_the_token(self):
        from firebase_admin import messaging

        with self.assertRaises(InvalidTokenError) as raised:
            self.send_raising(messaging.UnregisteredError(f"Requested entity was not found: {TOKEN}"))
        self.assertNotIn(TOKEN, str(raised.exception))

    def test_an_unavailable_service_is_retryable(self):
        from firebase_admin import exceptions

        with self.assertRaises(TemporaryPushError):
            self.send_raising(exceptions.UnavailableError("down"))

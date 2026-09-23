from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.activities.models import Activity, Invitation, InvitationResponseEvent
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.communications.models import Delivery, Notification
from apps.members.models import Member


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class ActivityChangeNoticeTests(APITestCase):
    """Quien ya esta convocado tiene que enterarse de los cambios."""

    def setUp(self):
        account_model = get_user_model()
        self.board = account_model.objects.create_user(
            username="junta@example.invalid", email="junta@example.invalid", password="secret-password"
        )
        self.musician_account = account_model.objects.create_user(
            username="musico@example.invalid", email="musico@example.invalid", password="secret-password"
        )
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        board_access = AssociationAccess.objects.create(association=self.association, account=self.board)
        AssociationRole.objects.create(access=board_access, role=AssociationRole.Role.ADMIN)
        musician_access = AssociationAccess.objects.create(
            association=self.association, account=self.musician_account
        )
        AssociationRole.objects.create(access=musician_access, role=AssociationRole.Role.MEMBER)
        self.member = Member.objects.create(
            association=self.association, account=self.musician_account, first_name="Pau", last_name="Test"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.board).key}")
        self.starts_at = timezone.now() + timedelta(days=7)

    def make_activity(self, status=Activity.Status.PUBLISHED, **extra):
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.board,
            kind=Activity.Kind.PERFORMANCE,
            status=status,
            title="Processó",
            location="Plaça",
            starts_at=self.starts_at,
            response_deadline=self.starts_at - timedelta(days=1),
            **extra,
        )
        self.invitation = Invitation.objects.create(activity=activity, member=self.member)
        return activity

    def accept(self, activity):
        self.invitation.response = Invitation.Response.ACCEPTED
        self.invitation.activity_version = activity.version
        self.invitation.responded_at = timezone.now()
        self.invitation.save()

    def patch(self, activity, payload):
        return self.client.patch(
            f"/api/v1/activities/{activity.id}/",
            {**payload, "association_id": str(self.association.id)},
            format="json",
        )

    def notices(self):
        return list(Notification.objects.filter(account=self.musician_account).order_by("created_at"))

    # --- Modificación -------------------------------------------------

    def test_changing_the_place_notifies_and_asks_to_confirm_again(self):
        activity = self.make_activity()
        self.accept(activity)

        response = self.patch(activity, {"location": "Casa de la Música"})
        self.assertEqual(response.status_code, 200)

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.response, Invitation.Response.PENDING)
        self.assertIsNone(self.invitation.responded_at)
        notices = self.notices()
        self.assertEqual(len(notices), 1)
        self.assertIn("confirmar", notices[0].title)
        self.assertIn("Casa de la Música", notices[0].body)

    def test_the_cancelled_answer_stays_in_the_history(self):
        activity = self.make_activity()
        self.accept(activity)

        self.patch(activity, {"starts_at": (self.starts_at + timedelta(hours=2)).isoformat()})

        history = InvitationResponseEvent.objects.filter(invitation=self.invitation)
        self.assertEqual([event.response for event in history], [Invitation.Response.PENDING])
        self.assertEqual(history.first().changed_by, self.board)

    def test_changing_the_uniform_notifies_without_cancelling_the_answer(self):
        activity = self.make_activity()
        self.accept(activity)

        self.patch(activity, {"uniform": "Uniforme de gala"})

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.response, Invitation.Response.ACCEPTED)
        notices = self.notices()
        self.assertEqual(len(notices), 1)
        self.assertIn("Uniforme de gala", notices[0].body)

    def test_changing_the_description_notifies_nobody(self):
        activity = self.make_activity()
        self.accept(activity)

        self.patch(activity, {"description": "Recordad el atril"})

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.response, Invitation.Response.ACCEPTED)
        self.assertEqual(self.notices(), [])

    def test_writing_the_same_value_is_not_a_change(self):
        activity = self.make_activity()
        self.accept(activity)

        self.patch(activity, {"location": "Plaça"})

        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.response, Invitation.Response.ACCEPTED)
        self.assertEqual(self.notices(), [])

    def test_a_draft_notifies_nobody(self):
        activity = self.make_activity(status=Activity.Status.DRAFT)

        self.patch(activity, {"location": "Casa de la Música"})

        self.assertEqual(self.notices(), [])

    def test_status_cannot_be_changed_with_a_plain_patch(self):
        activity = self.make_activity()

        self.patch(activity, {"status": Activity.Status.CANCELLED})

        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.PUBLISHED)
        self.assertEqual(self.notices(), [])

    # --- Cancelación --------------------------------------------------

    def test_cancelling_notifies_the_invited_people_with_the_reason(self):
        activity = self.make_activity()

        response = self.client.post(
            f"/api/v1/activities/{activity.id}/cancel/",
            {"association_id": str(self.association.id), "reason": "Pluja"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)

        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.CANCELLED)
        notices = self.notices()
        self.assertEqual(len(notices), 1)
        self.assertIn("Pluja", notices[0].body)

    def test_a_cancelled_activity_cannot_be_cancelled_again(self):
        activity = self.make_activity(status=Activity.Status.CANCELLED)

        response = self.client.post(
            f"/api/v1/activities/{activity.id}/cancel/",
            {"association_id": str(self.association.id), "reason": "Pluja"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_cancelling_without_a_reason_is_refused(self):
        activity = self.make_activity()

        response = self.client.post(
            f"/api/v1/activities/{activity.id}/cancel/",
            {"association_id": str(self.association.id), "reason": "   "},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.PUBLISHED)
        self.assertEqual(self.notices(), [])

    def test_nobody_can_answer_a_cancelled_activity(self):
        activity = self.make_activity()
        self.client.post(
            f"/api/v1/activities/{activity.id}/cancel/",
            {"association_id": str(self.association.id), "reason": "Pluja"},
            format="json",
        )

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.musician_account).key}"
        )
        response = self.client.post(
            f"/api/v1/activities/{activity.id}/respond/",
            {
                "association_id": str(self.association.id),
                "invitation_id": str(self.invitation.id),
                "response": "accepted",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    # --- Publicación y entregas ---------------------------------------

    def test_publishing_notifies_the_people_invited_while_it_was_a_draft(self):
        activity = self.make_activity(status=Activity.Status.DRAFT)

        response = self.client.post(
            f"/api/v1/activities/{activity.id}/publish/",
            {"association_id": str(self.association.id)},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.notices()), 1)

    def test_a_second_change_does_not_resend_the_first_notice(self):
        """Encolar todos los avisos de la actividad reenviaria los anteriores.

        La unicidad de `Delivery` no lo impide: dos filas de correo del mismo
        aviso tienen `device` nulo y no chocan entre si.
        """
        activity = self.make_activity()
        with self.captureOnCommitCallbacks(execute=True):
            self.patch(activity, {"location": "Casa de la Música"})
        with self.captureOnCommitCallbacks(execute=True):
            self.patch(activity, {"uniform": "Uniforme de gala"})

        self.assertEqual(len(self.notices()), 2)
        emails = Delivery.objects.filter(channel=Delivery.Channel.EMAIL)
        self.assertEqual(emails.count(), 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertNotEqual(mail.outbox[0].body, mail.outbox[1].body)

    def test_repeating_the_same_change_does_not_notify_twice(self):
        activity = self.make_activity()
        with self.captureOnCommitCallbacks(execute=True):
            self.patch(activity, {"location": "Casa de la Música"})
        with self.captureOnCommitCallbacks(execute=True):
            self.patch(activity, {"location": "Casa de la Música"})

        self.assertEqual(len(self.notices()), 1)
        self.assertEqual(len(mail.outbox), 1)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class ActivityPanelChangeTests(ActivityChangeNoticeTests):
    """Las mismas operaciones desde el panel de la junta."""

    def setUp(self):
        super().setUp()
        self.web = Client()
        self.web.force_login(self.board)

    def url(self, activity):
        return f"/panel/activities/{activity.id}/?association_id={self.association.id}"

    def form_fields(self, activity):
        return {
            "association_id": str(self.association.id),
            "title": activity.title,
            "starts_at": timezone.localtime(activity.starts_at).strftime("%Y-%m-%dT%H:%M"),
            "location": activity.location,
            "uniform": activity.uniform,
            "description": activity.description,
            "response_deadline": timezone.localtime(activity.response_deadline).strftime("%Y-%m-%dT%H:%M"),
        }

    def test_the_panel_offers_the_change_form(self):
        activity = self.make_activity()
        page = self.web.get(self.url(activity))
        self.assertContains(page, 'name="save_changes"')
        self.assertContains(page, 'name="starts_at"')
        self.assertContains(page, 'name="cancel"')

    def test_saving_a_new_place_from_the_panel_notifies_and_resets(self):
        activity = self.make_activity()
        self.accept(activity)

        response = self.web.post(
            self.url(activity),
            {**self.form_fields(activity), "location": "Casa de la Música", "save_changes": "1"},
        )
        self.assertEqual(response.status_code, 302)

        activity.refresh_from_db()
        self.assertEqual(activity.location, "Casa de la Música")
        self.invitation.refresh_from_db()
        self.assertEqual(self.invitation.response, Invitation.Response.PENDING)
        self.assertEqual(len(self.notices()), 1)

    def test_the_panel_warns_when_the_deadline_already_passed(self):
        activity = self.make_activity()
        Activity.objects.filter(pk=activity.pk).update(response_deadline=timezone.now() - timedelta(days=1))
        activity.refresh_from_db()
        self.accept(activity)

        response = self.web.post(
            self.url(activity),
            {**self.form_fields(activity), "location": "Casa de la Música", "save_changes": "1"},
            follow=True,
        )
        self.assertContains(response, "plazo de respuesta ya ha terminado")

    def test_cancelling_from_the_panel_notifies(self):
        activity = self.make_activity()

        response = self.web.post(
            self.url(activity),
            {"association_id": str(self.association.id), "cancel": "1", "reason": "Pluja"},
            follow=True,
        )
        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.CANCELLED)
        self.assertContains(response, "Actividad cancelada")
        self.assertIn("Pluja", self.notices()[0].body)

    def test_a_cancelled_activity_hides_the_change_and_invite_forms(self):
        activity = self.make_activity(status=Activity.Status.CANCELLED)
        page = self.web.get(self.url(activity))
        self.assertNotContains(page, 'name="save_changes"')
        self.assertNotContains(page, 'name="invite_all_musicians"')

    def test_an_invalid_change_reports_the_error_without_saving(self):
        activity = self.make_activity()
        response = self.web.post(
            self.url(activity),
            {**self.form_fields(activity), "title": "", "save_changes": "1"},
        )
        self.assertEqual(response.status_code, 200)
        activity.refresh_from_db()
        self.assertEqual(activity.title, "Processó")
        self.assertEqual(self.notices(), [])


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class ActivityNoticeLanguageTests(ActivityChangeNoticeTests):
    """Los avisos salen en el idioma que pide el cliente (ADR 0001)."""

    def cancel_in(self, language):
        activity = self.make_activity()
        self.client.post(
            f"/api/v1/activities/{activity.id}/cancel/",
            {"association_id": str(self.association.id), "reason": "Pluja"},
            format="json",
            HTTP_ACCEPT_LANGUAGE=language,
        )
        return self.notices()[0]

    def test_the_cancellation_notice_is_written_in_spanish(self):
        self.assertEqual(self.cancel_in("es").title, "Actividad cancelada")

    def test_the_cancellation_notice_is_written_in_valencian(self):
        notice = self.cancel_in("ca")
        self.assertEqual(notice.title, "Activitat cancel·lada")
        self.assertIn("Motiu", notice.body)

    def test_the_cancellation_notice_is_written_in_english(self):
        notice = self.cancel_in("en")
        self.assertEqual(notice.title, "Activity cancelled")
        self.assertIn("Reason", notice.body)

    def test_the_change_notice_is_translated_too(self):
        activity = self.make_activity()
        self.client.patch(
            f"/api/v1/activities/{activity.id}/",
            {"association_id": str(self.association.id), "location": "Casa de la Música"},
            format="json",
            HTTP_ACCEPT_LANGUAGE="ca",
        )
        notice = self.notices()[0]
        self.assertEqual(notice.title, "Canvi important: torna a confirmar")
        self.assertIn("Lloc", notice.body)

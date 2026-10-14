"""Actividades remuneradas, adeudos y pagos a músicos (decisión 0011)."""

import threading
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import Client, TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone, translation
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.activities.models import Activity, ActivityPayment, Attendance, Invitation
from apps.activities.payments import (
    association_earnings,
    mark_all_present_paid,
    mark_paid,
    member_earnings,
    payment_state,
    void_payment,
)
from apps.activities.services import cancel_activity, record_attendance
from apps.activities.templatetags.activity_payments import euros
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members.models import Member

Role = AssociationRole.Role


class PaymentFixtures:
    """Dos asociaciones con datos sintéticos y ayudas para crear personas y actividades."""

    def make_associations(self):
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.board = self.account("junta", Role.BOARD)
        self.starts_at = timezone.now() + timedelta(days=7)

    def account(self, name, *roles, association=None, email=None):
        association = association or self.association
        email = email or f"{name}-{association.slug}@example.invalid"
        User = get_user_model()
        account = User.objects.filter(email=email).first() or User.objects.create_user(
            username=email, email=email, password="secret-password"
        )
        access = AssociationAccess.objects.create(association=association, account=account)
        for role in roles:
            AssociationRole.objects.create(access=access, role=role)
        return account

    def member(self, first_name, account=None, association=None):
        return Member.objects.create(
            association=association or self.association,
            first_name=first_name,
            last_name="Prova",
            account=account,
        )

    def activity(self, title="Concert de Santa Cecília", fee="25.00", association=None, days=7, **extra):
        return Activity.objects.create(
            association=association or self.association,
            created_by=self.board,
            kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED,
            title=title,
            starts_at=timezone.now() + timedelta(days=days),
            is_paid=fee is not None,
            fee_amount=Decimal(fee) if fee is not None else None,
            **extra,
        )

    def invite(self, activity, member, attendance=None, response=Invitation.Response.ACCEPTED):
        invitation = Invitation.objects.create(activity=activity, member=member, response=response)
        if attendance:
            record_attendance(invitation, self.board, attendance)
        return Invitation.objects.select_related("activity").get(pk=invitation.pk)


class RemunerationValidationTests(PaymentFixtures, TestCase):
    def setUp(self):
        self.make_associations()

    def draft(self, **fields):
        return Activity(
            association=self.association,
            created_by=self.board,
            kind=Activity.Kind.PERFORMANCE,
            title="Processó",
            starts_at=self.starts_at,
            **fields,
        )

    def test_paid_activity_requires_a_positive_fee(self):
        for fee in (None, Decimal("0"), Decimal("-5.00")):
            with self.subTest(fee=fee), self.assertRaises(ValidationError) as caught:
                self.draft(is_paid=True, fee_amount=fee).full_clean()
            self.assertIn("fee_amount", caught.exception.message_dict)

    def test_unpaid_activity_discards_a_leftover_fee(self):
        activity = self.draft(is_paid=False, fee_amount=Decimal("10.00"))
        activity.full_clean()
        self.assertIsNone(activity.fee_amount)

    def test_database_rejects_a_paid_activity_without_fee(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.draft(is_paid=True, fee_amount=None).save()

    def test_database_rejects_a_fee_on_an_unpaid_activity(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.draft(is_paid=False, fee_amount=Decimal("10.00")).save()


class AccrualTests(PaymentFixtures, TestCase):
    def setUp(self):
        self.make_associations()
        self.musician = self.member("Marina")

    def test_only_recorded_presence_accrues(self):
        activity = self.activity()
        cases = {
            Attendance.Status.PRESENT: "owed",
            Attendance.Status.ABSENT: None,
            Attendance.Status.EXCUSED: None,
            Attendance.Status.UNRECORDED: None,
        }
        for attendance, expected in cases.items():
            with self.subTest(attendance=attendance):
                member = self.member(f"Persona {attendance}")
                invitation = self.invite(activity, member, attendance=attendance)
                self.assertEqual(payment_state(invitation).status, expected)

    def test_an_accepted_invitation_without_attendance_never_accrues(self):
        invitation = self.invite(self.activity(), self.musician, attendance=None)
        self.assertIsNone(payment_state(invitation).status)
        self.assertEqual(member_earnings(self.musician).owed_total, Decimal("0.00"))

    def test_a_cancelled_activity_does_not_accrue(self):
        activity = self.activity()
        self.invite(activity, self.musician, attendance=Attendance.Status.PRESENT)
        cancel_activity(activity, self.board, reason="Pluja")
        self.assertEqual(member_earnings(self.musician).items, [])

    def test_an_unpaid_activity_does_not_accrue(self):
        self.invite(self.activity(fee=None), self.musician, attendance=Attendance.Status.PRESENT)
        self.assertEqual(member_earnings(self.musician).items, [])

    def test_owed_uses_the_current_fee(self):
        activity = self.activity(fee="25.00")
        self.invite(activity, self.musician, attendance=Attendance.Status.PRESENT)
        Activity.objects.filter(pk=activity.pk).update(fee_amount=Decimal("30.00"))
        self.assertEqual(member_earnings(self.musician).owed_total, Decimal("30.00"))


class MarkPaidTests(PaymentFixtures, TestCase):
    def setUp(self):
        self.make_associations()
        self.musician = self.member("Marina")
        self.activity_ = self.activity()
        self.invitation = self.invite(self.activity_, self.musician, attendance=Attendance.Status.PRESENT)

    def test_marking_paid_snapshots_amount_author_and_time(self):
        before = timezone.now()
        payment, created = mark_paid(self.invitation, self.board, self.association)
        self.assertTrue(created)
        self.assertEqual(payment.amount, Decimal("25.00"))
        self.assertEqual(payment.paid_by, self.board)
        self.assertGreaterEqual(payment.paid_at, before)
        self.assertIsNone(payment.voided_at)

    def test_changing_the_fee_does_not_alter_a_recorded_payment(self):
        payment, _created = mark_paid(self.invitation, self.board, self.association)
        self.activity_.fee_amount = Decimal("40.00")
        self.activity_.save()
        payment.refresh_from_db()
        self.assertEqual(payment.amount, Decimal("25.00"))
        summary = member_earnings(self.musician)
        self.assertEqual((summary.paid_total, summary.owed_total), (Decimal("25.00"), Decimal("0.00")))

    def test_marking_twice_is_idempotent(self):
        first, created_first = mark_paid(self.invitation, self.board, self.association)
        second, created_second = mark_paid(self.invitation, self.board, self.association)
        self.assertEqual((created_first, created_second), (True, False))
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ActivityPayment.objects.count(), 1)

    def test_database_allows_only_one_active_payment_per_invitation(self):
        mark_paid(self.invitation, self.board, self.association)
        with self.assertRaises(IntegrityError), transaction.atomic():
            ActivityPayment.objects.create(
                invitation=self.invitation, amount=Decimal("25.00"), paid_at=timezone.now(), paid_by=self.board
            )

    def test_voiding_keeps_history_and_allows_paying_again(self):
        payment, _created = mark_paid(self.invitation, self.board, self.association)
        voided, did_void = void_payment(payment, self.board, self.association)
        self.assertTrue(did_void)
        self.assertEqual(voided.voided_by, self.board)
        self.assertIsNotNone(voided.voided_at)
        self.assertEqual(member_earnings(self.musician).owed_total, Decimal("25.00"))

        _again, did_void_again = void_payment(payment, self.board, self.association)
        self.assertFalse(did_void_again)

        self.activity_.fee_amount = Decimal("27.50")
        self.activity_.save()
        new_payment, created = mark_paid(self.invitation, self.board, self.association)
        self.assertTrue(created)
        self.assertEqual(new_payment.amount, Decimal("27.50"))
        self.assertEqual(
            [(item.amount, item.is_active) for item in ActivityPayment.objects.order_by("paid_at")],
            [(Decimal("25.00"), False), (Decimal("27.50"), True)],
        )

    def test_cannot_pay_someone_who_was_not_present(self):
        absent = self.invite(self.activity_, self.member("Absent"), attendance=Attendance.Status.ABSENT)
        with self.assertRaises(ValidationError):
            mark_paid(absent, self.board, self.association)
        self.assertFalse(ActivityPayment.objects.filter(invitation=absent).exists())

    def test_only_admin_and_board_can_pay(self):
        admin = self.account("admin", Role.ADMIN)
        _payment, created = mark_paid(self.invitation, admin, self.association)
        self.assertTrue(created)
        for role in (Role.ORGANIZER, Role.DIRECTOR, Role.MEMBER):
            with self.subTest(role=role):
                account = self.account(role, role)
                other = self.invite(self.activity_, self.member(f"M {role}"), attendance=Attendance.Status.PRESENT)
                with self.assertRaises(PermissionDenied):
                    mark_paid(other, account, self.association)
                with self.assertRaises(PermissionDenied):
                    mark_all_present_paid(self.activity_, account, self.association)

    def test_board_of_another_association_cannot_pay_here(self):
        foreign_board = self.account("junta-b", Role.BOARD, association=self.other_association)
        with self.assertRaises(PermissionDenied):
            mark_paid(self.invitation, foreign_board, self.other_association)
        with self.assertRaises(PermissionDenied):
            mark_paid(self.invitation, foreign_board, self.association)
        self.assertFalse(ActivityPayment.objects.exists())

    def test_voiding_checks_the_association(self):
        payment, _created = mark_paid(self.invitation, self.board, self.association)
        foreign_board = self.account("junta-b", Role.BOARD, association=self.other_association)
        with self.assertRaises(PermissionDenied):
            void_payment(payment, foreign_board, self.other_association)
        payment.refresh_from_db()
        self.assertIsNone(payment.voided_at)

    def test_mark_all_pays_only_present_and_is_repeatable(self):
        self.invite(self.activity_, self.member("Absent"), attendance=Attendance.Status.ABSENT)
        self.invite(self.activity_, self.member("Second"), attendance=Attendance.Status.PRESENT)
        self.assertEqual(mark_all_present_paid(self.activity_, self.board, self.association), 2)
        self.assertEqual(mark_all_present_paid(self.activity_, self.board, self.association), 0)
        self.assertEqual(ActivityPayment.objects.count(), 2)

    def test_a_paid_attendance_that_stops_being_present_is_an_incident(self):
        mark_paid(self.invitation, self.board, self.association)
        record_attendance(self.invitation, self.board, Attendance.Status.ABSENT)
        state = payment_state(Invitation.objects.select_related("activity").get(pk=self.invitation.pk))
        self.assertEqual(state.status, "paid")
        self.assertTrue(state.incident)
        summary = member_earnings(self.musician)
        self.assertEqual(summary.owed_total, Decimal("0.00"))
        self.assertEqual(summary.paid_total, Decimal("25.00"))
        self.assertEqual(summary.incidents, 1)

    def test_association_summary_is_isolated(self):
        foreign = self.member("Foraster", association=self.other_association)
        foreign_activity = self.activity(association=self.other_association)
        self.invite(foreign_activity, foreign, attendance=Attendance.Status.PRESENT)
        rows = association_earnings(self.association)
        self.assertEqual([member for member, _summary in rows], [self.musician])
        self.assertEqual(rows[0][1].owed_total, Decimal("25.00"))


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentMarkPaidTests(PaymentFixtures, TransactionTestCase):
    def test_two_simultaneous_clicks_create_a_single_payment(self):
        self.make_associations()
        invitation = self.invite(self.activity(), self.member("Marina"), attendance=Attendance.Status.PRESENT)
        barrier = threading.Barrier(2)
        results, errors = [], []

        def click():
            try:
                barrier.wait()
                results.append(mark_paid(invitation, self.board, self.association)[1])
            except Exception as exc:  # pragma: no cover - se informa en la aserción
                errors.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=click) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(ActivityPayment.objects.filter(voided_at__isnull=True).count(), 1)


class EarningsApiTests(PaymentFixtures, TestCase):
    url = "/api/v1/members/me/earnings/"

    def setUp(self):
        self.make_associations()
        self.musician_account = self.account("musica", Role.MEMBER)
        self.musician = self.member("Marina", account=self.musician_account)
        self.colleague = self.member("Company", account=self.account("company", Role.MEMBER))

    def api(self, account, association=None):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.get_or_create(user=account)[0].key}",
            HTTP_X_ASSOCIATION_ID=str((association or self.association).pk),
        )
        return client

    def test_returns_owed_and_paid_items_newest_first(self):
        older = self.activity(title="Concert de primavera", fee="25.00", days=3)
        newer = self.activity(title="Concert de Santa Cecília", fee="30.00", days=10)
        absent = self.activity(title="Processó", fee="15.00", days=5)
        paid_invitation = self.invite(older, self.musician, attendance=Attendance.Status.PRESENT)
        owed_invitation = self.invite(newer, self.musician, attendance=Attendance.Status.PRESENT)
        self.invite(absent, self.musician, attendance=Attendance.Status.ABSENT)
        payment, _created = mark_paid(paid_invitation, self.board, self.association)

        response = self.api(self.musician_account).get(self.url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            {key: data[key] for key in ("currency", "owed_total", "paid_total")},
            {"currency": "EUR", "owed_total": "30.00", "paid_total": "25.00"},
        )
        self.assertEqual(
            [(item["invitation"], item["status"], item["amount"]) for item in data["items"]],
            [(str(owed_invitation.pk), "owed", "30.00"), (str(paid_invitation.pk), "paid", "25.00")],
        )
        owed, paid = data["items"]
        self.assertEqual(
            owed["activity"],
            {"id": str(newer.pk), "title": newer.title, "starts_at": newer.starts_at.isoformat().replace("+00:00", "Z")},
        )
        self.assertTrue(owed["activity"]["starts_at"].endswith("Z"))
        self.assertIsNone(owed["paid_at"])
        self.assertTrue(paid["paid_at"].endswith("Z"))
        self.assertEqual(paid["paid_at"], payment.paid_at.isoformat().replace("+00:00", "Z"))

    def test_empty_when_nothing_accrued(self):
        data = self.api(self.musician_account).get(self.url).json()
        self.assertEqual(data, {"currency": "EUR", "owed_total": "0.00", "paid_total": "0.00", "items": []})

    def test_a_musician_never_sees_other_peoples_amounts(self):
        activity = self.activity()
        self.invite(activity, self.colleague, attendance=Attendance.Status.PRESENT)
        data = self.api(self.musician_account).get(self.url).json()
        self.assertEqual(data["items"], [])
        self.assertEqual(data["owed_total"], "0.00")

    def test_without_a_linked_profile_returns_the_members_me_error(self):
        board_without_profile = self.account("junta-sense-fitxa", Role.BOARD)
        earnings = self.api(board_without_profile).get(self.url)
        me = self.api(board_without_profile).get("/api/v1/members/me/")
        self.assertEqual(earnings.status_code, 400)
        self.assertEqual(earnings.status_code, me.status_code)
        self.assertEqual(earnings.json(), me.json())

    def test_requires_access_to_the_requested_association(self):
        response = self.api(self.musician_account, association=self.other_association).get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_roles_outside_the_band_are_rejected(self):
        editor = self.account("web", Role.WEB_EDITOR)
        self.member("Editor", account=editor)
        self.assertEqual(self.api(editor).get(self.url).status_code, 403)

    def test_requires_authentication(self):
        response = APIClient().get(self.url, HTTP_X_ASSOCIATION_ID=str(self.association.pk))
        self.assertEqual(response.status_code, 401)

    def test_one_account_in_two_associations_sees_each_separately(self):
        self.account("musica", Role.MEMBER, association=self.other_association, email=self.musician_account.email)
        other_profile = self.member("Marina B", account=self.musician_account, association=self.other_association)
        self.invite(self.activity(fee="25.00"), self.musician, attendance=Attendance.Status.PRESENT)
        self.invite(
            self.activity(fee="40.00", association=self.other_association),
            other_profile,
            attendance=Attendance.Status.PRESENT,
        )
        first = self.api(self.musician_account).get(self.url).json()
        second = self.api(self.musician_account, association=self.other_association).get(self.url).json()
        self.assertEqual((first["owed_total"], len(first["items"])), ("25.00", 1))
        self.assertEqual((second["owed_total"], len(second["items"])), ("40.00", 1))

    def test_is_read_only(self):
        response = self.api(self.musician_account).patch(self.url, {"owed_total": "0.00"}, format="json")
        self.assertEqual(response.status_code, 405)


class ActivityRemunerationApiTests(PaymentFixtures, TestCase):
    def setUp(self):
        self.make_associations()
        self.musician_account = self.account("musica", Role.MEMBER)
        self.musician = self.member("Marina", account=self.musician_account)

    def api(self, account, association=None):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.get_or_create(user=account)[0].key}",
            HTTP_X_ASSOCIATION_ID=str((association or self.association).pk),
        )
        return client

    def test_musician_receives_remuneration_fields(self):
        paid = self.activity(fee="25.00")
        unpaid = self.activity(title="Assaig", fee=None)
        self.invite(paid, self.musician)
        self.invite(unpaid, self.musician)
        client = self.api(self.musician_account)
        paid_data = client.get(f"/api/v1/activities/{paid.pk}/").json()
        unpaid_data = client.get(f"/api/v1/activities/{unpaid.pk}/").json()
        self.assertEqual((paid_data["is_paid"], paid_data["fee_amount"]), (True, "25.00"))
        self.assertEqual((unpaid_data["is_paid"], unpaid_data["fee_amount"]), (False, None))

    def payload(self, **extra):
        return {
            "kind": "performance",
            "title": "Concert de tardor",
            "starts_at": (timezone.now() + timedelta(days=5)).isoformat(),
            **extra,
        }

    def test_manager_creates_a_paid_activity(self):
        response = self.api(self.board).post(
            "/api/v1/activities/", self.payload(is_paid=True, fee_amount="25.50"), format="json"
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["fee_amount"], "25.50")
        self.assertEqual(Activity.objects.get().fee_amount, Decimal("25.50"))

    def test_paid_without_fee_is_rejected(self):
        for fee in (None, "0", "-1.00"):
            with self.subTest(fee=fee):
                response = self.api(self.board).post(
                    "/api/v1/activities/", self.payload(is_paid=True, fee_amount=fee), format="json"
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("fee_amount", response.json())
        self.assertFalse(Activity.objects.exists())

    def test_unmarking_paid_clears_the_fee(self):
        activity = self.activity(fee="25.00")
        response = self.api(self.board).patch(f"/api/v1/activities/{activity.pk}/", {"is_paid": False}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        activity.refresh_from_db()
        self.assertEqual((activity.is_paid, activity.fee_amount), (False, None))

    def test_patching_only_the_fee_keeps_it_validated(self):
        activity = self.activity(fee="25.00")
        response = self.api(self.board).patch(f"/api/v1/activities/{activity.pk}/", {"fee_amount": "0"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_musician_cannot_set_remuneration(self):
        activity = self.activity(fee="25.00")
        self.invite(activity, self.musician)
        response = self.api(self.musician_account).patch(
            f"/api/v1/activities/{activity.pk}/", {"fee_amount": "99.00"}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        activity.refresh_from_db()
        self.assertEqual(activity.fee_amount, Decimal("25.00"))

    def test_attendance_of_another_association_cannot_be_recorded(self):
        """Regresión: el registro de asistencia solo filtraba por actividad.

        Un gestor de A enviaba `X-Association-ID` de A con la actividad de B y
        pasaba lista allí, lo que además hacía devengar importes ajenos.
        """
        foreign_activity = self.activity(association=self.other_association)
        foreign_member = self.member("Foraster", association=self.other_association)
        invitation = Invitation.objects.create(activity=foreign_activity, member=foreign_member)
        response = self.api(self.board).post(
            f"/api/v1/activities/{foreign_activity.pk}/attendance/{invitation.pk}/",
            {"status": "present"},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Attendance.objects.filter(invitation=invitation).exists())


class PanelPaymentTests(PaymentFixtures, TestCase):
    def setUp(self):
        self.make_associations()
        self.musician = self.member("Marina")
        self.activity_ = self.activity(fee="25.00")
        self.invitation = self.invite(self.activity_, self.musician, attendance=Attendance.Status.PRESENT)
        self.detail_url = f"/panel/activities/{self.activity_.pk}/?association_id={self.association.pk}"
        self.payments_url = f"/panel/payments/?association_id={self.association.pk}"

    def web(self, account):
        client = Client()
        client.force_login(account)
        return client

    def test_detail_shows_amount_and_payment_buttons_to_the_board(self):
        page = self.web(self.board).get(self.detail_url)
        self.assertContains(page, "25,00 €")
        self.assertContains(page, "Adeudado")
        self.assertContains(page, 'value="mark_paid"')
        self.assertContains(page, 'value="mark_all_paid"')

    def test_board_marks_paid_and_voids_from_the_detail(self):
        web = self.web(self.board)
        response = web.post(
            self.detail_url,
            {"payment_action": "mark_paid", "invitation_id": self.invitation.pk, "association_id": self.association.pk},
        )
        self.assertRedirects(response, f"{self.detail_url}#pagos", fetch_redirect_response=False)
        payment = ActivityPayment.objects.get()
        self.assertEqual(payment.paid_by, self.board)
        self.assertContains(web.get(self.detail_url), 'value="void_payment"')

        web.post(self.detail_url, {"payment_action": "void_payment", "payment_id": payment.pk})
        payment.refresh_from_db()
        self.assertEqual(payment.voided_by, self.board)
        self.assertEqual(ActivityPayment.objects.count(), 1)

    def test_board_marks_all_present_paid(self):
        self.invite(self.activity_, self.member("Second"), attendance=Attendance.Status.PRESENT)
        self.invite(self.activity_, self.member("Absent"), attendance=Attendance.Status.ABSENT)
        self.web(self.board).post(self.detail_url, {"payment_action": "mark_all_paid"})
        self.assertEqual(ActivityPayment.objects.filter(voided_at__isnull=True).count(), 2)

    def test_organizer_and_director_see_the_detail_but_cannot_pay(self):
        for role in (Role.ORGANIZER, Role.DIRECTOR):
            with self.subTest(role=role):
                web = self.web(self.account(role, role))
                page = web.get(self.detail_url)
                self.assertEqual(page.status_code, 200)
                self.assertNotContains(page, 'value="mark_paid"')
                response = web.post(
                    self.detail_url, {"payment_action": "mark_paid", "invitation_id": self.invitation.pk}
                )
                self.assertEqual(response.status_code, 403)
                response = web.post(self.detail_url, {"payment_action": "mark_all_paid"})
                self.assertEqual(response.status_code, 403)
                self.assertEqual(web.get(self.payments_url).status_code, 403)
        self.assertFalse(ActivityPayment.objects.exists())

    def test_an_invitation_of_another_activity_is_not_found(self):
        other_activity = self.activity(title="Una altra")
        other_invitation = self.invite(other_activity, self.member("Other"), attendance=Attendance.Status.PRESENT)
        for raw in (other_invitation.pk, "no-es-un-uuid"):
            with self.subTest(raw=raw):
                response = self.web(self.board).post(
                    self.detail_url, {"payment_action": "mark_paid", "invitation_id": raw}
                )
                self.assertEqual(response.status_code, 404)
        self.assertFalse(ActivityPayment.objects.exists())

    def test_detail_flags_a_payment_without_presence(self):
        mark_paid(self.invitation, self.board, self.association)
        record_attendance(self.invitation, self.board, Attendance.Status.EXCUSED)
        page = self.web(self.board).get(self.detail_url)
        self.assertContains(page, "Incidencia: ya no devenga")
        self.assertContains(page, "Pagado")

    def test_unpaid_activity_has_no_payment_columns(self):
        unpaid = self.activity(title="Assaig", fee=None)
        page = self.web(self.board).get(f"/panel/activities/{unpaid.pk}/?association_id={self.association.pk}")
        self.assertNotContains(page, 'value="mark_all_paid"')
        self.assertNotContains(page, "No devenga")

    def test_payments_page_lists_owed_by_musician(self):
        foreign = self.member("Foraster", association=self.other_association)
        self.invite(self.activity(association=self.other_association), foreign, attendance=Attendance.Status.PRESENT)
        page = self.web(self.board).get(self.payments_url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Marina Prova")
        self.assertContains(page, "25,00 €")
        self.assertNotContains(page, "Foraster")

    def test_payments_page_marks_paid(self):
        response = self.web(self.board).post(
            self.payments_url, {"invitation_id": self.invitation.pk, "association_id": self.association.pk}
        )
        self.assertRedirects(response, self.payments_url, fetch_redirect_response=False)
        self.assertEqual(ActivityPayment.objects.count(), 1)

    def test_payments_page_rejects_an_invitation_of_another_association(self):
        foreign = self.member("Foraster", association=self.other_association)
        foreign_invitation = self.invite(
            self.activity(association=self.other_association), foreign, attendance=Attendance.Status.PRESENT
        )
        response = self.web(self.board).post(self.payments_url, {"invitation_id": foreign_invitation.pk})
        self.assertEqual(response.status_code, 404)
        self.assertFalse(ActivityPayment.objects.exists())

    def test_payments_page_is_for_admin_and_board_only(self):
        admin = self.account("admin", Role.ADMIN)
        self.assertEqual(self.web(admin).get(self.payments_url).status_code, 200)
        member = self.account("musica", Role.MEMBER)
        self.assertEqual(self.web(member).get(self.payments_url).status_code, 403)
        foreign_board = self.account("junta-b", Role.BOARD, association=self.other_association)
        self.assertEqual(self.web(foreign_board).get(self.payments_url).status_code, 403)

    def test_navigation_links_payments_only_for_payment_managers(self):
        board_home = self.web(self.board).get(f"/panel/?association_id={self.association.pk}")
        self.assertContains(board_home, "/panel/payments/")
        organizer = self.account("org", Role.ORGANIZER)
        organizer_home = self.web(organizer).get(f"/panel/?association_id={self.association.pk}")
        self.assertNotContains(organizer_home, "/panel/payments/")

    def test_payments_page_empty_state(self):
        ActivityPayment.objects.all().delete()
        record_attendance(self.invitation, self.board, Attendance.Status.ABSENT)
        page = self.web(self.board).get(self.payments_url)
        self.assertContains(page, "No hay importes devengados ni pagos registrados.")


class PanelRemunerationFormTests(PaymentFixtures, TestCase):
    def setUp(self):
        self.make_associations()
        self.url = f"/panel/activities/new/?association_id={self.association.pk}"

    def form_data(self, **extra):
        local = timezone.localtime(self.starts_at).strftime("%Y-%m-%dT%H:%M")
        return {"kind": Activity.Kind.PERFORMANCE, "title": "Concert", "starts_at": local, **extra}

    def web(self):
        client = Client()
        client.force_login(self.board)
        return client

    def test_creates_a_paid_activity_with_a_comma_decimal(self):
        response = self.web().post(self.url, self.form_data(is_paid="on", fee_amount="25,50"))
        self.assertEqual(response.status_code, 302)
        activity = Activity.objects.get()
        self.assertEqual((activity.is_paid, activity.fee_amount), (True, Decimal("25.50")))

    def test_paid_without_fee_shows_the_error(self):
        response = self.web().post(self.url, self.form_data(is_paid="on", fee_amount=""))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Indica un importe mayor que cero para una actividad remunerada.")
        self.assertFalse(Activity.objects.exists())

    def test_unpaid_discards_the_fee(self):
        self.web().post(self.url, self.form_data(fee_amount="25"))
        activity = Activity.objects.get()
        self.assertEqual((activity.is_paid, activity.fee_amount), (False, None))

    def test_changing_the_fee_from_the_detail_keeps_recorded_payments(self):
        activity = self.activity(fee="25.00")
        invitation = self.invite(activity, self.member("Marina"), attendance=Attendance.Status.PRESENT)
        mark_paid(invitation, self.board, self.association)
        data = {
            "save_changes": "1",
            "title": activity.title,
            "starts_at": timezone.localtime(activity.starts_at).strftime("%Y-%m-%dT%H:%M"),
            "is_paid": "on",
            "fee_amount": "30,00",
        }
        self.web().post(f"/panel/activities/{activity.pk}/?association_id={self.association.pk}", data)
        activity.refresh_from_db()
        self.assertEqual(activity.fee_amount, Decimal("30.00"))
        self.assertEqual(ActivityPayment.objects.get().amount, Decimal("25.00"))


class MoneyFormatTests(TestCase):
    def test_euros_follow_the_language(self):
        for language in ("es", "ca"):
            with self.subTest(language=language), translation.override(language):
                self.assertEqual(euros(Decimal("25")), "25,00 €")
        self.assertEqual(euros(None), "")


class ShadowedGettextRegressionTests(PaymentFixtures, TestCase):
    """Regresión: `x, _ = ...get_or_create()` tapaba `gettext` en toda la función.

    El mensaje de error previo lanzaba `UnboundLocalError` y la API respondía 500.
    """

    def setUp(self):
        self.make_associations()

    def test_invalid_attendance_status_is_a_validation_error(self):
        from rest_framework.exceptions import ValidationError as DRFValidationError

        invitation = self.invite(self.activity(), self.member("Marina"))
        with self.assertRaises(DRFValidationError):
            record_attendance(invitation, self.board, "teleported")

    def test_api_rejects_an_invalid_attendance_status_with_400(self):
        invitation = self.invite(self.activity(), self.member("Marina"))
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.get_or_create(user=self.board)[0].key}",
            HTTP_X_ASSOCIATION_ID=str(self.association.pk),
        )
        response = client.post(
            f"/api/v1/activities/{invitation.activity_id}/attendance/{invitation.pk}/",
            {"status": "teleported"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_login_with_wrong_password_is_401(self):
        response = APIClient().post(
            "/api/v1/auth/login", {"email": self.board.email, "password": "wrong-password"}, format="json"
        )
        self.assertEqual(response.status_code, 401)

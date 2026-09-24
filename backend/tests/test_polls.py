from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import models
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.communications.models import Notification
from apps.members.models import Instrument, Member, MemberInstrument, Section
from apps.polls.models import Ballot, Poll, PollRecipient


class BallotsCannotBeLinkedToVotersTests(TestCase):
    """ANALISIS.md 3.7: participacion y papeletas sin clave que las relacione."""

    def test_a_ballot_stores_neither_voter_nor_time(self):
        for field in Ballot._meta.get_fields():
            with self.subTest(field=field.name):
                self.assertNotIsInstance(field, (models.DateField, models.DateTimeField, models.TimeField))
                related = getattr(field, "related_model", None)
                self.assertNotIn(related, {Member, get_user_model(), PollRecipient})

    def test_the_ballot_key_does_not_grow_with_each_vote(self):
        """Un entero correlativo permitiria emparejar por orden de insercion."""
        self.assertIsInstance(Ballot._meta.pk, models.UUIDField)

    def test_the_participation_record_stores_no_time(self):
        for field in PollRecipient._meta.get_fields():
            with self.subTest(field=field.name):
                self.assertNotIsInstance(field, (models.DateField, models.DateTimeField, models.TimeField))
                self.assertNotEqual(getattr(field, "related_model", None), Ballot)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class PollApiTests(APITestCase):
    def setUp(self):
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.board = self.account("junta", AssociationRole.Role.BOARD)
        self.ana = self.account("ana", AssociationRole.Role.MEMBER)
        self.biel = self.account("biel", AssociationRole.Role.MEMBER)
        self.outsider = self.account("fora", AssociationRole.Role.MEMBER)
        self.ana_member = self.member(self.ana, "Ana")
        self.biel_member = self.member(self.biel, "Biel")
        self.outsider_member = self.member(self.outsider, "Fora")

    def account(self, name, role, association=None):
        account = get_user_model().objects.create_user(
            username=f"{name}@example.invalid", email=f"{name}@example.invalid", password="secret-password"
        )
        access = AssociationAccess.objects.create(association=association or self.association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def member(self, account, first_name, association=None):
        return Member.objects.create(
            association=association or self.association, account=account, first_name=first_name, last_name="Test"
        )

    def as_(self, account):
        client = self.client_class()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.get_or_create(user=account)[0].key}",
            HTTP_X_ASSOCIATION_ID=str(self.association.id),
        )
        return client

    def create_poll(self, closes_in=timedelta(days=3), options=("Valencia", "Alacant")):
        created = self.as_(self.board).post(
            "/api/v1/polls/",
            {
                "question": "¿Dónde hacemos el viaje?",
                "closes_at": (timezone.now() + closes_in).isoformat(),
                "options": list(options),
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        return created.json()

    def open_poll(self, member_ids=None):
        poll = self.create_poll()
        members = member_ids or [str(self.ana_member.id), str(self.biel_member.id)]
        self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/recipients/", {"member_ids": members}, format="json")
        opened = self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/open/")
        self.assertEqual(opened.status_code, 200, opened.content)
        return opened.json()

    def vote(self, account, poll, index=0):
        return self.as_(account).post(
            f"/api/v1/polls/{poll['id']}/vote/", {"option_id": poll["choices"][index]["id"]}, format="json"
        )

    def expire(self, poll):
        Poll.objects.filter(pk=poll["id"]).update(closes_at=timezone.now() - timedelta(minutes=1))

    def detail(self, account, poll):
        return self.as_(account).get(f"/api/v1/polls/{poll['id']}/")

    # --- Voto único ------------------------------------------------------

    def test_a_second_vote_is_rejected_by_the_server(self):
        poll = self.open_poll()
        self.assertEqual(self.vote(self.ana, poll, 0).status_code, 201)

        again = self.vote(self.ana, poll, 1)

        self.assertEqual(again.status_code, 409)
        self.assertIn("no se puede cambiar", again.json()["detail"])
        self.assertEqual(Ballot.objects.filter(poll_id=poll["id"]).count(), 1)

    def test_voting_marks_participation_without_saying_what(self):
        poll = self.open_poll()
        body = self.vote(self.ana, poll).json()

        self.assertTrue(body["has_voted"])
        self.assertFalse(body["can_vote"])
        self.assertNotIn("my_choice", body)
        self.assertTrue(PollRecipient.objects.get(poll_id=poll["id"], member=self.ana_member).has_voted)

    def test_only_recipients_can_vote(self):
        poll = self.open_poll(member_ids=[str(self.ana_member.id)])

        self.assertEqual(self.detail(self.biel, poll).status_code, 404)
        self.assertEqual(self.vote(self.biel, poll).status_code, 404)
        self.assertEqual(Ballot.objects.count(), 0)

    def test_an_option_from_another_poll_is_not_accepted(self):
        poll = self.open_poll()
        other = self.create_poll(options=("Sí", "No"))

        response = self.as_(self.ana).post(
            f"/api/v1/polls/{poll['id']}/vote/", {"option_id": other["choices"][0]["id"]}, format="json"
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(PollRecipient.objects.get(poll_id=poll["id"], member=self.ana_member).has_voted)

    def test_nobody_votes_after_the_deadline(self):
        poll = self.open_poll()
        self.expire(poll)

        self.assertEqual(self.vote(self.ana, poll).status_code, 400)

    # --- Recuento --------------------------------------------------------

    def test_recipients_see_the_provisional_tally_while_open(self):
        poll = self.open_poll()
        self.vote(self.ana, poll, 0)

        results = self.detail(self.biel, poll).json()["results"]

        self.assertEqual(results["kind"], "provisional")
        self.assertEqual(results["votes_cast"], 1)
        self.assertEqual([row["votes"] for row in results["options"]], [1, 0])

    def test_the_board_does_not_see_who_voted_while_voting_is_open(self):
        """Quien vota y como se mueve el recuento, juntos, delatarian el voto."""
        poll = self.open_poll()
        self.vote(self.ana, poll, 0)

        body = self.detail(self.board, poll).json()

        self.assertIsNone(body["recipients"])
        self.assertEqual(body["participation"], {"recipients": 2, "voted": 1})

    def test_after_the_deadline_only_the_board_sees_the_tally_until_published(self):
        poll = self.open_poll()
        self.vote(self.ana, poll, 0)
        self.expire(poll)

        self.assertIsNone(self.detail(self.biel, poll).json()["results"])
        board_view = self.detail(self.board, poll).json()
        self.assertEqual(board_view["results"]["kind"], "provisional")
        self.assertEqual(
            [(row["member_name"], row["has_voted"]) for row in board_view["recipients"]],
            [("Ana Test", True), ("Biel Test", False)],
        )

    def test_publishing_is_explicit_and_only_after_the_deadline(self):
        poll = self.open_poll()
        self.vote(self.ana, poll, 1)
        self.assertEqual(self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/publish/").status_code, 400)

        self.expire(poll)
        published = self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/publish/")

        self.assertEqual(published.status_code, 200)
        results = self.detail(self.biel, poll).json()["results"]
        self.assertEqual(results["kind"], "final")
        self.assertEqual([row["votes"] for row in results["options"]], [0, 1])
        notice = Notification.objects.get(account=self.biel, deduplication_key__contains=":published:")
        self.assertIn("Alacant: 1", notice.body)
        self.assertIn("1 de 2", notice.body)

    def test_a_cancelled_poll_shows_no_tally(self):
        poll = self.open_poll()
        self.vote(self.ana, poll)

        self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/cancel/", {"reason": "Error en las opciones"})

        self.assertIsNone(self.detail(self.board, poll).json()["results"])
        self.assertIsNone(self.detail(self.ana, poll).json()["results"])

    # --- Borrador y apertura ---------------------------------------------

    def test_a_draft_can_be_corrected_but_an_open_poll_cannot(self):
        poll = self.create_poll()
        fixed = self.as_(self.board).patch(
            f"/api/v1/polls/{poll['id']}/", {"options": ["Valencia", "Alacant", "Castelló"]}, format="json"
        )
        self.assertEqual(len(fixed.json()["choices"]), 3)

        opened = self.open_poll()
        refused = self.as_(self.board).patch(f"/api/v1/polls/{opened['id']}/", {"question": "Otra"}, format="json")
        self.assertEqual(refused.status_code, 400)

    def test_members_do_not_see_drafts(self):
        poll = self.create_poll()
        self.as_(self.board).post(
            f"/api/v1/polls/{poll['id']}/recipients/", {"member_ids": [str(self.ana_member.id)]}, format="json"
        )

        self.assertEqual(self.as_(self.ana).get("/api/v1/polls/").json()["results"], [])

    def test_opening_requires_recipients_and_two_options(self):
        poll = self.create_poll()
        self.assertEqual(self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/open/").status_code, 400)

        single = self.as_(self.board).post(
            "/api/v1/polls/",
            {"question": "¿Sí?", "closes_at": (timezone.now() + timedelta(days=1)).isoformat(), "options": ["Sí"]},
            format="json",
        )
        self.assertEqual(single.status_code, 400)

    def test_opening_notifies_each_recipient_once(self):
        poll = self.open_poll()
        self.as_(self.board).post(f"/api/v1/polls/{poll['id']}/open/")

        notices = Notification.objects.filter(poll_id=poll["id"])
        self.assertEqual(sorted(notices.values_list("account__username", flat=True)), ["ana@example.invalid", "biel@example.invalid"])
        self.assertEqual(notices.first().deep_link, f"gesband://polls/{poll['id']}")

    def test_members_cannot_manage_polls(self):
        poll = self.create_poll()
        client = self.as_(self.ana)

        self.assertEqual(client.post("/api/v1/polls/", {"question": "x"}, format="json").status_code, 403)
        self.assertEqual(client.post(f"/api/v1/polls/{poll['id']}/open/").status_code, 403)
        self.assertEqual(client.post(f"/api/v1/polls/{poll['id']}/publish/").status_code, 403)

    # --- Destinatarios y aislamiento -------------------------------------

    def test_recipients_by_section_or_instrument(self):
        brass = Section.objects.create(association=self.association, name="Metal")
        trumpet = Instrument.objects.create(association=self.association, name="Trompeta", section=brass)
        clarinet = Instrument.objects.create(association=self.association, name="Clarinete")
        MemberInstrument.objects.create(member=self.ana_member, instrument=trumpet)
        MemberInstrument.objects.create(member=self.biel_member, instrument=clarinet)
        poll = self.create_poll()

        by_section = self.as_(self.board).post(
            f"/api/v1/polls/{poll['id']}/recipients/", {"section_ids": [brass.id]}, format="json"
        )
        self.assertEqual(by_section.json(), {"recipients": 1})

        both = self.as_(self.board).post(
            f"/api/v1/polls/{poll['id']}/recipients/",
            {"section_ids": [brass.id], "instrument_ids": [clarinet.id]},
            format="json",
        )
        self.assertEqual(both.json(), {"recipients": 2})

    def test_members_of_another_association_are_ignored(self):
        other = Association.objects.create(name="Altra", slug="altra")
        stranger = self.member(None, "Estranya", association=other)
        poll = self.create_poll()

        response = self.as_(self.board).post(
            f"/api/v1/polls/{poll['id']}/recipients/", {"member_ids": [str(stranger.id)]}, format="json"
        )

        self.assertEqual(response.json(), {"recipients": 0})

    def test_another_association_cannot_read_the_poll(self):
        poll = self.open_poll()
        other = Association.objects.create(name="Altra", slug="altra")
        foreign_board = self.account("altra-junta", AssociationRole.Role.BOARD, association=other)
        client = self.client_class()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=foreign_board).key}",
            HTTP_X_ASSOCIATION_ID=str(other.id),
        )

        self.assertEqual(client.get(f"/api/v1/polls/{poll['id']}/").status_code, 404)
        self.assertEqual(client.post(f"/api/v1/polls/{poll['id']}/publish/").status_code, 404)

    def test_permissions_are_announced(self):
        def announced(account):
            body = self.as_(account).get("/api/v1/auth/me").json()
            return set(body["associations"][0]["permissions"])

        self.assertIn("polls.view", announced(self.ana))
        self.assertNotIn("polls.manage", announced(self.ana))
        self.assertIn("polls.manage", announced(self.board))

    def test_malformed_or_out_of_range_ids_are_ignored(self):
        """PostgreSQL no debe ver un entero fuera de bigint ni un UUID roto."""
        poll = self.create_poll()

        response = self.as_(self.board).post(
            f"/api/v1/polls/{poll['id']}/recipients/",
            {"member_ids": ["no-es-un-uuid"], "section_ids": [10**30, "x"], "instrument_ids": [-(10**30)]},
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"recipients": 0})

    def test_a_voted_poll_can_still_be_deleted_with_its_association(self):
        poll = self.open_poll()
        self.vote(self.ana, poll)

        Poll.objects.filter(pk=poll["id"]).delete()

        self.assertEqual(Ballot.objects.count(), 0)

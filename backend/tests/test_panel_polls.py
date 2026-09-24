from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.communications.models import Notification
from apps.members.models import Instrument, Member, MemberInstrument, Section
from apps.polls import services
from apps.polls.models import Poll


def local_input(moment):
    return timezone.localtime(moment).strftime("%Y-%m-%dT%H:%M")


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class PanelPollsTests(TestCase):
    """Panel de la junta para las encuestas (ANALISIS.md 3.7)."""

    def setUp(self):
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.other_association = Association.objects.create(name="Banda Fora", slug="banda-fora")
        self.board = self.account("junta", AssociationRole.Role.BOARD)
        self.musician = self.account("ana", AssociationRole.Role.MEMBER)
        self.ana = self.member("Ana", "Anónima", account=self.musician)
        self.biel = self.member("Biel", "Bosch", account=self.account("biel", AssociationRole.Role.MEMBER))
        self.outsider = self.member("Xavi", "Forani", association=self.other_association)
        self.client.force_login(self.board)

    def account(self, name, role, association=None):
        account = get_user_model().objects.create_user(
            username=f"{name}@example.invalid", email=f"{name}@example.invalid", password="secret-password"
        )
        access = AssociationAccess.objects.create(association=association or self.association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def member(self, first_name, last_name, association=None, account=None, **extra):
        return Member.objects.create(
            association=association or self.association,
            account=account,
            first_name=first_name,
            last_name=last_name,
            **extra,
        )

    def make_poll(self, association=None, closes_in=timedelta(days=3)):
        return services.create_poll(
            association=association or self.association,
            account=self.board,
            question="¿Dónde hacemos el viaje?",
            closes_at=timezone.now() + closes_in,
            options=["Valencia", "Alacant"],
        )

    def open_poll(self, recipients=None):
        poll = self.make_poll()
        members = Member.objects.filter(pk__in=[m.pk for m in (recipients or [self.ana, self.biel])])
        services.set_recipients(poll, members)
        services.open_poll(poll, self.board)
        return poll

    def expire(self, poll):
        Poll.objects.filter(pk=poll.pk).update(closes_at=timezone.now() - timedelta(minutes=1))

    def detail_url(self, poll):
        return reverse("panel-poll-detail", kwargs={"poll_id": poll.pk})

    def post(self, poll, **data):
        return self.client.post(self.detail_url(poll), data, follow=True)

    # Permisos

    def test_member_role_gets_403_on_every_page(self):
        poll = self.open_poll()
        self.client.force_login(self.musician)
        for url in [reverse("panel-polls"), reverse("panel-poll-new"), self.detail_url(poll)]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(self.detail_url(poll), {"action": "publish"}).status_code, 403)
        self.assertEqual(self.client.post(reverse("panel-poll-new"), {"question": "x"}).status_code, 403)

    def test_poll_of_another_association_is_not_found(self):
        foreign = self.make_poll(association=self.other_association)
        self.assertEqual(self.client.get(self.detail_url(foreign)).status_code, 404)
        response = self.client.post(self.detail_url(foreign), {"action": "cancel", "reason": "No"})
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, Poll.Status.DRAFT)

    def test_list_only_shows_own_association(self):
        self.make_poll()
        foreign = self.make_poll(association=self.other_association)
        Poll.objects.filter(pk=foreign.pk).update(question="Encuesta ajena")
        response = self.client.get(reverse("panel-polls"))
        self.assertContains(response, "¿Dónde hacemos el viaje?")
        self.assertNotContains(response, "Encuesta ajena")
        self.assertContains(response, reverse("panel-poll-new"))

    def test_navigation_links_to_polls(self):
        response = self.client.get(reverse("panel"))
        self.assertContains(response, reverse("panel-polls"))

    # Borrador

    def test_create_poll_in_draft(self):
        closes_at = timezone.now() + timedelta(days=2)
        response = self.client.post(
            reverse("panel-poll-new"),
            {
                "question": "¿Uniforme nuevo?",
                "description": "Presupuesto aprobado",
                "closes_at": local_input(closes_at),
                "options": "Sí\n\nNo\n",
            },
        )
        poll = Poll.objects.get(question="¿Uniforme nuevo?")
        self.assertRedirects(response, f"{self.detail_url(poll)}?association_id={self.association.id}")
        self.assertEqual(poll.status, Poll.Status.DRAFT)
        self.assertEqual(poll.created_by, self.board)
        self.assertEqual([option.label for option in poll.options.all()], ["Sí", "No"])

    def test_create_shows_service_errors_next_to_the_field(self):
        response = self.client.post(
            reverse("panel-poll-new"),
            {"question": "¿Uniforme?", "closes_at": local_input(timezone.now() + timedelta(days=1)), "options": "Sí"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "options", "Una encuesta necesita al menos dos opciones.")
        self.assertFalse(Poll.objects.filter(question="¿Uniforme?").exists())

    def test_correct_a_draft(self):
        poll = self.make_poll()
        closes_at = timezone.now() + timedelta(days=5)
        response = self.post(
            poll,
            action="save_draft",
            question="¿Viaje a Castelló?",
            description="",
            closes_at=local_input(closes_at),
            options="Sí\nNo\nMe da igual",
        )
        self.assertContains(response, "Borrador actualizado.")
        poll.refresh_from_db()
        self.assertEqual(poll.question, "¿Viaje a Castelló?")
        self.assertEqual(poll.options.count(), 3)

    def test_draft_errors_are_shown_without_saving(self):
        poll = self.make_poll()
        response = self.client.post(
            self.detail_url(poll),
            {
                "action": "save_draft",
                "question": "Otra",
                "closes_at": local_input(poll.closes_at),
                "options": "Sí\nsí",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Hay opciones repetidas.")
        poll.refresh_from_db()
        self.assertEqual(poll.question, "¿Dónde hacemos el viaje?")

    def test_choose_recipients_by_section_instrument_and_person(self):
        wind = Section.objects.create(association=self.association, name="Metales")
        trumpet = Instrument.objects.create(association=self.association, name="Trompeta", section=wind)
        flute = Instrument.objects.create(association=self.association, name="Flauta")
        carla = self.member("Carla", "Cano")
        dani = self.member("Dani", "Duran")
        MemberInstrument.objects.create(member=carla, instrument=trumpet)
        MemberInstrument.objects.create(member=dani, instrument=flute)
        poll = self.make_poll()

        self.post(poll, action="set_recipients", section_ids=[wind.pk])
        self.assertEqual(set(poll.recipients.values_list("member_id", flat=True)), {carla.pk})

        self.post(poll, action="set_recipients", instrument_ids=[flute.pk], member_ids=[self.ana.pk])
        self.assertEqual(set(poll.recipients.values_list("member_id", flat=True)), {dani.pk, self.ana.pk})

        response = self.post(poll, action="set_recipients", all_active_musicians="on")
        self.assertEqual(poll.recipients.count(), 4)
        self.assertContains(response, "Hay 4 destinatarios.")

    def test_foreign_or_malformed_ids_in_the_selection_are_ignored(self):
        foreign_section = Section.objects.create(association=self.other_association, name="Fora")
        poll = self.make_poll()
        response = self.post(
            poll,
            action="set_recipients",
            member_ids=[self.outsider.pk, self.biel.pk, "not-a-uuid"],
            section_ids=[foreign_section.pk, "x"],
            instrument_ids=["999999"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(poll.recipients.values_list("member_id", flat=True)), [self.biel.pk])

    def test_inactive_members_are_not_offered(self):
        self.member("Inés", "Inactiva", status=Member.Status.INACTIVE)
        response = self.client.get(self.detail_url(self.make_poll()))
        self.assertNotContains(response, "Inés Inactiva")
        self.assertContains(response, "Biel Bosch")

    def test_open_voting_notifies_and_explains_anonymity(self):
        poll = self.make_poll()
        page = self.client.get(self.detail_url(poll))
        self.assertContains(page, "El voto es anónimo")
        self.assertContains(page, "no se puede cambiar")
        self.post(poll, action="set_recipients", member_ids=[self.ana.pk, self.biel.pk])
        response = self.post(poll, action="open")
        self.assertContains(response, "Votación abierta. Se ha avisado a 2 personas consultadas.")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.OPEN)
        self.assertEqual(Notification.objects.filter(poll=poll).count(), 2)

    def test_open_without_recipients_shows_the_service_error(self):
        poll = self.make_poll()
        response = self.post(poll, action="open")
        self.assertContains(response, "Elige a quién se consulta antes de abrir la encuesta.")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.DRAFT)

    def test_delete_draft(self):
        poll = self.make_poll()
        response = self.post(poll, action="delete_draft")
        self.assertRedirects(response, f"{reverse('panel-polls')}?association_id={self.association.id}")
        self.assertFalse(Poll.objects.filter(pk=poll.pk).exists())

    def test_an_open_poll_cannot_be_deleted_or_corrected(self):
        poll = self.open_poll()
        response = self.post(poll, action="delete_draft")
        self.assertContains(response, "Solo se borra un borrador")
        self.assertTrue(Poll.objects.filter(pk=poll.pk).exists())
        response = self.post(
            poll, action="save_draft", question="Cambio", closes_at=local_input(poll.closes_at), options="A\nB"
        )
        self.assertContains(response, "Solo se puede corregir una encuesta en borrador.")
        poll.refresh_from_db()
        self.assertEqual(poll.question, "¿Dónde hacemos el viaje?")

    # Abierta

    def test_open_poll_shows_provisional_tally_but_never_who_voted(self):
        poll = self.open_poll()
        services.cast_vote(poll, self.musician, poll.options.get(label="Valencia").pk)
        for url in [self.detail_url(poll), reverse("panel-polls")]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                for name in ["Ana", "Anónima", "Biel", "Bosch"]:
                    self.assertNotContains(response, name)
                self.assertNotContains(response, "Ha votado")
        detail = self.client.get(self.detail_url(poll))
        self.assertContains(detail, "Recuento provisional")
        self.assertContains(detail, "Han votado 1 de 2 personas consultadas.")
        self.assertContains(detail, "100 %")
        self.assertNotContains(detail, "Publicar resultado")
        self.assertNotIn("roll", detail.context)
        self.assertContains(self.client.get(reverse("panel-polls")), "1 / 2")

    def test_publish_is_refused_while_voting_is_open(self):
        poll = self.open_poll()
        response = self.post(poll, action="publish")
        self.assertContains(response, "Solo se publica el resultado cuando ha terminado el plazo de votación.")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.OPEN)

    def test_cancel_requires_a_reason(self):
        poll = self.open_poll()
        response = self.post(poll, action="cancel", reason="  ")
        self.assertContains(response, "Indica el motivo de la anulación.")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.OPEN)

    def test_cancel_open_poll(self):
        poll = self.open_poll()
        services.cast_vote(poll, self.musician, poll.options.first().pk)
        response = self.post(poll, action="cancel", reason="Se aplaza el viaje")
        self.assertContains(response, "Encuesta anulada. Se ha avisado a 2 personas consultadas.")
        self.assertContains(response, "Se aplaza el viaje")
        self.assertNotContains(response, "Recuento provisional")
        self.assertNotContains(response, "Resultado definitivo")
        self.assertNotContains(response, "Ana Anónima")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.CANCELLED)

    # Plazo vencido y publicación

    def test_after_the_deadline_board_sees_roll_and_publishes(self):
        poll = self.open_poll()
        services.cast_vote(poll, self.musician, poll.options.get(label="Alacant").pk)
        self.expire(poll)
        page = self.client.get(self.detail_url(poll))
        self.assertContains(page, "Plazo vencido, pendiente de publicar")
        self.assertContains(page, "Recuento provisional")
        self.assertContains(page, "Publicar resultado")
        self.assertContains(page, "definitiva")
        roll = {recipient.member: recipient.has_voted for recipient in page.context["roll"]}
        self.assertEqual(roll, {self.ana: True, self.biel: False})
        self.assertContains(page, "Ana Anónima")
        self.assertContains(page, "Biel Bosch")

        response = self.post(poll, action="publish")
        self.assertContains(response, "Resultado publicado. Se ha avisado a 2 personas consultadas.")
        self.assertContains(response, "Resultado definitivo")
        self.assertContains(response, "Votos emitidos: 1 de 2 personas consultadas.")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.PUBLISHED)
        self.assertIsNotNone(poll.published_at)
        self.assertNotContains(response, "Publicar resultado")
        self.assertNotContains(response, "Anular y avisar")

    def test_cancel_after_the_deadline(self):
        poll = self.open_poll()
        self.expire(poll)
        self.post(poll, action="cancel", reason="Pocos votos")
        poll.refresh_from_db()
        self.assertEqual(poll.status, Poll.Status.CANCELLED)
        self.assertEqual(poll.cancel_reason, "Pocos votos")

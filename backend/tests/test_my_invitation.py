"""Lo que el musico ve de su propia convocatoria y su transporte, y el enlace del panel."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.activities.models import Activity, Invitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members.models import Member
from apps.transport.models import Transport, TransportAssignment


class MyInvitationTests(TestCase):
    def setUp(self):
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.musician = self._person("musica@example.invalid", AssociationRole.Role.MEMBER, "Musica")
        self.colleague = self._person("company@example.invalid", AssociationRole.Role.MEMBER, "Company")
        self.board = self._person("junta@example.invalid", AssociationRole.Role.BOARD, "Junta")
        start = timezone.now() + timedelta(days=3)
        self.activity = Activity.objects.create(
            association=self.association,
            created_by=self.board[0],
            kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED,
            title="Processó",
            starts_at=start,
        )
        self.own = Invitation.objects.create(activity=self.activity, member=self.musician[1], response="accepted")
        Invitation.objects.create(activity=self.activity, member=self.colleague[1])
        bus = Transport.objects.create(
            activity=self.activity,
            kind=Transport.Kind.CAR,
            label="Coche de Junta",
            meeting_point="Plaça",
            departure_at=start - timedelta(hours=1),
            capacity=4,
            driver=self.board[1],
        )
        TransportAssignment.objects.create(transport=bus, member=self.musician[1])

    def _person(self, email, role, name):
        account = get_user_model().objects.create_user(username=email, email=email, password="secret-password")
        access = AssociationAccess.objects.create(association=self.association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        member = Member.objects.create(association=self.association, first_name=name, last_name="Prova", account=account)
        return account, member

    def get_activity(self, account):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=account).key}")
        return client.get(f"/api/v1/activities/{self.activity.pk}/?association_id={self.association.pk}").json()

    def test_the_musician_gets_their_response_and_transport(self):
        data = self.get_activity(self.musician[0])

        self.assertEqual(data["my_invitation"]["id"], str(self.own.pk))
        self.assertEqual(data["my_invitation"]["response"], "accepted")
        self.assertEqual(data["my_transport"]["label"], "Coche de Junta")
        self.assertEqual(data["my_transport"]["meeting_point"], "Plaça")
        self.assertEqual(data["my_transport"]["driver_name"], str(self.board[1]))

    def test_without_an_assignment_there_is_no_transport(self):
        data = self.get_activity(self.colleague[0])

        self.assertEqual(data["my_invitation"]["response"], "pending")
        self.assertIsNone(data["my_transport"])

    def test_a_board_member_who_is_not_invited_has_no_own_invitation(self):
        data = self.get_activity(self.board[0])

        self.assertIsNone(data["my_invitation"])
        self.assertEqual(len(data["invitations"]), 2, "la junta sigue viendo la lista completa")

    def test_the_dashboard_links_to_the_panel_not_to_the_api(self):
        self.client.force_login(self.board[0])

        page = self.client.get(f"/panel/?association_id={self.association.pk}").content.decode()

        self.assertIn(f'href="/panel/activities/{self.activity.pk}/', page)
        self.assertNotIn(f"/api/v1/activities/{self.activity.pk}", page)

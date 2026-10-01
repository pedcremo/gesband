from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.associations.models import Association, AssociationAccess, AssociationRole


class PanelLoginTests(TestCase):
    """Una cuenta creada por invitacion tiene un usuario interno: entra con su correo."""

    def setUp(self):
        self.account = get_user_model().objects.create_user(
            username="member-0f3a9c", email="Junta@Example.invalid", password="secret-password"
        )
        association = Association.objects.create(name="Banda Test", slug="banda-test")
        access = AssociationAccess.objects.create(association=association, account=self.account)
        AssociationRole.objects.create(access=access, role=AssociationRole.Role.BOARD)

    def login(self, identifier, password="secret-password"):
        return self.client.post("/accounts/login/", {"username": identifier, "password": password}, follow=True)

    def test_the_email_opens_the_panel_whatever_its_case(self):
        response = self.login(" junta@example.INVALID ")

        self.assertEqual(response.redirect_chain[-1][0], "/panel/")
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.account.pk)

    def test_the_internal_username_still_works(self):
        self.login("member-0f3a9c")

        self.assertEqual(int(self.client.session["_auth_user_id"]), self.account.pk)

    def test_a_wrong_password_with_the_email_is_rejected(self):
        response = self.login("junta@example.invalid", password="wrong-password")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertTrue(response.context["form"].errors)

    def test_an_unknown_email_is_rejected_like_a_wrong_password(self):
        response = self.login("nadie@example.invalid")

        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(
            response.context["form"].non_field_errors(),
            self.login("junta@example.invalid", password="wrong-password").context["form"].non_field_errors(),
        )

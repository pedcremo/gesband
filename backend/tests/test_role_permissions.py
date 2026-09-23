from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.associations.models import Association, AssociationAccess, AssociationRole


class AnnouncedPermissionsMatchTheServerTests(APITestCase):
    """Lo que /auth/me promete tiene que ser lo que la API concede."""

    def setUp(self):
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")

    def account_with_role(self, role):
        account = get_user_model().objects.create_user(
            username=f"{role}@example.invalid", email=f"{role}@example.invalid", password="secret-password"
        )
        access = AssociationAccess.objects.create(association=self.association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def client_for(self, account):
        token, _ = Token.objects.get_or_create(user=account)
        client = self.client_class()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return client

    def announced_permissions(self, account):
        body = self.client_for(account).get("/api/v1/auth/me").json()
        association = next(item for item in body["associations"] if item["slug"] == self.association.slug)
        return set(association["permissions"])

    def activities_status(self, account):
        return self.client_for(account).get("/api/v1/activities/", {"association_id": self.association.id}).status_code

    def test_participant_roles_are_promised_activities_and_get_them(self):
        for role in [
            AssociationRole.Role.MEMBER,
            AssociationRole.Role.BOARD,
            AssociationRole.Role.ORGANIZER,
            AssociationRole.Role.DIRECTOR,
            AssociationRole.Role.ADMIN,
        ]:
            with self.subTest(role=role):
                account = self.account_with_role(role)
                self.assertIn("activities.view", self.announced_permissions(account))
                self.assertEqual(self.activities_status(account), 200)

    def test_platform_and_web_editor_are_not_promised_what_they_cannot_read(self):
        for role in [AssociationRole.Role.PLATFORM, AssociationRole.Role.WEB_EDITOR]:
            with self.subTest(role=role):
                account = self.account_with_role(role)
                self.assertNotIn("activities.view", self.announced_permissions(account))
                self.assertEqual(self.activities_status(account), 403)

    def test_every_role_keeps_the_permissions_that_are_per_account(self):
        for role in AssociationRole.Role.values:
            with self.subTest(role=role):
                announced = self.announced_permissions(self.account_with_role(role))
                self.assertIn("association.view", announced)
                self.assertIn("notifications.view", announced)
                self.assertIn("devices.manage_own", announced)

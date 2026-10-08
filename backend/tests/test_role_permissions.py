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

    def panel_status(self, account, path):
        from django.test import Client

        client = Client()
        client.force_login(account)
        return client.get(f"{path}?association_id={self.association.id}").status_code

    def test_access_and_role_management_is_promised_and_granted_to_admin_and_board_only(self):
        # Decision 0009: invitaciones, accesos y roles son de `admin` y `board`.
        for role in AssociationRole.Role.values:
            with self.subTest(role=role):
                account = self.account_with_role(role)
                announced = self.announced_permissions(account)
                manages = role in {AssociationRole.Role.ADMIN, AssociationRole.Role.BOARD}
                self.assertEqual("accounts.manage" in announced, manages)
                self.assertEqual("roles.manage" in announced, manages)
                expected = 200 if manages else 403
                self.assertEqual(self.panel_status(account, "/panel/access/"), expected)
                self.assertEqual(self.panel_status(account, "/panel/members/access/"), expected)

    def test_census_management_is_promised_and_granted_to_the_four_manager_roles(self):
        managers = {
            AssociationRole.Role.ADMIN,
            AssociationRole.Role.BOARD,
            AssociationRole.Role.ORGANIZER,
            AssociationRole.Role.DIRECTOR,
        }
        for role in AssociationRole.Role.values:
            with self.subTest(role=role):
                account = self.account_with_role(role)
                announced = self.announced_permissions(account)
                self.assertEqual("members.manage" in announced, role in managers)
                self.assertEqual(self.panel_status(account, "/panel/members/new/"), 200 if role in managers else 403)
                created = self.client_for(account).post(
                    "/api/v1/members/",
                    {"first_name": "Prova", "last_name": role},
                    format="json",
                    HTTP_X_ASSOCIATION_ID=str(self.association.id),
                )
                self.assertEqual(created.status_code, 201 if role in managers else 403)

    def test_physical_deletion_is_promised_and_granted_to_admin_only(self):
        from apps.members.models import Member

        for role in AssociationRole.Role.values:
            with self.subTest(role=role):
                account = self.account_with_role(role)
                is_admin = role == AssociationRole.Role.ADMIN
                self.assertEqual("members.delete" in self.announced_permissions(account), is_admin)
                member = Member.objects.create(association=self.association, first_name="Sense", last_name=role)
                deleted = self.client_for(account).delete(
                    f"/api/v1/members/{member.id}/", HTTP_X_ASSOCIATION_ID=str(self.association.id)
                )
                self.assertEqual(deleted.status_code, 204 if is_admin else 403)

    def test_my_access_page_explains_the_new_capabilities(self):
        from django.test import Client

        board = self.account_with_role(AssociationRole.Role.BOARD)
        client = Client()
        client.force_login(board)
        response = client.get(f"/panel/me/?association_id={self.association.id}")
        capabilities = {item["permission"]: item["allowed"] for item in response.context["capabilities"]}
        self.assertTrue(capabilities["accounts.manage"])
        self.assertTrue(capabilities["roles.manage"])
        self.assertFalse(capabilities["members.delete"])

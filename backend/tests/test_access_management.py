"""Accesos, invitaciones y roles desde el panel (decisión 0009).

`admin` y `board` gestionan; solo `admin` concede o quita `admin`; nunca queda
una asociación sin `admin` activo; `platform` y `web_editor` no se asignan
desde el panel. Todos los datos son sintéticos.
"""

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.test import Client, TestCase, override_settings

from apps.accounts import services
from apps.accounts.models import AccessChange, AccessInvitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members.models import Member

Role = AssociationRole.Role


class AccessFixture(TestCase):
    def setUp(self):
        self.association = Association.objects.create(name="Banda Sintética", slug="banda-sintetica")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.accounts = {}
        self.accesses = {}
        for role in Role.values:
            self.accounts[role], self.accesses[role] = self.account_with_roles(role, [role])
        # Una cuenta que es `admin` aquí y solo `member` en la otra asociación.
        self.other_admin, self.other_admin_access = self.account_with_roles(
            "other-admin", [Role.ADMIN], self.other_association
        )
        self.dual = self.accounts[Role.ADMIN]
        self.dual_other_access = AssociationAccess.objects.create(association=self.other_association, account=self.dual)
        AssociationRole.objects.create(access=self.dual_other_access, role=Role.MEMBER)

    def account_with_roles(self, label, roles, association=None):
        association = association or self.association
        account = get_user_model().objects.create_user(
            username=f"{label}-{association.slug}@example.invalid",
            email=f"{label}-{association.slug}@example.invalid",
            password="synthetic-password",
        )
        access = AssociationAccess.objects.create(association=association, account=account)
        for role in roles:
            AssociationRole.objects.create(access=access, role=role)
        return account, access

    def roles_of(self, access):
        return set(access.role_assignments.values_list("role", flat=True))

    def panel(self, account):
        client = Client()
        client.force_login(account)
        return client


class RoleServiceTests(AccessFixture):
    def test_board_and_admin_grant_and_revoke_ordinary_roles_with_a_trace(self):
        for actor_role in [Role.ADMIN, Role.BOARD]:
            with self.subTest(actor=actor_role):
                actor = self.accounts[actor_role]
                target = self.accesses[Role.MEMBER]
                self.assertTrue(
                    services.grant_role(actor=actor, association=self.association, access=target, role=Role.ORGANIZER)
                )
                self.assertFalse(
                    services.grant_role(actor=actor, association=self.association, access=target, role=Role.ORGANIZER)
                )
                self.assertIn(Role.ORGANIZER, self.roles_of(target))
                services.revoke_role(actor=actor, association=self.association, access=target, role=Role.ORGANIZER)
                self.assertNotIn(Role.ORGANIZER, self.roles_of(target))
                self.assertEqual(
                    list(
                        AccessChange.objects.filter(access=target, actor=actor)
                        .order_by("created_at")
                        .values_list("action", "role")
                    ),
                    [("role_granted", "organizer"), ("role_revoked", "organizer")],
                )

    def test_organizer_director_and_others_cannot_manage_roles(self):
        for role in [Role.ORGANIZER, Role.DIRECTOR, Role.MEMBER, Role.PLATFORM, Role.WEB_EDITOR]:
            with self.subTest(role=role):
                with self.assertRaises(PermissionDenied):
                    services.grant_role(
                        actor=self.accounts[role],
                        association=self.association,
                        access=self.accesses[Role.MEMBER],
                        role=Role.BOARD,
                    )
                with self.assertRaises(PermissionDenied):
                    services.set_access_active(
                        actor=self.accounts[role],
                        association=self.association,
                        access=self.accesses[Role.MEMBER],
                        active=False,
                    )
        self.assertEqual(self.roles_of(self.accesses[Role.MEMBER]), {Role.MEMBER})

    def test_board_cannot_grant_admin_to_anyone_including_itself(self):
        board = self.accounts[Role.BOARD]
        for target in [self.accesses[Role.BOARD], self.accesses[Role.MEMBER]]:
            with self.subTest(target=target.account.email), self.assertRaises(PermissionDenied):
                services.grant_role(actor=board, association=self.association, access=target, role=Role.ADMIN)
            self.assertNotIn(Role.ADMIN, self.roles_of(target))

    def test_board_cannot_remove_admin_nor_switch_off_an_admin(self):
        board = self.accounts[Role.BOARD]
        self.account_with_roles("second-admin", [Role.ADMIN])
        with self.assertRaises(PermissionDenied):
            services.revoke_role(
                actor=board, association=self.association, access=self.accesses[Role.ADMIN], role=Role.ADMIN
            )
        with self.assertRaises(PermissionDenied):
            services.set_access_active(
                actor=board, association=self.association, access=self.accesses[Role.ADMIN], active=False
            )
        self.accesses[Role.ADMIN].refresh_from_db()
        self.assertTrue(self.accesses[Role.ADMIN].is_active)
        self.assertIn(Role.ADMIN, self.roles_of(self.accesses[Role.ADMIN]))

    def test_admin_grants_and_removes_admin_but_never_the_last_one(self):
        admin = self.accounts[Role.ADMIN]
        with self.assertRaises(ValidationError):
            services.revoke_role(
                actor=admin, association=self.association, access=self.accesses[Role.ADMIN], role=Role.ADMIN
            )
        services.grant_role(
            actor=admin, association=self.association, access=self.accesses[Role.BOARD], role=Role.ADMIN
        )
        services.revoke_role(
            actor=admin, association=self.association, access=self.accesses[Role.ADMIN], role=Role.ADMIN
        )
        self.assertNotIn(Role.ADMIN, self.roles_of(self.accesses[Role.ADMIN]))
        new_admin = self.accounts[Role.BOARD]
        with self.assertRaises(ValidationError):
            services.revoke_role(
                actor=new_admin, association=self.association, access=self.accesses[Role.BOARD], role=Role.ADMIN
            )

    def test_an_inactive_admin_does_not_count_as_the_remaining_admin(self):
        _account, second = self.account_with_roles("second-admin", [Role.ADMIN])
        second.is_active = False
        second.save()
        with self.assertRaises(ValidationError):
            services.revoke_role(
                actor=self.accounts[Role.ADMIN],
                association=self.association,
                access=self.accesses[Role.ADMIN],
                role=Role.ADMIN,
            )

    def test_platform_and_web_editor_are_not_assigned_from_the_panel(self):
        for role in [Role.PLATFORM, Role.WEB_EDITOR]:
            with self.subTest(role=role):
                with self.assertRaises(ValidationError):
                    services.grant_role(
                        actor=self.accounts[Role.ADMIN],
                        association=self.association,
                        access=self.accesses[Role.MEMBER],
                        role=role,
                    )
                with self.assertRaises(ValidationError):
                    services.revoke_role(
                        actor=self.accounts[Role.ADMIN], association=self.association, access=self.accesses[role], role=role
                    )
                self.assertIn(role, self.roles_of(self.accesses[role]))
        with self.assertRaises(ValidationError):
            services.grant_role(
                actor=self.accounts[Role.ADMIN], association=self.association, access=self.accesses[Role.MEMBER], role="owner"
            )

    def test_access_of_another_association_is_not_found(self):
        with self.assertRaises(Http404):
            services.grant_role(
                actor=self.accounts[Role.ADMIN],
                association=self.association,
                access=self.other_admin_access,
                role=Role.BOARD,
            )
        # Siendo solo `member` en la otra asociación, no gestiona allí.
        with self.assertRaises(PermissionDenied):
            services.grant_role(
                actor=self.dual, association=self.other_association, access=self.other_admin_access, role=Role.BOARD
            )
        with self.assertRaises(PermissionDenied):
            services.set_access_active(
                actor=self.dual, association=self.other_association, access=self.other_admin_access, active=False
            )
        self.assertEqual(self.roles_of(self.other_admin_access), {Role.ADMIN})

    def test_deactivation_keeps_the_account_and_other_associations(self):
        target = self.dual_other_access
        services.set_access_active(
            actor=self.other_admin, association=self.other_association, access=target, active=False
        )
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        self.dual.refresh_from_db()
        self.assertTrue(self.dual.is_active)
        self.assertTrue(AssociationAccess.objects.get(association=self.association, account=self.dual).is_active)
        self.assertEqual(self.roles_of(target), {Role.MEMBER})
        with self.assertRaises(ValidationError):
            services.grant_role(
                actor=self.other_admin, association=self.other_association, access=target, role=Role.BOARD
            )
        services.set_access_active(actor=self.other_admin, association=self.other_association, access=target, active=True)
        target.refresh_from_db()
        self.assertTrue(target.is_active)
        self.assertEqual(
            list(AccessChange.objects.filter(access=target).order_by("created_at").values_list("action", flat=True)),
            ["access_deactivated", "access_reactivated"],
        )

    def test_nobody_switches_off_their_own_access_nor_the_last_admin(self):
        with self.assertRaises(ValidationError):
            services.set_access_active(
                actor=self.accounts[Role.BOARD],
                association=self.association,
                access=self.accesses[Role.BOARD],
                active=False,
            )
        superuser = get_user_model().objects.create_superuser(
            username="root@example.invalid", email="root@example.invalid", password="synthetic-password"
        )
        with self.assertRaises(ValidationError):
            services.set_access_active(
                actor=superuser, association=self.association, access=self.accesses[Role.ADMIN], active=False
            )
        self.accesses[Role.ADMIN].refresh_from_db()
        self.assertTrue(self.accesses[Role.ADMIN].is_active)

    def test_invitations_are_for_admin_and_board_only(self):
        member = Member.objects.create(
            association=self.association, first_name="Nova", last_name="Musica", email="nova@example.invalid"
        )
        for role in [Role.ORGANIZER, Role.DIRECTOR, Role.MEMBER]:
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                services.issue_access_invitation(member=member, created_by=self.accounts[role])
        invitation, _token = services.issue_access_invitation(member=member, created_by=self.accounts[Role.BOARD])
        with self.assertRaises(PermissionDenied):
            services.revoke_access_invitation(invitation=invitation, revoked_by=self.accounts[Role.DIRECTOR])
        with self.assertRaises(PermissionDenied):
            services.revoke_access_invitation(invitation=invitation, revoked_by=self.other_admin)
        services.revoke_access_invitation(invitation=invitation, revoked_by=self.accounts[Role.BOARD])
        invitation.refresh_from_db()
        self.assertEqual(invitation.revoked_by, self.accounts[Role.BOARD])


class AccessPanelTests(AccessFixture):
    url = "/panel/access/"

    def page(self, association=None):
        return f"{self.url}?association_id={(association or self.association).id}"

    def post(self, account, data, association=None):
        association = association or self.association
        return self.panel(account).post(self.url, {"association_id": association.id, **data})

    def test_role_matrix_for_access_pages(self):
        for role in Role.values:
            with self.subTest(role=role):
                client = self.panel(self.accounts[role])
                expected = 200 if role in [Role.ADMIN, Role.BOARD] else 403
                self.assertEqual(client.get(self.page()).status_code, expected)
                self.assertEqual(
                    client.get(f"/panel/members/access/?association_id={self.association.id}").status_code, expected
                )

    def test_account_in_two_associations_only_manages_where_it_is_admin(self):
        client = self.panel(self.dual)
        self.assertEqual(client.get(self.page()).status_code, 200)
        self.assertEqual(client.get(self.page(self.other_association)).status_code, 403)
        response = self.post(
            self.dual,
            {"access_id": self.other_admin_access.id, "action": "grant_role", "role": Role.BOARD},
            self.other_association,
        )
        self.assertEqual(response.status_code, 403)
        # Un acceso ajeno con la asociación propia en la petición: 404.
        response = self.post(self.dual, {"access_id": self.other_admin_access.id, "action": "grant_role", "role": Role.BOARD})
        self.assertEqual(response.status_code, 404)
        response = self.post(self.dual, {"access_id": "1 OR 1=1", "action": "grant_role", "role": Role.BOARD})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.roles_of(self.other_admin_access), {Role.ADMIN})

    def test_page_lists_accesses_and_never_offers_platform_roles(self):
        response = self.panel(self.accounts[Role.BOARD]).get(self.page())
        self.assertContains(response, self.accounts[Role.MEMBER].email)
        self.assertNotContains(response, f'value="{Role.PLATFORM}"')
        self.assertNotContains(response, f'value="{Role.WEB_EDITOR}"')
        self.assertNotContains(response, self.other_admin.email)

    def test_board_grants_a_role_from_the_panel(self):
        target = self.accesses[Role.MEMBER]
        response = self.post(
            self.accounts[Role.BOARD], {"access_id": target.id, "action": "grant_role", "role": Role.DIRECTOR}
        )
        self.assertRedirects(response, self.page(), fetch_redirect_response=False)
        self.assertIn(Role.DIRECTOR, self.roles_of(target))

    def test_board_trying_to_grant_admin_gets_an_error_and_nothing_changes(self):
        board = self.accounts[Role.BOARD]
        response = self.panel(board).post(
            self.url,
            {"association_id": self.association.id, "access_id": self.accesses[Role.BOARD].id, "action": "grant_role", "role": Role.ADMIN},
            follow=True,
        )
        self.assertContains(response, "Solo una cuenta con rol de administración")
        self.assertNotIn(Role.ADMIN, self.roles_of(self.accesses[Role.BOARD]))

    def test_removing_a_role_asks_for_confirmation(self):
        target = self.accesses[Role.DIRECTOR]
        admin = self.accounts[Role.ADMIN]
        response = self.post(admin, {"access_id": target.id, "action": "revoke_role", "role": Role.DIRECTOR})
        self.assertContains(response, "Quitar rol")
        self.assertIn(Role.DIRECTOR, self.roles_of(target))
        self.post(admin, {"access_id": target.id, "action": "revoke_role", "role": Role.DIRECTOR, "confirmed": "1"})
        self.assertNotIn(Role.DIRECTOR, self.roles_of(target))

    def test_last_admin_cannot_be_removed_from_the_panel(self):
        admin = self.accounts[Role.ADMIN]
        response = self.panel(admin).post(
            self.url,
            {
                "association_id": self.association.id,
                "access_id": self.accesses[Role.ADMIN].id,
                "action": "revoke_role",
                "role": Role.ADMIN,
                "confirmed": "1",
            },
            follow=True,
        )
        self.assertContains(response, "sin ninguna cuenta de administración activa")
        self.assertIn(Role.ADMIN, self.roles_of(self.accesses[Role.ADMIN]))

    def test_deactivate_with_confirmation_and_reactivate(self):
        target = self.accesses[Role.MEMBER]
        board = self.accounts[Role.BOARD]
        response = self.post(board, {"access_id": target.id, "action": "deactivate"})
        self.assertContains(response, "Desactivar acceso")
        target.refresh_from_db()
        self.assertTrue(target.is_active)
        self.post(board, {"access_id": target.id, "action": "deactivate", "confirmed": "1"})
        target.refresh_from_db()
        self.assertFalse(target.is_active)
        # Sin acceso activo, la cuenta deja de ver la asociación en la API.
        self.assertEqual(self.panel(self.accounts[Role.MEMBER]).get(f"/panel/me/?association_id={self.association.id}").status_code, 403)
        self.post(board, {"access_id": target.id, "action": "reactivate"})
        target.refresh_from_db()
        self.assertTrue(target.is_active)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_board_can_now_send_access_invitations(self):
        member = Member.objects.create(
            association=self.association, first_name="Nova", last_name="Musica", email="nova@example.invalid"
        )
        response = self.panel(self.accounts[Role.BOARD]).post(
            f"/panel/members/access/?association_id={self.association.id}",
            {"association_id": self.association.id, "action": "invite_selected", "member_ids": [member.id]},
        )
        self.assertEqual(response.status_code, 302)
        invitation = AccessInvitation.objects.get(member=member)
        self.assertEqual(invitation.created_by, self.accounts[Role.BOARD])
        self.assertEqual(len(mail.outbox), 1)
        response = self.panel(self.accounts[Role.ORGANIZER]).post(
            f"/panel/members/access/?association_id={self.association.id}",
            {"association_id": self.association.id, "revoke_id": invitation.id},
        )
        self.assertEqual(response.status_code, 403)

    def test_import_stays_admin_only(self):
        for role, expected in [(Role.ADMIN, 200), (Role.BOARD, 403), (Role.ORGANIZER, 403), (Role.DIRECTOR, 403)]:
            with self.subTest(role=role):
                response = self.panel(self.accounts[role]).get(
                    f"/panel/members/import/?association_id={self.association.id}"
                )
                self.assertEqual(response.status_code, expected)

    def test_access_page_is_translated_to_valencian(self):
        client = self.panel(self.accounts[Role.ADMIN])
        client.cookies["django_language"] = "ca"
        response = client.get(self.page())
        self.assertContains(response, "Accessos i rols")
        self.assertContains(response, "Concedir rol")

import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.activities.models import Activity, Invitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.associations.permissions import CAPABILITIES, permissions_for
from apps.communications.models import Notification
from apps.members.models import Instrument, Member, MemberInstrument, Section


def local(moment):
    return timezone.localtime(moment).strftime("%Y-%m-%dT%H:%M")


class PanelTestCase(TestCase):
    def setUp(self):
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.starts_at = timezone.now() + timedelta(days=7)

    def account_with_roles(self, *roles, association=None):
        association = association or self.association
        email = f"{'-'.join(roles) or 'sin-rol'}-{association.slug}@example.invalid"
        account = get_user_model().objects.create_user(username=email, email=email, password="secret-password")
        access = AssociationAccess.objects.create(association=association, account=account)
        for role in roles:
            AssociationRole.objects.create(access=access, role=role)
        return account

    def web_for(self, account):
        client = Client()
        client.force_login(account)
        return client

    def musician(self, first_name, association=None, **extra):
        return Member.objects.create(
            association=association or self.association,
            first_name=first_name,
            last_name="Test",
            **extra,
        )


class ActivityCreationTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.board = self.account_with_roles(AssociationRole.Role.BOARD)
        self.url = f"/panel/activities/new/?association_id={self.association.id}"

    def form_data(self, **extra):
        data = {
            "kind": Activity.Kind.PERFORMANCE,
            "title": "Processó de Sant Roc",
            "starts_at": local(self.starts_at),
            "ends_at": local(self.starts_at + timedelta(hours=2)),
            "meeting_at": local(self.starts_at - timedelta(minutes=30)),
            "location": "Plaça Major",
            "uniform": "Gala",
            "response_deadline": local(self.starts_at - timedelta(days=2)),
            "is_mandatory": "on",
            "description": "Recorregut habitual",
            "programme": "Paquito el chocolatero | de pasacalle\n\n  Amparito Roca  \n",
        }
        data.update(extra)
        return data

    def test_dashboard_offers_the_new_activity_button(self):
        page = self.web_for(self.board).get(f"/panel/?association_id={self.association.id}")
        self.assertContains(page, "/panel/activities/new/")

    def test_board_creates_a_draft_with_programme_and_lands_on_its_detail(self):
        response = self.web_for(self.board).post(self.url, self.form_data())

        activity = Activity.objects.get()
        self.assertRedirects(
            response,
            f"/panel/activities/{activity.id}/?association_id={self.association.id}",
            fetch_redirect_response=False,
        )
        self.assertEqual(activity.association, self.association)
        self.assertEqual(activity.created_by, self.board)
        self.assertEqual(activity.status, Activity.Status.DRAFT)
        self.assertEqual(activity.kind, Activity.Kind.PERFORMANCE)
        self.assertTrue(activity.is_mandatory)
        self.assertEqual(activity.location, "Plaça Major")
        self.assertEqual(
            list(activity.programme.values_list("title", "notes", "order")),
            [("Paquito el chocolatero", "de pasacalle", 0), ("Amparito Roca", "", 1)],
        )
        self.assertFalse(Notification.objects.exists())
        detail = self.web_for(self.board).get(response["Location"])
        self.assertContains(detail, "Amparito Roca")

    def test_admin_can_create_and_then_publish(self):
        admin = self.account_with_roles(AssociationRole.Role.ADMIN)
        web = self.web_for(admin)
        response = web.post(self.url, self.form_data(programme=""))
        activity = Activity.objects.get()
        web.post(response["Location"], {"publish": "1"})
        activity.refresh_from_db()
        self.assertEqual(activity.status, Activity.Status.PUBLISHED)
        self.assertFalse(activity.programme.exists())

    def test_model_validation_rejects_an_end_before_the_start(self):
        response = self.web_for(self.board).post(
            self.url, self.form_data(ends_at=local(self.starts_at - timedelta(hours=1)))
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El final no puede ser anterior al inicio.")
        self.assertFalse(Activity.objects.exists())

    def test_programme_notes_without_title_are_rejected(self):
        response = self.web_for(self.board).post(self.url, self.form_data(programme="| solo notas"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tiene notas pero no título")
        self.assertFalse(Activity.objects.exists())

    def test_member_cannot_create_activities(self):
        member = self.account_with_roles(AssociationRole.Role.MEMBER)
        web = self.web_for(member)
        self.assertEqual(web.get(self.url).status_code, 403)
        self.assertEqual(web.post(self.url, self.form_data()).status_code, 403)
        self.assertFalse(Activity.objects.exists())

    def test_board_of_another_association_cannot_create_here(self):
        outsider = self.account_with_roles(AssociationRole.Role.BOARD, association=self.other_association)
        response = self.web_for(outsider).post(self.url, self.form_data())
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Activity.objects.exists())

    def test_forbidden_page_points_to_my_access(self):
        member = self.account_with_roles(AssociationRole.Role.MEMBER)
        page = self.web_for(member).get(self.url)
        self.assertContains(page, "/panel/me/", status_code=403)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class SelectiveInvitationTests(PanelTestCase):
    def setUp(self):
        super().setUp()
        self.board = self.account_with_roles(AssociationRole.Role.BOARD)
        self.web = self.web_for(self.board)
        self.metal = Section.objects.create(association=self.association, name="Metal")
        self.wood = Section.objects.create(association=self.association, name="Madera")
        self.trumpet = Instrument.objects.create(association=self.association, name="Trompeta", section=self.metal)
        self.trombone = Instrument.objects.create(association=self.association, name="Trombón", section=self.metal)
        self.clarinet = Instrument.objects.create(association=self.association, name="Clarinete", section=self.wood)
        self.flute = Instrument.objects.create(association=self.association, name="Flauta", section=self.wood)
        self.trumpeter = self.plays("Trompetista", self.trumpet)
        self.trombonist = self.plays("Trombonista", self.trombone)
        self.clarinettist = self.plays("Clarinetista", self.clarinet)
        self.flautist = self.plays("Flautista", self.flute)
        self.retired = self.plays("Retirado", self.trumpet, status=Member.Status.INACTIVE)
        self.patron = self.musician("Mecenas", kind=Member.Kind.SUPPORTER)
        foreign_section = Section.objects.create(association=self.other_association, name="Metal")
        foreign_instrument = Instrument.objects.create(
            association=self.other_association, name="Trompeta", section=foreign_section
        )
        self.foreign_section = foreign_section
        self.foreign_instrument = foreign_instrument
        self.foreign_member = self.musician("Ajeno", association=self.other_association)
        MemberInstrument.objects.create(member=self.foreign_member, instrument=foreign_instrument, is_primary=True)
        self.activity = Activity.objects.create(
            association=self.association,
            created_by=self.board,
            kind=Activity.Kind.REHEARSAL,
            title="Ensayo parcial",
            starts_at=self.starts_at,
        )
        self.url = f"/panel/activities/{self.activity.id}/?association_id={self.association.id}"

    def plays(self, first_name, instrument, **extra):
        member = self.musician(first_name, **extra)
        MemberInstrument.objects.create(member=member, instrument=instrument, is_primary=True)
        return member

    def invite(self, **selection):
        return self.web.post(self.url, {"invite_selected": "1", **selection}, follow=True)

    def invited(self):
        return set(self.activity.invitations.values_list("member_id", flat=True))

    def test_detail_lists_sections_instruments_and_active_musicians_only(self):
        page = self.web.get(self.url)
        self.assertContains(page, f'name="section_ids" value="{self.metal.id}"')
        self.assertContains(page, f'name="instrument_ids" value="{self.flute.id}"')
        self.assertContains(page, f'name="member_ids" value="{self.trumpeter.id}"')
        self.assertNotContains(page, f'value="{self.retired.id}"')
        self.assertNotContains(page, f'value="{self.patron.id}"')
        self.assertNotContains(page, f'value="{self.foreign_member.id}"')
        self.assertNotContains(page, f'name="section_ids" value="{self.foreign_section.id}"')
        self.assertNotContains(page, f'name="instrument_ids" value="{self.foreign_instrument.id}"')

    def test_invites_a_whole_section(self):
        response = self.invite(section_ids=[self.metal.id])
        self.assertEqual(self.invited(), {self.trumpeter.id, self.trombonist.id})
        self.assertContains(response, "2 nuevas")

    def test_invites_by_instrument(self):
        self.invite(instrument_ids=[self.clarinet.id])
        self.assertEqual(self.invited(), {self.clarinettist.id})

    def test_invites_individual_people_and_combines_criteria(self):
        self.invite(member_ids=[self.flautist.id], instrument_ids=[self.trombone.id])
        self.assertEqual(self.invited(), {self.flautist.id, self.trombonist.id})

    def test_repeating_the_selection_does_not_duplicate(self):
        self.invite(section_ids=[self.metal.id])
        response = self.invite(section_ids=[self.metal.id], member_ids=[self.flautist.id])
        self.assertEqual(Invitation.objects.filter(activity=self.activity).count(), 3)
        self.assertContains(response, "1 nuevas y 2 ya existentes")

    def test_ids_from_another_association_or_malformed_are_ignored(self):
        response = self.invite(
            section_ids=[self.foreign_section.id, "no-es-un-id"],
            instrument_ids=[self.foreign_instrument.id, "99999999"],
            member_ids=[self.foreign_member.id, "abc"],
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.invited(), set())
        self.assertContains(response, "no se ha convocado a nadie")

    def test_foreign_ids_mixed_with_valid_ones_only_invite_local_people(self):
        self.invite(member_ids=[self.foreign_member.id, self.trumpeter.id], instrument_ids=[self.foreign_instrument.id])
        self.assertEqual(self.invited(), {self.trumpeter.id})

    def test_inactive_and_supporters_are_skipped_even_if_sent(self):
        self.invite(member_ids=[self.retired.id, self.patron.id, self.clarinettist.id])
        self.assertEqual(self.invited(), {self.clarinettist.id})

    def test_empty_selection_reports_an_error(self):
        response = self.invite()
        self.assertContains(response, "Elige al menos una cuerda")
        self.assertEqual(self.invited(), set())

    def test_mandatory_flag_is_applied_like_the_invite_all_button(self):
        self.invite(section_ids=[self.wood.id], is_mandatory="1")
        self.activity.refresh_from_db()
        self.assertTrue(self.activity.is_mandatory)

    def test_a_draft_does_not_notify_but_a_published_activity_does(self):
        self.trumpeter.account = self.account_with_roles(AssociationRole.Role.MEMBER)
        self.trumpeter.save(update_fields=["account"])
        self.invite(section_ids=[self.wood.id])
        self.assertFalse(Notification.objects.filter(activity=self.activity).exists())
        self.web.post(self.url, {"publish": "1"})
        self.activity.refresh_from_db()
        self.assertEqual(self.activity.status, Activity.Status.PUBLISHED)
        before = Notification.objects.filter(activity=self.activity).count()
        self.invite(section_ids=[self.metal.id])
        self.assertEqual(Notification.objects.filter(activity=self.activity).count(), before + 1)
        self.assertEqual(len(self.invited()), 4)

    def test_member_cannot_invite(self):
        member = self.account_with_roles(AssociationRole.Role.MEMBER)
        response = self.web_for(member).post(self.url, {"invite_selected": "1", "section_ids": [self.metal.id]})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.invited(), set())


class MyAccessTests(PanelTestCase):
    url = "/panel/me/"

    def announced(self, account):
        token, _created = Token.objects.get_or_create(user=account)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        body = client.get("/api/v1/auth/me").json()
        association = next(item for item in body["associations"] if item["slug"] == self.association.slug)
        return set(association["permissions"])

    def shown(self, page):
        html = page.content.decode()
        rows = re.findall(r'data-permission="([^"]+)" data-allowed="(yes|no)"', html)
        allowed = {code for code, flag in rows if flag == "yes"}
        denied = {code for code, flag in rows if flag == "no"}
        return allowed, denied

    def test_every_role_sees_capabilities_consistent_with_auth_me(self):
        for role in AssociationRole.Role.values:
            with self.subTest(role=role):
                account = self.account_with_roles(role)
                page = self.web_for(account).get(f"{self.url}?association_id={self.association.id}")
                self.assertEqual(page.status_code, 200)
                allowed, denied = self.shown(page)
                announced = self.announced(account)
                capability_codes = {code for code, _label in CAPABILITIES}
                self.assertEqual(allowed, capability_codes & announced)
                self.assertEqual(denied, capability_codes - announced)
                self.assertContains(page, str(AssociationRole.Role(role).label))

    def test_board_can_manage_activities_but_not_configure(self):
        page = self.web_for(self.account_with_roles(AssociationRole.Role.BOARD)).get(self.url)
        allowed, denied = self.shown(page)
        self.assertIn("activities.manage", allowed)
        self.assertIn("polls.manage", allowed)
        self.assertIn("association.manage", denied)
        self.assertIn("imports.manage", denied)
        self.assertContains(page, "Ir al panel de la junta")

    def test_admin_can_do_everything_listed(self):
        page = self.web_for(self.account_with_roles(AssociationRole.Role.ADMIN)).get(self.url)
        allowed, denied = self.shown(page)
        self.assertEqual(denied, set())
        self.assertIn("association.manage", allowed)

    def test_member_sees_the_page_and_what_is_off_limits(self):
        page = self.web_for(self.account_with_roles(AssociationRole.Role.MEMBER)).get(self.url)
        self.assertEqual(page.status_code, 200)
        allowed, denied = self.shown(page)
        self.assertEqual(allowed, {"activities.view", "polls.view"})
        self.assertIn("members.view", denied)
        self.assertNotContains(page, "Ir al panel de la junta")
        self.assertContains(page, "aplicación del músico")

    def test_accumulated_roles_are_all_listed(self):
        account = self.account_with_roles(AssociationRole.Role.MEMBER, AssociationRole.Role.DIRECTOR)
        page = self.web_for(account).get(self.url)
        self.assertContains(page, "Músico")
        self.assertContains(page, "Dirección musical")
        self.assertIn("attendance.manage", self.shown(page)[0])

    def test_account_without_active_access_gets_403(self):
        account = self.account_with_roles(AssociationRole.Role.BOARD)
        AssociationAccess.objects.filter(account=account).update(is_active=False)
        self.assertEqual(self.web_for(account).get(self.url).status_code, 403)

    def test_cannot_inspect_an_association_without_access(self):
        account = self.account_with_roles(AssociationRole.Role.BOARD)
        response = self.web_for(account).get(f"{self.url}?association_id={self.other_association.id}")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.web_for(account).get(f"{self.url}?association_id=nope").status_code, 403)

    def test_anonymous_is_sent_to_login(self):
        response = Client().get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response["Location"])

    def test_navigation_links_to_my_access(self):
        page = self.web_for(self.account_with_roles(AssociationRole.Role.BOARD)).get(
            f"/panel/?association_id={self.association.id}"
        )
        self.assertContains(page, f"/panel/me/?association_id={self.association.id}")


class PermissionsForTests(PanelTestCase):
    def test_superuser_gets_everything(self):
        admin = get_user_model().objects.create_superuser(
            username="root@example.invalid", email="root@example.invalid", password="secret-password"
        )
        self.assertEqual(permissions_for(admin, self.association), ["*"])

    def test_no_access_means_no_permissions(self):
        account = self.account_with_roles(AssociationRole.Role.ADMIN, association=self.other_association)
        self.assertEqual(permissions_for(account, self.association), [])

    def test_output_is_sorted_and_keeps_polls(self):
        account = self.account_with_roles(AssociationRole.Role.BOARD)
        permissions = permissions_for(account, self.association)
        self.assertEqual(permissions, sorted(permissions))
        self.assertIn("polls.view", permissions)
        self.assertIn("polls.manage", permissions)

"""Fichas del censo desde el panel y la API (decisión 0009).

Altas, cambios, baja lógica reversible, borrado físico solo de `admin` y sin
historial, y fotos privadas validadas. Todos los datos son sintéticos.
"""

import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.activities.models import Activity, Attendance, Invitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members import services
from apps.members.models import Instrument, Member, MemberPosition, Section

Role = AssociationRole.Role
MANAGERS = [Role.ADMIN, Role.BOARD, Role.ORGANIZER, Role.DIRECTOR]
NON_MANAGERS = [Role.MEMBER, Role.PLATFORM, Role.WEB_EDITOR]


def png_upload(name="foto.png", size=(40, 30)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class CensusFixture(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = self.settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.association = Association.objects.create(name="Banda Sintética", slug="banda-sintetica")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.section = Section.objects.get(code="brass")
        self.trumpet = Instrument.objects.create(association=self.association, name="Trompeta", section=self.section)
        self.flute = Instrument.objects.create(association=self.association, name="Flauta")
        self.foreign_instrument = Instrument.objects.create(association=self.other_association, name="Tuba")
        self.accounts = {role: self.account_with_role(role) for role in Role.values}
        self.member = Member.objects.create(association=self.association, first_name="Pau", last_name="Ferrer")
        self.foreign_member = Member.objects.create(
            association=self.other_association, first_name="Ana", last_name="Lluch"
        )

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def account_with_role(self, role, association=None):
        association = association or self.association
        account = get_user_model().objects.create_user(
            username=f"{role}-{association.slug}@example.invalid",
            email=f"{role}-{association.slug}@example.invalid",
            password="synthetic-password",
        )
        access = AssociationAccess.objects.create(association=association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def panel(self, role):
        client = Client()
        client.force_login(self.accounts[role])
        return client

    def api(self, role):
        token, _created = Token.objects.get_or_create(user=self.accounts[role])
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}", HTTP_X_ASSOCIATION_ID=str(self.association.id))
        return client

    def invite_to_activity(self, member, attendance=True):
        activity = Activity.objects.create(
            association=member.association,
            kind=Activity.Kind.REHEARSAL,
            title="Ensayo sintético",
            starts_at=timezone.now() + timezone.timedelta(days=3),
            created_by=self.accounts[Role.ADMIN],
        )
        invitation = Invitation.objects.create(activity=activity, member=member)
        if attendance:
            Attendance.objects.create(
                invitation=invitation, status=Attendance.Status.PRESENT, recorded_by=self.accounts[Role.ADMIN]
            )
        return invitation


class MemberServiceTests(CensusFixture):
    def test_every_manager_role_can_create_a_member_and_it_records_who(self):
        for role in MANAGERS:
            with self.subTest(role=role):
                member = services.create_member(
                    association=self.association,
                    actor=self.accounts[role],
                    data={"first_name": "Nova", "last_name": role, "kind": Member.Kind.MUSICIAN},
                    instruments=[self.flute],
                    primary_instrument=self.trumpet,
                    positions=[MemberPosition.Position.TREASURER],
                )
                self.assertEqual(member.created_by, self.accounts[role])
                self.assertEqual(member.status, Member.Status.ACTIVE)
                self.assertEqual(
                    set(member.member_instruments.values_list("instrument__name", "is_primary")),
                    {("Flauta", False), ("Trompeta", True)},
                )
                self.assertEqual(list(member.positions.values_list("position", flat=True)), ["treasurer"])

    def test_roles_without_census_management_cannot_create_or_edit(self):
        for role in NON_MANAGERS:
            with self.subTest(role=role):
                with self.assertRaises(PermissionDenied):
                    services.create_member(
                        association=self.association,
                        actor=self.accounts[role],
                        data={"first_name": "X", "last_name": "Y"},
                    )
                with self.assertRaises(PermissionDenied):
                    services.update_member(member=self.member, actor=self.accounts[role], data={"first_name": "Z"})
        self.assertFalse(Member.objects.filter(first_name="X").exists())

    def test_a_manager_of_one_association_cannot_touch_another(self):
        with self.assertRaises(PermissionDenied):
            services.update_member(
                member=self.foreign_member, actor=self.accounts[Role.BOARD], data={"first_name": "Intrusa"}
            )
        with self.assertRaises(PermissionDenied):
            services.set_member_status(
                member=self.foreign_member, actor=self.accounts[Role.BOARD], status=Member.Status.INACTIVE
            )
        self.foreign_member.refresh_from_db()
        self.assertEqual(self.foreign_member.first_name, "Ana")

    def test_instruments_of_another_association_are_rejected(self):
        with self.assertRaises(ValidationError):
            services.update_member(
                member=self.member,
                actor=self.accounts[Role.DIRECTOR],
                data={},
                instruments=[self.foreign_instrument],
            )
        with self.assertRaises(ValidationError):
            services.create_member(
                association=self.association,
                actor=self.accounts[Role.DIRECTOR],
                data={"first_name": "X", "last_name": "Y"},
                primary_instrument=self.foreign_instrument,
            )
        self.assertFalse(self.member.member_instruments.exists())

    def test_external_id_is_unique_within_the_association_only(self):
        services.update_member(member=self.member, actor=self.accounts[Role.BOARD], data={"external_id": "S-1"})
        with self.assertRaises(ValidationError) as raised:
            services.create_member(
                association=self.association,
                actor=self.accounts[Role.BOARD],
                data={"first_name": "Otra", "last_name": "Persona", "external_id": "S-1"},
            )
        self.assertIn("external_id", raised.exception.message_dict)
        other_admin = self.account_with_role(Role.ADMIN, self.other_association)
        services.create_member(
            association=self.other_association,
            actor=other_admin,
            data={"first_name": "Otra", "last_name": "Persona", "external_id": "S-1"},
        )

    def test_update_replaces_instruments_and_positions(self):
        services.update_member(
            member=self.member,
            actor=self.accounts[Role.ORGANIZER],
            data={"phone": "+34960000099"},
            instruments=[self.trumpet, self.flute],
            primary_instrument=self.flute,
            positions=["president", "board_member"],
        )
        services.update_member(
            member=self.member,
            actor=self.accounts[Role.ORGANIZER],
            data={},
            instruments=[self.trumpet],
            primary_instrument=self.trumpet,
            positions=["board_member"],
        )
        self.member.refresh_from_db()
        self.assertEqual(self.member.phone, "+34960000099")
        self.assertEqual(self.member.updated_by, self.accounts[Role.ORGANIZER])
        self.assertEqual(list(self.member.member_instruments.values_list("instrument__name", "is_primary")), [("Trompeta", True)])
        self.assertEqual(list(self.member.positions.values_list("position", flat=True)), ["board_member"])
        with self.assertRaises(ValidationError):
            services.update_member(member=self.member, actor=self.accounts[Role.BOARD], data={}, positions=["king"])

    def test_leaving_and_rejoining_keeps_the_history(self):
        invitation = self.invite_to_activity(self.member)
        member = services.set_member_status(
            member=self.member, actor=self.accounts[Role.DIRECTOR], status=Member.Status.INACTIVE
        )
        self.assertEqual(member.status, Member.Status.INACTIVE)
        self.assertEqual(member.status_changed_by, self.accounts[Role.DIRECTOR])
        self.assertIsNotNone(member.status_changed_at)
        self.assertTrue(Invitation.objects.filter(pk=invitation.pk).exists())
        self.assertTrue(Attendance.objects.filter(invitation=invitation).exists())
        member = services.set_member_status(member=member, actor=self.accounts[Role.BOARD], status=Member.Status.ACTIVE)
        self.assertEqual(member.status, Member.Status.ACTIVE)
        self.assertEqual(member.status_changed_by, self.accounts[Role.BOARD])
        self.assertEqual(services.member_history(member)["invitations"], 1)
        with self.assertRaises(ValidationError):
            services.set_member_status(member=member, actor=self.accounts[Role.BOARD], status="expelled")

    def test_only_admin_deletes_and_only_without_history(self):
        for role in [Role.BOARD, Role.ORGANIZER, Role.DIRECTOR, Role.MEMBER]:
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                services.delete_member(member=self.member, actor=self.accounts[role])
        self.invite_to_activity(self.member)
        with self.assertRaises(ValidationError):
            services.delete_member(member=self.member, actor=self.accounts[Role.ADMIN])
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())

        clean = Member.objects.create(association=self.association, first_name="Sense", last_name="Historial")
        services.delete_member(member=clean, actor=self.accounts[Role.ADMIN])
        self.assertFalse(Member.objects.filter(pk=clean.pk).exists())

    def test_a_member_with_a_linked_account_cannot_be_deleted(self):
        linked = Member.objects.create(
            association=self.association, first_name="Amb", last_name="Compte", account=self.accounts[Role.MEMBER]
        )
        self.assertTrue(services.member_deletion_blockers(linked))
        with self.assertRaises(ValidationError):
            services.delete_member(member=linked, actor=self.accounts[Role.ADMIN])

    def test_admin_of_another_association_cannot_delete(self):
        with self.assertRaises(PermissionDenied):
            services.delete_member(member=self.foreign_member, actor=self.accounts[Role.ADMIN])

    def test_photo_is_validated_replaced_and_deleted(self):
        with self.assertRaises(ValidationError):
            services.replace_member_photo(
                member=self.member,
                actor=self.accounts[Role.BOARD],
                upload=SimpleUploadedFile("foto.png", b"not an image", content_type="image/png"),
            )
        member = services.replace_member_photo(member=self.member, actor=self.accounts[Role.BOARD], upload=png_upload())
        first_name = member.photo.name
        self.assertTrue(first_name.endswith(".webp"))
        self.assertNotIn("foto", first_name)
        member = services.replace_member_photo(member=member, actor=self.accounts[Role.BOARD], upload=png_upload())
        self.assertNotEqual(member.photo.name, first_name)
        member = services.delete_member_photo(member=member, actor=self.accounts[Role.BOARD])
        self.assertFalse(member.photo)
        with self.assertRaises(PermissionDenied):
            services.replace_member_photo(member=self.member, actor=self.accounts[Role.MEMBER], upload=png_upload())


class MemberPanelTests(CensusFixture):
    def url(self, name, member=None):
        base = {
            "new": "/panel/members/new/",
            "detail": f"/panel/members/{(member or self.member).id}/",
            "photo": f"/panel/members/{(member or self.member).id}/photo/",
            "status": f"/panel/members/{(member or self.member).id}/status/",
            "delete": f"/panel/members/{(member or self.member).id}/delete/",
        }[name]
        return f"{base}?association_id={self.association.id}"

    def test_role_matrix_for_member_pages(self):
        for role in Role.values:
            with self.subTest(role=role):
                client = self.panel(role)
                expected = 200 if role in MANAGERS else 403
                self.assertEqual(client.get(self.url("new")).status_code, expected)
                self.assertEqual(client.get(self.url("detail")).status_code, expected)
                self.assertEqual(client.get(self.url("delete")).status_code, 200 if role == Role.ADMIN else 403)

    def test_director_creates_a_member_from_the_panel(self):
        response = self.panel(Role.DIRECTOR).post(
            self.url("new"),
            {
                "association_id": self.association.id,
                "first_name": "Marta",
                "last_name": "Vidal Soler",
                "kind": Member.Kind.MUSICIAN,
                "status": Member.Status.ACTIVE,
                "instruments": [self.trumpet.id],
                "primary_instrument": self.trumpet.id,
                "positions": ["secretary"],
            },
        )
        member = Member.objects.get(first_name="Marta")
        self.assertRedirects(response, self.url("detail", member), fetch_redirect_response=False)
        self.assertEqual(member.created_by, self.accounts[Role.DIRECTOR])
        self.assertEqual(member.association, self.association)
        self.assertTrue(member.positions.filter(position="secretary").exists())

    def test_form_errors_are_shown_and_nothing_is_saved(self):
        Member.objects.filter(pk=self.member.pk).update(external_id="S-7")
        response = self.panel(Role.BOARD).post(
            self.url("new"),
            {
                "association_id": self.association.id,
                "first_name": "Repe",
                "last_name": "Tida",
                "external_id": "S-7",
                "kind": Member.Kind.MUSICIAN,
                "status": Member.Status.ACTIVE,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya hay otra ficha con este identificador externo")
        self.assertFalse(Member.objects.filter(first_name="Repe").exists())

        response = self.panel(Role.BOARD).post(
            self.url("new"),
            {"association_id": self.association.id, "first_name": "", "last_name": "", "kind": "x", "status": "active"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Member.objects.filter(last_name="").exists())

    def test_foreign_instrument_is_not_offered_nor_accepted(self):
        response = self.panel(Role.BOARD).post(
            self.url("detail"),
            {
                "association_id": self.association.id,
                "first_name": "Pau",
                "last_name": "Ferrer",
                "kind": Member.Kind.MUSICIAN,
                "status": Member.Status.ACTIVE,
                "instruments": [self.foreign_instrument.id],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.member.member_instruments.exists())

    def test_member_of_another_association_is_not_found(self):
        client = self.panel(Role.ADMIN)
        for name in ["detail", "photo", "delete"]:
            with self.subTest(page=name):
                self.assertEqual(client.get(self.url(name, self.foreign_member)).status_code, 404)
        response = client.post(
            self.url("status", self.foreign_member),
            {"association_id": self.association.id, "status": "inactive", "confirmed": "1"},
        )
        self.assertEqual(response.status_code, 404)
        self.foreign_member.refresh_from_db()
        self.assertEqual(self.foreign_member.status, Member.Status.ACTIVE)

    def test_leaving_needs_confirmation_and_can_be_undone(self):
        invitation = self.invite_to_activity(self.member)
        client = self.panel(Role.ORGANIZER)
        response = client.post(self.url("status"), {"association_id": self.association.id, "status": "inactive"})
        self.assertContains(response, "Dar de baja")
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Member.Status.ACTIVE)

        client.post(self.url("status"), {"association_id": self.association.id, "status": "inactive", "confirmed": "1"})
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Member.Status.INACTIVE)
        self.assertTrue(Attendance.objects.filter(invitation=invitation).exists())

        client.post(self.url("status"), {"association_id": self.association.id, "status": "active"})
        self.member.refresh_from_db()
        self.assertEqual(self.member.status, Member.Status.ACTIVE)

    def test_physical_deletion_is_blocked_with_history_and_confirmed_without(self):
        self.invite_to_activity(self.member)
        client = self.panel(Role.ADMIN)
        page = client.get(self.url("delete"))
        self.assertContains(page, "Tiene convocatorias o asistencia registradas.")
        self.assertNotContains(page, 'name="confirmed"')
        client.post(self.url("delete"), {"association_id": self.association.id, "confirmed": "1"})
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())

        clean = Member.objects.create(association=self.association, first_name="Sense", last_name="Historial")
        client.post(self.url("delete", clean), {"association_id": self.association.id})
        self.assertTrue(Member.objects.filter(pk=clean.pk).exists(), "sin confirmación no se borra")
        response = client.post(self.url("delete", clean), {"association_id": self.association.id, "confirmed": "1"})
        self.assertRedirects(
            response, f"/panel/members/?association_id={self.association.id}", fetch_redirect_response=False
        )
        self.assertFalse(Member.objects.filter(pk=clean.pk).exists())

    def test_board_cannot_delete_from_the_panel(self):
        clean = Member.objects.create(association=self.association, first_name="Sense", last_name="Historial")
        response = self.panel(Role.BOARD).post(
            self.url("delete", clean), {"association_id": self.association.id, "confirmed": "1"}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Member.objects.filter(pk=clean.pk).exists())

    def test_photo_upload_rejects_invalid_files_and_serves_privately(self):
        client = self.panel(Role.BOARD)
        bad = SimpleUploadedFile("foto.png", b"<?php echo 1; ?>", content_type="image/png")
        response = client.post(self.url("photo"), {"association_id": self.association.id, "photo": bad})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "no es una imagen válida", status_code=400)
        self.member.refresh_from_db()
        self.assertFalse(self.member.photo)

        response = client.post(self.url("photo"), {"association_id": self.association.id, "photo": png_upload()})
        self.assertEqual(response.status_code, 302)
        served = client.get(self.url("photo"))
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Content-Type"], "image/webp")
        self.assertIn("private", served["Cache-Control"])
        self.assertEqual(self.panel(Role.MEMBER).get(self.url("photo")).status_code, 403)

        client.post(self.url("photo"), {"association_id": self.association.id, "action": "delete"})
        self.member.refresh_from_db()
        self.assertFalse(self.member.photo)
        self.assertEqual(client.get(self.url("photo")).status_code, 404)

    def test_member_list_offers_the_actions_each_role_has(self):
        board_page = self.panel(Role.BOARD).get(f"/panel/members/?association_id={self.association.id}")
        self.assertContains(board_page, "Nueva ficha")
        self.assertContains(board_page, "Accesos y roles")
        self.assertNotContains(board_page, "/panel/members/import/")
        director_page = self.panel(Role.DIRECTOR).get(f"/panel/members/?association_id={self.association.id}")
        self.assertContains(director_page, "Nueva ficha")
        self.assertNotContains(director_page, "Accesos y roles")
        admin_page = self.panel(Role.ADMIN).get(f"/panel/members/?association_id={self.association.id}")
        self.assertContains(admin_page, "/panel/members/import/")

    def test_member_pages_are_translated_to_valencian(self):
        client = self.panel(Role.BOARD)
        client.cookies["django_language"] = "ca"
        response = client.get(self.url("detail"))
        self.assertContains(response, "Donar de baixa")
        self.assertContains(response, "Guardar els canvis")


class MemberApiTests(CensusFixture):
    def test_api_create_and_update_go_through_the_service(self):
        response = self.api(Role.DIRECTOR).post(
            "/api/v1/members/",
            {"first_name": "Api", "last_name": "Sintètica", "kind": "musician", "status": "active"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        member = Member.objects.get(pk=response.json()["id"])
        self.assertEqual(member.created_by, self.accounts[Role.DIRECTOR])
        self.assertEqual(member.association, self.association)

        response = self.api(Role.BOARD).patch(f"/api/v1/members/{member.id}/", {"status": "inactive"}, format="json")
        self.assertEqual(response.status_code, 200, response.content)
        member.refresh_from_db()
        self.assertEqual(member.status_changed_by, self.accounts[Role.BOARD])

    def test_api_rejects_duplicate_external_id_with_400(self):
        Member.objects.filter(pk=self.member.pk).update(external_id="S-9")
        response = self.api(Role.BOARD).post(
            "/api/v1/members/",
            {"first_name": "Dup", "last_name": "Licat", "external_id": "S-9"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("external_id", response.json())

    def test_api_delete_is_admin_only_and_conflicts_with_history(self):
        clean = Member.objects.create(association=self.association, first_name="Sense", last_name="Historial")
        self.assertEqual(self.api(Role.BOARD).delete(f"/api/v1/members/{clean.id}/").status_code, 403)
        self.invite_to_activity(self.member)
        response = self.api(Role.ADMIN).delete(f"/api/v1/members/{self.member.id}/")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Member.objects.filter(pk=self.member.pk).exists())
        self.assertEqual(self.api(Role.ADMIN).delete(f"/api/v1/members/{clean.id}/").status_code, 204)
        self.assertFalse(Member.objects.filter(pk=clean.pk).exists())

    def test_api_cannot_reach_a_member_of_another_association(self):
        response = self.api(Role.ADMIN).patch(
            f"/api/v1/members/{self.foreign_member.id}/", {"first_name": "Intrusa"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.api(Role.ADMIN).delete(f"/api/v1/members/{self.foreign_member.id}/").status_code, 404)

    def test_invalid_photo_through_the_api_is_a_400_not_a_500(self):
        # Regresión: la `ValidationError` de Django de la foto llegaba como 500.
        bad = SimpleUploadedFile("foto.png", b"not an image", content_type="image/png")
        response = self.api(Role.BOARD).put(f"/api/v1/members/{self.member.id}/photo/", {"photo": bad}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("photo", response.json())

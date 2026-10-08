"""Imagen de la banda en el panel y sistema visual compartido (decisión 0010).

`admin` y `board` cambian logo, colores, lema, estilo y modo; el resto no. Todos
los datos son sintéticos.
"""

import io
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.utils import timezone
from PIL import Image

from apps.activities.models import Activity, Invitation
from apps.associations import services
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.associations.permissions import permissions_for
from apps.members.models import Member

Role = AssociationRole.Role
BRANDING_MANAGERS = {Role.ADMIN, Role.BOARD}


def image_upload(name="logo.png", size=(64, 64), mode="RGBA", fmt="PNG"):
    buffer = io.BytesIO()
    Image.new(mode, size, (255, 255, 255, 0) if mode == "RGBA" else (20, 20, 20)).save(buffer, format=fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f"image/{fmt.lower()}")


class BrandingFixture(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = self.settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.association = Association.objects.create(name="Unió Musical Sintètica", slug="ums")
        self.other = Association.objects.create(name="Altra Banda", slug="altra", primary_color="#2E5E3A")
        self.accounts = {role: self.account_with(role) for role in Role.values}

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def account_with(self, role, association=None):
        association = association or self.association
        account = get_user_model().objects.create_user(
            username=f"{role}-{association.slug}@example.invalid", email=f"{role}-{association.slug}@example.invalid",
            password="synthetic-password",
        )
        access = AssociationAccess.objects.create(association=association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def panel(self, account):
        client = Client()
        client.force_login(account)
        return client

    def url(self, association=None):
        return f"/panel/branding/?association_id={(association or self.association).id}"

    def payload(self, **overrides):
        data = {
            "association_id": str(self.association.id),
            "motto": "Música per a tot el poble",
            "primary_color": "#111111",
            "secondary_color": "#c9a227",
            "visual_style": "escenario",
            "color_mode": "system",
        }
        data.update(overrides)
        return data


class BrandingServiceTests(BrandingFixture):
    def test_board_saves_the_black_and_gold_of_the_band(self):
        saved = services.update_branding(
            actor=self.accounts[Role.BOARD], association=self.association,
            data={"primary_color": "#111111", "secondary_color": "#c9a227", "visual_style": "festa", "color_mode": "dark"},
        )
        self.assertEqual((saved.primary_color, saved.secondary_color), ("#111111", "#C9A227"))
        self.assertEqual((saved.visual_style, saved.color_mode), ("festa", "dark"))

    def test_roles_without_branding_manage_are_refused(self):
        for role in set(Role.values) - BRANDING_MANAGERS:
            with self.subTest(role=role), self.assertRaises(PermissionDenied):
                services.update_branding(actor=self.accounts[role], association=self.association, data={"motto": "x"})

    def test_an_admin_of_another_band_cannot_touch_this_one(self):
        outsider = self.account_with(Role.ADMIN, self.other)
        with self.assertRaises(PermissionDenied):
            services.update_branding(actor=outsider, association=self.association, data={"motto": "x"})

    def test_invalid_values_are_rejected_and_nothing_is_saved(self):
        for data in ({"primary_color": "red"}, {"visual_style": "barroco"}, {"color_mode": "sepia"}):
            with self.subTest(data=data), self.assertRaises(ValidationError):
                services.update_branding(actor=self.accounts[Role.ADMIN], association=self.association, data=data)
        self.association.refresh_from_db()
        self.assertEqual(self.association.visual_style, "escenario")

    def test_the_logo_is_re_encoded_without_metadata_and_keeps_transparency(self):
        saved = services.update_branding(
            actor=self.accounts[Role.ADMIN], association=self.association, data={}, logo=image_upload(),
        )
        self.assertTrue(saved.logo.name.endswith(".webp"))
        self.assertNotIn("logo.png", saved.logo.name)
        with saved.logo.open("rb") as handle:
            stored = Image.open(handle)
            self.assertEqual(stored.format, "WEBP")
            self.assertIn("A", stored.getbands())
            self.assertNotIn("exif", stored.info)

    def test_a_large_logo_is_scaled_down(self):
        saved = services.update_branding(
            actor=self.accounts[Role.ADMIN], association=self.association, data={}, logo=image_upload(size=(3000, 1500)),
        )
        with saved.logo.open("rb") as handle:
            self.assertLessEqual(max(Image.open(handle).size), services.LOGO_MAX_SIDE)

    def test_a_file_that_is_not_an_image_is_rejected(self):
        fake = SimpleUploadedFile("logo.png", b"<?php echo 'no'; ?>", content_type="image/png")
        with self.assertRaises(ValidationError):
            services.update_branding(actor=self.accounts[Role.ADMIN], association=self.association, data={}, logo=fake)

    def test_replacing_and_removing_the_logo(self):
        admin = self.accounts[Role.ADMIN]
        first = services.update_branding(actor=admin, association=self.association, data={}, logo=image_upload()).logo.name
        second = services.update_branding(actor=admin, association=self.association, data={}, logo=image_upload()).logo.name
        self.assertNotEqual(first, second)
        removed = services.update_branding(actor=admin, association=self.association, data={}, remove_logo=True)
        self.assertFalse(removed.logo)


class BrandingPanelTests(BrandingFixture):
    def test_only_admin_and_board_open_the_page_and_see_it_in_the_navigation(self):
        for role in Role.values:
            with self.subTest(role=role):
                client = self.panel(self.accounts[role])
                allowed = role in BRANDING_MANAGERS
                self.assertEqual(client.get(self.url()).status_code, 200 if allowed else 403)
                self.assertEqual("branding.manage" in permissions_for(self.accounts[role], self.association), allowed)
                if role in {Role.ORGANIZER, Role.DIRECTOR}:
                    page = client.get(f"/panel/?association_id={self.association.id}")
                    self.assertNotContains(page, "/panel/branding/")
        board_home = self.panel(self.accounts[Role.BOARD]).get(f"/panel/?association_id={self.association.id}")
        self.assertContains(board_home, "/panel/branding/")

    def test_the_page_of_another_band_is_forbidden(self):
        self.assertEqual(self.panel(self.accounts[Role.ADMIN]).get(self.url(self.other)).status_code, 403)

    def test_saving_from_the_panel_dresses_the_panel(self):
        client = self.panel(self.accounts[Role.BOARD])
        response = client.post(self.url(), self.payload(visual_style="partitura", color_mode="dark", logo=image_upload()))
        self.assertRedirects(response, self.url(), fetch_redirect_response=False)
        self.association.refresh_from_db()
        self.assertEqual(self.association.primary_color, "#111111")
        self.assertTrue(self.association.logo)
        page = client.get(f"/panel/?association_id={self.association.id}").content.decode()
        self.assertIn('data-style="partitura"', page)
        self.assertIn('data-mode="dark"', page)
        self.assertIn("--brand:#111111", page)
        self.assertIn("--brand-edge-dark:#C9A227", page, "una banda negra necesita filo en modo oscuro")
        self.assertIn(f"/api/v1/associations/{self.association.id}/logo/", page)

    def test_an_invalid_post_shows_errors_and_keeps_the_saved_brand_in_the_header(self):
        client = self.panel(self.accounts[Role.ADMIN])
        response = client.post(self.url(), self.payload(primary_color="no-es-color"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)
        self.assertContains(response, "--brand:#1B4965")
        self.association.refresh_from_db()
        self.assertEqual(self.association.primary_color, "#1B4965")

    def test_a_forged_post_by_a_member_changes_nothing(self):
        response = self.panel(self.accounts[Role.MEMBER]).post(self.url(), self.payload())
        self.assertEqual(response.status_code, 403)
        self.association.refresh_from_db()
        self.assertEqual(self.association.primary_color, "#1B4965")


class SharedShellTests(BrandingFixture):
    def test_without_a_band_the_login_is_gesband_with_escenario(self):
        page = Client().get("/accounts/login/").content.decode()
        self.assertIn('data-style="escenario"', page)
        self.assertIn("panel/panel.css", page)

    def test_the_dashboard_puts_the_next_published_activity_on_the_poster(self):
        board = self.accounts[Role.BOARD]
        now = timezone.now()
        Activity.objects.create(
            association=self.association, created_by=board, kind=Activity.Kind.REHEARSAL,
            status=Activity.Status.DRAFT, title="Assaig en esborrany", starts_at=now + timedelta(days=1),
        )
        concert = Activity.objects.create(
            association=self.association, created_by=board, kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED, title="Concert de Santa Cecília", starts_at=now + timedelta(days=4),
        )
        for index, response in enumerate(["accepted", "accepted", "declined", "pending"]):
            member = Member.objects.create(association=self.association, first_name="Músic", last_name=str(index))
            Invitation.objects.create(activity=concert, member=member, response=response)
        Activity.objects.create(
            association=self.association, created_by=board, kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED, title="Concert passat", starts_at=now - timedelta(days=10),
        )
        response = self.panel(board).get(f"/panel/?association_id={self.association.id}")
        self.assertEqual(response.context["next_activity"], concert)
        self.assertEqual((concert.pk, response.context["next_activity"].accepted), (concert.pk, 2))
        self.assertEqual(response.context["next_activity"].pending, 1)
        self.assertEqual([item.title for item in response.context["activities"]], ["Assaig en esborrany"])
        self.assertContains(response, "Concert passat")

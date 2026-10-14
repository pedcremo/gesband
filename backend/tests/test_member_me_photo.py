"""El músico descarga su propia foto por /members/me/photo/ (regresión del 14/10/2026).

`photo_url` de la ficha propia apuntaba a /members/{id}/photo/, que exige
gestionar el censo: el rol `member` recibía un 403 al abrir su propia foto.
"""

import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members.models import Member

Role = AssociationRole.Role


def png_upload(name="foto.png", size=(40, 30)):
    buffer = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class MemberMePhotoTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        override = self.settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, ignore_errors=True)
        self.association = Association.objects.create(name="Banda Sintética", slug="banda-sintetica")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.account = self.person("musica@example.invalid", Role.MEMBER)
        self.member = Member.objects.create(
            association=self.association, first_name="Marina", last_name="Prova", account=self.account
        )

    def person(self, email, role, association=None):
        account = get_user_model().objects.filter(email=email).first() or get_user_model().objects.create_user(
            username=email, email=email, password="secret-password"
        )
        access = AssociationAccess.objects.create(association=association or self.association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def api(self, account, association=None):
        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f"Token {Token.objects.get_or_create(user=account)[0].key}",
            HTTP_X_ASSOCIATION_ID=str((association or self.association).pk),
        )
        return client

    def test_musician_uploads_and_downloads_their_photo_through_photo_url(self):
        client = self.api(self.account)
        uploaded = client.put("/api/v1/members/me/photo/", {"photo": png_upload()}, format="multipart")
        self.assertEqual(uploaded.status_code, 200, uploaded.content)
        photo_url = uploaded.json()["photo_url"]
        self.assertIn("/api/v1/members/me/photo/", photo_url)

        downloaded = client.get(photo_url)

        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Content-Type"], "image/webp")
        self.assertEqual(downloaded["Cache-Control"], "private, no-store")
        self.assertTrue(b"".join(downloaded.streaming_content).startswith(b"RIFF"))
        self.assertEqual(client.get("/api/v1/members/me/").json()["photo_url"], photo_url)

    def test_photo_url_works_without_the_association_header(self):
        client = self.api(self.account)
        photo_url = client.put("/api/v1/members/me/photo/", {"photo": png_upload()}, format="multipart").json()[
            "photo_url"
        ]
        bare = APIClient()
        bare.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.get(user=self.account).key}")
        self.assertEqual(bare.get(photo_url).status_code, 200)

    def test_without_photo_is_not_found(self):
        self.assertEqual(self.api(self.account).get("/api/v1/members/me/photo/").status_code, 404)

    def test_downloads_only_the_profile_of_the_requested_association(self):
        self.api(self.account).put("/api/v1/members/me/photo/", {"photo": png_upload()}, format="multipart")
        self.person("musica@example.invalid", Role.MEMBER, association=self.other_association)
        Member.objects.create(
            association=self.other_association, first_name="Marina", last_name="B", account=self.account
        )
        other = self.api(self.account, association=self.other_association).get("/api/v1/members/me/photo/")
        self.assertEqual(other.status_code, 404)

    def test_requires_access_to_the_association(self):
        stranger = get_user_model().objects.create_user(
            username="fora@example.invalid", email="fora@example.invalid", password="secret-password"
        )
        self.assertEqual(self.api(stranger).get("/api/v1/members/me/photo/").status_code, 403)

    def test_managers_keep_the_photo_url_by_id(self):
        self.api(self.account).put("/api/v1/members/me/photo/", {"photo": png_upload()}, format="multipart")
        board = self.person("junta@example.invalid", Role.BOARD)
        client = self.api(board)
        data = client.get(f"/api/v1/members/{self.member.pk}/").json()
        self.assertIn(f"/api/v1/members/{self.member.pk}/photo/", data["photo_url"])
        downloaded = client.get(data["photo_url"])
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded["Cache-Control"], "private, no-store")

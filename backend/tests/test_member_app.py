import base64
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from apps.activities.models import Activity, Invitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members.models import Member

# PNG de 1x1 para no depender de ficheros de prueba en disco.
PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)


class MemberAppShellTests(TestCase):
    """El cliente web del musico: carcasa, manifiesto y service worker."""

    def test_the_shell_loads_without_a_session(self):
        page = self.client.get("/app/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, 'id="app"')
        self.assertContains(page, "member_app/app.js")

    def test_the_manifest_declares_the_app_scope(self):
        manifest = self.client.get("/app/manifest.webmanifest")
        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(manifest["Content-Type"], "application/manifest+json")
        self.assertContains(manifest, '"scope": "/app/"')
        self.assertContains(manifest, '"start_url": "/app/"')

    def test_the_service_worker_is_served_from_the_app_path(self):
        """Servido desde /static/ su alcance no cubriria /app/."""
        worker = self.client.get("/app/sw.js")
        self.assertEqual(worker.status_code, 200)
        self.assertIn("javascript", worker["Content-Type"])
        self.assertContains(worker, "gesband-shell")

    def test_the_shell_is_not_cached_by_intermediaries(self):
        page = self.client.get("/app/")
        self.assertIn("no-cache", page["Cache-Control"])

    def test_the_service_worker_is_versioned_with_the_shell(self):
        """Sin version, quien ya tiene la app instalada nunca recibe un cambio."""
        from config.member_app import shell_version

        version = shell_version()
        self.assertRegex(version, r"^[0-9a-f]{16}$")

        worker = self.client.get("/app/sw.js")
        self.assertContains(worker, f"gesband-shell-{version}")
        # La pagina pide las mismas URL que el service worker guarda.
        self.assertContains(self.client.get("/app/"), f"app.css?v={version}")
        self.assertContains(worker, f"app.css?v={version}")

    def test_the_version_changes_when_the_shell_changes(self):
        import config.member_app as shell

        first = shell.shell_version()
        with mock.patch.object(shell, "_version_cache", None), \
                mock.patch("pathlib.Path.read_bytes", return_value=b"otro contenido"):
            self.assertNotEqual(shell.shell_version(), first)


class AssociationBrandingTests(TestCase):
    """La app se viste con la marca de cada asociacion: README, requisito del promotor."""

    def setUp(self):
        self.account = get_user_model().objects.create_user(
            username="musico@example.invalid", email="musico@example.invalid", password="secret-password"
        )
        self.association = Association.objects.create(
            name="Banda Test", slug="banda-test",
            primary_color="#7A1F2B", secondary_color="#E8C87D", motto="La música que ens uneix",
        )
        access = AssociationAccess.objects.create(association=self.association, account=self.account)
        AssociationRole.objects.create(access=access, role=AssociationRole.Role.MEMBER)
        self.api = Client()
        self.api.force_login(self.account)

    def association_payload(self):
        response = self.api.get("/api/v1/auth/me")
        self.assertEqual(response.status_code, 200)
        return response.json()["associations"][0]

    def test_the_session_carries_the_colours_and_the_motto(self):
        payload = self.association_payload()
        self.assertEqual(payload["primary_color"], "#7A1F2B")
        self.assertEqual(payload["secondary_color"], "#E8C87D")
        self.assertEqual(payload["motto"], "La música que ens uneix")

    def test_without_a_logo_the_url_is_null(self):
        """El contrato pide `logo_url`; el campo crudo apuntaba a una ruta que nadie sirve."""
        payload = self.association_payload()
        self.assertIsNone(payload["logo_url"])
        self.assertNotIn("logo", payload)

    def test_the_logo_is_served_by_the_api_because_the_media_is_private(self):
        self.association.logo.save("logo.png", SimpleUploadedFile("logo.png", PNG, "image/png"), save=True)
        self.addCleanup(self.association.logo.delete, save=False)

        url = self.association_payload()["logo_url"]
        self.assertTrue(url.endswith(f"/api/v1/associations/{self.association.id}/logo/"))

        served = self.api.get(f"/api/v1/associations/{self.association.id}/logo/")
        self.assertEqual(served.status_code, 200)
        self.assertEqual(served["Content-Type"], "image/png")
        self.assertEqual(b"".join(served.streaming_content), PNG)

    def test_a_stranger_cannot_read_the_logo(self):
        self.association.logo.save("logo.png", SimpleUploadedFile("logo.png", PNG, "image/png"), save=True)
        self.addCleanup(self.association.logo.delete, save=False)

        stranger = Client()
        stranger.force_login(get_user_model().objects.create_user(
            username="fora@example.invalid", email="fora@example.invalid", password="secret-password"
        ))
        self.assertEqual(stranger.get(f"/api/v1/associations/{self.association.id}/logo/").status_code, 404)


class MemberAppReconfirmationSignalTests(TestCase):
    """La API tiene que decir si una respuesta fue anulada por un cambio."""

    def setUp(self):
        account = get_user_model().objects.create_user(
            username="musico@example.invalid", email="musico@example.invalid", password="secret-password"
        )
        self.board = get_user_model().objects.create_user(
            username="junta@example.invalid", email="junta@example.invalid", password="secret-password"
        )
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        for user, role in [(account, AssociationRole.Role.MEMBER), (self.board, AssociationRole.Role.ADMIN)]:
            access = AssociationAccess.objects.create(association=self.association, account=user)
            AssociationRole.objects.create(access=access, role=role)
        self.member = Member.objects.create(
            association=self.association, account=account, first_name="Pau", last_name="Test"
        )
        self.activity = Activity.objects.create(
            association=self.association,
            created_by=self.board,
            kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED,
            title="Processó",
            location="Plaça",
            starts_at=timezone.now() + timedelta(days=7),
        )
        self.invitation = Invitation.objects.create(activity=self.activity, member=self.member)
        self.api = Client()
        self.api.force_login(account)

    def invitation_payload(self):
        response = self.api.get(f"/api/v1/activities/{self.activity.id}/?association_id={self.association.id}")
        self.assertEqual(response.status_code, 200)
        return response.json()["invitations"][0]

    def test_an_unanswered_invitation_does_not_ask_to_reconfirm(self):
        payload = self.invitation_payload()
        self.assertEqual(payload["response"], "pending")
        self.assertFalse(payload["needs_reconfirmation"])

    def test_an_answered_invitation_does_not_ask_to_reconfirm(self):
        self.invitation.response = Invitation.Response.ACCEPTED
        self.invitation.save()
        self.assertFalse(self.invitation_payload()["needs_reconfirmation"])

    def test_an_answer_cancelled_by_a_change_asks_to_reconfirm(self):
        from apps.activities.services import reset_responses_for_reconfirmation

        self.invitation.response = Invitation.Response.ACCEPTED
        self.invitation.save()
        reset_responses_for_reconfirmation(self.activity, self.board)

        payload = self.invitation_payload()
        self.assertEqual(payload["response"], "pending")
        self.assertTrue(payload["needs_reconfirmation"])


class LoginWithPanelSessionTests(TestCase):
    """Quien ya entro al panel en el mismo navegador tambien puede entrar en /app/."""

    def test_the_api_login_ignores_the_panel_session_cookie(self):
        account = get_user_model().objects.create_user(
            username="junta@example.invalid", email="junta@example.invalid", password="secret-password"
        )
        browser = Client(enforce_csrf_checks=True)
        browser.force_login(account)

        response = browser.post(
            "/api/v1/auth/login",
            {"email": "junta@example.invalid", "password": "secret-password"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("access_token", response.json())


class MemberAppStringsTests(TestCase):
    """Los tres idiomas del cliente tienen los mismos textos."""

    def test_every_language_has_every_string(self):
        import re

        from django.contrib.staticfiles import finders

        source = open(finders.find("member_app/app.js"), encoding="utf-8").read()
        block = re.search(r"const STRINGS = \{(.*?)\n  \};", source, re.S).group(1)
        languages = dict(re.findall(r"\n    (\w\w): \{(.*?)\n    \},", block, re.S))
        self.assertEqual(set(languages), {"es", "ca", "en"})
        keys = {code: set(re.findall(r"(\w+): \"", body)) for code, body in languages.items()}
        self.assertIn("confirmWarning", keys["es"])
        self.assertEqual(keys["ca"], keys["es"])
        self.assertEqual(keys["en"], keys["es"])


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class MemberAppPollTests(TestCase):
    """Lo que el cliente del musico lee de una encuesta, con el token de la app."""

    def setUp(self):
        from rest_framework.authtoken.models import Token

        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.clients = {}
        self.members = {}
        for name, role in [("junta", AssociationRole.Role.BOARD), ("ana", AssociationRole.Role.MEMBER),
                           ("biel", AssociationRole.Role.MEMBER)]:
            account = get_user_model().objects.create_user(
                username=f"{name}@example.invalid", email=f"{name}@example.invalid", password="secret-password"
            )
            access = AssociationAccess.objects.create(association=self.association, account=account)
            AssociationRole.objects.create(access=access, role=role)
            self.members[name] = Member.objects.create(
                association=self.association, account=account, first_name=name.title(), last_name="Test"
            )
            # La app manda el token y la asociacion como cabeceras, y la asociacion
            # tambien en la consulta: se reproduce igual.
            self.clients[name] = Client(
                HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=account).key}",
                HTTP_X_ASSOCIATION_ID=str(self.association.id),
            )

        board = self.clients["junta"]
        created = board.post(
            "/api/v1/polls/",
            {"question": "¿Viaje?", "closes_at": (timezone.now() + timedelta(days=2)).isoformat(),
             "options": ["Valencia", "Alacant"]},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.poll = created.json()
        board.post(
            f"/api/v1/polls/{self.poll['id']}/recipients/",
            {"member_ids": [str(self.members["ana"].id), str(self.members["biel"].id)]},
            content_type="application/json",
        )
        self.assertEqual(board.post(f"/api/v1/polls/{self.poll['id']}/open/").status_code, 200)

    def get(self, name, path):
        response = self.clients[name].get(f"{path}?association_id={self.association.id}")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def vote(self, name, index):
        return self.clients[name].post(
            f"/api/v1/polls/{self.poll['id']}/vote/?association_id={self.association.id}",
            {"option_id": self.poll["choices"][index]["id"]},
            content_type="application/json",
        )

    def test_the_notice_carries_the_poll_it_opens(self):
        notices = self.clients["ana"].get("/api/v1/notifications/").json()["results"]
        self.assertEqual([notice["poll"] for notice in notices], [self.poll["id"]])
        self.assertIsNone(notices[0]["activity"])

    def test_the_list_says_what_is_waiting_for_a_vote(self):
        listed = self.get("ana", "/api/v1/polls/")["results"]
        self.assertEqual([(poll["id"], poll["can_vote"], poll["has_voted"]) for poll in listed],
                         [(self.poll["id"], True, False)])

    def test_after_voting_the_detail_does_not_depend_on_the_choice(self):
        """La app muestra «Has votado» sin saber que se eligio: la API tampoco lo dice."""
        self.assertEqual(self.vote("ana", 0).status_code, 201)
        self.assertEqual(self.vote("biel", 1).status_code, 201)

        ana = self.get("ana", f"/api/v1/polls/{self.poll['id']}/")
        biel = self.get("biel", f"/api/v1/polls/{self.poll['id']}/")
        self.assertEqual(ana, biel)
        self.assertEqual((ana["has_voted"], ana["can_vote"], ana["results"]["kind"]), (True, False, "provisional"))
        self.assertEqual([option["votes"] for option in ana["results"]["options"]], [1, 1])

    def test_a_second_vote_answers_409_for_the_app_to_reload(self):
        self.assertEqual(self.vote("ana", 0).status_code, 201)
        self.assertEqual(self.vote("ana", 1).status_code, 409)

    def test_after_the_deadline_the_member_waits_for_the_board(self):
        from apps.polls.models import Poll

        Poll.objects.filter(pk=self.poll["id"]).update(closes_at=timezone.now() - timedelta(minutes=1))
        detail = self.get("ana", f"/api/v1/polls/{self.poll['id']}/")
        self.assertEqual((detail["status"], detail["results"], detail["can_vote"]), ("open", None, False))

        published = self.clients["junta"].post(f"/api/v1/polls/{self.poll['id']}/publish/")
        self.assertEqual(published.status_code, 200, published.content)
        detail = self.get("ana", f"/api/v1/polls/{self.poll['id']}/")
        self.assertEqual((detail["status"], detail["results"]["kind"]), ("published", "final"))
        self.assertEqual(detail["participation"], {"recipients": 2, "voted": 0})

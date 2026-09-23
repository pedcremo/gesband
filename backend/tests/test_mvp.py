import re
from datetime import timedelta
from tempfile import TemporaryDirectory

from django.core import mail
from django.contrib.auth import authenticate, get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from apps.activities.models import Activity, Invitation
from apps.accounts.models import AccessInvitation
from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.communications.models import DeviceRegistration, Notification
from apps.members.models import ImportBatch, Instrument, Member, Section
from apps.transport.models import Transport, TransportAssignment


class MvpApiTests(APITestCase):
    def setUp(self):
        account_model = get_user_model()
        self.user = account_model.objects.create_user(username="maria@example.invalid", email="maria@example.invalid", password="secret-password")
        self.other = account_model.objects.create_user(username="other@example.invalid", email="other@example.invalid", password="secret-password")
        self.basic_user = account_model.objects.create_user(
            username="member@example.invalid", email="member@example.invalid", password="secret-password"
        )
        self.association = Association.objects.create(name="Banda Test", slug="banda-test")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        access = AssociationAccess.objects.create(association=self.association, account=self.user)
        AssociationRole.objects.create(access=access, role=AssociationRole.Role.ADMIN)
        basic_access = AssociationAccess.objects.create(association=self.association, account=self.basic_user)
        AssociationRole.objects.create(access=basic_access, role=AssociationRole.Role.MEMBER)
        other_access = AssociationAccess.objects.create(association=self.other_association, account=self.other)
        AssociationRole.objects.create(access=other_access, role=AssociationRole.Role.ADMIN)
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_logging_out_works_from_the_panel_bar(self):
        web_client = Client()
        web_client.force_login(self.user)
        page = web_client.get(f"/panel/?association_id={self.association.id}")
        self.assertContains(page, 'action="/accounts/logout/"')
        self.assertContains(page, 'method="post"')

        response = web_client.post("/accounts/logout/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [("/accounts/login/", 302)])
        self.assertFalse(web_client.session.get("_auth_user_id"))

    def test_the_root_url_leads_anonymous_visitors_to_the_login(self):
        anonymous = Client()
        response = anonymous.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain[0][0], "/panel/")
        self.assertIn("/accounts/login/", response.redirect_chain[-1][0])

    def test_the_root_url_leads_a_board_member_to_the_panel(self):
        web_client = Client()
        web_client.force_login(self.user)
        response = web_client.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.redirect_chain, [("/panel/", 302)])

    def test_association_isolation(self):
        response = self.client.get("/api/v1/associations/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["slug"] for item in response.data["results"]], ["banda-test"])
        response = self.client.get(f"/api/v1/members/?association_id={self.other_association.id}")
        self.assertEqual(response.status_code, 403)

    def test_activity_invitation_response_and_attendance(self):
        member = Member.objects.create(association=self.association, account=self.user, first_name="Maria", last_name="Test")
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.REHEARSAL,
            status=Activity.Status.PUBLISHED,
            title="Ensayo",
            starts_at=timezone.now() + timedelta(days=1),
        )
        invitation = Invitation.objects.create(activity=activity, member=member)
        response = self.client.post(
            f"/api/v1/activities/{activity.id}/respond/",
            {"invitation_id": str(invitation.id), "response": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["response"], "accepted")
        response = self.client.post(
            f"/api/v1/activities/{activity.id}/attendance/{invitation.id}/",
            {"status": "present"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "present")

    def test_mandatory_activity_requires_a_reason_to_decline(self):
        member = Member.objects.create(
            association=self.association,
            account=self.user,
            first_name="Maria",
            last_name="Test",
        )
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.REHEARSAL,
            status=Activity.Status.PUBLISHED,
            title="Ensayo obligatorio",
            starts_at=timezone.now() + timedelta(days=1),
            is_mandatory=True,
        )
        invitation = Invitation.objects.create(activity=activity, member=member)

        response = self.client.post(
            f"/api/v1/activities/{activity.id}/respond/",
            {"invitation_id": str(invitation.id), "response": "declined", "note": ""},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        invitation.refresh_from_db()
        self.assertEqual(invitation.response, Invitation.Response.PENDING)

        response = self.client.post(
            f"/api/v1/activities/{activity.id}/respond/",
            {
                "invitation_id": str(invitation.id),
                "response": "declined",
                "note": "Cita médica",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        invitation.refresh_from_db()
        self.assertEqual(invitation.response, Invitation.Response.DECLINED)
        self.assertEqual(invitation.response_note, "Cita médica")

    def test_notification_device_must_flow(self):
        installation = "4a5b4c5d-1111-4111-8111-111111111111"
        response = self.client.post(
            "/api/v1/devices",
            {"installation_id": installation, "platform": "android", "push_token": "synthetic-token", "permission": "granted"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/api/v1/devices/receipt", {"installation_id": installation}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(DeviceRegistration.objects.get(installation_id=installation).last_receipt_at)

    def test_other_account_cannot_respond_to_invitation(self):
        member = Member.objects.create(association=self.association, first_name="M", last_name="Test")
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED,
            title="Actuación",
            starts_at=timezone.now() + timedelta(days=1),
        )
        invitation = Invitation.objects.create(activity=activity, member=member)
        self.client.force_authenticate(user=self.other)
        response = self.client.post(
            f"/api/v1/activities/{activity.id}/respond/",
            {"invitation_id": str(invitation.id), "response": "accepted"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_basic_member_can_read_own_profile_but_not_the_census(self):
        own_profile = Member.objects.create(
            association=self.association,
            account=self.basic_user,
            first_name="Membre",
            last_name="Prova",
            national_id="SYNTHETIC-ID",
        )
        Member.objects.create(association=self.association, first_name="Altra", last_name="Persona")
        self.client.force_authenticate(user=self.basic_user)

        response = self.client.get(f"/api/v1/members/?association_id={self.association.id}")
        self.assertEqual(response.status_code, 403)

        response = self.client.get("/api/v1/members/me/", HTTP_X_ASSOCIATION_ID=str(self.association.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(own_profile.id))
        self.assertEqual(response.data["national_id"], "SYNTHETIC-ID")

    def test_permission_errors_respect_requested_language(self):
        self.client.force_authenticate(user=self.basic_user)

        response = self.client.get(
            f"/api/v1/members/?association_id={self.association.id}",
            HTTP_ACCEPT_LANGUAGE="en",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "You do not have permission to perform this action.")

        response = self.client.get(
            f"/api/v1/members/?association_id={self.association.id}",
            HTTP_ACCEPT_LANGUAGE="ca",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data["detail"], "No tens permisos per a realitzar esta acció.")

    def test_basic_member_cannot_modify_catalogues_or_activities(self):
        member = Member.objects.create(
            association=self.association,
            account=self.basic_user,
            first_name="Membre",
            last_name="Prova",
        )
        section = Section.objects.create(association=self.association, name="Vent")
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.REHEARSAL,
            status=Activity.Status.PUBLISHED,
            title="Assaig",
            starts_at=timezone.now() + timedelta(days=1),
        )
        Invitation.objects.create(activity=activity, member=member)
        self.client.force_authenticate(user=self.basic_user)

        response = self.client.patch(
            f"/api/v1/sections/{section.id}/?association_id={self.association.id}",
            {"name": "Modificat"},
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        section.refresh_from_db()
        self.assertEqual(section.name, "Vent")

        response = self.client.delete(
            f"/api/v1/activities/{activity.id}/?association_id={self.association.id}"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Activity.objects.filter(pk=activity.id).exists())

    def test_cross_association_relations_are_rejected(self):
        foreign_section = Section.objects.create(association=self.other_association, name="Metall")
        foreign_member = Member.objects.create(
            association=self.other_association, first_name="Persona", last_name="Aliena"
        )
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.PERFORMANCE,
            title="Concert",
            starts_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(
            f"/api/v1/instruments/?association_id={self.association.id}",
            {"name": "Trompeta", "section": foreign_section.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Instrument.objects.exists())

        response = self.client.post(
            f"/api/v1/transports/?association_id={self.association.id}",
            {
                "activity": activity.id,
                "kind": Transport.Kind.CAR,
                "label": "Cotxe 1",
                "capacity": 4,
                "driver": foreign_member.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Transport.objects.exists())

    def test_basic_member_only_sees_own_transport_assignment(self):
        account_model = get_user_model()
        second_user = account_model.objects.create_user(
            username="second@example.invalid", email="second@example.invalid", password="secret-password"
        )
        second_access = AssociationAccess.objects.create(association=self.association, account=second_user)
        AssociationRole.objects.create(access=second_access, role=AssociationRole.Role.MEMBER)
        own_member = Member.objects.create(
            association=self.association, account=self.basic_user, first_name="Membre", last_name="Prova"
        )
        second_member = Member.objects.create(
            association=self.association, account=second_user, first_name="Segona", last_name="Persona"
        )
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.PERFORMANCE,
            status=Activity.Status.PUBLISHED,
            title="Concert",
            starts_at=timezone.now() + timedelta(days=1),
        )
        own_transport = Transport.objects.create(
            activity=activity, kind=Transport.Kind.CAR, label="Cotxe propi", capacity=2
        )
        other_transport = Transport.objects.create(
            activity=activity, kind=Transport.Kind.CAR, label="Cotxe alié", capacity=2
        )
        own_assignment = TransportAssignment.objects.create(transport=own_transport, member=own_member)
        TransportAssignment.objects.create(transport=other_transport, member=second_member)
        self.client.force_authenticate(user=self.basic_user)

        response = self.client.get(f"/api/v1/transports/?association_id={self.association.id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [str(own_transport.id)])

        response = self.client.get(
            f"/api/v1/transport-assignments/?association_id={self.association.id}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([item["id"] for item in response.data["results"]], [own_assignment.id])

    def test_transport_assignment_rejects_full_capacity_and_activity_duplicate(self):
        first_member = Member.objects.create(
            association=self.association, first_name="Primera", last_name="Persona"
        )
        second_member = Member.objects.create(
            association=self.association, first_name="Segona", last_name="Persona"
        )
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.PERFORMANCE,
            title="Concert",
            starts_at=timezone.now() + timedelta(days=1),
        )
        first_transport = Transport.objects.create(
            activity=activity, kind=Transport.Kind.CAR, label="Cotxe ple", capacity=1
        )
        second_transport = Transport.objects.create(
            activity=activity, kind=Transport.Kind.CAR, label="Segon cotxe", capacity=2
        )

        response = self.client.post(
            f"/api/v1/transport-assignments/?association_id={self.association.id}",
            {"transport": first_transport.id, "member": first_member.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)

        response = self.client.post(
            f"/api/v1/transport-assignments/?association_id={self.association.id}",
            {"transport": first_transport.id, "member": second_member.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("transport", response.data)

        response = self.client.post(
            f"/api/v1/transport-assignments/?association_id={self.association.id}",
            {"transport": second_transport.id, "member": first_member.id},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("member", response.data)
        self.assertEqual(TransportAssignment.objects.count(), 1)

    def test_panel_is_restricted_to_manager_roles(self):
        basic_client = Client()
        basic_client.force_login(self.basic_user)
        self.assertEqual(basic_client.get("/panel/").status_code, 403)

        manager_client = Client()
        manager_client.force_login(self.user)
        self.assertEqual(manager_client.get("/panel/").status_code, 200)

    def test_panel_invites_all_active_musicians_once_and_marks_mandatory(self):
        first = Member.objects.create(
            association=self.association,
            account=self.basic_user,
            first_name="Música",
            last_name="Primera",
        )
        second = Member.objects.create(
            association=self.association,
            first_name="Músico",
            last_name="Segundo",
        )
        Member.objects.create(
            association=self.association,
            first_name="Mecenas",
            last_name="Activo",
            kind=Member.Kind.SUPPORTER,
        )
        Member.objects.create(
            association=self.association,
            first_name="Música",
            last_name="Inactiva",
            status=Member.Status.INACTIVE,
        )
        Member.objects.create(
            association=self.other_association,
            first_name="Otra",
            last_name="Banda",
        )
        activity = Activity.objects.create(
            association=self.association,
            created_by=self.user,
            kind=Activity.Kind.REHEARSAL,
            status=Activity.Status.PUBLISHED,
            title="Ensayo para toda la banda",
            starts_at=timezone.now() + timedelta(days=1),
        )
        web_client = Client()
        web_client.force_login(self.user)
        detail_url = f"/panel/activities/{activity.id}/?association_id={self.association.id}"

        response = web_client.post(
            detail_url,
            {"invite_all_musicians": "1", "is_mandatory": "1"},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 nuevas")
        activity.refresh_from_db()
        self.assertTrue(activity.is_mandatory)
        self.assertSetEqual(
            set(activity.invitations.values_list("member_id", flat=True)),
            {first.id, second.id},
        )
        self.assertEqual(Notification.objects.filter(activity=activity).count(), 1)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_member_access_invitation_creates_and_links_account_once(self):
        member = Member.objects.create(
            association=self.association,
            first_name="Núria",
            last_name="Ferrer Vidal",
            email="nuria@example.invalid",
        )
        web_client = Client()
        web_client.force_login(self.user)
        access_url = f"/panel/members/access/?association_id={self.association.id}"

        response = web_client.post(
            access_url,
            {
                "association_id": str(self.association.id),
                "action": "invite_selected",
                "member_ids": [str(member.id)],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se han enviado 1 invitaciones")
        invitation = AccessInvitation.objects.get(member=member)
        self.assertIsNotNone(invitation.sent_at)
        self.assertEqual(invitation.last_send_error, "")
        self.assertEqual(len(mail.outbox), 1)
        activation_path = re.search(
            r"http://testserver(/accounts/activate/[^\s]+/)",
            mail.outbox[0].body,
        ).group(1)
        raw_token = activation_path.rstrip("/").rsplit("/", 1)[-1]
        self.assertNotEqual(invitation.token_digest, raw_token)
        self.assertNotIn(raw_token, invitation.token_digest)

        anonymous_client = Client()
        self.assertEqual(anonymous_client.get(activation_path).status_code, 200)
        password = "Contrasenya-segura-2026!"
        response = anonymous_client.post(
            activation_path,
            {"password": password, "password_confirmation": password},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cuenta activada")
        member.refresh_from_db()
        invitation.refresh_from_db()
        self.assertIsNotNone(invitation.accepted_at)
        self.assertIsNotNone(member.account_id)
        self.assertEqual(member.account.email, "nuria@example.invalid")
        self.assertIsNotNone(authenticate(username=member.account.username, password=password))
        access = AssociationAccess.objects.get(association=self.association, account=member.account)
        self.assertTrue(
            access.role_assignments.filter(role=AssociationRole.Role.MEMBER).exists()
        )
        self.assertEqual(anonymous_client.get(activation_path).status_code, 400)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_resending_revokes_old_link_and_cross_association_is_excluded(self):
        member = Member.objects.create(
            association=self.association,
            first_name="Pau",
            last_name="Soler",
            email="pau@example.invalid",
        )
        other_member = Member.objects.create(
            association=self.other_association,
            first_name="Altra",
            last_name="Persona",
            email="altra@example.invalid",
        )
        web_client = Client()
        web_client.force_login(self.user)
        access_url = f"/panel/members/access/?association_id={self.association.id}"
        payload = {
            "association_id": str(self.association.id),
            "action": "invite_selected",
            "member_ids": [str(member.id), str(other_member.id)],
        }
        web_client.post(access_url, payload)
        first = AccessInvitation.objects.get(member=member)
        first_path = re.search(
            r"http://testserver(/accounts/activate/[^\s]+/)", mail.outbox[-1].body
        ).group(1)
        self.assertFalse(AccessInvitation.objects.filter(member=other_member).exists())

        web_client.post(access_url, payload)
        first.refresh_from_db()
        self.assertIsNotNone(first.revoked_at)
        self.assertEqual(AccessInvitation.objects.filter(member=member).count(), 2)
        self.assertEqual(Client().get(first_path).status_code, 400)

        latest = AccessInvitation.objects.filter(member=member).first()
        revoke_response = web_client.post(
            access_url,
            {"association_id": str(self.association.id), "revoke_id": str(latest.id)},
            follow=True,
        )
        self.assertContains(revoke_response, "Invitación revocada")
        latest.refresh_from_db()
        self.assertIsNotNone(latest.revoked_at)

    def test_member_cannot_manage_access_invitations(self):
        web_client = Client()
        web_client.force_login(self.basic_user)
        response = web_client.get(
            f"/panel/members/access/?association_id={self.association.id}"
        )
        self.assertEqual(response.status_code, 403)

        response = web_client.post(
            f"/panel/members/access/?association_id={self.association.id}",
            {"association_id": str(self.association.id)},
        )
        self.assertEqual(response.status_code, 403)

    def test_web_import_previews_confirms_reports_and_is_idempotent(self):
        csv_content = (
            "external_id,first_name,last_name,email,kind\n"
            "MUS-001,Marina,Soler,marina@example.invalid,musician\n"
            "MUS-002,,Sense Nom,invalid@example.invalid,musician\n"
        ).encode()
        web_client = Client()
        web_client.force_login(self.user)

        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = web_client.get(
                f"/panel/members/import/template.csv?association_id={self.association.id}"
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("plantilla-miembros.csv", response["Content-Disposition"])

            response = web_client.post(
                f"/panel/members/import/?association_id={self.association.id}",
                {
                    "association_id": str(self.association.id),
                    "file": SimpleUploadedFile("miembros.csv", csv_content, content_type="text/csv"),
                },
            )
            self.assertEqual(response.status_code, 302)
            batch = ImportBatch.objects.get()
            self.assertEqual(batch.status, ImportBatch.Status.UPLOADED)
            self.assertTrue(batch.source_file)
            self.assertEqual(Member.objects.count(), 0)

            detail_url = f"/panel/members/import/{batch.id}/?association_id={self.association.id}"
            self.assertContains(web_client.get(detail_url), "external_id")
            response = web_client.post(
                detail_url,
                {
                    "association_id": str(self.association.id),
                    "action": "preview",
                    "column_0": "external_id",
                    "column_1": "first_name",
                    "column_2": "last_name",
                    "column_3": "email",
                    "column_4": "kind",
                },
            )
            self.assertEqual(response.status_code, 302)
            batch.refresh_from_db()
            self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)
            self.assertEqual(len(batch.preview), 2)
            self.assertEqual(batch.preview[0]["errors"], [])
            self.assertIn("Falta el nombre.", batch.preview[1]["errors"])
            self.assertEqual(Member.objects.count(), 0)
            self.assertContains(web_client.get(detail_url), "MUS-001")
            source_name = batch.source_file.name

            with self.captureOnCommitCallbacks(execute=True):
                response = web_client.post(
                    detail_url,
                    {"association_id": str(self.association.id), "action": "confirm"},
                )
            self.assertEqual(response.status_code, 302)
            batch.refresh_from_db()
            self.assertEqual(batch.status, ImportBatch.Status.CONFIRMED)
            self.assertEqual(batch.result, {"created": 1, "updated": 0, "rejected": 1})
            self.assertEqual([item["action"] for item in batch.preview], ["created", "rejected"])
            self.assertFalse(batch.source_file)
            self.assertFalse(batch.source_file.storage.exists(source_name))
            self.assertEqual(Member.objects.filter(association=self.association).count(), 1)
            self.assertContains(web_client.get(detail_url), "MUS-001")

            response = web_client.post(
                detail_url,
                {"association_id": str(self.association.id), "action": "confirm"},
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(Member.objects.filter(association=self.association).count(), 1)

    def test_official_template_is_automapped_and_imports_split_surnames(self):
        web_client = Client()
        web_client.force_login(self.user)

        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            template_response = web_client.get(
                f"/panel/members/import/template.csv?association_id={self.association.id}"
            )
            self.assertEqual(template_response.status_code, 200)

            upload_response = web_client.post(
                f"/panel/members/import/?association_id={self.association.id}",
                {
                    "association_id": str(self.association.id),
                    "file": SimpleUploadedFile(
                        "plantilla-miembros.csv",
                        template_response.content,
                        content_type="text/csv",
                    ),
                },
            )
            self.assertEqual(upload_response.status_code, 302)
            batch = ImportBatch.objects.get()
            self.assertEqual(
                batch.mapping,
                {
                    "external_id": "external_id",
                    "first_name": "first_name",
                    "first_surname": "first_surname",
                    "second_surname": "second_surname",
                    "national_id": "national_id",
                    "address": "address",
                    "phone": "phone",
                    "email": "email",
                    "kind": "kind",
                },
            )

            detail_url = f"/panel/members/import/{batch.id}/?association_id={self.association.id}"
            detail_response = web_client.get(detail_url)
            self.assertContains(detail_response, 'option value="first_name" selected')
            self.assertContains(detail_response, 'option value="first_surname" selected')
            self.assertContains(detail_response, 'option value="second_surname" selected')

            preview_response = web_client.post(
                detail_url,
                {
                    "association_id": str(self.association.id),
                    "action": "preview",
                    **{
                        f"column_{index}": batch.mapping[header]
                        for index, header in enumerate(batch.source_headers)
                    },
                },
            )
            self.assertEqual(preview_response.status_code, 302)
            batch.refresh_from_db()
            self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)
            self.assertEqual(batch.preview[0]["errors"], [])
            self.assertEqual(batch.preview[0]["data"]["last_name"], "Soler Ferri")

            with self.captureOnCommitCallbacks(execute=True):
                confirm_response = web_client.post(
                    detail_url,
                    {"association_id": str(self.association.id), "action": "confirm"},
                )
            self.assertEqual(confirm_response.status_code, 302)
            member = Member.objects.get(external_id="MUS-001")
            self.assertEqual(member.first_name, "Marina")
            self.assertEqual(member.last_name, "Soler Ferri")

    def test_import_requires_name_and_surname_mapping(self):
        csv_content = b"codigo,nombre_persona\nMUS-101,Persona\n"
        web_client = Client()
        web_client.force_login(self.user)

        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            upload_response = web_client.post(
                f"/panel/members/import/?association_id={self.association.id}",
                {
                    "association_id": str(self.association.id),
                    "file": SimpleUploadedFile("sin-mapeo.csv", csv_content, content_type="text/csv"),
                },
            )
            batch = ImportBatch.objects.get()
            detail_url = f"/panel/members/import/{batch.id}/?association_id={self.association.id}"
            preview_response = web_client.post(
                detail_url,
                {"association_id": str(self.association.id), "action": "preview"},
                follow=True,
            )
            self.assertEqual(preview_response.status_code, 200)
            self.assertContains(preview_response, "Asigna una columna al campo Nombre.")
            batch.refresh_from_db()
            self.assertEqual(batch.status, ImportBatch.Status.UPLOADED)
            self.assertEqual(batch.preview, [])

    def test_all_rejected_preview_cannot_be_confirmed_and_can_be_remapped(self):
        csv_content = b"first_name,first_surname\n,\n"
        web_client = Client()
        web_client.force_login(self.user)

        with TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            web_client.post(
                f"/panel/members/import/?association_id={self.association.id}",
                {
                    "association_id": str(self.association.id),
                    "file": SimpleUploadedFile("rechazado.csv", csv_content, content_type="text/csv"),
                },
            )
            batch = ImportBatch.objects.get()
            detail_url = f"/panel/members/import/{batch.id}/?association_id={self.association.id}"
            web_client.post(
                detail_url,
                {
                    "association_id": str(self.association.id),
                    "action": "preview",
                    "column_0": "first_name",
                    "column_1": "first_surname",
                },
            )
            batch.refresh_from_db()
            self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)
            self.assertEqual(len(batch.preview[0]["errors"]), 2)

            response = web_client.get(detail_url)
            self.assertContains(response, "No hay filas válidas para confirmar")
            self.assertContains(response, 'option value="first_surname" selected')
            self.assertNotContains(response, ">Confirmar importación</button>")

            confirm_response = web_client.post(
                detail_url,
                {"association_id": str(self.association.id), "action": "confirm"},
                follow=True,
            )
            self.assertContains(confirm_response, "No hay filas válidas que confirmar")
            batch.refresh_from_db()
            self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)
            self.assertEqual(Member.objects.count(), 0)

    def test_member_without_admin_role_cannot_use_import_panel(self):
        web_client = Client()
        web_client.force_login(self.basic_user)
        response = web_client.get(
            f"/panel/members/import/?association_id={self.association.id}"
        )
        self.assertEqual(response.status_code, 403)

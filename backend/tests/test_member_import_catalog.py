"""Importación del censo con cuerdas e instrumentos.

La previsualización solo lee el catálogo de la asociación del lote y anuncia
qué cuerdas e instrumentos se crearán; se crean al confirmar, en la misma
transacción que las fichas. El catálogo de otra asociación nunca se reutiliza.
Todos los datos son sintéticos.
"""

import json
import shutil
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members import services
from apps.members.models import ImportBatch, Instrument, Member, MemberInstrument, Section

Role = AssociationRole.Role
EXAMPLE_CSV = Path(settings.BASE_DIR).parent / "docs" / "ejemplos" / "musicos-sinteticos.csv"

BASE_MAPPING = {"external_id": "external_id", "nombre": "first_name", "apellidos": "last_name"}
CATALOG_MAPPING = {**BASE_MAPPING, "cuerda": "section", "instrumento": "instrument"}
CATALOG_HEADER = "external_id,nombre,apellidos,cuerda,instrumento\n"


def csv_upload(body, header=CATALOG_HEADER, name="musicos.csv"):
    return SimpleUploadedFile(name, (header + body).encode(), content_type="text/csv")


class CatalogKeyTests(SimpleTestCase):
    def test_ignores_case_accents_and_spaces(self):
        self.assertEqual(services.catalog_key("  Trombón "), services.catalog_key("TROMBON"))
        self.assertEqual(services.catalog_key("Saxo  barítono"), services.catalog_key("saxo baritono"))
        self.assertEqual(services.catalog_key("Percusión"), services.catalog_key("percusion"))
        self.assertNotEqual(services.catalog_key("Clarinete"), services.catalog_key("Clarinete bajo"))

    def test_suggests_section_and_instrument_columns_from_aliases(self):
        for header in ("cuerda", "Corda", "Section", "SECCIÓN"):
            self.assertEqual(services.suggest_import_mapping([header]), {header: "section"})
        for header in ("instrumento", "Instrument", "Instrumentos"):
            self.assertEqual(services.suggest_import_mapping([header]), {header: "instrument"})

    def test_uses_catalog_columns(self):
        self.assertFalse(services.uses_catalog_columns(BASE_MAPPING))
        self.assertTrue(services.uses_catalog_columns({**BASE_MAPPING, "x": "instrument"}))
        self.assertFalse(services.uses_catalog_columns(None))


class ImportCatalogFixture(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = self.settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()
        self.association = Association.objects.create(name="Banda Sintética", slug="banda-sintetica")
        self.other_association = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.wood = Section.objects.create(association=self.association, name="Madera", order=1)
        self.clarinet = Instrument.objects.create(association=self.association, name="Clarinete", section=self.wood)
        self.loose_flute = Instrument.objects.create(association=self.association, name="Flauta")
        # Catálogo ajeno con nombres que coinciden: nunca debe reutilizarse.
        self.foreign_brass = Section.objects.create(association=self.other_association, name="Metal")
        self.foreign_tuba = Instrument.objects.create(
            association=self.other_association, name="Tuba", section=self.foreign_brass
        )
        self.admin = self.account_with_role("admin@example.invalid", self.association, Role.ADMIN)
        self.other_admin = self.account_with_role("otra@example.invalid", self.other_association, Role.ADMIN)

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def account_with_role(self, email, association, role):
        account = get_user_model().objects.create_user(username=email, email=email, password="synthetic-password")
        access = AssociationAccess.objects.create(association=association, account=account)
        AssociationRole.objects.create(access=access, role=role)
        return account

    def preview(self, body, mapping=CATALOG_MAPPING, header=CATALOG_HEADER, association=None):
        _content, content_hash, rows = services.parse_import(
            csv_upload(body, header), mapping, association=association
        )
        return rows

    def batch(self, body, mapping=CATALOG_MAPPING, header=CATALOG_HEADER, association=None):
        association = association or self.association
        rows = self.preview(body, mapping, header)
        return ImportBatch.objects.create(
            association=association,
            created_by=self.admin,
            filename="musicos.csv",
            content_hash=f"{len(ImportBatch.objects.all())}-{hash(body)}",
            mapping=mapping,
            preview=rows,
            status=ImportBatch.Status.PREVIEW,
        )


class ParseCatalogCellsTests(ImportCatalogFixture):
    def test_splits_several_instruments_and_drops_repeated_ones(self):
        rows = self.preview(
            "M-1,Pau,Climent,Madera,Clarinete; Requinto / clarinete;;\n"
            "M-2,Neus,Gil,Madera,  Saxo   alto  \n"
        )
        self.assertEqual(rows[0]["data"]["instruments"], ["Clarinete", "Requinto"])
        self.assertEqual(rows[0]["data"]["section"], "Madera")
        self.assertNotIn("instrument", rows[0]["data"])
        self.assertEqual(rows[1]["data"]["instruments"], ["Saxo alto"])
        self.assertEqual([row["errors"] for row in rows], [[], []])

    def test_row_without_instrument_is_valid(self):
        rows = self.preview("M-1,Pau,Climent,,\n")
        self.assertEqual(rows[0]["errors"], [])
        self.assertEqual(rows[0]["warnings"], [])
        self.assertEqual(rows[0]["data"]["instruments"], [])

    def test_section_without_instrument_is_a_warning(self):
        rows = self.preview("M-1,Pau,Climent,Metal,\n")
        self.assertEqual(rows[0]["errors"], [])
        self.assertIn("La cuerda «Metal» se ignora", rows[0]["warnings"][0])

    def test_formula_like_and_too_long_names_are_rejected(self):
        rows = self.preview(
            "M-1,Pau,Climent,=HYPERLINK(1),Clarinete\n"
            "M-2,Neus,Gil,Madera,@SUM(1)\n"
            f"M-3,Ana,Mas,Madera,{'x' * 81}\n"
        )
        self.assertIn("no puede empezar por", rows[0]["errors"][0])
        self.assertIn("no puede empezar por", rows[1]["errors"][0])
        self.assertIn("supera 80 caracteres", rows[2]["errors"][0])

    def test_parse_without_association_does_not_consult_the_catalog(self):
        rows = self.preview("M-1,Pau,Climent,Metal,Clarinete\n")
        self.assertEqual(rows[0]["errors"], [])

    def test_parse_with_association_reports_catalog_conflicts(self):
        rows = self.preview("M-1,Pau,Climent,Metal,Clarinete\n", association=self.association)
        self.assertIn("ya está en la cuerda «Madera»", rows[0]["errors"][0])


class PlanCatalogTests(ImportCatalogFixture):
    def plan(self, body, association=None):
        return services.plan_import_catalog(association or self.association, self.preview(body))

    def test_existing_entries_are_matched_without_case_accents_or_spaces(self):
        plan = self.plan("M-1,Pau,Climent,MADERA,  clarinete \nM-2,Ana,Mas,,FLAUTA\n")
        self.assertEqual(plan.new_sections, {})
        self.assertEqual(plan.new_instruments, {})
        self.assertEqual(plan.row_errors, {})

    def test_new_sections_and_instruments_are_listed_once(self):
        plan = self.plan(
            "M-1,Pau,Climent,Metal,Trompeta\n"
            "M-2,Ana,Mas,metal,trompeta; Tuba\n"
            "M-3,Neus,Gil,,Fagot\n"
            "M-4,Joan,Ribes,Madera,fagot\n"
        )
        self.assertEqual(list(plan.new_sections.values()), ["Metal"])
        self.assertEqual(plan.new_instrument_labels(), ["Trompeta (Metal)", "Tuba (Metal)", "Fagot (Madera)"])

    def test_instrument_under_another_section_is_a_row_error_not_a_reassignment(self):
        plan = self.plan("M-1,Pau,Climent,Metal,Clarinete; Bombo\n")
        self.assertIn("Clarinete", plan.row_errors[2][0])
        self.assertIn("«Madera»", plan.row_errors[2][0])
        # La fila rechazada no aporta nada al catálogo.
        self.assertEqual(plan.new_sections, {})
        self.assertEqual(plan.new_instruments, {})

    def test_file_putting_one_new_instrument_in_two_sections_rejects_the_later_row(self):
        plan = self.plan("M-1,Pau,Climent,Metal,Tuba\nM-2,Ana,Mas,Percusión,Tuba\n")
        self.assertNotIn(2, plan.row_errors)
        self.assertIn("«Metal» y «Percusión»", plan.row_errors[3][0])
        self.assertEqual(list(plan.new_sections.values()), ["Metal"])

    def test_instrument_without_section_in_catalog_is_kept_with_a_warning(self):
        plan = self.plan("M-1,Pau,Climent,Madera,Flauta\n")
        self.assertEqual(plan.row_errors, {})
        self.assertIn("no tiene cuerda en el catálogo", plan.row_warnings[2][0])

    def test_catalog_of_another_association_is_never_reused(self):
        plan = self.plan("M-1,Pau,Climent,Metal,Tuba\n")
        self.assertEqual(list(plan.new_sections.values()), ["Metal"])
        self.assertEqual(plan.new_instrument_labels(), ["Tuba (Metal)"])
        other_plan = self.plan("M-1,Pau,Climent,Metal,Tuba\n", association=self.other_association)
        self.assertEqual(other_plan.new_sections, {})
        self.assertEqual(other_plan.new_instruments, {})


class ConfirmCatalogTests(ImportCatalogFixture):
    def test_confirm_creates_catalog_and_links_instruments_with_first_as_primary(self):
        batch = self.batch("M-1,Pau,Climent,Metal,Trompeta / Fliscorno\nM-2,Ana,Mas,madera,CLARINETE\nM-3,Neus,Gil,,\n")
        self.assertFalse(Section.objects.filter(association=self.association, name="Metal").exists())

        result = services.confirm_import(batch)

        self.assertEqual(result["created"], 3)
        self.assertEqual(result["sections_created"], ["Metal"])
        self.assertEqual(result["instruments_created"], ["Trompeta (Metal)", "Fliscorno (Metal)"])
        brass = Section.objects.get(association=self.association, name="Metal")
        self.assertGreater(brass.order, self.wood.order)
        trumpet = Instrument.objects.get(association=self.association, name="Trompeta")
        self.assertEqual(trumpet.section, brass)
        pau = Member.objects.get(association=self.association, external_id="M-1")
        links = {link.instrument.name: link.is_primary for link in pau.member_instruments.select_related("instrument")}
        self.assertEqual(links, {"Trompeta": True, "Fliscorno": False})
        ana = Member.objects.get(association=self.association, external_id="M-2")
        self.assertEqual([link.instrument for link in ana.member_instruments.all()], [self.clarinet])
        self.assertFalse(Member.objects.get(external_id="M-3").member_instruments.exists())
        # Sin duplicar el clarinete existente ni tocar el catálogo ajeno.
        self.assertEqual(Instrument.objects.filter(association=self.association, name__iexact="clarinete").count(), 1)
        self.assertEqual(Section.objects.filter(association=self.other_association).count(), 1)
        self.assertEqual(Instrument.objects.filter(association=self.other_association).count(), 1)

    def test_conflicting_row_is_rejected_at_confirm_even_if_preview_missed_it(self):
        batch = self.batch("M-1,Pau,Climent,Metal,Clarinete\nM-2,Ana,Mas,Metal,Trompeta\n")
        self.assertEqual(batch.preview[0]["errors"], [])

        result = services.confirm_import(batch)

        self.assertEqual((result["created"], result["rejected"]), (1, 1))
        batch.refresh_from_db()
        self.assertEqual(batch.preview[0]["action"], "rejected")
        self.assertIn("ya está en la cuerda «Madera»", batch.preview[0]["errors"][0])
        self.clarinet.refresh_from_db()
        self.assertEqual(self.clarinet.section, self.wood)
        self.assertFalse(Member.objects.filter(external_id="M-1").exists())

    def test_catalog_entry_created_between_preview_and_confirm_is_reused(self):
        batch = self.batch("M-1,Pau,Climent,Percusión,Caja\n")
        percussion = Section.objects.create(association=self.association, name="Percusion")
        drum = Instrument.objects.create(association=self.association, name="caja", section=percussion)

        result = services.confirm_import(batch)

        self.assertEqual(result["sections_created"], [])
        self.assertEqual(result["instruments_created"], [])
        self.assertEqual(Member.objects.get(external_id="M-1").member_instruments.get().instrument, drum)

    def test_reimport_updates_by_external_id_without_duplicating_instruments(self):
        services.confirm_import(self.batch("M-1,Pau,Climent,Madera,Clarinete; Requinto\nM-2,Ana,Mas,Madera,Clarinete\n"))
        pau = Member.objects.get(external_id="M-1")
        self.assertEqual(pau.member_instruments.count(), 2)

        result = services.confirm_import(
            self.batch("M-1,Pau,Climent Ortolà,Madera,requinto; clarinete\nM-2,Ana,Mas,,\n")
        )

        self.assertEqual((result["created"], result["updated"]), (0, 2))
        self.assertEqual(Member.objects.filter(association=self.association).count(), 2)
        pau.refresh_from_db()
        self.assertEqual(pau.last_name, "Climent Ortolà")
        links = {link.instrument.name: link.is_primary for link in pau.member_instruments.select_related("instrument")}
        self.assertEqual(links, {"Requinto": True, "Clarinete": False})
        self.assertEqual(MemberInstrument.objects.filter(member=pau).count(), 2)
        # Una celda vacía no borra los instrumentos que ya tenía la ficha.
        ana = Member.objects.get(external_id="M-2")
        self.assertEqual([link.instrument for link in ana.member_instruments.all()], [self.clarinet])
        self.assertEqual(Instrument.objects.filter(association=self.association, name="Requinto").count(), 1)

    def test_without_catalog_columns_result_keeps_its_previous_shape(self):
        batch = self.batch("M-1,Pau,Climent\n", mapping=BASE_MAPPING, header="external_id,nombre,apellidos\n")
        self.assertEqual(services.confirm_import(batch), {"created": 1, "updated": 0, "rejected": 0})

    def test_all_rows_in_conflict_cannot_be_confirmed_and_nothing_is_created(self):
        batch = self.batch("M-1,Pau,Climent,Metal,Clarinete; Bombo\n")
        with self.assertRaises(services.ValidationError):
            services.confirm_import(batch)
        self.assertFalse(Member.objects.exists())
        self.assertFalse(Instrument.objects.filter(association=self.association, name="Bombo").exists())
        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)


class PanelImportCatalogTests(ImportCatalogFixture):
    def upload(self, client, content, name="musicos.csv", association=None):
        association = association or self.association
        response = client.post(
            f"/panel/members/import/?association_id={association.id}",
            {"association_id": str(association.id), "file": SimpleUploadedFile(name, content, content_type="text/csv")},
        )
        self.assertEqual(response.status_code, 302)
        return ImportBatch.objects.filter(association=association).latest("created_at")

    def generate_preview(self, client, batch):
        response = client.post(
            self.detail_url(batch),
            {
                "association_id": str(batch.association_id),
                "action": "preview",
                **{f"column_{index}": batch.mapping.get(header, "") for index, header in enumerate(batch.source_headers)},
            },
        )
        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        return batch

    def detail_url(self, batch):
        return f"/panel/members/import/{batch.id}/?association_id={batch.association_id}"

    def confirm(self, client, batch):
        with self.captureOnCommitCallbacks(execute=True):
            response = client.post(
                self.detail_url(batch), {"association_id": str(batch.association_id), "action": "confirm"}
            )
        self.assertEqual(response.status_code, 302)
        batch.refresh_from_db()
        return batch

    def test_preview_announces_new_catalog_without_creating_anything_then_confirm_creates_it(self):
        client = Client()
        client.force_login(self.admin)
        content = (
            CATALOG_HEADER
            + "M-1,Pau,Climent,Metal,Trompeta; Fliscorno\n"
            + "M-2,Ana,Mas,Percusión,Caja\n"
            + "M-3,Joan,Ribes,Metal,Clarinete\n"
            + "M-4,Neus,Gil,,\n"
        ).encode()
        batch = self.upload(client, content)
        self.assertEqual(batch.mapping["cuerda"], "section")
        self.assertEqual(batch.mapping["instrumento"], "instrument")
        page = client.get(self.detail_url(batch))
        self.assertContains(page, 'option value="section" selected')
        self.assertContains(page, 'option value="instrument" selected')

        batch = self.generate_preview(client, batch)
        self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)
        self.assertFalse(Member.objects.exists())
        self.assertEqual(Section.objects.filter(association=self.association).count(), 1)
        self.assertEqual(Instrument.objects.filter(association=self.association).count(), 2)

        page = client.get(self.detail_url(batch))
        self.assertContains(page, "Se crearán 2 cuerdas:")
        self.assertContains(page, "Metal, Percusión")
        self.assertContains(page, "Se crearán 3 instrumentos:")
        self.assertContains(page, "Trompeta (Metal), Fliscorno (Metal), Caja (Percusión)")
        self.assertContains(page, "<th>Cuerda</th>", html=False)
        self.assertContains(page, "Trompeta, Fliscorno")
        self.assertContains(page, "ya está en la cuerda «Madera» del catálogo")
        self.assertContains(page, ">Confirmar importación</button>")

        batch = self.confirm(client, batch)
        self.assertEqual(batch.status, ImportBatch.Status.CONFIRMED)
        self.assertEqual((batch.result["created"], batch.result["rejected"]), (3, 1))
        self.assertEqual(
            set(Section.objects.filter(association=self.association).values_list("name", flat=True)),
            {"Madera", "Metal", "Percusión"},
        )
        page = client.get(self.detail_url(batch))
        self.assertContains(page, "Se crearon 2 cuerdas:")
        self.assertContains(page, "Se crearon 3 instrumentos:")

    def test_preview_with_only_existing_catalog_says_so(self):
        client = Client()
        client.force_login(self.admin)
        batch = self.generate_preview(client, self.upload(client, (CATALOG_HEADER + "M-1,Pau,Climent,Madera,Clarinete\n").encode()))
        page = client.get(self.detail_url(batch))
        self.assertContains(page, "Todas las cuerdas e instrumentos del fichero ya existen")

    def test_import_without_catalog_columns_keeps_the_previous_table(self):
        client = Client()
        client.force_login(self.admin)
        batch = self.generate_preview(client, self.upload(client, b"external_id,nombre,apellidos\nM-1,Pau,Climent\n"))
        page = client.get(self.detail_url(batch))
        self.assertNotContains(page, "<th>Cuerda</th>", html=False)
        self.assertNotContains(page, "Catálogo de cuerdas e instrumentos")

    def test_other_association_admin_cannot_see_or_confirm_the_batch(self):
        client = Client()
        client.force_login(self.admin)
        batch = self.generate_preview(client, self.upload(client, (CATALOG_HEADER + "M-1,Pau,Climent,Metal,Tuba\n").encode()))

        intruder = Client()
        intruder.force_login(self.other_admin)
        foreign_url = f"/panel/members/import/{batch.id}/?association_id={self.other_association.id}"
        self.assertEqual(intruder.get(foreign_url).status_code, 404)
        self.assertEqual(
            intruder.post(foreign_url, {"association_id": str(self.other_association.id), "action": "confirm"}).status_code,
            404,
        )
        self.assertEqual(intruder.get(self.detail_url(batch)).status_code, 403)
        batch.refresh_from_db()
        self.assertEqual(batch.status, ImportBatch.Status.PREVIEW)

        # La Tuba ajena no sirve: la banda importadora crea la suya.
        self.confirm(client, batch)
        tuba = Instrument.objects.get(association=self.association, name="Tuba")
        self.assertNotEqual(tuba.pk, self.foreign_tuba.pk)
        self.assertEqual(tuba.section.association, self.association)
        self.assertEqual(Instrument.objects.filter(association=self.other_association).count(), 1)

    def test_board_member_without_admin_role_cannot_import(self):
        board = self.account_with_role("junta@example.invalid", self.association, Role.BOARD)
        client = Client()
        client.force_login(board)
        response = client.get(f"/panel/members/import/?association_id={self.association.id}")
        self.assertEqual(response.status_code, 403)

    def test_synthetic_example_file_imports_fifty_musicians_and_the_whole_catalog(self):
        empty_band = Association.objects.create(name="Banda Nueva", slug="banda-nueva")
        admin = self.account_with_role("nueva@example.invalid", empty_band, Role.ADMIN)
        client = Client()
        client.force_login(admin)
        content = EXAMPLE_CSV.read_bytes()

        batch = self.upload(client, content, name=EXAMPLE_CSV.name, association=empty_band)
        self.assertEqual(
            set(batch.mapping.values()),
            {"external_id", "first_name", "first_surname", "second_surname", "national_id", "phone", "email", "kind", "section", "instrument"},
        )
        batch = self.generate_preview(client, batch)
        self.assertEqual([item for item in batch.preview if item["errors"]], [])
        self.assertFalse(Member.objects.filter(association=empty_band).exists())
        self.assertFalse(Instrument.objects.filter(association=empty_band).exists())
        page = client.get(self.detail_url(batch))
        self.assertContains(page, "Se crearán 3 cuerdas:")
        self.assertContains(page, "Se crearán 21 instrumentos:")

        batch = self.confirm(client, batch)
        self.assertEqual(batch.result["created"], 50)
        self.assertEqual(batch.result["rejected"], 0)
        members = Member.objects.filter(association=empty_band)
        self.assertEqual(members.count(), 50)
        self.assertTrue(all(member.external_id.startswith("DEMO-") for member in members))
        self.assertTrue(all(member.email.endswith(".invalid") for member in members))
        self.assertTrue(all(member.national_id == "" for member in members))
        self.assertTrue(all(member.phone.startswith("+34 600 000 0") for member in members))
        catalog = {
            section.name: sorted(section.instruments.values_list("name", flat=True))
            for section in Section.objects.filter(association=empty_band)
        }
        self.assertEqual(
            catalog,
            {
                "Madera": sorted(
                    ["Flauta", "Flautín", "Oboe", "Fagot", "Clarinete", "Requinto", "Clarinete bajo",
                     "Saxo alto", "Saxo tenor", "Saxo barítono"]
                ),
                "Metal": sorted(["Trompeta", "Fliscorno", "Trompa", "Trombón", "Bombardino", "Tuba"]),
                "Percusión": sorted(["Caja", "Bombo", "Platos", "Timbales", "Láminas"]),
            },
        )
        primary = MemberInstrument.objects.filter(member__association=empty_band, is_primary=True)
        self.assertEqual(primary.count(), 50)
        self.assertEqual(primary.filter(instrument__name="Clarinete").count(), 13)
        self.assertEqual(primary.filter(instrument__name="Tuba").count(), 1)
        self.assertEqual(MemberInstrument.objects.filter(member__association=empty_band).count(), 52)
        # El catálogo de las otras bandas sigue intacto.
        self.assertEqual(Instrument.objects.filter(association=self.association).count(), 2)
        self.assertEqual(Instrument.objects.filter(association=self.other_association).count(), 1)


class ApiImportCatalogTests(ImportCatalogFixture):
    def test_api_preview_and_confirm_accept_the_new_columns(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.admin).key}")
        response = client.post(
            "/api/v1/imports/preview",
            {
                "association_id": str(self.association.id),
                "file": csv_upload("M-1,Pau,Climent,Metal,Trompeta\n"),
                "mapping": json.dumps(CATALOG_MAPPING),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["preview"][0]["data"]["instruments"], ["Trompeta"])
        self.assertFalse(Instrument.objects.filter(association=self.association, name="Trompeta").exists())

        response = client.post(f"/api/v1/imports/{response.data['id']}/confirm")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["sections_created"], ["Metal"])
        self.assertEqual(response.data["instruments_created"], ["Trompeta (Metal)"])

    def test_the_api_preview_reports_catalog_conflicts_before_confirming(self):
        Instrument.objects.create(association=self.association, name="Trompa", section=Section.objects.create(association=self.association, name="Metal"))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.admin).key}")
        response = client.post(
            "/api/v1/imports/preview",
            {
                "association_id": str(self.association.id),
                "file": csv_upload("M-1,Pau,Climent,Madera,Trompa\n"),
                "mapping": json.dumps(CATALOG_MAPPING),
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.data["preview"][0]["errors"])

    def test_confirming_an_unknown_import_is_a_404_not_a_500(self):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {Token.objects.create(user=self.admin).key}")
        response = client.post("/api/v1/imports/00000000-0000-0000-0000-000000000000/confirm")
        self.assertEqual(response.status_code, 404)

"""Cuerdas comunes y precarga de instrumentos (decisión 0012). Datos sintéticos."""

from collections import defaultdict
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, SimpleTestCase, TestCase, TransactionTestCase
from django.utils import translation
from rest_framework.test import APIClient

from apps.associations.models import Association, AssociationAccess, AssociationRole
from apps.members import catalog, services
from apps.members.models import Instrument, Member, MemberInstrument, Section

SECTION_CODES = ["brass", "woodwind", "percussion", "bowed_strings", "struck_strings", "plucked_strings"]


class CatalogDataTests(SimpleTestCase):
    def test_codes_are_unique_and_every_instrument_points_to_a_section(self):
        section_codes = [entry[0] for entry in catalog.SECTIONS]
        self.assertEqual(section_codes, SECTION_CODES)
        instrument_codes = [entry[0] for entry in catalog.INSTRUMENTS]
        self.assertEqual(len(instrument_codes), len(set(instrument_codes)))
        self.assertTrue({entry[1] for entry in catalog.INSTRUMENTS} <= set(section_codes))

    def test_every_entry_has_its_three_names(self):
        for code, _section, es, ca, en, _aliases in catalog.INSTRUMENTS:
            self.assertTrue(es and ca and en, code)
        for code, es, ca, en, _aliases in catalog.SECTIONS:
            self.assertTrue(es and ca and en, code)

    def test_no_name_or_alias_points_to_two_entries(self):
        for entries, names in ((catalog.INSTRUMENTS, catalog.instrument_names), (catalog.SECTIONS, catalog.section_names)):
            owners = defaultdict(set)
            for entry in entries:
                for name in names(entry):
                    owners[catalog.catalog_key(name)].add(entry[0])
            self.assertEqual({key: codes for key, codes in owners.items() if len(codes) > 1}, {})


class GlobalSectionTests(TestCase):
    def test_the_six_sections_exist_after_migrating(self):
        self.assertEqual(list(Section.objects.values_list("code", flat=True)), SECTION_CODES)
        self.assertEqual(
            list(Section.objects.values_list("name", flat=True)),
            ["Viento metal", "Viento madera", "Percusión", "Cuerda frotada", "Cuerda percutida", "Cuerda pulsada"],
        )

    def test_label_follows_the_active_language(self):
        brass = Section.objects.get(code="brass")
        with translation.override("ca"):
            self.assertEqual(brass.label, "Vent metall")
        with translation.override("en"):
            self.assertEqual(str(brass), "Brass")
        with translation.override("es"):
            self.assertEqual(brass.label, "Viento metal")

    def test_instrument_without_translation_falls_back_to_its_name(self):
        band = Association.objects.create(name="Banda", slug="banda")
        own = Instrument.objects.create(association=band, name="Bombarda")
        with translation.override("en"):
            self.assertEqual(own.label, "Bombarda")


class SeedInstrumentsTests(TestCase):
    def setUp(self):
        self.band = Association.objects.create(name="Banda Sintética", slug="banda-sintetica")
        self.other = Association.objects.create(name="Otra Banda", slug="otra-banda")

    def test_seeds_every_predefined_instrument_once(self):
        created = services.seed_default_instruments(self.band)
        self.assertEqual(created, len(catalog.INSTRUMENTS))
        self.assertEqual(services.seed_default_instruments(self.band), 0)
        self.assertEqual(Instrument.objects.filter(association=self.band).count(), len(catalog.INSTRUMENTS))
        self.assertFalse(Instrument.objects.filter(association=self.other).exists())
        dulzaina = Instrument.objects.get(association=self.band, code="dulzaina")
        self.assertEqual((dulzaina.name, dulzaina.name_ca, dulzaina.name_en), ("Dulzaina", "Dolçaina", "Dulzaina"))
        self.assertEqual(dulzaina.section.code, "woodwind")
        self.assertEqual(Instrument.objects.get(association=self.band, code="harp").section.code, "plucked_strings")
        self.assertEqual(Instrument.objects.get(association=self.band, code="piano").section.code, "struck_strings")

    def test_links_an_own_instrument_with_a_known_name_instead_of_duplicating_it(self):
        brass = Section.objects.get(code="brass")
        sax = Instrument.objects.create(association=self.band, name="Saxo alto")
        trumpet = Instrument.objects.create(association=self.band, name="trompeta", section=brass)
        member = Member.objects.create(association=self.band, first_name="Neus", last_name="Gil")
        MemberInstrument.objects.create(member=member, instrument=sax, is_primary=True)

        services.seed_default_instruments(self.band)

        sax.refresh_from_db()
        self.assertEqual((sax.name, sax.code, sax.name_en), ("Saxo alto", "alto_saxophone", "Alto saxophone"))
        self.assertEqual(sax.section.code, "woodwind")
        trumpet.refresh_from_db()
        self.assertEqual((trumpet.name, trumpet.code), ("trompeta", "trumpet"))
        self.assertEqual(Instrument.objects.filter(association=self.band, code="alto_saxophone").count(), 1)
        self.assertEqual(Instrument.objects.filter(association=self.band).count(), len(catalog.INSTRUMENTS))
        self.assertEqual(member.member_instruments.get().instrument, sax)

    def test_keeps_the_section_already_chosen_by_the_band(self):
        percussion = Section.objects.get(code="percussion")
        piano = Instrument.objects.create(association=self.band, name="Piano", section=percussion)
        services.seed_default_instruments(self.band)
        piano.refresh_from_db()
        self.assertEqual((piano.code, piano.section), ("piano", percussion))

    def test_command_seeds_one_or_every_association(self):
        out = StringIO()
        call_command("seed_instrument_catalog", "--association", "otra-banda", stdout=out)
        self.assertIn(f"otra-banda: {len(catalog.INSTRUMENTS)} instrumentos añadidos.", out.getvalue())
        self.assertFalse(Instrument.objects.filter(association=self.band).exists())
        out = StringIO()
        call_command("seed_instrument_catalog", stdout=out)
        self.assertIn("otra-banda: 0 instrumentos añadidos.", out.getvalue())
        self.assertIn(f"banda-sintetica: {len(catalog.INSTRUMENTS)} instrumentos añadidos.", out.getvalue())


class AdminCatalogTests(TestCase):
    def setUp(self):
        self.operator = get_user_model().objects.create_superuser(
            username="operacion@example.invalid", email="operacion@example.invalid", password="synthetic-password"
        )
        self.client = Client()
        self.client.force_login(self.operator)

    def test_creating_an_association_in_the_admin_seeds_its_instruments(self):
        response = self.client.post(
            "/admin/associations/association/add/",
            {
                "name": "Banda Nova",
                "slug": "banda-nova",
                "primary_color": "#1B4965",
                "secondary_color": "#F2C14E",
                "timezone": "Europe/Madrid",
                "visual_style": "escenario",
                "color_mode": "system",
            },
        )
        self.assertEqual(response.status_code, 302, getattr(response, "context", None) and response.context["adminform"].form.errors)
        band = Association.objects.get(slug="banda-nova")
        self.assertEqual(Instrument.objects.filter(association=band).count(), len(catalog.INSTRUMENTS))

    def test_sections_cannot_be_edited_in_the_admin(self):
        brass = Section.objects.get(code="brass")
        self.assertEqual(self.client.get("/admin/members/section/add/").status_code, 403)
        self.client.post(f"/admin/members/section/{brass.pk}/change/", {"code": "brass", "name": "Metal", "order": 1})
        brass.refresh_from_db()
        self.assertEqual(brass.name, "Viento metal")
        self.assertEqual(self.client.get("/admin/members/section/").status_code, 200)


class SectionApiTests(TestCase):
    def setUp(self):
        self.band = Association.objects.create(name="Banda Sintética", slug="banda-sintetica")
        self.other = Association.objects.create(name="Otra Banda", slug="otra-banda")
        self.account = get_user_model().objects.create_user(
            username="junta@example.invalid", email="junta@example.invalid", password="synthetic-password"
        )
        access = AssociationAccess.objects.create(association=self.band, account=self.account)
        AssociationRole.objects.create(access=access, role=AssociationRole.Role.ADMIN)
        self.client = APIClient()
        self.client.force_authenticate(self.account)

    def test_lists_the_common_sections_in_the_language_of_the_request(self):
        response = self.client.get(f"/api/v1/sections/?association_id={self.band.id}", HTTP_ACCEPT_LANGUAGE="ca")
        self.assertEqual(response.status_code, 200)
        results = response.json()["results"]
        self.assertEqual([item["code"] for item in results], SECTION_CODES)
        self.assertEqual(results[0]["name"], "Vent metall")

    def test_sections_cannot_be_created_or_changed_even_by_an_admin(self):
        url = f"/api/v1/sections/?association_id={self.band.id}"
        self.assertEqual(self.client.post(url, {"name": "Vent"}, format="json").status_code, 405)
        brass = Section.objects.get(code="brass")
        response = self.client.patch(
            f"/api/v1/sections/{brass.id}/?association_id={self.band.id}", {"name": "X"}, format="json"
        )
        self.assertEqual(response.status_code, 405)
        self.assertEqual(Section.objects.count(), len(SECTION_CODES))

    def test_listing_sections_still_requires_belonging_to_the_association(self):
        response = self.client.get(f"/api/v1/sections/?association_id={self.other.id}")
        self.assertEqual(response.status_code, 403)

    def test_instruments_are_listed_with_their_translated_name(self):
        services.seed_default_instruments(self.band)
        response = self.client.get(
            f"/api/v1/instruments/?association_id={self.band.id}&page_size=100", HTTP_ACCEPT_LANGUAGE="en"
        )
        self.assertEqual(response.status_code, 200)
        names = {item["code"]: item["name"] for item in response.json()["results"]}
        self.assertEqual(names["french_horn"], "French horn")

    def test_an_instrument_can_be_created_in_any_common_section(self):
        plucked = Section.objects.get(code="plucked_strings")
        response = self.client.post(
            f"/api/v1/instruments/?association_id={self.band.id}",
            {"name": "Timple", "section": plucked.id},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["code"], "")
        self.assertEqual(Instrument.objects.get(association=self.band, name="Timple").section, plucked)


class SectionMigrationTests(TransactionTestCase):
    """La migración 0006 fusiona las cuerdas por asociación del piloto en las comunes."""

    before = [("members", "0004_member_traceability_and_positions")]
    after = [("members", "0007_global_sections_finish")]

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_old_sections_are_merged_and_bands_get_the_predefined_instruments(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old_apps = executor.loader.project_state(self.before).apps
        OldSection = old_apps.get_model("members", "Section")
        OldInstrument = old_apps.get_model("members", "Instrument")
        OldMember = old_apps.get_model("members", "Member")
        OldMemberInstrument = old_apps.get_model("members", "MemberInstrument")

        # Las asociaciones no cambian en estas migraciones: se crean con el modelo actual.
        aumb = Association.objects.create(name="Banda A", slug="banda-a")
        alfa = Association.objects.create(name="Banda B", slug="banda-b")
        metal_a = OldSection.objects.create(association_id=aumb.pk, name="Metal")
        vent_a = OldSection.objects.create(association_id=aumb.pk, name="Vent")
        metall_b = OldSection.objects.create(association_id=alfa.pk, name="Metall")
        fusta_b = OldSection.objects.create(association_id=alfa.pk, name="Fusta")
        trumpet_a = OldInstrument.objects.create(association_id=aumb.pk, name="Trompeta", section=metal_a)
        # Mal clasificado en origen: el catálogo manda para los instrumentos conocidos.
        sax_a = OldInstrument.objects.create(association_id=aumb.pk, name="Saxo alto", section=metal_a)
        own_a = OldInstrument.objects.create(association_id=aumb.pk, name="Corneta de órdenes", section=vent_a)
        bombarda_b = OldInstrument.objects.create(association_id=alfa.pk, name="Bombarda", section=fusta_b)
        tuba_b = OldInstrument.objects.create(association_id=alfa.pk, name="Tuba", section=metall_b)
        member = OldMember.objects.create(association_id=aumb.pk, first_name="Pau", last_name="Climent")
        OldMemberInstrument.objects.create(member=member, instrument=trumpet_a, is_primary=True)

        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(self.after)
        new_apps = executor.loader.project_state(self.after).apps
        NewSection = new_apps.get_model("members", "Section")
        NewInstrument = new_apps.get_model("members", "Instrument")
        NewMemberInstrument = new_apps.get_model("members", "MemberInstrument")

        self.assertEqual(list(NewSection.objects.order_by("order").values_list("code", flat=True)), SECTION_CODES)

        def section_of(instrument):
            return NewInstrument.objects.get(pk=instrument.pk).section.code if NewInstrument.objects.get(pk=instrument.pk).section_id else None

        self.assertEqual(section_of(trumpet_a), "brass")
        self.assertEqual(section_of(sax_a), "woodwind")
        self.assertIsNone(section_of(own_a))
        self.assertEqual(section_of(bombarda_b), "woodwind")
        self.assertEqual(section_of(tuba_b), "brass")
        trumpet = NewInstrument.objects.get(pk=trumpet_a.pk)
        self.assertEqual((trumpet.code, trumpet.name_ca, trumpet.name_en), ("trumpet", "Trompeta", "Trumpet"))
        for band in (aumb, alfa):
            instruments = NewInstrument.objects.filter(association_id=band.pk)
            self.assertEqual(instruments.exclude(code="").count(), len(catalog.INSTRUMENTS))
            self.assertEqual(instruments.filter(code="trumpet").count(), 1)
        self.assertEqual(NewInstrument.objects.filter(association_id=aumb.pk, name="Corneta de órdenes").count(), 1)
        self.assertEqual(NewMemberInstrument.objects.get(member_id=member.pk).instrument_id, trumpet_a.pk)

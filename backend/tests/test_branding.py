from django.test import SimpleTestCase

from apps.associations.branding import (
    DARK_SURFACE,
    LIGHT_SURFACE,
    MIN_TEXT_CONTRAST,
    brand_tokens,
    contrast,
    ink_on,
    readable_on,
)
from apps.associations.models import Association


class ContrastTests(SimpleTestCase):
    def test_black_on_white_is_the_maximum(self):
        self.assertAlmostEqual(contrast("#000000", "#FFFFFF"), 21, places=1)

    def test_ink_follows_the_lightness_of_the_background(self):
        self.assertEqual(ink_on("#FFE600"), "#111214")
        self.assertEqual(ink_on("#7A1F2B"), "#FFFFFF")
        self.assertEqual(ink_on("#000000"), "#FFFFFF")


class ReadableBrandTextTests(SimpleTestCase):
    """Cualquier color de escudo se puede elegir; lo que se corrige es el texto."""

    EXTREMES = ["#FFE600", "#FFFFFF", "#000000", "#7A1F2B", "#1B4965", "#CAE9FF", "#00FF00"]

    def test_every_colour_reads_on_both_modes(self):
        for color in self.EXTREMES:
            for background in (LIGHT_SURFACE, DARK_SURFACE, "#FFFFFF", "#0F1012"):
                with self.subTest(color=color, background=background):
                    self.assertGreaterEqual(contrast(readable_on(color, background), background), MIN_TEXT_CONTRAST)

    def test_a_colour_that_already_reads_is_kept(self):
        self.assertEqual(readable_on("#7A1F2B", LIGHT_SURFACE), "#7A1F2B")


class BrandTokensTests(SimpleTestCase):
    def test_without_association_it_is_gesband_with_escenario(self):
        tokens = brand_tokens()
        self.assertEqual(tokens["style"], "escenario")
        self.assertEqual(tokens["mode"], "system")
        self.assertEqual(tokens["brand"], "#1B4965")

    def test_the_association_choice_travels_to_the_panel(self):
        association = Association(
            name="Banda", slug="banda", primary_color="#ffe600", secondary_color="#000000",
            visual_style=Association.VisualStyle.PARTITURA, color_mode=Association.ColorMode.DARK,
        )
        tokens = brand_tokens(association)
        self.assertEqual(tokens["style"], "partitura")
        self.assertEqual(tokens["mode"], "dark")
        self.assertEqual(tokens["brand"], "#FFE600")
        self.assertEqual(tokens["brand_ink"], "#111214")
        self.assertGreaterEqual(contrast(tokens["brand_text_light"], LIGHT_SURFACE), MIN_TEXT_CONTRAST)
        self.assertEqual(tokens["accent_ink"], "#FFFFFF")


class BrandEdgeTests(SimpleTestCase):
    """Bocairent es negro y oro: en oscuro, el cartel negro necesita un filo dorado."""

    def tokens(self, primary, secondary):
        return brand_tokens(Association(name="B", slug="b", primary_color=primary, secondary_color=secondary))

    def test_a_black_band_gets_a_golden_edge_only_in_dark_mode(self):
        tokens = self.tokens("#111111", "#C9A227")
        self.assertEqual(tokens["brand_edge_dark"], "#C9A227")
        self.assertEqual(tokens["brand_edge_light"], "transparent")

    def test_a_white_band_gets_an_edge_in_light_mode(self):
        tokens = self.tokens("#FFFFFF", "#C9A227")
        self.assertEqual(tokens["brand_edge_light"], "#C9A227")
        self.assertEqual(tokens["brand_edge_dark"], "transparent")

    def test_without_a_distinct_accent_the_edge_is_the_theme_line(self):
        tokens = self.tokens("#111111", "#000000")
        self.assertEqual(tokens["brand_edge_dark"], "#2C2F35")

    def test_a_coloured_band_needs_no_edge(self):
        tokens = self.tokens("#7A1F2B", "#C9A227")
        self.assertEqual(tokens["brand_edge_light"], "transparent")
        self.assertEqual(tokens["brand_edge_dark"], "transparent")

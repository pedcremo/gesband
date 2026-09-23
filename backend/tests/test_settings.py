import os
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from config.settings import env_flag


class EnvFlagTests(SimpleTestCase):
    """infra/.env y compose.yaml escriben `true`, no `1`."""

    def read(self, raw, default=False):
        environ = {} if raw is None else {"GESBAND_TEST_FLAG": raw}
        with mock.patch.dict(os.environ, environ, clear=True):
            return env_flag("GESBAND_TEST_FLAG", default)

    def test_accepts_the_usual_spellings_of_true(self):
        for raw in ["1", "true", "True", "TRUE", " true ", "yes", "on"]:
            with self.subTest(raw=raw):
                self.assertIs(self.read(raw), True)

    def test_accepts_the_usual_spellings_of_false(self):
        for raw in ["0", "false", "False", " no ", "off"]:
            with self.subTest(raw=raw):
                self.assertIs(self.read(raw, default=True), False)

    def test_missing_or_empty_falls_back_to_the_default(self):
        for raw in [None, "", "   "]:
            with self.subTest(raw=raw):
                self.assertIs(self.read(raw, default=True), True)
                self.assertIs(self.read(raw, default=False), False)

    def test_unrecognised_value_stops_the_boot_instead_of_reading_as_false(self):
        with self.assertRaises(ImproperlyConfigured) as caught:
            self.read("quizas", default=True)
        self.assertIn("GESBAND_TEST_FLAG", str(caught.exception))
        self.assertIn("quizas", str(caught.exception))

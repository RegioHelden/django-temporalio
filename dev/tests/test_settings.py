from unittest import TestCase

from django.conf import settings as django_settings
from django.test.utils import override_settings

from django_temporalio.conf import (
    SETTINGS_KEY,
    DEFAULTS,
    settings as temporalio_settings,
)


class SettingsTestCase(TestCase):
    """
    Test case for django_temporalio.conf.settings.
    """

    def test_default_settings(self):
        self.assertFalse(hasattr(django_settings, SETTINGS_KEY))
        self.assertEqual(temporalio_settings.URL, DEFAULTS["URL"])
        self.assertEqual(temporalio_settings.NAMESPACE, DEFAULTS["NAMESPACE"])
        self.assertEqual(temporalio_settings.WORKER_CONFIGS, DEFAULTS["WORKER_CONFIGS"])

    def test_user_settings(self):
        user_settings = {
            "URL": "http://temporal:7233",
            "NAMESPACE": "main",
            "WORKER_CONFIGS": {"main": "config"},
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            self.assertEqual(temporalio_settings.URL, user_settings["URL"])
            self.assertEqual(temporalio_settings.NAMESPACE, user_settings["NAMESPACE"])
            self.assertEqual(
                temporalio_settings.WORKER_CONFIGS, user_settings["WORKER_CONFIGS"]
            )

    def test_fallback_to_defaults(self):
        user_settings = {
            "NAMESPACE": "main",
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            self.assertEqual(temporalio_settings.URL, DEFAULTS["URL"])
            self.assertEqual(temporalio_settings.NAMESPACE, user_settings["NAMESPACE"])
            self.assertEqual(
                temporalio_settings.WORKER_CONFIGS, DEFAULTS["WORKER_CONFIGS"]
            )

    def test_invalid_setting(self):
        with self.assertRaises(AttributeError):
            temporalio_settings.SOMETHING

from unittest import TestCase

from django.conf import settings as django_settings
from django.test.utils import override_settings

from django_temporalio.conf import (
    DEFAULTS,
    SETTINGS_KEY,
)
from django_temporalio.conf import (
    settings as temporalio_settings,
)


class SettingsTestCase(TestCase):
    """
    Test case for django_temporalio.conf.settings.
    """

    def test_default_settings(self):
        self.assertFalse(hasattr(django_settings, SETTINGS_KEY))
        self.assertEqual(temporalio_settings.CLIENT_CONFIG, DEFAULTS["CLIENT_CONFIG"])
        self.assertEqual(temporalio_settings.WORKER_CONFIGS, DEFAULTS["WORKER_CONFIGS"])
        self.assertEqual(temporalio_settings.BASE_MODULE, DEFAULTS["BASE_MODULE"])

    def test_user_settings(self):
        user_settings = {
            "CLIENT_CONFIG": {"target_host": "temporal:7233"},
            "WORKER_CONFIGS": {"main": "config"},
            "BASE_MODULE": "example.temporalio",
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            self.assertEqual(
                temporalio_settings.CLIENT_CONFIG,
                user_settings["CLIENT_CONFIG"],
            )
            self.assertEqual(
                temporalio_settings.WORKER_CONFIGS,
                user_settings["WORKER_CONFIGS"],
            )
            self.assertEqual(
                temporalio_settings.BASE_MODULE,
                user_settings["BASE_MODULE"],
            )

    def test_fallback_to_defaults(self):
        user_settings = {
            "CLIENT_CONFIG": {"target_host": "temporal:7233"},
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            self.assertEqual(
                temporalio_settings.CLIENT_CONFIG,
                user_settings["CLIENT_CONFIG"],
            )
            self.assertEqual(
                temporalio_settings.WORKER_CONFIGS,
                DEFAULTS["WORKER_CONFIGS"],
            )
            self.assertEqual(temporalio_settings.BASE_MODULE, DEFAULTS["BASE_MODULE"])

    def test_invalid_setting(self):
        with self.assertRaises(AttributeError):
            temporalio_settings.SOMETHING  # noqa: B018

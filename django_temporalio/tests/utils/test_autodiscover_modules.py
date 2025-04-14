from importlib import import_module
from unittest import TestCase, mock

from django.test import override_settings

from django_temporalio.conf import SETTINGS_KEY, SettingIsNotSetError, settings
from django_temporalio.utils import autodiscover_modules


class AutodiscoverModulesTestCase(TestCase):
    """
    Test case for utils.autodiscover_modules.
    """

    @override_settings(**{SETTINGS_KEY: {"BASE_MODULE": "example.temporalio"}})
    @mock.patch("django_temporalio.utils.import_module", wraps=import_module)
    def test_autodiscover_modules(self, import_module_mock):
        autodiscover_modules("*workflows*")

        import_module_mock.assert_has_calls(
            [
                mock.call("example.temporalio"),
                mock.call("example.temporalio.workflows"),
                mock.call("example.temporalio.foo.foo_workflows"),
                mock.call("example.temporalio.foo.bar.workflows_bar"),
            ],
        )

    def test_autodiscover_modules_raises_exception(self):
        self.assertIsNone(settings.BASE_MODULE)
        with self.assertRaises(SettingIsNotSetError):
            autodiscover_modules("*workflows*")

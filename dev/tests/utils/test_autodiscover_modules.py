from importlib import import_module
from unittest import TestCase, mock

from django.test import override_settings

from django_temporalio.conf import settings, SETTINGS_KEY, SettingIsNotSetError
from django_temporalio.utils import autodiscover_modules


class AutodiscoverModulesTestCase(TestCase):
    """
    Test case for utils.autodiscover_modules.
    """

    @override_settings(**{SETTINGS_KEY: {"BASE_MODULE": "dev.temporalio"}})
    @mock.patch("django_temporalio.utils.import_module", wraps=import_module)
    def test_autodiscover_modules(self, import_module_mock):
        autodiscover_modules("*workflows*")

        import_module_mock.assert_has_calls(
            [
                mock.call("dev.temporalio"),
                mock.call("dev.temporalio.workflows"),
                mock.call("dev.temporalio.foo.foo_workflows"),
                mock.call("dev.temporalio.foo.bar.workflows_bar"),
            ]
        )

    def test_autodiscover_modules_raises_exception(self):
        self.assertIsNone(settings.BASE_MODULE)
        with self.assertRaises(SettingIsNotSetError):
            autodiscover_modules("*workflows*")

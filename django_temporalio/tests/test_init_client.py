from unittest import IsolatedAsyncioTestCase, mock

from django.test import override_settings

from django_temporalio.client import init_client
from django_temporalio.conf import SETTINGS_KEY


class InitClientTestCase(IsolatedAsyncioTestCase):
    """
    Test case for init_client function.
    """

    async def test_init_client(self):
        settings = {
            "CLIENT_CONFIG": {"foo": "bar"},
        }

        with (
            mock.patch("django_temporalio.client.Client.connect") as connect_mock,
            override_settings(**{SETTINGS_KEY: settings}),
        ):
            await init_client()

            connect_mock.assert_called_once_with(foo="bar")

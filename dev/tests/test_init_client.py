from unittest import IsolatedAsyncioTestCase, mock

from django_temporalio.client import init_client


class InitClientTestCase(IsolatedAsyncioTestCase):
    """
    Test case for init_client function.
    """

    async def test_init_client(self):
        with mock.patch("django_temporalio.client.Client.connect") as connect_mock:
            await init_client()

            connect_mock.assert_called_once_with(
                target_host="http://localhost:7233", namespace="default"
            )

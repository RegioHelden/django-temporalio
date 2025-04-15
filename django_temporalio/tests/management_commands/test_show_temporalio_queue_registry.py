from io import StringIO
from unittest import TestCase, mock

from django.core.management import call_command


class ShowTemporalioQueueRegistryTestCase(TestCase):
    """
    Test case for show_temporalio_queue_registry management command.
    """

    def test_command(self):
        registry = {
            "TEST_QUEUE_1": mock.Mock(
                workflows=[mock.Mock(__name__="TestWorkflow_1")],
                activities=[mock.Mock(__name__="test_activity_1")],
            ),
            "TEST_QUEUE_2": mock.Mock(
                workflows=[mock.Mock(__name__="TestWorkflow_2")],
                activities=[mock.Mock(__name__="test_activity_2")],
            ),
        }

        with (
            mock.patch(
                "django_temporalio.management.commands.show_temporalio_queue_registry.get_queue_registry",
                return_value=registry,
            ) as get_queue_registry_mock,
            StringIO() as stdout,
        ):
            call_command("show_temporalio_queue_registry", stdout=stdout)

            get_queue_registry_mock.assert_called_once_with()
            self.assertEqual(
                stdout.getvalue(),
                "TEST_QUEUE_1\n"
                "  workflows:\n"
                "    unittest.mock.TestWorkflow_1\n"
                "  activities:\n"
                "    unittest.mock.test_activity_1\n"
                "TEST_QUEUE_2\n"
                "  workflows:\n"
                "    unittest.mock.TestWorkflow_2\n"
                "  activities:\n"
                "    unittest.mock.test_activity_2\n",
            )

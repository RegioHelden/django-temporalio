from unittest import TestCase, mock

from django_temporalio.registry import QueueRegistryItem, get_queue_registry


class GetQueueRegistryTestCase(TestCase):
    @mock.patch("django_temporalio.registry.queue_activities.get_registry")
    @mock.patch("django_temporalio.registry.queue_workflows.get_registry")
    def test_get_queue_registry(
        self,
        get_workflows_registry_mock,
        get_activities_registry_mock,
    ):
        """
        Test that the queue registry is correctly built from the workflows and
        activities registries.
        """
        get_workflows_registry_mock.return_value = {
            "TEST_QUEUE_1": ["TestWorkflow_1"],
            "TEST_QUEUE_2": ["TestWorkflow_2"],
        }
        get_activities_registry_mock.return_value = {
            "TEST_QUEUE_1": ["activity_1"],
            "TEST_QUEUE_2": ["activity_2"],
        }

        registry = get_queue_registry()

        get_workflows_registry_mock.assert_called_once_with()
        get_activities_registry_mock.assert_called_once_with()
        self.assertEqual(
            registry,
            {
                "TEST_QUEUE_1": QueueRegistryItem(
                    workflows=["TestWorkflow_1"],
                    activities=["activity_1"],
                ),
                "TEST_QUEUE_2": QueueRegistryItem(
                    workflows=["TestWorkflow_2"],
                    activities=["activity_2"],
                ),
            },
        )

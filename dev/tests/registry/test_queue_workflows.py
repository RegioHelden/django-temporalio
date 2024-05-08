from unittest import TestCase, mock

from django.conf import settings
from django.utils.module_loading import autodiscover_modules
from temporalio import workflow

from django_temporalio.registry import queue_workflows


@workflow.defn
class TestWorkflow2:
    @workflow.run
    async def run(self):
        pass


class QueueWorkflowRegistryTestCase(TestCase):
    """
    Test case for queue_workflows registry.
    """

    def tearDown(self):
        queue_workflows.clear_registry()

    @mock.patch(
        "django_temporalio.registry.autodiscover_modules", wraps=autodiscover_modules
    )
    @mock.patch(
        "django_temporalio.registry.queue_workflows.register",
        wraps=queue_workflows.register,
    )
    def test_get_registry(self, mock_register, mock_autodiscover_modules):
        """
        Test that workflows defined in workflows.py are automatically registered when the registry is accessed.
        """
        registry = queue_workflows.get_registry()

        mock_register.assert_called_once_with(settings.TEST_TASK_QUEUES["MAIN"])
        mock_autodiscover_modules.assert_called_once_with("workflows")
        self.assertEquals(len(registry), 1)
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        workflows = registry[settings.TEST_TASK_QUEUES["MAIN"]]
        self.assertEqual(len(workflows), 1)
        self.assertEqual("TestWorkflow", workflows[0].__name__)

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register(self, _):
        """
        Test that a workflow can be registered.
        """
        queue_workflows.register(settings.TEST_TASK_QUEUES["MAIN"])(TestWorkflow2)

        registry = queue_workflows.get_registry()
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        self.assertIn(TestWorkflow2, registry[settings.TEST_TASK_QUEUES["MAIN"]])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_multiple_queues(self, _):
        """
        Test that a workflow can be registered with multiple queues.
        """
        queue_workflows.register(
            settings.TEST_TASK_QUEUES["MAIN"],
            settings.TEST_TASK_QUEUES["HIGH_PRIORITY"],
        )(TestWorkflow2)

        registry = queue_workflows.get_registry()
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        self.assertIn(settings.TEST_TASK_QUEUES["HIGH_PRIORITY"], registry)
        self.assertIn(TestWorkflow2, registry[settings.TEST_TASK_QUEUES["MAIN"]])
        self.assertIn(
            TestWorkflow2, registry[settings.TEST_TASK_QUEUES["HIGH_PRIORITY"]]
        )

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_registry_uniqueness(self, _):
        """
        Test that a workflow can only be registered once.
        """
        queue_workflows.register(settings.TEST_TASK_QUEUES["MAIN"])(TestWorkflow2)
        queue_workflows.register(settings.TEST_TASK_QUEUES["MAIN"])(TestWorkflow2)

        registry = queue_workflows.get_registry()
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        workflows = registry[settings.TEST_TASK_QUEUES["MAIN"]]
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0], TestWorkflow2)

    def test_register_no_queue(self):
        """
        Test that an exception is raised when a workflow is registered without a queue.
        """
        with self.assertRaises(ValueError):
            queue_workflows.register()

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_failure_on_missing_temporal_decorators(self, _):
        """
        Test that an exception is raised when a workflow class is not decorated with Temporal.io decorator.
        """
        with self.assertRaises(queue_workflows.MissingTemporalDecorator):

            @queue_workflows.register(settings.TEST_TASK_QUEUES["MAIN"])
            class TestWorkflow:
                pass

        self.assertDictEqual(queue_workflows.get_registry(), {})

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_clear_registry(self, _):
        """
        Test that the registry can be cleared.
        """
        queue_workflows.register(settings.TEST_TASK_QUEUES["MAIN"])(TestWorkflow2)

        queue_workflows.clear_registry()

        self.assertDictEqual(queue_workflows.get_registry(), {})

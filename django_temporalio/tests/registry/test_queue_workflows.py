from unittest import TestCase, mock

from django.test import override_settings
from temporalio import workflow

from django_temporalio.conf import SETTINGS_KEY
from django_temporalio.registry import autodiscover_modules, queue_workflows
from example.temporalio.queues import TestTaskQueues


@workflow.defn
class TestWorkflow:
    @workflow.run
    async def run(self):
        pass


class QueueWorkflowRegistryTestCase(TestCase):
    """
    Test case for queue_workflows registry.
    """

    def tearDown(self):
        queue_workflows.clear_registry()

    @override_settings(**{SETTINGS_KEY: {"BASE_MODULE": "example.temporalio"}})
    @mock.patch(
        "django_temporalio.registry.autodiscover_modules",
        wraps=autodiscover_modules,
    )
    @mock.patch(
        "django_temporalio.registry.queue_workflows.register",
        wraps=queue_workflows.register,
    )
    def test_get_registry(self, mock_register, mock_autodiscover_modules):
        """
        Test that workflows defined in workflows.py are automatically registered when
        the registry is accessed.
        """
        registry = queue_workflows.get_registry()

        mock_register.assert_called_once_with(TestTaskQueues.MAIN)
        mock_autodiscover_modules.assert_called_once_with("*workflows*")
        self.assertEqual(len(registry), 1)
        self.assertIn(TestTaskQueues.MAIN, registry)
        workflows = registry[TestTaskQueues.MAIN]
        self.assertEqual(len(workflows), 1)
        self.assertEqual(
            "example.temporalio.workflows.TestWorkflow",
            f"{workflows[0].__module__}.{workflows[0].__name__}",
        )

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register(self, _):
        """
        Test that a workflow can be registered.
        """
        queue_workflows.register(TestTaskQueues.MAIN)(TestWorkflow)

        registry = queue_workflows.get_registry()
        self.assertIn(TestTaskQueues.MAIN, registry)
        self.assertIn(TestWorkflow, registry[TestTaskQueues.MAIN])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_multiple_queues(self, _):
        """
        Test that a workflow can be registered with multiple queues.
        """
        queue_workflows.register(
            TestTaskQueues.MAIN,
            TestTaskQueues.HIGH_PRIORITY,
        )(TestWorkflow)

        registry = queue_workflows.get_registry()
        self.assertIn(TestTaskQueues.MAIN, registry)
        self.assertIn(TestTaskQueues.HIGH_PRIORITY, registry)
        self.assertIn(TestWorkflow, registry[TestTaskQueues.MAIN])
        self.assertIn(TestWorkflow, registry[TestTaskQueues.HIGH_PRIORITY])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_registry_uniqueness(self, _):
        """
        Test that a workflow can only be registered once.
        """
        queue_workflows.register(TestTaskQueues.MAIN)(TestWorkflow)
        queue_workflows.register(TestTaskQueues.MAIN)(TestWorkflow)

        registry = queue_workflows.get_registry()
        self.assertIn(TestTaskQueues.MAIN, registry)
        workflows = registry[TestTaskQueues.MAIN]
        self.assertEqual(len(workflows), 1)
        self.assertEqual(workflows[0], TestWorkflow)

    def test_register_no_queue(self):
        """
        Test that an exception is raised when a workflow is registered without a queue.
        """
        with self.assertRaises(ValueError):
            queue_workflows.register()

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_failure_on_missing_temporal_decorators(self, _):
        """
        Test that an exception is raised when a workflow class is not decorated with
        Temporal.io decorator.
        """
        with self.assertRaises(queue_workflows.MissingTemporalDecoratorError):

            @queue_workflows.register(TestTaskQueues.MAIN)
            class TestWorkflow:
                pass

        self.assertDictEqual(queue_workflows.get_registry(), {})

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_clear_registry(self, _):
        """
        Test that the registry can be cleared.
        """
        queue_workflows.register(TestTaskQueues.MAIN)(TestWorkflow)

        queue_workflows.clear_registry()

        self.assertDictEqual(queue_workflows.get_registry(), {})

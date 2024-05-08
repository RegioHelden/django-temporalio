from unittest import TestCase, mock

from django.utils.module_loading import autodiscover_modules
from temporalio import activity

from dev.temporalio import TestTaskQueues
from django_temporalio.registry import queue_activities


@activity.defn
def test_activity():
    pass


class QueueActivityRegistryTestCase(TestCase):
    """
    Test case for queue_activities registry.
    """

    def tearDown(self):
        queue_activities.clear_registry()

    @mock.patch(
        "django_temporalio.registry.autodiscover_modules", wraps=autodiscover_modules
    )
    @mock.patch(
        "django_temporalio.registry.queue_activities.register",
        wraps=queue_activities.register,
    )
    def test_get_registry(self, mock_register, mock_autodiscover_modules):
        """
        Test that activities defined in activities.py are automatically registered when the registry is accessed.
        """
        registry = queue_activities.get_registry()

        mock_register.assert_called_once_with(TestTaskQueues.MAIN)
        mock_autodiscover_modules.assert_called_once_with("activities")
        self.assertEqual(len(registry), 1)
        self.assertIn(TestTaskQueues.MAIN, registry)
        activities = registry[TestTaskQueues.MAIN]
        self.assertEqual(len(activities), 1)
        self.assertEqual(
            f"{activities[0].__module__}.{activities[0].__name__}",
            "dev.activities.test_activity",
        )

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register(self, _):
        """
        Test that an activity can be registered.
        """
        queue_activities.register(TestTaskQueues.MAIN)(test_activity)

        registry = queue_activities.get_registry()
        self.assertIn(TestTaskQueues.MAIN, registry)
        self.assertIn(test_activity, registry[TestTaskQueues.MAIN])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_multiple_queues(self, _):
        """
        Test that an activity can be registered with multiple queues.
        """
        queue_activities.register(
            TestTaskQueues.MAIN,
            TestTaskQueues.HIGH_PRIORITY,
        )(test_activity)

        registry = queue_activities.get_registry()
        self.assertIn(TestTaskQueues.MAIN, registry)
        self.assertIn(TestTaskQueues.HIGH_PRIORITY, registry)
        self.assertIn(test_activity, registry[TestTaskQueues.MAIN])
        self.assertIn(test_activity, registry[TestTaskQueues.HIGH_PRIORITY])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_registry_uniqueness(self, _):
        """
        Test that an activity can only be registered once.
        """
        queue_activities.register(TestTaskQueues.MAIN)(test_activity)
        queue_activities.register(TestTaskQueues.MAIN)(test_activity)

        registry = queue_activities.get_registry()
        self.assertIn(TestTaskQueues.MAIN, registry)
        activities = registry[TestTaskQueues.MAIN]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], test_activity)

    def test_register_no_queue(self):
        """
        Test that an exception is raised when an activity is registered without a queue.
        """
        with self.assertRaises(ValueError):
            queue_activities.register()

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_failure_on_missing_temporal_decorators(self, _):
        """
        Test that an exception is raised when an activity function is not decorated with Temporal.io decorator.
        """
        with self.assertRaises(queue_activities.MissingTemporalDecorator):

            @queue_activities.register(TestTaskQueues.MAIN)
            def test_activity():
                pass

        self.assertDictEqual(queue_activities.get_registry(), {})

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_clear_registry(self, _):
        """
        Test that the registry can be cleared.
        """
        queue_activities.register(TestTaskQueues.MAIN)(test_activity)

        queue_activities.clear_registry()

        self.assertDictEqual(queue_activities.get_registry(), {})

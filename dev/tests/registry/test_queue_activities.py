from unittest import TestCase, mock

from django.utils.module_loading import autodiscover_modules
from temporalio import activity

from django_temporalio.registry import queue_activities
from django.conf import settings

@activity.defn
def test_activity_2():
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

        mock_register.assert_called_once_with(settings.TEST_TASK_QUEUES["MAIN"])
        mock_autodiscover_modules.assert_called_once_with("activities")
        self.assertEquals(len(registry), 1)
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        activities = registry[settings.TEST_TASK_QUEUES["MAIN"]]
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
        queue_activities.register(settings.TEST_TASK_QUEUES["MAIN"])(test_activity_2)

        registry = queue_activities.get_registry()
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        self.assertIn(test_activity_2, registry[settings.TEST_TASK_QUEUES["MAIN"]])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register_multiple_queues(self, _):
        """
        Test that an activity can be registered with multiple queues.
        """
        queue_activities.register(
            settings.TEST_TASK_QUEUES["MAIN"],
            settings.TEST_TASK_QUEUES["HIGH_PRIORITY"],
        )(test_activity_2)

        registry = queue_activities.get_registry()
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        self.assertIn(settings.TEST_TASK_QUEUES["HIGH_PRIORITY"], registry)
        self.assertIn(test_activity_2, registry[settings.TEST_TASK_QUEUES["MAIN"]])
        self.assertIn(test_activity_2, registry[settings.TEST_TASK_QUEUES["HIGH_PRIORITY"]])

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_registry_uniqueness(self, _):
        """
        Test that an activity can only be registered once.
        """
        queue_activities.register(settings.TEST_TASK_QUEUES["MAIN"])(test_activity_2)
        queue_activities.register(settings.TEST_TASK_QUEUES["MAIN"])(test_activity_2)

        registry = queue_activities.get_registry()
        self.assertIn(settings.TEST_TASK_QUEUES["MAIN"], registry)
        activities = registry[settings.TEST_TASK_QUEUES["MAIN"]]
        self.assertEqual(len(activities), 1)
        self.assertEqual(activities[0], test_activity_2)

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

            @queue_activities.register(settings.TEST_TASK_QUEUES["MAIN"])
            def test_activity():
                pass

        self.assertDictEqual(queue_activities.get_registry(), {})

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_clear_registry(self, _):
        """
        Test that the registry can be cleared.
        """
        queue_activities.register(settings.TEST_TASK_QUEUES["MAIN"])(test_activity_2)

        queue_activities.clear_registry()

        self.assertDictEqual(queue_activities.get_registry(), {})

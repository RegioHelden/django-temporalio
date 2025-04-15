from unittest import TestCase, mock

from django.test import override_settings
from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleCalendarSpec,
    ScheduleRange,
    ScheduleSpec,
)

from django_temporalio.conf import SETTINGS_KEY
from django_temporalio.registry import schedules
from django_temporalio.utils import autodiscover_modules
from example.temporalio.queues import TestTaskQueues


class ScheduleRegistryTestCase(TestCase):
    """
    Test case for schedules registry.
    """

    @classmethod
    def setUpClass(cls):
        cls.schedule_id = "test-schedule"
        cls.schedule = Schedule(
            action=ScheduleActionStartWorkflow(
                "TestWorkflow",
                id="do-something-every-hour",
                task_queue=TestTaskQueues.MAIN,
            ),
            spec=ScheduleSpec(
                calendars=[
                    ScheduleCalendarSpec(
                        hour=[ScheduleRange(0, 23)],
                        minute=[ScheduleRange(0)],
                        second=[ScheduleRange(0)],
                    ),
                ],
            ),
        )

    def tearDown(self):
        schedules.clear_registry()

    @override_settings(**{SETTINGS_KEY: {"BASE_MODULE": "example.temporalio"}})
    @mock.patch(
        "django_temporalio.registry.autodiscover_modules",
        wraps=autodiscover_modules,
    )
    @mock.patch.object(schedules, "register", wraps=schedules.register)
    def test_get_registry(self, mock_register, mock_autodiscover_modules):
        """
        Test that schedules defined in schedules.py are automatically registered when
        the registry is accessed.
        """
        registry = schedules.get_registry()

        mock_register.assert_called_once()
        mock_autodiscover_modules.assert_called_once_with("*schedules*")
        self.assertEqual(len(registry), 1)
        self.assertIn("do-cool-stuff-every-hour", registry)

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_register(self, _):
        """
        Test that a schedule can be registered.
        """
        schedules.register(self.schedule_id, self.schedule)

        registry = schedules.get_registry()
        self.assertIn(self.schedule_id, registry)
        self.assertEqual(registry[self.schedule_id], self.schedule)

    def test_already_registered_exception(self):
        """
        Test that an exception is raised when attempting to register a schedule with
        the same ID.
        """
        schedules.register(self.schedule_id, self.schedule)

        with self.assertRaises(schedules.AlreadyRegisteredError):
            schedules.register(self.schedule_id, self.schedule)

    @mock.patch("django_temporalio.registry.autodiscover_modules")
    def test_clear_registry(self, _):
        """
        Test that the registry can be cleared.
        """
        schedules.register(self.schedule_id, self.schedule)

        schedules.clear_registry()

        self.assertEqual(len(schedules.get_registry()), 0)

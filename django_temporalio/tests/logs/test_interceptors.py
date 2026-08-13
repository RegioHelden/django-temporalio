from unittest import IsolatedAsyncioTestCase, TestCase, mock

from django.test import override_settings
from temporalio.common import RetryPolicy
from temporalio.exceptions import CancelledError
from temporalio.testing import ActivityEnvironment

from django_temporalio.conf import SETTINGS_KEY
from django_temporalio.logs.interceptors import (
    ActivityFailureLoggingInterceptor,
    get_interceptors,
)
from django_temporalio.tests.logs.factories import make_info

LOGGER_NAME = "django_temporalio.activity"


class ShouldLogTestCase(TestCase):
    """
    Test case for the ActivityFailureLoggingInterceptor.should_log wiring;
    the decision logic itself is covered in test_throttling.
    """

    def setUp(self):
        self.interceptor = ActivityFailureLoggingInterceptor()
        self.err = ValueError("boom")

    def test_schedule_comes_from_settings(self):
        user_settings = {
            "ACTIVITY_FAILURE_LOG_ATTEMPTS": (5,),
            "ACTIVITY_FAILURE_LOG_EVERY": 100,
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            self.assertTrue(self.interceptor.should_log(make_info(5), self.err))
            self.assertTrue(self.interceptor.should_log(make_info(200), self.err))
            self.assertFalse(self.interceptor.should_log(make_info(1), self.err))

    def test_retry_policy_comes_from_info(self):
        retry_policy = RetryPolicy(maximum_attempts=3)

        self.assertFalse(
            self.interceptor.should_log(make_info(1, retry_policy), self.err),
        )
        self.assertTrue(
            self.interceptor.should_log(make_info(3, retry_policy), self.err),
        )


class ExecuteActivityTestCase(IsolatedAsyncioTestCase):
    """
    Test case for the inbound interceptor created by
    ActivityFailureLoggingInterceptor.intercept_activity.
    """

    def setUp(self):
        self.next = mock.Mock(execute_activity=mock.AsyncMock())
        self.interceptor = ActivityFailureLoggingInterceptor().intercept_activity(
            self.next,
        )
        self.input = mock.Mock()
        # provides the activity context the interceptor and the SDK
        # LoggerAdapter read the activity info from
        self.env = ActivityEnvironment()
        self.env.info = make_info(attempt=1)

    async def execute_activity(self):
        return await self.env.run(self.interceptor.execute_activity, self.input)

    async def test_result_is_passed_through(self):
        self.next.execute_activity.return_value = "result"

        result = await self.execute_activity()

        self.assertEqual(result, "result")
        self.next.execute_activity.assert_awaited_once_with(self.input)

    async def test_failure_is_logged_and_reraised(self):
        self.next.execute_activity.side_effect = ValueError("boom")

        with (
            self.assertLogs(LOGGER_NAME, level="ERROR") as logs,
            self.assertRaises(ValueError),
        ):
            await self.execute_activity()

        self.assertIn("Activity my_activity failed", logs.output[0])
        self.assertIn("attempt 1", logs.output[0])
        self.assertIn("ValueError: boom", logs.output[0])
        self.assertEqual(
            logs.records[0].temporal_activity,
            {
                "activity_id": "activity-id",
                "activity_type": "my_activity",
                "attempt": 1,
                "namespace": "default",
                "task_queue": "TEST_QUEUE",
                "workflow_id": "workflow-id",
                "workflow_run_id": "run-id",
                "workflow_type": "MyWorkflow",
            },
        )

    async def test_throttled_failure_is_not_logged(self):
        self.env.info = make_info(attempt=2)
        self.next.execute_activity.side_effect = ValueError("boom")

        with self.assertNoLogs(LOGGER_NAME), self.assertRaises(ValueError):
            await self.execute_activity()

    async def test_cancellation_is_not_logged(self):
        self.next.execute_activity.side_effect = CancelledError("cancelled")

        with self.assertNoLogs(LOGGER_NAME), self.assertRaises(CancelledError):
            await self.execute_activity()


class GetInterceptorsTestCase(TestCase):
    INTERCEPTORS = (
        "django_temporalio.logs.interceptors.ActivityFailureLoggingInterceptor",
    )

    def test_no_interceptors_by_default(self):
        self.assertEqual(get_interceptors(), [])

    def test_interceptors_from_settings(self):
        user_settings = {"INTERCEPTORS": self.INTERCEPTORS}
        with override_settings(**{SETTINGS_KEY: user_settings}):
            interceptors = get_interceptors()

        self.assertEqual(len(interceptors), 1)
        self.assertIsInstance(interceptors[0], ActivityFailureLoggingInterceptor)

    def test_extra_interceptors_are_appended(self):
        extra = mock.Mock()

        user_settings = {"INTERCEPTORS": self.INTERCEPTORS}
        with override_settings(**{SETTINGS_KEY: user_settings}):
            interceptors = get_interceptors([extra])

        self.assertEqual(len(interceptors), 2)
        self.assertIsInstance(interceptors[0], ActivityFailureLoggingInterceptor)
        self.assertIs(interceptors[1], extra)

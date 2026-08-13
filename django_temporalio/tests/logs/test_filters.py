from unittest import TestCase, mock

from django.test import override_settings
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from django_temporalio.conf import SETTINGS_KEY
from django_temporalio.logs.filters import ActivityFailureThrottleFilter
from django_temporalio.tests.logs.factories import make_failure_record, make_record


class ActivityFailureThrottleFilterTestCase(TestCase):
    """
    Test case for the ActivityFailureThrottleFilter record handling and wiring;
    the decision logic itself is covered in test_throttling.
    """

    def setUp(self):
        self.filter = ActivityFailureThrottleFilter()

    def test_custom_schedule(self):
        throttle = ActivityFailureThrottleFilter(attempts=(5,), every=100)

        self.assertTrue(throttle.filter(make_failure_record(5)))
        self.assertTrue(throttle.filter(make_failure_record(200)))
        self.assertFalse(throttle.filter(make_failure_record(1)))
        self.assertFalse(throttle.filter(make_failure_record(150)))

    def test_schedule_defaults_to_settings(self):
        user_settings = {
            "ACTIVITY_FAILURE_LOG_ATTEMPTS": (5,),
            "ACTIVITY_FAILURE_LOG_EVERY": 100,
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            throttle = ActivityFailureThrottleFilter()

        self.assertTrue(throttle.filter(make_failure_record(5)))
        self.assertTrue(throttle.filter(make_failure_record(200)))
        self.assertFalse(throttle.filter(make_failure_record(1)))
        self.assertFalse(throttle.filter(make_failure_record(150)))

    def test_kwargs_override_settings(self):
        user_settings = {"ACTIVITY_FAILURE_LOG_ATTEMPTS": (5,)}
        with override_settings(**{SETTINGS_KEY: user_settings}):
            throttle = ActivityFailureThrottleFilter(attempts=(7,))

        self.assertTrue(throttle.filter(make_failure_record(7)))
        self.assertFalse(throttle.filter(make_failure_record(5)))

    def test_every_disabled(self):
        throttle = ActivityFailureThrottleFilter(every=0)

        self.assertTrue(throttle.filter(make_failure_record(10)))
        self.assertFalse(throttle.filter(make_failure_record(2000)))

    def test_retry_policy_comes_from_the_activity_context(self):
        info = mock.Mock(retry_policy=RetryPolicy(maximum_attempts=3))
        with mock.patch(
            "django_temporalio.logs.filters.activity.info",
            return_value=info,
        ):
            self.assertFalse(self.filter.filter(make_failure_record(1)))
            self.assertFalse(self.filter.filter(make_failure_record(2)))
            self.assertTrue(self.filter.filter(make_failure_record(3)))

    def test_error_comes_from_exc_info(self):
        # attempt 2 is off the schedule, only the non-retryable error read
        # from the record's exc_info makes it pass
        record = make_failure_record(
            2,
            err=ApplicationError("boom", non_retryable=True),
        )

        self.assertTrue(self.filter.filter(record))

    def test_outside_activity_context_follows_the_schedule(self):
        # activity.info() raises outside an activity, e.g. when the record is
        # processed behind a QueueHandler - the attempt schedule still applies
        self.assertTrue(self.filter.filter(make_failure_record(1)))
        self.assertFalse(self.filter.filter(make_failure_record(2)))

    def test_non_temporal_record_passes_through(self):
        self.assertTrue(self.filter.filter(make_record()))

    def test_other_temporal_error_passes_through(self):
        record = make_record({"__temporal_error_identifier": "WorkflowTaskFailure"})

        self.assertTrue(self.filter.filter(record))

    def test_record_without_activity_details_passes_through(self):
        record = make_record({"__temporal_error_identifier": "ActivityFailure"})

        self.assertTrue(self.filter.filter(record))

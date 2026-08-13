from unittest import TestCase

from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError, ApplicationErrorCategory

from django_temporalio.logs.throttling import (
    error_type,
    is_final_attempt,
    should_log_failure,
)


class ErrorTypeTestCase(TestCase):
    def test_plain_exception_uses_the_class_name(self):
        self.assertEqual(error_type(ValueError("boom")), "ValueError")

    def test_application_error_uses_its_explicit_type(self):
        self.assertEqual(
            error_type(ApplicationError("boom", type="IntegrityError")),
            "IntegrityError",
        )

    def test_application_error_without_type_uses_the_class_name(self):
        self.assertEqual(error_type(ApplicationError("boom")), "ApplicationError")

    def test_no_error(self):
        self.assertIsNone(error_type(None))


class IsFinalAttemptTestCase(TestCase):
    def test_non_retryable_error(self):
        err = ApplicationError("boom", non_retryable=True)

        self.assertTrue(is_final_attempt(1, err, None))

    def test_unknown_retry_policy(self):
        self.assertFalse(is_final_attempt(1000, ValueError("boom"), None))

    def test_non_retryable_error_type(self):
        retry_policy = RetryPolicy(non_retryable_error_types=["ValueError"])

        self.assertTrue(is_final_attempt(1, ValueError("boom"), retry_policy))
        self.assertFalse(is_final_attempt(1, TypeError("boom"), retry_policy))
        # an ApplicationError matches via its explicit type, not its class name
        custom_type_err = ApplicationError("boom", type="ValueError")
        self.assertTrue(is_final_attempt(1, custom_type_err, retry_policy))

    def test_attempts_exhausted(self):
        retry_policy = RetryPolicy(maximum_attempts=3)

        self.assertFalse(is_final_attempt(2, ValueError("boom"), retry_policy))
        self.assertTrue(is_final_attempt(3, ValueError("boom"), retry_policy))

    def test_unlimited_attempts(self):
        retry_policy = RetryPolicy(maximum_attempts=0)

        self.assertFalse(is_final_attempt(1000, ValueError("boom"), retry_policy))


class ShouldLogFailureTestCase(TestCase):
    ATTEMPTS = (1, 10, 100, 1000)
    EVERY = 1000

    def should_log(self, attempt, err=None, retry_policy=None, every=EVERY):
        return should_log_failure(attempt, err, retry_policy, self.ATTEMPTS, every)

    def test_schedule(self):
        expectations = [
            (1, True),
            (2, False),
            (10, True),
            (11, False),
            (100, True),
            (999, False),
            (1000, True),
            (2000, True),
            (2001, False),
        ]
        for attempt, expected in expectations:
            with self.subTest(attempt=attempt):
                self.assertEqual(self.should_log(attempt), expected)

    def test_every_disabled(self):
        self.assertTrue(self.should_log(10, every=0))
        self.assertFalse(self.should_log(2000, every=0))

    def test_limited_retries_log_only_the_final_attempt(self):
        retry_policy = RetryPolicy(maximum_attempts=3)

        # attempt 1 is on the schedule but will be retried
        self.assertFalse(self.should_log(1, ValueError("boom"), retry_policy))
        self.assertFalse(self.should_log(2, ValueError("boom"), retry_policy))
        self.assertTrue(self.should_log(3, ValueError("boom"), retry_policy))

    def test_non_retryable_error_logs_immediately(self):
        err = ApplicationError("boom", non_retryable=True)

        # attempt 2 is off the schedule and below maximum_attempts
        self.assertTrue(self.should_log(2, err, RetryPolicy(maximum_attempts=5)))

    def test_benign_error_never_logs(self):
        benign = ApplicationError("benign", category=ApplicationErrorCategory.BENIGN)

        self.assertFalse(self.should_log(1, benign))
        self.assertTrue(self.should_log(1, ApplicationError("regular")))

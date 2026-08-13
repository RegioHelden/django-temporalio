import logging

from temporalio import activity
from temporalio.common import RetryPolicy

from django_temporalio.conf import settings
from django_temporalio.logs.throttling import should_log_failure


class ActivityFailureThrottleFilter(logging.Filter):
    """
    Throttles the per-attempt "Completing activity as failed" records the
    temporalio SDK emits, following the rules of
    `throttling.should_log_failure`. The `attempts`/`every` kwargs default to
    the ACTIVITY_FAILURE_LOG_ATTEMPTS / ACTIVITY_FAILURE_LOG_EVERY settings
    (`every=0` disables). Records that are not activity failures pass through
    untouched.
    """

    def __init__(
        self,
        name: str = "",
        attempts: tuple[int, ...] | None = None,
        every: int | None = None,
    ):
        super().__init__(name)
        # `is None` checks, not `or`: () and 0 are meaningful (disable) values
        self.attempts = (
            settings.ACTIVITY_FAILURE_LOG_ATTEMPTS if attempts is None else attempts
        )
        self.every = settings.ACTIVITY_FAILURE_LOG_EVERY if every is None else every

    def filter(self, record: logging.LogRecord) -> bool:
        # the marker the SDK puts on its activity-failure records
        if getattr(record, "__temporal_error_identifier", None) != "ActivityFailure":
            return True

        attempt = getattr(record, "temporal_activity", {}).get("attempt")
        if attempt is None:
            return True

        err = record.exc_info[1] if record.exc_info else None
        return should_log_failure(
            attempt,
            err,
            self._current_retry_policy(),
            self.attempts,
            self.every,
        )

    @staticmethod
    def _current_retry_policy() -> RetryPolicy | None:
        # the record doesn't carry the retry policy, but the SDK emits the
        # record from inside the activity context; records processed elsewhere
        # (e.g. behind a QueueHandler) fall back to the attempt schedule
        try:
            return activity.info().retry_policy
        except RuntimeError:
            return None

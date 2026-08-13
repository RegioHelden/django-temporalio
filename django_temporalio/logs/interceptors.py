from __future__ import annotations

import logging
from collections.abc import Iterable

from django.utils.module_loading import import_string
from temporalio import activity
from temporalio.exceptions import CancelledError
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
)

from django_temporalio.conf import settings
from django_temporalio.logs.throttling import should_log_failure

# the SDK adapter attaches the activity details from the context as the
# `temporal_activity` extra of every record
# https://python.temporal.io/temporalio.activity.LoggerAdapter.html
logger = activity.LoggerAdapter(logging.getLogger("django_temporalio.activity"), None)
# the message already carries the essentials
logger.activity_info_on_message = False


class _ActivityFailureLoggingInterceptor(ActivityInboundInterceptor):
    """
    Wraps activity execution to log failures, delegating the decisions to the
    `root` ActivityFailureLoggingInterceptor. Exceptions are always re-raised.
    """

    def __init__(
        self,
        next_interceptor: ActivityInboundInterceptor,
        root: ActivityFailureLoggingInterceptor,
    ):
        super().__init__(next_interceptor)
        self.root = root

    async def execute_activity(self, activity_input: ExecuteActivityInput):
        try:
            return await self.next.execute_activity(activity_input)
        except CancelledError:
            raise
        except Exception as err:
            info = activity.info()
            if self.root.should_log(info, err):
                self.root.log_failure(info, err)
            raise


class ActivityFailureLoggingInterceptor(Interceptor):
    """
    Logs activity failures at ERROR level to the `django_temporalio.activity`
    logger - the SDK catches every activity exception to hand it to the
    server for retry and only logs a WARNING, so failures never reach error
    tracking otherwise.

    Throttled per `throttling.should_log_failure`; cancellations and benign
    errors are never logged. To customize, subclass and override
    `should_log`/`log_failure`, then point the INTERCEPTORS setting at it.
    """

    def intercept_activity(
        self,
        next: ActivityInboundInterceptor,  # noqa: A002 - base class signature
    ) -> ActivityInboundInterceptor:
        return _ActivityFailureLoggingInterceptor(next, self)

    def should_log(self, info: activity.Info, err: Exception) -> bool:
        return should_log_failure(
            info.attempt,
            err,
            info.retry_policy,
            settings.ACTIVITY_FAILURE_LOG_ATTEMPTS,
            settings.ACTIVITY_FAILURE_LOG_EVERY,
        )

    def log_failure(self, info: activity.Info, err: Exception) -> None:
        logger.error(
            "Activity %s failed (attempt %d, workflow %s, workflow_id %s)",
            info.activity_type,
            info.attempt,
            info.workflow_type,
            info.workflow_id,
            exc_info=err,
        )


def get_interceptors(extra: Iterable[Interceptor] = ()) -> list[Interceptor]:
    """
    Instantiate the interceptors declared in the INTERCEPTORS setting (import
    strings), followed by any extra interceptors, e.g. from a worker config.
    """
    return [*(import_string(path)() for path in settings.INTERCEPTORS), *extra]

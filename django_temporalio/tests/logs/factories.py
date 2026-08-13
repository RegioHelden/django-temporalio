import dataclasses
import logging
import sys

from temporalio.testing import ActivityEnvironment


def make_info(attempt=1, retry_policy=None):
    # a real Info, not a Mock, so the SDK LoggerAdapter can derive
    # its logger details from it
    return dataclasses.replace(
        ActivityEnvironment().info,
        attempt=attempt,
        retry_policy=retry_policy,
        activity_id="activity-id",
        activity_type="my_activity",
        task_queue="TEST_QUEUE",
        workflow_id="workflow-id",
        workflow_run_id="run-id",
        workflow_type="MyWorkflow",
    )


def make_record(extra=None, err=None):
    exc_info = None
    if err is not None:
        try:
            raise err
        except type(err):
            exc_info = sys.exc_info()

    return logging.getLogger("temporalio.activity").makeRecord(
        name="temporalio.activity",
        level=logging.WARNING,
        fn=__file__,
        lno=1,
        msg="Completing activity as failed",
        args=None,
        exc_info=exc_info,
        extra=extra,
    )


def make_failure_record(attempt, err=None):
    return make_record(
        {
            "__temporal_error_identifier": "ActivityFailure",
            "temporal_activity": {"attempt": attempt},
        },
        err=err,
    )

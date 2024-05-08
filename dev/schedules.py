# this file is needed for testing purposes only

from django.conf import settings
from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleCalendarSpec,
    ScheduleRange,
    ScheduleSpec,
)

from django_temporalio.registry import schedules

schedules.register(
    "do-cool-stuff-every-hour",
    Schedule(
        action=ScheduleActionStartWorkflow(
            "TestWorkflow",
            id="do-cool-stuff-every-hour",
            task_queue=settings.TEST_TASK_QUEUES["MAIN"],
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
    ),
)

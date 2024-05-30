from temporalio.client import (
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleCalendarSpec,
    ScheduleRange,
    ScheduleSpec,
)

from dev.temporalio.queues import TestTaskQueues
from django_temporalio.registry import schedules

schedules.register(
    "do-cool-stuff-every-hour",
    Schedule(
        action=ScheduleActionStartWorkflow(
            "TestWorkflow",
            id="do-cool-stuff-every-hour",
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
    ),
)

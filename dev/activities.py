from temporalio import activity

from dev.temporalio import TestTaskQueues
from django_temporalio.registry import queue_activities


@queue_activities.register(TestTaskQueues.MAIN)
@activity.defn
async def test_activity():
    pass

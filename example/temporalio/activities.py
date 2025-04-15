from temporalio import activity

from django_temporalio.registry import queue_activities
from example.temporalio.queues import TestTaskQueues


@queue_activities.register(TestTaskQueues.MAIN)
@activity.defn
async def test_activity():
    pass

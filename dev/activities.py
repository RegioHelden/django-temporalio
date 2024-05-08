# this file is needed for testing purposes only

from django.conf import settings
from temporalio import activity

from django_temporalio.registry import queue_activities


@queue_activities.register(settings.TEST_TASK_QUEUES["MAIN"])
@activity.defn
async def test_activity():
    pass

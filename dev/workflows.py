# this file is needed for testing purposes only

from django.conf import settings
from temporalio import workflow

from django_temporalio.registry import queue_workflows


@queue_workflows.register(settings.TEST_TASK_QUEUES["MAIN"])
@workflow.defn
class TestWorkflow:
    @workflow.run
    async def run(self):
        pass

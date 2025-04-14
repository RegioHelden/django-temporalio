from temporalio import workflow

from django_temporalio.registry import queue_workflows
from example.temporalio.queues import TestTaskQueues


@queue_workflows.register(TestTaskQueues.MAIN)
@workflow.defn
class TestWorkflow:
    @workflow.run
    async def run(self):
        pass

from temporalio import workflow

from dev.temporalio import TestTaskQueues
from django_temporalio.registry import queue_workflows


@queue_workflows.register(TestTaskQueues.MAIN)
@workflow.defn
class TestWorkflow:
    @workflow.run
    async def run(self):
        pass

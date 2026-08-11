from asgiref.sync import async_to_sync
from django.core.management import BaseCommand
from temporalio.worker import Worker

from django_temporalio.client import init_client
from django_temporalio.registry import get_queue_registry


class Command(BaseCommand):
    help = "Validates Temporal.io workers."

    @async_to_sync
    async def handle(self, **kwargs):
        self.stdout.write("👷 Validating workers...")
        client = await init_client()
        for queue_name, item in get_queue_registry().items():
            Worker(
                client,
                task_queue=queue_name,
                workflows=item.workflows,
                activities=item.activities,
            )
        self.stdout.write(self.style.SUCCESS("🥳 All workers validated!"))

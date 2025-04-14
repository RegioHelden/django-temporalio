import asyncio
import contextlib
import sys

from django.core.management import BaseCommand
from temporalio.worker import Worker

from django_temporalio.client import init_client
from django_temporalio.conf import settings
from django_temporalio.registry import get_queue_registry


class Command(BaseCommand):
    help = "Starts Temporal.io worker."

    def add_arguments(self, parser):
        parser.add_argument(
            "worker_name",
            nargs="?",
            choices=settings.WORKER_CONFIGS.keys(),
            help="The name of the worker to start.",
        )
        parser.add_argument(
            "-a",
            "--all",
            action="store_true",
            default=False,
            help=(
                "Start a worker per queue registered in the django-temporalio registry."
                " Meant for development purposes."
            ),
        )

    async def start_dev_workers(self):
        client = await init_client()
        tasks = []
        queues = []

        for queue_name, item in get_queue_registry().items():
            worker = Worker(
                client,
                task_queue=queue_name,
                workflows=item.workflows,
                activities=item.activities,
            )
            tasks.append(worker.run())
            queues.append(queue_name)

        self.stdout.write(
            f"Starting dev Temporal.io workers for queues: {', '.join(queues)}\n"
            f"(press ctrl-c to stop)...",
        )
        await asyncio.gather(*tasks)

    async def start_worker(self, name):
        worker_config = settings.WORKER_CONFIGS[name]
        queue_name = worker_config["task_queue"]
        registry = get_queue_registry().get(queue_name)

        if not registry:
            self.stderr.write(
                f"Failed to start '{name}' worker.\n"
                f"No activities/workflows registered for queue '{queue_name}'.",
            )
            sys.exit(1)

        client = await init_client()
        worker = Worker(
            client,
            **worker_config,
            workflows=registry.workflows,
            activities=registry.activities,
        )
        self.stdout.write(
            f"Starting '{name}' worker for '{queue_name}' queue\n"
            f"(press ctrl-c to stop)...",
        )
        await worker.run()

    def handle(self, *args, **options):
        worker_name = options["worker_name"]
        run_all = options["all"]

        if not worker_name and not run_all:
            self.stderr.write("You must provide either a worker name or --all flag.")
            sys.exit(2)

        with contextlib.suppress(KeyboardInterrupt):
            asyncio.run(
                (
                    self.start_dev_workers()
                    if run_all
                    else self.start_worker(worker_name)
                ),
            )

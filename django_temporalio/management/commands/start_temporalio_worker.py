import asyncio

from django.core.management import BaseCommand, CommandError

from django_temporalio.conf import settings
from django_temporalio.worker import WorkerStartError, get_worker_runner


class Command(BaseCommand):
    help = "Starts Temporal.io workers."

    def add_arguments(self, parser):
        parser.add_argument(
            "worker_name",
            nargs="?",
            choices=settings.WORKER_CONFIGS.keys(),
            help=(
                "The name of the worker to start, as defined in WORKER_CONFIGS;"
                " omit it to start all of them."
            ),
        )

    def handle(self, *args, **options):
        worker_name = options["worker_name"]
        runner = get_worker_runner(self.stdout)
        try:
            asyncio.run(runner.start(worker_name) if worker_name else runner.start())
        except WorkerStartError as e:
            raise CommandError(e) from e

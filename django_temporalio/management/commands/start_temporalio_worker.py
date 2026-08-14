import asyncio
import sys

from django.core.management import BaseCommand, CommandError

from django_temporalio.conf import settings
from django_temporalio.worker import WorkerStartError, get_worker_runner


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

    def handle(self, *args, **options):
        worker_name = options["worker_name"]
        run_all = options["all"]

        if not worker_name and not run_all:
            self.stderr.write("You must provide either a worker name or --all flag.")
            sys.exit(2)

        runner = get_worker_runner(self.stdout)
        try:
            asyncio.run(runner.start() if run_all else runner.start(worker_name))
        except WorkerStartError as e:
            raise CommandError(e) from e

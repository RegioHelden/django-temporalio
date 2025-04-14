import asyncio

from django.core.management.base import BaseCommand
from temporalio.client import ScheduleUpdate

from django_temporalio.client import init_client
from django_temporalio.registry import schedules


class Command(BaseCommand):
    verbose = False
    dry_run = False
    help = "Syncs Temporal.io schedules."

    def add_arguments(self, parser):
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            default=False,
            help="Prints what would be done without actually doing it.",
        )

    def log(self, msg: str):
        if self.verbose or self.dry_run:
            self.stdout.write(msg)

    async def sync_schedules(self):
        client = await init_client()
        current_schedule_ids = {s.id async for s in await client.list_schedules()}
        registry = schedules.get_registry()
        removed_schedule_ids = sorted(current_schedule_ids - set(registry))
        updated_schedule_ids = []
        new_schedule_ids = []

        for schedule_id in removed_schedule_ids:
            if not self.dry_run:
                handle = client.get_schedule_handle(schedule_id)
                await handle.delete()
            self.log(f"Removed '{schedule_id}'")

        for schedule_id, schedule in registry.items():
            if schedule_id in current_schedule_ids:
                if not self.dry_run:
                    handle = client.get_schedule_handle(schedule_id)
                    await handle.update(
                        lambda schedule=schedule: ScheduleUpdate(schedule=schedule),
                    )
                updated_schedule_ids.append(schedule_id)
                self.log(f"Updated '{schedule_id}'")
            else:
                if not self.dry_run:
                    await client.create_schedule(schedule_id, schedule)
                new_schedule_ids.append(schedule_id)
                self.log(f"Created '{schedule_id}'")

        self.stdout.write(
            f"removed {len(removed_schedule_ids)}, "
            f"updated {len(updated_schedule_ids)}, "
            f"created {len(new_schedule_ids)}",
        )

    def handle(self, *args, **options):
        self.verbose = int(options["verbosity"]) > 1
        self.dry_run = options["dry_run"]
        self.stdout.write(f"Syncing schedules{' [DRY RUN]' if self.dry_run else ''}...")
        asyncio.run(self.sync_schedules())

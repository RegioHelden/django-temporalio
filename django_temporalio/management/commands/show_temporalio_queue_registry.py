from django.core.management.base import BaseCommand

from django_temporalio.registry import get_queue_registry


class Command(BaseCommand):
    help = "Show django-temporalio queue registry."
    indent = 2

    def handle(self, *args, **options):
        for queue_name, item in get_queue_registry().items():
            self.stdout.write(f"{queue_name}")
            for label, entities in [
                ("workflows", item.workflows),
                ("activities", item.activities),
            ]:
                if not entities:
                    continue

                self.stdout.write(f"{' ' * self.indent}{label}:")
                for entity in entities:
                    self.stdout.write(
                        f"{' ' * self.indent * 2}{entity.__module__}.{entity.__name__}",
                    )

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from functools import wraps

from temporalio.client import Schedule

from django_temporalio.utils import autodiscover_modules


class ScheduleRegistry:
    _registry: dict[str, Schedule]

    class AlreadyRegisteredError(Exception):
        pass

    def __init__(self):
        self._init_registry()

    def _init_registry(self):
        self._registry = {}

    def register(self, schedule_id: str, schedule: Schedule):
        if schedule_id in self._registry:
            raise self.AlreadyRegisteredError(
                f"Schedule with ID '{schedule_id}' is already registered.",
            )
        self._registry[schedule_id] = schedule

    def get_registry(self):
        autodiscover_modules("*schedules*")
        return self._registry

    def clear_registry(self):
        self._init_registry()


class QueueRegistry:
    module_name: str
    check_attr: str
    _registry: dict[str, list]
    _registered_object_ids: set

    class MissingTemporalDecoratorError(Exception):
        pass

    def __init__(self, module_name: str, check_attr: str):
        self.module_name = module_name
        self.check_attr = check_attr
        self._init_registry()

    def _init_registry(self):
        self._registry = {}
        self._registered_object_ids = set()

    @staticmethod
    def _make_id(obj: Callable):
        return f"{obj.__module__}.{obj.__name__}"

    def register(self, *queue_names: str):
        if not queue_names:
            raise ValueError("At least one queue name must be provided.")

        @wraps(*queue_names)
        def decorator(obj):
            if not hasattr(obj, self.check_attr):
                raise self.MissingTemporalDecoratorError(
                    f"'{self._make_id(obj)}' must be decorated with 'defn' Temporal.io"
                    "decorator.\n"
                    "See https://github.com/temporalio/sdk-python/blob/main/README.md",
                )

            if (obj_id := self._make_id(obj)) not in self._registered_object_ids:
                self._registered_object_ids.add(obj_id)
                for queue_name in queue_names:
                    self._registry.setdefault(queue_name, []).append(obj)

            return obj

        return decorator

    def clear_registry(self):
        self._init_registry()

    def get_registry(self):
        autodiscover_modules(self.module_name)
        return self._registry


schedules = ScheduleRegistry()
queue_workflows = QueueRegistry("*workflows*", "__temporal_workflow_definition")
queue_activities = QueueRegistry("*activities*", "__temporal_activity_definition")


@dataclass
class QueueRegistryItem:
    workflows: Sequence[type] = field(default_factory=list)
    activities: Sequence[Callable] = field(default_factory=list)


def get_queue_registry():
    """
    merges the workflows and activities registries
    """
    result: dict[str, QueueRegistryItem] = {
        queue_name: QueueRegistryItem(
            workflows=workflows,
        )
        for queue_name, workflows in queue_workflows.get_registry().items()
    }

    for queue_name, activities in queue_activities.get_registry().items():
        result.setdefault(queue_name, QueueRegistryItem()).activities = activities
    return result

import asyncio
import contextlib
import signal

from django.utils.module_loading import import_string
from temporalio.client import Client
from temporalio.worker import Worker, WorkerConfig

from django_temporalio.client import init_client
from django_temporalio.conf import settings
from django_temporalio.logs.interceptors import get_interceptors
from django_temporalio.registry import QueueRegistryItem, get_queue_registry


class WorkerStartError(Exception):
    """Raised when a worker cannot be built and started."""


class WorkerRunner:
    """The default WORKER_RUNNER; subclass it and point the setting at yours."""

    SHUTDOWN_SIGNALS = (signal.SIGINT, signal.SIGTERM)  # Ctrl+C / kill <pid>

    client: Client
    queue_registry: dict[str, QueueRegistryItem]
    event_loop: asyncio.AbstractEventLoop
    stop_event: asyncio.Event
    tasks: list[asyncio.Future]

    def __init__(self, stdout):
        self.stdout = stdout

    async def _init_start(self):
        # not in __init__: the client is loop-bound, it must be created on the
        # running loop - the runner itself is constructed before the loop exists
        self.queue_registry = get_queue_registry()
        self.client = await init_client()

    async def start(self, *names):
        """
        Run the workers declared under `names` in the WORKER_CONFIGS setting;
        without names, run a worker per queue registered in the registry.
        """
        await self._init_start()
        configs = self._get_configs(*names)

        workers = [self._build_worker(name, config) for name, config in configs.items()]

        self.stdout.write(
            f"Starting Temporal.io workers: {', '.join(configs)}\n"
            f"(press ctrl-c to stop)...",
        )
        await self.run(workers)

    async def run(self, workers: list[Worker]):
        """
        Run the workers until they finish or a signal shuts them down - the
        first signal drains gracefully, a second stops immediately.
        """
        if not workers:
            return

        self.stop_event = asyncio.Event()
        self.tasks = [asyncio.create_task(worker.run()) for worker in workers]

        self._install_signal_handlers()
        try:
            await self._wait_for_stop()
            await self._drain(workers)
        finally:
            self._remove_signal_handlers()

    def _get_configs(self, *names):
        if names:
            return {name: settings.WORKER_CONFIGS[name] for name in names}
        return {queue: WorkerConfig(task_queue=queue) for queue in self.queue_registry}

    def _build_worker(self, name, config: WorkerConfig) -> Worker:
        config = dict(config)
        # pop it or **config below would duplicate the interceptors kwarg
        extra_interceptors = config.pop("interceptors", ())
        queue_name = config["task_queue"]
        registry = self.queue_registry.get(queue_name)

        if not registry:
            raise WorkerStartError(
                f"Failed to start '{name}' worker.\n"
                f"No activities/workflows registered for queue '{queue_name}'.",
            )

        return Worker(
            self.client,
            **config,
            workflows=registry.workflows,
            activities=registry.activities,
            interceptors=get_interceptors(extra_interceptors),
        )

    async def _wait_for_stop(self):
        """Wait until a signal arrives or any worker stops on its own."""
        stop_requested = asyncio.create_task(self.stop_event.wait())
        try:
            await asyncio.wait(
                [stop_requested, *self.tasks],
                return_when=asyncio.FIRST_COMPLETED,
            )
        finally:
            stop_requested.cancel()

    async def _drain(self, workers: list[Worker]):
        """Stop the workers and await their run tasks; a crash re-raises here."""
        run_tasks = [*self.tasks]
        await asyncio.gather(
            *(
                worker.shutdown()
                for worker, task in zip(workers, run_tasks, strict=True)
                if not task.done()
            ),
        )
        await asyncio.gather(*run_tasks)

    def _install_signal_handlers(self):
        # signal.signal, not loop.add_signal_handler: under load the Temporal core
        # starves the loop's signal self-pipe, so add_signal_handler never fires.
        self.event_loop = asyncio.get_running_loop()
        for sig in self.SHUTDOWN_SIGNALS:
            with contextlib.suppress(ValueError):  # signal.signal needs main thread
                signal.signal(sig, self._graceful_shutdown)

    def _graceful_shutdown(self, signum, frame):
        self.stdout.write(
            "Graceful shutdown - waiting for running tasks to finish\n"
            "(interrupting again stops the worker immediately)...",
        )
        for sig in self.SHUTDOWN_SIGNALS:  # a further signal now stops immediately
            with contextlib.suppress(ValueError):
                signal.signal(sig, self._forced_shutdown)
        self.event_loop.call_soon_threadsafe(self.stop_event.set)

    def _forced_shutdown(self, signum, frame):
        self.stdout.write("Forced shutdown - stopping immediately.")
        self._remove_signal_handlers()
        signal.raise_signal(signum)

    def _remove_signal_handlers(self):
        for sig in self.SHUTDOWN_SIGNALS:
            with contextlib.suppress(ValueError):
                signal.signal(sig, signal.SIG_DFL)


def get_worker_runner(stdout) -> WorkerRunner:
    """Instantiate the runner declared in the WORKER_RUNNER setting."""
    return import_string(settings.WORKER_RUNNER)(stdout)

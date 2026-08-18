import asyncio

from django_temporalio.worker import WorkerRunner


class FakeWorker:
    """
    Mimics Worker.run/shutdown semantics: run() completes once shutdown() has.
    """

    def __init__(self):
        self.shutdown_requested = asyncio.Event()
        self.shutdown_called = False

    async def run(self):
        await self.shutdown_requested.wait()

    async def shutdown(self):
        self.shutdown_called = True
        self.shutdown_requested.set()


class CrashingWorker(FakeWorker):
    async def run(self):
        raise RuntimeError("worker crashed")


class CustomWorkerRunner(WorkerRunner):
    """Stands in for a consumer's runner swapped in via the WORKER_RUNNER setting."""

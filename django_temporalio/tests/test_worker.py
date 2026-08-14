import asyncio
import os
import signal
from io import StringIO
from unittest import IsolatedAsyncioTestCase, TestCase, mock

from django.test import override_settings

from django_temporalio.conf import SETTINGS_KEY
from django_temporalio.tests.factories import (
    CrashingWorker,
    CustomWorkerRunner,
    FakeWorker,
)
from django_temporalio.worker import WorkerRunner, get_worker_runner


class WorkerRunnerTestCase(IsolatedAsyncioTestCase):
    """
    Covers WorkerRunner's shutdown escalation - a signal drains gracefully, a
    second forces an immediate stop - and that neither path hides a worker crash.
    """

    def setUp(self):
        self.stdout = StringIO()
        self.addCleanup(self.stdout.close)
        self.runner = WorkerRunner(self.stdout)

    async def interrupt(self):
        await asyncio.sleep(0.05)  # let handlers install and workers start
        os.kill(os.getpid(), signal.SIGINT)

    async def test_signal_triggers_graceful_shutdown(self):
        worker = FakeWorker()
        run = asyncio.create_task(self.runner.run([worker]))

        await self.interrupt()
        await asyncio.wait_for(run, timeout=2)

        self.assertTrue(worker.shutdown_called)
        self.assertIn("Graceful shutdown", self.stdout.getvalue())

    async def test_second_signal_terminates_the_process(self):
        # a task that refuses to cancel would trap asyncio.run, so the second
        # signal re-raises under the OS default to terminate the process outright
        self.runner.stop_event = asyncio.Event()
        self.runner.tasks = []
        self.runner._install_signal_handlers()

        self.runner._graceful_shutdown(signal.SIGINT, None)  # first signal ...
        # ... arms the forced handler for the next one
        self.assertEqual(
            signal.getsignal(signal.SIGINT),
            self.runner._forced_shutdown,
        )

        with mock.patch(
            "django_temporalio.worker.signal.raise_signal",
        ) as terminate:
            self.runner._forced_shutdown(signal.SIGINT, None)  # second signal

        self.assertIn("Forced shutdown", self.stdout.getvalue())
        terminate.assert_called_once_with(signal.SIGINT)
        # reset to the OS default before re-raising
        self.assertIs(signal.getsignal(signal.SIGINT), signal.SIG_DFL)
        self.assertIs(signal.getsignal(signal.SIGTERM), signal.SIG_DFL)

    async def test_crashed_worker_shuts_down_the_rest(self):
        healthy = FakeWorker()

        with self.assertRaises(RuntimeError):
            await asyncio.wait_for(
                self.runner.run([CrashingWorker(), healthy]),
                timeout=2,
            )

        self.assertTrue(healthy.shutdown_called)


class GetWorkerRunnerTestCase(TestCase):
    def test_default_runner(self):
        self.assertIsInstance(get_worker_runner(StringIO()), WorkerRunner)

    def test_runner_from_settings(self):
        user_settings = {
            "WORKER_RUNNER": "django_temporalio.tests.factories.CustomWorkerRunner",
        }
        with override_settings(**{SETTINGS_KEY: user_settings}):
            runner = get_worker_runner(StringIO())

        self.assertIsInstance(runner, CustomWorkerRunner)

import asyncio
import inspect
import threading
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from unittest import IsolatedAsyncioTestCase, mock

from asgiref.sync import sync_to_async
from django.db import connections
from temporalio.worker import ExecuteActivityInput

from django_temporalio.interceptors import ActivityIsolationInterceptor


class ActivityIsolationInterceptorTestCase(IsolatedAsyncioTestCase):
    """Test case for the inbound interceptor of ActivityIsolationInterceptor."""

    def setUp(self):
        self.next = mock.Mock(
            execute_activity=mock.AsyncMock(side_effect=self.run_activity),
        )
        self.interceptor = ActivityIsolationInterceptor().intercept_activity(self.next)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.addCleanup(self.executor.shutdown)
        self.addCleanup(lambda: self.executor.submit(connections.close_all).result())

    async def execute_activity(self, fn, executor=None):
        activity_input = ExecuteActivityInput(
            fn=fn,
            args=[],
            executor=executor or self.executor,
            headers={},
        )
        return await self.interceptor.execute_activity(activity_input)

    @staticmethod
    async def run_activity(activity_input: ExecuteActivityInput):
        if inspect.iscoroutinefunction(activity_input.fn):
            return await activity_input.fn()
        return await asyncio.get_running_loop().run_in_executor(
            activity_input.executor,
            activity_input.fn,
        )

    @staticmethod
    def open_connection():
        connection = connections["default"]
        connection.ensure_connection()
        return connection

    async def test_concurrent_async_activities_get_their_own_thread(self):
        # a shared thread would block on the first wait and break the barrier
        barrier = threading.Barrier(3)

        async def activity():
            await sync_to_async(barrier.wait)(timeout=1)

        await asyncio.gather(*(self.execute_activity(activity) for _ in range(3)))

    async def test_async_activity_connection_is_closed(self):
        async def activity():
            return await sync_to_async(self.open_connection)()

        connection = await self.execute_activity(activity)

        self.assertIsNone(connection.connection)

    async def test_async_activity_connection_is_closed_on_failure(self):
        opened = []

        async def activity():
            opened.append(await sync_to_async(self.open_connection)())
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            await self.execute_activity(activity)

        self.assertIsNone(opened[0].connection)

    async def test_sync_activity_connection_is_closed(self):
        connection = await self.execute_activity(self.open_connection)

        self.assertIsNone(connection.connection)

    async def test_sync_activity_connection_is_closed_on_failure(self):
        opened = []

        def activity():
            opened.append(self.open_connection())
            raise ValueError("boom")

        with self.assertRaises(ValueError):
            await self.execute_activity(activity)

        self.assertIsNone(opened[0].connection)

    async def test_sync_activity_keeps_persistent_connection(self):
        def activity():
            return self.open_connection().connection

        with mock.patch.dict(connections.settings["default"], CONN_MAX_AGE=None):
            first_connection = await self.execute_activity(activity)
            second_connection = await self.execute_activity(activity)

        self.assertIs(second_connection, first_connection)

    async def test_sync_activity_on_process_pool_is_left_untouched(self):
        def activity():
            pass

        # hands back the function the SDK would run instead of running it
        self.next.execute_activity.side_effect = lambda activity_input: (
            activity_input.fn
        )

        executed_fn = await self.execute_activity(
            activity,
            executor=mock.Mock(spec=ProcessPoolExecutor),
        )

        self.assertIs(executed_fn, activity)

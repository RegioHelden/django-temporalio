from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from asgiref.sync import ThreadSensitiveContext, sync_to_async
from django.core.cache import close_caches
from django.db import close_old_connections, connections, reset_queries
from temporalio.worker import (
    ActivityInboundInterceptor,
    ExecuteActivityInput,
    Interceptor,
)


class _ActivityIsolationInterceptor(ActivityInboundInterceptor):
    """Delegates every isolation step to the `root` ActivityIsolationInterceptor."""

    def __init__(
        self,
        next_interceptor: ActivityInboundInterceptor,
        root: ActivityIsolationInterceptor,
    ):
        super().__init__(next_interceptor)
        self.root = root

    async def execute_activity(self, activity_input: ExecuteActivityInput) -> Any:
        if self.root.runs_on_event_loop(activity_input.fn):
            async with ThreadSensitiveContext():
                try:
                    return await self.next.execute_activity(activity_input)
                finally:
                    # must run inside the context to reach the activity's own thread
                    await sync_to_async(self.root.release_discarded_thread)()

        # the wrapper is a closure, which a process pool cannot pickle
        if isinstance(activity_input.executor, ThreadPoolExecutor):
            activity_input.fn = self.root.with_refreshed_thread(activity_input.fn)
        return await self.next.execute_activity(activity_input)


class ActivityIsolationInterceptor(Interceptor):
    """
    Runs each activity the way Django runs a request.

    Django's async APIs hand their sync code to one shared thread unless a
    unit of work is marked, so concurrent async activities would query the
    database one after another.

    Each async activity gets its own thread, released when it ends; sync
    activities refresh their reused executor thread before and after.

    To release further per-thread resources, subclass, extend
    `release_discarded_thread`/`refresh_reused_thread` and point the
    INTERCEPTORS setting at the subclass.
    """

    def intercept_activity(
        self,
        next: ActivityInboundInterceptor,  # noqa: A002 - base class signature
    ) -> ActivityInboundInterceptor:
        return _ActivityIsolationInterceptor(next, self)

    def release_discarded_thread(self) -> None:
        # the thread dies right after, so its connections could never be reused
        connections.close_all()
        close_caches()

    def refresh_reused_thread(self) -> None:
        # the thread outlives the activity, so CONN_MAX_AGE decides what is kept
        reset_queries()
        close_old_connections()
        close_caches()

    def with_refreshed_thread(self, fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            self.refresh_reused_thread()
            try:
                return fn(*args, **kwargs)
            finally:
                self.refresh_reused_thread()

        return wrapper

    @staticmethod
    def runs_on_event_loop(fn: Callable) -> bool:
        # the SDK's own check, so both agree on which activities are async
        return inspect.iscoroutinefunction(fn) or inspect.iscoroutinefunction(
            fn.__call__,
        )

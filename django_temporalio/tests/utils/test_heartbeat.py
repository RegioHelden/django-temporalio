import asyncio
from datetime import timedelta
from unittest import IsolatedAsyncioTestCase

from temporalio.testing import ActivityEnvironment

from django_temporalio.utils import heartbeat


class HeartbeatTestCase(IsolatedAsyncioTestCase):
    """Test case for utils.heartbeat."""

    def setUp(self):
        self.heartbeats = []
        self.env = ActivityEnvironment()
        self.env.on_heartbeat = lambda *details: self.heartbeats.append(details)

    async def test_heartbeats_while_the_body_runs(self):
        async def activity():
            async with heartbeat(timedelta(milliseconds=10)):
                await asyncio.sleep(0.05)
            return len(self.heartbeats)

        heartbeats_during_body = await self.env.run(activity)

        self.assertGreaterEqual(heartbeats_during_body, 2)

    async def test_heartbeats_stop_after_the_body(self):
        async def activity():
            async with heartbeat(timedelta(milliseconds=10)):
                pass
            count = len(self.heartbeats)
            await asyncio.sleep(0.05)
            return count

        heartbeats_during_body = await self.env.run(activity)

        self.assertEqual(len(self.heartbeats), heartbeats_during_body)

    async def test_body_failure_is_reraised(self):
        async def activity():
            async with heartbeat(timedelta(milliseconds=10)):
                raise ValueError("boom")

        with self.assertRaises(ValueError):
            await self.env.run(activity)

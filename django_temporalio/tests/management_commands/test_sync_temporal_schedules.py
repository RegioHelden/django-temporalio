from io import StringIO
from unittest import TestCase, mock

from django.core.management import call_command


async def async_iterable(*items):
    for item in items:
        yield item


class SyncTemporalioSchedulesTestCase(TestCase):
    """
    Test case for sync_temporalio_schedules management command.
    """

    def setUp(self, *args, **kwargs):
        self.schedule_handle_mock = mock.AsyncMock()
        self.client_mock = mock.AsyncMock(
            list_schedules=mock.AsyncMock(
                return_value=async_iterable(
                    mock.Mock(id="schedule_1"),
                    mock.Mock(id="schedule_2"),
                    mock.Mock(id="schedule_3"),
                    mock.Mock(id="schedule_4"),
                    mock.Mock(id="schedule_5"),
                ),
            ),
            get_schedule_handle=mock.Mock(return_value=self.schedule_handle_mock),
        )
        init_client_patcher = mock.patch(
            "django_temporalio.management.commands.sync_temporalio_schedules.init_client",
            return_value=self.client_mock,
        )
        init_client_patcher.start()
        self.addCleanup(init_client_patcher.stop)

        get_registry_patcher = mock.patch(
            "django_temporalio.management.commands.sync_temporalio_schedules.schedules.get_registry",
            return_value={
                "schedule_1": "schedule_instance_1",
                "schedule_2": "schedule_instance_2",
                "schedule_6": "schedule_instance_6",
            },
        )
        self.get_registry_mock = get_registry_patcher.start()
        self.addCleanup(get_registry_patcher.stop)

        self.stdout = StringIO()
        self.addCleanup(self.stdout.close)

    def _test_sync_schedules(self, verbosity=0):
        call_command(
            "sync_temporalio_schedules",
            verbosity=verbosity,
            stdout=self.stdout,
        )

        self.get_registry_mock.assert_called_once_with()
        self.client_mock.assert_has_calls(
            [
                mock.call.list_schedules(),
                # get handle to initiate delete
                mock.call.get_schedule_handle("schedule_3"),
                mock.call.get_schedule_handle("schedule_4"),
                mock.call.get_schedule_handle("schedule_5"),
                # get handle to initiate update
                mock.call.get_schedule_handle("schedule_1"),
                mock.call.get_schedule_handle("schedule_2"),
                mock.call.create_schedule("schedule_6", "schedule_instance_6"),
            ],
        )
        self.schedule_handle_mock.assert_has_calls(
            [
                mock.call.delete(),
                mock.call.update(mock.ANY),
            ],
        )

    def test_sync_schedules(self):
        self._test_sync_schedules()
        self.assertEqual(
            "Syncing schedules...\nremoved 3, updated 2, created 1\n",
            self.stdout.getvalue(),
        )

    def test_sync_schedules_verbose_output(self):
        self._test_sync_schedules(verbosity=2)
        self.assertEqual(
            self.stdout.getvalue(),
            "Syncing schedules...\n"
            "Removed 'schedule_3'\n"
            "Removed 'schedule_4'\n"
            "Removed 'schedule_5'\n"
            "Updated 'schedule_1'\n"
            "Updated 'schedule_2'\n"
            "Created 'schedule_6'\n"
            "removed 3, updated 2, created 1\n",
        )

    def test_sync_schedules_dry_run(self):
        call_command("sync_temporalio_schedules", dry_run=True, stdout=self.stdout)

        self.get_registry_mock.assert_called_once_with()
        self.client_mock.assert_has_calls(
            [
                mock.call.list_schedules(),
            ],
        )
        self.schedule_handle_mock.assert_not_called()
        self.assertEqual(
            self.stdout.getvalue(),
            "Syncing schedules [DRY RUN]...\n"
            "Removed 'schedule_3'\n"
            "Removed 'schedule_4'\n"
            "Removed 'schedule_5'\n"
            "Updated 'schedule_1'\n"
            "Updated 'schedule_2'\n"
            "Created 'schedule_6'\n"
            "removed 3, updated 2, created 1\n",
        )

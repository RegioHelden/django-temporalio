from io import StringIO
from unittest import TestCase, mock

from django.core.management import CommandError, call_command
from django.test import override_settings
from temporalio.worker import WorkerConfig

from django_temporalio.conf import SETTINGS_KEY


class StartTemporalioWorkerTestCase(TestCase):
    """
    Test case for start_temporalio_worker management command.
    """

    @classmethod
    def setUpClass(cls):
        worker_configs: dict[str, WorkerConfig] = {
            "worker_1": WorkerConfig(
                task_queue="TEST_QUEUE_1",
            ),
            "worker_2": WorkerConfig(
                task_queue="TEST_QUEUE_2",
            ),
        }

        cls._overridden_context = override_settings(
            **{SETTINGS_KEY: {"WORKER_CONFIGS": worker_configs}},
        )
        cls._overridden_context.enable()
        cls.addClassCleanup(cls._overridden_context.disable)

    def setUp(self):
        self.worker_run_mock = mock.AsyncMock()
        worker_patcher = mock.patch(
            "django_temporalio.management.commands.start_temporalio_worker.Worker",
            return_value=mock.Mock(run=self.worker_run_mock),
        )
        self.worker_mock = worker_patcher.start()
        self.addCleanup(worker_patcher.stop)

        self.client_mock = mock.Mock()
        init_client_patcher = mock.patch(
            "django_temporalio.management.commands.start_temporalio_worker.init_client",
            return_value=self.client_mock,
        )
        init_client_patcher.start()
        self.addCleanup(init_client_patcher.stop)

        get_queue_registry_patcher = mock.patch(
            "django_temporalio.management.commands.start_temporalio_worker.get_queue_registry",
            return_value={
                "TEST_QUEUE_1": mock.MagicMock(
                    workflows=["workflow_1"],
                    activities=["activity_1"],
                ),
                "TEST_QUEUE_2": mock.MagicMock(
                    workflows=["workflow_2"],
                    activities=["activity_2"],
                ),
            },
        )
        get_queue_registry_patcher.start()
        self.addCleanup(get_queue_registry_patcher.stop)

        self.stdout = StringIO()
        self.addCleanup(self.stdout.close)

    def test_flag_all(self):
        """
        Test command execution with --all flag.
        """
        call_command("start_temporalio_worker", all=True, stdout=self.stdout)

        self.worker_mock.assert_has_calls(
            [
                mock.call(
                    self.client_mock,
                    task_queue="TEST_QUEUE_1",
                    workflows=["workflow_1"],
                    activities=["activity_1"],
                ),
                mock.call(
                    self.client_mock,
                    task_queue="TEST_QUEUE_2",
                    workflows=["workflow_2"],
                    activities=["activity_2"],
                ),
            ],
            any_order=True,
        )
        self.worker_run_mock.assert_has_calls([mock.call(), mock.call()])
        self.assertEqual(
            self.stdout.getvalue(),
            "Starting dev Temporal.io workers for queues: TEST_QUEUE_1, TEST_QUEUE_2\n"
            "(press ctrl-c to stop)...\n",
        )

    def test_start_worker(self):
        """
        Test command execution with worker name argument.
        """
        call_command("start_temporalio_worker", "worker_1", stdout=self.stdout)

        self.worker_mock.assert_called_once_with(
            self.client_mock,
            task_queue="TEST_QUEUE_1",
            workflows=["workflow_1"],
            activities=["activity_1"],
        )
        self.worker_run_mock.assert_called_once()
        self.assertEqual(
            self.stdout.getvalue(),
            "Starting 'worker_1' worker for 'TEST_QUEUE_1' queue\n"
            "(press ctrl-c to stop)...\n",
        )

    def test_start_invalid_worker(self):
        """
        Test that an error is raised when not declared worker name is provided.
        """
        with self.assertRaises(CommandError) as cm:
            call_command("start_temporalio_worker", "worker_3", stdout=self.stdout)

        self.worker_mock.assert_not_called()
        # use regex due to different error messages in different Python versions
        self.assertRegex(
            str(cm.exception),
            r"Error: argument worker_name: invalid choice: '?worker_3'? "
            r"\(choose from '?worker_1'?, '?worker_2'?\)",
        )

    def test_no_arguments(self):
        """
        Test that an error is raised when no arguments are provided.
        """
        with self.assertRaises(SystemExit):
            call_command("start_temporalio_worker", stderr=self.stdout)

        self.worker_mock.assert_not_called()
        self.assertEqual(
            self.stdout.getvalue(),
            "You must provide either a worker name or --all flag.\n",
        )

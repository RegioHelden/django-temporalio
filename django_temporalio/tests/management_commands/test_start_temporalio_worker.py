from io import StringIO
from unittest import TestCase, mock

from django.core.management import CommandError, call_command
from django.test import override_settings
from temporalio.worker import WorkerConfig

from django_temporalio.conf import SETTINGS_KEY
from django_temporalio.logs.interceptors import ActivityFailureLoggingInterceptor


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
            "django_temporalio.worker.Worker",
            return_value=mock.Mock(run=self.worker_run_mock),
        )
        self.worker_mock = worker_patcher.start()
        self.addCleanup(worker_patcher.stop)

        self.client_mock = mock.Mock()
        init_client_patcher = mock.patch(
            "django_temporalio.worker.init_client",
            return_value=self.client_mock,
        )
        init_client_patcher.start()
        self.addCleanup(init_client_patcher.stop)

        get_queue_registry_patcher = mock.patch(
            "django_temporalio.worker.get_queue_registry",
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
                    interceptors=[],
                ),
                mock.call(
                    self.client_mock,
                    task_queue="TEST_QUEUE_2",
                    workflows=["workflow_2"],
                    activities=["activity_2"],
                    interceptors=[],
                ),
            ],
            any_order=True,
        )
        self.worker_run_mock.assert_has_calls([mock.call(), mock.call()])
        self.assertEqual(
            self.stdout.getvalue(),
            "Starting Temporal.io workers: TEST_QUEUE_1, TEST_QUEUE_2\n"
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
            interceptors=[],
        )
        self.worker_run_mock.assert_called_once()
        self.assertEqual(
            self.stdout.getvalue(),
            "Starting Temporal.io workers: worker_1\n(press ctrl-c to stop)...\n",
        )

    def test_interceptors_from_settings(self):
        """
        Test that workers are started with the interceptors
        declared in the INTERCEPTORS setting.
        """
        user_settings = {
            "WORKER_CONFIGS": {"worker_1": WorkerConfig(task_queue="TEST_QUEUE_1")},
            "INTERCEPTORS": (
                "django_temporalio.logs.ActivityFailureLoggingInterceptor",
            ),
        }

        with override_settings(**{SETTINGS_KEY: user_settings}):
            call_command("start_temporalio_worker", "worker_1", stdout=self.stdout)

        interceptors = self.worker_mock.call_args.kwargs["interceptors"]
        self.assertEqual(len(interceptors), 1)
        self.assertIsInstance(interceptors[0], ActivityFailureLoggingInterceptor)

    def test_worker_config_interceptors_are_merged(self):
        """
        Test that interceptors from the worker config are appended
        to the ones declared in the INTERCEPTORS setting.
        """
        custom_interceptor = mock.Mock()
        worker_configs: dict[str, WorkerConfig] = {
            "worker_1": WorkerConfig(
                task_queue="TEST_QUEUE_1",
                interceptors=[custom_interceptor],
            ),
        }
        user_settings = {
            "WORKER_CONFIGS": worker_configs,
            "INTERCEPTORS": (
                "django_temporalio.logs.ActivityFailureLoggingInterceptor",
            ),
        }

        with override_settings(**{SETTINGS_KEY: user_settings}):
            call_command("start_temporalio_worker", "worker_1", stdout=self.stdout)

        interceptors = self.worker_mock.call_args.kwargs["interceptors"]
        self.assertEqual(len(interceptors), 2)
        self.assertIsInstance(interceptors[0], ActivityFailureLoggingInterceptor)
        self.assertIs(interceptors[1], custom_interceptor)
        # the worker config in the settings must not be mutated
        self.assertEqual(
            worker_configs["worker_1"]["interceptors"],
            [custom_interceptor],
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

    def test_start_worker_without_registered_queue(self):
        """
        Test that a worker whose queue has no registered activities/workflows
        fails with a CommandError.
        """
        worker_configs = {"worker_3": WorkerConfig(task_queue="MISSING_QUEUE")}

        with (
            override_settings(**{SETTINGS_KEY: {"WORKER_CONFIGS": worker_configs}}),
            self.assertRaises(CommandError) as cm,
        ):
            call_command("start_temporalio_worker", "worker_3", stdout=self.stdout)

        self.worker_mock.assert_not_called()
        self.assertIn(
            "No activities/workflows registered for queue 'MISSING_QUEUE'",
            str(cm.exception),
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

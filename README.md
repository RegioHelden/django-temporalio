# django-temporalio
___

A small Django app that provides helpers for integrating [Temporal.io](https://temporal.io/) with Django.

## Features

- Registry: Provides a registry that holds mappings between queue names and registered activities and workflows.
- Management Commands: Includes management commands to manage Temporal.io workers and sync schedules.
- Activity Failure Logging: An opt-in worker interceptor that logs activity failures at ERROR level 
  with the full traceback, so errors in endlessly retried activities surface in your error tracking 
  instead of only in the Temporal UI, plus a logging filter to throttle the SDK's own per-attempt 
  failure records.

## Installation

You can install `django_temporalio` using pip:

```bash
$ pip install django-temporalio
```

Add `django_temporalio` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    ...
    'django_temporalio.apps.DjangoTemporalioConfig',
    ...
]
```

Add the following settings to your `settings.py`:

```python
from temporalio.worker import WorkerConfig

DJANGO_TEMPORALIO = {
    "CLIENT_CONFIG": {
        "target_host": "localhost:7233",
    },
    "BASE_MODULE": "path.to.module",
    "WORKER_CONFIGS": {
        "main": WorkerConfig(
            task_queue="MAIN_TASK_QUEUE",
            ...
        ),
        ...
    },
}
```

## Usage

Activities, workflows and schedules should be placed inside the base module defined by the `BASE_MODULE` setting, 
preferably outside of any Django application, in order to keep the uses of 
the [imports_passed_through](https://python.temporal.io/temporalio.workflow.unsafe.html) context manager encapsulated 
inside the module, along with Temporal.io related code.

### Workflow and Activity Registry

The registry is a singleton that holds mappings between queue names and registered activities and workflows.
You can register activities and workflows using the `register` method. 

Activities and workflows should be declared in modules matching the following patterns `*workflows*.py` and 
`*activities*.py` respectively. 

```python
from temporalio import activity, workflow
from django_temporalio.registry import queue_activities, queue_workflows


@queue_activities.register("HIGH_PRIORITY_TASK_QUEUE", "MAIN_TASK_QUEUE")
@activity.defn
def my_activity():
    pass


@queue_workflows.register("HIGH_PRIORITY_TASK_QUEUE", "MAIN_TASK_QUEUE")
@workflow.defn
class MyWorkflow:
    pass
```

### Schedule Registry

You can register schedules using the `register` method. 

Schedules should be declared in `schedules.py` module.

```python
from django_temporalio.registry import schedules
from temporalio.client import Schedule


schedules.register("do-cool-stuff-every-hour", Schedule(...))
```

### Heartbeat
Good practice for long-running activities is setting up a `heartbeat_timeout` and calling heartbeat periodically to make sure the activity is still alive.
This can be achieved by setting up providing `heartbeat_timeout` when starting the activity and calling `activity.heartbeat()` directly inside your core logic e.g. on each iteration.
If you encountered a use case where this approach does not fit your design, you can use `heartbeat` contextmanager. It creates a background task utilizing asyncio and calls the heartbeat with defined intervals.

```python
from django_temporalio.utils import heartbeat


@queue_activities.register("MAIN_TASK_QUEUE")
@activity.defn
async def long_running_activity():
    async with heartbeat(timedelta(seconds=10)):
        await count_sheeps()


await workflow.execute_activity(
    long_running_activity,
    start_to_close_timeout=timedelta(minutes=20),
    heartbeat_timeout=timedelta(seconds=30),
)
```

### Activity Failure Logging

The temporalio SDK catches every activity exception to report it to the Temporal server for retry, so 
it never surfaces as an unhandled exception, and the SDK's own log record is a WARNING - below the 
threshold error trackers turn into an alert. An activity failing under an infinite retry policy is 
therefore invisible unless someone checks the Temporal UI.

The package ships `ActivityFailureLoggingInterceptor`, which logs activity failures to the 
`django_temporalio.activity` logger at ERROR level with the full traceback, so error trackers hooked 
into Python logging (e.g. Sentry) pick them up as events. Workers are started with the interceptors 
declared in the `INTERCEPTORS` setting (none by default), followed by any in their `WorkerConfig`:

```python
DJANGO_TEMPORALIO = {
    ...
    "INTERCEPTORS": ["django_temporalio.logs.ActivityFailureLoggingInterceptor"],
}
```

When a failure is logged depends on the activity's retry policy:

- Limited retries (`maximum_attempts` > 0): only the final attempt is logged - earlier failures will 
  be retried and may yet succeed.
- Endless retries (`maximum_attempts` = 0): throttled by attempt number - the attempts listed in 
  `ACTIVITY_FAILURE_LOG_ATTEMPTS`, then every `ACTIVITY_FAILURE_LOG_EVERY`-th attempt (default 
  1, 10, 100, 1000, then every 1000th). Transient errors log at most once, persistent errors keep 
  resurfacing without flooding the logs.
- Non-retryable failures (`ApplicationError(non_retryable=True)` or a type listed in the policy's 
  `non_retryable_error_types`) are final and logged immediately.
- Cancellations and benign application errors are never logged.
- Retries cut off by `schedule_to_close_timeout` are not detectable on the worker - the final 
  attempt of a limited-retry activity may go unlogged when the timeout, not the attempt count, 
  ends the retries.

Each log record carries a `temporal_activity` dict (`activity_id`, `activity_type`, `attempt`, 
`task_queue`, `workflow_id`, `workflow_run_id`, `workflow_type`) in `extra` for structured logging.

To customize the behavior, subclass the interceptor and point the `INTERCEPTORS` setting to your class:

```python
from django_temporalio.logs import ActivityFailureLoggingInterceptor


class MyInterceptor(ActivityFailureLoggingInterceptor):
    def should_log(self, info, err) -> bool:
        if isinstance(err, SomeExpectedError):
            return False
        return super().should_log(info, err)
```

Independently of the interceptor, the SDK logs every failed attempt as a WARNING on the 
`temporalio.activity` logger. If your logging setup routes that logger (or the root logger) to a 
real sink, `django_temporalio.logs.ActivityFailureThrottleFilter` throttles those records with the 
same rules and schedule; the `attempts`/`every` kwargs override the settings per instance 
(`every=0` disables). Records processed outside the activity context (e.g. behind a `QueueHandler`) 
fall back to the attempt schedule:

```python
LOGGING = {
    ...
    "filters": {
        "throttle_activity_failures": {
            "()": "django_temporalio.logs.ActivityFailureThrottleFilter",
            # optionally override the schedule: "attempts": (1, 50), "every": 500,
        },
    },
    "loggers": {
        "temporalio.activity": {
            "handlers": ["console"],
            "level": "WARNING",
            "filters": ["throttle_activity_failures"],
        },
    },
}
```

Records that are not activity failures pass through untouched; the filter identifies them by the 
`__temporal_error_identifier` marker the SDK sets on its failure records.

### Management Commands

To see a queue's registered activities and workflows:

```bash
$ ./manage.py show_temporalio_queue_registry
```

To start a worker defined in the settings (for production):

```bash
$ ./manage.py start_temporalio_worker <worker_name>
```

To start a worker for development (starts a worker for each registered queue, WORKER_CONFIGS setting is ignored):

```bash
$ ./manage.py start_temporalio_worker --all
```

The first SIGINT/SIGTERM triggers a graceful shutdown: the worker stops polling and waits for running
tasks to finish; a second signal stops immediately. Running activities are cancelled after the worker's
`graceful_shutdown_timeout` (0 by default), so set it for long-running activities - and make sure the
process manager's stop timeout exceeds it, or its SIGKILL cuts the shutdown short.

Workers are built and run by `django_temporalio.worker.WorkerRunner` - the command is only a CLI shim.
To customise the behaviour, subclass `WorkerRunner` and point the `WORKER_RUNNER` setting (a dotted
path) at your class.

To sync schedules with Temporal.io:

```bash
$ ./manage.py sync_temporalio_schedules
```

To see what sync operation would do without actually syncing:

```bash
$ ./manage.py sync_temporal_schedules --dry-run
```

## Configuration

You can configure the app using the following settings:

DJANGO_TEMPORALIO: A dictionary containing the following keys:

- CLIENT_CONFIG: A dictionary of kwargs that are passed to the `temporalio.client.Client.connect` 
  method on the client initialization, defaults to `{}`
- WORKER_CONFIGS: A dictionary containing worker configurations. 
  The key is the worker name and the value is a `temporalio.worker.WorkerConfig` instance.
- BASE_MODULE: A python module that holds workflows, activities and schedules, defaults to `None`
- INTERCEPTORS: A list of import strings of `temporalio.worker.Interceptor` classes workers are 
  started with, defaults to `()`
- WORKER_RUNNER: Import string of the `WorkerRunner` subclass used to build and run workers and handle 
  shutdown, defaults to `"django_temporalio.worker.WorkerRunner"`
- ACTIVITY_FAILURE_LOG_ATTEMPTS: Attempt numbers on which an activity failure is logged, 
  defaults to `(1, 10, 100, 1000)`
- ACTIVITY_FAILURE_LOG_EVERY: After the attempts above, log every Nth attempt, 
  set to `None` to disable, defaults to `1000`

## Making a new release

This project makes use of [RegioHelden's reusable GitHub workflows](https://github.com/RegioHelden/github-reusable-workflows). \
Make a new release by manually triggering the `Open release PR` workflow.

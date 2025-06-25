# django-temporalio
___

A small Django app that provides helpers for integrating [Temporal.io](https://temporal.io/) with Django.

## Features

- Registry: Provides a registry that holds mappings between queue names and registered activities and workflows.
- Management Commands: Includes management commands to manage Temporal.io workers and sync schedules.

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

## Making a new release

This project makes use of [RegioHelden's reusable GitHub workflows](https://github.com/RegioHelden/github-reusable-workflows). \
Make a new release by manually triggering the `Open release PR` workflow.

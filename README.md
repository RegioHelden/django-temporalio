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
    "URL": "localhost:7233",
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

### Workflow and Activity Registry

The registry is a singleton that holds mappings between queue names and registered activities and workflows.
You can register activities and workflows using the `register` method. 

Activities and workflows should be declared in `workflows.py` and `activities.py` modules respectively. 

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

- URL: The Temporal.io host to connect to, defaults to `http://localhost:7233`
- NAMESPACE: The Temporal.io namespace to use, defaults to `default`
- WORKER_CONFIGS: A dictionary containing worker configurations. 
  The key is the worker name and the value is a `WorkerConfig` instance.

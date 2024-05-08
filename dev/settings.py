import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "secret-key"
DEBUG = True

INSTALLED_APPS = [
    "dev.apps.DevConfig",
    "django_temporalio.apps.DjangoTemporalioConfig",
]

# use StrEnum in newer python versions
TEST_TASK_QUEUES = {
    "MAIN": "MAIN_TASK_QUEUE",
    "HIGH_PRIORITY": "HIGH_PRIORITY_TASK_QUEUE",
}

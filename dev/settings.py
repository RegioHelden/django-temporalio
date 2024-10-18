import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = "secret-key"
DEBUG = True

INSTALLED_APPS = [
    "dev.apps.DevConfig",
    "django_temporalio.apps.DjangoTemporalioConfig",
]

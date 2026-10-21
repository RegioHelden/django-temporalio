import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "B*7t*&TB*T^*&T67rVC%^$EC$%EC$e45cE$%^E$%e"  # noqa: S105
DEBUG = True

INSTALLED_APPS = [
    "example.apps.ExampleConfig",
    "django_temporalio.apps.DjangoTemporalioConfig",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # a file, since Django never closes an in-memory SQLite connection
        "NAME": Path(tempfile.gettempdir()) / "django_temporalio.sqlite3",
    },
}

"""
Settings for django-temporalio are all namespaced in the DJANGO_TEMPORALIO setting.
For example your project's `settings.py` file might look like this:

DJANGO_TEMPORALIO = {
    # params passed to the `temporalio.client.Client.connect' method
    'CLIENT_CONFIG': {
        'target_host': 'localhost:7233',
    },
}

This module provides the `settings` object, that is used to access
django-temporalio settings, checking for user settings first, then falling
back to the defaults.
"""

from django.conf import settings as django_settings
from django.core.signals import setting_changed
from django.dispatch import receiver

SETTINGS_KEY = "DJANGO_TEMPORALIO"
DEFAULTS = {
    "CLIENT_CONFIG": {},
    "WORKER_CONFIGS": {},
    "BASE_MODULE": None,
}


class SettingIsNotSetError(Exception):
    pass


class Settings:
    def __init__(self):
        self.defaults = DEFAULTS

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(django_settings, SETTINGS_KEY, {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}'")

        if attr in self.user_settings:
            return self.user_settings[attr]

        return self.defaults[attr]

    def reload(self):
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


settings = Settings()


@receiver(setting_changed)
def reload_settings(*args, **kwargs):
    if kwargs["setting"] == SETTINGS_KEY:
        settings.reload()

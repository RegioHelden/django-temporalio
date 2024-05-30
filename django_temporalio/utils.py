import fnmatch
import os
from importlib import import_module

from django_temporalio.conf import settings, SettingIsNotSetError


def autodiscover_modules(related_name_pattern: str):
    """
    Autodiscover modules matching the related name pattern in the base module.

    Example for the following directory structure:

    foo/
        workflows.py
        activities.py
        bar/
            bar_workflows.py
            activities.py
            baz/
                workflows_baz.py
                activities.py

    Calling `autodiscover_modules('foo', '*workflows*')` will discover the following modules:
    - foo.workflows
    - foo.bar.bar_workflows
    - foo.bar.baz.workflows_baz
    """
    base_module_name = settings.BASE_MODULE

    if not base_module_name:
        raise SettingIsNotSetError("BASE_MODULE setting must be set.")

    base_module = import_module(base_module_name)
    base_module_path = base_module.__path__[0]

    for root, _, files in os.walk(base_module_path):
        for file in files:
            if not fnmatch.fnmatch(file, f"{related_name_pattern}.py"):
                continue

            module_name = root.replace(base_module_path, base_module_name).replace(
                os.sep, "."
            )
            # import pdb; pdb.set_trace()
            import_module(f"{module_name}.{file[:-3]}")

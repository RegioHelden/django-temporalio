# -*- coding: UTF-8 -*-
import os

from setuptools import setup, find_packages

import django_temporalio


def read_file(filename):
    try:
        return open(os.path.join(os.path.dirname(__file__), filename)).read()
    except IOError:
        return ""


setup(
    name=django_temporalio.__title__,
    packages=find_packages(exclude=["dev*"]),
    version=django_temporalio.__version__,
    description=django_temporalio.__description__,
    author=django_temporalio.__author__,
    author_email=django_temporalio.__author_email__,
    long_description=(read_file("README.md") + "\n\n" + read_file("CHANGELOG.md")),
    long_description_content_type="text/markdown",
    install_requires=[
        "django>=4.0",
        "temporalio>=1.5.1",
    ],
    license=django_temporalio.__license__,
    url=django_temporalio.__url__,
    download_url="",
    keywords=[
        "django",
        "temporal.io",
        "temporal",
    ],
    include_package_data=True,
    python_requires=">=3.11",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Topic :: Internet :: WWW/HTTP",
    ],
)

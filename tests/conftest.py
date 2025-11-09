# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""
Pytest auto configuration.

This module is run automatically by pytest, to define and enable fixtures.
"""

import re
import warnings

import django.utils.deprecation
import pytest


@pytest.fixture(autouse=True)
def set_warnings():
    """Configure warnings to show while running tests."""
    warnings.simplefilter("default")
    warnings.simplefilter("once", DeprecationWarning)

    # Warnings to suppress:
    # How come these warnings are successfully suppressed here, but not in setup.cfg??

    # We know we do tricky things with Django settings, don't warn us about it.
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=r"Overriding setting DATABASES can lead to unexpected behavior.",
        )

    # Django has warnings like RemovedInDjango40Warning.  We use features that are going to be
    # deprecated, so we don't need to see those warnings. But the specific warning classes change
    # in every release.  Find them and ignore them.
    for name, obj in vars(django.utils.deprecation).items():
        if re.match(r"RemovedInDjango\d+Warning", name):
            warnings.filterwarnings("ignore", category=obj)

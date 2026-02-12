# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""For printing the versions from tox.ini."""

import platform

import coverage
import django

print(
    "{} {}; Django {}; Coverage {}".format(
        platform.python_implementation(),
        platform.python_version(),
        django.get_version(),
        coverage.__version__,
    )
)

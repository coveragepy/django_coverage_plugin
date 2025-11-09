# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""The tests for the Django Coverage Plugin."""

# Define URLs here so we can use ROOT_URLCONF="tests"

try:
    from django.urls import re_path
except ImportError:
    from django.conf.urls import url as re_path


def index(request):
    """A bogus view to use in the urls below."""
    pass


urlpatterns = [
    re_path(r'^home$', index, name='index'),
]

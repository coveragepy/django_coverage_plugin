# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Django Template Coverage Plugin"""

__version__ = "3.2.2"

from .plugin import DjangoTemplatePluginException  # noqa
from .plugin import DjangoTemplatePlugin


def coverage_init(reg, options):
    plugin = DjangoTemplatePlugin(options)
    reg.add_file_tracer(plugin)
    reg.add_configurer(plugin)

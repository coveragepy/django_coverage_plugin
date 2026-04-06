# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests for {# pragma: no cover #} support in Django templates."""

import coverage
from django.template.loader import get_template

from .plugin_test import DjangoPluginTestCase


class PragmaTest(DjangoPluginTestCase):

    def test_pragma_on_block_tag_excludes_entire_block(self):
        for condition in (True, False):
            with self.subTest(condition=condition):
                self.make_template("""\
                    Before
                    {% if condition %}{# pragma: no cover #}
                        {{ content }}
                    {% endif %}
                    After
                    """)
                self.run_django_coverage(context={'condition': condition, 'content': 'hi'})
                self.assert_analysis([1, 5])

    def test_pragma_on_plain_text_line(self):
        self.make_template("""\
            Before
            excluded line {# pragma: no cover #}
            After
            """)
        self.run_django_coverage()
        self.assert_analysis([1, 3])

    def test_pragma_on_non_closing_tag(self):
        """Test that pragma does not treat tags like {% cycle $} as blocks."""
        self.make_template("""\
            <div>
                {% cycle 'a' 'b' as values %}{# pragma: no cover #}
                Covered
                Not covered {{ values|last }}{# pragma: no cover #}
            </div>
            """)
        self.run_django_coverage()
        self.assert_analysis([1, 3, 5])

    def test_pragma_with_nested_blocks(self):
        self.make_template("""\
            Before
            {% if condition %}{# pragma: no cover #}
                {% for item in items %}
                    {{ item }}
                {% endfor %}
            {% endif %}
            After
            """)
        self.run_django_coverage(
            context={'condition': True, 'items': ['a', 'b']},
        )
        self.assert_analysis([1, 7])

    def test_custom_exclude_patterns(self):
        """Test that coverage.py config for report:exclude_lines is used."""
        self.make_template("""\
            Before
            {% if condition %}{# noqa: no-cover #}
                {{ content }}
            {% endif %}
            {% if not condition %} {# this block won't execute #}
                {% now "SHORT_DATETIME_FORMAT" %} {# !SKIP ME! #}
                {% lorem %}{# pragma: no cover #}{# I'm not covered because of custom exclude #}
            {% endif %}
            {% lorem %}{# I'm covered! #}
            After
            """)
        tem = get_template(self.template_file)
        self.cov = coverage.Coverage(source=['.'])
        self.append_config("run:plugins", "django_coverage_plugin")
        # Set the exclude_lines with own patterns.
        self.cov.config.set_option(
            "report:exclude_lines", ["noqa: no-cover", "!SKIP ME!"],
        )
        self.cov.start()
        tem.render({'condition': True, 'content': 'hi'})
        self.cov.stop()
        self.cov.save()
        self.assert_analysis([1, 5, 7, 9, 10], missing=[7])  # Expecting 1 missing line

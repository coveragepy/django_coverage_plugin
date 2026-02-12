# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests of template inheritance for django_coverage_plugin."""

from .plugin_test import DjangoPluginTestCase


class BlockTest(DjangoPluginTestCase):

    def test_empty_block(self):
        self.make_template("""\
            {% block somewhere %}{% endblock %}
            """)

        text = self.run_django_coverage()
        self.assertEqual(text.strip(), '')
        self.assert_analysis([1])

    def test_empty_block_with_text_inside(self):
        self.make_template("""\
            {% block somewhere %}Hello{% endblock %}
            """)

        text = self.run_django_coverage()
        self.assertEqual(text.strip(), 'Hello')
        self.assert_analysis([1])

    def test_empty_block_with_text_outside(self):
        self.make_template("""\
            {% block somewhere %}{% endblock %}
            Hello
            """)

        text = self.run_django_coverage()
        self.assertEqual(text.strip(), 'Hello')
        self.assert_analysis([1, 2])

    def test_two_empty_blocks(self):
        self.make_template("""\
            {% block somewhere %}{% endblock %}
            X
            {% block elsewhere %}{% endblock %}
            Y
            """)

        text = self.run_django_coverage()
        self.assertEqual(text.strip(), 'X\n\nY')
        self.assert_analysis([1, 2, 3, 4])

    def test_inheriting(self):
        self.make_template(name="base.html", text="""\
            Hello
            {% block second_line %}second{% endblock %}
            Goodbye
            """)

        self.make_template(name="specific.html", text="""\
            PROLOG
            {% extends "base.html" %}
            THIS DOESN'T APPEAR
            {% block second_line %}
            SECOND
            {% endblock %}

            THIS WON'T EITHER
            """)

        text = self.run_django_coverage(name="specific.html")
        self.assertEqual(text, "PROLOG\nHello\n\nSECOND\n\nGoodbye\n")
        self.assert_analysis([1, 2, 3], name="base.html")
        self.assert_analysis([1, 2, 5], name="specific.html")

    def test_inheriting_with_unused_blocks(self):
        self.make_template(name="base.html", text="""\
            Hello
            {% block second_line %}second{% endblock %}
            Goodbye
            """)

        self.make_template(name="specific.html", text="""\
            {% extends "base.html" %}

            {% block second_line %}
            SECOND
            {% endblock %}

            {% block sir_does_not_appear_in_this_movie %}
            I was bit by a moose once
            {% endblock %}
            """)

        text = self.run_django_coverage(name="specific.html")
        self.assertEqual(text, "Hello\n\nSECOND\n\nGoodbye\n")
        self.assert_analysis([1, 2, 3], name="base.html")
        self.assert_analysis([1, 4, 8], [8], name="specific.html")


class LoadTest(DjangoPluginTestCase):
    def test_load(self):
        self.make_template(name="load.html", text="""\
            {% load i18n %}

            FIRST
            SECOND
            """)

        text = self.run_django_coverage(name="load.html")
        self.assertEqual(text, "\n\nFIRST\nSECOND\n")
        self.assert_analysis([1, 2, 3, 4], name="load.html")

    def test_load_with_extends(self):
        self.make_template(name="base.html", text="""\
            Hello
            {% block second_line %}second{% endblock %}
            Goodbye
            """)

        self.make_template(name="specific.html", text="""\
            {% extends "base.html" %}
            {% load i18n %}
            {% block second_line %}
            SPECIFIC
            {% endblock %}
            """)

        text = self.run_django_coverage(name="specific.html")
        self.assertEqual(text, "Hello\n\nSPECIFIC\n\nGoodbye\n")
        self.assert_analysis([1, 4], name="specific.html")


class IncludeTest(DjangoPluginTestCase):
    def test_include(self):
        self.make_template(name="outer.html", text="""\
            First
            {% include "nested.html" %}
            Last
            """)

        self.make_template(name="nested.html", text="""\
            Inside
            Job
            """)

        text = self.run_django_coverage(name="outer.html")
        self.assertEqual(text, "First\nInside\nJob\n\nLast\n")
        self.assert_analysis([1, 2, 3], name="outer.html")
        self.assert_analysis([1, 2], name="nested.html")

# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests of i18n tags for django_coverage_plugin."""

from .plugin_test import DjangoPluginTestCase


class I18nTest(DjangoPluginTestCase):
    def test_trans(self):
        self.make_template("""\
            {% load i18n %}
            Hello
            {% trans "World" %}
            done.
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "\nHello\nWorld\ndone.\n")
        self.assert_analysis([1, 2, 3, 4])

    def test_blocktrans(self):
        self.make_template("""\
            {% load i18n %}
            Hello
            {% blocktrans with where="world" %}
            to {{ where }}.
            {% endblocktrans %}
            bye.
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "\nHello\n\nto world.\n\nbye.\n")
        self.assert_analysis([1, 2, 3, 4, 6])

    def test_blocktrans_plural(self):
        self.make_template("""\
            {% load i18n %}
            {% blocktrans count counter=cats|length %}
            There is one cat.
            {% plural %}
            There are {{ counter }} cats.
            {% endblocktrans %}
            bye.
            """)
        # It doesn't make a difference whether you use the plural or not, we
        # can't tell, so the singluar and plural are always marked as used.
        text = self.run_django_coverage(context={"cats": ["snowy"]})
        self.assertEqual(text, "\n\nThere is one cat.\n\nbye.\n")
        self.assert_analysis([1, 2, 3, 4, 5, 7])

        text = self.run_django_coverage(context={"cats": ["snowy", "coaly"]})
        self.assertEqual(text, "\n\nThere are 2 cats.\n\nbye.\n")
        self.assert_analysis([1, 2, 3, 4, 5, 7])

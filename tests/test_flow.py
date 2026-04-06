# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests of control-flow structures for django_coverage_plugin."""

import textwrap

from .plugin_test import DjangoPluginTestCase, squashed


class IfTest(DjangoPluginTestCase):
    def test_if(self):
        self.make_template("""\
            {% if foo %}
            Hello
            {% endif %}
            """)

        text = self.run_django_coverage(context={"foo": True})
        self.assertEqual(text.strip(), "Hello")
        self.assert_analysis([1, 2])

        text = self.run_django_coverage(context={"foo": False})
        self.assertEqual(text.strip(), "")
        self.assert_analysis([1, 2], [2])

    def test_endif_not_at_start_of_line(self):
        self.make_template("""\
            <article>
              {% if foo %}
                Hello
              {% endif %}
              After
            </article>
            """)
        self.run_django_coverage(context={"foo": False})
        self.assert_analysis([1, 2, 3, 5, 6], missing=[3])

    def test_else_not_at_start_of_line(self):
        self.make_template("""\
            <article>
              {% if foo %}
                Hello
              {% else %}
                Goodbye
              {% endif %}
            </article>
            """)
        self.run_django_coverage(context={"foo": True})
        self.assert_analysis([1, 2, 3, 5, 7], missing=[5])

    def test_if_else(self):
        self.make_template("""\
            {% if foo %}
            Hello
            {% else %}
            Goodbye
            {% endif %}
            """)

        text = self.run_django_coverage(context={"foo": True})
        self.assertEqual(text.strip(), "Hello")
        self.assert_analysis([1, 2, 4], [4])

        text = self.run_django_coverage(context={"foo": False})
        self.assertEqual(text.strip(), "Goodbye")
        self.assert_analysis([1, 2, 4], [2])

    def test_if_elif_else(self):
        self.make_template("""\
            {% if foo %}
            Hello
            {% elif bar %}
            Aloha
            {% else %}
            Goodbye
            {% endif %}
            """)

        text = self.run_django_coverage(context={"foo": True, "bar": False})
        self.assertEqual(text.strip(), "Hello")
        self.assert_analysis([1, 2, 4, 6], [4, 6])

        text = self.run_django_coverage(context={"foo": False, "bar": True})
        self.assertEqual(text.strip(), "Aloha")
        self.assert_analysis([1, 2, 4, 6], [2, 6])

        text = self.run_django_coverage(context={"foo": False, "bar": False})
        self.assertEqual(text.strip(), "Goodbye")
        self.assert_analysis([1, 2, 4, 6], [2, 4])


class LoopTest(DjangoPluginTestCase):
    def test_loop(self):
        self.make_template("""\
            Before
            {% for item in items %}
            {% cycle "-" "+" %}{{ item }}
            {% endfor %}
            After
            """)

        text = self.run_django_coverage(context={"items": "ABC"})
        self.assertEqual(text, "Before\n\n-A\n\n+B\n\n-C\n\nAfter\n")
        self.assert_analysis([1, 2, 3, 5])

        text = self.run_django_coverage(context={"items": ""})
        self.assertEqual(text, "Before\n\nAfter\n")
        self.assert_analysis([1, 2, 3, 5], [3])

    def test_endfor_not_at_start_of_line(self):
        self.make_template("""\
            <ul>
              {% for item in items %}
                <li>{{ item }}</li>
              {% endfor %}
            </ul>
            """)
        self.run_django_coverage(context={"items": []})
        self.assert_analysis([1, 2, 3, 5], missing=[3])

    def test_loop_with_empty_clause(self):
        self.make_template("""\
            Before
            {% for item in items %}
            -{{ item }}
            {% empty %}
            NONE
            {% endfor %}
            After
            """)

        text = self.run_django_coverage(context={"items": "ABC"})
        self.assertEqual(text, "Before\n\n-A\n\n-B\n\n-C\n\nAfter\n")
        self.assert_analysis([1, 2, 3, 5, 7], [5])

        text = self.run_django_coverage(context={"items": ""})
        self.assertEqual(text, "Before\n\nNONE\n\nAfter\n")
        self.assert_analysis([1, 2, 3, 5, 7], [3])

    def test_regroup(self):
        self.make_template("""\
            {% spaceless %}
            {% regroup cities by country as country_list %}
            <ul>
            {% for country in country_list %}
                <li>{{ country.grouper }}
                <ul>
                    {% for item in country.list %}
                    <li>{{ item.name }}: {{ item.population }}</li>
                    {% endfor %}
                </ul>
                </li>
            {% endfor %}
            </ul>
            {% endspaceless %}
            """)
        text = self.run_django_coverage(
            context={
                "cities": [
                    {"name": "Mumbai", "population": "19", "country": "India"},
                    {"name": "Calcutta", "population": "15", "country": "India"},
                    {"name": "New York", "population": "20", "country": "USA"},
                    {"name": "Chicago", "population": "7", "country": "USA"},
                    {"name": "Tokyo", "population": "33", "country": "Japan"},
                ],
            }
        )
        self.assertEqual(
            text,
            textwrap.dedent("""\
            <ul><li>India
                <ul><li>Mumbai: 19</li><li>Calcutta: 15</li></ul></li><li>USA
                <ul><li>New York: 20</li><li>Chicago: 7</li></ul></li><li>Japan
                <ul><li>Tokyo: 33</li></ul></li></ul>
            """),
        )
        self.assert_analysis([1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 13])


class IfChangedTest(DjangoPluginTestCase):
    def test_ifchanged(self):
        self.make_template("""\
            {% for a,b in items %}
                {% ifchanged %}
                    {{ a }}
                {% endifchanged %}
                {{ b }}
            {% endfor %}
            """)

        text = self.run_django_coverage(
            context={
                "items": [("A", "X"), ("A", "Y"), ("B", "Z"), ("B", "W")],
            }
        )
        self.assertEqual(squashed(text), "AXYBZW")
        self.assert_analysis([1, 2, 3, 5])

    def test_ifchanged_variable(self):
        self.make_template("""\
            {% for a,b in items %}
                {% ifchanged a %}
                    {{ a }}
                {% endifchanged %}
                {{ b }}
            {% endfor %}
            """)

        text = self.run_django_coverage(
            context={
                "items": [("A", "X"), ("A", "Y"), ("B", "Z"), ("B", "W")],
            }
        )
        self.assertEqual(squashed(text), "AXYBZW")
        self.assert_analysis([1, 2, 3, 5])

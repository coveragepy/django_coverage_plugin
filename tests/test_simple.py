# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Simple tests for django_coverage_plugin."""

from .plugin_test import DjangoPluginTestCase

# 200 Unicode chars: snowman + poo.
UNIUNI = "\u26C4\U0001F4A9"*100
if isinstance(UNIUNI, str):
    UNISTR = UNIUNI
else:
    UNISTR = UNIUNI.encode("utf8")


class SimpleTemplateTest(DjangoPluginTestCase):

    def test_one_line(self):
        self.make_template('Hello')
        text = self.run_django_coverage()
        self.assertEqual(text, 'Hello')
        self.assert_analysis([1])

    def test_plain_text(self):
        self.make_template('Hello\nWorld\n\nGoodbye')
        text = self.run_django_coverage()
        self.assertEqual(text, 'Hello\nWorld\n\nGoodbye')
        self.assert_analysis([1, 2, 3, 4])

    def test_variable(self):
        self.make_template("""\
            Hello, {{name}}
            """)
        text = self.run_django_coverage(context={'name': 'John'})
        self.assertEqual(text, "Hello, John\n")
        self.assert_analysis([1])

    def test_variable_on_second_line(self):
        self.make_template("""\
            Hello,
            {{name}}
            """)
        text = self.run_django_coverage(context={'name': 'John'})
        self.assertEqual(text, "Hello,\nJohn\n")
        self.assert_analysis([1, 2])

    def test_lone_variable(self):
        self.make_template("""\
            {{name}}
            """)
        text = self.run_django_coverage(context={'name': 'John'})
        self.assertEqual(text, "John\n")
        self.assert_analysis([1])

    def test_long_text(self):
        self.make_template("line\n"*50)
        text = self.run_django_coverage()
        self.assertEqual(text, "line\n"*50)
        self.assert_analysis(list(range(1, 51)))

    def test_non_ascii(self):
        self.make_template("""\
            υηιcσɗє ιѕ тяιcку
            {{more}}!
            """)
        text = self.run_django_coverage(context={'more': 'ɘboɔinU'})
        self.assertEqual(text, 'υηιcσɗє ιѕ тяιcку\nɘboɔinU!\n')
        self.assert_analysis([1, 2])
        self.assertEqual(self.get_html_report(), 100)
        self.assertEqual(self.get_xml_report(), 100)


class CommentTest(DjangoPluginTestCase):

    def test_simple(self):
        self.make_template("""\
            First
            {% comment %}
                ignore this
            {% endcomment %}
            Last
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "First\n\nLast\n")
        self.assert_analysis([1, 2, 5])

    def test_with_stuff_inside(self):
        self.make_template("""\
            First
            {% comment %}
                {% if foo %}
                    {{ foo }}
                {% endif %}
            {% endcomment %}
            Last
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "First\n\nLast\n")
        self.assert_analysis([1, 2, 7])

    def test_inline_comment(self):
        self.make_template("""\
            First
            {# disregard all of this #}
            Last
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "First\n\nLast\n")
        self.assert_analysis([1, 3])


class OtherTest(DjangoPluginTestCase):
    """Tests of miscellaneous tags."""

    def test_autoescape(self):
        self.make_template("""\
            First
            {% autoescape on %}
            {{ body }}
            {% endautoescape %}
            {% autoescape off %}
            {{ body }}
            {% endautoescape %}
            Last
            """)
        text = self.run_django_coverage(context={'body': '<Hello>'})
        self.assertEqual(text, "First\n\n&lt;Hello&gt;\n\n\n<Hello>\n\nLast\n")
        self.assert_analysis([1, 2, 3, 5, 6, 8])

    def test_filter(self):
        self.make_template("""\
            First
            {% filter force_escape|lower %}
                LOOK: 1 < 2
            {% endfilter %}
            Last
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "First\n\n    look: 1 &lt; 2\n\nLast\n")
        self.assert_analysis([1, 2, 3, 5])

    def test_firstof(self):
        self.make_template("""\
            {% firstof var1 var2 var3 "xyzzy" %}
            {% firstof var2 var3 "plugh" %}
            {% firstof var3 "quux" %}
            """)
        text = self.run_django_coverage(context={'var1': 'A'})
        self.assertEqual(text, "A\nplugh\nquux\n")
        self.assert_analysis([1, 2, 3])

        text = self.run_django_coverage(context={'var2': 'B'})
        self.assertEqual(text, "B\nB\nquux\n")
        self.assert_analysis([1, 2, 3])

    def test_lorem(self):
        self.make_template("""\
            First
            {% lorem 3 w %}
            Last
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "First\nlorem ipsum dolor\nLast\n")
        self.assert_analysis([1, 2, 3])

    def test_now(self):
        self.make_template("""\
            Now:
            {% now "\\n\\o\\w" %}
            .
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "Now:\nnow\n.\n")
        self.assert_analysis([1, 2, 3])

    def test_now_as(self):
        self.make_template("""\
            {% now "\\n\\o\\w" as right_now %}
            Now it's {{ right_now }}.
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "\nNow it's now.\n")
        self.assert_analysis([1, 2])

    def test_templatetag(self):
        self.make_template("""\
            {% templatetag openblock %}
            url 'entry_list'
            {% templatetag closeblock %}
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "{%\nurl 'entry_list'\n%}\n")
        self.assert_analysis([1, 2, 3])

    def test_url(self):
        self.make_template("""\
            {% url 'index' %}
            nice.
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "/home\nnice.\n")
        self.assert_analysis([1, 2])

    def test_verbatim(self):
        self.make_template("""\
            1
            {% verbatim %}
            {{if dying}}Alive.{{/if}}
            second.
            {%third%}.UNISTR
            {% endverbatim %}
            7
            """.replace("UNISTR", UNISTR))
        text = self.run_django_coverage()
        self.assertEqual(
            text,
            "1\n\n{{if dying}}Alive.{{/if}}\nsecond.\n"
            "{%third%}.UNIUNI\n\n7\n".replace("UNIUNI", UNIUNI)
        )
        self.assert_analysis([1, 2, 3, 4, 5, 7])

    def test_widthratio(self):
        self.make_template("""\
            {% widthratio 175 200 100 %}
            == 88
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "88\n== 88\n")
        self.assert_analysis([1, 2])

    def test_with(self):
        self.make_template("""\
            {% with alpha=1 beta=2 %}
            alpha = {{ alpha }}, beta = {{ beta }}.
            {% endwith %}
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "\nalpha = 1, beta = 2.\n\n")
        self.assert_analysis([1, 2])

    def test_endwith_not_at_start_of_line(self):
        self.make_template("""\
            <div>
              {% with alpha=1 %}
                {{ alpha }}
              {% endwith %}
            </div>
            """)
        self.run_django_coverage()
        self.assert_analysis([1, 2, 3, 5])


class StringTemplateTest(DjangoPluginTestCase):

    run_in_temp_dir = False

    def test_string_template(self):
        # I don't understand why coverage 6 warns about no data,
        # but coverage 5 does not.
        with self.assert_no_data(min_cov=(6, 0)):
            text = self.run_django_coverage(
                text="Hello, {{name}}!",
                context={'name': 'World'},
                options={},
                )
        self.assertEqual(text, "Hello, World!")


class BranchTest(DjangoPluginTestCase):

    def test_with_branch_enabled(self):
        self.make_template('Hello\nWorld\n\nGoodbye')
        text = self.run_django_coverage(
            options={'source': ["."], 'branch': True}
            )
        self.assertEqual(text, 'Hello\nWorld\n\nGoodbye')
        self.assert_analysis([1, 2, 3, 4])


class ExcludeTest(DjangoPluginTestCase):
    """Tests of excluding block tokens by regex."""

    def test_exclude_block(self):
        self.make_template("""\
            First
            {% with foo='bar' %}
                {{ foo }}
            {% endwith %}
            Last
            """)
        text = self.run_django_coverage()
        self.assertEqual(text, "First\n\n    bar\n\nLast\n")
        self.assert_analysis([1, 2, 3, 5])

        self.make_file(".coveragerc", """\
            [run]
            plugins = django_coverage_plugin
            [django_coverage_plugin]
            exclude_blocks = [".+foo.+"]
            """)

        text = self.run_django_coverage()
        self.assertEqual(text, "First\n\n    bar\n\nLast\n")
        self.assert_analysis([1, 3, 5])

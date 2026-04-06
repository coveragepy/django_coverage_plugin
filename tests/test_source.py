# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests of template inheritance for django_coverage_plugin."""

import os

try:
    from coverage.exceptions import NoSource
except ImportError:
    # for coverage 5.x
    from coverage.misc import NoSource

from .plugin_test import DjangoPluginTestCase


class FindSourceTest(DjangoPluginTestCase):
    def test_finding_source(self):
        # This is a template that is rendered.
        self.make_template(name="main.html", text="Hello")
        # These are templates that aren't rendered, but are considered renderable.
        self.make_template(name="unused.html", text="Not used")
        self.make_template(name="unused.htm", text="Not used")
        self.make_template(name="unused.txt", text="Not used")
        # These are things left behind by an editor.
        self.make_template(name="~unused.html", text="junk")
        self.make_template(name="unused=.html", text="junk")
        self.make_template(name="unused.html,", text="junk")
        # This is some other file format we don't recognize.
        self.make_template(name="phd.tex", text="Too complicated to read")

        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        # The rendered file has data, and was measured.
        self.assert_analysis([1], name="main.html")
        # The unrendered files have data, and were not measured.
        self.assert_analysis([1], name="unused.html", missing=[1])
        self.assert_analysis([1], name="unused.htm", missing=[1])
        self.assert_analysis([1], name="unused.txt", missing=[1])
        # The editor leave-behinds are not in the measured files.
        self.assert_measured_files("main.html", "unused.html", "unused.htm", "unused.txt")

    def test_customized_extensions(self):
        self.make_file(
            ".coveragerc",
            """\
            [run]
            plugins = django_coverage_plugin
            [django_coverage_plugin]
            template_extensions = html, tex
            """,
        )
        # This is a template that is rendered.
        self.make_template(name="main.html", text="Hello")
        # These are templates that aren't rendered, but are considered renderable.
        self.make_template(name="unused.html", text="Not used")
        self.make_template(name="phd.tex", text="Too complicated to read")
        # These are things left behind by an editor.
        self.make_template(name="~unused.html", text="junk")
        self.make_template(name="unused=.html", text="junk")
        self.make_template(name="unused.html,", text="junk")
        # This is some other file format we don't recognize.
        self.make_template(name="unused.htm", text="Not used")
        self.make_template(name="unused.txt", text="Not used")

        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        # The rendered file has data, and was measured.
        self.assert_analysis([1], name="main.html")
        # The unrendered files have data, and were not measured.
        self.assert_analysis([1], name="unused.html", missing=[1])
        self.assert_analysis([1], name="phd.tex", missing=[1])
        # The editor leave-behinds are not in the measured files.
        self.assert_measured_files("main.html", "unused.html", "phd.tex")

    def test_non_utf8_error(self):
        # A non-UTF8 text file will raise an error.
        self.make_file(
            ".coveragerc",
            """\
            [run]
            plugins = django_coverage_plugin
            source = .
            """,
        )
        # This is a template that is rendered.
        self.make_template(name="main.html", text="Hello")
        # Extra file containing a word encoded in CP-1252
        self.make_file(self._path("static/changelog.txt"), bytes=b"sh\xf6n")

        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        self.assert_measured_files("main.html", f"static{os.sep}changelog.txt")
        self.assert_analysis([1], name="main.html")
        with self.assertRaisesRegex(NoSource, r"changelog.txt.*invalid start byte"):
            self.cov.html_report()

    def test_non_utf8_omitted(self):
        # If we omit the directory with the non-UTF8 file, all is well.
        self.make_file(
            ".coveragerc",
            """\
            [run]
            plugins = django_coverage_plugin
            source = .
            [report]
            omit = */static/*
            """,
        )
        # This is a template that is rendered.
        self.make_template(name="main.html", text="Hello")
        # Extra file containing a word encoded in CP-1252
        self.make_file(self._path("static/changelog.txt"), bytes=b"sh\xf6n")

        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        self.assert_measured_files("main.html", f"static{os.sep}changelog.txt")
        self.assert_analysis([1], name="main.html")
        self.cov.html_report()

    def test_non_utf8_ignored(self):
        # If we ignore reporting errors, a non-UTF8 text file is fine.
        self.make_file(
            ".coveragerc",
            """\
            [run]
            plugins = django_coverage_plugin
            source = .
            [report]
            ignore_errors = True
            """,
        )
        # This is a template that is rendered.
        self.make_template(name="main.html", text="Hello")
        # Extra file containing a word encoded in CP-1252
        self.make_file(self._path("static/changelog.txt"), bytes=b"sh\xf6n")

        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        self.assert_measured_files("main.html", f"static{os.sep}changelog.txt")
        self.assert_analysis([1], name="main.html")
        warn_msg = (
            "'utf-8' codec can't decode byte 0xf6 in position 2: "
            + "invalid start byte (couldnt-parse)"
        )
        with self.assert_coverage_warnings(warn_msg, min_cov=(6, 0)):
            self.cov.html_report()

    def test_htmlcov_isnt_measured(self):
        # We used to find the HTML report and think it was template files.
        self.make_file(
            ".coveragerc",
            """\
            [run]
            plugins = django_coverage_plugin
            source = .
            """,
        )
        self.make_template(name="main.html", text="Hello")
        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        self.assert_measured_files("main.html")
        self.cov.html_report()

        # Run coverage again with an HTML report on disk.
        text = self.run_django_coverage(name="main.html")
        self.assert_measured_files("main.html")

    def test_custom_html_report_isnt_measured(self):
        # We used to find the HTML report and think it was template files.
        self.make_file(
            ".coveragerc",
            """\
            [run]
            plugins = django_coverage_plugin
            source = .
            [html]
            directory = my_html_report
            """,
        )
        self.make_template(name="main.html", text="Hello")
        text = self.run_django_coverage(name="main.html")
        self.assertEqual(text, "Hello")

        self.assert_measured_files("main.html")
        self.cov.html_report()

        # Run coverage again with an HTML report on disk.
        text = self.run_django_coverage(name="main.html")
        self.assert_measured_files("main.html")

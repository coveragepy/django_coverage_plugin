# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests of HTML reporting for django_coverage_plugin."""

import glob

from .plugin_test import DjangoPluginTestCase


class HtmlTest(DjangoPluginTestCase):

    def test_simple(self):
        self.make_template("""\
            Simple © 2015
            """)

        self.run_django_coverage()
        self.cov.html_report()
        html_file = glob.glob("htmlcov/*_test_simple_html.html")[0]
        with open(html_file) as fhtml:
            html = fhtml.read()
        self.assertIn('<span class="txt">Simple &#169; 2015</span>', html)

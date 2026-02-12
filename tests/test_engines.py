# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

"""Tests of multiple engines for django_coverage_plugin."""

from django.test import modify_settings

from .plugin_test import DjangoPluginTestCase


class MultipleEngineTests(DjangoPluginTestCase):
    def setUp(self):
        super().setUp()

        engine = {
            'NAME': 'other',
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': ['templates2'],         # where the tests put things.
            'OPTIONS': {
                'debug': True,
            },
        }
        modified_settings = modify_settings(TEMPLATES={'append': [engine]})
        modified_settings.enable()
        self.addCleanup(modified_settings.disable)

        self.template_directory = 'templates2'

    def test_file_template(self):
        self.make_template('Hello')
        text = self.run_django_coverage(using='other')
        self.assertEqual(text, 'Hello')
        self.assert_analysis([1])

    def test_string_template(self):
        with self.assert_no_data():
            text = self.run_django_coverage(text='Hello', using='other')
        self.assertEqual(text, 'Hello')

    def test_third_engine_not_debug(self):
        engine3 = {
            'NAME': 'notdebug',
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': ['templates3'],         # where the tests put things.
        }
        modified_settings = modify_settings(TEMPLATES={'append': [engine3]})
        modified_settings.enable()
        self.addCleanup(modified_settings.disable)

        self.make_template('Hello')
        with self.assert_plugin_disabled("Template debugging must be enabled in settings."):
            self.run_django_coverage()

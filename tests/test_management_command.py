# -*- coding: utf-8 -*-
import logging
import os
import sys

from django.core.management import (
    call_command, find_commands, load_command_class,
)
from django.test import TestCase

from django_extensions.compat import StringIO, importlib


class MockLoggingHandler(logging.Handler):
    """ Mock logging handler to check for expected logs. """

    def __init__(self, *args, **kwargs):
        self.reset()
        logging.Handler.__init__(self, *args, **kwargs)

    def emit(self, record):
        self.messages[record.levelname.lower()].append(record.getMessage())

    def reset(self):
        self.messages = {
            'debug': [],
            'info': [],
            'warning': [],
            'error': [],
            'critical': [],
        }


class CommandTest(TestCase):
    def test_error_logging(self):
        # Ensure command errors are properly logged and reraised
        from django_extensions.management.base import logger
        logger.addHandler(MockLoggingHandler())
        module_path = "tests.management.commands.error_raising_command"
        module = importlib.import_module(module_path)
        error_raising_command = module.Command()
        self.assertRaises(Exception, error_raising_command.execute)
        handler = logger.handlers[0]
        self.assertEqual(len(handler.messages['error']), 1)


class ShowTemplateTagsTests(TestCase):
    def test_some_output(self):
        out = StringIO()
        call_command('show_templatetags', stdout=out)
        output = out.getvalue()
        # Once django_extension is installed during tests it should appear with
        # its templatetags
        self.assertIn('django_extensions', output)
        # let's check at least one
        self.assertIn('truncate_letters', output)


class UpdatePermissionsTests(TestCase):
    def test_works(self):
        from django.db import models

        class PermModel(models.Model):
            class Meta:
                app_label = 'django_extensions'
                permissions = (('test_permission', 'test_permission'),)

        original_stdout = sys.stdout
        out = sys.stdout = StringIO()
        call_command('update_permissions', stdout=out, verbosity=3)
        sys.stdout = original_stdout
        self.assertIn("Can change perm model", out.getvalue())


class CommandSignalTests(TestCase):
    pre = None
    post = None

    def test_works(self):
        from django_extensions.management.signals import post_command, \
            pre_command
        from django_extensions.management.commands.show_templatetags import \
            Command

        def pre(sender, **kwargs):
            CommandSignalTests.pre = dict(**kwargs)

        def post(sender, **kwargs):
            CommandSignalTests.post = dict(**kwargs)

        pre_command.connect(pre, Command)
        post_command.connect(post, Command)

        out = StringIO()
        call_command('show_templatetags', stdout=out)

        self.assertIn('args', CommandSignalTests.pre)
        self.assertIn('kwargs', CommandSignalTests.pre)

        self.assertIn('args', CommandSignalTests.post)
        self.assertIn('kwargs', CommandSignalTests.post)
        self.assertIn('outcome', CommandSignalTests.post)


class CommandClassTests(TestCase):
    """Try to load every management command to catch exceptions."""
    def test_load_commands(self):
        try:
            management_dir = os.path.join('django_extensions', 'management')
            commands = find_commands(management_dir)
            for command in commands:
                load_command_class('django_extensions', command)
        except Exception as e:
            self.fail("Can't load command class of {0}\n{1}".format(command, e))

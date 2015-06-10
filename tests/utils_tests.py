"""
Utility Tests

"""
try:
    import unittest2 as unittest
except ImportError:
    import unittest

from formulary import utils


class TestPortParsing(unittest.TestCase):

    def test_as_integer_value(self):
        self.assertEqual(('tcp', 80, 80), utils.parse_port_value(80))

    def test_as_string_value_with_protocol(self):
        self.assertEqual(('udp', 53, 53), utils.parse_port_value('53/UDP'))

    def test_as_port_range(self):
        self.assertEqual(('tcp', 1024, 65535),
                         utils.parse_port_value('1024-65535'))

    def test_as_port_range_with_protocol(self):
        self.assertEqual(('tcp', 1024, 65535),
                         utils.parse_port_value('1024/TCP-65535/UDP'))


class TestCamelCase(unittest.TestCase):

    def test_underscore_delimited(self):
        self.assertEqual('FooBarBaz', utils.camel_case('foo_bar_baz'))

    def test_dash_delimited(self):
        self.assertEqual('FooBarBaz', utils.camel_case('foo-bar-baz'))

    def test_mix_delimiters(self):
        self.assertEqual('FooBarBaz', utils.camel_case('foo_bar-baz'))

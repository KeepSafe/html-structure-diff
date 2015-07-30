from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff import parser, tree_utils
from sdiff.model import *

class TestParser(TestCase):
    def _run_and_assert(self, data, expected):
        #TODO arghhhh flatten, better to check the tree but flatten makes it so easy
        actual = tree_utils.flatten(parser.parse(data))
        self.assertEqual(expected, actual)

    def test_empty(self):
        self._run_and_assert('', '')

    def test_header(self):
        self._run_and_assert('###header', 'ht')

    def test_header_in_list(self):
        self._run_and_assert('1. ###header\n2. ###header', 'lmhtmht')

    def test_link(self):
        self._run_and_assert('[link](url)', 'pa')

    def test_broken_link_space(self):
        self._run_and_assert('[link] (http://www.google.com)', 'ptt')

    def test_broken_link_new_line(self):
        self._run_and_assert('[link]\n(http://www.google.com)', 'ptt')

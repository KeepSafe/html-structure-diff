from unittest import TestCase, skip
from unittest.mock import MagicMock, patch

from sdiff import parser, tree_utils
from sdiff.model import *

import re

class TestParser(TestCase):
    def _run_and_assert(self, data, expected):
        #TODO arghhhh flatten, better to check the tree but flatten makes it so easy
        actual = tree_utils.flatten(parser.parse(data))
        self.assertEqual(expected, actual)

    def test_empty(self):
        self._run_and_assert('', '')

    def test_header(self):
        self._run_and_assert('###header', '3t')

    def test_header_in_list(self):
        self._run_and_assert('1. ###header\n2. ###header', 'lm3tm3t')

    def test_link(self):
        self._run_and_assert('[link](url)', 'pt')

    def test_image(self):
        self._run_and_assert('![Alt text][url/to/image]', 'pi')

    def test_broken_link_space(self):
        self._run_and_assert('[link] (http://www.google.com)', 'pt')

    def test_broken_link_new_line(self):
        self._run_and_assert('[link]\n(http://www.google.com)', 'pt')

    def test_single_quote(self):
        self._run_and_assert('code d\\\'acti & vation', 'pt')

    def test_exclamation_mark(self):
        self._run_and_assert('Danke!', 'pt')
        
    def test_escape_html(self):
        actual = parser.parse('<sub>text</sub>')
        self.assertEqual('&lt;sub&gt;text&lt;/sub&gt;', actual[0].nodes[0].text)

    @skip('this should return a new paragraph but with the current mistune regular expressions it is too hard')
    def test_ignore_single_space(self):
        self._run_and_assert('test\n \ntest', 'ptpt')
        
    def test_ignore_tailing_new_line(self):
        self._run_and_assert('[link](url)\n ', 'pt')
        
    def test_space_new_line_saparated_as_single_text(self):
        self._run_and_assert('<!-- TODO local on badges and iOS link --> \n<span id="appstore_badge">', 'pt')
        
    def test_lheading_text(self):
        actual = parser.parse('heading\n=============')
        self.assertEqual('heading', actual[0].nodes[0].text)
        
    def test_heading_text(self):
        actual = parser.parse('###heading')
        self.assertEqual('heading', actual[0].nodes[0].text)


class TestReplaceLines(TestCase):
    def test_single_empty_line(self):
        text = '  '
        actual = parser._remove_spaces_from_empty_lines(text)
        self.assertEqual('\n', actual)
        
    def test_many_empty_line(self):
        text = '  \n \n   \n\n'
        actual = parser._remove_spaces_from_empty_lines(text)
        self.assertEqual('\n\n\n\n\n\n', actual)
        
    def test_leave_spaces_with_text(self):
        text = 'test  \n  test'
        actual = parser._remove_spaces_from_empty_lines(text)
        self.assertEqual(text, actual)
        
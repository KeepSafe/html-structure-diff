from unittest import TestCase, skip
from unittest.mock import MagicMock, patch

from sdiff.compare import diff_links, diff_struct
from sdiff.parser import parse
from sdiff.errors import DeleteError, InsertError
from .fixtures import trees


class TestLinks(TestCase):
    def test_no_links(self):
        _, _, actual = diff_links(trees.paragraph, trees.paragraph)
        self.assertEqual([], actual)

    def test_equal_links(self):
        _, _, actual = diff_links(trees.paragraph_link, trees.paragraph_link)
        self.assertEqual([], actual)

    def test_not_equal_links(self):
        _, _, actual = diff_links(trees.paragraph_link, trees.paragraph_link_link)
        self.assertEqual('dummy link 2', actual[0].node.text)


class TestEqual(TestCase):
    def test_single_header(self):
        _, _, errors = diff_struct(trees.header, trees.header)
        self.assertEqual([], errors)

    def test_single_paragraph(self):
        _, _, errors = diff_struct(trees.paragraph, trees.paragraph)
        self.assertEqual([], errors)

    def test_link_in_paragraph(self):
        _, _, errors = diff_struct(trees.paragraph_text_link_text, trees.paragraph_text_link_text)
        self.assertEqual([], errors)

    def test_header_in_list(self):
        _, _, errors = diff_struct(trees.list_header_header, trees.list_header_header)
        self.assertEqual([], errors)

class TestDifferent(TestCase):
    def test_no_header(self):
        _, _, errors = diff_struct(trees.header, trees.paragraph)
        self.assertEqual('del', errors[0].node.meta['style'])
        self.assertEqual(2, errors[0].node.level)
        self.assertEqual('ins', errors[1].node.meta['style'])

    def test_different_header(self):
        _, _, errors = diff_struct(trees.header, trees.header_small)
        self.assertEqual(2, errors[0].node.level)
        self.assertEqual('del', errors[0].node.meta['style'])
        self.assertEqual(4, errors[1].node.level)
        self.assertEqual('ins', errors[1].node.meta['style'])

    def test_missing_new_line(self):
        _, _, errors = diff_struct(trees.paragraph, trees.paragraph_text_newline_text)
        self.assertEqual('n', errors[0].node.symbol)
        self.assertEqual('text', errors[1].node.text)

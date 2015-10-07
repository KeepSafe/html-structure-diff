from unittest import TestCase, skip
from unittest.mock import MagicMock, patch

from sdiff.compare import diff_links, diff_struct
from sdiff.parser import parse
from sdiff.errors import DeleteError, InsertError
from .fixtures import trees


class TestLinks(TestCase):

    def test_no_links(self):
        _, _, actual = diff_links(trees.pt(), trees.pt())
        self.assertEqual([], actual)

    def test_equal_links(self):
        _, _, actual = diff_links(trees.pa(), trees.pa())
        self.assertEqual([], actual)

    def test_not_equal_links(self):
        _, _, actual = diff_links(trees.pa(), trees.paa())
        self.assertEqual('dummy link 2', actual[0].node.text)


class TestEqual(TestCase):

    def test_single_header(self):
        _, _, errors = diff_struct(trees.r2t(), trees.r2t())
        self.assertEqual([], errors)

    def test_single_paragraph(self):
        _, _, errors = diff_struct(trees.pt(), trees.pt())
        self.assertEqual([], errors)

    def test_link_in_paragraph(self):
        _, _, errors = diff_struct(trees.ptat(), trees.ptat())
        self.assertEqual([], errors)

    def test_header_in_list(self):
        _, _, errors = diff_struct(trees.lm2tm2t(), trees.lm2tm2t())
        self.assertEqual([], errors)

    def test_concatenate_text_nodes_when_element_in_middle_ignored(self):
        _, _, errors = diff_struct(trees.ptat(), trees.pt())
        self.assertEqual([], errors)


class TestDifferent(TestCase):

    def test_no_header(self):
        _, _, errors = diff_struct(trees.r2t(), trees.pt())
        self.assertEqual('del', errors[0].node.meta['style'])
        self.assertEqual(2, errors[0].node.level)
        self.assertEqual('ins', errors[1].node.meta['style'])

    def test_different_header(self):
        _, _, errors = diff_struct(trees.r2t(), trees.r4t())
        self.assertEqual(2, errors[0].node.level)
        self.assertEqual('del', errors[0].node.meta['style'])
        self.assertEqual(4, errors[1].node.level)
        self.assertEqual('ins', errors[1].node.meta['style'])

    def test_missing_new_line(self):
        _, _, errors = diff_struct(trees.pt(), trees.ptnt())
        self.assertEqual('n', errors[0].node.symbol)
        self.assertEqual('text', errors[1].node.text)

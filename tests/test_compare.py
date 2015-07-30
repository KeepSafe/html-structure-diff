from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff import compare
from sdiff.parser import parse
from sdiff.errors import ReplaceError, DeleteError, InsertError
from pprint import pprint

class TestEqual(TestCase):
    def test_single_header(self):
        text = '#h'
        tree1 = parse(text)
        tree2 = parse(text)
        errors = compare(tree1, tree2)
        self.assertEqual([], errors)

    def test_single_paragraph(self):
        text = 'test'
        tree1 = parse(text)
        tree2 = parse(text)
        errors = compare(tree1, tree2)
        self.assertEqual([], errors)

    def test_link_in_paragraph(self):
        text = 'test [link](url)'
        tree1 = parse(text)
        tree2 = parse(text)
        errors = compare(tree1, tree2)
        self.assertEqual([], errors)

    def test_header_in_list(self):
        text = '1. ###header\n2. ###header'
        tree1 = parse(text)
        tree2 = parse(text)
        errors = compare(tree1, tree2)
        self.assertEqual([], errors)

class TestDifferent(TestCase):
    def test_no_header(self):
        tree1 = parse('#h')
        tree2 = parse('h')
        errors = compare(tree1, tree2)
        self.assertIsInstance(errors[0], ReplaceError)

    def _test_different_header(self):
        tree1 = parse('#h')
        tree2 = parse('##h')
        errors = compare(tree1, tree2)
        self.assertIsInstance(errors[0], ReplaceError)

    def test_missing_new_line(self):
        tree1 = parse('test  \nnew line')
        tree2 = parse('test \nnew line')
        errors = compare(tree1, tree2)
        self.assertIsInstance(errors[0], DeleteError)

    def test_broken_link(self):
        tree1 = parse('[link](url)')
        tree2 = parse('[link] (url)')
        errors = compare(tree1, tree2)

        self.assertIsInstance(errors[0], ReplaceError)

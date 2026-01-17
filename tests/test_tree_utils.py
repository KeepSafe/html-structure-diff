from unittest import TestCase

from sdiff.model import Header, Link, Paragraph, Root, Text
from sdiff.tree_utils import traverse


class TestTraverse(TestCase):

    def test_preorder_traversal(self):
        tree = Root([
            Paragraph([
                Text('one'),
                Link('link'),
            ]),
            Header(2, [
                Text('heading'),
            ]),
        ])
        symbols = [node.symbol for node in traverse(tree)]
        self.assertEqual(['p', 't', 'a', 'h', 't'], symbols)

    def test_consecutive_text_nodes_coalesced(self):
        tree = Root([
            Paragraph([
                Text('one'),
                Text('two'),
                Link('link'),
                Text('three'),
                Text('four'),
            ]),
        ])
        texts = [node.text for node in traverse(tree) if isinstance(node, Text)]
        self.assertEqual(['one', 'three'], texts)

    def test_exclude_symbols_prunes_children(self):
        tree = Root([
            Paragraph([
                Text('one'),
                Link('link'),
            ]),
        ])
        symbols = [node.symbol for node in traverse(tree, exclude_symbols=['a'])]
        self.assertEqual(['p', 't'], symbols)

    def test_include_symbols_filters_children(self):
        tree = Root([
            Paragraph([
                Text('one'),
                Link('link'),
            ]),
        ])
        symbols = [node.symbol for node in traverse(tree, include_symbols=['a'])]
        self.assertEqual(['p', 'a'], symbols)

    def test_include_exclude_conflict_excludes(self):
        tree = Root([
            Paragraph([
                Link('link'),
            ]),
        ])
        symbols = [node.symbol for node in traverse(tree, include_symbols=['a'], exclude_symbols=['a'])]
        self.assertEqual(['p'], symbols)

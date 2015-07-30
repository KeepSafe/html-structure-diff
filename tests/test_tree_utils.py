from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff.tree_utils import index_of, flatten
from sdiff.model import *

class TestIndexOf(TestCase):
    def test_single_paragraph(self):
        tree = [ParagraphNode([TextNode('test')])]
        self.assertEqual(tree[0], index_of(0, tree))
        self.assertEqual(tree[0].nodes[0], index_of(1, tree))

    def test_single_header(self):
        tree = [HeaderNode(1, [TextNode('test')])]
        self.assertEqual(tree[0], index_of(0, tree))
        self.assertEqual(tree[0].nodes[0], index_of(1, tree))

    def test_two_blocks(self):
        tree = [ParagraphNode([TextNode('test'), LinkNode('link')]), HeaderNode(2, [TextNode('heading')])]
        self.assertEqual(tree[0], index_of(0, tree))
        self.assertEqual(tree[0].nodes[0], index_of(1, tree))
        self.assertEqual(tree[0].nodes[1], index_of(2, tree))
        self.assertEqual(tree[1], index_of(3, tree))
        self.assertEqual(tree[1].nodes[0], index_of(4, tree))

class TestFlatten(TestCase):
    def test_no_elements(self):
        tree = []
        actual = flatten(tree)
        self.assertEqual('', actual)

    def test_single_paragraph(self):
        tree = [ParagraphNode([TextNode('test')])]
        actual = flatten(tree)
        self.assertEqual('pt', actual)

    def test_several_elements(self):
        tree = [ParagraphNode([TextNode('test'), LinkNode('link')]), HeaderNode(2, [TextNode('heading')])]
        actual = flatten(tree)
        self.assertEqual('ptaht', actual)

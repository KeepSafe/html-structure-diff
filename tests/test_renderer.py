from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff.parser import parse
from sdiff.renderer import TextRenderer, HtmlRenderer
from sdiff.model import *
from .fixtures import trees

class TestTextRenderer(TestCase):
    def setUp(self):
        self.renderer = TextRenderer()

    def test_paragraph(self):
        actual = self.renderer.render(trees.pt())
        self.assertEqual('dummy text', actual)

    def test_header(self):
        actual = self.renderer.render(trees.r2t())
        self.assertEqual('##dummy text', actual)

    def test_several_elements(self):
        actual = self.renderer.render(trees.pta2t())
        self.assertEqual('test link\n\n##heading', actual)

class TestHtmlRenderer(TestCase):
    def setUp(self):
        self.renderer = HtmlRenderer()

    def test_paragraph(self):
        actual = self.renderer.render(trees.pt())
        self.assertEqual('<pre>\ndummy text\n</pre>', actual)

    def test_header(self):
        actual = self.renderer.render(trees.r2t())
        self.assertEqual('<pre>\n##dummy text\n</pre>', actual)

    def test_several_elements(self):
        actual = self.renderer.render(trees.pta2t())
        self.assertEqual('<pre>\ntest link\n\n##heading\n</pre>', actual)

    def test_ins_node(self):
        extra_text = Text('extra')
        extra_text.meta['style'] = 'ins'
        tree = trees.pt()
        tree.nodes[0].add_node(extra_text)

        actual = self.renderer.render(tree)

        self.assertEqual('<pre>\ndummy text<ins>extra</ins>\n</pre>', actual)

    def test_ins_node(self):
        extra_text = Text('extra')
        extra_text.meta['style'] = 'del'
        tree = trees.pt()
        tree.nodes[0].add_node(extra_text)

        actual = self.renderer.render(tree)

        self.assertEqual('<pre>\ndummy text<del>extra</del>\n</pre>', actual)

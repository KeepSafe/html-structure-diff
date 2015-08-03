from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff.parser import parse
from sdiff.renderer import TextRenderer, HtmlRenderer
from sdiff.model import *

class TestTextRenderer(TestCase):
    def setUp(self):
        self.renderer = TextRenderer()

    def test_paragraph(self):
        tree = [ParagraphNode([TextNode('test')])]
        actual = self.renderer.render(tree)
        self.assertEqual('test', actual)

    def test_header(self):
        tree = [HeaderNode(2, [TextNode('test')])]
        actual = self.renderer.render(tree)
        self.assertEqual('##test', actual)

    def test_several_elements(self):
        tree = [ParagraphNode([TextNode('test '), LinkNode('link')]), HeaderNode(2, [TextNode('heading')])]
        actual = self.renderer.render(tree)
        self.assertEqual('test link\n\n##heading', actual)

class TestHtmlRenderer(TestCase):
    def setUp(self):
        self.renderer = HtmlRenderer()

    def test_paragraph(self):
        tree = [ParagraphNode([TextNode('test')])]
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest\n</pre>', actual)

    def test_header(self):
        tree = [HeaderNode(2, [TextNode('test')])]
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\n##test\n</pre>', actual)

    def test_several_elements(self):
        tree = [ParagraphNode([TextNode('test '), LinkNode('link')]), HeaderNode(2, [TextNode('heading')])]
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest link\n\n##heading\n</pre>', actual)

    def test_ins_node(self):
        extra_text = TextNode('test')
        extra_text.style = 'ins'
        tree = [ParagraphNode([TextNode('test'), extra_text])]
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest<ins>test</ins>\n</pre>', actual)

    def test_ins_node(self):
        extra_text = TextNode('test')
        extra_text.style = 'del'
        tree = [ParagraphNode([TextNode('test'), extra_text])]
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest<del>test</del>\n</pre>', actual)

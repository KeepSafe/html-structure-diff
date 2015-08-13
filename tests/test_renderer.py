from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff.parser import parse
from sdiff.renderer import TextRenderer, HtmlRenderer
from sdiff.model import *

class TestTextRenderer(TestCase):
    def setUp(self):
        self.renderer = TextRenderer()

    def test_paragraph(self):
        tree = Root([Paragraph([Text('test')])])
        actual = self.renderer.render(tree)
        self.assertEqual('test', actual)

    def test_header(self):
        tree = Root([Header(2, [Text('test')])])
        actual = self.renderer.render(tree)
        self.assertEqual('##test', actual)

    def test_several_elements(self):
        tree = Root([Paragraph([Text('test '), Link('link')]), Header(2, [Text('heading')])])
        actual = self.renderer.render(tree)
        self.assertEqual('test link\n\n##heading', actual)

class TestHtmlRenderer(TestCase):
    def setUp(self):
        self.renderer = HtmlRenderer()

    def test_paragraph(self):
        tree = Root([Paragraph([Text('test')])])
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest\n</pre>', actual)

    def test_header(self):
        tree = Root([Header(2, [Text('test')])])
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\n##test\n</pre>', actual)

    def test_several_elements(self):
        tree = Root([Paragraph([Text('test '), Link('link')]), Header(2, [Text('heading')])])
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest link\n\n##heading\n</pre>', actual)

    def test_ins_node(self):
        extra_text = Text('test')
        extra_text.meta['style'] = 'ins'
        tree = Root([Paragraph([Text('test'), extra_text])])
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest<ins>test</ins>\n</pre>', actual)

    def test_ins_node(self):
        extra_text = Text('test')
        extra_text.meta['style'] = 'del'
        tree = Root([Paragraph([Text('test'), extra_text])])
        actual = self.renderer.render(tree)
        self.assertEqual('<pre>\ntest<del>test</del>\n</pre>', actual)

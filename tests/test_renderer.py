from unittest import TestCase

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

    def test_zendesk_steps(self):
        actual = self.renderer.render(trees.Slmtmt())
        self.assertEqual('<steps>\n\n0. one\n1. two\n\n\n</steps>', actual)

    def test_zendesk_tabs(self):
        actual = self.renderer.render(trees.T1tpt())
        self.assertEqual('<tabs>\n\n#tab title\n\ntab content\n\n</tabs>', actual)

    def test_zendesk_callout(self):
        actual = self.renderer.render(trees.C1tpt())
        self.assertEqual('<callout>\n\n#callout title\n\ncallout content\n\n</callout>', actual)

    def test_zendesk_callout_styled(self):
        actual = self.renderer.render(trees.C1tpt(style='awesome'))
        self.assertEqual('<callout awesome>\n\n#callout title\n\ncallout content\n\n</callout>', actual)


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

    def test_del_node(self):
        extra_text = Text('extra')
        extra_text.meta['style'] = 'del'
        tree = trees.pt()
        tree.nodes[0].add_node(extra_text)

        actual = self.renderer.render(tree)

        self.assertEqual('<pre>\ndummy text<del>extra</del>\n</pre>', actual)

from unittest import TestCase
from sdiff import parser, MdParser, ZendeskHelpMdParser
from sdiff.model import Paragraph, Root, Text, ZendeskHelpSteps


class ParserTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.parser_cls = MdParser

    def _run_and_assert(self, data: str, expected: str):
        actual = parser.parse(data, parser_cls=self.parser_cls).print_all()
        self.assertEqual(expected, actual)

    def _parse(self, data: str):
        return parser.parse(data, parser_cls=self.parser_cls)


class TestParser(ParserTestCase):
    def test_empty(self):
        self._run_and_assert('', '')

    def test_header(self):
        self._run_and_assert('###header', '3t')

    def test_header_in_list(self):
        self._run_and_assert('1. ###header\n2. ###header', 'lm3tm3t')

    def test_link(self):
        self._run_and_assert('[link](url)', 'pa')
        actual = self._parse('[link](url)')
        self.assertEqual('[link](url)', actual.nodes[0].nodes[0].text)

    def test_image(self):
        self._run_and_assert('![Alt text][url/to/image]', 'pi')
        actual = self._parse('![Alt text][url/to/image]')
        self.assertEqual('![Alt text][url/to/image]', actual.nodes[0].nodes[0].text)

    def test_broken_link_space(self):
        self._run_and_assert('[link] (http://www.google.com)', 'pt')

    def test_broken_link_new_line(self):
        self._run_and_assert('[link]\n(http://www.google.com)', 'pt')

    def test_single_quote(self):
        self._run_and_assert('code d\\\'acti & vation', 'pt')

    def test_exclamation_mark(self):
        self._run_and_assert('Danke!', 'pt')

    def test_escape_html(self):
        actual = self._parse('<sub>text</sub>')
        self.assertEqual('&lt;sub&gt;text&lt;/sub&gt;', actual.nodes[0].nodes[0].text)

    def test_ignore_single_space(self):
        self._run_and_assert('test\n \ntest', 'ptpt')

    def test_ignore_tailing_new_line(self):
        self._run_and_assert('[link](url)\n ', 'pa')

    def test_space_new_line_saparated_as_single_text(self):
        self._run_and_assert('<!-- TODO local on badges and iOS link --> \n<span id="appstore_badge">', 'xpt')

    def test_lheading_text(self):
        actual = self._parse('heading\n=============')
        self.assertEqual('heading', actual.nodes[0].nodes[0].text)

    def test_heading_text(self):
        actual = self._parse('### heading')
        self.assertEqual('heading', actual.nodes[0].nodes[0].text)

    def test_link_wrapped_in_text(self):
        self._run_and_assert('some text [link](url) new text', 'ptat')

    def test_link_label_with_codespan(self):
        actual = self._parse('[use `foo`](url)')
        self.assertEqual('[use `foo`](url)', actual.nodes[0].nodes[0].text)

    def test_link_label_with_strong_preserves_markers(self):
        actual = self._parse('[**bold**](url)')
        self.assertEqual('[**bold**](url)', actual.nodes[0].nodes[0].text)

    def test_link_title_preserved(self):
        actual = self._parse('[label](https://example.com "Title Here")')
        self.assertEqual('[label](https://example.com "Title Here")', actual.nodes[0].nodes[0].text)

    def test_image_title_preserved(self):
        actual = self._parse('![alt](https://img "Img Title")')
        self.assertEqual('![alt](https://img "Img Title")', actual.nodes[0].nodes[0].text)

    def test_reference_definition_preserved(self):
        data = 'See [API][id].\n\n[id]: https://example.com'
        tree = self._parse(data)
        link = next(node for node in tree.nodes[0].nodes if node.name == 'link')
        self.assertEqual('[API][id]', link.text)
        self.assertEqual('[id]: https://example.com', tree.nodes[1].nodes[0].text)

    def test_reference_definition_inside_list_item_preserved(self):
        data = '- item\n  [id]: https://example.com'
        tree = self._parse(data)
        list_item = tree.nodes[0].nodes[0]
        self.assertIn('[id]: https://example.com', list_item.nodes[0].text)

    def test_reference_links_with_whitespace_and_empty_id(self):
        data = 'See [API][] and [Ref] [id].\n\n[API]: https://example.com\n[id]: https://example.com'
        tree = self._parse(data)
        link_texts = [node.text for node in tree.nodes[0].nodes if node.name == 'link']
        self.assertIn('[API][]', link_texts)
        self.assertIn('[Ref] [id]', link_texts)

    def test_reference_definition_inside_fence_is_text(self):
        data = """```
[id]: https://example.com
[link][id]
```"""
        tree = self._parse(data)
        self.assertEqual('pt', tree.print_all())

    def test_reference_definition_inside_long_fence_is_text(self):
        data = """````
[id]: https://example.com
[link][id]
````"""
        tree = self._parse(data)
        self.assertEqual('pt', tree.print_all())

    def test_softbreak_preserves_space(self):
        actual = self._parse('hello\nworld')
        self.assertEqual('hello world', actual.nodes[0].nodes[0].text)

    def test_block_quote_preserves_marker(self):
        actual = self._parse('> quote')
        self.assertEqual('&gt; quote', actual.nodes[0].nodes[0].text)

    def test_fenced_code_preserves_fences(self):
        actual = self._parse('```\ncode\n```')
        self.assertEqual('```\ncode\n```', actual.nodes[0].nodes[0].text)

    def test_ordered_list_parses_as_ordered(self):
        tree = self._parse('1. one\n2. two')
        list_node = tree.nodes[0]
        self.assertTrue(list_node.ordered)

    def test_unordered_list_parses_as_unordered(self):
        tree = self._parse('- one\n- two')
        list_node = tree.nodes[0]
        self.assertFalse(list_node.ordered)


class TestZendeskParser(ParserTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.parser_cls = ZendeskHelpMdParser

    def test_callout(self):
        fixture = """
        <callout>
        # title
        content
        </callout>
        """
        self._run_and_assert(fixture, 'C1tpt')

    def test_callout_style(self):
        fixture = """
        <callout green>
        # title
        content
        </callout>
        """
        actual = self._parse(fixture)
        self.assertEqual(actual.nodes[0].style, 'green')

    def test_callout_invalid_style(self):
        fixture = """
        <callout invalid>
        # title
        content
        </callout>
        """
        actual = self._parse(fixture)
        self.assertNotEqual(actual.nodes[0].name, 'callout')

    def test_tabs(self):
        fixture = """
        <tabs>
        # title 1
        content 1
        # title 2
        content 2
        </tabs>
        """
        self._run_and_assert(fixture, 'T1tpt1tpt')

    def test_inline_callout_is_structural(self):
        fixture = """intro <callout>
# title
content
</callout> outro"""
        self._run_and_assert(fixture, 'ptC1tptpt')

    def test_zendesk_tags_inside_fenced_code_are_text(self):
        fixture = """```
<callout>
# title
content
</callout>
<steps>
1. one
</steps>
<tabs>
# tab
content
</tabs>
```"""
        tree = self._parse(fixture)
        self.assertEqual('pt', tree.print_all())
        self.assertFalse(any(node.name in {'callout', 'steps', 'tabs'} for node in tree.nodes))

    def test_steps(self):
        steps_fixture = """
        <steps>
        1. one
        2. two
        3. tri
        </steps>
        """
        with self.subTest('happy path'):
            self._run_and_assert(steps_fixture, 'Slmtmtmt')
        with self.subTest('nested in tabs'):
            fixture = """
            <tabs>
            # title 1
            content 1
            # title 2
            %s
            </tabs>
            """ % steps_fixture
            self._run_and_assert(fixture, 'T1tpt1tSlmtmtmt')

    def test_invalid_closing_tag(self):
        fixture = """
        <steps>
        1. one
        </step>
        """
        actual = self._parse(fixture)
        self.assertNotEqual(actual.nodes[0], ZendeskHelpSteps())

    def test_parses_with_invalid_formatting(self):
        fixture = '<steps>1. one</steps>'
        actual = self._parse(fixture)
        self.assertEqual(actual.nodes[0], ZendeskHelpSteps())


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

    def test_remove_ltr_rtl_marks(self):
        text = 'a\u200eb\u200f'
        actual = parser._remove_ltr_rtl_marks(text)
        self.assertEqual('ab', actual)


class DummyParser:
    last_text = None

    def parse(self, text, rules=None):
        DummyParser.last_text = text
        return [Paragraph([Text(text)])]


class TestParseWrapper(TestCase):
    def test_wraps_list_parser_output(self):
        tree = parser.parse('hello', parser_cls=DummyParser)
        self.assertIsInstance(tree, Root)
        self.assertEqual('pt', tree.print_all())

    def test_custom_parser_input_not_mutated_by_ref_defs(self):
        data = 'See [API][id].\n\n[id]: https://example.com'
        parser.parse(data, parser_cls=DummyParser)
        self.assertIn('[id]: https://example.com', DummyParser.last_text)

    def test_mdparser_parse_accepts_rules_argument(self):
        md_parser = MdParser()
        nodes = md_parser.parse('1. one', MdParser.list_rules)
        self.assertIsInstance(nodes, list)

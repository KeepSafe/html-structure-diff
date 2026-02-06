from unittest import TestCase
from sdiff import parser, MdParser, ZendeskHelpMdParser
from sdiff.model import Paragraph, Root, Text, ZendeskHelpSteps
from sdiff.renderer import TextRenderer


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

    def test_heading_without_space_followed_by_text_parses_as_header(self):
        actual = self._parse('##Heading\ntext')
        self.assertEqual('2tpt', actual.print_all())

    def test_heading_without_space_with_link_parses_as_header(self):
        actual = self._parse('##[Verify email]({{url}})\ntext')
        self.assertEqual('header', actual.nodes[0].name)
        self.assertEqual(2, actual.nodes[0].level)
        self.assertEqual('link', actual.nodes[0].nodes[0].name)
        self.assertEqual('[Verify email]({{url}})', actual.nodes[0].nodes[0].text)

    def test_heading_without_space_in_list_item_followed_by_text(self):
        actual = self._parse('1. ##Heading\n   text')
        self.assertEqual('lm2tt', actual.print_all())

    def test_link_wrapped_in_text(self):
        self._run_and_assert('some text [link](url) new text', 'ptat')

    def test_link_with_trailing_text_does_not_duplicate_buffer(self):
        actual = self._parse('some text [link](url) new text')
        paragraph = actual.nodes[0]
        self.assertEqual(['text', 'link', 'text'], [node.name for node in paragraph.nodes])
        self.assertEqual('some text ', paragraph.nodes[0].text)
        self.assertEqual('[link](url)', paragraph.nodes[1].text)
        self.assertEqual(' new text', paragraph.nodes[2].text)

    def test_image_with_trailing_text_does_not_duplicate_buffer(self):
        actual = self._parse('some ![alt](url) new')
        paragraph = actual.nodes[0]
        self.assertEqual(['text', 'image', 'text'], [node.name for node in paragraph.nodes])
        self.assertEqual('some ', paragraph.nodes[0].text)
        self.assertEqual('![alt](url)', paragraph.nodes[1].text)
        self.assertEqual(' new', paragraph.nodes[2].text)

    def test_inline_marker_does_not_duplicate_buffer(self):
        actual = self._parse('some **bold** text')
        self.assertEqual('some **bold** text', TextRenderer().render(actual))

    def test_inline_linebreak_does_not_duplicate_buffer(self):
        actual = self._parse('a\\\nb')
        paragraph = actual.nodes[0]
        self.assertEqual(['text', 'new-line', 'text'], [node.name for node in paragraph.nodes])
        self.assertEqual('a', paragraph.nodes[0].text)
        self.assertEqual('b', paragraph.nodes[2].text)

    def test_text_before_link_not_duplicated(self):
        actual = self._parse('some text and [link](url)')
        paragraph = actual.nodes[0]
        self.assertEqual(['text', 'link'], [node.name for node in paragraph.nodes])
        self.assertEqual(['some text and '], [node.text for node in paragraph.nodes if node.name == 'text'])

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
        self.assertEqual('item', list_item.nodes[0].text)
        self.assertEqual('[id]: https://example.com', tree.nodes[1].nodes[0].text)

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
        self.assertEqual('ptttptattt', tree.print_all())

    def test_reference_definition_inside_long_fence_is_text(self):
        data = """````
[id]: https://example.com
[link][id]
````"""
        tree = self._parse(data)
        self.assertEqual('pttttptatttt', tree.print_all())

    def test_softbreak_preserves_space(self):
        actual = self._parse('hello\nworld')
        self.assertEqual('hello world', actual.nodes[0].nodes[0].text)

    def test_block_quote_preserves_marker(self):
        actual = self._parse('> quote')
        self.assertEqual('&gt; quote', actual.nodes[0].nodes[0].text)

    def test_fenced_code_preserves_fences(self):
        actual = self._parse('```\ncode\n```')
        self.assertEqual('ptttttt', actual.print_all())
        text = ''.join(node.text for node in actual.nodes[0].nodes)
        self.assertTrue(text.startswith('```'))
        self.assertTrue(text.endswith('```'))

    def test_ordered_list_parses_as_ordered(self):
        tree = self._parse('1. one\n2. two')
        list_node = tree.nodes[0]
        self.assertTrue(list_node.ordered)

    def test_ordered_list_marker_other_than_1_interrupts_paragraph(self):
        self._run_and_assert('para\n2. item\n', 'ptlmt')

    def test_list_item_allows_unindented_heading_lazy_continuation(self):
        tree = self._parse('* a\n###### b\n')
        self.assertEqual(1, len(tree.nodes))
        self.assertEqual('list', tree.nodes[0].name)
        item = tree.nodes[0].nodes[0]
        self.assertEqual(['text', 'header'], [node.name for node in item.nodes])
        self.assertEqual('a', item.nodes[0].text)
        self.assertEqual(6, item.nodes[1].level)
        self.assertEqual('b', item.nodes[1].nodes[0].text)

    def test_unordered_list_parses_as_unordered(self):
        tree = self._parse('- one\n- two')
        list_node = tree.nodes[0]
        self.assertFalse(list_node.ordered)

    def test_double_blank_lines_between_list_items_nests_next_list(self):
        self._run_and_assert('* a\n\n\n* b\n', 'lmtlmt')

    def test_double_blank_lines_between_ordered_list_items_nests_next_list(self):
        self._run_and_assert('1. a\n\n\n1. b\n', 'lmtlmt')


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

    def test_callout_invalid_style_does_not_swallow_trailing_closing_tag(self):
        fixture = '<callout invalid>\n# title\ncontent\n</callout>\n</callout>\n'
        self._run_and_assert(fixture, 'xpt')

    def test_callout_tags_inside_list_item_are_text_and_allow_headings(self):
        fixture = '1. item\n<callout>\n# title\ncontent\n</callout>\n'
        tree = self._parse(fixture)
        self.assertEqual(1, len(tree.nodes))
        self.assertEqual('list', tree.nodes[0].name)
        item = tree.nodes[0].nodes[0]
        self.assertEqual(['text', 'text', 'header', 'text', 'text'], [node.name for node in item.nodes])
        self.assertEqual('&lt;callout&gt;', item.nodes[1].text)
        self.assertEqual(1, item.nodes[2].level)
        self.assertEqual('title', item.nodes[2].nodes[0].text)
        self.assertEqual('&lt;/callout&gt;', item.nodes[-1].text)

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

    def test_inline_callout_is_not_structural(self):
        fixture = """intro <callout>
# title
content
</callout> outro"""
        self._run_and_assert(fixture, 'pt1tpt')

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
        self.assertEqual('ptttxxxpttt', tree.print_all())
        self.assertFalse(any(node.name in {'callout', 'steps', 'tabs'} for node in tree.nodes))

    def test_zendesk_tags_after_fenced_code_are_parsed(self):
        fixture = """```
<callout>
# title
content
</callout>
```

<callout>
# title
content
</callout>
"""
        tree = self._parse(fixture)
        self.assertTrue(any(node.name == 'callout' for node in tree.nodes))
        self.assertEqual(1, tree.print_all().count('C'))

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

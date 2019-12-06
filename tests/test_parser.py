from unittest import TestCase
from sdiff import parser, MdParser, ZendeskHelpMdParser
from sdiff.model import ZendeskHelpSteps


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

    def test_image(self):
        self._run_and_assert('![Alt text][url/to/image]', 'pi')

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

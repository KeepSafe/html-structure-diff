import json
from time import perf_counter
from pathlib import Path
from unittest import TestCase

import mistune
import sdiff

from sdiff import MdParser, ZendeskHelpMdParser, parser
from sdiff.model import Html, Image, Link, Text, ZendeskHelpCallout
from sdiff.renderer import TextRenderer
from sdiff.renderer import HtmlRenderer
from scripts.mistune_compat_cases import expand_cases
from scripts.mistune_compat_signatures import canonical_hash, run_case


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPATIBILITY_CORPUS = REPO_ROOT / 'tests/fixtures/compatibility/mistune_cases.json'
GOLDEN_MISTUNE_084_FIXTURES = (
    REPO_ROOT / 'tests/fixtures/compatibility/golden_mistune_084_fixtures.json'
)


class TestLegacyMistuneBehaviorContract(TestCase):
    def test_existing_entities_are_not_double_escaped(self):
        tree = parser.parse('a & b &amp; &copy; &bogus; < >')
        self.assertEqual('a &amp; b &amp; &copy; &bogus; &lt; &gt;', tree.nodes[0].nodes[0].text)

    def test_nonstructural_markdown_remains_text(self):
        source = '*em* **strong** `code` ~~strike~~\n\n> quote\n\n```python\npass\n```'
        tree = parser.parse(source)
        self.assertNotIn('code', {node.name for node in tree.nodes})
        self.assertEqual(source.replace('> quote', '&gt; quote'), TextRenderer().render(tree))

    def test_link_and_image_keep_the_exact_markdown_source(self):
        link_tree = parser.parse('[label](https://example.test/path "title")')
        image_tree = parser.parse("![alt](image.png 'title')")
        link = link_tree.nodes[0].nodes[0]
        image = image_tree.nodes[0].nodes[0]
        self.assertIsInstance(link, Link)
        self.assertIsInstance(image, Image)
        self.assertEqual('[label](https://example.test/path "title")', link.text)
        self.assertEqual("![alt](image.png 'title')", image.text)

    def test_inline_image_after_text_keeps_legacy_link_classification(self):
        tree = parser.parse('text ![alt](image.png)')
        self.assertEqual('pta', tree.print_all())
        self.assertEqual('text !', tree.nodes[0].nodes[0].text)
        self.assertEqual('[alt](image.png)', tree.nodes[0].nodes[1].text)

    def test_nested_parenthesis_link_keeps_legacy_truncated_structure(self):
        tree = parser.parse('[label](https://example.test/a_(b) "title")')
        self.assertEqual('pat', tree.print_all())
        self.assertEqual('[label](https://example.test/a_(b)', tree.nodes[0].nodes[0].text)
        self.assertEqual(' "title")', tree.nodes[0].nodes[1].text)

    def test_escaped_bracket_label_keeps_legacy_link_boundary(self):
        tree = parser.parse(r'[escaped \] label](url)')
        self.assertEqual('pa', tree.print_all())
        self.assertEqual(r'[escaped \] label](url)', tree.nodes[0].nodes[0].text)

    def test_invalid_link_boundaries_remain_text(self):
        sources = (
            '[label][unclosed',
            '[label][bad^reference]',
        )
        for source in sources:
            with self.subTest(source=source):
                tree = parser.parse(source)
                self.assertNotIn('a', tree.print_all())

    def test_nested_and_angle_boundaries_keep_legacy_link_shapes(self):
        expectations = {
            '[[[label]]](url)': 'pa',
            '[[label](url)': 'pta',
            '[label](<url)': 'pa',
            '[label](<url)>)': 'pa',
        }
        for source, expected in expectations.items():
            with self.subTest(source=source):
                self.assertEqual(expected, parser.parse(source).print_all())

    def test_nested_label_atoms_and_greedy_closing_match_legacy_regex(self):
        expectations = {
            '[[[]](u)': ('pa', ['[[[]](u)']),
            '![[[]](u)': ('pi', ['![[[]](u)']),
            '[[[]][r]': ('pa', ['[[[]][r]']),
            '![[[]][r]': ('pi', ['![[[]][r]']),
            '[a](u)](v)': ('pa', ['[a](u)](v)']),
            '[a](u)](': ('pat', ['[a](u)', '](']),
            '[a](<x)y>)': ('pa', ['[a](<x)y>)']),
            '[a](<x)y)': ('pat', ['[a](<x)', 'y)']),
            '[[a](u)](v)': ('pa', ['[[a](u)](v)']),
        }
        for source, (structure, texts) in expectations.items():
            with self.subTest(source=source):
                tree = parser.parse(source)
                self.assertEqual(structure, tree.print_all())
                self.assertEqual(texts, [node.text for node in tree.nodes[0].nodes])

    def test_whitespace_in_link_boundaries_matches_legacy_parser(self):
        direct = parser.parse('[label](   url)')
        reference = parser.parse('[label]  [missing]')
        self.assertEqual('pa', direct.print_all())
        self.assertEqual('pa', reference.print_all())

    def test_unresolved_reference_link_remains_structural(self):
        tree = parser.parse('[label][missing]')
        self.assertIsInstance(tree.nodes[0].nodes[0], Link)
        self.assertEqual('[label][missing]', tree.nodes[0].nodes[0].text)

    def test_inline_html_is_text_but_block_html_is_html(self):
        inline = parser.parse('before <sub>one</sub> after')
        block = parser.parse('<div>\none\n</div>')
        self.assertIsInstance(inline.nodes[0].nodes[0], Text)
        self.assertEqual('before &lt;sub&gt;one&lt;/sub&gt; after', inline.nodes[0].nodes[0].text)
        self.assertIsInstance(block.nodes[0], Html)
        self.assertEqual('<div>\none\n</div>', block.nodes[0].text)

    def test_bare_thematic_break_is_not_a_structural_node(self):
        tree = parser.parse('---')
        self.assertEqual('pt', tree.print_all())
        self.assertEqual('---', tree.nodes[0].nodes[0].text)

    def test_zendesk_callout_recursively_uses_compatibility_parser(self):
        tree = parser.parse(
            '<callout red>\n# Heading\n[label][missing]\n</callout>',
            parser_cls=ZendeskHelpMdParser,
        )
        self.assertIsInstance(tree.nodes[0], ZendeskHelpCallout)
        self.assertEqual('red', tree.nodes[0].style)
        self.assertEqual('C1tpa', tree.print_all())

    def test_parser_facades_remain_constructible(self):
        nodes = MdParser()('plain')
        self.assertEqual('paragraph', nodes[0].name)
        self.assertEqual([], parser.InlineLexer()(' '))
        self.assertEqual('ZendeskHelpMdParser', ZendeskHelpMdParser.__name__)
        self.assertEqual('3.3.4', mistune.__version__)

    def test_inline_parser_honors_explicit_rule_selection(self):
        text_only = parser.InlineLexer().parse('[x](url)', ['text'])
        direct_only = parser.InlineLexer().parse('[x](url)', ['link', 'text'])
        reference_only = parser.InlineLexer()('[x][ref]', ['reflink', 'text'])
        self.assertEqual([('[x](url)', Text)], [(node.text, type(node)) for node in text_only])
        self.assertEqual([('[x](url)', Link)], [(node.text, type(node)) for node in direct_only])
        self.assertEqual([('[x][ref]', Link)], [(node.text, type(node)) for node in reference_only])

    def test_parser_instances_reuse_the_legacy_token_list(self):
        block_parser = MdParser()
        first_block_result = block_parser.parse('# first')
        second_block_result = block_parser.parse('second')
        self.assertIs(first_block_result, second_block_result)
        self.assertIs(block_parser.tokens, second_block_result)
        self.assertEqual(['header', 'paragraph'], [node.name for node in second_block_result])

        inline_parser = parser.InlineLexer()
        first_inline_result = inline_parser.parse('first')
        second_inline_result = inline_parser.parse('second')
        self.assertIs(first_inline_result, second_inline_result)
        self.assertIs(inline_parser.tokens, second_inline_result)
        self.assertEqual(['first', 'second'], [node.text for node in second_inline_result])

    def test_parser_factory_and_preprocessing_boundaries_match_legacy_api(self):
        source = '\u200eone\u200f'
        direct = MdParser().parse(source)
        public = parser.parse(source)
        self.assertEqual(source, direct[0].nodes[0].text)
        self.assertEqual('one', public.nodes[0].nodes[0].text)
        self.assertIs(type(MdParser.get_lexer()), MdParser)
        self.assertIs(type(ZendeskHelpMdParser.get_lexer()), ZendeskHelpMdParser)

    def test_legacy_list_thematic_break_value_is_retained(self):
        nodes = MdParser().parse('* one\n\n  ---\n* two')
        thematic_break = nodes[0].nodes[0].nodes[2]
        self.assertEqual({'type': 'hrule'}, thematic_break)

    def test_zendesk_rules_do_not_leak_into_plain_parser_instances(self):
        original_rules = list(MdParser.default_rules)
        first = ZendeskHelpMdParser()
        second = ZendeskHelpMdParser()
        self.assertEqual(original_rules, MdParser.default_rules)
        self.assertIsNot(first._active_rules, second._active_rules)
        self.assertEqual(['tabs', 'steps', 'callout'], first._active_rules[:3])
        parser.parse('<tabs>one</tabs>', parser_cls=ZendeskHelpMdParser)
        plain = parser.parse('<tabs>one</tabs>', parser_cls=MdParser)
        self.assertNotEqual('tabs', plain.nodes[0].name)

    def test_malformed_links_are_scanned_in_bounded_time(self):
        cases = (
            '[label](' * 8_000,
            '[' * 16_000 + 'x](url)',
            '![' * 16_000 + 'x](url)',
        )
        for source in cases:
            with self.subTest(prefix=source[:16], length=len(source)):
                started = perf_counter()
                tree = parser.parse(source)
                elapsed = perf_counter() - started
                self.assertEqual('paragraph', tree.nodes[0].name)
                self.assertLess(elapsed, 2.0)


class TestGoldenMistune084Fixtures(TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads(GOLDEN_MISTUNE_084_FIXTURES.read_text(encoding='utf-8'))
        cls.cases = expand_cases(COMPATIBILITY_CORPUS, REPO_ROOT)

    def test_expanded_corpus_matches_golden_fixture_inventory(self):
        case_names = [case['name'] for case in self.cases]
        self.assertEqual(1, self.expected['schema_version'])
        self.assertEqual('0.8.4', self.expected['oracle']['mistune'])
        self.assertEqual(self.expected['case_count'], len(self.cases))
        self.assertEqual(len(case_names), len(set(case_names)))
        self.assertEqual(set(self.expected['cases']), set(case_names))
        self.assertEqual(self.expected['expanded_cases_sha256'], canonical_hash(self.cases))

    def test_every_target_result_matches_golden_mistune_084_fixture(self):
        for case in self.cases:
            with self.subTest(case=case['name']):
                signature = run_case(case, sdiff, parser, HtmlRenderer, TextRenderer)
                actual_hash = canonical_hash(signature)
                expected_hash = self.expected['cases'][case['name']]
                if actual_hash != expected_hash:
                    details = {
                        'case': case,
                        'expected_hash': expected_hash,
                        'actual_hash': actual_hash,
                        'actual_signature': signature,
                    }
                    self.fail(json.dumps(details, ensure_ascii=False, indent=2, sort_keys=True))

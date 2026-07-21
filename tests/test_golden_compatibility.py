import json
from pathlib import Path
from unittest import TestCase

import sdiff
from sdiff import parser
from sdiff.renderer import HtmlRenderer, TextRenderer


GOLDEN_PATH = Path(__file__).parent / 'fixtures' / 'golden' / 'python311_compatibility.json'

CASES = {
    'block_html_and_comment': (
        '<!-- English note -->\n\n<div class="notice">\nEnglish\n</div>',
        '<!-- Deutsche Notiz -->\n\n<div class="notice">\nDeutsch\n</div>',
        sdiff.MdParser,
    ),
    'extra_paragraph': ('one', 'eins\n\nzwei', sdiff.MdParser),
    'hard_break_and_direction_marks': (
        '\u200eone  \ntwo\n   \nthree\u200f',
        '\u200eeins  \nzwei\n   \ndrei\u200f',
        sdiff.MdParser,
    ),
    'heading_styles': (
        '# Heading\n\nSetext heading\n--------------',
        '# Ueberschrift\n\nSetext Ueberschrift\n-------------------',
        sdiff.MdParser,
    ),
    'image_and_reference_link': (
        '![English alt](image.png)\n\nRead [the guide][docs].\n\n[docs]: https://example.test/docs',
        '![Deutscher Alt-Text](image.png)\n\nLies [die Anleitung][docs].\n\n[docs]: https://example.test/docs',
        sdiff.MdParser,
    ),
    'inline_html': ('before <sub>one</sub> after', 'vor <sub>eins</sub> danach', sdiff.MdParser),
    'link_count_change': (
        'Read [one](https://example.test/one).',
        'Lies [eins](https://example.test/one) und [zwei](https://example.test/two).',
        sdiff.MdParser,
    ),
    'list_variants': (
        '* one\n* two\n\n1. first\n2. second',
        '* eins\n* zwei\n\n1. erste\n2. zweite',
        sdiff.MdParser,
    ),
    'removed_paragraph': ('one\n\ntwo', 'eins', sdiff.MdParser),
    'same_links': (
        'A [link](https://example.test)',
        'B [translated](https://example.test)',
        sdiff.MdParser,
    ),
    'zendesk_callout_style': (
        '<callout red>\n# Title\nbody\n</callout>',
        '<callout green>\n# Titel\ninhalt\n</callout>',
        sdiff.ZendeskHelpMdParser,
    ),
    'zendesk_steps_in_tabs': (
        '<tabs>\n# Steps\n<steps>\n1. one\n2. two\n</steps>\n</tabs>',
        '<tabs>\n# Schritte\n<steps>\n1. eins\n2. zwei\n</steps>\n</tabs>',
        sdiff.ZendeskHelpMdParser,
    ),
    'zendesk_unstyled_callout_in_tabs': (
        '<tabs>\n# Topic\n<callout>\nbody\n</callout>\n</tabs>',
        '<tabs>\n# Thema\n<callout>\ninhalt\n</callout>\n</tabs>',
        sdiff.ZendeskHelpMdParser,
    ),
}


def _serialize_errors(errors):
    return [
        {
            'type': type(error).__name__,
            'symbol': error.node.symbol,
            'style': error.node.meta.get('style'),
            'message': error.message,
        }
        for error in errors
    ]


def _snapshot(left, right, parser_cls):
    left_tree = parser.parse(left, parser_cls=parser_cls)
    right_tree = parser.parse(right, parser_cls=parser_cls)
    _, _, link_errors = sdiff.diff_links(left_tree, right_tree)
    left_text, right_text, errors = sdiff.diff(
        left,
        right,
        renderer=TextRenderer(),
        parser_cls=parser_cls,
    )
    left_html, right_html, _ = sdiff.diff(
        left,
        right,
        renderer=HtmlRenderer(),
        parser_cls=parser_cls,
    )
    return {
        'left_structure': left_tree.print_all(),
        'right_structure': right_tree.print_all(),
        'text': [left_text, right_text],
        'html': [left_html, right_html],
        'errors': _serialize_errors(errors),
        'link_errors': _serialize_errors(link_errors),
    }


class TestGoldenCompatibility(TestCase):
    maxDiff = None

    def test_parser_renderer_and_diff_outputs_match_python311_baseline(self):
        expected = json.loads(GOLDEN_PATH.read_text(encoding='utf-8'))
        actual = {
            name: _snapshot(left, right, parser_cls)
            for name, (left, right, parser_cls) in CASES.items()
        }
        self.assertEqual(expected, actual)

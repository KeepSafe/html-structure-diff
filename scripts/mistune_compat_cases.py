"""Expand the committed Mistune compatibility corpus deterministically."""

import json
import random
import runpy


SEED = 311_084_334
FUZZ_CASES = 200
FUZZ_FRAGMENTS = (
    '', 'plain', ' ', '\n', '\n\n', '  \n', '# heading', '###heading',
    'setext\n---', '* item', '1. item', '[label](url)', '![alt](image.png)',
    '[label][ref]', '[ref]: https://example.test', '<sub>x</sub>', '<!-- note -->',
    '*em*', '**strong**', '`code`', '---', '>', '&', '&amp;', '\u200e', '\u200f',
    '<tabs>', '</tabs>', '<callout red>', '</callout>', '\\[escaped]', '(', ')',
)


def expand_cases(corpus_path, repo):
    corpus = json.loads(corpus_path.read_text(encoding='utf-8'))
    cases = []
    for case in corpus['cases']:
        cases.append(dict(case))

    golden_namespace = runpy.run_path(str(repo / 'tests/test_golden_compatibility.py'))
    for name, (left, right, parser_cls) in golden_namespace['CASES'].items():
        cases.append({
            'name': f'golden_{name}',
            'parser': parser_cls.__name__,
            'left': left,
            'right': right,
        })

    for english_path in sorted((repo / 'tests/fixtures').glob('*/*.en.md')):
        german_path = english_path.with_name(english_path.name.replace('.en.md', '.de.md'))
        relative = english_path.relative_to(repo)
        cases.append({
            'name': 'fixture_' + str(relative).replace('/', '_').replace('.en.md', ''),
            'parser': 'ZendeskHelpMdParser' if 'zendesk' in english_path.name else 'MdParser',
            'left': english_path.read_text(encoding='utf-8'),
            'right': german_path.read_text(encoding='utf-8'),
        })

    rng = random.Random(corpus.get('fuzz_seed', SEED))
    fuzz_count = corpus.get('fuzz_cases', FUZZ_CASES)
    for index in range(fuzz_count):
        fragment_count = rng.randint(1, 7)
        left = ''.join(rng.choice(FUZZ_FRAGMENTS) for _ in range(fragment_count))
        right = ''.join(rng.choice(FUZZ_FRAGMENTS) for _ in range(fragment_count))
        cases.append({
            'name': f'fuzz_{index:04d}',
            'parser': rng.choice(('MdParser', 'ZendeskHelpMdParser')),
            'left': left,
            'right': right,
        })
    return cases

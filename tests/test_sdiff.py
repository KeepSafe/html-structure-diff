from pathlib import Path
from unittest import TestCase

import sdiff
from sdiff import ZendeskHelpMdParser


def _load_fixture(*path):
    return Path('tests/fixtures', *path).read_text(encoding='utf-8')


def _read_test_files(dirpath):
    path = Path('tests/fixtures', dirpath)
    filenames = {f.name.split('.')[0] for f in path.glob('*.md')}
    return [('%s.en.md' % fn, '%s.de.md' % fn) for fn in filenames]


class TestSdiff(TestCase):

    def test_same(self):
        cases = _read_test_files('same')
        for case in cases:
            with self.subTest(case=case):
                path1, path2 = case
                _, _, errors = sdiff.diff(_load_fixture('same', path1), _load_fixture('same', path2),
                                          parser_cls=ZendeskHelpMdParser)
                self.assertEqual([], errors, msg=case)

    def test_different(self):
        cases = _read_test_files('different')
        for case in cases:
            with self.subTest(case=case):
                path1, path2 = case
                _, _, errors = sdiff.diff(_load_fixture('different', path1), _load_fixture('different', path2),
                                          parser_cls=ZendeskHelpMdParser)
                self.assertNotEqual([], errors, msg=case)

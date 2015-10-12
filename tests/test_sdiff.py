from unittest import TestCase
from unittest.mock import MagicMock, patch

import os
import sdiff
from pathlib import Path
from sdiff.errors import *


def _load_fixture(*path):
    return open(os.path.join('tests/fixtures', *path)).read()


def _read_test_files(dirpath):
    path = Path(os.path.join('tests/fixtures', dirpath))
    filenames = set(f.name.split('.')[0] for f in path.glob('*.md'))
    return [('%s.en.md' % fn, '%s.de.md' % fn) for fn in filenames]


class TestSdiff(TestCase):

    def test_same(self):
        cases = _read_test_files('same')
        for case in cases:
            with self.subTest(case=case):
                path1, path2 = case
                _, _, errors = sdiff.diff(_load_fixture('same', path1), _load_fixture('same', path2))
                self.assertEqual([], errors)

    def test_different(self):
        cases = _read_test_files('different')
        for case in cases:
            with self.subTest(case=case):
                path1, path2 = case
                _, _, errors = sdiff.diff(_load_fixture('different', path1), _load_fixture('different', path2))
                self.assertNotEqual([], errors)

    def test_html(self):
        path1 = 'inline_html.en.md'
        path2 = 'inline_html.de.md'
        _, _, errors = sdiff.diff(_load_fixture('same', path1), _load_fixture('same', path2))
        self.assertEqual([], errors)

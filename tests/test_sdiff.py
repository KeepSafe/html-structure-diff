from unittest import TestCase

import os
import sdiff
from pathlib import Path

from sdiff import ZendeskHelpMdParser


def _load_fixture(*path):
    return open(os.path.join('tests/fixtures', *path), encoding='utf-8').read()


def _read_test_files(dirpath):
    path = Path(os.path.join('tests/fixtures', dirpath))
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

    def test_ignores_link_content(self):
        left = '[Link](http://example.com)'
        right = '[Different](http://example.org)'
        _, _, errors = sdiff.diff(left, right)
        self.assertEqual([], errors)

    def test_missing_link_is_reported(self):
        left = 'text [Link](http://example.com)'
        right = 'text'
        tree1 = sdiff.parse(left)
        tree2 = sdiff.parse(right)
        _, _, errors = sdiff.diff_links(tree1, tree2)
        self.assertTrue(any(error.node.name == 'link' for error in errors))

    def test_extra_paragraph_has_paragraph_error(self):
        left = _load_fixture('different', 'extra_paragraph.en.md')
        right = _load_fixture('different', 'extra_paragraph.de.md')
        _, _, errors = sdiff.diff(left, right, parser_cls=ZendeskHelpMdParser)
        self.assertTrue(any(error.node.name == 'paragraph' for error in errors))

    def test_softbreaks_ignored_in_structure(self):
        left = 'hello\nworld'
        right = 'hello world'
        _, _, errors = sdiff.diff(left, right)
        self.assertEqual([], errors)

    def test_reference_definition_missing_is_reported(self):
        left = 'See [API][id].\n\n[id]: https://example.com'
        right = 'See [API][id].'
        _, _, errors = sdiff.diff(left, right)
        self.assertTrue(any(error.node.name == 'paragraph' for error in errors))

    def test_code_block_content_ignored_in_structure(self):
        left = """```
code sample
```"""
        right = """```
different code sample
```"""
        _, _, errors = sdiff.diff(left, right)
        self.assertEqual([], errors)

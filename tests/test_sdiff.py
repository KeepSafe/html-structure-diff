from unittest import TestCase
from unittest.mock import MagicMock, patch

import os
import sdiff
from sdiff.errors import *

def load_fixture(name):
    return open(os.path.join('tests/fixtures', name)).read()


class TestFixturesSame(TestCase):

    def test_simple(self):
        md1 = load_fixture('same/simple.en.md')
        md2 = load_fixture('same/simple.de.md')
        _, _, errors = sdiff.diff(md1, md2)
        self.assertEqual([], errors)

    def test_special_chars(self):
        md1 = load_fixture('same/special_chars.en.md')
        md2 = load_fixture('same/special_chars.de.md')
        _, _, errors = sdiff.diff(md1, md2)
        self.assertEqual([], errors)

    def test_long(self):
        md1 = load_fixture('same/long.en.md')
        md2 = load_fixture('same/long.fr.md')
        _, _, errors = sdiff.diff(md1, md2)
        self.assertEqual([], errors)

    def test_ignore_one_tailing_space(self):
        md1 = load_fixture('same/extra_end_space.en.md')
        md2 = load_fixture('same/extra_end_space.de.md')
        _, _, errors = sdiff.diff(md1, md2)
        self.assertEqual([], errors)
        
    def test_ignore_only_spaces_text(self):
        md1 = load_fixture('same/spaces_text.en.md')
        md2 = load_fixture('same/spaces_text.fr.md')
        _, _, errors = sdiff.diff(md1, md2)
        self.assertEqual([], errors)
    

class TestFixturesDifferent(TestCase):
    def test_simple(self):
        md1 = load_fixture('different/extra_paragraph.en.md')
        md2 = load_fixture('different/extra_paragraph.de.md')
        _, _, errors = sdiff.diff(md1, md2)
        self.assertIsInstance(errors[0], InsertError)
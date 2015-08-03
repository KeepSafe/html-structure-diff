from unittest import TestCase
from unittest.mock import MagicMock, patch

from sdiff.links import links_diff

class TestLinks(TestCase):
    def test_no_links(self):
        actual = links_diff('test', 'hello you')
        self.assertIsNone(actual)
        
    def test_equal_links(self):
        actual = links_diff('[link](url)', '[link1](url1)')
        self.assertIsNone(actual)
        
    def test_not_equal_links(self):
        actual = links_diff('[link](url)', '[link1](url1)\n[link2](url2)')
        self.assertEqual(1, actual.count1)
        self.assertEqual(2, actual.count2)
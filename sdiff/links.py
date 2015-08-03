import re

from .parser import InlineLexer
from .errors import LinkError

link_re = re.compile(
    r'!?\[('
    r'(?:\[[^^\]]*\]|[^\[\]]|\](?=[^\[]*\]))*'
    r')\]\('
    r'''\s*(<)?([\s\S]*?)(?(2)>)(?:\s+['"]([\s\S]*?)['"])?\s*'''
    r'\)'
)
reflink_re = re.compile(
    r'!?\[('
    r'(?:\[[^^\]]*\]|[^\[\]]|\](?=[^\[]*\]))*'
    r')\]\s*\[([^^\]]*)\]'
)


def _count_links(text):
    return len(re.findall(link_re, text)) + len(re.findall(reflink_re, text))


def links_diff(text1, text2):
    count1 = _count_links(text1)
    count2 = _count_links(text2)
    if count1 != count2:
        return LinkError(count1, count2)
    return None

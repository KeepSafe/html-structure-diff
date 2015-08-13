import re
import logging
from difflib import SequenceMatcher
from itertools import zip_longest

from .parser import parse
from .tree_utils import traverse
from .errors import DeleteError, InsertError
from .model import Text

logger = logging.getLogger(__name__)


def _diff_ranges(seq1, seq2):
    opcodes = SequenceMatcher(a=seq1, b=seq2, autojunk=False).get_opcodes()
    return list(filter(lambda i: i[0] != 'equal', opcodes))


def _apply_diff_ranges(codes, seq1, seq2):
    errors = []
    seq = zip_longest(seq1, seq2)
    for idx, item in enumerate(seq):
        for code in codes:
            if code[1] <= idx < code[2]:
                node = item[0]
                # print(node)
                # HACK ignore single space errors
                if not (isinstance(node, Text) and node.text == ' '):
                    node.meta['style'] = 'del'
                    errors.append(DeleteError(node))
            if code[3] <= idx < code[4]:
                node = item[1]
                # HACK ignore single space errors
                if not (isinstance(node, Text) and node.text == ' '):
                    node.meta['style'] = 'ins'
                    errors.append(InsertError(node))
    return errors


def _diff(tree1, tree2, include_symbols=None, exclude_symbols=None):
    seq1 = list(traverse(tree1, include_symbols, exclude_symbols))
    seq2 = list(traverse(tree2, include_symbols, exclude_symbols))
    diff_ranges = _diff_ranges(seq1, seq2)
    errors = _apply_diff_ranges(diff_ranges, seq1, seq2)

    return tree1, tree2, errors


def diff_links(tree1, tree2):
    return _diff(tree1, tree2, include_symbols=['p', 'h', 'l', 'a'])


def diff_struct(tree1, tree2):
    return _diff(tree1, tree2, exclude_symbols=['a', 'i'])

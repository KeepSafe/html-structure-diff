from difflib import SequenceMatcher
from .tree_utils import flatten, index_of
from .errors import DeleteError, InsertError, ReplaceError
from .model import TextNode


def _apply_insert(code, tree1, tree2):
    _, start_idx1, _, start_idx2, stop_idx2 = code
    node1 = index_of(start_idx1 - 1, tree1) or index_of(start_idx1, tree1)
    nodes2 = [index_of(idx, tree2) for idx in range(start_idx2, stop_idx2)]

    # HACK ignore single space errors
    if len(nodes2) == 1 and isinstance(nodes2[0], TextNode) and nodes2[0].text == ' ':
        return

    for node in nodes2:
        node.style = 'ins'
    return InsertError(node1, nodes2)


def _apply_delete(code, tree1, tree2):
    _, start_idx1, stop_idx1, _, _ = code
    nodes = [index_of(idx, tree1) for idx in range(start_idx1, stop_idx1)]

    # HACK ignore single space errors
    if len(nodes) == 1 and isinstance(nodes[0], TextNode) and nodes[0].text == ' ':
        return

    for node in nodes:
        node.style = 'del'
    return DeleteError(nodes)


def _apply_replace(code, tree1, tree2):
    _, start_idx1, stop_idx1, start_idx2, stop_idx2 = code
    nodes1 = [index_of(idx, tree1) for idx in range(start_idx1, stop_idx1)]
    nodes2 = [index_of(idx, tree2) for idx in range(start_idx2, stop_idx2)]
    for node in nodes1:
        node.style = 'del'
    for node in nodes2:
        node.style = 'ins'
    return ReplaceError(nodes1, nodes2)


def _apply_codes(codes, tree1, tree2):
    errors = []
    for code in codes:
        action = code[0]
        error = None
        if action == 'insert':
            error = _apply_insert(code, tree1, tree2)
        elif action == 'delete':
            error = _apply_delete(code, tree1, tree2)
        elif action == 'replace':
            error = _apply_replace(code, tree1, tree2)
        if error:
            errors.append(error)
    return errors


def _get_diff_codes(seq1, seq2):
    return SequenceMatcher(a=seq1, b=seq2, autojunk=False).get_opcodes()


def compare(tree1, tree2):
    seq1 = flatten(tree1)
    seq2 = flatten(tree2)
    print(tree1)
    print(tree2)
    codes = _get_diff_codes(seq1, seq2)
    errors = _apply_codes(codes, tree1, tree2)
    return errors

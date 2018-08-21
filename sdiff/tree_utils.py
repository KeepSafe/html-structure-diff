from collections import deque
from .model import Text


def _ignore_node(node, include_symbols, exclude_symbols):
    in_includes = not include_symbols or node.symbol in include_symbols
    in_excludes = exclude_symbols and node.symbol in exclude_symbols
    return bool(in_includes and not in_excludes)


def traverse(tree, include_symbols=None, exclude_symbols=None):
    exclude_symbols = exclude_symbols or []
    include_symbols = include_symbols or []
    previous = None
    stack = deque(tree.nodes)
    while stack:
        node = stack.popleft()
        if isinstance(node, Text) and isinstance(previous, Text):
            continue
        yield node
        previous = node

        child_list = [i for i in node.nodes if _ignore_node(i, include_symbols, exclude_symbols)]
        children = reversed(child_list)
        stack.extendleft(children)

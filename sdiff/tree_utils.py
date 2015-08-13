from collections import deque

def _ignore_node(node, include_symbols, exclude_symbols):
    in_includes = not include_symbols or node.symbol in include_symbols
    in_excludes = exclude_symbols and node.symbol in exclude_symbols
    return bool(in_includes and not in_excludes)


def traverse(tree, include_symbols=None, exclude_symbols=None):
    exclude_symbols = exclude_symbols or []
    include_symbols = include_symbols or []
    stack = deque(tree.nodes)
    while stack:
        node = stack.popleft()
        yield node
        children = reversed(list(filter(lambda i: _ignore_node(i, include_symbols, exclude_symbols), node.nodes)))
        stack.extendleft(children)

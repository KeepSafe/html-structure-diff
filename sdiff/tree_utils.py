def flatten(tree):
    result = ''
    for node in tree:
        result = result + str(node)
    return result


def _index_of_recur(idx, nodes, count):
    '''
    Deep, deep magic
    '''
    for node in nodes:
        if count == idx:
            return node, count
        if hasattr(node, 'nodes'):
            result, count = _index_of_recur(idx, node.nodes, count + 1)
            if count == idx:
                return result, count
        count = count + 1
    return None, count - 1


def index_of(idx, nodes):
    result, count = _index_of_recur(idx, nodes, 0)
    return result

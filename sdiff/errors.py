class InsertError(object):

    def __init__(self, node1, nodes2):
        nodes2_msg = str([n.name for n in nodes2])
        node1_msg = node1.name
        self.message = 'There are missing elements %s which should be placed after %s element' % (nodes2_msg, node1_msg)


class DeleteError(object):

    def __init__(self, nodes):
        nodes_msg = str([n.name for n in nodes])
        self.message = 'There are additional elements %s which should be removed' % nodes_msg


class ReplaceError(object):

    def __init__(self, nodes1, nodes2):
        nodes1_msg = str([n.name for n in nodes1])
        nodes2_msg = str([n.name for n in nodes2])
        self.message = 'There are additional elements %s which should be replaced with %s' % (nodes1_msg, nodes2_msg)

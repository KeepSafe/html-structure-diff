class DiffError(object):

    def __str__(self):
        return self.message


class InsertError(DiffError):

    def __init__(self, node1, nodes2):
        nodes2_msg = str([n.name for n in nodes2])
        node1_msg = node1.name
        self.message = 'There are missing elements %s. Please check the provided diffs.' % nodes2_msg


class DeleteError(DiffError):

    def __init__(self, nodes):
        nodes_msg = str([n.name for n in nodes])
        self.message = 'There are additional elements %s. Please check the provided diffs.' % nodes_msg


class ReplaceError(DiffError):

    def __init__(self, nodes1, nodes2):
        nodes1_msg = str([n.name for n in nodes1])
        nodes2_msg = str([n.name for n in nodes2])
        self.message = ('There are additional elements %s which should be replaced with %s.'
                        ' Please check the provided diffs.') % (nodes1_msg, nodes2_msg)


class LinkError(DiffError):

    def __init__(self, count1, count2):
        self.count1 = count1
        self.count2 = count2
        self.message = ('There are %s links in the first text but %s in second one'
                        ' please check if all links are present.') % (count1, count2)

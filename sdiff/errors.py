class DiffError(object):

    def __str__(self):
        return self.message


class InsertError(DiffError):

    def __init__(self, node):
        self.node = node
        self.message = 'There is a missing element `%s`.' % node.name


class DeleteError(DiffError):

    def __init__(self, node):
        self.node = node
        self.message = 'There is an additional element `%s`.' % node.name

class Node(object):
    symbol = ''
    name = ''

    def __init__(self, nodes=None):
        self.nodes = nodes or []
        self.meta = {}

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'nodes': self.nodes})

    def __hash__(self):
        return hash(self.symbol)

    def __eq__(self, other):
        if not isinstance(other, Node):
            return False
        return self.symbol == other.symbol

    def add_node(self, node):
        self.nodes.append(node)

    def add_nodes(self, nodes):
        self.nodes.extend(nodes)

    def print_all(self):
        return '%s%s' % (self.symbol, ''.join(map(lambda i: i.print_all(), self.nodes)))


class Root(Node):
    name = 'root'

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        return renderer.render_node(self, result)


class Paragraph(Node):
    symbol = 'p'
    name = 'paragraph'

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)


class Header(Node):
    symbol = 'h'
    name = 'header'

    def __init__(self, level, nodes=None):
        super().__init__(nodes)
        self.level = level

    def __str__(self):
        return self.level

    def __repr__(self):
        data = super().__repr__()
        data['level'] = self.level
        return data

    def __hash__(self):
        return hash(self.level)

    def __eq__(self, other):
        if not isinstance(other, Header):
            return False
        return self.level == other.level

    def original(self, renderer):
        result = '#' * self.level
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)

    def print_all(self):
        return '%s%s' % (self.level, ''.join(map(lambda i: i.print_all(), self.nodes)))


class List(Node):
    symbol = 'l'
    name = 'list'

    def __init__(self, ordered, nodes=None):
        super().__init__(nodes)
        self.ordered = ordered

    def __repr__(self):
        data = super().__repr__()
        data['ordered'] = self.ordered
        return data

    def original(self, renderer):
        result = ''
        for idx, node in enumerate(self.nodes):
            if self.ordered:
                result += '%s. %s' % (idx, node.original(renderer))
            else:
                result += '* ' + node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)


class ListItem(Node):
    symbol = 'm'
    name = 'list-item'

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n'
        return result


class Text(Node):
    symbol = 't'
    name = 'text'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'text': self.text})

    # def __hash__(self):
    #     return hash(self.symbol)
    #
    # def __eq__(self, other):
    #     if not isinstance(other, Text):
    #         return False
    #     wc = len(self.text.split(' '))
    #     wc1 = len(other.text.split(' '))
    #     return 2 > wc / wc1 > 0.5

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class Link(Node):
    symbol = 'a'
    name = 'link'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'text': self.text})

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class Image(Link):
    symbol = 'i'
    name = 'image'


class NewLine(Node):
    symbol = 'n'
    name = 'new-line'

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta})

    def original(self, renderer):
        return renderer.render_node(self, u'  \u00B6\n')

from enum import Enum


class Symbols(Enum):
    null = ''
    paragraph = 'p'
    header = 'h'
    list = 'l'
    list_item = 'm'
    html = 'x'
    text = 't'
    link = 'a'
    image = 'i'
    new_line = 'n'


class Node(object):
    symbol = Symbols.null.value
    name = ''

    def __init__(self, nodes=None):
        self.nodes = nodes or []
        self.meta = {}

    def __str__(self):
        s = self.symbol
        return s + ''.join([str(n) for n in self.nodes])

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
    symbol = Symbols.paragraph.value
    name = 'paragraph'

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)


class Header(Node):
    symbol = Symbols.header.value
    name = 'header'

    def __init__(self, level, nodes=None):
        super().__init__(nodes)
        self.level = level

    def __str__(self):
        return str(self.level)

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'nodes': self.nodes, 'level': self.level})

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
    symbol = Symbols.list.value
    name = 'list'

    def __init__(self, ordered, nodes=None):
        super().__init__(nodes)
        self.ordered = ordered

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'nodes': self.nodes, 'ordered': self.ordered})

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
    symbol = Symbols.list_item.value
    name = 'list-item'

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n'
        return result


class Html(Node):
    symbol = Symbols.html.value
    name = 'html'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class Text(Node):
    symbol = Symbols.text.value
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
    symbol = Symbols.link.value
    name = 'link'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'text': self.text})

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class Image(Link):
    symbol = Symbols.image.value
    name = 'image'


class NewLine(Node):
    symbol = Symbols.new_line.value
    name = 'new-line'

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta})

    def original(self, renderer):
        return renderer.render_node(self, u'  \u00B6\n')

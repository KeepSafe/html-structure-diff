class Node(object):
    symbol = ''
    name = ''

    def __init__(self, nodes=None):
        self.nodes = nodes or []
        self.style = ''

    def add_node(self, node):
        self.nodes.append(node)

    def add_nodes(self, nodes):
        self.nodes.extend(nodes)

    def __str__(self):
        return '%s%s' % (self.symbol, ''.join(map(lambda i: str(i), self.nodes)))


class ParagraphNode(Node):
    symbol = 'p'
    name = 'paragraph'

    def __init__(self, nodes=None):
        super().__init__(nodes)

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'nodes': self.nodes})

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)


class HeaderNode(Node):
    symbol = 'h'
    name = 'header'

    def __init__(self, level, nodes=None):
        super().__init__(nodes)
        self.level = level
        
    def __str__(self):
        return '%s%s' % (self.level, ''.join(map(lambda i: str(i), self.nodes)))

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'level': self.level, 'nodes': self.nodes})
        
    def original(self, renderer):
        result = '#' * self.level
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)



class ListNode(Node):
    symbol = 'l'
    name = 'list'

    def __init__(self, ordered, nodes=None):
        super().__init__(nodes)
        self.ordered = ordered

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'ordered': self.ordered, 'nodes': self.nodes})

    def original(self, renderer):
        result = ''
        for idx, node in enumerate(self.nodes):
            if self.ordered:
                result += '%s. %s' % (idx, node.original(renderer))
            else:
                result += '* ' + node.original(renderer)
        result = result + '\n\n'
        return renderer.render_node(self, result)


class ListItemNode(Node):
    symbol = 'm'
    name = 'list-item'

    def __init__(self, nodes=None):
        super().__init__(nodes)

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'nodes': self.nodes})

    def original(self, renderer):
        result = ''
        for node in self.nodes:
            result += node.original(renderer)
        result = result + '\n'
        return result


class TextNode(Node):
    symbol = 't'
    name = 'text'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'text': self.text})

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class LinkNode(Node):
    symbol = 't'
    name = 'link'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'text': self.text})

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class ImageNode(Node):
    symbol = 'i'
    name = 'image'

    def __init__(self, text):
        super().__init__()
        self.text = text

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style, 'text': self.text})

    def original(self, renderer):
        return renderer.render_node(self, self.text)


class NewLineNode(Node):
    symbol = 'n'
    name = 'new-line'

    def __repr__(self):
        return repr({'type': self.__class__.__name__, 'style': self.style})

    def original(self, renderer):
        return renderer.render_node(self, u'  \u00B6\n')

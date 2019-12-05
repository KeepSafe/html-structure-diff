from abc import ABC
from enum import Enum

import typing
from typing import Union

if typing.TYPE_CHECKING:
    from sdiff.renderer import HtmlRenderer, TextRenderer


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


class ZendeskArtSymbols(Enum):
    steps = 'S'
    tabs = 'T'
    callout = 'C'


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


class ZendeskArtNode(Node, ABC):
    def wrap(self, content: str) -> str:
        return f'<{self.name}>\n\n{content}</{self.name}>\n'

    def original(self, renderer: Union['HtmlRenderer', 'TextRenderer']) -> str:
        nested_content = ''.join(node.original(renderer) for node in self.nodes)
        result = self.wrap(nested_content)
        return renderer.render_node(self, result)


class ZendeskArtSteps(ZendeskArtNode):
    symbol = ZendeskArtSymbols.steps.value
    name = 'steps'

    def wrap(self, content: str) -> str:
        return f'<{self.name}>\n\n{content}</{self.name}>\n'

    def original(self, renderer: Union['HtmlRenderer', 'TextRenderer']) -> str:
        nested_content = ''.join(node.original(renderer) for node in self.nodes)
        result = self.wrap(nested_content)
        return renderer.render_node(self, result)


class ZendeskArtTabs(ZendeskArtNode):
    symbol = ZendeskArtSymbols.tabs.value
    name = 'tabs'


class ZendeskArtCallout(ZendeskArtNode):
    symbol = ZendeskArtSymbols.callout.value
    name = 'callout'

    def __init__(self, style: str = None, nodes: typing.List[Node] = None):
        super().__init__(nodes)
        self.style = style

    def __repr__(self):
        return repr({'type': self.name, 'meta': self.meta, 'nodes': self.nodes, 'style': self.style})

    def __hash__(self):
        return hash((self.name, self.style))

    def __eq__(self, other):
        if not isinstance(other, ZendeskArtCallout):
            return False
        return self.style == other.style

    def wrap(self, content: str) -> str:
        if self.style:
            attr = f' {self.style}'
        else:
            attr = ''
        return f'<{self.name}{attr}>\n\n{content}</{self.name}>\n'

import mistune
import re

from .model import *


class InlineLexer(mistune.BlockLexer):
    grammar_class = mistune.InlineGrammar

    default_rules = [
        'linebreak', 'link',
        'reflink', 'nolink',
        'text',
    ]

    def __init__(self):
        super().__init__()
        self.links = {}
        self.grammar_class.text = re.compile(r'^[\s\S]+?(?=[<!\[`~]|https?://| {2,}\n|$)')

    def parse_autolink(self, m):
        self.tokens.append(LinkNode(m.group(0)))

    def parse_url(self, m):
        self.tokens.append(LinkNode(m.group(0)))

    def parse_link(self, m):
        return self._process_link(m, m.group(3), m.group(4))

    def parse_reflink(self, m):
        key = mistune._keyify(m.group(2) or m.group(1))
        if key not in self.links:
            return None
        ret = self.links[key]
        return self._process_link(m, ret['link'], ret['title'])

    def parse_nolink(self, m):
        key = mistune._keyify(m.group(1))
        if key not in self.links:
            return None
        ret = self.links[key]
        return self._process_link(m, ret['link'], ret['title'])

    def _process_link(self, m, link, title=None):
        line = m.group(0)
        text = m.group(1)
        if line[0] == '!':
            node = ImageNode(line)
        else:
            node = LinkNode(line)

        self.tokens.append(node)

    def parse_linebreak(self, m):
        node = NewLineNode()
        self.tokens.append(node)

    def parse_text(self, m):
        text = m.group(0)
        node = TextNode(text)
        self.tokens.append(node)


class BlockLexer(mistune.BlockLexer):
    default_rules = [
        'newline', 'list_block',
        'heading', 'lheading',
        'paragraph', 'text',
    ]

    list_rules = (
        'newline', 'heading', 'lheading',
        'hrule', 'list_block', 'text',
    )

    def _parse_inline(self, text):
        inline = InlineLexer()
        return inline.parse(text)

    def parse_newline(self, m):
        length = len(m.group(0))
        if length > 1:
            self.tokens.append(NewLineNode())

    def parse_heading(self, m):
        level = len(m.group(1))
        text = m.group(0)
        node = HeaderNode(level)
        node.add_nodes(self._parse_inline(text))
        self.tokens.append(node)

    def parse_lheading(self, m):
        level = 1 if m.group(2) == '=' else 2
        text = m.group(1)
        node = HeaderNode(level)
        node.add_nodes(self._parse_inline(text))
        self.tokens.append(node)

    def parse_paragraph(self, m):
        text = m.group(1).rstrip('\n')
        node = ParagraphNode()
        node.add_nodes(self._parse_inline(text))
        self.tokens.append(node)

    def parse_text(self, m):
        text = m.group(0)
        node = TextNode(text)
        self.tokens.append(node)

    def parse_list_block(self, m):
        bull = m.group(2)
        cap = m.group(0)
        ordered = '.' in bull
        node = ListNode(ordered)
        node.add_nodes(self._process_list_item(cap, bull))
        self.tokens.append(node)

    def _process_list_item(self, cap, bull):
        result = []
        cap = self.rules.list_item.findall(cap)

        _next = False
        length = len(cap)

        for i in range(length):
            item = cap[i][0]

            # remove the bullet
            space = len(item)
            item = self.rules.list_bullet.sub('', item)

            # outdent
            if '\n ' in item:
                space = space - len(item)
                pattern = re.compile(r'^ {1,%d}' % space, flags=re.M)
                item = pattern.sub('', item)

            # determin whether item is loose or not
            loose = _next
            if not loose and re.search(r'\n\n(?!\s*$)', item):
                loose = True

            rest = len(item)
            if i != length - 1 and rest:
                _next = item[rest-1] == '\n'
                if not loose:
                    loose = _next

            node = ListItemNode()
            block_lexer = BlockLexer()
            nodes = block_lexer.parse(item, self.list_rules)
            node.add_nodes(nodes)
            result.append(node)
        return result


def parse(text):
    block_lexer = BlockLexer()
    return block_lexer.parse(text)

from re import Match

import mistune
import re

from .model import *


class InlineLexer(mistune.BlockLexer):
    grammar_class = mistune.InlineGrammar

    default_rules = [
        'linebreak', 'link',
        'reflink', 'text',
    ]

    def __init__(self):
        self.links = {}
        self.grammar_class.text = re.compile(r'^ {1,}\n|^[\s\S]+?(?=[\[`~]| {2,}\n|$)')
        super().__init__()

    def parse_autolink(self, m):
        self.tokens.append(Link(m.group(0)))

    def parse_url(self, m):
        self.tokens.append(Link(m.group(0)))

    def parse_link(self, m):
        return self._process_link(m)

    def parse_reflink(self, m):
        # TODO skip this check for now
        # key = mistune._keyify(m.group(2) or m.group(1))
        # if key not in self.links:
        #     return None
        # ret = self.links[key]
        return self._process_link(m)

    def _process_link(self, m):
        line = m.group(0)
        if line[0] == '!':
            node = Image(line)
        else:
            node = Link(line)

        self.tokens.append(node)

    def parse_linebreak(self, m):
        node = NewLine()
        self.tokens.append(node)

    def parse_text(self, m):
        text = m.group(0)
        if text.strip():
            escaped_text = mistune.escape(text)
            node = Text(escaped_text)
            self.tokens.append(node)


class MdParser(mistune.BlockLexer):
    default_rules = [
        'newline', 'list_block', 'block_html',
        'heading', 'lheading',
        'paragraph', 'text',
    ]

    list_rules = (
        'newline', 'heading', 'lheading',
        'hrule', 'list_block', 'text',
    )

    @classmethod
    def get_lexer(cls):
        return cls()

    def __init__(self):
        super().__init__()
        self.grammar_class.block_html = re.compile(
            r'^\s* *(?:{}|{}|{}) *(?:\n{{1,}}|\s*$)'.format(
                r'<!--[\s\S]*?-->',
                r'<({})((?:{})*?)>([\s\S]+?)<\/\1>'.format(mistune._block_tag, mistune._valid_attr),
                r'<{}(?:{})*?>'.format(mistune._block_tag, mistune._valid_attr),
            )
        )

    def _parse_inline(self, text):
        inline = InlineLexer()
        return inline.parse(text)

    def parse_newline(self, m):
        length = len(m.group(0))
        if length > 1:
            self.tokens.append(NewLine())

    def parse_heading(self, m):
        level = len(m.group(1))
        node = Header(level)
        node.add_nodes(self._parse_inline(m.group(2)))
        self.tokens.append(node)

    def parse_lheading(self, m):
        level = 1 if m.group(2) == '=' else 2
        text = m.group(1)
        node = Header(level)
        node.add_nodes(self._parse_inline(text))
        self.tokens.append(node)

    def parse_block_html(self, m):
        text = m.group(0)
        html = Html(text)
        self.tokens.append(html)

    def parse_paragraph(self, m):
        text = m.group(1).rstrip('\n')
        node = Paragraph()
        node.add_nodes(self._parse_inline(text))
        self.tokens.append(node)

    def parse_text(self, m):
        text = m.group(0)
        escaped_text = mistune.escape(text)
        node = Text(escaped_text)
        self.tokens.append(node)

    def parse_list_block(self, m):
        bull = m.group(2)
        cap = m.group(0)
        ordered = '.' in bull
        node = List(ordered)
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

            # determine whether item is loose or not
            loose = _next
            if not loose and re.search(r'\n\n(?!\s*$)', item):
                loose = True

            rest = len(item)
            if i != length - 1 and rest:
                _next = item[rest - 1] == '\n'
                if not loose:
                    loose = _next

            node = ListItem()
            block_lexer = self.get_lexer()
            nodes = block_lexer.parse(item, self.list_rules)
            node.add_nodes(nodes)
            result.append(node)
        return result


class ZendeskHelpMdParser(MdParser):
    TAG_CONTENT_GROUP = 'tag_content'
    TAG_PATTERN = r'^\s*(<{tag_name}{attr_re}>(?P<%s>[\s\S]+?)</{tag_name}>)\s*$' % TAG_CONTENT_GROUP
    CALLOUT_STYLE_GROUP = 'style'
    CALLOUT_ATTR_PATTERN = r'( (?P<%s>green|red|yellow))*' % CALLOUT_STYLE_GROUP

    def __init__(self):
        super().__init__()
        self.grammar_class.callout = re.compile(self.TAG_PATTERN.format(tag_name='callout',
                                                                        attr_re=self.CALLOUT_ATTR_PATTERN))
        self.default_rules.insert(0, 'callout')

        self.grammar_class.steps = re.compile(self.TAG_PATTERN.format(tag_name='steps', attr_re=''))
        self.default_rules.insert(0, 'steps')

        self.grammar_class.tabs = re.compile(self.TAG_PATTERN.format(tag_name='tabs', attr_re=''))
        self.default_rules.insert(0, 'tabs')

    def parse_callout(self, m: Match[str]) -> None:
        style = m.group(self.CALLOUT_STYLE_GROUP)
        self._parse_nested(ZendeskHelpCallout(style), m)

    def parse_steps(self, m: Match[str]) -> None:
        self._parse_nested(ZendeskHelpSteps(), m)

    def parse_tabs(self, m: Match[str]) -> None:
        self._parse_nested(ZendeskHelpTabs(), m)

    def _parse_nested(self, node: Node, m: Match[str]) -> None:
        nested_content = m.group(self.TAG_CONTENT_GROUP)
        nested_nodes = self.get_lexer().parse(nested_content)
        node.add_nodes(nested_nodes)
        self.tokens.append(node)


def _remove_spaces_from_empty_lines(text):
    return '\n'.join([re.sub(r'^( {1,}|\t{1,})$', '\n', line) for line in text.splitlines()])


def _remove_ltr_rtl_marks(text):
    return re.sub(r'(\u200e|\u200f)', '', text)


def parse(text, parser_cls: type[MdParser] = MdParser):
    # HACK dirty hack to be consistent with Markdown list_block
    text = _remove_spaces_from_empty_lines(text)
    text = _remove_ltr_rtl_marks(text)
    block_lexer = parser_cls()
    return Root(block_lexer.parse(text))

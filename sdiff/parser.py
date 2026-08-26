import re
from re import Match

import mistune
from mistune import InlineState

from .model import *


# Mistune 3 intentionally removed the lexer/grammar APIs used by sdiff with
# Mistune 0.8. Keep sdiff's narrow Markdown dialect local so its public tree
# remains stable without importing private Mistune constants.
_INLINE_TAGS = (
    'a', 'em', 'strong', 'small', 's', 'cite', 'q', 'dfn', 'abbr', 'data',
    'time', 'code', 'var', 'samp', 'kbd', 'sub', 'sup', 'i', 'b', 'u',
    'mark', 'ruby', 'rt', 'rp', 'bdi', 'bdo', 'span', 'br', 'wbr', 'ins',
    'del', 'img', 'font',
)
_BLOCK_TAG = r'(?!(?:{})\b)\w+(?!:/|[^\w\s@]*@)\b'.format('|'.join(_INLINE_TAGS))
_VALID_ATTR = r'''\s*[a-zA-Z\-](?:\s*\=\s*(?:"[^"]*"|'[^']*'|[^\s'">]+))?'''
_SMART_AMP = re.compile(r'&(?!#?\w+;)')
_LINK_OPENER = re.compile(r'!?\[')


def _pure_pattern(pattern):
    value = pattern.pattern
    return value[1:] if value.startswith('^') else value


def _legacy_escape(text):
    text = _SMART_AMP.sub('&amp;', text)
    return text.replace('<', '&lt;').replace('>', '&gt;')


class _InlineGrammar:
    linebreak = re.compile(r' {2,}\n(?!\s*$)')
    text = re.compile(r' {1,}\n|[\s\S]+?(?=[\[`~]| {2,}\n|$)')


class _BlockGrammar:
    def_links = re.compile(
        r'^ *\[([^^\]]+)\]: *'
        r'<?([^\s>]+)>?'
        r'(?: +["(]([^\n]+)[")])? *(?:\n+|$)'
    )
    def_footnotes = re.compile(
        r'^\[\^([^\]]+)\]: *('
        r'[^\n]*(?:\n+|$)'
        r'(?: {1,}[^\n]*(?:\n+|$))*'
        r')'
    )
    newline = re.compile(r'^\n+')
    fences = re.compile(
        r'^ *(`{3,}|~{3,}) *([^`\s]+)? *\n'
        r'([\s\S]+?)\s*'
        r'\1 *(?:\n+|$)'
    )
    hrule = re.compile(r'^ {0,3}[-*_](?: *[-*_]){2,} *(?:\n+|$)')
    heading = re.compile(r'^ *(#{1,6}) *([^\n]+?) *#* *(?:\n+|$)')
    lheading = re.compile(r'^([^\n]+)\n *(=|-)+ *(?:\n+|$)')
    block_quote = re.compile(r'^( *>[^\n]+(\n[^\n]+)*\n*)+')
    list_block = re.compile(
        r'^( *)(?=[*+-]|\d+\.)(([*+-])?(?:\d+\.)?) [\s\S]+?'
        r'(?:'
        r'\n+(?=\1?(?:[-*_] *){3,}(?:\n+|$))'
        r'|\n+(?=%s)'
        r'|\n+(?=%s)'
        r'|\n+(?=\1(?(3)\d+\.|[*+-]) )'
        r'|\n{2,}'
        r'(?! )'
        r'(?!\1(?:[*+-]|\d+\.) )\n*'
        r'|'
        r'\s*$)' % (
            _pure_pattern(def_links),
            _pure_pattern(def_footnotes),
        )
    )
    list_item = re.compile(
        r'^(( *)(?:[*+-]|\d+\.) [^\n]*'
        r'(?:\n(?!\2(?:[*+-]|\d+\.) )[^\n]*)*)',
        flags=re.M,
    )
    list_bullet = re.compile(r'^ *(?:[*+-]|\d+\.) +')
    paragraph = re.compile(
        r'^((?:[^\n]+\n?(?!'
        r'%s|%s|%s|%s|%s|%s|%s|%s|%s'
        r'))+)\n*' % (
            _pure_pattern(fences).replace(r'\1', r'\2'),
            _pure_pattern(list_block).replace(r'\1', r'\3'),
            _pure_pattern(hrule),
            _pure_pattern(heading),
            _pure_pattern(lheading),
            _pure_pattern(block_quote),
            _pure_pattern(def_links),
            _pure_pattern(def_footnotes),
            '<' + _BLOCK_TAG,
        )
    )
    block_html = re.compile(
        r'^\s* *(?:{}|{}|{}) *(?:\n{{1,}}|\s*$)'.format(
            r'<!--[\s\S]*?-->',
            fr'<({_BLOCK_TAG})((?:{_VALID_ATTR})*?)>([\s\S]+?)<\/\1>',
            fr'<{_BLOCK_TAG}(?:{_VALID_ATTR})*?>',
        )
    )
    text = re.compile(r'^[^\n]+')


class _HardenedLinkParser(mistune.InlineParser):
    """Use Mistune 3's bounded link scanner without its rendering semantics."""

    def precedence_scan(self, match, state, end_pos, rules=None):
        return None


def _next_character_indexes(source, character):
    indexes = [None] * (len(source) + 1)
    next_index = None
    for position in range(len(source) - 1, -1, -1):
        if source[position] == character:
            next_index = position
        indexes[position] = next_index
    return indexes


def _next_nonspace_indexes(source):
    indexes = [len(source)] * (len(source) + 1)
    for position in range(len(source) - 1, -1, -1):
        indexes[position] = indexes[position + 1] if source[position].isspace() else position
    return indexes


def _build_direct_tail_ends(source, next_parenthesis, next_nonspace):
    """Return the Mistune 0.8 direct-link tail end for each possible label close."""
    quote_tail_ends = [None] * len(source)
    next_valid_quote = [None] * (len(source) + 1)
    next_quote = None
    for position in range(len(source) - 1, -1, -1):
        if source[position] in ('\'', '"'):
            close_parenthesis = next_nonspace[position + 1]
            if close_parenthesis < len(source) and source[close_parenthesis] == ')':
                quote_tail_ends[position] = close_parenthesis + 1
                next_quote = position
        next_valid_quote[position] = next_quote

    angle_tail_ends = [None] * len(source)
    next_valid_angle = [None] * (len(source) + 1)
    next_angle = None
    for position in range(len(source) - 1, -1, -1):
        if source[position] == '>':
            tail_start = next_nonspace[position + 1]
            if tail_start < len(source) and source[tail_start] == ')':
                angle_tail_ends[position] = tail_start + 1
            elif tail_start > position + 1 and tail_start < len(source) and source[tail_start] in ('\'', '"'):
                closing_quote = next_valid_quote[tail_start + 1]
                if closing_quote is not None:
                    angle_tail_ends[position] = quote_tail_ends[closing_quote]
            if angle_tail_ends[position] is not None:
                next_angle = position
        next_valid_angle[position] = next_angle

    tail_ends = [None] * len(source)
    for position in range(len(source) - 1):
        if source[position:position + 2] != '](':
            continue
        destination_start = next_nonspace[position + 2]
        fallback_parenthesis = next_parenthesis[destination_start]
        if fallback_parenthesis is None:
            continue
        if destination_start < len(source) and source[destination_start] == '<':
            closing_angle = next_valid_angle[destination_start + 1]
            if closing_angle is not None:
                tail_ends[position] = angle_tail_ends[closing_angle]
                continue
        tail_ends[position] = fallback_parenthesis + 1
    return tail_ends


def _build_reference_tail_ends(source, next_bracket, next_caret, next_nonspace):
    """Return the Mistune 0.8 reference-link tail end for each label close."""
    tail_ends = [None] * len(source)
    for position, char in enumerate(source):
        if char != ']':
            continue
        reference_start = next_nonspace[position + 1]
        if reference_start >= len(source) or source[reference_start] != '[':
            continue
        reference_end = next_bracket[reference_start + 1]
        caret = next_caret[reference_start + 1]
        if reference_end is not None and (caret is None or caret > reference_end):
            tail_ends[position] = reference_end + 1
    return tail_ends


def _build_link_end_index(source, tail_ends, next_open, next_bracket, next_caret):
    """Compile Mistune 0.8's greedy nested-label expression into a linear index."""
    link_ends = [None] * (len(source) + 1)
    for position in range(len(source) - 1, -1, -1):
        char = source[position]
        if char == '[':
            nested_end = next_bracket[position + 1]
            caret = next_caret[position + 1]
            if nested_end is not None and (caret is None or caret > nested_end):
                link_ends[position] = link_ends[nested_end + 1]
            continue
        if char == ']':
            later_bracket = next_bracket[position + 1]
            later_open = next_open[position + 1]
            can_extend = later_bracket is not None and (
                later_open is None or later_bracket < later_open
            )
            if can_extend and link_ends[position + 1] is not None:
                link_ends[position] = link_ends[position + 1]
            else:
                link_ends[position] = tail_ends[position]
            continue
        link_ends[position] = link_ends[position + 1]
    return link_ends


def _build_link_indexes(source):
    next_open = _next_character_indexes(source, '[')
    next_bracket = _next_character_indexes(source, ']')
    next_caret = _next_character_indexes(source, '^')
    next_parenthesis = _next_character_indexes(source, ')')
    next_nonspace = _next_nonspace_indexes(source)
    direct_tails = _build_direct_tail_ends(source, next_parenthesis, next_nonspace)
    reference_tails = _build_reference_tail_ends(
        source,
        next_bracket,
        next_caret,
        next_nonspace,
    )
    return (
        _build_link_end_index(source, direct_tails, next_open, next_bracket, next_caret),
        _build_link_end_index(source, reference_tails, next_open, next_bracket, next_caret),
    )


class InlineLexer:
    default_rules = [
        'linebreak', 'link',
        'reflink', 'text',
    ]

    def __init__(self):
        self.links = {}
        self.tokens = []
        self.rules = _InlineGrammar()
        self._link_parser = _HardenedLinkParser()

    def __call__(self, text, rules=None):
        return self.parse(text, rules)

    def parse(self, text, rules=None):
        text = text.rstrip('\n')
        active_rules = rules or self.default_rules
        position = 0
        direct_link_ends, reference_link_ends = _build_link_indexes(text)
        modern_state = InlineState({'ref_links': {}})
        modern_state.src = text

        while position < len(text):
            for rule in active_rules:
                if rule == 'linebreak':
                    linebreak = self.rules.linebreak.match(text, position)
                    if linebreak:
                        self.tokens.append(NewLine())
                        position += len(linebreak.group(0))
                        break
                    continue

                if rule in ('link', 'reflink') and text.startswith(('![', '['), position):
                    marker_length = 2 if text.startswith('![', position) else 1
                    opener_end = position + marker_length
                    if rule == 'link':
                        end_position = direct_link_ends[opener_end]
                    else:
                        end_position = reference_link_ends[opener_end]
                    if end_position is not None:
                        opener = _LINK_OPENER.match(text, position)
                        # Exercise Mistune 3's hardened parser for syntax it
                        # accepts; the local boundary remains authoritative for
                        # legacy raw-source compatibility.
                        self._link_parser.parse_link(opener, modern_state)
                        source = text[position:end_position]
                        self.tokens.append(Image(source) if source[0] == '!' else Link(source))
                        position = end_position
                        break
                    continue

                if rule == 'text':
                    text_match = self.rules.text.match(text, position)
                    if text_match:
                        raw = text_match.group(0)
                        if raw.strip():
                            self.tokens.append(Text(_legacy_escape(raw)))
                        position += len(raw)
                        break
            else:  # pragma: no cover - default rules end with the text fallback
                raise RuntimeError(f'Infinite loop at: {text[position:]}')

        return self.tokens


class _CompatibilityBlockLexer:
    grammar_class = _BlockGrammar
    default_rules = ()

    def _configure_compatibility_lexer(self):
        self.tokens = []
        self.rules = self.grammar_class()
        self._active_rules = list(self.default_rules)

    def __call__(self, text, rules=None):
        return self.parse(text, rules)

    def parse(self, text, rules=None):
        text = text.rstrip('\n')
        active_rules = rules or self._active_rules

        while text:
            for name in active_rules:
                match = getattr(self.rules, name).match(text)
                if match:
                    getattr(self, f'parse_{name}')(match)
                    text = text[len(match.group(0)):]
                    break
            else:  # pragma: no cover - every grammar ends with a text rule
                raise RuntimeError(f'Infinite loop at: {text}')
        return self.tokens


class MdParser(_CompatibilityBlockLexer):
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
        self._configure_compatibility_lexer()

    def _parse_inline(self, text):
        return InlineLexer().parse(text)

    def parse_newline(self, match):
        if len(match.group(0)) > 1:
            self.tokens.append(NewLine())

    def parse_heading(self, match):
        node = Header(len(match.group(1)))
        node.add_nodes(self._parse_inline(match.group(2)))
        self.tokens.append(node)

    def parse_lheading(self, match):
        level = 1 if match.group(2) == '=' else 2
        node = Header(level)
        node.add_nodes(self._parse_inline(match.group(1)))
        self.tokens.append(node)

    def parse_block_html(self, match):
        self.tokens.append(Html(match.group(0)))

    def parse_paragraph(self, match):
        node = Paragraph()
        node.add_nodes(self._parse_inline(match.group(1).rstrip('\n')))
        self.tokens.append(node)

    def parse_text(self, match):
        self.tokens.append(Text(_legacy_escape(match.group(0))))

    def parse_hrule(self, match):
        # Preserve Mistune 0.8's inherited behavior for a thematic break
        # nested in a list. The compatibility reporter records the exception.
        self.tokens.append({'type': 'hrule'})

    def parse_list_block(self, match):
        bullet = match.group(2)
        node = List('.' in bullet)
        node.add_nodes(self._process_list_item(match.group(0)))
        self.tokens.append(node)

    def _process_list_item(self, captured):
        result = []
        items = self.rules.list_item.findall(captured)

        for captured_item in items:
            item = captured_item[0]
            space = len(item)
            item = self.rules.list_bullet.sub('', item)

            if '\n ' in item:
                space -= len(item)
                item = re.compile(r'^ {1,%d}' % space, flags=re.M).sub('', item)

            node = ListItem()
            node.add_nodes(self.get_lexer().parse(item, self.list_rules))
            result.append(node)
        return result


class ZendeskHelpMdParser(MdParser):
    TAG_CONTENT_GROUP = 'tag_content'
    TAG_PATTERN = r'^\s*(<{tag_name}{attr_re}>(?P<%s>[\s\S]+?)</{tag_name}>)\s*$' % TAG_CONTENT_GROUP
    CALLOUT_STYLE_GROUP = 'style'
    CALLOUT_ATTR_PATTERN = r'( (?P<%s>green|red|yellow))*' % CALLOUT_STYLE_GROUP

    def __init__(self):
        super().__init__()
        self.rules.callout = re.compile(self.TAG_PATTERN.format(
            tag_name='callout',
            attr_re=self.CALLOUT_ATTR_PATTERN,
        ))
        self._active_rules.insert(0, 'callout')

        self.rules.steps = re.compile(self.TAG_PATTERN.format(tag_name='steps', attr_re=''))
        self._active_rules.insert(0, 'steps')

        self.rules.tabs = re.compile(self.TAG_PATTERN.format(tag_name='tabs', attr_re=''))
        self._active_rules.insert(0, 'tabs')

    def parse_callout(self, match: Match[str]) -> None:
        style = match.group(self.CALLOUT_STYLE_GROUP)
        self._parse_nested(ZendeskHelpCallout(style), match)

    def parse_steps(self, match: Match[str]) -> None:
        self._parse_nested(ZendeskHelpSteps(), match)

    def parse_tabs(self, match: Match[str]) -> None:
        self._parse_nested(ZendeskHelpTabs(), match)

    def _parse_nested(self, node: Node, match: Match[str]) -> None:
        nested_nodes = self.get_lexer().parse(match.group(self.TAG_CONTENT_GROUP))
        node.add_nodes(nested_nodes)
        self.tokens.append(node)


def _remove_spaces_from_empty_lines(text):
    return '\n'.join([re.sub(r'^( {1,}|\t{1,})$', '\n', line) for line in text.splitlines()])


def _remove_ltr_rtl_marks(text):
    return re.sub(r'(\u200e|\u200f)', '', text)


def parse(text, parser_cls: type[MdParser] = MdParser):
    text = _remove_spaces_from_empty_lines(text)
    text = _remove_ltr_rtl_marks(text)
    return Root(parser_cls().parse(text))

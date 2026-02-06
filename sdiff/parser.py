import re
import textwrap
from typing import Iterable
from urllib.parse import unquote

import mistune
from mistune import block_parser

from .model import (Html, Image, Link, List, ListItem, NewLine, Paragraph, Root,
                    Text, Header, ZendeskHelpCallout, ZendeskHelpSteps,
                    ZendeskHelpTabs)

_HEADING_LINE_RE = re.compile(r'^(\s*)(#{1,6})(?!#)(?=\S)')
_ATX_HEADING_NO_SPACE_RE = re.compile(r'^(\s{0,3})(#{1,6})(?!#)(?=\S)')
_LIST_ITEM_ATX_HEADING_NO_SPACE_RE = re.compile(r'^(\s{0,3}(?:[*+-]|\d+[.)])\s+)(#{1,6})(?!#)(?=\S)')
_LIST_MARKER_RE = re.compile(r'^\s{0,3}(?:[*+-]|\d+[.)])\s+')
_ORDERED_LIST_MARKER_RE = re.compile(r'^\s{0,3}(\d+)[.)]\s+')
_REF_LINK_OR_IMAGE_RE = re.compile(r'!?\[[^\]]+\]\s*\[[^\]]*\]')
_REF_DEF_LINE_RE = re.compile(r'^\s{0,3}\[[^\]]+\]:\s+\S+')
_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
_FENCE_ONLY_LINE_RE = re.compile(r'^\s*(`{3,}|~{3,})\s*$')
_BLOCKQUOTE_LINE_RE = re.compile(r'^\s{0,3}>\s?.*')
_MISTUNE08_FENCE_BLOCK_RE = re.compile(
    r'^ *(`{3,}|~{3,}) *(\S+)? *\n'  # opening fence (+ optional info)
    r'([\s\S]+?)\s*'                 # content (must be non-empty; mistune 0.x quirk)
    r'\1 *(?:\n+|$)',                # closing fence
    flags=re.M,
)
_INLINE_MARKERS = {
    'strong': '**',
    'emphasis': '*',
    'strikethrough': '~~',
}

_LEGACY_INLINE_TAGS = {
    # Copied from mistune 0.8.1's `_block_tag` negative lookahead.
    'a',
    'em',
    'strong',
    'small',
    's',
    'cite',
    'q',
    'dfn',
    'abbr',
    'data',
    'time',
    'code',
    'var',
    'samp',
    'kbd',
    'sub',
    'sup',
    'i',
    'b',
    'u',
    'mark',
    'ruby',
    'rt',
    'rp',
    'bdi',
    'bdo',
    'span',
    'br',
    'wbr',
    'ins',
    'del',
    'img',
    'font',
}

_MISTUNE_BLOCK_OR_PRE_TAGS = set(block_parser.BLOCK_TAGS) | set(block_parser.PRE_TAGS)

_LEGACY_VALID_ATTR_RE = r"\s*[a-zA-Z\-](?:\=(?:\"[^\"]*\"|'[^']*'|[^\s'\">]+))?"
_LEGACY_BLOCK_TAG_RE = (
    r"(?!(?:%s)\b)\w+(?!:/|[^\w\s@]*@)\b" % "|".join(sorted(_LEGACY_INLINE_TAGS))
)
_LEGACY_BLOCK_HTML_RE = re.compile(
    r'^\s* *(?:'
    r'<!--[\s\S]*?-->'
    r'|<(' + _LEGACY_BLOCK_TAG_RE + r')((?:' + _LEGACY_VALID_ATTR_RE + r')*?)>([\s\S]+?)<\/\1>'
    r'|<' + _LEGACY_BLOCK_TAG_RE + r'(?:' + _LEGACY_VALID_ATTR_RE + r')*?>'
    r') *(?:\n{1,}|\s*$)'
)


def _split_legacy_block_html(raw: str) -> tuple[str, str] | None:
    """Split over-greedy HTML blocks produced by mistune 3.

    Mistune 0.x treats a line like `<callout>` as a single HTML block and continues parsing
    following Markdown lines. Mistune 3 follows CommonMark and may consume subsequent lines
    until a blank line, which changes our structural tree.
    """
    if not raw or '\n' not in raw:
        return None
    match = _LEGACY_BLOCK_HTML_RE.match(raw)
    if match is None:
        return None
    end = match.end()
    if end >= len(raw):
        return None
    return raw[:end], raw[end:]


class _SdiffBlockParser(block_parser.BlockParser):
    """Mistune block parser tweaked for legacy-compat structure diffs.

    The master branch (mistune 0.x) did not treat fenced code blocks or block quotes
    as special blocks. We disable them so they are parsed as normal text and then
    normalized in our conversion layer.
    """

    def parse_fenced_code(self, m, state):  # noqa: ANN001
        return None

    def parse_block_quote(self, m, state):  # noqa: ANN001
        return None

    def parse_raw_html(self, m, state):  # noqa: ANN001
        """Parse raw HTML more like mistune 0.x.

        In mistune 3, unknown tags are "type 7" HTML blocks and may not interrupt
        paragraphs. The legacy mistune 0.x parser used in `master` treats any
        non-inline tag as block HTML and it can interrupt paragraphs.
        """
        marker = m.group(0).strip()

        # Legacy parser does not recognize closing tags alone as block HTML.
        if marker.startswith('</'):
            return None

        # Defer to the upstream implementation for comments and other directives.
        if marker in {'<!--', '<?', '<![CDATA['} or marker.startswith('<!'):
            return super().parse_raw_html(m, state)

        open_tag = marker[1:].lower()
        if open_tag and open_tag not in _MISTUNE_BLOCK_OR_PRE_TAGS and open_tag not in _LEGACY_INLINE_TAGS:
            return block_parser._parse_html_to_newline(state, self.BLANK_LINE)

        return super().parse_raw_html(m, state)


class MdParser:
    """Markdown parser that builds a lightweight structural tree.

    Uses Mistune AST tokens to build sdiff Node objects.
    """
    list_rules = None

    @classmethod
    def get_lexer(cls):
        return cls()

    def __init__(self):
        block = _SdiffBlockParser()
        # Don't recognize fences/quotes as block-level syntax; see _SdiffBlockParser.
        for rule in ('fenced_code', 'block_quote'):
            if rule in block.rules:
                block.rules.remove(rule)

        # In mistune 0.x the list parser does not include the `block_html` / `raw_html`
        # rule, so HTML-like lines inside list items become plain text (not Html nodes)
        # and don't swallow following Markdown.
        if 'raw_html' in getattr(block, 'list_rules', []):
            block.list_rules.remove('raw_html')

        inline = mistune.InlineParser()
        # Prevent code spans from consuming legacy fence markers like ```...```.
        if 'codespan' in inline.rules:
            inline.rules.remove('codespan')

        self._markdown = mistune.Markdown(renderer=None, block=block, inline=inline)
        self._reference_definitions = {}

    def parse(self, text, rules=None):
        """Parse Markdown text into a list of Node objects.

        Args:
            text: Markdown string.
            rules: Optional rules argument kept for compatibility.

        Returns:
            list[Node]
        """
        tokens = self._markdown(text)
        return self._convert_block_tokens(tokens)

    def _set_reference_definitions(self, definitions):
        self._reference_definitions = definitions

    def _convert_block_tokens(self, tokens: Iterable[dict]):
        nodes = []
        for token in tokens:
            nodes.extend(self._convert_block_token(token))
        return nodes

    def _convert_block_token(self, token):
        token_type = token.get('type')
        if token_type == 'paragraph':
            return self._convert_paragraph_token(token.get('children', []))
        if token_type == 'heading':
            return [self._convert_heading(token)]
        if token_type == 'list':
            return [self._convert_list(token)]
        if token_type == 'list_item':
            return [self._convert_list_item(token)]
        if token_type == 'block_text':
            return [self._convert_paragraph_or_heading(token.get('children', []))]
        if token_type == 'block_html':
            return self._convert_block_html(token)
        if token_type == 'block_quote':
            return self._convert_block_quote(token)
        if token_type == 'block_code':
            return self._convert_block_code(token)
        if token_type == 'thematic_break':
            return self._convert_passthrough_block(token)
        return self._convert_passthrough_block(token)

    def _convert_heading(self, token):
        level = token.get('level') or token.get('attrs', {}).get('level', 1)
        header = Header(level)
        header.add_nodes(self._convert_inline_tokens(token.get('children', [])))
        return header

    def _convert_list(self, token):
        ordered = token.get('ordered')
        if ordered is None:
            ordered = token.get('attrs', {}).get('ordered', False)
        list_node = List(bool(ordered))
        for item in token.get('children', []):
            list_node.add_node(self._convert_list_item(item))
        return list_node

    def _convert_block_html(self, token):
        raw = token.get('raw', '')
        if _is_block_html(raw):
            split = _split_legacy_block_html(raw)
            if split is None:
                return [Html(raw)]
            prefix, suffix = split
            nodes = [Html(prefix)]
            if suffix and suffix.strip():
                nodes.extend(self._convert_block_tokens(self._markdown(suffix)))
            return nodes
        text = mistune.escape(raw)
        if text.strip():
            return [Paragraph([Text(text)])]
        return []

    def _convert_passthrough_block(self, token):
        child_nodes = self._convert_block_tokens(token.get('children', []))
        if child_nodes:
            return child_nodes
        raw = token.get('raw') or token.get('text') or ''
        if raw.strip():
            return [Paragraph([Text(mistune.escape(raw))])]
        return []

    def _convert_block_quote(self, token):
        children = token.get('children', [])
        if not children:
            return []
        content = self._render_inline_children(children)
        if not content.strip():
            return []
        lines = content.splitlines()
        quoted = '\n'.join([f'> {line}' if line.strip() else '>' for line in lines])
        return [Paragraph([Text(mistune.escape(quoted))])]

    def _convert_block_code(self, token):
        raw = token.get('raw') or ''
        marker = token.get('marker') or '```'
        fence = marker if marker else '```'
        content = raw.rstrip('\n')
        code_block = f'{fence}\n{content}\n{fence}'
        return [Paragraph([Text(mistune.escape(code_block))])]

    def _render_inline_children(self, children):
        parts = []
        for child in children:
            child_type = child.get('type')
            if child_type in {'paragraph', 'block_text'}:
                parts.append(self._flatten_inline_text(child.get('children', [])))
            else:
                raw = child.get('raw') or child.get('text') or ''
                if raw:
                    parts.append(raw)
        return '\n'.join([part for part in parts if part is not None])

    def _convert_list_item(self, token):
        item = ListItem()
        for child in token.get('children', []):
            child_type = child.get('type')
            if child_type in {'block_text', 'paragraph'}:
                item.add_nodes(self._convert_list_block_nodes(child.get('children', [])))
            elif child_type == 'block_html':
                item.add_nodes(self._convert_list_item_block_html(child))
            else:
                item.add_nodes(self._convert_block_tokens([child]))
        return item

    def _convert_list_item_block_html(self, token):
        # In mistune 0.x the list parser does not include the `block_html` rule,
        # so HTML-like lines inside list items become plain text (not Html nodes).
        raw = token.get('raw', '') or ''
        if not raw.strip():
            return []

        split = _split_legacy_block_html(raw)
        if split is None:
            prefix, suffix = raw, ''
        else:
            prefix, suffix = split

        nodes = []
        _append_text(nodes, mistune.escape(prefix))
        if suffix and suffix.strip():
            nodes.extend(self._convert_list_item_block_html_text(suffix))
        return nodes

    def _convert_list_item_block_html_text(self, text: str):
        nodes = []
        for child in self._markdown(text):
            child_type = child.get('type')
            if child_type in {'block_text', 'paragraph'}:
                nodes.extend(self._convert_list_block_nodes(child.get('children', [])))
            elif child_type == 'heading':
                nodes.append(self._convert_heading(child))
            elif child_type == 'list':
                nodes.append(self._convert_list(child))
            elif child_type == 'list_item':
                nodes.append(self._convert_list_item(child))
            elif child_type == 'block_html':
                nodes.extend(self._convert_list_item_block_html(child))
            else:
                raw = child.get('raw') or child.get('text') or ''
                if raw.strip():
                    _append_text(nodes, mistune.escape(raw))
        return nodes

    def _convert_inline_tokens(self, tokens: Iterable[dict]):
        nodes = []
        buffer = ''

        def flush_buffer():
            nonlocal buffer
            if buffer:
                for part in _split_text_on_legacy_markers(buffer):
                    self._split_reference_links(part, nodes)
                buffer = ''

        handlers = {
            'text': self._handle_inline_text,
            'inline_html': self._handle_inline_text,
            'block_html': self._handle_inline_text,
            'codespan': self._handle_inline_codespan,
            'softbreak': self._handle_inline_softbreak,
            'linebreak': self._handle_inline_linebreak,
            'link': self._handle_inline_link,
            'image': self._handle_inline_image,
            'strong': self._handle_inline_marker,
            'emphasis': self._handle_inline_marker,
            'strikethrough': self._handle_inline_marker,
        }

        for token in tokens:
            token_type = token.get('type')
            handler = handlers.get(token_type)
            if handler:
                buffer = handler(token, nodes, buffer, flush_buffer)
            else:
                buffer = self._handle_inline_other(token, nodes, buffer, flush_buffer)

        flush_buffer()
        return nodes

    def _handle_inline_text(self, token, nodes, buffer, flush_buffer):
        raw = token.get('raw', '')
        buffer += self._reference_definitions.get(raw, raw)
        return buffer

    def _handle_inline_codespan(self, token, nodes, buffer, flush_buffer):
        buffer += f"`{token.get('raw') or token.get('text') or ''}`"
        return buffer

    def _handle_inline_softbreak(self, token, nodes, buffer, flush_buffer):
        buffer += ' '
        return buffer

    def _handle_inline_linebreak(self, token, nodes, buffer, flush_buffer):
        flush_buffer()
        nodes.append(NewLine())
        return ''

    def _handle_inline_link(self, token, nodes, buffer, flush_buffer):
        flush_buffer()
        text = self._flatten_inline_text(token.get('children', []))
        attrs = token.get('attrs', {})
        url = _unquote_url_if_template(attrs.get('url', ''))
        title = attrs.get('title')
        nodes.append(Link(_format_link_markup(text, url, title)))
        return ''

    def _handle_inline_image(self, token, nodes, buffer, flush_buffer):
        flush_buffer()
        alt = token.get('attrs', {}).get('alt') or self._flatten_inline_text(token.get('children', []))
        attrs = token.get('attrs', {})
        url = _unquote_url_if_template(attrs.get('url', ''))
        title = attrs.get('title')
        nodes.append(Image(_format_image_markup(alt, url, title)))
        return ''

    def _handle_inline_marker(self, token, nodes, buffer, flush_buffer):
        flush_buffer()
        marker = _INLINE_MARKERS[token.get('type')]
        _append_text(nodes, marker)
        children = token.get('children', [])
        if children:
            nodes.extend(self._convert_inline_tokens(children))
        _append_text(nodes, marker)
        return ''

    def _handle_inline_other(self, token, nodes, buffer, flush_buffer):
        flush_buffer()
        children = token.get('children', [])
        if children:
            nodes.extend(self._convert_inline_tokens(children))
        else:
            raw = token.get('raw') or token.get('text') or ''
            if raw.strip():
                _append_text(nodes, mistune.escape(raw))
        return ''

    def _flatten_inline_text(self, tokens: Iterable[dict]):
        parts = []
        for token in tokens:
            token_type = token.get('type')
            if token_type in {'text', 'inline_html', 'block_html'}:
                raw = token.get('raw') or token.get('text') or ''
                parts.append(self._reference_definitions.get(raw, raw))
            elif token_type == 'codespan':
                parts.append(f"`{token.get('raw') or token.get('text') or ''}`")
            elif token_type in _INLINE_MARKERS:
                marker = _INLINE_MARKERS[token_type]
                inner = self._flatten_inline_text(token.get('children', []))
                parts.append(f'{marker}{inner}{marker}')
            elif token_type in {'linebreak', 'softbreak'}:
                parts.append(' ')
            else:
                children = token.get('children', [])
                if children:
                    parts.append(self._flatten_inline_text(children))
                else:
                    parts.append(token.get('raw') or token.get('text') or '')
        return ''.join(parts).strip()

    def _convert_paragraph_or_heading(self, inline_tokens: Iterable[dict]):
        ref_text = self._reference_definition_text(inline_tokens)
        if ref_text is not None:
            return Paragraph([Text(ref_text)])
        heading = self._heading_from_inline(inline_tokens)
        if heading:
            return heading
        return Paragraph(self._convert_inline_tokens(inline_tokens))

    def _convert_paragraph_token(self, inline_tokens: Iterable[dict]):
        ref_text = self._reference_definition_text(inline_tokens)
        if ref_text is not None:
            return [Paragraph([Text(ref_text)])]
        heading = self._heading_from_inline(inline_tokens)
        if heading:
            return [heading]

        split = self._split_paragraph_inline_on_fence(inline_tokens)
        if split is not None:
            nodes = []
            for part in split:
                children = self._convert_inline_tokens(part)
                if children:
                    nodes.append(Paragraph(children))
            if nodes:
                return nodes

        return [Paragraph(self._convert_inline_tokens(inline_tokens))]

    def _split_paragraph_inline_on_fence(self, inline_tokens: Iterable[dict]):
        # Legacy mistune 0.x breaks paragraphs when it encounters a fence-only marker
        # line (``` / ~~~), even though we treat fences as plain text blocks.
        if not inline_tokens:
            return None

        lines = [[]]
        seps = []
        for token in inline_tokens:
            token_type = token.get('type')
            if token_type in {'softbreak', 'linebreak'}:
                seps.append(token)
                lines.append([])
            else:
                lines[-1].append(token)

        if len(lines) <= 1:
            return None

        line_texts = [self._flatten_inline_markup(line) for line in lines]

        def fence_marker(tokens):
            raw = self._flatten_inline_markup(tokens).strip()
            match = _FENCE_ONLY_LINE_RE.match(raw)
            if match is None:
                return None
            return match.group(1)

        if fence_marker(lines[0]) is not None:
            return None

        split_idx = None
        for idx in range(1, len(lines)):
            marker = fence_marker(lines[idx])
            if marker is None:
                continue
            # Only split when this fence line begins a complete fence block according
            # to mistune 0.x's `fences` regex. This avoids breaking on sequences like
            # ```\n``` which mistune 0.x does not treat as a fence block (no content).
            tail = '\n'.join(line_texts[idx:])
            if _MISTUNE08_FENCE_BLOCK_RE.match(tail):
                split_idx = idx
                break

        if split_idx is None:
            return None

        first = []
        for idx, line in enumerate(lines[:split_idx]):
            first.extend(line)
            if idx < split_idx - 1:
                first.append(seps[idx])

        second = []
        for line_idx in range(split_idx, len(lines)):
            second.extend(lines[line_idx])
            if line_idx < len(lines) - 1:
                second.append(seps[line_idx])

        parts = []
        if first:
            parts.append(first)
        if second:
            parts.append(second)
        return parts if len(parts) > 1 else None

    def _convert_list_block_nodes(self, inline_tokens: Iterable[dict]):
        text = self._flatten_inline_markup(inline_tokens, softbreak_as_newline=True)
        if not text or not text.strip():
            return []

        nodes = []
        for line in text.splitlines():
            if not line.strip():
                continue

            ref_text = self._reference_definitions.get(line)
            if ref_text is not None:
                nodes.append(Text(ref_text))
                continue

            heading = self._heading_from_inline([{'type': 'text', 'raw': line}])
            if heading:
                nodes.append(heading)
                continue

            nodes.append(Text(mistune.escape(line)))

        return nodes

    def _flatten_inline_markup(self, tokens: Iterable[dict], *, softbreak_as_newline: bool = False):
        parts = []
        for token in tokens:
            token_type = token.get('type')
            if token_type in {'text', 'inline_html', 'block_html'}:
                raw = token.get('raw') or token.get('text') or ''
                parts.append(self._reference_definitions.get(raw, raw))
            elif token_type == 'link':
                label = self._flatten_inline_markup(
                    token.get('children', []),
                    softbreak_as_newline=softbreak_as_newline,
                )
                attrs = token.get('attrs', {})
                url = _unquote_url_if_template(attrs.get('url', ''))
                title = attrs.get('title')
                parts.append(_format_link_markup(label, url, title))
            elif token_type == 'image':
                alt = token.get('attrs', {}).get('alt') or self._flatten_inline_markup(
                    token.get('children', []),
                    softbreak_as_newline=softbreak_as_newline,
                )
                attrs = token.get('attrs', {})
                url = _unquote_url_if_template(attrs.get('url', ''))
                title = attrs.get('title')
                parts.append(_format_image_markup(alt, url, title))
            elif token_type == 'softbreak':
                parts.append('\n' if softbreak_as_newline else ' ')
            elif token_type == 'linebreak':
                parts.append('\n')
            elif token_type == 'codespan':
                parts.append(f"`{token.get('raw') or token.get('text') or ''}`")
            elif token_type in _INLINE_MARKERS:
                marker = _INLINE_MARKERS[token_type]
                inner = self._flatten_inline_markup(
                    token.get('children', []),
                    softbreak_as_newline=softbreak_as_newline,
                )
                parts.append(f'{marker}{inner}{marker}')
            else:
                children = token.get('children', [])
                if children:
                    parts.append(self._flatten_inline_markup(children, softbreak_as_newline=softbreak_as_newline))
                else:
                    parts.append(token.get('raw') or token.get('text') or '')
        return ''.join(parts)

    def _heading_from_inline(self, inline_tokens: Iterable[dict]):
        if len(inline_tokens) != 1:
            return None
        token = inline_tokens[0]
        if token.get('type') != 'text':
            return None
        raw = token.get('raw', '')
        match = _HEADING_LINE_RE.match(raw)
        if not match:
            return None
        level = len(match.group(2))
        content = raw[match.end(2):].lstrip()
        heading_tokens = self._markdown(f"{'#' * level} {content}")
        if heading_tokens and heading_tokens[0].get('type') == 'heading':
            children = heading_tokens[0].get('children', [])
        else:
            children = [{'type': 'text', 'raw': content}]
        header = Header(level)
        header.add_nodes(self._convert_inline_tokens(children))
        return header

    def _reference_definition_text(self, inline_tokens: Iterable[dict]):
        if len(inline_tokens) != 1:
            return None
        token = inline_tokens[0]
        if token.get('type') != 'text':
            return None
        raw = token.get('raw', '')
        return self._reference_definitions.get(raw)

    def _split_reference_links(self, raw: str, nodes):
        last = 0
        for match in _REF_LINK_OR_IMAGE_RE.finditer(raw):
            if match.start() > last:
                _append_text(nodes, mistune.escape(raw[last:match.start()]))
            snippet = match.group(0)
            if snippet.startswith('!['):
                nodes.append(Image(snippet))
            else:
                nodes.append(Link(snippet))
            last = match.end()
        if last < len(raw):
            _append_text(nodes, mistune.escape(raw[last:]))
        return nodes


class ZendeskHelpMdParser(MdParser):
    _CALLOUT_PATTERN_MIN = re.compile(r'(?sm)^[ \t]*<callout(?P<attrs>[^>]*)>(?P<content>.*?)</callout>')
    _CALLOUT_PATTERN_MAX = re.compile(r'(?sm)^[ \t]*<callout(?P<attrs>[^>]*)>(?P<content>.*)</callout>')
    _STEPS_PATTERN_MIN = re.compile(r'(?sm)^[ \t]*<steps>(?P<content>.*?)</steps>')
    _STEPS_PATTERN_MAX = re.compile(r'(?sm)^[ \t]*<steps>(?P<content>.*)</steps>')
    _TABS_PATTERN_MIN = re.compile(r'(?sm)^[ \t]*<tabs>(?P<content>.*?)</tabs>')
    _TABS_PATTERN_MAX = re.compile(r'(?sm)^[ \t]*<tabs>(?P<content>.*)</tabs>')

    def parse(self, text, rules=None):
        """Parse Markdown with Zendesk tag support into a list of Node objects."""
        nodes = self._parse_nodes(text)
        return nodes

    def _parse_nodes(self, text: str):
        nodes = []
        remaining = text
        while remaining:
            tag_name = None
            match = None
            search_at = 0
            while True:
                tag_name, match = self._find_next_tag(remaining, start_at=search_at)
                if not match:
                    break
                absolute_start = (len(text) - len(remaining)) + match.start()
                if _is_inside_list_block(text, absolute_start):
                    # The legacy mistune 0.x list parser treats block-level content
                    # lazily; Zendesk tags that appear inside list items become plain
                    # text and are not recognized structurally. Avoid splitting the
                    # input at such tags, since that would terminate the list early.
                    search_at = match.start() + 1
                    continue
                break
            if not match:
                nodes.extend(self._parse_markdown(_normalize_block_indentation(remaining)))
                break

            if match.start() > 0:
                prefix = remaining[:match.start()]
                nodes.extend(self._parse_markdown(_normalize_block_indentation(prefix)))

            # The legacy parser only recognizes Zendesk tags when they consume the
            # remainder of the current parsing slice (it uses `\\s*$` in the rule
            # regex). Because of this, it will also match *across* multiple tag
            # blocks of the same kind if the last closing tag is at the end.
            #
            # We emulate this by preferring a greedy match when it is terminal.
            terminal_match = None
            tail = remaining[match.start():]
            if tag_name == 'callout':
                m2 = self._CALLOUT_PATTERN_MAX.match(tail)
            elif tag_name == 'steps':
                m2 = self._STEPS_PATTERN_MAX.match(tail)
            else:
                m2 = self._TABS_PATTERN_MAX.match(tail)
            if m2 is not None and not tail[m2.end():].strip():
                terminal_match = m2

            if terminal_match is None:
                # Non-terminal: treat the first (minimal) tag block as opaque HTML.
                nodes.append(Html(match.group(0)))
                remaining = remaining[match.end():]
                continue

            content = terminal_match.group('content')
            trailing = tail[terminal_match.end():]

            if tag_name == 'callout':
                attrs = (terminal_match.group('attrs') or '').strip()
                styles = [part for part in attrs.split() if part]
                if not styles:
                    node = ZendeskHelpCallout(None)
                elif len(styles) == 1 and styles[0] in {'green', 'red', 'yellow'}:
                    node = ZendeskHelpCallout(styles[0])
                else:
                    # Invalid callout attrs: legacy parser does not treat this as a
                    # Zendesk callout block. Keep the first (minimal) tag as opaque
                    # HTML and continue parsing the remaining text.
                    nodes.append(Html(match.group(0)))
                    remaining = remaining[match.end():]
                    continue
            elif tag_name == 'steps':
                node = ZendeskHelpSteps()
            else:
                node = ZendeskHelpTabs()

            node.add_nodes(self._parse_nodes(content))
            nodes.append(node)

            remaining = trailing
        return nodes

    def _find_next_tag(self, text: str, start_at: int = 0):
        best = None
        for name, pattern in (
            ('callout', self._CALLOUT_PATTERN_MIN),
            ('steps', self._STEPS_PATTERN_MIN),
            ('tabs', self._TABS_PATTERN_MIN),
        ):
            for match in pattern.finditer(text, start_at):
                candidate = (match.start(), name, match)
                if best is None or candidate[0] < best[0]:
                    best = candidate
                break

        if best is None:
            return None, None
        _, name, match = best
        return name, match

    def _parse_markdown(self, text: str):
        normalized = _remove_spaces_from_empty_lines(text)
        normalized = _remove_ltr_rtl_marks(normalized)
        return self._convert_block_tokens(self._markdown(normalized))


def _append_text(nodes, text):
    if not text or not text.strip():
        return
    nodes.append(Text(text))


def _split_text_on_legacy_markers(raw: str) -> list[str]:
    """Split text into segments similar to mistune 0.x inline text tokenization.

    The legacy parser splits text at backticks and tildes (it stops before those
    markers and then consumes them as separate text tokens). This matters for our
    structural tree because each segment becomes its own Text node.
    """
    if not raw:
        return []
    markers = ('`', '~')
    out = []
    i = 0
    n = len(raw)
    while i < n:
        j = n
        for m in markers:
            pos = raw.find(m, i + 1)
            if pos != -1 and pos < j:
                j = pos
        out.append(raw[i:j])
        i = j
    return out


def _format_title(title: str) -> str:
    if title is None:
        return ''
    escaped = title.replace('"', '\\"')
    return f' "{escaped}"'


def _unquote_url_if_template(url: str) -> str:
    """Undo Mistune's percent-encoding for template-like URLs.

    Mistune percent-encodes some characters in URLs (e.g. `{{url}}` becomes `%7B%7Burl%7D%7D`).
    For structural diffs we don't care about URL contents, but we do want rendered markup to remain
    readable and close to the original input.
    """
    if not url or '%' not in url:
        return url
    unquoted = unquote(url)
    if unquoted != url and ('{' in unquoted or '}' in unquoted):
        return unquoted
    return url


def _format_link_markup(text: str, url: str, title: str | None) -> str:
    return f'[{text}]({url}{_format_title(title)})'


def _format_image_markup(alt: str, url: str, title: str | None) -> str:
    return f'![{alt}]({url}{_format_title(title)})'


def _is_block_html(raw: str) -> bool:
    stripped = raw.lstrip()
    if stripped.startswith('<!--'):
        return True
    match = re.match(r'<\/?\s*([a-zA-Z0-9]+)', stripped)
    if not match:
        return False
    tag = match.group(1).lower()
    return tag not in _LEGACY_INLINE_TAGS


def _normalize_block_indentation(text: str) -> str:
    dedented = textwrap.dedent(text)
    lines = dedented.splitlines()
    indents = []
    for line in lines:
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith('<'):
            continue
        indent = len(line) - len(stripped)
        indents.append(indent)
    if indents:
        min_indent = min(indents)
        if min_indent:
            lines = [line[min_indent:] if len(line) >= min_indent else line for line in lines]
    return '\n'.join(lines).strip()


def _normalize_atx_heading_spaces(text: str) -> str:
    """Normalize ATX headings that omit the mandatory space after the # markers.

    Mistune 3 follows CommonMark and requires a space: `## Heading`. The legacy parser
    (mistune 0.x) accepted `##Heading` and our fixtures rely on that.

    We also normalize headings that appear right after list markers (e.g. `1. ##Heading`)
    to keep list-item heading parsing compatible.
    """
    output = []
    for line in text.splitlines(True):
        match = _LIST_ITEM_ATX_HEADING_NO_SPACE_RE.match(line)
        if match:
            end = match.end(2)
            line = f'{line[:end]} {line[end:]}'
        else:
            match = _ATX_HEADING_NO_SPACE_RE.match(line)
            if match:
                end = match.end(2)
                line = f'{line[:end]} {line[end:]}'

        output.append(line)
    return ''.join(output)


def _normalize_double_blank_line_list_nesting(text: str) -> str:
    """Emulate mistune 0.x list nesting triggered by double blank lines.

    The legacy parser nests a following list under the previous list item when there
    are two consecutive blank lines between list marker lines. Mistune 3 does not
    do this, so we indent the subsequent marker to force a nested list.
    """
    out = []
    prev_nonblank_was_list = False
    prev_list_indent = 0
    blank_lines = 0
    for line in text.splitlines(True):
        if not line.strip():
            blank_lines += 1
            out.append(line)
            continue

        stripped = line.lstrip(' ')
        current_indent = len(line) - len(stripped)
        is_list = bool(_LIST_MARKER_RE.match(line))
        if is_list and prev_nonblank_was_list and blank_lines >= 2:
            desired_indent = prev_list_indent + 4
            if current_indent < desired_indent:
                line = (' ' * desired_indent) + stripped
                current_indent = desired_indent

        out.append(line)
        prev_nonblank_was_list = is_list
        if is_list:
            prev_list_indent = current_indent
        blank_lines = 0
    return ''.join(out)


def _normalize_ordered_list_marker_interrupts(text: str) -> str:
    """Allow ordered list markers like `2.` to interrupt paragraphs (mistune 0.x compat).

    Mistune 3 follows CommonMark and does not allow an ordered list starting with a
    number other than 1 to interrupt a paragraph. Mistune 0.x is more permissive and
    will start a list for `2.` / `3.` etc.

    To emulate the legacy behavior we insert a blank line before such ordered list
    marker lines when they immediately follow non-list, non-blank text and we're not
    currently inside a list block.
    """
    out = []
    in_list = False
    pending_list_end = False
    prev_blank = True
    prev_was_list_marker = False

    for line in text.splitlines():
        if not line.strip():
            out.append(line)
            prev_blank = True
            prev_was_list_marker = False
            if in_list:
                pending_list_end = True
            continue

        if pending_list_end:
            if line[:1] in {' ', '\t'} or _LIST_MARKER_RE.match(line):
                # Still inside the list block.
                pass
            else:
                in_list = False
            pending_list_end = False

        if in_list and _REF_DEF_LINE_RE.match(line):
            in_list = False

        ordered = _ORDERED_LIST_MARKER_RE.match(line)
        if not in_list and not prev_blank and ordered:
            number = int(ordered.group(1))
            if number != 1 and not prev_was_list_marker:
                out.append('')
                prev_blank = True
                prev_was_list_marker = False

        out.append(line)
        prev_blank = False
        prev_was_list_marker = bool(_LIST_MARKER_RE.match(line))
        if prev_was_list_marker:
            in_list = True

    return '\n'.join(out)


def _normalize_list_lazy_continuations(text: str) -> str:
    """Emulate mistune 0.x lazy list continuations for block-start lines.

    Mistune 3 follows CommonMark and will break a list when it encounters a
    block-start line (e.g. `###### Heading`) that is not indented as a list-item
    continuation. Mistune 0.x is much more permissive and will keep consuming
    unindented lines as part of the current list item until the list is closed
    by a blank line.

    We emulate the legacy behavior by indenting unindented non-marker lines while
    inside a list block so that mistune 3 keeps them as list-item continuation
    lines.
    """
    out = []
    in_list = False
    pending_list_end = False
    continue_prefix = ''

    for raw_line in text.splitlines(True):
        has_nl = raw_line.endswith('\n')
        line = raw_line[:-1] if has_nl else raw_line

        if not line.strip():
            out.append(raw_line)
            if in_list:
                pending_list_end = True
            continue

        if pending_list_end:
            if line[:1] in {' ', '\t'} or _LIST_MARKER_RE.match(line):
                # Still inside the list block.
                pass
            else:
                in_list = False
                continue_prefix = ''
            pending_list_end = False

        marker_match = _LIST_MARKER_RE.match(line)
        if marker_match:
            in_list = True
            continue_prefix = ' ' * marker_match.end()
            out.append(raw_line)
            continue

        # Mistune 0.x list parsing stops before reference definition lines, even
        # without blank lines. Treat those as list terminators so following blocks
        # don't get indented into the list item.
        if in_list and _REF_DEF_LINE_RE.match(line):
            in_list = False
            continue_prefix = ''
            out.append(raw_line)
            continue

        if in_list and line[:1] not in {' ', '\t'}:
            normalized = f'{continue_prefix}{line}'
            if has_nl:
                normalized += '\n'
            out.append(normalized)
            continue

        out.append(raw_line)

    return ''.join(out)


def _extract_reference_definitions(text: str):
    lines = text.splitlines()
    output = []
    definitions = {}
    counter = 0
    for idx, line in enumerate(lines):
        if _REF_DEF_LINE_RE.match(line):
            placeholder = f"SDIFF_REF_DEF_{counter}"
            counter += 1
            definitions[placeholder] = line.strip()
            # The legacy parser treats reference definition lines as their own blocks
            # (even without blank lines) and they must also not become lazy-continuation
            # lines inside list items. Force block separation.
            if output and output[-1].strip():
                output.append('')
            output.append(placeholder)
            # Special-case: When a reference definition is followed by a fence-only line,
            # and after blank lines another fence-only line begins, mistune 0.x tends to
            # split the ref def into its own paragraph (it doesn't keep it glued to the
            # closing fence marker). Insert a blank line after the placeholder to match.
            if idx + 1 < len(lines) and _FENCE_ONLY_LINE_RE.match(lines[idx + 1]):
                j = idx + 2
                # Only split when there is at least one blank line between fences.
                if j < len(lines) and not lines[j].strip():
                    while j < len(lines) and not lines[j].strip():
                        j += 1
                    if j < len(lines) and _FENCE_ONLY_LINE_RE.match(lines[j]):
                        output.append('')
            continue

        output.append(line)

    return '\n'.join(output), definitions


def _is_inside_fenced_block(text: str, offset: int) -> bool:
    fence = None
    fence_len = 0
    running = 0
    for line in text.splitlines(True):
        line_len = len(line)
        if running + line_len > offset:
            return fence is not None
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            marker_len = len(marker)
            if fence is None:
                fence = marker[0]
                fence_len = marker_len
            elif marker[0] == fence and marker_len >= fence_len:
                fence = None
                fence_len = 0
        running += line_len
    return False


def _is_inside_list_block(text: str, offset: int) -> bool:
    """Best-effort mistune 0.x list-block detection.

    Mistune 0.x list parsing is permissive and supports lazy continuation lines.
    For compatibility we treat everything following a list marker as being inside
    the list block until a blank line is followed by a non-indented, non-list
    marker line.

    We also treat reference definition lines as list terminators even without
    blank lines (legacy behavior).
    """
    in_list = False
    pending_list_end = False
    running = 0

    for raw_line in text.splitlines(True):
        line_len = len(raw_line)
        line = raw_line[:-1] if raw_line.endswith('\n') else raw_line

        if not line.strip():
            if in_list:
                pending_list_end = True
            if running + line_len > offset:
                return in_list
            running += line_len
            continue

        if pending_list_end:
            if line[:1] in {' ', '\t'} or _LIST_MARKER_RE.match(line):
                # Still inside the list block.
                pass
            else:
                in_list = False
            pending_list_end = False

        # Mistune 0.x list parsing stops before reference definition lines, even
        # without blank lines.
        if in_list and _REF_DEF_LINE_RE.match(line):
            in_list = False

        line_is_list_marker = bool(_LIST_MARKER_RE.match(line))
        line_in_list = in_list or line_is_list_marker
        if running + line_len > offset:
            return line_in_list

        if line_is_list_marker:
            in_list = True

        running += line_len

    return False


def _remove_spaces_from_empty_lines(text):
    return '\n'.join([re.sub(r'^( {1,}|\t{1,})$', '\n', line) for line in text.splitlines()])


def _remove_ltr_rtl_marks(text):
    return re.sub(r'(\u200e|\u200f)', '', text)


def _normalize_consecutive_fence_lines(text: str) -> str:
    """Split consecutive fence-marker lines into separate blocks.

    The legacy parser tends to break paragraphs at repeated fence marker lines
    like:
        ~~~~
        ~~~~
    We insert a blank line between consecutive fence-only lines to keep block
    structure compatible.
    """
    out = []
    prev_was_fence = False
    for line in text.splitlines():
        is_fence = bool(_FENCE_ONLY_LINE_RE.match(line))
        if is_fence and prev_was_fence and out and out[-1].strip():
            out.append('')
        out.append(line)
        prev_was_fence = is_fence
    return '\n'.join(out)


def _normalize_consecutive_blockquote_lines(text: str) -> str:
    """Split consecutive `>` quote lines into separate blocks.

    Mistune 0.x tends to break paragraphs on each quote-marker line when block quote
    syntax isn't enabled in the lexer. We emulate that by inserting blank lines
    between consecutive quote lines.
    """
    out = []
    in_list = False
    pending_list_end = False
    for line in text.splitlines():
        if not line.strip():
            out.append(line)
            if in_list:
                pending_list_end = True
            continue

        if pending_list_end:
            if line[:1] in {' ', '\t'} or _LIST_MARKER_RE.match(line):
                # Still inside the list block.
                pass
            else:
                in_list = False
            pending_list_end = False

        # Mistune 0.x list parsing stops before reference definition lines, even
        # without blank lines. Treat those as list terminators for normalization
        # purposes.
        if in_list and _REF_DEF_LINE_RE.match(line):
            in_list = False

        is_quote = bool(_BLOCKQUOTE_LINE_RE.match(line))
        if is_quote and out and out[-1].strip() and not in_list:
            out.append('')
        out.append(line)

        if _LIST_MARKER_RE.match(line):
            in_list = True
    return '\n'.join(out)


def _normalize_fence_block_starts(text: str) -> str:
    """Force mistune 0.x paragraph breaks before complete fence blocks.

    Mistune 0.x's `paragraph` regex stops when a *complete* fence block (as defined
    by its `fences` regex) starts on the next line. We disable fence parsing, but
    still need the same paragraph splitting behavior for structural diffs.

    We insert a blank line before any line that begins a fence block according to
    the mistune 0.x `fences` regex.

    NOTE: This is intentionally restricted to non-indented lines to avoid
    perturbing list-item parsing; legacy list items don't use paragraph parsing
    either (they tokenize as plain text).
    """
    if not text:
        return text

    insert_positions = set()
    in_list = False
    pending_list_end = False
    prev_blank = True

    offset = 0
    for raw_line in text.splitlines(True):
        line_start = offset
        offset += len(raw_line)
        line = raw_line[:-1] if raw_line.endswith('\n') else raw_line

        if not line.strip():
            prev_blank = True
            if in_list:
                pending_list_end = True
            continue

        if pending_list_end:
            if line[:1] in {' ', '\t'} or _LIST_MARKER_RE.match(line):
                # Still inside the list block.
                pass
            else:
                in_list = False
            pending_list_end = False

        # Mistune 0.x list parsing stops before reference definition lines, even
        # without blank lines. Treat those as list terminators for normalization
        # purposes.
        if in_list and _REF_DEF_LINE_RE.match(line):
            in_list = False

        if _LIST_MARKER_RE.match(line):
            in_list = True

        first = line[:1]
        if not in_list and not prev_blank and first in {'`', '~'} and first not in {' ', '\t'}:
            if _MISTUNE08_FENCE_BLOCK_RE.match(text, line_start):
                insert_positions.add(line_start)

        prev_blank = False

    if not insert_positions:
        return text

    out = text
    for start in sorted(insert_positions, reverse=True):
        out = out[:start] + '\n' + out[start:]
    return out


def _normalize_fence_only_lines_start_new_paragraphs(text: str) -> str:
    """Force fence-only lines to start new paragraphs like mistune 0.x.

    The legacy parser breaks paragraphs when it encounters a fence-only marker line
    (``` / ~~~) even though it doesn't parse fences as code blocks. Mistune 3 tends to
    keep those markers inside a paragraph when fenced code parsing is disabled.
    """
    out = []
    prev_was_blank = True
    in_fence_paragraph = False
    for line in text.splitlines(True):
        if not line.strip():
            out.append(line)
            prev_was_blank = True
            in_fence_paragraph = False
            continue

        is_fence = bool(_FENCE_ONLY_LINE_RE.match(line))
        if is_fence and not prev_was_blank and not in_fence_paragraph:
            out.append('\n')
            prev_was_blank = True

        out.append(line)
        if prev_was_blank:
            in_fence_paragraph = is_fence
        prev_was_blank = False
    return ''.join(out)


def _merge_adjacent_lists(nodes):
    """Merge directly-adjacent list blocks.

    The legacy parser is quite permissive and tends to merge adjacent lists even
    when bullet markers or orderedness changes. Normalizing this reduces spurious
    structural diffs vs `master`.
    """
    merged = []
    for node in nodes:
        # Recurse first.
        if getattr(node, 'nodes', None):
            node.nodes = _merge_adjacent_lists(node.nodes)

        if merged and isinstance(node, List) and isinstance(merged[-1], List):
            merged[-1].add_nodes(node.nodes)
            continue
        merged.append(node)
    return merged


def parse(text, parser_cls: type[MdParser] = MdParser):
    """Parse Markdown into a Root node using the given parser class."""
    text = _remove_spaces_from_empty_lines(text)
    text = _remove_ltr_rtl_marks(text)
    text = _normalize_atx_heading_spaces(text)
    text = _normalize_double_blank_line_list_nesting(text)
    text = _normalize_ordered_list_marker_interrupts(text)
    text = _normalize_list_lazy_continuations(text)
    text = _normalize_consecutive_blockquote_lines(text)
    text = _normalize_fence_block_starts(text)
    parser = parser_cls()
    if hasattr(parser, '_set_reference_definitions'):
        text, reference_definitions = _extract_reference_definitions(text)
        parser._set_reference_definitions(reference_definitions)
    result = parser.parse(text)
    if isinstance(result, list):
        root = Root(result)
        root.nodes = _merge_adjacent_lists(root.nodes)
        return root
    return result

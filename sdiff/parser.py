import re
import textwrap
from typing import Iterable

import mistune
from mistune import block_parser

from .model import (Html, Image, Link, List, ListItem, NewLine, Paragraph, Root,
                    Text, Header, ZendeskHelpCallout, ZendeskHelpSteps,
                    ZendeskHelpTabs)

_BLOCK_TAGS = {tag.lower() for tag in block_parser.BLOCK_TAGS}
_HEADING_LINE_RE = re.compile(r'^(\s*)(#{1,6})(?!#)(?=\S)')
_REF_LINK_OR_IMAGE_RE = re.compile(r'!?\[[^\]]+\]\s*\[[^\]]*\]')
_REF_DEF_LINE_RE = re.compile(r'^\s{0,3}\[[^\]]+\]:\s+\S+')
_FENCE_RE = re.compile(r'^\s*(`{3,}|~{3,})')
_INLINE_MARKERS = {
    'strong': '**',
    'emphasis': '*',
    'strikethrough': '~~',
}


class MdParser:
    """Markdown parser that builds a lightweight structural tree.

    Uses Mistune AST tokens to build sdiff Node objects.
    """
    list_rules = None

    @classmethod
    def get_lexer(cls):
        return cls()

    def __init__(self):
        self._markdown = mistune.create_markdown(renderer='ast')
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
            return [self._convert_paragraph_or_heading(token.get('children', []))]
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
        if token_type in {'thematic_break', 'block_quote', 'block_code', 'fenced_code'}:
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
            return [Html(raw)]
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

    def _convert_list_item(self, token):
        item = ListItem()
        for child in token.get('children', []):
            child_type = child.get('type')
            if child_type in {'block_text', 'paragraph'}:
                item.add_nodes(self._convert_list_block_nodes(child.get('children', [])))
            else:
                item.add_nodes(self._convert_block_tokens([child]))
        return item

    def _convert_inline_tokens(self, tokens: Iterable[dict]):
        nodes = []
        buffer = ''

        def flush_buffer():
            nonlocal buffer
            if buffer:
                self._split_reference_links(buffer, nodes)
                buffer = ''

        for token in tokens:
            token_type = token.get('type')
            if token_type in {'text', 'inline_html', 'block_html'}:
                buffer += token.get('raw', '')
            elif token_type == 'codespan':
                buffer += f"`{token.get('raw') or token.get('text') or ''}`"
            elif token_type == 'softbreak':
                buffer += ' '
            elif token_type == 'linebreak':
                flush_buffer()
                nodes.append(NewLine())
            elif token_type == 'link':
                flush_buffer()
                text = self._flatten_inline_text(token.get('children', []))
                attrs = token.get('attrs', {})
                url = attrs.get('url', '')
                title = attrs.get('title')
                nodes.append(Link(_format_link_markup(text, url, title)))
            elif token_type == 'image':
                flush_buffer()
                alt = token.get('attrs', {}).get('alt') or self._flatten_inline_text(token.get('children', []))
                attrs = token.get('attrs', {})
                url = attrs.get('url', '')
                title = attrs.get('title')
                nodes.append(Image(_format_image_markup(alt, url, title)))
            elif token_type in _INLINE_MARKERS:
                flush_buffer()
                marker = _INLINE_MARKERS[token_type]
                _append_text(nodes, marker)
                children = token.get('children', [])
                if children:
                    nodes.extend(self._convert_inline_tokens(children))
                _append_text(nodes, marker)
            else:
                flush_buffer()
                children = token.get('children', [])
                if children:
                    nodes.extend(self._convert_inline_tokens(children))
                else:
                    raw = token.get('raw') or token.get('text') or ''
                    if raw.strip():
                        _append_text(nodes, mistune.escape(raw))

        flush_buffer()
        return nodes

    def _flatten_inline_text(self, tokens: Iterable[dict]):
        parts = []
        for token in tokens:
            token_type = token.get('type')
            if token_type in {'text', 'inline_html', 'block_html'}:
                parts.append(token.get('raw') or token.get('text') or '')
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

    def _convert_list_block_nodes(self, inline_tokens: Iterable[dict]):
        heading = self._heading_from_inline(inline_tokens)
        if heading:
            return [heading]
        return self._convert_inline_tokens(inline_tokens)

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
    _CALLOUT_PATTERN = re.compile(
        r'(?s)<callout(?:\s+(?P<style>green|red|yellow))?>(?P<content>.*?)</callout>'
    )
    _STEPS_PATTERN = re.compile(r'(?s)<steps>(?P<content>.*?)</steps>')
    _TABS_PATTERN = re.compile(r'(?s)<tabs>(?P<content>.*?)</tabs>')

    def parse(self, text, rules=None):
        """Parse Markdown with Zendesk tag support into a list of Node objects."""
        nodes = self._parse_nodes(text)
        return nodes

    def _parse_nodes(self, text: str):
        nodes = []
        remaining = text
        while remaining:
            tag_name, match = self._find_next_tag(remaining)
            if not match:
                nodes.extend(self._parse_markdown(_normalize_block_indentation(remaining)))
                break

            if match.start() > 0:
                prefix = remaining[:match.start()]
                nodes.extend(self._parse_markdown(_normalize_block_indentation(prefix)))

            content = match.group('content')
            if tag_name == 'callout':
                node = ZendeskHelpCallout(match.group('style'))
            elif tag_name == 'steps':
                node = ZendeskHelpSteps()
            else:
                node = ZendeskHelpTabs()

            node.add_nodes(self._parse_nodes(content))
            nodes.append(node)

            remaining = remaining[match.end():]
        return nodes

    def _find_next_tag(self, text: str):
        matches = []
        for name, pattern in (
            ('callout', self._CALLOUT_PATTERN),
            ('steps', self._STEPS_PATTERN),
            ('tabs', self._TABS_PATTERN),
        ):
            match = pattern.search(text)
            if match:
                matches.append((match.start(), name, match))
        if not matches:
            return None, None
        matches.sort(key=lambda item: item[0])
        for _, name, match in matches:
            if not _is_inside_fenced_block(text, match.start()):
                return name, match
        return None, None

    def _parse_markdown(self, text: str):
        normalized = _remove_spaces_from_empty_lines(text)
        normalized = _remove_ltr_rtl_marks(normalized)
        return self._convert_block_tokens(self._markdown(normalized))


def _append_text(nodes, text):
    if not text:
        return
    if nodes and isinstance(nodes[-1], Text):
        nodes[-1].text += text
    else:
        nodes.append(Text(text))


def _format_title(title: str) -> str:
    if title is None:
        return ''
    escaped = title.replace('"', '\\"')
    return f' "{escaped}"'


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
    return match.group(1).lower() in _BLOCK_TAGS


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


def _extract_reference_definitions(text: str):
    lines = text.splitlines()
    output = []
    definitions = {}
    fence = None
    fence_len = 0
    counter = 0
    for line in lines:
        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            marker_len = len(marker)
            marker_char = marker[0]
            if fence is None:
                fence = marker_char
                fence_len = marker_len
            elif marker_char == fence and marker_len >= fence_len:
                fence = None
                fence_len = 0
            output.append(line)
            continue

        if fence is None and _REF_DEF_LINE_RE.match(line):
            placeholder = f"SDIFF_REF_DEF_{counter}"
            counter += 1
            definitions[placeholder] = line.strip()
            output.append(placeholder)
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


def _remove_spaces_from_empty_lines(text):
    return '\n'.join([re.sub(r'^( {1,}|\t{1,})$', '\n', line) for line in text.splitlines()])


def _remove_ltr_rtl_marks(text):
    return re.sub(r'(\u200e|\u200f)', '', text)


def parse(text, parser_cls: type[MdParser] = MdParser):
    """Parse Markdown into a Root node using the given parser class."""
    text = _remove_spaces_from_empty_lines(text)
    text = _remove_ltr_rtl_marks(text)
    parser = parser_cls()
    if hasattr(parser, '_set_reference_definitions'):
        text, reference_definitions = _extract_reference_definitions(text)
        parser._set_reference_definitions(reference_definitions)
    result = parser.parse(text)
    if isinstance(result, list):
        return Root(result)
    return result

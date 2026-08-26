"""Build deterministic, exact sdiff behavior signatures.

The signature records both parsed trees, rendered output, diff output, and
exception details.  Canonical SHA-256 digests make the complete oracle result
small enough to run as part of the normal test suite.
"""

import hashlib
import itertools
import json


def node_signature(node):
    if isinstance(node, dict):
        return {
            'type': 'non-node-dict',
            'value': node,
        }
    signature = {
        'type': type(node).__name__,
        'name': node.name,
        'symbol': node.symbol,
        'string': str(node),
        'meta': dict(sorted(node.meta.items())),
        'nodes': [node_signature(child) for child in node.nodes],
    }
    for attribute in ('level', 'ordered', 'style', 'text'):
        if hasattr(node, attribute):
            signature[attribute] = getattr(node, attribute)
    return signature


def error_signature(error):
    return {
        'type': type(error).__name__,
        'message': error.message,
        'node': node_signature(error.node),
    }


def capture(function):
    try:
        return {
            'status': 'ok',
            'value': function(),
        }
    except Exception as error:  # pragma: no cover - exercised through signatures
        return {
            'status': 'error',
            'error_type': type(error).__name__,
            'error_message': str(error),
        }


def parse_signature(source, parser_cls, parser):
    tree = parser.parse(source, parser_cls=parser_cls)
    return {
        'tree': node_signature(tree),
        'structure': tree.print_all(),
    }


def render_signature(source, parser_cls, parser, renderer):
    tree = parser.parse(source, parser_cls=parser_cls)
    return renderer.render(tree)


def diff_signature(left, right, parser_cls, sdiff, renderer):
    left_output, right_output, errors = sdiff.diff(
        left,
        right,
        renderer=renderer,
        parser_cls=parser_cls,
    )
    return {
        'left': left_output,
        'right': right_output,
        'errors': [error_signature(error) for error in errors],
    }


def tree_diff_signature(left, right, parser_cls, parser, diff_function):
    left_tree = parser.parse(left, parser_cls=parser_cls)
    right_tree = parser.parse(right, parser_cls=parser_cls)
    left_tree, right_tree, errors = diff_function(left_tree, right_tree)
    return {
        'left_tree': node_signature(left_tree),
        'right_tree': node_signature(right_tree),
        'errors': [error_signature(error) for error in errors],
    }


def _document_signature(case, sdiff, parser, HtmlRenderer, TextRenderer):
    parser_cls = getattr(sdiff, case['parser'])
    left = case['left']
    right = case.get('right', left)
    return {
        'left_parse': capture(lambda: parse_signature(left, parser_cls, parser)),
        'right_parse': capture(lambda: parse_signature(right, parser_cls, parser)),
        'left_text_render': capture(
            lambda: render_signature(left, parser_cls, parser, TextRenderer())
        ),
        'right_text_render': capture(
            lambda: render_signature(right, parser_cls, parser, TextRenderer())
        ),
        'left_html_render': capture(
            lambda: render_signature(left, parser_cls, parser, HtmlRenderer())
        ),
        'right_html_render': capture(
            lambda: render_signature(right, parser_cls, parser, HtmlRenderer())
        ),
        'text_diff': capture(
            lambda: diff_signature(left, right, parser_cls, sdiff, TextRenderer())
        ),
        'html_diff': capture(
            lambda: diff_signature(left, right, parser_cls, sdiff, HtmlRenderer())
        ),
        'struct_diff': capture(
            lambda: tree_diff_signature(left, right, parser_cls, parser, sdiff.diff_struct)
        ),
        'link_diff': capture(
            lambda: tree_diff_signature(left, right, parser_cls, parser, sdiff.diff_links)
        ),
    }


def _reused_parser_signature(case, sdiff, parser):
    parser_cls = getattr(sdiff, case['parser'])
    if case['scenario'] == 'reuse_inline_parser':
        instance = parser.InlineLexer()
    else:
        instance = parser_cls()

    first_result = instance(case['left'])
    first_signature = [node_signature(node) for node in first_result]
    second_result = instance(case['right'])
    return {
        'first_result_before_reuse': first_signature,
        'second_result': [node_signature(node) for node in second_result],
        'same_result_object': first_result is second_result,
        'tokens_are_result': instance.tokens is second_result,
    }


def _rule_selection_signature(case, sdiff, parser):
    results = {}
    for operation in case['operations']:
        if case['scenario'] == 'inline_rule_selection':
            instance = parser.InlineLexer()
        else:
            instance = getattr(sdiff, case['parser'])()
        parse_method = instance if operation.get('call') else instance.parse
        results[operation['name']] = capture(
            lambda method=parse_method, item=operation: [
                node_signature(node)
                for node in method(item['source'], item.get('rules'))
            ]
        )
    return results


def _preprocessing_signature(case, sdiff, parser):
    parser_cls = getattr(sdiff, case['parser'])
    direct_nodes = parser_cls().parse(case['left'])
    public_tree = parser.parse(case['left'], parser_cls=parser_cls)
    return {
        'direct_nodes': [node_signature(node) for node in direct_nodes],
        'public_tree': node_signature(public_tree),
        'lexer_type': type(parser_cls.get_lexer()).__name__,
    }


def _matrix_signature(sources, sdiff, parser):
    digest = hashlib.sha256()
    count = 0
    for source in sources:
        signature = capture(lambda item=source: parse_signature(item, sdiff.MdParser, parser))
        payload = json.dumps(
            [source, signature],
            ensure_ascii=False,
            separators=(',', ':'),
            sort_keys=True,
        ).encode('utf-8')
        digest.update(len(payload).to_bytes(8, byteorder='big'))
        digest.update(payload)
        count += 1
    return {
        'case_count': count,
        'sha256': digest.hexdigest(),
    }


def _link_label_matrix_sources():
    for length in range(6):
        for characters in itertools.product('[]^a\\', repeat=length):
            label = ''.join(characters)
            yield f'[{label}](u)'
            yield f'![{label}](u)'
            yield f'[{label}][r]'
            yield f'![{label}][r]'


def _link_tail_matrix_sources():
    for length in range(6):
        for characters in itertools.product('<>)\'" a', repeat=length):
            suffix = ''.join(characters)
            yield '[x](' + suffix
            yield '![x](' + suffix
        for characters in itertools.product('[]^ a', repeat=length):
            suffix = ''.join(characters)
            yield '[x]' + suffix
            yield '![x]' + suffix


def run_case(case, sdiff, parser, HtmlRenderer, TextRenderer):
    scenario = case.get('scenario', 'documents')
    if scenario in ('reuse_block_parser', 'reuse_inline_parser'):
        return capture(lambda: _reused_parser_signature(case, sdiff, parser))
    if scenario in ('block_rule_selection', 'inline_rule_selection'):
        return capture(lambda: _rule_selection_signature(case, sdiff, parser))
    if scenario == 'preprocessing_boundary':
        return capture(lambda: _preprocessing_signature(case, sdiff, parser))
    if scenario == 'link_label_matrix':
        return _matrix_signature(_link_label_matrix_sources(), sdiff, parser)
    if scenario == 'link_tail_matrix':
        return _matrix_signature(_link_tail_matrix_sources(), sdiff, parser)
    if scenario != 'documents':
        raise ValueError(f"Unknown compatibility scenario: {scenario}")
    return _document_signature(case, sdiff, parser, HtmlRenderer, TextRenderer)


def canonical_hash(value):
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(',', ':'),
        sort_keys=True,
    ).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()

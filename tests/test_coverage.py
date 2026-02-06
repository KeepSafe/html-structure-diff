from unittest import TestCase

import sdiff.compare as compare_mod
from sdiff import MdParser, parser
from sdiff.compare import diff_struct
from sdiff.errors import InsertError
from sdiff.model import Header, Link, List, ListItem, NewLine, Root, Text, ZendeskHelpCallout
from sdiff.renderer import TextRenderer
from tests.fixtures import trees


class TestCoverageMisc(TestCase):
    def test_diff_error_str_uses_message(self):
        err = InsertError(Text("x"))
        self.assertIn("missing element", str(err))

    def test_node_str_repr_and_eq(self):
        node = Root([Text("x")])
        self.assertTrue(str(node))
        self.assertIn("root", repr(node))
        self.assertNotEqual(node, "not-a-node")

    def test_header_str_repr(self):
        header = Header(3, [Text("x")])
        self.assertEqual("3", str(header))
        self.assertIn("level", repr(header))

    def test_list_and_link_repr_and_eq_branches(self):
        self.assertFalse(List(False) == "nope")  # noqa: E711
        self.assertIn("ordered", repr(List(False)))
        self.assertIn("link", repr(Link("x")))
        self.assertIn("new-line", repr(NewLine()))
        self.assertIn("callout", repr(ZendeskHelpCallout("green")))
        self.assertFalse(ZendeskHelpCallout("green") == "nope")  # noqa: E711

    def test_fixture_empty_tree(self):
        self.assertEqual("", trees.empty_tree().print_all())

    def test_diff_struct_ignores_single_space_nodes(self):
        # Cover the "ignore single space errors" branch in compare.py.
        tree1 = Root([Text(" "), Text("x")])
        tree2 = Root([Text("x")])
        _, _, errors = diff_struct(tree1, tree2)
        self.assertEqual(0, len(errors))

    def test_apply_diff_ranges_ignores_single_space_nodes(self):
        # Cover the "ignore single space errors" branches in compare.py explicitly.
        delete_only = [("x", 0, 1, 0, 0)]
        insert_only = [("x", 0, 0, 0, 1)]

        errors = compare_mod._apply_diff_ranges(delete_only, [Text(" ")], [])
        self.assertEqual([], errors)

        errors = compare_mod._apply_diff_ranges(insert_only, [], [Text(" ")])
        self.assertEqual([], errors)

        errors = compare_mod._apply_diff_ranges(delete_only, [Text("x")], [])
        self.assertEqual(1, len(errors))
        self.assertIn("additional element", str(errors[0]))

        errors = compare_mod._apply_diff_ranges(insert_only, [], [Text("x")])
        self.assertEqual(1, len(errors))
        self.assertIn("missing element", str(errors[0]))


class TestCoverageParserHelpers(TestCase):
    def test_split_legacy_block_html_variants(self):
        self.assertIsNone(parser._split_legacy_block_html(""))
        self.assertIsNone(parser._split_legacy_block_html("not html\n"))

        # Exact match should return None (no suffix to split).
        self.assertIsNone(parser._split_legacy_block_html("<div>hi</div>\n"))

        prefix, suffix = parser._split_legacy_block_html("<div>hi</div>\n\nnext")
        self.assertTrue(prefix.startswith("<div>hi</div>"))
        self.assertEqual("next", suffix)

    def test_block_parser_disabled_rules_return_none(self):
        block = parser._SdiffBlockParser()
        self.assertIsNone(block.parse_fenced_code(None, None))
        self.assertIsNone(block.parse_block_quote(None, None))

    def test_mdparser_get_lexer_returns_instance(self):
        self.assertIsInstance(MdParser.get_lexer(), MdParser)

    def test_split_text_on_legacy_markers(self):
        self.assertEqual([], parser._split_text_on_legacy_markers(""))
        self.assertEqual(["a", "`b", "`c"], parser._split_text_on_legacy_markers("a`b`c"))

    def test_unquote_url_if_template(self):
        url = "https://example.com/%7B%7Burl%7D%7D"
        self.assertIn("{{url}}", parser._unquote_url_if_template(url))
        # Percent-encoded but not template-like => keep as-is.
        self.assertEqual("https://example.com/%2F", parser._unquote_url_if_template("https://example.com/%2F"))

    def test_is_block_html(self):
        self.assertTrue(parser._is_block_html("<!-- hi -->"))
        self.assertFalse(parser._is_block_html("<sub>text</sub>"))
        self.assertTrue(parser._is_block_html("<div>text</div>"))
        self.assertFalse(parser._is_block_html("nope"))

    def test_normalize_block_indentation(self):
        # Only non-HTML lines should be considered for min-indent normalization.
        raw = "    <div>\n        x\n    </div>\n        y"
        normalized = parser._normalize_block_indentation(raw)
        self.assertIn("y", normalized)

    def test_extract_reference_definitions_fence_special_case(self):
        raw = "[id]: https://example.com\n```\n\n```"
        text, defs = parser._extract_reference_definitions(raw)
        self.assertEqual(1, len(defs))
        # The special-case inserts a blank line after the placeholder.
        self.assertTrue(text.startswith("SDIFF_REF_DEF_0\n\n"))

    def test_extract_reference_definitions_fence_special_case_not_triggered_without_blank_line(self):
        raw = "[id]: https://example.com\n```\n```"
        text, defs = parser._extract_reference_definitions(raw)
        self.assertEqual(1, len(defs))
        self.assertEqual("SDIFF_REF_DEF_0\n```\n```", text)

    def test_is_inside_fenced_block(self):
        raw = "```\ncode\n```\noutside"
        # Offset inside "code".
        self.assertTrue(parser._is_inside_fenced_block(raw, raw.index("code")))
        # Offset inside "outside".
        self.assertFalse(parser._is_inside_fenced_block(raw, raw.index("outside")))
        # Offset past end => fall through.
        self.assertFalse(parser._is_inside_fenced_block(raw, len(raw) + 1))

    def test_is_inside_list_block(self):
        raw = "- a\n  b\n\nc"
        self.assertTrue(parser._is_inside_list_block(raw, raw.index("b")))
        self.assertFalse(parser._is_inside_list_block(raw, raw.index("c")))
        # Offset past end => fall through.
        self.assertFalse(parser._is_inside_list_block(raw, len(raw) + 1))

    def test_normalize_consecutive_fence_lines(self):
        raw = "```\n```\ntext"
        normalized = parser._normalize_consecutive_fence_lines(raw)
        self.assertIn("```\n\n```", normalized)

    def test_normalize_consecutive_blockquote_lines(self):
        raw = "> a\n> b\nc"
        normalized = parser._normalize_consecutive_blockquote_lines(raw)
        self.assertIn("> a\n\n> b", normalized)

    def test_normalize_fence_only_lines_start_new_paragraphs(self):
        raw = "a\n```\nb"
        normalized = parser._normalize_fence_only_lines_start_new_paragraphs(raw)
        self.assertIn("a\n\n```", normalized)
        # Blank line resets state.
        normalized = parser._normalize_fence_only_lines_start_new_paragraphs("a\n\n```\n\n```")
        self.assertIn("\n\n```\n\n```", normalized)

    def test_normalize_double_blank_line_list_nesting_does_not_overindent(self):
        raw = "* a\n\n\n    * b\n"
        normalized = parser._normalize_double_blank_line_list_nesting(raw)
        self.assertEqual(raw, normalized)

    def test_merge_adjacent_lists(self):
        l1 = List(False, [ListItem([Text("a")])])
        l2 = List(True, [ListItem([Text("b")])])
        root = Root([l1, l2])
        merged = parser._merge_adjacent_lists(root.nodes)
        self.assertEqual(1, len(merged))
        self.assertEqual(2, len(merged[0].nodes))

    def test_parse_passthrough_when_parser_returns_non_list(self):
        class _Dummy(MdParser):
            def parse(self, text, rules=None):  # noqa: ANN001
                return Root([Text("x")])

        parsed = parser.parse("x", parser_cls=_Dummy)
        self.assertIsInstance(parsed, Root)


class TestCoverageParserConversions(TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.p = MdParser()

    def test_convert_block_token_branches(self):
        item = self.p._convert_block_token(
            {
                "type": "list_item",
                "children": [{"type": "paragraph", "children": [{"type": "text", "raw": "x"}]}],
            }
        )[0]
        self.assertEqual("list-item", item.name)

        block_text = self.p._convert_block_token({"type": "block_text", "children": [{"type": "text", "raw": "x"}]})[0]
        self.assertEqual("paragraph", block_text.name)

        quote = self.p._convert_block_token(
            {"type": "block_quote", "children": [{"type": "paragraph", "children": [{"type": "text", "raw": "q"}]}]}
        )[0]
        self.assertEqual("paragraph", quote.name)
        self.assertIn("&gt;", quote.nodes[0].text)

        code = self.p._convert_block_token({"type": "block_code", "raw": "code\n", "marker": "```"})[0]
        self.assertTrue(code.nodes[0].text.startswith("```"))

    def test_convert_list_ordered_attr_fallback(self):
        lst = self.p._convert_list({"type": "list", "attrs": {"ordered": True}, "children": []})
        self.assertTrue(lst.ordered)

    def test_convert_block_html_with_suffix(self):
        token = {"type": "block_html", "raw": "<div>hi</div>\n\ntext"}
        nodes = self.p._convert_block_html(token)
        self.assertEqual("html", nodes[0].name)
        self.assertEqual("paragraph", nodes[1].name)

        # Split happens, but suffix is whitespace-only => no extra nodes.
        token = {"type": "block_html", "raw": "<div>hi</div>\n\n   "}
        nodes = self.p._convert_block_html(token)
        self.assertEqual(1, len(nodes))

        # Whitespace-only raw => empty conversion.
        self.assertEqual([], self.p._convert_block_html({"type": "block_html", "raw": "  "}))

    def test_convert_passthrough_block_children_and_raw(self):
        out = self.p._convert_passthrough_block(
            {"type": "unknown", "children": [{"type": "paragraph", "children": [{"type": "text", "raw": "x"}]}]}
        )
        self.assertEqual("paragraph", out[0].name)
        out2 = self.p._convert_passthrough_block({"type": "unknown", "raw": "raw"})
        self.assertEqual("paragraph", out2[0].name)

    def test_convert_block_quote_early_returns(self):
        self.assertEqual([], self.p._convert_block_quote({"type": "block_quote", "children": []}))
        self.assertEqual(
            [],
            self.p._convert_block_quote({"type": "block_quote", "children": [{"type": "paragraph", "children": []}]}),
        )

    def test_render_inline_children_unknown_child_type(self):
        out = self.p._render_inline_children([{"type": "thematic_break", "raw": "---"}])
        self.assertEqual("---", out)

    def test_inline_other_and_codespan_text_fallback(self):
        tokens = [{"type": "codespan", "text": "x"}, {"type": "unknown", "raw": "<x>"}]
        out = self.p._convert_inline_tokens(tokens)
        self.assertEqual("`x`&lt;x&gt;", "".join(node.text for node in out))

    def test_inline_marker_without_children_and_inline_other_with_children(self):
        out = self.p._convert_inline_tokens([{"type": "strong", "children": []}])
        self.assertEqual(["text", "text"], [n.name for n in out])

        out = self.p._convert_inline_tokens([{"type": "unknown", "children": [{"type": "text", "raw": "x"}]}])
        self.assertEqual("x", out[0].text)

        out = self.p._convert_inline_tokens([{"type": "unknown", "raw": " "}])
        self.assertEqual([], out)

    def test_flatten_inline_text_unknown_branches(self):
        text = self.p._flatten_inline_text(
            [
                {"type": "codespan", "raw": "x"},
                {"type": "unknown", "children": [{"type": "text", "raw": "y"}]},
                {"type": "unknown", "raw": "z"},
            ]
        )
        self.assertIn("`x`", text)
        self.assertTrue(text.endswith("z"))

    def test_flatten_inline_markup_link_and_image(self):
        tokens = [
            {"type": "text", "raw": "a"},
            {"type": "softbreak"},
            {"type": "link", "children": [{"type": "text", "raw": "L"}], "attrs": {"url": "%7B%7Burl%7D%7D"}},
            {"type": "softbreak"},
            {"type": "image", "children": [{"type": "text", "raw": "A"}], "attrs": {"url": "u", "title": 't"'}},
        ]
        s = self.p._flatten_inline_markup(tokens, softbreak_as_newline=True)
        self.assertIn("[L]({{url}})", s)
        self.assertIn('![A](u "t\\"")', s)

    def test_flatten_inline_markup_unknown_branches(self):
        tokens = [
            {"type": "unknown", "children": [{"type": "text", "raw": "x"}]},
            {"type": "unknown", "raw": "y"},
        ]
        s = self.p._flatten_inline_markup(tokens)
        self.assertEqual("xy", s)

    def test_convert_list_block_nodes_ref_heading_and_text(self):
        self.p._set_reference_definitions(
            {
                "SDIFF_REF_DEF_0": "[id]: https://example.com",
                "[id]: https://example.com": "[id]: https://example.com",
            }
        )
        tokens = [
            {"type": "text", "raw": "SDIFF_REF_DEF_0"},
            {"type": "softbreak"},
            {"type": "text", "raw": "###header"},
            {"type": "softbreak"},
            {"type": "text", "raw": " "},
            {"type": "softbreak"},
            {"type": "text", "raw": "plain"},
        ]
        nodes = self.p._convert_list_block_nodes(tokens)
        self.assertEqual(["text", "header", "text"], [n.name for n in nodes])

    def test_convert_list_block_nodes_empty(self):
        self.assertEqual([], self.p._convert_list_block_nodes([]))

    def test_heading_from_inline_fallback_branch(self):
        class _NoHeading(MdParser):
            def __init__(self):
                super().__init__()
                self._markdown = lambda _: [{"type": "paragraph", "children": []}]  # noqa: E731

        p = _NoHeading()
        heading = p._heading_from_inline([{"type": "text", "raw": "###header"}])
        self.assertEqual("header", heading.name)
        self.assertEqual("text", heading.nodes[0].name)

    def test_convert_paragraph_or_heading_ref_and_heading(self):
        self.p._set_reference_definitions({"SDIFF_REF_DEF_0": "[id]: https://example.com"})
        node = self.p._convert_paragraph_or_heading([{"type": "text", "raw": "SDIFF_REF_DEF_0"}])
        self.assertEqual("paragraph", node.name)

        node = self.p._convert_paragraph_or_heading([{"type": "text", "raw": "###header"}])
        self.assertEqual("header", node.name)

        node = self.p._convert_paragraph_token([{"type": "text", "raw": "###header"}])[0]
        self.assertEqual("header", node.name)

    def test_split_paragraph_inline_on_fence_variants(self):
        self.assertIsNone(self.p._split_paragraph_inline_on_fence([]))
        self.assertIsNone(self.p._split_paragraph_inline_on_fence([{"type": "text", "raw": "x"}]))

        # First line is a fence-only marker => do not split.
        tokens = [{"type": "text", "raw": "```"}, {"type": "softbreak"}, {"type": "text", "raw": "x"}]
        self.assertIsNone(self.p._split_paragraph_inline_on_fence(tokens))

        # Tail is fence markers but not a complete fence block => do not split.
        tokens = [
            {"type": "text", "raw": "a"},
            {"type": "softbreak"},
            {"type": "text", "raw": "```"},
            {"type": "softbreak"},
            {"type": "text", "raw": "```"},
        ]
        self.assertIsNone(self.p._split_paragraph_inline_on_fence(tokens))

        # Complete fence block tail => split.
        tokens = [
            {"type": "text", "raw": "a"},
            {"type": "softbreak"},
            {"type": "text", "raw": "```"},
            {"type": "softbreak"},
            {"type": "text", "raw": "code"},
            {"type": "softbreak"},
            {"type": "text", "raw": "```"},
        ]
        parts = self.p._split_paragraph_inline_on_fence(tokens)
        self.assertEqual(2, len(parts))

        nodes = self.p._convert_paragraph_token(tokens)
        self.assertEqual(2, len(nodes))

    def test_split_paragraph_inline_on_fence_first_part_includes_seps(self):
        tokens = [
            {"type": "text", "raw": "a"},
            {"type": "softbreak"},
            {"type": "text", "raw": "b"},
            {"type": "softbreak"},
            {"type": "text", "raw": "```"},
            {"type": "softbreak"},
            {"type": "text", "raw": "code"},
            {"type": "softbreak"},
            {"type": "text", "raw": "```"},
        ]
        parts = self.p._split_paragraph_inline_on_fence(tokens)
        self.assertEqual(2, len(parts))

    def test_convert_list_item_block_html_text_smoke(self):
        # Exercise conversion of text following a (hypothetical) HTML block inside a list item.
        nodes = self.p._convert_list_item_block_html_text("text\n\n# h\n\n- a\n")
        self.assertTrue(any(n.name == "header" for n in nodes))
        self.assertTrue(any(n.name == "list" for n in nodes))

    def test_convert_list_item_with_block_html_child(self):
        token = {
            "type": "list_item",
            "children": [
                {"type": "block_html", "raw": "<div>hi</div>"},
            ],
        }
        item = self.p._convert_list_item(token)
        self.assertTrue(item.nodes)

    def test_convert_list_item_block_html_variants(self):
        self.assertEqual([], self.p._convert_list_item_block_html({"type": "block_html", "raw": "  "}))

        nodes = self.p._convert_list_item_block_html({"type": "block_html", "raw": "not html\n"})
        self.assertTrue(nodes)

        nodes = self.p._convert_list_item_block_html({"type": "block_html", "raw": "<div>hi</div>\n\n   "})
        self.assertTrue(nodes)

    def test_convert_list_item_block_html_text_with_block_html_and_raw(self):
        nodes = self.p._convert_list_item_block_html_text("<div>hi</div>\n\n---\n")
        self.assertTrue(any(n.name == "text" for n in nodes))

    def test_convert_list_item_block_html_smoke(self):
        token = {"type": "block_html", "raw": "<div>hi</div>\n\ntext"}
        nodes = self.p._convert_list_item_block_html(token)
        self.assertTrue(any(isinstance(n, Text) for n in nodes))

    def test_rendering_roundtrip_smoke(self):
        md = "some text [link](url) new text"
        tree = parser.parse(md, parser_cls=MdParser)
        self.assertEqual(md, TextRenderer().render(tree))

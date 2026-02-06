# md-sdiff

Structural diffs for Markdown. The library parses two Markdown inputs into a lightweight tree and compares the *shape* (headings, lists, paragraphs, links, etc.) instead of the text content. This is useful when you expect the same document structure across translations or when you want to validate formatting consistency without caring about the wording.

## What it does
- Parses Markdown into an AST-like node tree using `mistune`.
- Compares trees node-by-node and flags insertions/deletions in structure.
- Returns a rendered view of each document plus a list of structural errors.
- Supports a Zendesk-specific parser (`ZendeskHelpMdParser`) for `<callout>`, `<steps>`, and `<tabs>` blocks.

## Example usage
```python
from sdiff import diff, TextRenderer, MdParser

left = "# Title\n\n- One\n- Two"
right = "# Title\n\n- One\n- Two\n- Three"

rendered_left, rendered_right, errors = diff(left, right, renderer=TextRenderer(), parser_cls=MdParser)
print(errors[0])  # "There is a missing element `li`."
```

## Renderers
`TextRenderer` returns the original Markdown structure as text. `HtmlRenderer` wraps the output and marks structural insertions/deletions with `<ins>` and `<del>`.

## One-off usage
```sh
python - <<'PY'
from sdiff import diff, TextRenderer

left = open("left.md", "r", encoding="utf-8").read()
right = open("right.md", "r", encoding="utf-8").read()
_, _, errors = diff(left, right, renderer=TextRenderer())

for err in errors:
    print(err)
PY
```

## Notes
This project is a library (no CLI). If you need different token handling, you can provide a custom parser class that extends `MdParser`.

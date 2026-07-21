# md-sdiff

Diffs to markdown texts only based on their structure. Ignores content. Helpful to diff 2 files that contain the same content in different languages.

## Python API

```python
import sdiff
from sdiff import ZendeskHelpMdParser

left, right, errors = sdiff.diff(
    '# English title',
    '# Deutscher Titel',
    parser_cls=ZendeskHelpMdParser,
)
```

The package intentionally has no command-line or service entry point. Public behavior is exposed through
`sdiff.diff`, the parser classes, renderer classes, and the model/error objects returned by comparisons.

## Python 3.11 development

```sh
make dev
make lint
make test
make fixture-smoke
make depcheck
```

Exact parser, renderer, and diff behavior is protected by
`tests/fixtures/golden/python311_compatibility.json`. Migration scope and proof results are recorded in
`docs/python311-migration-contract.md`.

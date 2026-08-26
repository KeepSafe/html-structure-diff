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
make mistune-compat
make depcheck
make requirements
```

`make requirements` uses `pip-compile` to regenerate `requirements.txt` and `requirements-dev.txt` from
`pyproject.toml`.

### Golden Mistune 0.8.4 Fixtures

Normal development and `make test` do not need an oracle checkout. The regular test suite checks every curated,
golden, fixture, exhaustive-matrix, and deterministic-fuzz result against the committed Golden Mistune 0.8.4
Fixtures.

For a live two-version comparison, prepare the target with `make dev` and run:

```sh
make mistune-compat
```

The Make target always starts fresh. It removes any stale oracle state at
`/tmp/html-structure-diff-mistune-084-oracle`, creates a detached pre-port checkout there, builds an isolated Python
3.11 environment with Mistune 0.8.4, runs the comparison, and removes the oracle again. No reusable oracle setup is
required, and a partially cleaned `/tmp` directory is never trusted.

Success ends with:

```text
Mistune 0.8.4 oracle vs 3.3.4 target: 1086 cases, 0 mismatches
```

The command runs each checkout with its own `venv`, compares normalized parser, renderer, and diff results, and exits
nonzero with unified result diffs when behavior differs.

Only refresh the committed Golden Mistune 0.8.4 Fixtures after deliberately changing and reviewing the compatibility
corpus. The refresh is generated from the 0.8.4 worktree, not from the target implementation, and refuses any other
oracle Mistune version:

```sh
make mistune-compat-refresh
git diff -- tests/fixtures/compatibility/golden_mistune_084_fixtures.json
make test
```

Do not refresh the golden fixtures merely to hide a mismatch; investigate and either restore parity or document an
explicitly approved behavior change first.

Exact parser, renderer, and diff behavior is protected by
`tests/fixtures/golden/python311_compatibility.json` plus the Mistune compatibility corpus under
`tests/fixtures/compatibility`. Migration scope and proof results are recorded in
`docs/python311-migration-contract.md`.

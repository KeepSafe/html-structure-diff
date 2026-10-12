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

`make env`, `make dev`, and the CircleCI setup read the exact local/CI interpreter version from `.python-version`.
They use the active `python`; pyenv automatically selects the file's version during local development, and CircleCI
provides the same pinned version. `make dev`, Travis, and CircleCI install the compiled
`requirements-dev.txt` environment, then install this project editable with `--no-deps`. Direct dependency declarations
remain authoritative in `pyproject.toml`; regenerate the compiled files after changing them. Travis is intentionally a
Python 3.11.9 compatibility lane because that is the patch release available from its Jammy Python catalog.

### New release

#### Release

1. Bump the version in `pyproject.toml` and add the release date to `CHANGELOG`.
2. Commit the changes and merge them to `master`.
3. `git tag <version>`
4. `git push origin <version>`
5. `make publish`
6. Go to http://10.10.1.166:8080/#/admin, log in with the admin credentials from BE 1Password, select
   **Rebuild package list**, and wait for completion.
7. Go to http://10.10.2.107:8080/#/admin, log in with the admin credentials from BE 1Password, select
   **Rebuild package list**, and wait for completion.

Step 5 builds the wheel and source distribution, then uploads the wheel to the internal PyPI. If `sdiff` code changed,
a new version must be assigned or the upload will fail. Internal PyPI credentials are required and are available in
[1Password](https://start.1password.com/open/i?a=RAREY3D7KJDHPFPS5BGKXGA5TI&h=keepsafe.1password.com&i=vsqhjp66yb7r5mg2bb3whwiqg4&v=7frtpxbxiu4bkuqxh5rnechwhi).
[Twine keyring support](https://twine.readthedocs.io/en/stable/#keyring-support) may also be used.
`make package` is an alias of `make publish` and performs the same upload workflow.

### Golden Mistune 0.8.4 Fixtures

Normal development and `make test` do not need an oracle checkout. The regular test suite checks every curated,
golden, fixture, exhaustive-matrix, and deterministic-fuzz result against the committed Golden Mistune 0.8.4
Fixtures.

For a live two-version comparison, prepare the target with `make dev` and run:

```sh
make mistune-compat
```

The Make target always starts fresh. It removes any stale oracle state at
`/tmp/html-structure-diff-mistune-084-oracle`, creates a detached checkout of the permanent pre-port master commit
`12e7782208e4b458c8c4242882fda2377d9cba6b`, and removes the oracle again after the comparison. The runner uses the
target's absolute Python 3.11.13 interpreter to create a fresh oracle venv, then independently installs exactly
`mistune==0.8.4` and that checkout's `sdiff==1.0.0`; it does not trust the historical Makefile or any partially
cleaned `/tmp` state.

Before comparing results, the runner verifies the exact oracle Git revision, a clean oracle worktree, Python
3.11.13, Mistune 0.8.4, and sdiff 1.0.0. It also verifies that the target report was produced with Python 3.11.13.
No reusable oracle setup is required.

Success ends with:

```text
Mistune 0.8.4 oracle vs 3.3.4 target: 1091 cases, 0 mismatches
```

The command runs each checkout with its own `venv`, compares normalized parser, renderer, and diff results, and exits
nonzero with unified result diffs when behavior differs.

Only refresh the committed Golden Mistune 0.8.4 Fixtures after deliberately changing and reviewing the compatibility
corpus. The refresh is generated from the verified permanent master oracle, not from the target implementation. The
regular test suite asserts the fixture's oracle revision, Python, Mistune, and sdiff versions so provenance drift is
visible:

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

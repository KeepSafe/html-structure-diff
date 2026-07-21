# html-structure-diff Python 3.11 Migration Contract

## Scope and Repo Shape

`html-structure-diff` is a no-stack Python library, not a service.

- Distribution: `sdiff`
- Import package: `sdiff`
- CLI surface: none
- Service/runtime surfaces: none; the audit found no PasteDeploy app factory, Gunicorn configuration, service INI,
  health endpoint, worker, Docker runtime, backing-service dependency, or network client
- Migration lane: one lightweight `python311-upgrade` branch, not the six-PR service stack

The `python311-service-upgrade-stack` skill is the convention source for the applicable packaging, dependency,
workflow, and verification work. Service-only tasks are explicitly excluded below.

## Branch and Write Scope

- Source checkout: `/Users/olmos/keepsafe/repos/html-structure-diff`
- Edit root: `/Users/olmos/keepsafe/repos/worktrees/html-structure-diff-python-upgrade`
- Base: clean `master` at `12e7782208e4b458c8c4242882fda2377d9cba6b`
- Branch: `python311-upgrade`
- First write scope: this contract and golden parser/renderer/diff compatibility proof
- Follow-on scope: packaging metadata, exact dependency pins, Makefile/CI workflow, and proof documentation

## Public and Behavior-Sensitive Surfaces

Public imports exercised by this migration:

- `sdiff.diff`
- `sdiff.diff_struct`
- `sdiff.diff_links`
- `sdiff.MdParser`
- `sdiff.ZendeskHelpMdParser`
- `sdiff.renderer.TextRenderer`
- `sdiff.renderer.HtmlRenderer`
- model and error objects exposed through `sdiff.model` and diff results

Behavior that must remain stable:

- Mistune 0.8 Markdown tokenization and structural symbols
- translated documents with matching structure
- link structure independent of translated link text
- inline HTML escaping
- Zendesk `<tabs>`, `<steps>`, and styled `<callout>` parsing/rendering
- insert/delete error ordering, node symbols, styles, and user-facing messages

The existing Markdown fixture pairs under `tests/fixtures/same` and `tests/fixtures/different` remain the broad
classification proof. `tests/fixtures/golden/python311_compatibility.json` records exact parser, renderer,
structural-diff, and link-diff outputs for 12 compact Mistune 0.8.4 scenarios. The oracle covers block and inline
HTML, heading styles, lists, images and reference links, hard breaks and directional marks, link-count changes,
insert/delete symmetry, and nested Zendesk constructs.

## Downstream Consumers

Local source and requirements scans found:

- `content-validator` directly imports `diff`, `renderer`, and `MdParser`.
- The migrated `content-validator` branch targets
  `sdiff @ git+https://github.com/KeepSafe/html-structure-diff.git@1.0.0`.
- `email-service` and `translation-real-time-validaton` consume `sdiff` transitively through
  `content-validator`; their legacy requirements still reference tag `0.4.1`.

This library migration unblocks downstream requirement refresh and service proof. It does not claim those service
flows are safe until each downstream repo reruns its own integration proof with the migrated package.

## Python and Packaging Target

- Interpreter target: CPython 3.11, with `.python-version` normalized to `3.11.13`
- Packaging source of truth: `pyproject.toml`
- Package version: `1.1.0`
- Runtime dependencies: exact compatible pins
- Build/test/dev dependencies: exact pins in a `dev` optional dependency group
- Requirements artifacts: generated with `pip-compile` from `pyproject.toml`

`master` already contains the prior Python 3.11 work and is tagged `1.0.0`. This compatibility-focused follow-up
therefore uses a minor release, `1.1.0`, rather than treating the already-established runtime baseline as another
major-version break.

## Baseline Audit

Before migration edits:

- `.python-version` was `3.11`; local resolution in the worktree was Python 3.11.9.
- `setup.py` and `setup.cfg` were the packaging/config sources.
- Package metadata already declared `python_requires='>=3.11'` and version `1.0.0`.
- Runtime metadata allowed `mistune <= 1`; `requirements.txt` separately pinned `mistune==0.8.1`.
- The untouched dev install resolved `mistune==0.8.4`.
- The repo already used `pytest`, `coverage`, and Python 3.11 Travis.
- There was no CircleCI config on `master`, no pre-push hook, no explicit import smoke target, and no exact-output
  golden fixture.
- Source history already included a pyupgrade-to-Python-3.11 pass; the final branch reran the complete ladder.

Untouched baseline proof on 2026-07-16:

| Command | Result |
| --- | --- |
| `make dev` | Pass; installed `sdiff==1.0.0` and `mistune==0.8.4`. |
| `make test` | Pass; 53 tests on Python 3.11.9. |
| `make coverage` | Pass; 96% total coverage. |
| `venv/bin/pip check` | Pass; no broken requirements. |
| public import smoke | Pass; `sdiff==1.0.0` and documented imports loaded. |
| `venv/bin/python -m compileall -q sdiff tests` | Pass. |

## Task Mapping from python311-service-upgrade-stack

| Skill task | Status | Repo mapping |
| --- | --- | --- |
| Task 1: pyproject, Python 3.11, dependency audit, pyupgrade | Applicable: complete | Replaced legacy packaging, normalized the interpreter target, hard-pinned Mistune, completed and reconfirmed every pyupgrade ladder stage, then removed the one-time tool. |
| Task 2a: formatting and Flake8 alignment | Applicable: complete | Moved Flake8 and coverage config into `pyproject.toml`, added `flake8-pyproject`, and retained the 120-character convention. |
| Task 2b: hooks, CI, Makefile, README | Applicable: complete | Normalized package-oriented Makefile targets, retained Python 3.11 Travis, added native CircleCI 2.1 package CI and a pre-push hook. Service launch targets are excluded. |
| Task 2c: mypy stabilization | Not applicable | The repo has no mypy baseline; introducing a typing program is not required to preserve this library's Python 3.11 behavior. |
| Task 3: msgpack, redis, asynctest, and nose compatibility | Not applicable | The repo uses pytest and has no msgpack, redis, aioredis, asynctest, or nose dependency/call site. |
| Task 4: asyncio/aiohttp modernization | Not applicable | No asyncio or aiohttp code exists. |
| Task 4c: async test harness modernization | Not applicable | No async tests or custom loop harness exists. |
| Task 5: Gunicorn and Docker local infrastructure | Not applicable | The audit proves library-only shape with no runtime service or local dependencies. |
| Task 6: deterministic requirements pipeline | Applicable: complete | `make requirements` uses `pip-tools==7.5.3` with `pip<26` to compile runtime and dev artifacts from `pyproject.toml`; architecture service lockfiles and Ansible artifacts do not apply. |

## Service-Only Tasks Intentionally Skipped

- Docker daemon preflight, Docker Compose dependencies, and runtime smoke
- Gunicorn configuration and PasteDeploy launcher wiring
- service INI, health endpoint, worker, or queue startup proof
- `ks-local-e2e` profile and production-egress guard
- local backing-service fixtures or paid-provider fakes
- `libks==1.0.0`, `LIBKS_VERSION`, and private-index handling
- architecture-specific service requirements and Ansible deployment artifacts
- service contract checker and migration gate, whose assertions require service-template files

No external or paid service call is needed by this package. Dependency installation may use package indexes; all
behavior proof is local and fixture-backed.

## Required Proof and Artifacts

Required commands on the final branch:

- `make clean`
- `make env`
- `make dev`
- `make ci-dev-install`
- `make requirements`
- the skill's full `--py36-plus` through `--py311-plus` pyupgrade ladder with `--keep-percent-format`
- `make lint`
- `make test`
- `make fixture-smoke`
- `CI=1 make test-only`
- public import/API smoke
- `make depcheck`
- `venv/bin/python -m compileall -q sdiff tests`
- `make package`
- built-wheel install and import smoke in an isolated CPython 3.11.13 venv
- `circleci config validate .circleci/config.yml` when the local CircleCI CLI can validate without a paid service
- `git diff --check`

Expected evidence:

- exact golden snapshot at `tests/fixtures/golden/python311_compatibility.json`
- golden compatibility test at `tests/test_golden_compatibility.py`
- coverage XML at `build/coverage/coverage.xml` in CI mode
- xUnit output at `build/test/results.xml` in CI mode
- local sdist and wheel under ignored `dist/`
- source distribution containing all Markdown and JSON compatibility fixtures
- command results in this contract and the umbrella ExecPlan

## Dependency and Package Notes

- Runtime metadata and `requirements.txt` now agree on `mistune==0.8.4`. The untouched editable-install baseline
  already resolved 0.8.4 from the old `mistune <= 1` range, so this is a deterministic pin of proven behavior rather
  than a broad parser upgrade.
- Mistune 3.3.3 is intentionally deferred to a separate, approval-gated commit. Its API/changelog audit and any
  compatibility implementation will be performed against the committed golden oracle.
- Existing compatible hard pins are retained: `coverage==7.6.1` and `flake8==7.1.1`.
- The previously ranged `pytest >= 8` dependency is pinned to the proven environment's `pytest==9.1.1`.
- Added exact workflow pins: `build==1.5.0`, `flake8-pyproject==1.2.4`, `pip-tools==7.5.3`, and `twine==6.2.0`.
- `pipdeptree` was removed because `pip check` is the required integrity gate for this one-runtime-dependency
  library. `pyupgrade` was removed after the official six-stage ladder was rerun with zero remaining changes.
- `make requirements` generated stable runtime/dev outputs on two consecutive runs. The compile environment uses
  `pip==25.3` to satisfy the skill's `pip<26` compatibility guardrail.
- Removed unused legacy `nose` and `autopep8` entries from `requirements-dev.txt`; this repo uses pytest and does
  not have an autopep8 target.
- The built wheel metadata declares `Requires-Python: >=3.11,<3.12` and `Requires-Dist: mistune==0.8.4`.
- `MANIFEST.in` narrowly includes Markdown and JSON fixture data in the sdist; wheel contents remain package-only.
- No direct or transitive `msgpack` or `libks` dependency is present.

## Migration Result and Proof Log

Date: 2026-07-21

Branch: `python311-upgrade`

Ten reviewable commits, including this evidence record, were created on `python311-upgrade`; no pull request or push
was created.

Completed applicable work:

- Replaced `setup.py` and `setup.cfg` with `pyproject.toml`.
- Normalized `.python-version` and package/CI policy to Python 3.11.13.
- Bumped the package from `1.0.0` to the compatible minor release `1.1.0` and preserved public behavior.
- Hard-pinned the runtime dependency and generated deterministic requirements artifacts with `pip-compile`.
- Moved Flake8 and coverage configuration into `pyproject.toml`.
- Added package-oriented `env`, `dev`, `lint`, `test-only`, `fixture-smoke`, `import-smoke`, `depcheck`,
  `requirements`, package-build, CI-install, and hook targets.
- Added native CircleCI 2.1 package jobs with reusable executors/commands for dependency preparation, lint, tests,
  xUnit, and coverage XML.
- Added exact golden parser/renderer/structural-diff/link-diff snapshots for 12 behavior-sensitive scenarios.
- Ran the full skill ladder. The `--py36-plus` stage converted one list-rendering format call and two parser regex
  format calls to f-strings; Python 3.7 through 3.11 stages were no-ops. Golden outputs remained unchanged.
- Review found that the first sdist omitted fixture data; `MANIFEST.in` fixed the package artifact before handoff.
- Removed `pipdeptree` and the completed one-time `pyupgrade` tool from the final developer environment.

Proof results:

| Command | Result | Evidence |
| --- | --- | --- |
| `make clean`; `make env`; `make dev` | Pass | Fresh venv is CPython 3.11.13 with editable `sdiff==1.1.0`, `mistune==0.8.4`, and exact dev tooling. |
| `make ci-dev-install` | Pass | CI bootstrap installed/reused the exact-version venv and final `.[dev]` dependency shape. |
| full skill pyupgrade ladder over `sdiff` and `tests` | Pass | All six stages were reconfirmed live with zero remaining changes; the earlier Python 3.6 stage changes are isolated in commit `7c78ad3`. |
| `make requirements` twice | Pass | Both pip-compile outputs were byte-stable; compile tooling is `pip-tools==7.5.3` with `pip==25.3`. |
| `make test` | Pass | Flake8 and msgpack guard passed; 54 tests passed on Python 3.11.13. |
| `make coverage` | Pass | Total branch-aware coverage remained 96%. |
| `make fixture-smoke` | Pass | 3 test methods and 12 fixture subtests passed, including the exact golden snapshot. |
| `make import-smoke` | Pass | Imported documented public API and printed `1.1.0 MdParser ZendeskHelpMdParser TextRenderer`. |
| `make depcheck` | Pass | `pip check` found no broken requirements. |
| `CI=1 make test-only` | Pass | 54 tests passed and wrote `build/test/results.xml` plus `build/coverage/coverage.xml`. |
| `venv/bin/python -m compileall -q sdiff tests` | Pass | Source and tests compiled on Python 3.11.13. |
| `make package` | Pass | Built isolated `sdiff-1.1.0.tar.gz` and `sdiff-1.1.0-py3-none-any.whl`. |
| `venv/bin/twine check dist/*` | Pass | Both distribution artifacts passed metadata/README validation. |
| sdist fixture listing | Pass | Archive contains all same/different Markdown fixtures and `python311_compatibility.json`. |
| isolated wheel install/import/diff smoke | Pass | A separate CPython 3.11.13 venv installed the wheel with `mistune==0.8.4` and ran `sdiff.diff()`. |
| CircleCI validate, `--next`, and config process | Pass | CircleCI accepted the native source `version: 2.1`, strict upcoming-compiler validation, and reusable-config expansion. |
| `make hooks`, installed-file comparison, `make unhooks` | Pass | Executable pre-push hook installed exactly and was removed after verification. |
| `git diff --check` | Pass | No whitespace errors. |

An additional pre-final run passed all 54 tests on Python 3.11.9 before the exact 3.11.13 environment was selected.

## Known Gaps

- Remote CI is not exercised by default local proof.
- Downstream `content-validator`, `email-service`, and `translation-real-time-validaton` still need their own
  requirements refresh and integration proof after consuming the merged package state.
- Mistune 3.3.3 research and implementation have not started; they require explicit user approval and a separate
  commit after this checkpoint.
- No package release, tag, push, or pull request is part of this local checkpoint.

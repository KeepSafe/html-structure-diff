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

Behavior that must remain stable across the Mistune 0.8.4-to-3.3.4 adapter:

- Mistune 0.8 Markdown tokenization and structural symbols
- translated documents with matching structure
- link structure independent of translated link text
- inline HTML escaping
- Zendesk `<tabs>`, `<steps>`, and styled `<callout>` parsing/rendering
- insert/delete error ordering, node symbols, styles, and user-facing messages

The existing Markdown fixture pairs under `tests/fixtures/same` and `tests/fixtures/different` remain the broad
classification proof. `tests/fixtures/golden/python311_compatibility.json` records exact parser, renderer,
structural-diff, and link-diff outputs for 13 compact Mistune 0.8.4 scenarios. The oracle covers block and inline
HTML, heading styles, lists, images and reference links, hard breaks and directional marks, link-count changes,
insert/delete symmetry, and nested Zendesk constructs.

`scripts/run_mistune_compat.py` runs permanent pre-port master commit
`12e7782208e4b458c8c4242882fda2377d9cba6b` and this 3.3.4 worktree in isolated virtual environments. The runner
creates the oracle from scratch under `/tmp` with the target's absolute Python 3.11.13 interpreter, installs exactly
Mistune 0.8.4 plus the historical sdiff 1.0.0 checkout independently of its Makefile, and verifies the Git revision,
clean worktree, Python, Mistune, and sdiff provenance before accepting results. It expands 66 committed corpus
entries, all 13 golden cases, all 12 automatically discovered Markdown fixture pairs, and 1,000 fixed-seed structured
fuzz pairs for 1,091 named comparisons. Four aggregate corpus entries check another 329,200 short link/image label and
destination combinations, 52,272 generated inline-rule operations, and 643 generated block-facade operations. The
runner compares recursive ASTs, exact text/HTML rendering, structural and link diff results, mutated parser state, and
phase-specific exception signatures.

Normal `make test` recomputes every target result against the Golden Mistune 0.8.4 Fixtures at
`tests/fixtures/compatibility/golden_mistune_084_fixtures.json`. This compact expected-results file is generated only
from that permanent 0.8.4 oracle, and the test suite pins its revision and environment metadata, so the normal suite
retains the complete parity proof without requiring another worktree. `make mistune-compat` provides readable
full-result diffs, and `make mistune-compat-refresh` deliberately refreshes the golden fixtures after an approved
corpus change.

## Downstream Consumers

Local source and requirements scans found:

- `content-validator` directly imports `diff`, `renderer`, and `MdParser`.
- The migrated `content-validator` branch currently targets immutable commit `7cac220`; it must move to the final
  reviewed 2.x tag/commit to receive Mistune 3.3.4.
- `email-service` and `translation-real-time-validaton` consume `sdiff` transitively through
  `content-validator`; their legacy requirements still reference tag `0.4.1`.

This library migration unblocks downstream requirement refresh and service proof. It does not claim those service
flows are safe until each downstream repo reruns its own integration proof with the migrated package.

## Python and Packaging Target

- Interpreter target: CPython 3.11, with `.python-version` normalized to `3.11.13`
- Packaging source of truth: `pyproject.toml`
- Package version: `2.0.0`
- Runtime dependencies: exact compatible pins
- Build/test/dev dependencies: exact pins in a `dev` optional dependency group
- Requirements artifacts: generated with `pip-compile` from `pyproject.toml`

The historical repository already uses 1.x tags. The Python 3.11 migration branch therefore starts a 2.x release
line. Only downstream consumers that have migrated to Python 3.11 should move to those tags.

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
- `make mistune-compat`
- `CI=1 make test-only`
- public import/API smoke
- `make depcheck`
- `venv/bin/python -m compileall -q sdiff tests scripts`
- `rm -rf dist && venv/bin/python -m build .`
- built-wheel install and import smoke in an isolated CPython 3.11.13 venv
- `circleci config validate .circleci/config.yml` when the local CircleCI CLI can validate without a paid service
- `git diff --check`

Expected evidence:

- exact golden snapshot at `tests/fixtures/golden/python311_compatibility.json`
- golden compatibility test at `tests/test_golden_compatibility.py`
- target-side parity/regression tests at `tests/test_mistune_compatibility.py`
- dual-version reporter and runner under `scripts/`
- curated/fuzz corpus configuration at `tests/fixtures/compatibility/mistune_cases.json`
- Golden Mistune 0.8.4 Fixtures at
  `tests/fixtures/compatibility/golden_mistune_084_fixtures.json`
- coverage XML at `build/coverage/coverage.xml` in CI mode
- xUnit output at `build/test/results.xml` in CI mode
- local sdist and wheel under ignored `dist/`
- source distribution containing the full test suite, compatibility helpers, and Markdown/JSON fixtures
- command results in this contract and the umbrella ExecPlan

## Dependency and Package Notes

- Runtime metadata and both generated requirement files now agree on `mistune==3.3.4`.
- Mistune 3 removed the `BlockLexer`, `InlineLexer`, and private grammar constants used by the old implementation.
  The adapter owns sdiff's intentionally narrow default block/list/text grammar locally, retains the explicitly
  callable legacy rule facade, and emits the existing sdiff model directly. It exercises Mistune 3's inline link
  parser as a non-authoritative compatibility probe; the probe's return and tokens do not determine sdiff output.
- The adapter preserves smart entity escaping, literal unsupported Markdown, raw link/image source, unresolved
  reference links, legacy list shapes, inline-vs-block HTML classification, and recursive Zendesk tags.
- The adapter honors direct `InlineLexer.parse(..., rules=...)` rule ordering for links, reference links, autolinks,
  and bare URLs. Explicit block rules retain 0.8.4 block-quote/code/table token shapes, definition maps, footnote
  recursion, post-construction `default_rules` changes, and reused-parser token-list identity.
- Mistune 0.8's class hierarchy and unrelated private lexer internals are intentionally not recreated. The 2.x
  compatibility contract covers sdiff's callable parser facade and observable results, not subclassing removed
  Mistune implementation classes; no indexed downstream consumer relies on that private inheritance surface.
- The legacy nested-label and destination grammar is compiled into a linear-time index. This preserves 0.8.4's
  unusual greedy/backtracking boundaries, including quoted titles containing `)` and angle-destination fallback,
  while eliminating repeated suffix scans on malformed nested openers. This local index—not Mistune 3's probe—is
  authoritative for link and image boundaries.
- The port removes the class-level Zendesk rule mutation that could make a later plain `MdParser` call fail. This is
  an intentional target-only defect fix; document outputs remain oracle-identical.
- Existing compatible hard pins are retained: `coverage==7.6.1` and `flake8==7.1.1`.
- The previously ranged `pytest >= 8` dependency is pinned to the proven environment's `pytest==9.1.1`.
- Added exact workflow pins: `build==1.5.0`, `flake8-pyproject==1.2.4`, `pip-tools==7.5.3`, and `twine==6.2.0`.
- `pipdeptree` was removed because `pip check` is the required integrity gate for this one-runtime-dependency
  library. `pyupgrade` was removed after the official six-stage ladder was rerun with zero remaining changes.
- `make requirements` generated stable runtime/dev outputs on two consecutive runs. The compile environment uses
  `pip==25.3` to satisfy the skill's `pip<26` compatibility guardrail.
- Removed unused legacy `nose` and `autopep8` entries from `requirements-dev.txt`; this repo uses pytest and does
  not have an autopep8 target.
- The built wheel metadata declares `Requires-Python: >=3.11,<3.12` and `Requires-Dist: mistune==3.3.4`.
- `MANIFEST.in` includes the test modules, compatibility helper scripts, and Markdown/JSON fixture data needed to run
  the complete suite from an extracted sdist; wheel contents remain package-only.
- No direct or transitive `msgpack` or `libks` dependency is present.

## Migration Result and Proof Log

Date: 2026-08-26

Branch: `python311-upgrade`

Draft PR #14 contains the committed Python migration, Mistune 3.3.4 compatibility port, and 2.0.0 release workflow
on `python311-upgrade`. The final 2.0.0 tag and internal package publication remain pending.

Completed applicable work:

- Replaced `setup.py` and `setup.cfg` with `pyproject.toml`.
- Normalized `.python-version` and package/CI policy to Python 3.11.13.
- Started the Python 3.11-only 2.x release line and preserved public behavior.
- Hard-pinned the runtime dependency and generated deterministic requirements artifacts with `pip-compile`.
- Moved Flake8 and coverage configuration into `pyproject.toml`.
- Added package-oriented `env`, `dev`, `lint`, `test-only`, `fixture-smoke`, `import-smoke`, `depcheck`,
  `requirements`, CI-install, release, and hook targets. `package` intentionally aliases the publishing workflow;
  build-only verification uses `venv/bin/python -m build .` directly.
- Added native CircleCI 2.1 package jobs with reusable executors/commands for dependency preparation, lint, tests,
  xUnit, and coverage XML.
- Added exact golden parser/renderer/structural-diff/link-diff snapshots for 13 behavior-sensitive scenarios.
- Ported the parser from removed Mistune 0.8 lexer APIs to a Mistune 3.3.4 compatibility adapter.
- Added a dual-worktree exact-signature harness, self-contained Golden Mistune 0.8.4 Fixtures, expanded
  curated/fuzz/exhaustive link matrices, and target-side parity unit tests.
- Anchored the live oracle to the permanent pre-port master commit, made its Python 3.11.13 environment entirely
  runner-owned, and added exact revision/runtime/package provenance plus stale `/tmp` cleanup checks.
- Fixed a review-discovered `InlineLexer` explicit-rule mismatch and replaced the first nested-label scanner after
  exhaustive testing exposed Mistune 0.8 greedy-label edge cases.
- Restored the remaining sdiff-authored autolink/URL rules and the inherited callable block-rule facade, including
  exact raw token dictionaries, definition state, footnote recursion, and mutable default-rule behavior.
- Ran the full skill ladder. The `--py36-plus` stage converted one list-rendering format call and two parser regex
  format calls to f-strings; Python 3.7 through 3.11 stages were no-ops. Golden outputs remained unchanged.
- Review found that the first sdist omitted fixture data, and the expanded parity suite exposed missing test helper
  modules in the archive. `MANIFEST.in` now makes the complete extracted-sdist suite runnable before handoff.
- Removed `pipdeptree` and the completed one-time `pyupgrade` tool from the final developer environment.

Proof results:

| Command | Result | Evidence |
| --- | --- | --- |
| `make clean`; `make env`; `make dev` | Pass | Fresh venv is CPython 3.11.13 with editable `sdiff==2.0.0`, `mistune==3.3.4`, and the locked dev toolchain. |
| `make ci-dev-install` | Pass | CI bootstrap installed/reused the exact-version venv and final `.[dev]` dependency shape. |
| full skill pyupgrade ladder over `sdiff` and `tests` | Pass | All six stages were reconfirmed live with zero remaining changes; the earlier Python 3.6 stage changes are isolated in commit `7c78ad3`. |
| `make requirements` twice | Pass | Both pip-compile outputs were byte-stable; compile tooling is `pip-tools==7.5.3` with `pip==25.3`. |
| `make test` | Pass | Flake8 and msgpack guard passed; 96 tests passed on Python 3.11.13, including the Golden Mistune 0.8.4 Fixtures, oracle-runner hardening, and non-authoritative Mistune 3 probe coverage. |
| `make coverage` | Pass | Total branch-aware coverage is 99%; `sdiff/parser.py` has 100% statement and 99% branch coverage, and the oracle runner has 96%. |
| `make fixture-smoke` | Pass | 3 test methods and 12 fixture subtests passed, including the exact golden snapshot. |
| `make mistune-compat` | Pass | A fresh `/tmp` oracle at permanent master commit `12e7782`, with Python 3.11.13, `sdiff==1.0.0`, and `mistune==0.8.4`, matched the 3.3.4 target across 1,091 named cases with 0 mismatches; post-run cleanup succeeded. |
| direct-link endpoint oracle sweep | Pass | 1,921,600 exhaustive tails through length seven plus 500,000 deterministic randomized inputs matched Mistune 0.8.4 with zero mismatches. |
| malformed-link bounded-time regression | Pass | 16,000 nested link and image openers complete in about 0.03 seconds each; the test ceiling is 2 seconds. |
| `make import-smoke` | Pass | Imported documented public API and printed `2.0.0 MdParser ZendeskHelpMdParser TextRenderer`. |
| `make depcheck` | Pass | `pip check` found no broken requirements. |
| `CI=1 make test-only` | Pass | 83 tests passed and wrote `build/test/results.xml` plus `build/coverage/coverage.xml`. |
| `venv/bin/python -m compileall -q sdiff tests scripts` | Pass | Source, tests, and compatibility scripts compiled on Python 3.11.13. |
| `rm -rf dist && venv/bin/python -m build .` | Pass | Built isolated `sdiff-2.0.0.tar.gz` and `sdiff-2.0.0-py3-none-any.whl` without invoking the publishing targets. |
| `venv/bin/twine check dist/*` | Pass | Both distribution artifacts passed metadata/README validation. |
| sdist content listing | Pass | Archive contains all tests, compatibility helpers, same/different Markdown fixtures, golden JSON, and Golden Mistune 0.8.4 Fixtures. |
| extracted-sdist test suite | Pass | All 96 tests and 1,149 subtests passed directly from the unpacked source archive, including runner tests that create their own disposable Git fixtures. |
| isolated wheel install/import/diff smoke | Pass | A separate CPython 3.11.13 venv installed `sdiff==2.0.0` with `mistune==3.3.4` and ran `sdiff.diff()`. |
| CircleCI validate, `--next`, and config process | Pass | CircleCI accepted the native source `version: 2.1`, strict upcoming-compiler validation, and reusable-config expansion. |
| PR #14 remote CI | Pass | CircleCI `prepare_cache`, `lint`, and `test`, plus Travis CI branch and pull-request builds, passed at `5ebec5545ba6df34942403c9afd73fc87b471c49`. |
| downstream `content-validator` test suite | Pass | 65 tests passed with one expected skip against the local target and Mistune 3.3.4; HTTP was mocked. |
| `make hooks`, installed-file comparison, `make unhooks` | Pass | Executable pre-push hook installed exactly and was removed after verification. |
| `git diff --check` | Pass | No whitespace errors. |

An additional clean run passed all 71 tests on Python 3.11.9 before the exact 3.11.13 environment was selected.

## Known Gaps

- Downstream `content-validator`, `email-service`, and `translation-real-time-validaton` still need their own
  requirements refresh and integration proof after consuming the merged package state.
- No 2.x package tag or release has been created. Downstreams must pin the final reviewed immutable tag/commit,
  never the moving branch.

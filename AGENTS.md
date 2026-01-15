# Repository Guidelines

## Project Structure & Module Organization
The core library lives in `sdiff/` (parser, comparer, renderer, and models). Tests are in `tests/`, with shared fixtures in `tests/fixtures/`. Reference PDFs sit in `docs/`. Packaging and tooling are defined in `setup.py`, `setup.cfg`, and the `Makefile`; `CHANGELOG` tracks releases.

## Build, Test, and Development Commands
- `make env` creates the local `venv/` (Python 3.11+).
- `make dev` installs the package plus test/dev extras (`.[tests,devtools]`) into the venv.
- `make test` runs linting and the full pytest suite with coverage.
- `make vtest` runs pytest verbosely.
- `make flake` runs flake8 on `sdiff/` and `tests/`.
- `make cov` prints the coverage report.
- `make clean` removes build artifacts and the venv.

Example flow:
```sh
make dev
make test
```

## Coding Style & Naming Conventions
Use standard Python conventions: 4-space indentation, `snake_case` for modules/functions/variables, and `PascalCase` for classes. Flake8 enforces a 120-character line limit (see `setup.cfg`). `autopep8` is available for formatting. Keep new modules in `sdiff/` and new tests in `tests/` with filenames like `test_<area>.py`.

## Testing Guidelines
The suite uses `pytest` with `coverage`. Coverage is expected to stay high (current config fails under 96%). Add or update tests for behavior changes, and prefer small, focused unit tests. Place reusable data in `tests/fixtures/`. Run `make test` before submitting changes.

## Commit & Pull Request Guidelines
Commit messages in this repo are short and often use a type prefix (e.g., `chore: ...`, `fixes: ...`, `hotfix: ...`, `refactors: ...`). Follow that pattern where practical, and keep the summary concise. For PRs, include a brief description, list tests run (e.g., `make test`), and link related issues or tickets when available.

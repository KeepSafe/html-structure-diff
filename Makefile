# Package development and verification tasks (UNIX only).

PYTHON_VERSION=3.11.13
BOOTSTRAP_PYTHON?=python3.11
PYTHON=venv/bin/python
PIP=venv/bin/pip
COVERAGE=venv/bin/coverage
PYTEST=venv/bin/pytest
FLAKE=venv/bin/flake8
PIP_COMPILE=venv/bin/pip-compile
PYUPGRADE=venv/bin/pyupgrade
RG=rg

PYTHON_FILES=$(shell rg --files sdiff tests -g '*.py')
PYTEST_SHARED_FLAGS=-s --durations=3 --durations-min=0.005
PYTEST_FLAGS=$(PYTEST_SHARED_FLAGS)
CI_COVERAGE_REPORT=

PYPICLOUD_HOST=pypicloud.getkeepsafe.local
TWINE=venv/bin/twine
HOOK_PATH=$(shell git rev-parse --git-path hooks/pre-push)

ifdef CI
PYTEST_FLAGS += --junitxml=build/test/results.xml
CI_COVERAGE_REPORT=$(COVERAGE) xml -o build/coverage/coverage.xml
endif

build-dir:
	mkdir -p build/test build/coverage

env:
	test -d venv || $(BOOTSTRAP_PYTHON) -m venv venv
	$(PIP) install -U "pip<26" "setuptools>=82.0.1" "wheel>=0.47.0"
	$(PIP) install -e .

dev: env
	$(PIP) install -e '.[dev]'

update:
	$(PIP) install -U .

install: env

ci-env:
	@if [ -d "venv" ] && $(PIP) --version >/dev/null 2>&1 \
		&& $(PYTHON) -c 'import platform, sys; sys.exit(platform.python_version() != "$(PYTHON_VERSION)")'; then \
		echo "Reusing cached CI venv, no need to recreate when it has not changed"; \
	else \
		echo "No valid cached venv found, creating a fresh venv"; \
		if [ -d "venv" ]; then rm -rf venv; fi; \
		$(BOOTSTRAP_PYTHON) -m venv venv; \
		$(PIP) install -U "pip<26" "setuptools>=82.0.1" "wheel>=0.47.0"; \
	fi

ci-dev-install: ci-env
	$(PIP) install -e '.[dev]'

flake:
	$(FLAKE) sdiff tests

check-msgpack:
	@echo "Checking for direct msgpack imports..."
	@! $(RG) -n --glob '*.py' '^(import msgpack|from msgpack)' sdiff tests \
		|| (echo "ERROR: Unexpected direct msgpack import found." && exit 1)

lint: build-dir flake check-msgpack

test-only: build-dir
	$(COVERAGE) erase
	$(COVERAGE) run -m pytest $(PYTEST_FLAGS)
	$(CI_COVERAGE_REPORT)

test: lint test-only

vtest vtests: build-dir
	$(COVERAGE) erase
	$(COVERAGE) run -m pytest -v $(PYTEST_FLAGS)
	$(CI_COVERAGE_REPORT)

fixture-smoke:
	$(PYTEST) -q tests/test_golden_compatibility.py tests/test_sdiff.py

import-smoke:
	$(PYTHON) -c 'import importlib.metadata as m; import sdiff; from sdiff import MdParser, ZendeskHelpMdParser, diff, diff_links, diff_struct, renderer; print(m.version("sdiff"), MdParser.__name__, ZendeskHelpMdParser.__name__, renderer.TextRenderer.__name__)'

smoke: fixture-smoke import-smoke

depcheck:
	$(PIP) check

requirements: dev
	$(PIP_COMPILE) --annotation-style=line --output-file=requirements.txt pyproject.toml
	$(PIP_COMPILE) --annotation-style=line --output-file=requirements-dev.txt --extra=dev pyproject.toml

pyupgrade:
	$(PYUPGRADE) --py311-plus --keep-percent-format $(PYTHON_FILES)

coverage:
	$(COVERAGE) report -m

cov cover:
	$(COVERAGE) html --directory coverage
	@echo "Coverage HTML written to coverage/index.html"

package:
	$(PYTHON) -m build

publish: package
	$(TWINE) upload --verbose --sign --username developer --repository-url http://$(PYPICLOUD_HOST)/simple/ dist/*.whl

hooks:
	cp git_hooks/pre-push $(HOOK_PATH)
	chmod +x $(HOOK_PATH)

unhooks:
	rm -f $(HOOK_PATH)

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	find . -type f \( -name '*.py[co]' -o -name '*~' -o -name '.*~' -o -name '*.orig' -o -name '*.rej' \) -delete
	rm -f .coverage
	rm -rf build coverage dist sdiff.egg-info venv

.PHONY: build-dir check-msgpack ci-dev-install ci-env clean cov cover coverage depcheck dev env fixture-smoke \
	flake hooks import-smoke install lint package publish pyupgrade requirements smoke test test-only unhooks update \
	vtest vtests

# Some simple testing tasks (sorry, UNIX only).

PYTHON=venv/bin/python3
PIP=venv/bin/pip
COVERAGE=venv/bin/coverage
TEST_RUNNER=venv/bin/pytest
TEST_RUNNER_FLAGS=-s --durations=3 --durations-min=0.005
FLAKE=venv/bin/flake8
FLAGS=
PYPICLOUD_HOST=pypicloud.getkeepsafe.local
TWINE=./venv/bin/twine

update:
	$(PIP) install -U pip
	$(PIP) install -U .

env:
	test -d venv || python3 -m venv venv

dev: env update
	$(PIP) install .[tests,devtools]

install: env update

publish:
	rm -rf dist
	$(PYTHON) -m build .
	$(TWINE) upload --verbose --sign --username developer --repository-url http://$(PYPICLOUD_HOST)/simple/ dist/*.whl

flake:
	$(FLAKE) sdiff tests

test: flake
	$(COVERAGE) run -m pytest $(TEST_RUNNER_FLAGS)

vtest:
	$(COVERAGE) run -m pytest -v $(TEST_RUNNER_FLAGS)

testloop:
	while sleep 1; do $(TEST_RUNNER) -s --lf $(TEST_RUNNER_FLAGS); done

cov cover coverage:
	$(COVERAGE) report -m

clean:
	rm -rf `find . -name __pycache__`
	rm -f `find . -type f -name '*.py[co]' `
	rm -f `find . -type f -name '*~' `
	rm -f `find . -type f -name '.*~' `
	rm -f `find . -type f -name '@*' `
	rm -f `find . -type f -name '#*#' `
	rm -f `find . -type f -name '*.orig' `
	rm -f `find . -type f -name '*.rej' `
	rm -f .coverage
	rm -rf coverage
	rm -rf build
	rm -rf venv


.PHONY: all build env linux run pep test vtest testloop cov clean

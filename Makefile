# Some simple testing tasks (sorry, UNIX only).

PYTHON=venv/bin/python3
PIP=venv/bin/pip
NOSE=venv/bin/nosetests
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
	$(NOSE) -s $(FLAGS)

vtest:
	$(NOSE) -s -v $(FLAGS)

cov cover coverage:
	$(NOSE) -s --with-cover --cover-html --cover-html-dir ./coverage $(FLAGS)
	echo "open file://`pwd`/coverage/index.html"

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

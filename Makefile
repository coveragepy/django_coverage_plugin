# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://github.com/coveragepy/django_coverage_plugin/blob/main/NOTICE.txt

# Makefile for django_coverage_plugin

.PHONY: help test clean sterile dist pypi test_pypi tag ghrelease

help:					## Show this help.
	@echo "Available targets:"
	@grep '^[a-zA-Z]' $(MAKEFILE_LIST) | sort | awk -F ':.*?## ' 'NF==2 {printf "  %-26s%s\n", $$1, $$2}'

test:					## Run all the tests.
	tox -q -- -q

clean:					## Remove non-source files.
	-rm -rf *.egg-info
	-rm -rf build dist
	-rm -f *.pyc */*.pyc */*/*.pyc */*/*/*.pyc */*/*/*/*.pyc */*/*/*/*/*.pyc
	-rm -f *.pyo */*.pyo */*/*.pyo */*/*/*.pyo */*/*/*/*.pyo */*/*/*/*/*.pyo
	-rm -f *.bak */*.bak */*/*.bak */*/*/*.bak */*/*/*/*.bak */*/*/*/*/*.bak
	-rm -rf __pycache__ */__pycache__ */*/__pycache__ */*/*/__pycache__ */*/*/*/__pycache__ */*/*/*/*/__pycache__
	-rm -f MANIFEST
	-rm -f .coverage .coverage.* coverage.xml
	-rm -f setuptools-*.egg distribute-*.egg distribute-*.tar.gz

sterile: clean                          ## Remove all non-controlled content, even if expensive.
	-rm -rf .tox*

dist:					## Make the source distribution.
	python -m build
	python -m twine check dist/*

_install_e:
	python -m pip install -q -e .

tag: _install_e				## Make a git tag with the version number.
	@export VER="$$(python -c "import django_coverage_plugin as me; print(me.__version__)")" && \
	git tag -s -m "Version v$$VER" v$$VER
	git push --all

ghrelease:				## Make a GitHub release for the latest version.
	python -m scriv github-release

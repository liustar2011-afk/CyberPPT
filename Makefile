PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
.PHONY: doctor env-check test test-unittest test-validate-pptx body-blueprint-prompts final-script-pages

doctor:
	$(PYTHON) -m cyberppt doctor

env-check:
	@$(PYTHON) -c 'import sys; print("python:", sys.executable); print("version:", sys.version.split()[0])'
	@$(PYTHON) -m pytest --version
	@$(PYTHON) -m pip check

test: env-check
	$(PYTHON) -m pytest -q

test-unittest:
	$(PYTHON) -m unittest discover -s tests

test-validate-pptx:
	$(PYTHON) scripts/test_validate_pptx.py

body-blueprint-prompts:
	$(PYTHON) scripts/body_blueprint_prompt.py --help

final-script-pages:
	$(PYTHON) -m cyberppt final-script-pages --help

PYTHON ?= python3
NPM ?= npm

.PHONY: doctor test test-validate-pptx body-blueprint-prompts final-script-pages

doctor:
	$(PYTHON) -m cyberppt doctor

test:
	$(PYTHON) -m unittest discover -s tests

test-validate-pptx:
	$(PYTHON) scripts/test_validate_pptx.py

body-blueprint-prompts:
	$(PYTHON) scripts/body_blueprint_prompt.py --help

final-script-pages:
	$(PYTHON) -m cyberppt final-script-pages --help

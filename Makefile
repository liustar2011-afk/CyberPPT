PYTHON ?= python3
NPM ?= npm

.PHONY: doctor test test-validate-pptx render-dual-image-overlay

doctor:
	$(PYTHON) -m cyberppt doctor

test:
	$(PYTHON) -m unittest discover -s tests

test-validate-pptx:
	$(PYTHON) scripts/test_validate_pptx.py

render-dual-image-overlay:
	$(NPM) run render:dual-image-overlay -- --help

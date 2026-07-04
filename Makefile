PYTHON ?= python3
NPM ?= npm

.PHONY: doctor test test-validate-pptx body-blueprint-prompts source-capture template-rebuild render-dual-image-overlay

doctor:
	$(PYTHON) -m cyberppt doctor

test:
	$(PYTHON) -m unittest discover -s tests

test-validate-pptx:
	$(PYTHON) scripts/test_validate_pptx.py

body-blueprint-prompts:
	$(PYTHON) scripts/body_blueprint_prompt.py --help

source-capture:
	$(PYTHON) scripts/dual_image_overlay/source_capture.py --help

template-rebuild:
	$(PYTHON) scripts/dual_image_overlay/template_rebuild.py --help

render-dual-image-overlay:
	$(NPM) run render:dual-image-overlay -- --help

# Workflow

## Input modes

### Default two-image mode

Run `python scripts/run_pipeline.py --mode review --input-mode two-image --full FULL.png --background BACKGROUND.png --ocr OCR.json --registration registration.json --output-dir OUT`.

OCR JSON is produced from FULL; BACKGROUND is the final PowerPoint base. Use this mode for GPT-generated slides when direct OCR is sufficiently reliable. It produces `review` rather than `passed` whenever OCR confidence is below the automatic threshold.

### Optional three-image mode

Run `python scripts/run_pipeline.py --mode review --input-mode three-image --full FULL.png --background BACKGROUND.png --text TEXT.png --ocr OCR.json --registration registration.json --output-dir OUT`.

Use a separate pure-text image only when it materially improves OCR accuracy. FULL remains the visual reference and BACKGROUND remains the final target coordinate system.

## Review mode

Use either input-mode command above.

The state machine is `validate inputs → normalize line OCR → apply approved global mapping → validate page JSON → render PPTX → render PNG → test overflow → write QA`. Stop immediately on an invalid input, malformed OCR/registration, schema error, rendering error, or failed QA rule. A threshold-level issue completes the artifacts with `status: review`; a clean page uses `status: passed`; a failure returns nonzero and preserves `qa.json` with `status: failed`.

Registration JSON may include `line_corrections`, a map keyed by normalized
`line_id`. Entries may contain `dx`, `dy`, `width_delta`, `height_delta`,
`font_scale`, `reason`, and `source`. Geometry changes occur before the global
transform. Sources `manual` and `powerpoint` are retained as manual corrections;
other sources remain automatic. Limit each font-size step to 3% and cumulative
font-size drift to 8%.

Review checkpoints are the FULL image, geometry-locked text-free background, readable text image plus normalized lines, and final PPT render. Generated RGB/RGBA text images are valid. Review OCR accuracy and the approved transform when the text image drifts; do not approve a later checkpoint when an earlier one is unresolved.

## Batch mode

Use `python scripts/run_pipeline.py --mode batch --manifest batch.json`. The manifest is `{ "input_mode": "two-image", "pages": [...] }`; every page supplies `page_id`, `full`, `background`, `ocr`, `registration`, and `output_dir`, plus `text` only for three-image mode. Keep deterministic page order and a separate output directory per page. A failed page stops only that page; collect `review` pages for human inspection and continue the remaining jobs. Never promote `review` to `passed` merely to complete a batch.

Final acceptance requires readable images with identical positive dimensions, at least one OCR visual line, newline-free line values, one editable textbox per visual line, zero wrapping/merging/overflow, and separately traceable source, mapping, target, automatic-correction, and manual-correction data. Pixel extraction and high-precision registration are optional future advanced-mode steps, not V1 gates.

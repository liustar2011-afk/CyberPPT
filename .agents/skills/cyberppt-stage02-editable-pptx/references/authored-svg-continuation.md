# Authored SVG Continuation

Use this reference only for the `editable` and `both` assembly branches after audited full images exist and the active manifest reports a missing hand-authored SVG.

## Keep the active build

1. Read `<output-dir>/build_context.json` and its `artifacts.page_image_pairs.path`.
2. Verify the source-script hash, style-lock hash, requested pages, production mode and assembly mode against the command being resumed.
3. Continue in that output directory and build ID. A new build loses the page-level recovery boundary.
4. Select only pairs whose audited `full` image exists, `full.text_audit.valid` is true, and `authoring_svg` is missing or invalid.

## Author one page

For each selected pair:

1. Inspect the normalized full image, locked visible text, visual design decision, clean-base requirements and registered local assets.
2. Write `<output-dir>/authoring/page_NNN.svg` on the full-image canvas. Preserve the exact `width`, `height` and `viewBox`; the current production canvas is normally `2048 × 1024`.
3. Reconstruct the complete page with native SVG geometry, text and verified local image layers. Include each locked text item exactly once. Preserve explicit coordinates, font size, weight, color, wrapping and z-order.
4. Keep the audited full image out of the authored SVG. Local cropped or registered assets may be referenced when their identity and page role are verified.
5. Inspect the SVG as a rendered page before registration. Cross-region `<tspan>` jumps, missing locked text, residual Chinese from the base, empty containers and unreadable text require page-local repair.

## Register the page in the active manifest

Update only the current pair:

- Set `authoring_svg` to the absolute SVG path.
- Complete `graphic_text_policy` with schema `cyberppt.image_to_pptx.graphic_text_policy.v1`, the page number, `status: complete`, `empty_container_check: passed`, coordinate binding to the audited full image, and one classified item for every readable graphic-text region.
- Use `native_text` for ordinary readable text and include a unique id, exact text, `source_visible: true`, a bounded full-canvas bbox and its authored line layout.
- Use `preserved_in_image` and `decorative_glyph` only under the main Skill's evidence and visual-review rules.
- Keep `clean_base` unchanged when it is still `required`. The official rerun generates or validates the clean base from the completed policy and authored SVG; do not fabricate a completion receipt.

Do not create a separate manifest, call the adapter directly, or replace the current final script.

## Resume and review

Rerun the original `.venv/bin/python3 -m cyberppt final-script-pages ...` command with the same build ID, output directory, `--generate-images`, `--production-build`, production mode and assembly mode. The orchestrator preserves valid authored SVG and policy fields, prepares the clean base, and continues page-local Quick QA.

For every rendered preview:

1. Inspect the exact OfficeCLI PNG.
2. Record the result with `.venv/bin/python3 -m cyberppt review-quick-page ...`.
3. Resume the same build until every requested page has a current passed checkpoint and the final deck completes OfficeCLI delivery QA.

A page defect remains local. Passed pages with unchanged bindings stay reusable.

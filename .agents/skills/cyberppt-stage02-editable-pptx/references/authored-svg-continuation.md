# Authored SVG Continuation

Use this reference only for the `editable` and `both` assembly branches after audited full images exist and the active manifest reports a missing hand-authored SVG.

## Keep the active build

1. Read `<output-dir>/build_context.json` and its `artifacts.page_image_pairs.path`.
2. Verify the source-script hash, style-lock hash, requested pages, production mode and assembly mode against the command being resumed.
3. Continue in that output directory and build ID. A new build loses the page-level recovery boundary.
4. Select only pairs whose audited `full` image exists, `full.text_audit.valid` is true, and `authoring_svg` is missing or invalid.

## Author one page

For each selected pair:

1. Inspect the normalized full image and locked visible text. Use native reference-image editing to remove readable text while retaining graphic identity, geometry, colors and composition. Save the same-canvas base inside `<output-dir>/authoring/`. Extract exact source crops for photos or identity graphics when needed; inspect every derived image. Do not call the legacy automatic cleaner or read assets from an external project.
2. Write `<output-dir>/authoring/page_NNN.svg` on the full-image canvas. Preserve the exact `width`, `height` and `viewBox`; the current production canvas is normally `2048 × 1024`. Set root `data-cyberppt-native-text-style="locked"` and use relative local image references within this build.
3. Reconstruct the complete page with native SVG geometry, text and verified local image layers. Include each locked text item exactly once. Preserve explicit coordinates, font size, weight, color, wrapping and z-order. Size text for the assembled slide, accounting for the body-slot scale: `authoring_px = target_pt / 0.75 / (body_height / source_height)`. For the standard `1024 → 607` body height, 12 pt body copy requires about 27 px in the authored SVG. The geometry gate enforces final floors of 20 pt for page titles, 15 pt for module titles, 12 pt for body, 10 pt for card body and 9 pt for captions.
4. Keep the audited full image out of the authored SVG. Local cropped or registered assets may be referenced when their identity and page role are verified.
5. Inspect the SVG as a rendered page before registration. Cross-region `<tspan>` jumps, missing locked text, residual Chinese from the base, empty containers and unreadable text require page-local repair.

## Register the page in the active manifest

Update only the current pair:

- Complete `graphic_text_policy` with schema `cyberppt.image_to_pptx.graphic_text_policy.v1`, `fidelity_mode: exact_source_image`, the audited full-image SHA-256 in `source_image_sha256`, the page number, `status: complete`, `empty_container_check: passed`, coordinate binding to the audited full image, and one classified item for every readable graphic-text region.
- Before authoring, freeze every visually verified source text region in `source_text_inventory`. Each entry must contain the final unique `id`, exact visible `text` (or `observed_text` for a reviewed decorative glyph), and the observed full-canvas `bbox`. Copy those entries into `items` without changing their order, wording or coordinates, then add treatment-specific fields. Registration and production fail if the inventory is absent, its source-image hash is stale, or `items` differs from it.
- Use `native_text` for ordinary readable text and include a unique id, exact text, `source_visible: true`, a bounded full-canvas bbox, its authored line layout and a semantic `role` used by the final-size gate. Add the same unique id as `data-cyberppt-text-id` on the corresponding SVG `<text>` node. Every non-empty SVG `<text>` node must be classified exactly once; duplicate wording must use explicit ids so matching remains unambiguous.
- Use `preserved_in_image` and `decorative_glyph` only under the main Skill's evidence and visual-review rules.
- After actual layer and SVG inspection, register the page with the command below. Supply the SHA-256 of the exact source inspected. The command validates the authored inputs and records their current hashes; the four passed decisions must come from visual inspection. It records `authoring_svg` and `clean_base` in the current pair. Do not fabricate a completion receipt.

```bash
.venv/bin/python3 -m cyberppt register-quick-page <output-dir>/page_image_pairs.json \
  --page 1 --svg <output-dir>/authoring/page_001.svg \
  --clean-base <output-dir>/authoring/assets/page_001_clean_base.png \
  --source-sha256 <inspected-full-image-sha256> --reviewer codex-main \
  --source-layout passed --graphic-identity passed \
  --text-removed passed --background-continuity passed
```

Do not create a separate manifest, call the adapter directly, or replace the current final script.

## Resume and review

Rerun the original `.venv/bin/python3 -m cyberppt final-script-pages ...` command with the same build ID, output directory, `--generate-images`, `--production-build`, production mode and assembly mode. The orchestrator preserves valid authored SVG and policy fields, validates registered layers, and continues page-local Quick QA. It does not generate a clean base. A changed base, source crop, SVG or policy requires inspection and registration again.

For every rendered preview:

1. Inspect the exact OfficeCLI PNG.
2. Record the result with `.venv/bin/python3 -m cyberppt review-quick-page ...`.
3. Resume the same build until every requested page has a current passed checkpoint and the final deck completes OfficeCLI delivery QA.

A page defect remains local. Passed pages with unchanged bindings stay reusable.

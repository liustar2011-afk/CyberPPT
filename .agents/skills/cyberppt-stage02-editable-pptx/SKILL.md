---
name: cyberppt-stage02-editable-pptx
description: Route CyberPPT Stage 02 requests for high-fidelity editable PPTX, picture PPT, dual delivery, or image/screenshot/reference-visual reconstruction through the registered production chain.
---

# CyberPPT Stage 02 Editable PPTX

Use this Skill for “图转可编辑 PPT”“按图复刻 PPT”“图片转 PPTX”“高保真可编辑 PPT” and equivalent requests.

## Registered production routes

This Skill is the authoritative owner of these Stage 02 route identifiers:

- `stage02.high_fidelity_quick_editable`: 高保真+Quick、高保真 Quick、无字底图+文字 SVG、authored SVG、图片转可编辑 PPT。
- `stage02.picture_ppt`: 图片型 PPT、整页图片 PPT。
- `stage02.dual_delivery`: 图片型和可编辑 PPT 双份交付。

When any high-fidelity Quick alias appears, select
`stage02.high_fidelity_quick_editable` immediately. Do not search for a separate
legacy pipeline under `scripts/image_to_editable_svg/`; that entry is retired.
The executable orchestration is `cyberppt/commands/final_script_pages.py`, its
CyberPPT-to-Quick boundary is
`scripts/image_to_pptx_runtime/stage02_adapter.py`, and the vendored source
runtime provenance is recorded in
`scripts/image_to_pptx_runtime/UPSTREAM.md`.

Run repository commands from the repository root with `.venv/bin/python3`.
The only production route is `.venv/bin/python3 -m cyberppt final-script-pages` with
`--production-build`; do not construct a final script or `page_image_pairs.json`
by hand and do not call `run_stage02_reconstruction` directly.

Default chain: final script + current `references/visual-system.md` style → audited
full image → reconstruction visual-source binding → text-free base → high-fidelity authored SVG
reconstruction → vendored Quick assembly → render and final-visible-text QA. The
audited full image is the visual source for the editable reconstruction; authored SVG
may reconstruct and decompose it but must not introduce a second visual design.

Stage 02 does not require or invoke a separate visual-structure preparation stage.

## Per-page Quick checkpoint loop

Process authored pages as individual quality transactions. For each content
page: validate the clean-base and graphic-text policy, copy and style the
authored SVG, run geometry and SVG quality QA, build one wrapped preview PPTX,
render its OfficeCLI PNG, and write `quick_page_checkpoint` back to the active
`page_image_pairs.json` immediately with `status: rendered_pending_visual_review`.
The main agent must inspect that exact PNG before the page can pass. Check layout
fidelity, typography, color and weight, wrapping, residual Chinese text, and
readability; syntax, geometry, and file existence never substitute for this look.
Record the result with `.venv/bin/python3 -m cyberppt review-quick-page ...`; the receipt is
bound to the preview PNG hash, so a changed render automatically requires review.

A failed page records `status: failed` while later pages are still checked and
checkpointed. On resume, reuse a visually reviewed passed page when its authored SVG, audited full
image and clean base are unchanged and its target SVG, preview PPTX and preview
PNG still exist. Changed inputs cause local revalidation, not a hash gate,
full-image redraw, or whole-batch invalidation. Assemble the final deck once,
after every requested page has a passed checkpoint; do not merge separately
published one-page PPTX files.

For the high-fidelity Quick branch, use `final-script-pages --production-build
--assembly-mode editable`. It consumes the text-audited full image, same-canvas
clean base, and completed high-fidelity `authoring_svg`. The production command
must not synthesize that SVG from OCR boxes. `image` is
the separate picture-PPT branch; do not use it as evidence about the editable
branch or substitute it for the Quick result.

The default editable branch also runs read-only native-text geometry QA after
the authored SVG is copied into the runtime project and before native styling.
It writes `analysis/native_text_geometry_qa.json` and includes the report in
the Stage 02 result. The report compares policy OCR regions with SVG text
baselines, line metrics and authored font sizes; it does not rewrite SVG
coordinates or infer a PowerPoint font size from OCR bbox height. Ambiguous
matches, missing bboxes and locked SVGs remain explicit review outcomes.
The geometry gate must also inspect every explicit `<tspan>` coordinate inside
each text node. A line that jumps into another column or visual region is a
blocking authored-SVG defect even when the parent `<text>` x/y matches its OCR
box; do not let a page-level visual-review receipt override that failure.

Before export, every page needs a complete `clean_base` contract and
`graphic_text_policy`. Ordinary readable text uses `native_text`. Use
`preserved_in_image` only for text integral to an identity graphic, with
`identity_integral: true` and a verified local asset. Read the canonical
[`docs/CYBERPPT_WORKFLOW.md`](../../../docs/CYBERPPT_WORKFLOW.md)
before production.

## Authored SVG continuation

When the active manifest records `requires a hand-authored SVG from the image-to-PPTX runtime`, production has reached the authored-SVG checkpoint. Do not start a new build and do not report delivery failure as a finished result. Read [references/authored-svg-continuation.md](references/authored-svg-continuation.md), complete the missing page artifacts in the active manifest, and resume the same build with the same output directory, production mode, assembly mode and image-generation flags.

## Text-free base policy

Treat the locked script as text truth and OCR only as a coordinate anchor. Classify
every visible body-graphic text item before removal:

For high-fidelity Quick reconstruction, the authoring step must provide a real,
completed SVG on the normalized slide canvas. OCR supplies text truth and
location evidence only; it does not authorize a production-time OCR-box SVG
generator. The vendored Quick runtime consumes the authored SVG and preserves
its explicit coordinates, font size, weight, and color.

The current Codex main agent owns this reconstruction step, matching the source Quick
workflow: inspect the normalized audited full image, clean base, locked onscreen text
and registered local assets, then reproduce the accepted visual composition as the
complete page SVG on the same canvas. The authored SVG preserves the bound full
image's spatial composition and visual hierarchy; it does not reopen visual design.
`final-script-pages` prepares and validates the workspace; if an
`authoring_svg` is absent it must stop for authoring, then resume the same build.
Do not replace this step with an OCR-to-SVG generator or redraw an already-audited
full image merely because its recognized wording differs from the locked text
truth; write the locked truth into the authored SVG.

- `native_text`: all readable information, labels, figures, captions and ordinary
  text. Remove it from the base and rebuild it in SVG.
- `preserved_in_image`: only wording inseparable from an identity graphic, using a
  verified local crop. Never preserve it in the full image or clean base.
- `decorative_glyph`: an OCR false positive or pseudo-text mark that has no
  business meaning. Keep it as part of its local graphic; record its observed
  glyph, bounding box and a passed `non_semantic_glyph` visual review. It must
  not be rebuilt as SVG text or used for ordinary readable wording.

Use native reference-image editing to prepare the same-canvas text-free base.
Inspect the source first. Preserve composition, graphic identity and background
continuity; use exact source crops for identity-sensitive photos or graphics.
Inspect every derived raster layer and the recomposed SVG before registration.
Do not use OCR-box whiteout or the legacy automatic masked clean-base generator.
Pixel identity outside a text mask is not the acceptance rule for reference edits.

Complete the graphic-text policy from observed source regions, without estimating
region widths from character counts. Author explicit line coordinates and set
`data-cyberppt-native-text-style="locked"` on the SVG root so native export preserves
the author's typography. Register the inspected local assets using
`register-quick-page` as described in the continuation reference. The command
binds source, base, SVG, all image layers and policy to the review; changes require
fresh review. It does not author pages or make visual decisions.

This workflow and its runtime are fully local to CyberPPT. Do not import another
project's completed SVGs or invoke an external Quick backend. The official
`final-script-pages` route consumes reviewed layers and never calls the old
automatic cleaner. Historical v3 receipts remain readable for existing projects.
Post-clean OCR remains diagnostic; final rendered-page review decides release.

The release decision belongs after SVG rewrite and PPTX render. Check the final
visible result for wrong Chinese characters and pseudo-Chinese only. Ignore
punctuation, isolated digits, and English tokens. A real residual Chinese string
that remains visible alongside, or instead of, its SVG rewrite blocks release;
an OCR-only residual in the intermediate clean base does not.

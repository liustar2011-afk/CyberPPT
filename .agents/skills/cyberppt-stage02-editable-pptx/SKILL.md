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

Default chain: audited full image → text-free base → high-fidelity authored SVG →
vendored Quick assembly → render and final-visible-text QA.

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
`identity_integral: true` and a verified local asset. Read
[`docs/CYBERPPT_WORKFLOW.md`](../../../docs/CYBERPPT_WORKFLOW.md) and the repository
[`SKILL.md`](../../../SKILL.md) before production.

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

The current Codex main agent owns this authoring step, matching the source Quick
workflow: inspect the normalized full image, clean base, locked onscreen text and
registered local assets, then write the complete page SVG directly on that same
canvas. `final-script-pages` prepares and validates the workspace; if an
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

For every `native_text` item, record one exact bounded clearance region linked by
its policy id. Repair only that region with `flat-surface-rebuild`,
`local-background-reconstruction`, or `masked-inpainting`. OCR-region whiteout is
not an acceptable final repair method.

The clean-base review must pass three image-integrity checks: the declared
clearance regions change, background continuity is restored, and pixels outside
the declared clearance mask stay within tolerance. Reference-image reconstruction
is not exempt: generated pixels may be written back only inside declared masks,
while every outside pixel must come from the audited full image; validation must
recompute the pixel difference instead of trusting the manifest receipt. Post-clean OCR is diagnostic
evidence for the clearance operation. It must not independently require zero OCR
residuals or trigger image regeneration after the source full image has passed
its Chinese-character gate.

The release decision belongs after SVG rewrite and PPTX render. Check the final
visible result for wrong Chinese characters and pseudo-Chinese only. Ignore
punctuation, isolated digits, and English tokens. A real residual Chinese string
that remains visible alongside, or instead of, its SVG rewrite blocks release;
an OCR-only residual in the intermediate clean base does not.

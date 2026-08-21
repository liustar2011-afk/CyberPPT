---
name: cyberppt-stage02-editable-pptx
description: Route any request to convert a rendered image, screenshot, or reference visual into an editable CyberPPT PPTX through the mandatory Stage 02 default chain.
---

# CyberPPT Stage 02 Editable PPTX

Use this Skill for “图转可编辑 PPT”“按图复刻 PPT”“图片转 PPTX”“高保真可编辑 PPT” and equivalent requests.

The only production route is `python -m cyberppt final-script-pages` with
`--production-build`; do not construct a final script or `page_image_pairs.json`
by hand and do not call `run_stage02_reconstruction` directly.

Default chain: audited full image → text-free base → native SVG text rebuild →
editable PPTX assembly → render and text QA.

Before export, every page needs a complete `clean_base` contract and
`graphic_text_policy`. Ordinary readable text uses `native_text`. Use
`preserved_in_image` only for text integral to an identity graphic, with
`identity_integral: true` and a verified local asset. Read
`docs/CYBERPPT_WORKFLOW.md` and the repository `SKILL.md` before production.

## Text-free base policy

Treat the locked script as text truth and OCR only as a coordinate anchor. Classify
every visible body-graphic text item before removal:

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

The clean-base review must pass four checks: the intended text is removed,
background continuity is restored, pixels outside the declared clearance mask are
preserved, and a post-clean OCR pass finds no removed native text. The runtime also
measures pixel changes: every clearance region must change and changes outside the
mask must remain within the declared tolerance. A failed check blocks export.

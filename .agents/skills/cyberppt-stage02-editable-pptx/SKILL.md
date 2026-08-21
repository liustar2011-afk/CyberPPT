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

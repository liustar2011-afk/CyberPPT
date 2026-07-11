---
name: three-image-to-ppt
description: Convert a FULL slide image, a text-free background image, and a text image into line-level OCR JSON and a PowerPoint slide with editable text. Use when the user asks to generate three slide images, convert AI-generated slide artwork to editable-text PPT, preserve visual line breaks, calibrate text coordinates to a text-free background, or batch-review three-image-to-PPT outputs.
---

# Three Image to PPT

Convert GPT slide images plus OCR JSON into a PowerPoint slide whose background remains visually faithful while its text stays editable. Default to two-image mode (FULL + text-free BACKGROUND + OCR JSON); use three-image mode when a separate TEXT image is needed for cleaner OCR.

## Choose a mode

- **Build mode:** Default two-image input is FULL + text-free BACKGROUND + OCR JSON. Three-image input adds TEXT as the OCR source. Follow [workflow.md](references/workflow.md), use [page-schema.md](references/page-schema.md), and apply [prompt-spec.md](references/prompt-spec.md).
- **Review mode:** Use when inspecting an existing three-image conversion. Do not rebuild unless asked; validate artifacts against [qa-rules.md](references/qa-rules.md) and report issues with slide and line identifiers.
- **Batch mode:** Use when processing or reviewing multiple slides. Treat each slide as an independent three-image set, preserve deterministic input order, isolate per-slide failures, and return a combined summary after applying [qa-rules.md](references/qa-rules.md) to every slide.

For build or batch production, route each page through `scripts/run_pipeline.py --input-mode two-image` by default; use `--input-mode three-image --text TEXT.png` when required. Batch manifests contain independently scheduled pages with deterministic order. Treat each page `qa.json` status as authoritative: continue on `passed`, pause for inspection on `review`, and stop only that page on `failed`.

## Core requirements

1. Resolve the canvas from the page script before generation: use an explicit pixel size first, then an explicit ratio, otherwise default to 1920×1080 (16:9). Require FULL and BACKGROUND to be readable, have positive identical pixel dimensions matching that contract, and represent the same slide. In three-image mode TEXT must match those dimensions. Record SHA-256 hashes; do not require transparency or pixel provenance.
2. Treat FULL as the visual reference and coordinate bridge, the text-free background as the PowerPoint background and final target coordinate system, and the text image as OCR input. The text image may drift; use an approved global transform plus traceable manual per-line corrections to map OCR geometry into target coordinates.
3. Preserve visual line breaks: each text value must contain no carriage-return or line-feed characters (CR/LF), and each visual text line must map to exactly one editable text box. Set every text box to zero internal inset, no wrap, and no automatic reflow. Never merge separate visual lines or split one visual line across boxes.
4. Use Microsoft YaHei as the default PowerPoint font. When correcting font size for visual fit, limit each correction to at most 3% of the current size and all cumulative corrections to at most 8% of the initial size.
5. Preserve placement, alignment, rotation, and relative scale when converting source pixels to slide coordinates.
6. Validate both the structured output and rendered slide using [page-schema.md](references/page-schema.md) and [qa-rules.md](references/qa-rules.md).

## V1 limitations

- V1 handles text at visual-line granularity, not character-, word-, span-, or paragraph-level rich-text reconstruction.
- It does not guarantee exact font identification, kerning, glyph substitution, or pixel-perfect typography when the source font is unavailable.
- Complex effects such as warped text, text on a path, perspective distortion, dense overlaps, and decorative glyph artwork may require manual correction.
- V1 accepts generated RGB or RGBA text images and does not perform pixel extraction, segmentation, transform estimation, or high-precision registration. Those are optional future advanced-mode capabilities.
- Editable output covers recognized text only. Non-text artwork remains flattened in the text-free background.

## References

- [End-to-end workflow](references/workflow.md)
- [Line-level page schema](references/page-schema.md)
- [Generation and OCR prompt specification](references/prompt-spec.md)
- [Quality assurance rules](references/qa-rules.md)
- [Canvas contract](references/canvas-spec.md)

# Editable-Text Three-Image Production Design

**Date:** 2026-07-11

## Goal

Add an opt-in CyberPPT production branch that turns approved Stage 1 and
Stage 2 page scripts into template-based PPTX slides with editable body text.
The branch uses the vendored `vendor/three-image-to-ppt` workflow, while the
existing `full_image_ppt` branch remains the default and unchanged.

## Decision

Use a template-native adapter. The vendor workflow owns three-image validation,
OCR normalization, coordinate mapping, line-level QA, and its portable
`page.json` contract. CyberPPT owns project state, approval gates, template
text, speaker notes, final slide assembly, delivery QA, and artifact ledger.

Do not import vendor-produced page PPTX files into the CyberPPT deck. That
would create conflicting slide sizes, masters, and public template elements.

## Configuration and CLI

Project configuration gains `production_mode` with these values:

- `full_image_ppt` — default current behavior.
- `editable_text_three_image` — requires FULL, BACKGROUND, and TEXT images for
  each selected page, then creates editable body text from line-level OCR.

The production CLI gains an explicit editable-text transition after the shared
`produce prepare` output. Its status result must state the selected mode and
the next legal action. Existing commands retain their behavior for projects
without an editable-text mode declaration.

## Workflow

```text
approved analysis and blueprint script
  -> shared final-script / template-text-lock / speaker-notes preparation
  -> editable-text three-image generation contract per page
  -> FULL + BACKGROUND + TEXT + OCR + registration
  -> vendor validation, normalization, mapping, page.json and qa.json
  -> CyberPPT template-native editable-body assembly
  -> existing render QA, strict PPTX validation, delivery promotion
```

For each page, CyberPPT writes a project-local job directory containing the
three image paths and SHA-256 hashes, OCR source and registration inputs,
vendor `page.json`, vendor `qa.json`, rendered review image, and a resume
command. Batch scheduling remains deterministic and page-isolated: `failed`
blocks only that page, `review` stops at a human inspection gate, and only
`passed` pages may enter template assembly.

## Assembly Contract

The editable-body adapter consumes a passed vendor `page.json` and the
existing per-page template text lock.

- `BACKGROUND` is placed in the CyberPPT template body region.
- Every vendor `text_line` creates exactly one native PowerPoint textbox, named
  `text-<page_id>-<line_id>`.
- The adapter maps vendor target coordinates from image pixels into the
  template body region without stretching inputs or altering approved geometry.
- Textboxes use Microsoft YaHei by default, zero margins, no automatic wrap or
  reflow, and preserve mapped alignment and rotation.
- Template-owned title, subtitle, logo, header, footer, page-badge behavior,
  and speaker notes continue to use existing CyberPPT truth artifacts. They
  are never inferred from OCR or image pixels.

## Gates and Recovery

The branch shares analysis, visual style, blueprint input, and speaker-notes
approvals with the current mainline. It adds these hard gates before assembly:

1. Every selected page has readable, same-size FULL/BACKGROUND/TEXT inputs and
   a current hash manifest.
2. Vendor page QA has status `passed`; `review` requires explicit approval and
   `failed` rejects that page.
3. Page JSON has at least one newline-free text line, stable object names, and
   valid target geometry.
4. The full selected page set passes before a deck can be promoted.

All artifacts are registered in `workbench/artifact-ledger.json` with their
dependencies, status, hashes where available, supersession chain, and resume
command. A changed image, OCR input, registration input, or `page.json` makes
the dependent assembly and delivery stale.

## Testing

Tests must prove:

1. Existing projects retain `full_image_ppt` behavior.
2. Editable-text configuration and CLI status select the new legal path.
3. Missing images, mismatched dimensions, stale artifacts, `review`, and
   `failed` vendor results cannot assemble or promote a deck.
4. A passed page creates the background plus one stable editable textbox per
   source visual line, while template text remains template-owned.
5. Batch ordering, page-isolated failure reporting, recovery commands, ledger
   entries, final rendering, and delivery validation all work across multiple
   pages.

## Scope Boundaries

This change does not change default production mode, support OCR as a source
for template text, add character-level rich-text reconstruction, or silently
promote vendor review findings. The vendor continues to be invoked from its
vendored location; CyberPPT consumes its documented page-level artifacts rather
than duplicating its OCR and coordinate-mapping implementation.

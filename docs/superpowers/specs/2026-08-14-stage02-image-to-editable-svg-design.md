# Stage 02 image-to-editable-SVG replacement design

## Decision

Stage 02 will replace the legacy dual-image editable-overlay route with one
production branch: `image-to-editable-svg`.

The branch accepts only a generated `full` page image that has already passed
the existing image-text/typo audit.  It reconstructs that page as editable SVG
objects, validates the SVG, and uses the existing SVG-to-DrawingML exporter to
assemble the final PPTX.  It must not use a complete page screenshot as a
delivered slide backing layer with text merely overlaid above it.

## Scope

Remove the production modes `editable-overlay` and
`editable-overlay-text-reference`, including their `background` and
`text_reference` manifest variants, image-generation operations, CLI choices,
rebuild entrypoints, and mode-specific tests.  `full-image` remains the image
generation mode and is the input stage for `image-to-editable-svg`; it is not
an alternative editable assembly route.

The change is intentionally not backward compatible with old dual-image
manifests.  A legacy manifest must fail with a clear migration error rather
than silently run an obsolete rebuild path.

## Production flow

```text
approved final script + Stage 02 visual design
  -> full image generation
  -> existing image-text / typo audit (hard gate)
  -> image-to-editable-svg reconstruction, one page at a time
  -> SVG quality gate
  -> SVG-to-DrawingML PPTX assembly
  -> PPTX native-text readback + rendered reference comparison
  -> delivery readiness report
```

The reconstruction step reads the current approved script as the text truth
and the audited full image as the visible-surface reference.  It writes a
single page SVG with native text and native simple geometry, placing only
independently useful non-text visual layers as image objects.

## Page reconstruction contract

Each selected page writes under the current Stage 02 build root:

- `analysis/reconstruction_inventory.json`, describing observed text,
  graphics, image regions, data graphics, source bboxes, and confidence;
- `svg_output/pNN.svg`, the editable page representation;
- `analysis/pNN-reconstruction-quality.json`, covering source truth binding,
  object realization, reference exclusion, and SVG quality;
- final assembly artifacts: the exported PPTX, editable-text readback report,
  render comparison report, and delivery-readiness report.

Objects follow these rules:

| Visible family | Realization |
| --- | --- |
| Ordinary slide text | Native SVG/PPT text using the approved script as truth |
| Simple geometry | Native SVG shapes |
| Scene/illustration | Registered image layer(s), never a hidden full-page screenshot |
| Logo, icon, ornament | Exact asset or deterministic redraw only when identity is verified |
| Chart, table, data graphic | Verified native object or exact source graphic; never generative recreation |

If a required visible region cannot be reliably reconstructed, the page records
`manual_required` with the region id and reason.  Such a page blocks PPTX
assembly and delivery.

## Gates and errors

The existing image-text audit remains before reconstruction and cannot be
skipped by the new branch.  Reconstruction validates that the audited full
image exists and that its audit receipt is valid.  The new readiness report
blocks on any of: missing text truth, unresolved text mismatch, unverified
data/identity graphic, missing SVG, SVG quality error, PPTX text mismatch, or
failed render comparison.

The CLI reports page-specific failures and retains generated evidence for
diagnosis.  It does not generate a background image, retry through the removed
dual-image workflow, or flatten an unresolved page to force delivery.

## Integration boundaries

The manifest builder owns production-mode validation and produces only the
`full` image variant.  A dedicated image-to-editable-SVG orchestrator owns
inventory, SVG authoring, per-page QA, and assembly handoff.  The existing
SVG-to-PPTX builder remains the sole final PPTX compiler.  Existing full-image
generation and image-text QA remain upstream owners and are not duplicated.

## Verification matrix

1. Manifest and CLI tests reject removed modes and legacy dual-image manifests.
2. Image generation tests prove a valid `full` image plus valid typo-audit
   receipt is required before reconstruction.
3. Reconstruction tests use a representative page to assert native script
   text, no canonical full-page source image packaged as slide media, and SVG
   quality success.
4. Failure tests cover `manual_required`, invalid typo receipt, missing script
   truth, and unverified data graphic; each blocks final assembly.
5. End-to-end tests compile multiple page SVGs to a PPTX, read its editable
   text back, render it, and confirm the delivery-readiness report passes.

## Non-goals

This change does not redesign Stage 01, alter prompt authorship, retain dual
image compatibility, or claim that every raster visual can be fully native.
Unverifiable source regions remain an honest manual-reconstruction blocker.

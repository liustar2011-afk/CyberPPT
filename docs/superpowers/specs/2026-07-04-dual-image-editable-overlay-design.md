# CyberPPT Dual Image Editable Overlay Design

Date: 2026-07-04
Status: approved design draft
Owner: CyberPPT workflow

## Purpose

Add a CyberPPT third-stage delivery mode named `dual_image_editable_overlay`.

The mode combines CyberPPT's content governance with the dual-image rebuild pattern:

- CyberPPT remains the source of truth for evidence, storyline, slide content, visual system, approval gates, and QA.
- A text-bearing `full` image is used as visual evidence for composition, text placement, hierarchy, and style.
- A no-text `background` image is used as the locked raster visual layer.
- The final PPTX places editable PowerPoint text boxes over the no-text background.

This mode is meant for high-visual-fidelity production when full native reconstruction would be too slow or would degrade the generated visual surface.

## Problem

CyberPPT's current third-stage contract targets full or mixed native reconstruction. It explicitly treats whole-slide blueprint backgrounds as a failure risk and requires PptxGenJS as the formal generation engine.

The dual-image workflow from `ppt-master` solves a different problem: preserve a completed visual page as a no-text raster background and rebuild only the text layer as editable objects. It is faster and more visually stable, but it conflicts with CyberPPT's current default QA assumptions unless represented as a separate, explicit mode.

## Goals

1. Keep CyberPPT's evidence and content locks as the only truth for final text, numbers, labels, caveats, and SO WHAT.
2. Support generated image dimensions that differ from the working canvas by normalizing all page images and coordinates to `1280x720`.
3. Use full images for locator/style evidence, not for final text truth.
4. Use no-text backgrounds as legal full-slide raster backgrounds only inside this declared mode.
5. Generate formal delivery PPTX files with PptxGenJS. A temporary non-PptxGenJS adapter may be used only for diagnostics and cannot produce an accepted CyberPPT final page.
6. Provide page-level QA that checks text editability, text-content fidelity, background text removal, safe-area fit, local visual alignment, and batch readiness.
7. Preserve CyberPPT's staged review model: pilot pages first, then batch pages, then merge only approved single-page PPTX files.

## Non-Goals

1. This mode does not make background shapes, icons, charts, curves, or table structure editable.
2. This mode does not replace the existing native reconstruction path.
3. This mode does not allow text, key numbers, chart labels, sources, or SO WHAT to remain baked into the background.
4. This mode does not use OCR text as final wording.
5. This mode does not waive visual QA; it changes the QA questions to match the delivery mode.

## Mode Contract

`delivery_mode = "dual_image_editable_overlay"`

Allowed:

- One full-slide no-text background picture covering the slide.
- Editable PowerPoint text boxes for all key text.
- Local non-text visual details embedded in the background.

Required:

- `background_snapshot_editable_text = true`
- `background_has_no_text = true`
- `all_key_text_editable = true`
- `text_content_matches_lock = true`
- `container_overflow_pass = true`
- `layout_qa_error_count = 0`
- `visual_semantics_preserved = true`
- `background_image_declared = true`

Disallowed:

- Treating the generated full image text as factual truth.
- Hiding text mismatch by changing the content lock.
- Letting the background contain readable primary text.
- Using this mode when the user needs editable charts, arrows, tables, or background components.

## Architecture

The design has five layers.

1. Content Governance Layer

   CyberPPT Stage 1 and Stage 2 continue to produce or reference:

   - `slide_content_lock.json`
   - `blueprint_component_signature.json`
   - `visual_element_registry.json`
   - `stage2_visual_lock.md`
   - approved full/background image prompts

2. Image Pair Layer

   Each page has:

   - `page-XX-full.png`: text-bearing image
   - `page-XX-background.png`: same composition with all text removed
   - `page-XX-full-1280x720.png`
   - `page-XX-background-1280x720.png`

   The preferred background generation method is image editing from the full image, not independent text-to-image generation, because it reduces drift.

3. Layout Evidence Layer

   Each page has:

   - `text_layout.json`: locator and style evidence from the full image
   - `background_text_scan.json`: OCR/vision check proving the background is no-text
   - optional `alignment_report.json`: small full-to-background drift estimate

   These artifacts are diagnostic evidence. They do not decide final wording.

4. Semantic Plan Layer

   Each page has `semantic_plan.json` generated from CyberPPT locks:

   - `containers[]`: background geometry and text-safe bboxes
   - `items[]`: final editable text from `slide_content_lock`
   - `container_id`: explicit binding from each item to its owning container
   - `role`: title, subtitle, body, KPI, evidence label, caveat, SO WHAT, etc.
   - `source_text`: locked source text
   - `display_text`: final visible text, defaulting to locked source text unless explicitly revised

   The semantic plan owns final geometry for production. OCR boxes only help derive or validate it.

5. PPTX Render Layer

   PptxGenJS builds each formal single-page PPTX:

   - set slide size to 16:9
   - place the normalized background image full-slide
   - add editable text boxes from `semantic_plan.items[]`
   - record every text box in `text_mapping.json`
   - render preview PNG/PDF for visual QA

## Data Flow

```text
Stage 1 evidence and storyline
  -> slide_content_lock.json
  -> Stage 2 visual lock and approved page prompts
  -> full image + no-text background image
  -> normalize both images to 1280x720
  -> text_layout.json from full image
  -> semantic_plan.json from CyberPPT locks and containers
  -> PptxGenJS single-page PPTX
  -> text_content_qa.json
  -> layout_qa.json
  -> visual_qa_gate.json
  -> user page approval
  -> merge approved pages only
```

## Artifact Layout

Recommended per-project layout:

```text
workbench/dual-image/
  page-XX/
    sources/
      page-XX-full.png
      page-XX-background.png
    normalized/
      page-XX-full-1280x720.png
      page-XX-background-1280x720.png
    analysis/
      text_layout.json
      background_text_scan.json
      semantic_plan.json
      alignment_report.json
      text_mapping.json
      text_content_qa.json
      layout_qa.json
      production_readiness.json
    exports/
      page-XX.pptx
      page-XX-render.png
      side-by-side.png
      local-crops/
```

## QA Model

Existing CyberPPT `native_rebuild` QA remains unchanged.

For `dual_image_editable_overlay`, QA must check these gates:

1. Background Text Removal Gate

   The background image must have no readable primary text, numbers, labels, evidence IDs, title text, SO WHAT, source text, or page metadata. Use OCR/vision plus local crop review for title, table, evidence label, caveat, and SO WHAT regions.

2. Content Truth Gate

   Final PPTX text must match `slide_content_lock` and `semantic_plan.items[]`. The check reads the exported PPTX text layer directly; PDF rendering and OCR are not accepted as text truth.

3. Editability Gate

   All key text roles must be native text boxes:

   - title
   - subtitle
   - body
   - KPI / key number
   - table text when represented as visible text
   - evidence labels
   - caveats
   - SO WHAT

4. Container Fit Gate

   Every text item must fit inside its `text_safe_bbox` or declared container. Minimum font floors apply; the workflow cannot solve fit by shrinking text indefinitely.

5. Drift Gate

   Full/background drift must be bounded. If explicit semantic containers exist, their geometry is the production source. If they do not exist, the output is diagnostic only.

6. Visual Semantics Gate

   The page must preserve the intended visual hierarchy, surface system, composition, and reading order. A full background image is allowed in this mode, but only as the non-text visual layer.

7. Batch Gate

   Run P2/P3 first as pilot pages. Batch all pages only after the pilot pages pass text-content QA, layout QA, background text scan, and human visual review.

## Risk Controls

| Risk | Control |
|---|---|
| Background keeps text residue | OCR/vision scan plus crop QA; regenerate or repair background |
| Full/background drift | Generate background by image edit from full; normalize to 1280x720; use semantic containers as final geometry |
| Real script text is longer than generated placeholder | Prompt for reserved text space; use `text_safe_bbox`; enforce font floors; revise content or regenerate background when it cannot fit |
| OCR locator mistakes | OCR is diagnostic only; final text comes from content lock; bind text through roles and container IDs |
| Delivery is not object-level editable | Declare `delivery_mode`; route object-editable requests back to native rebuild |
| QA false failure from old full-slide-background rule | Add mode-aware validator logic for declared no-text backgrounds |
| Batch inconsistency | Pilot pages first; per-page manifests and QA; merge only approved pages |

## Implementation Phases

Phase 1: Pilot Adapter

- Use existing P2/P3 assets.
- Create hand-reviewed `semantic_plan.json` for P2/P3.
- Generate a PptxGenJS single-page PPTX. If any external adapter is used to compare behavior, mark its output diagnostic-only.
- Record the full artifact set and QA gaps.

Phase 2: CyberPPT Native Generator

- Add repo-local `dual_image_editable_overlay` scripts.
- Generate with PptxGenJS.
- Add `semantic_plan` builder from `slide_content_lock`, component signature, registry, and locator evidence.

Phase 3: Mode-Aware QA

- Extend `validate_pptx.py` for `delivery_mode`.
- Add text-content QA.
- Add background text scan.
- Add container fit QA.
- Adjust `visual_qa_gate.json` so `blueprint_background_not_used` is not required in this mode; use `background_snapshot_declared_and_no_text` instead.

Phase 4: Batch Production

- Run P2/P3 pilot.
- Batch generate the remaining pages.
- Review failed pages individually.
- Merge only approved single-page PPTX outputs.

## Acceptance Criteria

A page in this mode is acceptable only when:

- source and background images are normalized to `1280x720`
- the background no-text scan passes
- `semantic_plan.containers[]` exists
- every final text item has `container_id`
- exported PPTX text matches the mapping and lock
- all key text is editable
- layout QA reports zero hard errors
- visual QA confirms readable text and preserved visual semantics
- the page has a complete manifest and render evidence

## Design Decision

Use a separate CyberPPT delivery mode rather than weakening the existing third-stage native reconstruction rules.

This preserves the original high-editability path for users who need editable charts, tables, shapes, arrows, and background objects, while adding a faster high-fidelity path for cases where the practical requirement is a stable visual background with editable key text.

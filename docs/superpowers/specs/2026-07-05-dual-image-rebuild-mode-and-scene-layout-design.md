# Dual Image Rebuild Mode And Scene Layout Design

## Context

CyberPPT dual-image rebuild currently has two valid operating modes:

- `full_slide`: the supplied `full` and `background` images are complete 16:9 slides. The rebuilt PPT render should be compared against the original full slide.
- `template_body_region`: the supplied images are treated as the body/content region and are inserted into the CyberPPT template chrome. The rebuilt PPT render should be compared against a template-normalized reference, not directly against the raw source full image.

The page 006 test exposed two different issues:

- The rebuild ran through the template body route while the visual QA compared the final PPT render directly with the raw full image. That mixes legal template chrome differences into the visual failure count.
- The semantic layout plan correctly produced per-line slots for ability-card text, but `scene_graph.layout` collapsed several text nodes in the same card to one container safe bbox. This caused visible text stacking and is a real rendering bug independent of QA reference mode.

## Goals

- Make rebuild mode explicit and machine-readable.
- Ensure visual QA compares against the correct reference for the selected mode.
- Preserve `semantic_layout_plan.items[].bbox` through scene graph layout so final editable text uses the fine-grained slots already computed upstream.
- Keep strict gates: template-mode normalization can remove false positives, but text stacking, text overflow, and spatial drift must remain blocking.

## Non-Goals

- Do not redesign OCR or introduce a new OCR dependency.
- Do not change the source-capture schema wholesale.
- Do not change the default CyberPPT template chrome.
- Do not make native object-level reconstruction of icons, arrows, and containers part of this revision.

## Proposed Approach

### 1. Rebuild Mode Contract

Add `rebuild_mode` to `page_image_pairs.json` or its `generation_contract`:

- `full_slide`
- `template_body_region`

If absent, preserve current behavior by treating the manifest as `template_body_region`.

The mode should flow into:

- `rebuild_quality.json`
- `template_rebuild_readiness.json`
- `visual_qa_gate.json`

Each readiness artifact should include `visual_reference_mode` so a failed QA can be interpreted correctly.

### 2. Template-Normalized Visual Reference

For `full_slide`, visual QA uses:

- blueprint/reference: raw `full` image
- comparison target: PPT render

For `template_body_region`, visual QA uses:

- blueprint/reference: generated template-normalized reference image
- comparison target: PPT render

The template-normalized reference should use the same body region and master chrome geometry used by export. It exists only for QA; it is not a delivery asset.

### 3. Scene Graph Layout Slot Preservation

`build_page_scene_graph()` already receives `semantic_layout_plan`. The missing link is that `build_layout_plan_from_scene_graph()` cannot see the semantic item bbox it should preserve.

Add item-level layout evidence to text nodes, for example:

- `style["layout_bbox"]`
- `style["layout_strategy"]`
- `style["layout_source"] = "semantic_layout_plan"`

The scene graph layout executor should resolve text bbox in this order:

1. Explicit item-level `layout_bbox` from semantic layout plan.
2. Edge-label bbox logic for `edge_label`.
3. Honored text-zone bbox from layout intent.
4. Binding `safe_bbox`.
5. Container inset fallback.

The emitted page layout item should retain:

- `layout_strategy`
- `layout_source`
- `target_id`
- `binding_type`

This makes downstream QA able to distinguish "slot-preserved" from "container fallback".

### 4. Gate Behavior

Visual QA should be mode-aware:

- Wrong reference mode is a QA setup failure, not a visual fidelity result.
- `template_body_region` must not compare raw source full slide directly against a template render.
- Any item whose final bbox is duplicated with sibling text in the same target container should be flagged as text stacking.

The readiness status sequence should distinguish:

- `template_rebuild_required`
- `scene_graph_rework_required`
- `source_capture_rework_required`
- `visual_qa_setup_required`
- `visual_qa_rework_required`
- `ready_for_visual_qa`

## Testing Plan

Use test-first implementation.

### Red Tests

1. `test_scene_graph_layout_preserves_semantic_item_bbox`
   - Build a graph with semantic layout items for `1`, `目录管理`, and two bullets in one ability card.
   - Assert page layout emits distinct bboxes matching the semantic layout item slots.
   - Current behavior should fail because all items collapse to the same safe bbox.

2. `test_template_body_region_visual_reference_is_template_normalized`
   - Given a manifest with `rebuild_mode: template_body_region`, assert readiness or QA metadata records a template-normalized reference instead of raw full image comparison.
   - Current behavior should fail because the QA can point to the raw full image as reference.

3. `test_full_slide_visual_reference_uses_raw_full_image`
   - Given `rebuild_mode: full_slide`, assert the raw full image remains the reference.

### Verification Commands

- `PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_scene_graph_layout.py tests/test_scene_graph_workflow.py tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_overlay_semantic_plan.py`
- Re-run page 006 rebuild after implementation.
- Confirm page 006 readiness no longer reports a false mode/reference mismatch.
- Confirm ability-card text nodes no longer share the same bbox.

## Risks

- Template-normalized visual reference generation may initially be image-composition-only and not a full PowerPoint render. It must still use the exact same template/body geometry to be valid for QA.
- Preserving semantic item bboxes may expose bad upstream semantic plans. That is acceptable; bad upstream geometry should fail visibly instead of being hidden by coarse container fallback.
- Existing tests may rely on the old container fallback behavior. Those should be updated only where the new explicit slot-preservation contract applies.

## Acceptance Criteria

- Rebuild artifacts declare `rebuild_mode` and `visual_reference_mode`.
- Template-body visual QA no longer compares raw full image directly against final template render.
- Scene graph page layout preserves semantic layout item bboxes when available.
- Page 006 ability-card text no longer collapses to identical bboxes.
- Tests cover both rebuild modes and the scene graph layout preservation behavior.

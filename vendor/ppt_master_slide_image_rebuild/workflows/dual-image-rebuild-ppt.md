---
description: 双图复刻ppt — use a full text-bearing slide image plus a no-text background image to export background + editable text PPTX.
---

# 双图复刻ppt

> Use this standalone branch when the user provides two images of the same slide:
> one complete image with text, and one no-text image that keeps the visual
> background, containers, icons, charts, and other non-text elements.

This workflow does **not** replace the default `strict-path.md` image rebuild.
It reuses the original Phase A architecture intake and semantic understanding
contract, then changes only the execution target: the no-text image becomes the
locked slide background, while semantic text from the full image is rebuilt as
editable PowerPoint text boxes. It does not draw shapes, icons, arrows,
connectors, charts, or decorative elements.

## Trigger

Run this route when the user says any of:

| User intent | Route |
|---|---|
| "双图复刻ppt" | This workflow |
| "一张完整图，一张无文字底图" | This workflow |
| "底图不编辑，只把文字做成可编辑" | This workflow |
| "用完整图定位文字，用无字图做底稿" | This workflow |

Do **not** run this route for ordinary single-image "图转PPT / 按图复刻PPT"
requests. Those stay on `strict-path.md`.

## Contract

| Layer | Treatment |
|---|---|
| No-text background image | Full-slide raster background, locked by layer order |
| Visible text | Editable PPT text boxes; final wording comes from AI-designed `display_text` based on semantic understanding. Default to clear, complete expression; revise only when it cannot fit readably after using the semantic safe area. Production acceptance requires explicit `semantic_plan.containers[]` and `items[].container_id`; OCR/text-layout alone is diagnostic input, not delivery truth. |
| Cards / icons / connectors / charts / decorations | Preserved inside the background image, not editable |
| Architecture intake | Keep original `layout_reference`, `content_mapping`, `text_region_map`, `design_spec`, `svg_build_plan` artifacts |
| Full-image style learning | During semantic extraction, learn the full image's text-layer style: hierarchy, font size, weight, color, alignment, line rhythm, and grouping. This is style evidence only; full-image hard line breaks are not final wrapping truth. |
| Typesetting policy | Preserve AI-authored `display_text`; prefer readable fit inside the semantic safe area over imitating full-image line breaks; apply wrapping defaults, alignment defaults, safe-area height expansion, and readable font floors before layout planning. When restoring a longer `source_text` in place of a shortened `display_text`, the fit check is evaluated per item, then a further group-aware guard applies: if a sibling item sharing the same `container_id` is also a restoration candidate, the check uses that item's own authored bbox (not the whole shared container box) and persists whatever font size the check used, so a size that only "fits" against the wider shared box at the original font can't slip through and collide with a sibling once actually rendered at its real, narrower width. This closes the two page014 `top_actor_card` collisions found in the 2026-07-03 review. Separately, before any per-item fit check runs, sibling items in the same container that carry the *identical* `source_text` (one shared original sentence split across two authored lines, e.g. page014's `label_dual_track` "公益 + 市场化" / "双轨模式") are unconditionally excluded from restoration -- each copy would independently pass its own fit check, so a geometry check cannot catch this; restoring both would duplicate one sentence into two boxes rather than recover truncated meaning, so every item in such a group keeps its originally authored, distinct `display_text`. |
| Layout plan | Mandatory before rendering text: map container roles + text roles to alignment, vertical anchor, safe area, font bounds, and simplification policy. Container-role branches that stack several sibling text items vertically inside one container (`profit_card` body lines, `top_actor_card` title+summary lines) go through a shared `_stack_text_group_in_region` helper: it measures each entry's real wrapped height with the same estimator Layout QA uses (not a fixed assumed line height), shrinks the whole group's font uniformly if needed to fit, and places entries as sequential, non-overlapping slots -- each slot is also written back as that item's own `container_safe_bbox`, so later stages (e.g. the safe-area height expansion in `build_overlay_boxes`) are bounded by the item's real slot instead of the whole shared container box. This replaced two independent single-line-per-item assumptions that had let a restored (longer) sentence expand into a sibling's slot (2026-07-03 review, page014 `profit_card` and `top_actor_card`). Width/wrap estimation: `_estimated_text_width` measures against the repo-bundled Microsoft YaHei font file (`slide-image-rebuild/templates/fonts/`, user-supplied, PIL `getlength` at a fixed reference size scaled linearly) whenever that file is present, and falls back to the previous fixed per-character-ratio heuristic (roughly one full-width unit per CJK character) only when no bundled font is available. Verified against the real bundled font: CJK glyph advance measures ~1.0x font size and ASCII ~0.605x, both wider than the old heuristic's 0.95x/0.52x, so wrap/line-count estimates are now measurably closer to real glyph metrics. `text_boxes_overlap` in Layout QA remains the backstop for whatever this estimate does not fully cover. |
| Layout QA | Machine-readable geometry and readability check after text boxes are built: safe-bbox containment, reserved-zone avoidance, group alignment, index marker centering, font floors, text capacity, orphan-line detection, fallback-container usage, and pairwise text-box overlap (`text_boxes_overlap`, any two distinct non-empty boxes, not limited to shared-container siblings). Findings carry a severity: `error` for hard defects (font below the role's legibility floor, large safe-area/vertical overflow, an `isolated_text_region_used_for_body_role` hit, or a `text_boxes_overlap` hit), `warning` for everything else, including `isolated_text_region_used_for_non_body_role`. `error_count > 0` sets `P01_layout_qa.json`'s `valid` to `false` and makes the CLI exit `3`, so a caller can gate on it without parsing JSON. Note: `text_boxes_overlap` catches two boxes colliding in space; it does not catch two adjacent, non-overlapping boxes rendering duplicate/near-duplicate content (a content-level defect, not a geometry one) — that class still needs human/AI review. |
| Rendered QA | Use Codex right-side / built-in image preview and PDF-rendered PNGs as the visual QA basis for readability, safe-area fit, overflow, and editability. The PDF preview is rendered by LibreOffice (`soffice`), not PowerPoint/WPS; `build_pdf_preview` records `render_engine`, `font_family_requested`, and `font_available` (best-effort, via `fc-list`; `None` when undeterminable, `true` once a matching font file exists under `slide-image-rebuild/templates/fonts/`), and warns when the requested font is confirmed missing. Treat this PDF as a repeatable regression aid, not proof of real Office rendering — cross-check in PowerPoint/WPS before sign-off. Confirmed 2026-07-03: this LibreOffice conversion path can render a small number of CJK characters as a *different, valid* character rather than tofu or a missing-glyph box (reproduced on a real 52-textbox page014 export, font-independent -- identical corruption with Microsoft YaHei and with Noto Sans CJK SC, so it is a LibreOffice PDF-export defect, not a font or estimation-code issue; the underlying PPTX XML carries the correct text in both cases). This is more dangerous than tofu because a wrong-but-plausible character is easy to miss during a quick visual scan of the PDF preview. The script now writes `P01_text_content_qa.json`, which compares the PPTX's extracted editable text against the mapping text without OCR; use that artifact before trusting any PDF glyph. Similarity scoring is optional diagnostics only, not an acceptance target. |
| Local crop QA | When a specific region is questioned, crop that region from the Codex-visible preview or PDF-rendered PNG and inspect the crop. OfficeCLI PPT screenshots are smoke tests only and must not overrule the visible preview. |
| Speaker notes | Generated from semantic plan; fallback notes are scaffolded when no semantic plan is supplied |
| Canvas | Normalized to `1280x720` |

This is a fidelity-first branch for visual stability. It intentionally does not
attempt object-level reconstruction of the background.

### Container role vocabularies

The script carries two independent container-role vocabularies. They are not
interchangeable and there is no code path that translates one into the other;
this is a known gap, not an implementation choice to build on.

| Path | Where | Roles | When it runs |
|---|---|---|---|
| Explicit semantic containers | `build_layout_plan` / `_container_layout_context` | `center_coordination_node`, `left_stage_label`, `top_actor_card`, `middle_service_panel`, `profit_card` | Semantic plan declares `containers[]` and links items via `container_id`. This is the preferred, formally-specified path. |
| Auto-inferred fallback | `infer_semantic_containers_from_full_style` | `stage_card`, `process_chain_card`, `product_panel`, `service_card`, `trust_card`, `side_actor_panel`, `chain_terminal_note`, `isolated_text_region` | Semantic plan has roles but no `containers[]`. Row/column eligibility gates, plus the per-family container/text-safe row-anchor coordinates (e.g. `stage_card_container_top`, `product_panel_text_top`), are reverse-engineered from one reference slide (project page012) and live in `CONTAINER_INFERENCE_DEFAULT_PROFILE`; pass a `profile` dict to `infer_semantic_containers_from_full_style()` to override any subset of them for a different slide layout instead of editing the defaults. Local padding and sizing-ratio constants inside each branch remain inline and are not profile-overridable. `P01_safe_area_inference.json` records `profile_source: page012_default_unverified` for the default gates and `explicit_override` when a project profile is supplied. This path is diagnostic/scaffold only: `P01_production_readiness.json` rejects it for production until explicit semantic containers are authored. `isolated_text_region` is the catch-all when nothing else claims an item — a text item with a body-like role (`BODY_TEXT_ROLES`) landing here is a hard QA error (`isolated_text_region_used_for_body_role`), while non-body roles landing here still produce `isolated_text_region_used_for_non_body_role` warning for review. Each `inferred_isolated_text_safe_bbox` action also carries a `near_miss` field: for roles that belong to a known family (`stage_label`/`stage_body`, `chain_label`, `chain_body`, `service_item`, `actor_summary`), it names the single eligibility gate the item came closest to passing and the miss distance, so a wrong threshold shows up as an actionable delta instead of a silent catch-all; it is `null` for roles with no known family gate or when isolation had some other cause (e.g. a passed-gate item that simply found no sibling to pair with). `summary.isolated_near_miss_count` gives a quick per-run count. |

Prefer the explicit-containers path whenever the semantic plan can declare
`containers[]`; only rely on the auto-inferred fallback when container geometry
truly cannot be authored up front.

## Input Requirements

| Input | Required | Notes |
|---|---:|---|
| Full image | Yes | Contains text and all visual elements |
| No-text background image | Yes | Contains all non-text visual elements |
| OCR / vision text layout JSON | Recommended | Coordinate hints: `{"image_size": {"width": W, "height": H}, "items": [{"text": "...", "bbox": [x1,y1,x2,y2]}]}` |
| Semantic plan JSON | Required for production | Corrected meaning, AI-designed display wording, roles, grouping, notes, full-image text style, and container-to-background geometry. Production acceptance requires `containers[]` + `items[].container_id`; this is the final geometry truth. Containers may declare `text_safe_bbox` for the usable text area inside irregular shapes such as rings. |

If no text layout JSON is supplied, the command still scaffolds a project and
exports the background-only PPTX, but it warns that no editable text boxes were
created. Use an external OCR/vision step first for production work.

If no semantic plan is supplied at all (only `--text-layout`), the command still
exports a PPTX for inspection via the auto-inferred fallback path, but
`P01_production_readiness.json` is invalid and the CLI returns `3`. Treat that
output as diagnostic only. If a semantic plan *is* supplied but its items lack
`container_id`s that resolve against a declared `containers[]` entry,
`validate_semantic_plan`'s preflight gate now aborts the run before any
export (`semantic_plan_preflight_valid: false`, no PPTX, no `P01_layout_qa.json`)
rather than exporting a diagnostic-only PPTX -- confirmed 2026-07-04 while
building the page012 real-fixture regression test
(`tests/test_dual_image_rebuild_pptx.py::test_page012_real_fixture_auto_inferred_fallback_has_zero_layout_qa_errors`),
which has to call the pipeline functions directly instead of the CLI for this
reason. This is a known drift from the paragraph above, not an intentional
design choice; if you need the fallback path's diagnostic output for a
semantic plan that has roles but no containers yet, omit `--semantic-plan` and
pass the same items via `--text-layout` instead.

## Command

```bash
scripts/repo_python.sh scripts/dual_image_rebuild_pptx.py \
  --full <full_text_image.png> \
  --background <no_text_background.png> \
  --text-layout <full_image_text_layout.json> \
  --semantic-plan <semantic_plan.json> \
  --name <project_name>
```

Debug without visual alignment:

```bash
scripts/repo_python.sh scripts/dual_image_rebuild_pptx.py \
  --full <full_text_image.png> \
  --background <no_text_background.png> \
  --text-layout <full_image_text_layout.json> \
  --name <project_name> \
  --no-align
```

## Processing Steps

1. Create a normal project shell under `projects/`.
2. Copy both source images into `sources/`.
3. Normalize both images to `1280x720`.
4. Run original architecture intake on the full image:
   - `slide_image_rebuild_manifest.json`
   - `layout_reference.json`
   - `content_mapping.json`
   - `text_region_map.json`
   - `design_spec.md`
   - `svg_build_plan.json` / `svg_build_plan.md`
5. Normalize OCR / vision text boxes to the same canvas.
6. Load semantic plan when supplied; semantic text, container roles, and notes
   override raw OCR.
   - `source_text` / `source_meaning` preserve the original semantics.
   - `display_text` is the final AI-designed visible text. Default to clear,
     complete expression. Do not turn full sentences into short phrases merely
     because the workflow is making a presentation.
   - When the full expression does not fit after using the semantic safe area,
     AI may revise `display_text`, expand or move the text safe area, split the
     message, or move detail to notes. Record this as a semantic revision, not
     as a mechanical script rewrite.
   - Learn the full image's text-layer style at the same time: title/body
     hierarchy, font scale, color/weight emphasis, alignment, line rhythm, and
     grouping. Use this to preserve the original slide's typography feel while
     avoiding raw OCR bbox or full-image hard line breaks as final text
     geometry.
7. Build `P01_text_style_profile.json` from the full image / semantic text
   layer. Use it as style evidence for layout planning, not as a geometry lock.
8. Infer semantic safe areas from full-image grouping when a semantic plan has
   roles but no `containers[]`. This is a fallback: it may expand a text box to
   the card/panel's usable text area, but formal quality still prefers explicit
   semantic containers.
9. Apply the role-scoped typesetting policy before layout planning:
   - Body-like roles (`actor_summary`, `stage_body`, `chain_body`,
     `product_body`, `service_item`, `trust_body`, etc.) default to wrapping.
   - Full-image hard line breaks are downgraded to layout artifacts. First use
     the semantic safe area; restore complete `source_text` when it fits; only
     preserve line breaks when the semantic plan explicitly locks them with a
     field such as `preserve_linebreaks` or `lock_linebreaks`.
   - In narrow stage-card bodies, semantic punctuation remains normal text by
     default. Do not insert hard line breaks around short enumerations such as
     `许可、转让`; rely on PowerPoint wrapping inside the semantic safe area
     unless the semantic plan explicitly locks a line break.
   - Explanatory body roles use readable font floors instead of shrinking below
     legibility.
   - `display_text` is AI-authored and is not mechanically shortened, split by
     character count, or rewritten by the script.
   - If the visible text does not fit the safe area, `P01_layout_qa.json`
     reports `needs_semantic_revision`; AI must revise `display_text`, enlarge
     the semantic safe area, or move detail to notes.
   - The script writes defaulting actions to `P01_typesetting_report.json`.
10. If the semantic plan declares `containers[]` and text items linked by
   `container_id`, use container coordinates on the no-text background as the
   final geometry. Do not estimate or apply full-image/background alignment.
11. Build `P01_layout_plan.json` before rendering text. This is a planning stage,
   not a repair loop:
   - Container role decides the layout family and usable text safe area.
     Example: `center_coordination_node` uses stacked center text inside the
     ring's `text_safe_bbox`; if absent, it infers an inner ring bbox.
     `left_stage_label` uses the whole badge as the safe area; `top_actor_card`
     infers a left icon reserved zone and places title/summaries as a text
     group; `middle_service_panel` infers left/right icon or ring reserved
     zones; `profit_card` is partitioned into index marker, background-icon,
     title, and body regions.
   - Text role decides local treatment. Example: `center_label` is horizontal
     center + vertical middle; single-line `stage_label` fills its badge
     container and is vertically centered; multiple `stage_label` lines are
     stacked and centered as a group; `index` is centered; body/list labels use
     the container's declared alignment.
   - Text groups are planned as groups before individual boxes are rendered.
     `group_id` records the logical group, and `group_align` records whether
     the group should share a left edge or a center line.
   - Card-like containers must reserve top/bottom padding before placing text.
     The last line should not share the same y coordinate as the container
     bottom; if the group is too tall, shrink font or simplify `display_text`.
   - Service-panel containers should reserve non-text icon zones before placing
     labels. When a right-side icon would collide with a service label, reflow
     the labels into a compact text grid inside the usable text area instead of
     following the original OCR column.
   - Profit-card index numbers use the colored circular marker as their
     container. Infer the marker from the profit card's top-left marker zone,
     center the number horizontally and vertically, then shrink only if the
     marker is unusually small.
   - AI display-text decisions are role-scoped and recorded in the semantic plan
     instead of inferred by the script. The default is complete, readable
     expression in the available safe area; concise wording is only a fit/readability
     response or an explicit semantic design choice.
   - The plan records `align`, `v_align`, `bbox`, `font_size`, `font_weight`,
     `lock_bbox`, `container_fit`, `fit_order`, `container_safe_bbox`,
     `reserved_zones`, `group_id`, `group_align`, `layout_rationale`, and
     `semantic_compression_level` per text item.
12. Fit text by container, not by original-image pixel matching:
   - First identify the semantic container, for example the inside of a ring.
   - If the container has `text_safe_bbox`, keep the text box inside that area.
   - If the box touches an unsafe side, nudge it inside the container, commonly
     left-shifting text away from a right-side ring stroke.
   - For wrapped body text, expand the text box downward or within the available
     safe-area height before any font-size reduction. Do not shrink text while
     legal vertical space in the owning container is unused.
   - If it still does not fit, reduce font size only to the readable floor; if
      readability would suffer, report `needs_semantic_revision` and let AI
      revise content or safe area.
13. If no semantic container geometry exists, fall back to small visual alignment
   from full image to background image.
14. Place semantic text inside its container using the layout plan.
15. Apply boundary clamps, then Office-safe text box expansion, then font-size
   fitting, then checks for text color -- this is `build_overlay_boxes(...)`'s
   actual call order (clamp, expand, fit); the expansion step re-derives its
   target height against the same safe-area bounds used for the clamp, so
   clamping first does not re-clip the box once expansion has run.
16. Write:
   - `analysis/dual_image_rebuild/P01_text_layout_1280x720.json`
   - `analysis/dual_image_rebuild/P01_semantic_plan.json` when supplied
   - `analysis/dual_image_rebuild/P01_text_style_profile.json`
   - `analysis/dual_image_rebuild/P01_safe_area_inference.json`
   - `analysis/dual_image_rebuild/P01_frameworks.json`
   - `analysis/dual_image_rebuild/P01_composition_contract.json`
   - `analysis/dual_image_rebuild/P01_typesetting_report.json`
   - `analysis/dual_image_rebuild/P01_layout_plan.json`
   - `analysis/dual_image_rebuild/P01_layout_qa.json`
   - `analysis/dual_image_rebuild/P01_text_content_qa.json`
   - `analysis/dual_image_rebuild/P01_production_readiness.json`
   - `analysis/dual_image_rebuild/P01_text_mapping.json`
   - `notes/01_dual_image_rebuild.md`
   - `svg_output/01_dual_image_rebuild.svg`
   - `exports/dual_image_rebuild_*.pptx`
   - `qa_pdf/slide.pdf` and `qa_pdf/page-1.png` when PDF preview tools are available
17. Build a rendered QA view:
   - Use Codex right-side / built-in preview as the primary human visual check
     for readability and local crowding.
   - Convert the PPTX to PDF when `soffice` is available, then render page 1
     with `pdftoppm`. The generated artifacts live under `qa_pdf/slide.pdf`
     and `qa_pdf/page-1.png`.
   - Treat OfficeCLI PPT screenshots as open/export smoke tests only. They can
     miss wrapping, spacing, and clipping problems visible in Codex preview,
     PowerPoint, WPS, or PDF renders.
   - Do not use similarity score as a required target. When the user points to
     a specific region, crop that region from the Codex-visible preview or
     PDF-rendered PNG first; full-page thumbnails can hide local text issues.
18. Optional diagnostic only: when the user asks for visual similarity review or
   you need a crop sheet to locate drift, run:
   ```bash
   scripts/repo_python.sh scripts/dual_image_similarity_report.py \
     --reference <full_text_image.png> \
     --render <project>/qa_render/page-1.png \
     --output <project>/qa_render/visual_similarity_report.json \
     --crops-output <project>/qa_render/comparison_crops.png
   ```
   Treat `comparison_crops.png` as a debugging aid. Low similarity alone is not
   failure when the text is readable, inside its semantic safe area, and
   editable.

## QA

Open or render the exported PPTX and inspect:

| Check | Expected |
|---|---|
| Background | The no-text image fills the full slide |
| Text editability | Text can be selected and edited in PowerPoint/WPS |
| Semantic-first layout | Identify text, semantic role, and owning container first; compute the container safe area; place text inside that safe area before any visual polish |
| OCR role | OCR boxes are locator evidence for finding text/container membership only. They must not become final text box geometry when a larger legal container safe area exists |
| Alignment | Text sits inside the intended containers |
| Contrast | Text remains readable on the sampled background |
| Notes | PPTX contains speaker notes derived from semantic understanding |
| Architecture artifacts | `layout_reference.json` and `svg_build_plan.md` exist for review |
| Text style profile | `P01_text_style_profile.json` captures full-image typography/grouping style without treating OCR bbox as final geometry |
| Safe-area inference | `P01_safe_area_inference.json` records fallback semantic safe areas inferred from full-image grouping when explicit containers are absent, plus `profile_source` (`page012_default_unverified` or `explicit_override`) and any `profile_overrides` passed for a non-default slide layout (see "Container role vocabularies") |
| Visual frameworks | `P01_frameworks.json` records parent composition frames inferred from semantic containers, such as lifecycle row, processing chain, role swimlane, product band, service row, and trust column. It also records `relation_edges` so directional arrows and flow relations survive handoff. |
| Composition contract | `P01_composition_contract.json` is the main-flow handoff contract: it carries framework coverage, relation-edge coverage, layout zones, directional arrows, topology constraints, reading order, and text-safe policy so a later native rebuild can preserve the full-image composition instead of only local cards. |
| Typesetting report | `P01_typesetting_report.json` records wrapping, alignment, font-floor, and semantic-text preservation actions |
| Layout plan | `P01_layout_plan.json` exists and explains alignment / vertical anchor / fit order before rendering |
| Layout QA | `P01_layout_qa.json` reports safe-bbox, reserved-zone, group-alignment, index-marker, font-floor, text-capacity, orphan-line, and pairwise text-box-overlap checks, each tagged `error` or `warning`; `error_count` must be `0` (CLI exit `3` otherwise) before treating a page as accepted |
| Text content QA | `P01_text_content_qa.json` compares the exported PPTX's editable text with `P01_text_mapping.json` box text in order, without OCR or PDF rendering; `valid: false` means the PPTX text layer no longer matches the mapping truth |
| Production readiness | `P01_production_readiness.json` must be `valid: true`: explicit semantic containers exist, page012 default profile is not used as acceptance basis, layout QA is valid, and PPTX text matches mapping |
| Rendered QA | Codex right-side / built-in preview and, when available, `qa_pdf/page-1.png` are visually checked for readability, safe-area containment, overflow, and editable-text placement. Remember `qa_pdf/page-1.png` is a LibreOffice render (`pdf_preview.render_engine`); check `pdf_preview.font_available` was not `false` before trusting its line wrapping, and still cross-check in PowerPoint/WPS for anything user-facing |
| Local crop QA | User-raised or suspicious regions are cropped from the Codex-visible preview or PDF-rendered PNG and checked at local scale before claiming the issue is fixed |
| OfficeCLI role | OfficeCLI PPT screenshots are useful smoke tests for opening/exporting files, but they are not the visual pass/fail authority for this workflow |
| Optional similarity diagnostics | `qa_render/visual_similarity_report.json` and `qa_render/comparison_crops.png` may exist when explicitly requested or useful for debugging; they are not required for acceptance |
| Semantic fidelity | Visible `display_text` may be concise, but must be traceable to `source_text` / notes |
| Display policy | `P01_text_mapping.json` records `text_display_policy: ai_designed_display_text_from_semantics` |
| Container fit | `P01_text_mapping.json` records `container_fit_policy: container_first_safe_bbox_then_nudge_shrink_simplify`; wrapped body boxes use available safe-area height before shrinking |
| Overflow handling | If text still cannot fit the safe area after font-size fitting, report semantic revision so AI can simplify wording before final polish |

`analysis/dual_image_rebuild/P01_text_mapping.json` records the alignment
transform and final text boxes for manual review or future repair.

For a new visual family, validate one real page end-to-end with explicit
`containers[]` before treating the route as reusable for that family. The target
is not visual similarity; it is `P01_layout_qa.json error_count == 0`,
`P01_text_content_qa.json valid == true`, `P01_production_readiness.json valid
== true`, and human visual review confirming readable text inside each container.

## Boundary

Use default `strict-path.md` instead when the user needs editable background
objects, editable icons, editable cards, connectors, or chart shapes. This
branch keeps architecture and semantic analysis, maps semantic containers to the
background, but final rendering is only background snapshot + editable semantic
text.

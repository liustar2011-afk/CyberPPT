---
description: Strict slide-image-rebuild path — reconstruction policy, phase steps, and artifact commands. QA/export via run_slide_image_rebuild_strict.py only.
---

# Strict Path — Slide Image Rebuild

> **Strict delivery only** (`vector-hifi` + 复刻流程2). Skips Strategist; does **not** skip strict runner gates.
> Index + Agent SOP: [`../SKILL.md`](../SKILL.md). Required reads: [`../references/required-reads.md`](../references/required-reads.md).

## Core Pipeline

`Slide Image(s) -> Project -> Layout Extraction -> Content Decision -> Editable SVG Rebuild -> Speaker Notes -> Strict QA -> Export PPTX`

---

## Reconstruction Policy

> **Validator pass never waives an object-source violation.** `strict_run_summary.json` `valid: true` is a structure gate, not a content gate — it proves SVG/PPTX correctness, not that an icon, crop, or shape is the right *kind* of object. A required icon downgraded to a crop, a card/connector approximated with a decorative crop, or a business diagram replaced by a screenshot stays a violation of this policy even when every strict-runner check is green. Catch these during Phase B authoring against the tables below — do not rely on QA to surface them.

### Default boundary (`vector-hifi`)

| Slide element | Default treatment |
|---|---|
| Title, subtitle, body text, page number, footer text | Editable PPT text |
| Cards, callout boxes, dividers, pills, simple shapes | Editable DrawingML/SVG primitives |
| Simple functional icons | Editable semantic vectors |
| Page numbers, decorative badges, corner labels | Editable text/shapes in owning zone; not in `icon_reconstruction.icons[]` unless semantic |
| Complex decorative background, photo scenery, dense infrastructure, texture, illustration | Cropped image only when decorative, no business structure |
| Full-slide reference image | **Forbidden** as final slide body |

Only vector-rebuild complex background when the user explicitly requires editable background detail.

### Crop boundary

**Allowed:** footer decorative line art; clean decorative background (text underlays removed); texture with no business meaning; tight complex icon inside icon slot.

**Forbidden:** card body/border; process arrows/connectors; center node; text-bearing regions; main business diagram; card border + connector bundles.

Mandatory: except pure decorative background, footer line art, and tight small-icon crops, **do not** use crops for main structure.

### Icon and asset fidelity rule

Use repository SVG icons first for functional icons so the page remains editable
and stylistically consistent. Tight icon crops are an explicit opt-in when the
user prioritizes reference-icon visual fidelity over icon editability; they are
still object-level reconstruction, not a shortcut to cropping the slide:

| Object | Treatment |
|---|---|
| Functional icons with distinctive style | Repository SVG icon from the shared icon library; keep the surrounding label as editable text |
| Small complex pictograms / stacked visual marks | Repository SVG icon first; tight crop only with explicit user opt-in and source bbox overrides |
| Text next to an icon | Editable text; never included in the icon crop |
| Cards, panels, row bands, border strokes | Editable SVG/PPT shapes |
| Relationship arrows and dependency connectors | Editable vector arrows/connectors; never removed to satisfy icon or crop gates |

When tight icon crops are explicitly chosen, every icon crop must be local to the icon only and declared on the SVG `<image>`
with `data-crop-role="complex_small_icon"` or `small_complex_icon`,
`data-crop-id`, and `data-crop-purpose="tight_icon_slot_crop"`. Record the same
asset in `image_asset_manifest.json` with `contains_text: false`.

If a generated icon crop visually includes adjacent text, border, or another
object, **do not accept it**. Add an explicit source crop override and regenerate
the crop. A clean crop is required even when `strict_run_summary.json` is green.

### Relationship and arrow preservation

Architecture, process, dependency, and flow pages often carry the story through
arrows rather than text. Preserve those relationships as first-class objects:

| Relationship element | Requirement |
|---|---|
| Up/down dependency arrows | Filled vector arrows with `data-chain-connector` or equivalent semantic marker |
| Dashed callbacks to upstream nodes | Visible dashed connector plus arrowhead; keep alignment to the target card |
| Section-to-section wedges / funnels | Editable vector wedge or block arrow; keep it behind text/icons |
| Ambient decorative rays | Decorative only; do not mark as `data-chain-connector` |

**Arrow library first**: before drawing or approximating any relationship arrow,
connector, route, dependency line, branch/merge, cycle, or lift arrow, first
search the shared ppt-master arrow library resolved through
`resource_bindings.json`: `skills/ppt-master/templates/arrows/connector_index.json`
for relationship connectors, then `skills/ppt-master/templates/arrows/arrows_index.json`
for the full structural arrow set. Adapt a matching indexed SVG template to the
reference geometry whenever possible. Use `arrow_geometry.py` or hand-authored
custom paths only when no indexed template matches the semantic role; record the
reason in `svg_build_plan` / Phase B notes instead of silently defaulting to
custom drawing.

Do not globally rewrite filled paths/polygons into outline-only geometry merely
to pass a validator. If layer-order warnings appear, fix the draw order or
metadata while preserving the visible relationship arrow. Losing an arrow,
wedge, callback line, or dependency indicator is a reconstruction failure even
when export succeeds.

### Foundation / base-band layout rule

For bottom foundation bands such as "1 base / core capability" layouts, use a
stable two-tier composition:

| Area | Rule |
|---|---|
| Left visual asset | Reserve a fixed icon column; crop the visual asset tightly and keep it separate from text |
| Title + explanatory sentence | Place in a dedicated text column; do not let the sentence overlap or visually attach to the asset |
| Capability chips | Place in a separate bottom row with consistent widths, icon/text centerline, and even gaps |
| Dependency arrows above the band | Align to the support-layer targets; keep them visually connected to the foundation band |

The foundation asset, title, description, and chips must not collide or compete
for the same horizontal lane. If there is not enough room, shrink the visual
asset or title size before moving text across the icon.

### Decorative crop checklist

| Step | Action |
|---|---|
| 1 | Crop to `<project_path>/images/crop_<page_id>_<role>.png` |
| 2 | SVG `href="../images/crop_<page_id>_<role>.png"` (+ `xlink:href` if preview needs it) |
| 3 | Local to visual band only — never full-slide or card/arrow surrogate |
| 4–6 | Verified by Phase C `run_slide_image_rebuild_strict.py` (do not call validators separately) |

If preview missing: check relative path from `svg_output/`, PNG/RGBA format, re-run strict runner after path fix — not ad-hoc file copy.

### Text-bearing image policy

| Rule | Requirement |
|---|---|
| Reference use | Text-bearing image as layout reference only, never final full-slide body |
| Text mapping | All visible text regions in `text_region_map.json` |
| Editable replacement | Default `final_treatment: editable_text` |
| Crop declaration | Every `<image>` in `image_crops_manifest.json` with `contains_text`, `text_removed`, `treatment`, `reason` |
| Gate | `verify_text_bearing_images` via strict runner — release blocker |

`image_asset_manifest.json` / `harvested_asset_plan` may provide local crops for
declared decorative/photo/logo/complex-small-icon assets. They are an asset
source, not permission to replace text, cards, connectors, or main business
structure with pictures.

Minimum `text_region_map.json`:

```json
{
  "workflow": "slide-image-rebuild",
  "version": "1.0",
  "pages": [
    {
      "page_id": "01",
      "regions": [
        {
          "id": "title",
          "bbox": [72, 44, 680, 96],
          "draft_text": "Reference text draft",
          "role": "title",
          "final_treatment": "editable_text",
          "background_action": "remove_text_underlay",
          "reason": ""
        }
      ]
    }
  ]
}
```

Empty `regions` when no visible text (proves checked, not skipped).

### Reference measurement

1. Detect geometry from reference image
2. Record in `layout_reference.json` (`bbox_px`, zones, anchors, `structure_contract`)
3. Build SVG from coordinates — no crop substitute for hard geometry
4–6. Phase C strict runner: preview PNG + similarity/anchor drift reported as **advisory warnings** (non-blocking); repair only for true correctness failures via `strict_run_report.json`

### Rebuild modes

| Mode | Use |
|---|---|
| `vector-hifi` | **Default** — formal editable rebuild |
| `text-editable-snapshot` | User accepts snapshot underlay (not formal deliverable) |
| `full-editable` | Editability over visual exactness |
| `hifi` / `editable` / `wps-hifi` | Legacy export aliases — see manifest `pptx_export_mode` |

`visual_locked` is **incompatible** with default v2 — rejected at intake.

### Component quality

| Component | Rule |
|---|---|
| Central diagonal arrows | Short chunky polygon arrows into center node |
| Flow connectors | First adapt a matching template from `connector_index.json` / `arrows_index.json`; if none fits, use `<polygon>` or `<path>` + `data-chain-connector` with `arrow_geometry.py` for box-to-box |
| Decorative streams | No `data-chain-connector` on glow/grid/background art |
| Pills / callouts | Center icon, divider, labels on container centerline |
| Multi-line pills | Vertical center stack; `svg_centered_paragraph_text()` or `data-fit-center-y` |
| C×R / N×N icon grids | Optional only; create `grid_contract.json` and run `verify_grid_contract.py` when the page or asset is a true regular grid |

```python
cy = y + height / 2
label_y = cy + font_size * 0.35
text_y = cy - line_gap / 2 + font_size * 0.35 if len(lines) > 1 else label_y
```

### Paragraph editability (fidelity guard)

- Default: "图转可编辑PPT" implies safe paragraph blocks (`<text>` + `<tspan>` + `data-paragraph-line-height`)
- Keep titles, badges, table cells, connector labels separate unless one visual paragraph
- Export via strict runner with `--export-mode editable` when safe
- If similarity breaks after merge, demote blocks to line-level text and re-run strict runner
- No blind 1–2px nudging across many elements

---

## Phase A — Intake + Layout

### Step 1: Create project

**One-click scaffold (P0 entry):**

```bash
scripts/repo_python.sh scripts/image_to_editable_pptx.py \
  --image <reference.png> \
  --name <project_name> \
  --format ppt169 \
  --text-density dense_formal_cn \
  --stage scaffold
```

`--stage scaffold` initializes the project, copies the reference image, writes
`slide_image_rebuild_manifest.json` (with `text_layout_policy` when
`dense_formal_cn`), runs layout extraction (`--rebuild2`), scaffolds
`text_region_map.json` / `content_mapping.json`, and generates design/svg plan
artifacts. **It does not build `svg_output/`** — that remains Phase B
(Executor / UTF-8-safe `_gen.py`).

After `svg_output/` exists and `notes/total.md` is ready:

```bash
scripts/repo_python.sh scripts/image_to_editable_pptx.py \
  --project projects/<project_dir> \
  --stage qa
```

`--stage qa` is a thin wrapper around `run_slide_image_rebuild_strict.py --stage full --render --precise-lock --agent-summary`. On success, optional convenience copies land in `exports/final/`.

**Repair tasks + auto patch (P1):**

```bash
scripts/repo_python.sh scripts/aggregate_repair_tasks.py <project> --write-report
scripts/repo_python.sh scripts/apply_rebuild_repairs.py <project> --dry-run
scripts/repo_python.sh scripts/apply_rebuild_repairs.py <project> --write --refresh-tasks
```

Strict runner optional flag: `--auto-repair` runs apply between repair aggregation and enforce (coordinate drift ≤5px, text reflow, repeat-group y spacing only).

Post-export editability: `exports/qa/editability_score.json` (also summarized in `strict_run_summary.json` → `editability_score`).

Manual init (equivalent first step):

```bash
python3 scripts/project_manager.py init <project_name> --format ppt169
```

| Input | Path |
|---|---|
| Single reference | `<project_path>/images/reference_layout.<ext>` |
| Multi-page | `<project_path>/images/reference_pages/P01.<ext>`, … |
| Formal source | `<project_path>/sources/<name>.md` |
| Manifest | `<project_path>/slide_image_rebuild_manifest.json` |

Minimum manifest:

```json
{
  "workflow": "slide-image-rebuild",
  "format": "ppt169",
  "rebuild_mode": "vector-hifi",
  "pptx_export_mode": "hifi",
  "rebuild_quality_mode": "balanced",
  "execution_profile": "chatgpt_precise_rebuild",
  "qa": {
    "preview_render_backend": "cairo"
  },
  "pages": [
    {
      "page_id": "P01",
      "reference_image": "images/reference_pages/P01.png",
      "page_dir": "pages/P01",
      "content_source": "image_text_draft",
      "notes_style": "formal_briefing"
    }
  ]
}
```

`rebuild_mode` = reconstruction policy; `pptx_export_mode` = `svg_to_pptx.py` only.

`qa.preview_render_backend`: optional explicit `cairo` (default for slide-image-rebuild via strict runner) or `none` for non-rendered checks only.

Text granularity: `text_granularity` (`paragraph_editable` | `visual_line_lock`), `text_density` (`standard` | `dense_formal_cn`). Dense CN / visual_line_lock → export `hifi` or `wps-hifi`, not `editable`.

Optional `text_layout_policy` (validated by `verify_slide_image_rebuild_manifest.py`; defaults applied when omitted):

```json
{
  "font_family": "Microsoft YaHei",
  "min_font_size_pt": 7.5,
  "max_font_size_pt": 12.0,
  "line_height_ratio": 1.12,
  "prefer_visual_line_lock": true,
  "fit_strategy": "shrink_then_wrap_then_truncate"
}
```

Executor generators may call `layout_reference_components.fit_text_box()` for CJK labels; overflow checks write `exports/qa/text_fit_report.json` via `verify_text_fit.py --write-report`.

`execution_profile: chatgpt_precise_rebuild` → optional precise lock; requires `icon_manifest.json` when functional icons present. Default icon implementation is repository SVG (`asset_svg`), not crop or hand-vector. Draft icons:

```bash
python3 scripts/build_icon_manifest_from_layout.py <project_path> --write
```

After scaffold/manual Phase A edits and before the mapped gate, run the contract sync preflight:

```bash
scripts/repo_python.sh scripts/sync_rebuild_contract.py <project_path> --write
```

It normalizes the target canvas, removes scaffold placeholder tokens, syncs
`content_mapping.main_chain_labels`, defaults icon contracts to repo-icons, and
reports missing `data-zone-id` / `data-icon-id` markers when SVG output already
exists.

#### Step 1b: Optional preprocess

```bash
python3 scripts/preprocess_reference_image.py \
  <project_path>/images/reference_layout.png \
  --project <project_path>
```

#### Step 1c: Optional crop precrop

When `intake.precrop_candidates.enabled: true`:

```bash
python3 scripts/precrop_layout_candidates.py \
  --project <project_path> \
  --source-image images/reference_layout.normalized.png \
  --write-back
```

#### Step 1d: Debug only (not main path)

```bash
python3 scripts/verify_slide_image_rebuild_manifest.py <project_path> --stage intake
```

RMS / `layout_plan` debug tools: see `docs/zh/slide-image-rebuild-visual-qa-analysis.md` (ppt-master monorepo only; not present in this standalone checkout) — do not replace strict runner.

### Step 2: Extract layout

```bash
python3 scripts/extract_layout_reference_from_image.py \
  <reference_image> --project <project_path> --copy-image --rebuild2
```

Multi-page: per `pages/Pxx/`.

Complete `layout_reference.json` (v2, `structure_contract`, zones, `icon_reconstruction`, `geometry_locks`, …). Artifacts: `layout_measurement_report.json`, `layout_measurement_overlay.png`.

Do **not** run `validate_layout_reference` / `verify_icon_text_fit` / manifest `--stage extracted` here — they run once at **Phase A gate** (below).

### Step 2.5: Text regions

Create `text_region_map.json` — fields: `page_id`, `bbox`, `draft_text`, `role`, `final_treatment`, `background_action`, `reason`.

### Step 3: Content mapping

Write `content_mapping.json`, then generate plan artifacts:

```bash
python3 scripts/layout_reference_to_design_spec.py <page_or_project> --write-design-spec
python3 scripts/layout_reference_to_svg_plan.py <page_or_project>
```

Outputs: `layout_reference_brief.md`, `design_spec.md`, `svg_build_plan.json`, `svg_build_plan.md`.

### Step 3b: Phase A gate (layout validators — run once)

Single entry for all layout/mapped validators. On success writes `exports/qa/layout_artifacts_stamp.json`; Phase C `--stage full` skips re-running these when the fingerprint still matches.

```bash
scripts/repo_python.sh scripts/run_slide_image_rebuild_strict.py \
  --project <project_path> \
  --stage mapped \
  --skip-export
```

Do **not** also call `validate_layout_reference`, `validate_content_mapping`, or manifest `--stage extracted/mapped` by hand.

If layout/mapping files change later, re-run Step 3b before Phase B or C.

---

## Phase B — Executor (SVG)

### Step 4: Build editable SVG

Output: `<project_path>/svg_output/<stem>.svg`

| Item | Requirement |
|---|---|
| Canvas | [`canvas-formats.md`](../../skills/ppt-master/references/canvas-formats.md) |
| Structure | `layout_reference.json` + `svg_build_plan` |
| Markers | `data-zone-id`, `data-icon-id`, `data-primitive`, `data-chain-connector` |
| Layers | content → structure → semantic icons → decorative |
| Images | Declared crops only; `data-crop-id`, `data-crop-role` |
| Icons | See [`icon-contract.md`](../references/icon-contract.md); icon assets resolve through `resource_bindings.json`, preferring `../skills/ppt-master/templates/icons/` |
| Writer | UTF-8-safe only — no shell redirection into `.svg` |

Shared drawing tool:

```bash
python3 scripts/open_shared_svg_editor.py <project_path> --live
```

This launches the ppt-master browser SVG editor against the slide-image-rebuild project. Use it for manual SVG inspection and direct edits; final QA/export still runs through `run_slide_image_rebuild_strict.py`.

Default editing alignment:

- The temporary reference-image underlay is marked `data-alignment-underlay="temporary"`.
- It is a visual ruler only, not object ownership and not a final background.
- The strict runner injects it only after SVG-stage validation for a pure `--stage svg` run, so the browser SVG editor can use it for alignment.
- Manual use:

```bash
scripts/repo_python.sh scripts/alignment_underlay.py <project_path> inject --opacity 0.28
python3 scripts/open_shared_svg_editor.py <project_path> --live
```

Use `scripts/repo_python.sh scripts/alignment_underlay.py <project_path> strip` to remove it and `scripts/repo_python.sh scripts/alignment_underlay.py <project_path> check` to confirm no temporary underlay remains.

### Validator hard contracts (read before authoring)

Non-obvious literal requirements enforced by the strict runner; each one is a
blocking error when violated.

| Contract | Enforced by |
|---|---|
| `data-chain-connector` ids must literally be `<from>-><to>` for every `main_chain.connectors[]` entry | `verify_svg_rebuild_completeness` |
| Every `icon_reconstruction.icons[]` entry needs a `text_anchor` block | `validate_layout_reference --rebuild2` |
| `layout_grammar.page_type_hint` is a closed enum: `agenda` `comparison` `cover` `custom` `dashboard` `matrix` `process` `quote` `summary` `timeline` | `validate_layout_reference --rebuild2` |
| `main_chain.nodes` count must equal column-zone count; a `relationship_style` containing `arrow`/`directed`/`flow`/`chain`/`connector` forces `connectors >= nodes - 1` (hub pages: pick a style word outside that list) | `validate_layout_reference --rebuild2` |
| Polygon connectors: max bbox dimension 80px once both sides are >=14px — keep block arrows short and chunky | `verify_svg_spacing` |
| Anchor drift detector searches expected_y +/-14px for the strongest horizontal edge; keep other strong full-width edges (e.g. a banner's bottom border) out of that window | `verify_reference_similarity` (advisory) |
| Icons sitting on a colored surface (navy chevron, tinted strip) skip rendered fill/padding metrics automatically; presence, bbox and stroke checks still apply | `verify_icon_contract --render` |

After SVG: go to Phase C. **Do not** run individual QA scripts.

Repair reports (via strict runner failure):

| Report | Task types |
|---|---|
| `object_similarity_report.json` | `color_deviation`, `coordinate_drift`, `residual_object` |
| `text_wrap_similarity_report.json` | `text_reflow` |
| `geometry_locks_report.json` | `geometry_lock_violation` |
| `layout_family_contract_report.json` | `connector_geometry` |
| `icon_contract_report.json` | `icon_style_mismatch` |

---

## Phase C — Notes + Strict QA + Export

### Step 5: Speaker notes

`<project_path>/notes/total.md` — `# <svg_stem>` headings must match `svg_output/` filenames exactly.

Styles: `formal_briefing` (default), `concise_talk_track`, `word_for_word`, `short_video_voiceover`.

### Step 6: Export (strict runner only)

Before validation/export, the strict runner strips and checks any temporary
alignment underlay (`data-alignment-underlay="temporary"`). Any remaining
full-slide reference image is a blocker, not a permitted final background.

```bash
scripts/repo_python.sh scripts/run_slide_image_rebuild_strict.py \
  --project <project_path> \
  --export-mode hifi \
  --precise-lock \
  --render \
  --stage full
```

| Flag | When |
|---|---|
| `--stage pre-export` | SVG ready; notes not written |
| `--skip-export --stage svg` | SVG-only QA (layout steps skipped when stamp matches) |
| `--export-mode editable` | Paragraph blocks + user wants paragraph editability |
| `--export-mode wps-hifi` | WPS / Chinese delivery |

**Resume:** use `next_action.resume_command` from `strict_run_summary.json` — not `--stage full` after a partial pass.

**Do not** separately run `total_md_split`, `finalize_svg`, `svg_to_pptx`, or post-export `verify_*`.

The strict runner renders the exported PPTX with repository-local OfficeCLI as
part of the post-export hard gates. Successful runs write
`exports/qa/officecli_screenshot.png` and
`exports/qa/officecli_screenshot.json`; missing or empty screenshot output blocks
the final package check.

Report consumption: read `exports/qa/strict_run_summary.json` first (`--agent-summary` prints it to stdout). See [`../SKILL.md` § Agent SOP](../SKILL.md#agent-sop). Multi-chat handoff: [`conversation-split.md`](conversation-split.md).

After `valid: true`, optional: [`generate-audio.md`](../../skills/ppt-master/workflows/generate-audio.md).

---

## Checkpoint

- [ ] Layout artifacts + `svg_build_plan` complete
- [ ] `svg_output/` editable pages
- [ ] `notes/total.md`
- [ ] `run_slide_image_rebuild_strict.py --stage full --render` → `valid: true`
- [ ] `exports/qa/strict_run_report.json` + exported PPTX
- [ ] `exports/qa/officecli_screenshot.png` + `exports/qa/officecli_screenshot.json`

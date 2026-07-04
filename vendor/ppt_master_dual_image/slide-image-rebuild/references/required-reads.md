# Slide Image Rebuild — Required Reads

> Load on demand by **phase** and **manifest profile**. Do not read every file at skill start.  
> Index + Agent SOP: [`../SKILL.md`](../SKILL.md). Step commands: [`../workflows/strict-path.md`](../workflows/strict-path.md). 双图复刻 branch: [`../workflows/dual-image-rebuild-ppt.md`](../workflows/dual-image-rebuild-ppt.md).

---

## By phase

| Phase | Read now | Defer until needed |
|-------|----------|-------------------|
| **A — Layout** | [`strict-path.md`](../workflows/strict-path.md) § Phase A; run `sync_rebuild_contract.py --write`, then end with `--stage mapped --skip-export` | [`shared-standards.md`](../../skills/ppt-master/references/shared-standards.md) full text |
| **A — `structure_contract`** | `scripts/layout_reference_rebuild2_lib.py` constants/schema behavior through `extract_layout_reference_from_image.py --rebuild2` and `validate_layout_reference.py --rebuild2` | — |
| **B — SVG construction** | Project `design_spec.md`, `svg_build_plan.md` (**Executor Obligations** / **Components** sections) | Full `svg_build_plan.json` unless md is insufficient |
| **B — arrows / text / paragraph** | Relevant sections of [`shared-standards.md`](../../skills/ppt-master/references/shared-standards.md); for any arrow/connector reconstruction, read [`connector_index.json`](../../skills/ppt-master/templates/arrows/connector_index.json) first, then [`arrows_index.json`](../../skills/ppt-master/templates/arrows/arrows_index.json) if needed | Unrelated chapters |
| **B — canvas** | [`canvas-formats.md`](../../skills/ppt-master/references/canvas-formats.md) when canvas size unclear | — |
| **C — QA / export** | Run `run_slide_image_rebuild_strict.py`; read `exports/qa/strict_run_summary.json` | Full `strict_run_report.json` unless deep triage |
| **C — multi-chat** | [`conversation-split.md`](../workflows/conversation-split.md) when starting chat 2 or 3 | — |
| **Narration / video** | [`generate-audio.md`](../../skills/ppt-master/workflows/generate-audio.md) | — |

---

## By manifest profile

| Trigger | Additional read |
|---------|-----------------|
| User says "双图复刻ppt", gives full image + no-text background, or asks for background snapshot + editable text only | [`dual-image-rebuild-ppt.md`](../workflows/dual-image-rebuild-ppt.md) |
| `execution_profile: chatgpt_precise_rebuild` | [`icon-contract.md`](./icon-contract.md) |
| `icon_manifest.json` exists or icon slots in layout | [`icon-contract.md`](./icon-contract.md) |
| `grid_contract.json` or `asset_grid_contract.json` exists | [`grid-contract.md`](./grid-contract.md) |
| Need to cut a C×R / N×N icon contact sheet | [`grid-contract.md`](./grid-contract.md), then use `scripts/grid_chroma_cut.py` |
| `image_asset_manifest.json` exists or `svg_build_plan.md` has `Harvested Image Assets` | [`asset-harvesting.md`](./asset-harvesting.md) |
| `detected_layout_family.archetype` exists | [`layout-archetypes.md`](./layout-archetypes.md) |
| `intake.precrop_candidates.enabled: true` | [`strict-path.md` § Step 1c](../workflows/strict-path.md#step-1c-optional-crop-precrop) |
| User switches to full deck pipeline | [`ppt-master/SKILL.md`](../../skills/ppt-master/SKILL.md) |

---

## Project artifacts (read during work, not upfront)

| Artifact | When |
|----------|------|
| `layout_reference.json` | Phase A completion + Phase B coordinate work |
| `layout_measurement_overlay.png` | Phase B tweaks (prefer over re-attaching reference image) |
| `layout_reference_brief.md` | Before Phase B SVG |
| `text_region_map.json` | Phase B text placement |
| `content_mapping.json` | Phase B visible copy |
| `svg_build_plan.md` | Phase B primary execution brief |
| `svg_build_plan.json` | Only when md insufficient or plan validator errors |

---

## Do not load

| File | Unless |
|------|--------|
| Full `skills/ppt-master/SKILL.md` (ppt-master monorepo only) | User explicitly wants full Strategist deck generation |
| All validator script source | Debugging tooling only |
| `docs/zh/slide-image-rebuild-strict-token-optimization.md` (ppt-master monorepo only) | Planning / workflow changes — not required per task |

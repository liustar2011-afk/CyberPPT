---
name: slide-image-rebuild
description: >
  Convert slide images, ChatGPT-generated presentation pages, screenshots, or
  visual reference pages into editable PPTX with speaker notes. Use when the
  user wants an image-to-PPT workflow, "按图重建ppt技能", "按图重建PPT",
  "按图复刻PPT", "图转PPT", "ChatGPT图转PPT", "图片转可编辑PPT",
  "截图复刻", "复刻成PPT并生成解说词", or a lightweight rebuild that does not
  need the full ppt-master Strategist pipeline.
---

# Slide Image Rebuild Skill

> **Index + Agent SOP.** Default delivery is **strict** (`vector-hifi` + 复刻流程2 + strict runner). Similarity/pixel-alignment gates are **advisory**, not blocking — see Strict Delivery table.  
> **Steps & construction rules:** [`workflows/strict-path.md`](workflows/strict-path.md)  
> **What to read when:** [`references/required-reads.md`](references/required-reads.md)  
> **Shared ppt-master resources:** [`resource_bindings.json`](resource_bindings.json) resolves the host repo's SVG/template libraries, icon library, shared SVG quality checker, browser SVG editor, references, and OfficeCLI defaults.  
> **Token optimization plan:** `docs/zh/slide-image-rebuild-strict-token-optimization.md` (only present when this skill is embedded in the ppt-master monorepo; not included in this standalone checkout)  
> **Multi-chat split:** [`workflows/conversation-split.md`](workflows/conversation-split.md)
> **双图复刻ppt:** [`workflows/dual-image-rebuild-ppt.md`](workflows/dual-image-rebuild-ppt.md) — full text-bearing image + no-text background image → background snapshot + editable text PPTX. This is an independent branch and does not change the strict default route.

## Strict Delivery (default)

| Item | Value |
|---|---|
| Rebuild | `vector-hifi`, `extract_layout_reference_from_image.py --rebuild2` |
| QA / export | **`run_slide_image_rebuild_strict.py` only** — preview/similarity render default **cairo** (fast; set `qa.preview_render_backend` in the manifest to override); post-export final check also renders the exported PPTX through OfficeCLI screenshot |
| Similarity | **advisory (non-blocking)**: reference/object/text-wrap/geometry-lock and icon position/size drift are reported as warnings — they never block export or trigger a repair loop. Only true correctness violations (text overflow, non-editable body, CJK mojibake, element collision, missing/broken icon, connector/layout-family contract) block. |
| Done when | `--stage full --render` → `exports/qa/strict_run_summary.json` `valid: true`, with `exports/qa/officecli_screenshot.png` present |

`valid: true` proves SVG/PPTX structure, not object-source correctness — see [`strict-path.md` § Reconstruction Policy](workflows/strict-path.md#reconstruction-policy) before treating a green run as license to keep a downgraded icon/crop/shape.

## Three Phases

```text
Phase A  Intake + Layout   → manifest, layout_reference, text_region_map, content_mapping, svg_build_plan
Phase B  Executor (SVG)    → svg_output (UTF-8-safe writer; reference image once + measurement overlay)
Phase C  Notes + Strict QA → notes/total.md → strict runner (sole QA/export entry)
```

| Phase | Doc section | Do not run |
|---|---|---|
| A | [`strict-path.md` § Phase A](workflows/strict-path.md#phase-a--intake--layout) | similarity, export; hand-run layout `verify_*` (use Step 3b mapped gate once) |
| B | [`strict-path.md` § Phase B](workflows/strict-path.md#phase-b--executor-svg) | any validator outside strict runner |
| C | [`strict-path.md` § Phase C](workflows/strict-path.md#phase-c--notes--strict-qa--export) | `total_md_split` / `finalize_svg` / `svg_to_pptx` / `verify_*` alone |

## Agent SOP

### Vision budget

| When | Action |
|---|---|
| Phase B start | Attach reference image **once** |
| Coordinate tweaks | `layout_measurement_overlay.png` + `layout_reference.json` bbox |
| Editing alignment | Phase B can use a temporary reference-image underlay for SVG editor alignment; strict validation/export strips it before checks/PPTX generation; the underlay is never final slide body. |
| Similarity failure | `exports/preview_qa/<stem>.preview.png` + report fields |
| **Forbidden** | Re-attach reference every repair round |

### Strict runner (sole QA / export)

```bash
# SVG ready; notes not written
scripts/repo_python.sh scripts/run_slide_image_rebuild_strict.py \
  --project <project_path> --stage pre-export --render --precise-lock --export-mode hifi

# Notes ready; export PPTX (default Phase C entry; use repo_python.sh — no manual venv/playwright_env per run)
scripts/repo_python.sh scripts/run_slide_image_rebuild_strict.py \
  --project <project_path> --stage full --render --precise-lock --export-mode hifi --agent-summary
```

`--skip-export --stage svg` for SVG-only QA. Resolve `--export-mode` / `--precise-lock` from `slide_image_rebuild_manifest.json`.

**Phase A end:** `run_slide_image_rebuild_strict.py --stage mapped --skip-export` once (writes `layout_artifacts_stamp.json`).

**Phase C:** local `run_slide_image_rebuild_strict.py` only (commands above). On repair, use `resume_command` from summary — not `--stage full` if a later stage failed.

**Multi-chat:** Prefer [`workflows/conversation-split.md`](workflows/conversation-split.md) for multi-page or repair-heavy work.

### Shared resources

| Resource | Default source |
|---|---|
| Icon library | `../skills/ppt-master/templates/icons/` via `scripts/shared_ppt_resources.py` |
| SVG / chart / layout / brand libraries | `../skills/ppt-master/templates/` via `resource_bindings.json` |
| Arrow / connector libraries | `../skills/ppt-master/templates/arrows/arrows_index.json` and `../skills/ppt-master/templates/arrows/connector_index.json` via `resource_bindings.json`;复刻箭头时先选库模板，再考虑自绘 |
| Shared SVG quality checker | `../skills/ppt-master/scripts/svg_quality_checker.py` inside the strict runner |
| Browser drawing / live SVG editor | `scripts/open_shared_svg_editor.py <project> --live` → `../skills/ppt-master/scripts/svg_editor/server.py` |
| Office preview / screenshots | Repository-local `../skills/officecli/` where available; strict runner writes `exports/qa/officecli_screenshot.png` and `.json` after PPTX export |

`slide-image-rebuild` still owns image-rebuild-specific gates: layout extraction, text-bearing image policy, structure contracts, icon contracts, similarity reports, repair aggregation, and strict export orchestration.

### Report consumption

1. Read `exports/qa/strict_run_summary.json` (or run strict runner with `--agent-summary` for stdout). `valid: true` → done.
2. `valid: false` → `blocking_errors[]` → `next_action.reread[]` → `next_action.resume_command`.
3. Full `strict_run_report.json` only for deep triage (contains all `steps[]`).
4. Same `failed_step_id` ≥3 failures → stop; surface errors for human review.

### Prohibited

Do **not** individually run validators inside strict runner (similarity, contract, `aggregate_repair_tasks`, post-export `verify_editable_pptx`, …).  
**Phase A:** one `--stage mapped --skip-export` run replaces hand-running layout/mapped `verify_*`. **Phase C:** never hand-run those again; stamp + runner handle skip/resume.

## When to Use

| User intent | Action |
|---|---|
| Slide image(s) → editable PPT + notes | This skill |
| Screenshot + formal content | This skill; replace image text with formal content |
| 双图复刻ppt / 完整图 + 无字底图 / 底图不编辑只复刻文字层 | [`workflows/dual-image-rebuild-ppt.md`](workflows/dual-image-rebuild-ppt.md) |
| Full deck strategy from source docs | `skills/ppt-master/SKILL.md` (ppt-master monorepo only; not present in this standalone checkout) |
| Brand / template / image acquisition planning | `skills/ppt-master/SKILL.md` (ppt-master monorepo only; not present in this standalone checkout) |

## Required Reads

See [`references/required-reads.md`](references/required-reads.md) — load by phase, not all at start.

## Execution Rules

| Rule | Requirement |
|---|---|
| Scope | Editable PPTX + speaker notes; no Strategist Eight Confirmations |
| Fidelity | Default `--rebuild2`, v2 `structure_contract`, contract markers |
| Text trust | Reference image text is draft unless user trusts it |
| Editability | No full-slide raster body |
| Arrows | For any relationship/connector/flow arrow, first select from shared `connector_index.json` / `arrows_index.json`; custom drawing is fallback only when no semantic match exists |
| SVG | UTF-8-safe writer only |
| Notes | Always `notes/total.md` |
| QA / export | **`run_slide_image_rebuild_strict.py` only** |

## Quick Start

```bash
scripts/repo_python.sh scripts/image_to_editable_pptx.py \
  --image <reference.png> --name <project_name> --format ppt169 \
  --text-density dense_formal_cn --stage scaffold
# Normalize Phase A contracts before mapped/full QA:
scripts/repo_python.sh scripts/sync_rebuild_contract.py projects/<project_dir> --write
# Phase B: build svg_output/ (UTF-8-safe writer, repo-icons first). Then:
scripts/repo_python.sh scripts/image_to_editable_pptx.py \
  --project projects/<project_dir> --stage qa
```

Manual equivalent: `project_manager.py init` + manifest — see [`workflows/strict-path.md`](workflows/strict-path.md) Phase A → B → C.

### 双图复刻ppt Quick Start

```bash
scripts/repo_python.sh scripts/dual_image_rebuild_pptx.py \
  --full <full_text_image.png> \
  --background <no_text_background.png> \
  --text-layout <full_image_text_layout.json> \
  --semantic-plan <semantic_plan_with_containers.json> \
  --name <project_name>
```

This route exports a PPTX directly with the no-text background as a full-slide
image and editable text boxes on top. It intentionally bypasses the strict
object-level SVG rebuild pipeline. Production acceptance requires explicit
`semantic_plan.containers[]`; running with only OCR/text-layout is diagnostic
and exits non-zero after writing review artifacts.

## Checkpoint

- [ ] Layout artifacts + `svg_build_plan`  
- [ ] `svg_output/` + `notes/total.md`  
- [ ] Strict runner `--stage full --render` → `valid: true`  
- [ ] OfficeCLI final screenshot → `exports/qa/officecli_screenshot.png`  
- [ ] PPTX exported  

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
# optional: TLS-impersonating fetch support for import-sources URLs
.venv/bin/pip install -r requirements-optional.txt
```

`scripts/repo_python.sh` auto-detects `.venv/bin/python` and falls back to `python3` when absent.

## Standalone Packaging

This skill is runnable standalone, but when it is embedded in the ppt-master monorepo it **prefers shared ppt-master resources** through `resource_bindings.json`.

`scripts/{project_manager,finalize_svg,svg_to_pptx,total_md_split,verify_editable_pptx,config,error_helper,project_utils,update_spec}.py` and `scripts/svg_to_pptx/` remain local copies because strict image-rebuild export has its own post-export gates. The icon library and shared SVG quality checker prefer the host `skills/ppt-master/` versions and fall back to local copies only when the host resources are unavailable.

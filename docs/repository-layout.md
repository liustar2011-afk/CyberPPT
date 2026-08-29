# CyberPPT Repository Layout

This repository is a runnable project toolchain with repository-local stage
Skills. The layout below is the placement contract for code, workflow
references, reusable assets, project workspaces, and generated artifacts.

## Top-Level Contract

| Path | Role | Rules |
|---|---|---|
| `docs/CYBERPPT_WORKFLOW.md` | Canonical workflow overview and route index | Keep the main sequence and route selection here; stage details belong in `.agents/skills/`. |
| `.agents/skills/` | Repository-local authoritative stage Skills | Keep only Skills used by the current workflow; do not add a second root-level workflow Skill. |
| `cyberppt/` | Installable Python package and CLI | Keep stable command routing, project scaffolding, and package helpers here. Do not put generated project artifacts here. |
| `scripts/` | Repo-owned workflow tools | Keep runnable helper scripts here when docs and tests call them directly. Avoid storing one-off outputs under this tree. |
| `scripts/imagegen_pipeline/` | Stage 02 ImageGen production chain | Keep artifact prompt compilation, approval, manifest, provider, style, and send-record logic here. |
| `scripts/image_to_editable_svg/` | Audited full-image reconstruction | Inventory registered layers, author fidelity-gated editable SVG, then assemble native PPTX. |
| `scripts/image_to_pptx_runtime/` | Native SVG/PPTX assembly runtime | Keep the current editable assembly implementation here; it must consume audited Stage 02 artifacts. |
| `scripts/presentation_qa/` | Presentation QA utilities | Keep rendering, layout, and text-content QA helpers here. |
| `references/` | Stage-specific workflow references | Keep required reads and QA contracts here. References should describe behavior, not store project outputs. |
| `assets/` | Reusable public assets | Keep sample palettes and reusable icon libraries here. Generated slide images do not belong here. |
| `docs/` | Repository documentation, specs, and plans | Keep repo layout docs, design specs, and implementation plans here. |
| `tests/` | Regression tests | Keep pytest/unittest tests here. Test-only helper modules may stay in `scripts/` only when existing entrypoints rely on that path. |
| `vendor/` | Local vendored upstream resources | Keep only upstream resources still consumed by the current workflow. Do not mix project outputs into vendor trees. |
| `examples/` | Minimal examples | Keep small, durable examples here. Large generated decks and runs belong in project workspaces. |
| `projects/` | Named CyberPPT project workspaces | Preferred home for user-facing projects created by `python3 -m cyberppt init`. Source files, stage work, approvals, outputs, and delivery files live under each project. |
| `assets/presentation-templates/` | Reusable native presentation templates | Store only curated templates used by the current template-page generator. |

## Project Workspace Contract

New project workspaces should be created with:

```bash
python3 -m cyberppt init projects/<project-name>
```

Each project owns its inputs, locks, staged work, run attempts, outputs, and
delivery files:

| Project Path | Role |
|---|---|
| `source/` | User-provided source materials and raw inputs. |
| `workbench/artifact-ledger.json` | Durable artifact index with dependencies, status, and resume commands. |
| `workbench/stages/01-analysis/` | Evidence tables, conflicts, SCR, storylines, page plans, density plans. |
| `workbench/stages/02-imagegen/` | Style/content locks, approved ImageGen prompts, full-image manifest, send records, reconstruction inventory, and SVG/PPTX readiness artifacts. |
| `workbench/stages/05-qa-delivery/` | Visual QA, side-by-side checks, final manifests, delivery notes. |
| `workbench/locks/` | Slide content locks, template text locks, visual locks, and related truth files. |
| `workbench/prompts/` | Plaintext prompt artifacts that require review or reuse. |
| `workbench/scripts/` | Draft and final slide scripts used as generation truth. |
| `workbench/approvals/` | User approval records for gates. |
| `workbench/runs/` | Page-specific or attempt-specific intermediate runs that may be resumed. |
| `workbench/archive/` | Superseded run artifacts retained for traceability. |
| `workbench/tmp/` | Disposable local scratch files for the current project. |
| `workbench/qa/` | QA reports that are not already stage-specific. |
| `outputs/` | Rendered pages and generated intermediate deliverables. |
| `delivery/` | User-facing final files and delivery notes. |

Stage 02 and later builds use a fresh `build_id` directory by default. Existing
PPTX, images, and QA records remain addressable; a deliberate overwrite must
move the replaced item under `backup/` and keep the previous ledger record linked
through `supersedes`. Export consumers use the run's explicit artifact path (or
`analysis/export_artifact.json`) rather than selecting a file by modification time.

## Cleanup Rules

- Remove ignored caches such as `__pycache__/` and `.pytest_cache/` whenever they
  clutter reviews.
- Do not add new generated images, decks, QA renders, or source materials at the
  repository root. Put them under a project workspace and register durable
  artifacts in `workbench/artifact-ledger.json`.
- Do not commit `image2pptx_runs/`, root `tmp/`, prompt attempts, test caches, or
  other generated run products. These paths are ignored and may be deleted at
  any time.

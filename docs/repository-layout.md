# CyberPPT Repository Layout

This repository is both a Codex skill and a runnable project toolchain. The
layout below is the placement contract for code, workflow references, reusable
assets, project workspaces, and generated artifacts.

## Top-Level Contract

| Path | Role | Rules |
|---|---|---|
| `SKILL.md` | Canonical workflow contract | Keep phase gates, reference gates, and delivery rules here. Do not replace it with CLI-only behavior. |
| `cyberppt/` | Installable Python package and CLI | Keep stable command routing, project scaffolding, and package helpers here. Do not put generated project artifacts here. |
| `scripts/` | Repo-owned workflow tools | Keep runnable helper scripts here when docs and tests call them directly. Avoid storing one-off outputs under this tree. |
| `scripts/dual_image_overlay/` | CyberPPT-owned dual-image pipeline | Keep overlay, template rebuild, scene graph, QA, and rebuild-mode logic together. |
| `scripts/dual_image_overlay/rebuild_engine/` | Internalized dual-image rebuild runtime | Treat as a vendored runtime now owned by CyberPPT. Do not split it during layout cleanup. |
| `references/` | Stage-specific workflow references | Keep required reads and QA contracts here. References should describe behavior, not store project outputs. |
| `assets/` | Reusable public assets | Keep sample palettes and reusable icon libraries here. Generated slide images do not belong here. |
| `docs/` | Repository documentation, specs, and plans | Keep repo layout docs, design specs, and implementation plans here. |
| `tests/` | Regression tests | Keep pytest/unittest tests here. Test-only helper modules may stay in `scripts/` only when existing entrypoints rely on that path. |
| `vendor/` | Local vendored upstream resources | Keep imported upstream workflow assets here to avoid hidden runtime dependencies on other repos. Do not mix project outputs into vendor trees. |
| `examples/` | Minimal examples | Keep small, durable examples here. Large generated decks and runs belong in project workspaces. |
| `projects/` | Named CyberPPT project workspaces | Preferred home for user-facing projects created by `python3 -m cyberppt init`. Source files, stage work, approvals, outputs, and delivery files live under each project. |
| `image2pptx_runs/` | Temporary or historical run workspaces | Allowed for ad hoc run captures and resume/debug sessions. New formal projects should prefer `projects/<name>/`. |
| `images/` | Legacy root scratch images | Legacy only. Do not use as a default output target for new workflows. Move new image generation under a project workspace. |

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
| `workbench/stages/02-blueprint-dual-image/` | Style lock, content locks, ImageGen prompts, full/background pair manifests. |
| `workbench/stages/03-overlay/` | Dual-image overlay artifacts, semantic plans, text mapping, fit and layout QA. |
| `workbench/stages/04-template-rebuild/` | Template assembly jobs, source capture, readiness records, normalized references. |
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

## Cleanup Rules

- Remove ignored caches such as `__pycache__/` and `.pytest_cache/` whenever they
  clutter reviews.
- Do not move existing `image2pptx_runs/` directories casually. Many run ledgers
  and QA files contain absolute paths, so migration needs a deliberate manifest
  rewrite.
- Do not move `vendor/ppt_master_slide_image_rebuild/` or
  `scripts/dual_image_overlay/rebuild_engine/` as part of routine hygiene.
- Do not add new generated images, decks, QA renders, or source materials at the
  repository root. Put them under a project workspace and register durable
  artifacts in `workbench/artifact-ledger.json`.

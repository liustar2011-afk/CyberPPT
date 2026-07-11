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
| `workbench/analysis_expression/` | Project-level five-gate contract, staged confirmation records, approval records, and status metadata. It records source analysis, reporting direction, report structure, page design, and business script without replacing their source workspaces. |
| `workbench/stages/01-analysis/` | Evidence tables, conflicts, SCR, storylines, page plans, density plans. |
| `workbench/stages/01-analysis/model-runs/` | Prompt-first Stage 1 model runs: reviewable prompts, raw responses, candidates, grounding QA, critic reports, and run manifests. Model outputs are candidates only and must not be auto-approved. |
| `workbench/stages/02-blueprint-dual-image/` | Historical path name for the current `full_image_ppt` mainline: style lock, template text lock, human-editable `imagegen_script.md`, its `imagegen_script.validation.json`, ImageGen full images, `page_image_pairs.json`, speaker notes, image-PPT assembly, and `assembly_report.json`. The MD is the prompt source; its validation report and hash are recorded in the manifest. |
| `workbench/stages/03-overlay/` | Legacy/Advanced editable rebuild artifacts only: overlay plans, semantic plans, text mapping, fit and layout QA. |
| `workbench/stages/04-template-rebuild/` | Legacy/Advanced template rebuild jobs only: source capture, readiness records, normalized references. |
| `workbench/stages/05-qa-delivery/` | Production visual report, full-image delivery manifest, strict validation report, production readiness, and delivery notes. |
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

## Analysis Expression Contract

The analysis-expression contract is project-scoped and sequential: reporting
analysis -> reporting direction -> report structure -> page design -> business
script. Staging a gate persists its Markdown source plus a pending-confirmation
record with a question, recommendation, selectable UI choices, and audit data;
staging is not approval. The next gate is unavailable until the predecessor's
recorded option is approved.

Business scripts retain non-visible evidence IDs, source locations,
completeness checks, and density units. Stage 02 then records four separate
artifacts: an approved visual-style lock, an approved clean blueprint input,
an approved generated-image review, and the assembled image-PPT/QA output.
The blueprint input must preserve source-backed visible facts but must not
contain evidence IDs, source positions, geometry, or final-composition
instructions. Navigation pages are deliberately non-argumentative and contain
no evidence bindings.

The default project production sequence is:

```bash
python3 -m cyberppt produce prepare <project> --pages <range>
python3 -m cyberppt produce assemble <project> --pages <range>
python3 -m cyberppt produce verify <project> --pages <range>
```

`produce prepare` stops for speaker-notes approval, `produce assemble` consumes only approved notes/template/full-image inputs, and `produce verify` is the only step that can promote a PPTX to `delivery/` and `deliverable_ready`.

New workspaces receive this contract during initialization. For an existing
workspace, `adopt-analysis-expression-contract` creates only contract metadata.
It does not overwrite existing business/page files or create a blueprint input.
Use `analysis-expression-status --json` after adoption to identify the next
gate, pending choices, and any missing upstream artifact.

The optional model-assisted Stage 1 path is prompt-first and gate-by-gate:

```bash
python3 -m cyberppt phase1 prepare <project> --gate source_analysis --input <source_extract.md>
python3 -m cyberppt phase1 generate <project> --gate source_analysis
python3 -m cyberppt phase1 critique <project> --gate source_analysis
python3 -m cyberppt phase1 stage <project> --gate source_analysis --recommendation <id> --options-json '<json>'
python3 -m cyberppt approve-source-analysis <project> --option-id <id>
```

The prompt Markdown is a reviewable prompt and is editable before generation.
Raw model responses, candidate Markdown, grounding reports, critic findings,
model metadata, and hashes are recorded under `model-runs/`. Model output is
never auto-approved，不得自动批准；the existing human confirmation record
remains authoritative.

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

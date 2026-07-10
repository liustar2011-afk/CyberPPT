# CyberPPT Main Workflow Production Closure Design

Date: 2026-07-10
Status: Approved for implementation planning

## Objective

Turn the current controlled, semi-automatic workflow into one production path whose final state is trustworthy. A run may report `deliverable_ready` only when approved upstream artifacts were consumed, the assembled PPTX exists, rendering succeeded, strict structural validation passed, visual comparison passed, and the artifact ledger records the complete dependency chain.

The default production mode remains `full_image_ppt`: content-region text and visuals are carried by approved full images, while titles, subtitles, page chrome, page numbers, footers, logos, and speaker notes are generated as PowerPoint/template layers. Legacy OCR, overlay, semantic-plan, and native rebuild tools remain available only as explicit advanced/debug paths.

## Chosen Approach

Add one project-scoped production command family:

```text
python3 -m cyberppt produce prepare <project> --pages <range>
python3 -m cyberppt produce assemble <project> --pages <range>
python3 -m cyberppt produce verify <project> --pages <range>
python3 -m cyberppt produce status <project> --pages <range> --json
```

`produce` is the documented main entry. Its subcommands reflect the required human stop points; a single non-interactive command must not silently cross a review gate.

Lower-level commands remain callable for diagnostics and tests, but every generation or assembly alias invoked through `python3 -m cyberppt` must receive an explicit `--project`. Path inference is removed from the safety decision. Direct execution of files under `scripts/` is an advanced/debug interface and must not write `deliverable_ready`.

## State Model

The project production state advances in this order:

```text
analysis_approved
  -> visual_style_approved
  -> blueprint_input_approved
  -> production_inputs_prepared
  -> speaker_notes_approved
  -> blueprint_images_approved
  -> image_ppt_assembled
  -> render_qa_passed
  -> strict_qa_passed
  -> deliverable_ready
```

Every transition is fail-closed. A changed or missing dependency moves the project back to the earliest stale state. Status is calculated from artifacts and hashes, not trusted from the last run's label.

## Components

### 1. Production Orchestrator

Add `cyberppt/commands/produce.py` as the only owner of production-state transitions.

- `prepare` derives the approved blueprint script and approved visual style from project records. It compiles prompts and `page_image_pairs.json`, writes `template_text_lock`, builds a speaker-notes draft, stages the notes for confirmation, and stops.
- `assemble` requires current speaker-notes approval and current generated-image approval. It invokes the image-PPT exporter with explicit project, template-text lock, style lock, page manifest, and speaker-notes manifest inputs.
- `verify` checks the assembly bundle, renders the PPTX, compares rendered body regions with approved full images, runs strict structural validation, writes QA reports, and only then records `deliverable_ready`.
- `status` recalculates every state from current files and hashes and reports the next legal command.

`final-script-pages` remains a compatibility/preparation helper. It must not report `production_ready`; production callers are directed to `produce`.

### 2. Explicit Project Boundary

Generation aliases routed by `cyberppt/commands/script_runner.py` require `--project <path>`. The runner verifies that the project contains an adopted analysis-expression contract and calls the relevant readiness assertion before launching a script.

The runner must reject:

- missing `--project` for a production-capable alias;
- a path that does not contain a CyberPPT project contract;
- stale or incomplete analysis approvals;
- disagreement between the explicit project and project-owned input paths.

Legacy/debug execution must use direct script paths or a future explicit `--advanced` surface. It cannot create project production states.

### 3. Template Text Truth

`template_image_ppt_export.py` gains a required `--template-text-lock` input for project production. The lock, rather than the drawing script or OCR, supplies title, subtitle, section, template variant, page-badge setting, footer setting, and provenance.

The exporter validates:

- requested pages have exactly one lock record;
- every record is approved and its source dependencies are current;
- the page manifest and lock cover the same pages;
- the project path and output path agree;
- title/subtitle fields are not silently inferred when project production is active.

Script parsing remains available for prompt/body content and advanced standalone use, but it is not the title-layer truth in project production.

### 4. Speaker Notes Approval

Add stage, approve, and status operations for speaker notes. The approval record binds:

- the notes manifest hash;
- the approved business-script hash;
- the selected page range;
- the source-analysis dependency already carried by the business script;
- the user-selected approval option.

Regenerating notes, editing the business script, or changing the page range invalidates approval. `assemble` accepts only the approved manifest. The exporter must not fall back to drawing-script notes in project production.

### 5. Assembly Readiness

A subprocess return code of zero is necessary but not sufficient. Assembly succeeds only when all required artifacts exist and validate:

- non-empty exported PPTX;
- valid `template_image_manifest.json`;
- page count and page set equal the requested range;
- all approved full-image inputs exist and match recorded hashes;
- template-text and speaker-notes coverage is complete;
- the PPTX is a readable ZIP package and contains the expected slide and notes parts;
- output paths stay under the project workspace.

The assembly report records `image_ppt_assembled`, never `production_ready` or `deliverable_ready`.

### 6. Render And Strict QA

`produce verify` creates a project-owned QA bundle under `workbench/stages/05-qa-delivery/<page-range>/`:

- rendered page PNGs;
- per-page body-region comparison report against the approved full image;
- template-layer presence and bounds report;
- speaker-notes presence report;
- full-image delivery manifest;
- strict validation JSON;
- aggregate production-readiness report.

Rendering uses the existing LibreOffice/Poppler path. Missing rendering dependencies are blocking in production verification, not warnings. The full-image delivery manifest defines mode-specific strict rules: body content is intentionally image-based, while template text/chrome and speaker notes must remain native and present.

`deliverable_ready` requires all requested pages to pass both render QA and strict QA. The final PPTX is copied or registered under `delivery/` only after that transition.

### 7. Artifact Ledger

Every durable production artifact is registered with `stage`, `page`, `path`, `status`, `depends_on`, `supersedes`, `resume_command`, and SHA-256.

The dependency chain must be traversable:

```text
delivery PPTX
  -> strict QA + render QA
  -> assembled PPTX + template image manifest
  -> approved full images + approved speaker notes + template text lock
  -> approved blueprint input + approved visual style + approved business script
  -> approved source analysis
```

Status code must recompute hashes instead of trusting ledger labels. Superseded runs remain traceable but are excluded from delivery selection.

## Error Handling

Errors identify the failed gate, stale dependency, expected artifact, current artifact, and exact recovery command. Production commands never repair or reapprove inputs implicitly.

Examples:

- stale notes: rerun `produce prepare`, review notes, then approve them;
- changed image: restage and reapprove blueprint-image review;
- missing title lock: stop at `metadata_required`;
- assembly return code zero but missing PPTX: `assembly_artifact_missing`;
- render dependency missing: `render_tool_unavailable`;
- body-region comparison failure: return to the affected full image, not template assembly;
- template-layer failure: rerun assembly without regenerating approved full images.

## Compatibility And Documentation

- Keep legacy OCR/overlay/template-rebuild code and tests, but mark them advanced and exclude them from mainline status.
- Fix package-relative imports so mainline exporter helpers remain importable by legacy modules.
- Update `SKILL.md`, `README.md`, and `docs/repository-layout.md` to describe one default mode: `full_image_ppt`.
- Move editable-overlay requirements into a clearly labeled legacy/advanced section. The default contract must state that content-region text is generally not editable.
- Replace old README examples with the `produce` state-machine commands and explicit approval commands.

## Testing Strategy

Implementation follows test-first development.

1. Unit tests cover every transition, stale hash, missing artifact, page-range mismatch, explicit-project requirement, and recovery command.
2. Exporter tests prove that template text comes from the lock and that project production rejects fallback title inference.
3. Speaker-notes tests prove that unapproved or stale notes cannot be assembled.
4. Assembly tests use a real minimal PPTX export where practical; mocked subprocess tests must additionally create and validate the expected artifact bundle.
5. QA tests use fixture PPTX/full-image pairs and cover pass, render-tool absence, comparison failure, strict failure, and missing notes.
6. CLI tests cover `produce prepare|assemble|verify|status` and rejection of production aliases without `--project`.
7. Regression tests keep legacy module help/import execution working.
8. The full test suite must not write to tracked project workspaces; all generated test assets stay in temporary directories.

## Acceptance Criteria

- No project production command can run without an explicit valid project.
- No assembly can consume an unapproved blueprint image or unapproved speaker-notes manifest.
- `template_text_lock` is a required, verified exporter input in project production.
- A zero subprocess return code without the expected artifacts fails assembly.
- `deliverable_ready` is impossible without rendered pages, body-region comparisons, strict validation, and complete ledger records.
- `final-script-pages` cannot report production completion.
- Mainline documentation contains no default full/background dual-image or editable-overlay claims.
- Focused mainline tests and the complete test suite pass without modifying tracked project artifacts.

## Out Of Scope

- Removing legacy OCR, overlay, semantic-plan, scene-graph, or native-rebuild implementations.
- Making content-region text editable in the default `full_image_ppt` mode.
- Building a graphical workflow UI.
- Automatically approving any human review gate.

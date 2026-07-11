# Stage 1 LLM Quality Pipeline Design

## Purpose

Turn CyberPPT Stage 1 from a workflow where an operator supplies finished Markdown into a reproducible, reviewable model-assisted workflow. The feature must improve semantic quality while preserving the existing evidence, hash, ordering, and human-approval gates.

## Scope

This design covers the five analysis-expression gates:

1. `source_analysis`
2. `reporting_direction`
3. `report_structure`
4. `page_design`
5. `business_script`

It consumes an existing normalized source extract (`source_extract.md` and optionally `source_extract.json`). Raw DOCX/PDF/XLSX extraction adapters, external web research, OCR, Stage 2 image generation, and automatic approval are out of scope. A separate source-ingestion plan can productize raw-format extraction after this quality pipeline is stable.

## Design Decision

Use a prompt-first, gate-by-gate hybrid pipeline:

```text
normalized source extract
        -> reviewable prompt MD
        -> model raw JSON
        -> deterministic grounding and rendering
        -> candidate Markdown
        -> optional model critic report
        -> existing stage/approve gate
```

The model handles classification, comparison, organization, critique, and language. Deterministic code owns source locators, evidence IDs, number fidelity, hashes, dependency freshness, and legal state transitions.

## Commands

Add a nested `phase1` command group:

```bash
python3 -m cyberppt phase1 prepare <project> --gate <gate> [--input <source_extract.md>]
python3 -m cyberppt phase1 generate <project> --gate <gate> [--model <model>] [--dry-run-llm]
python3 -m cyberppt phase1 critique <project> --gate <gate> [--model <model>]
python3 -m cyberppt phase1 stage <project> --gate <gate> --recommendation <value> --options-json '<json>'
python3 -m cyberppt phase1 status <project> [--json]
```

`prepare` writes the prompt and never calls a model. `generate` consumes the current prompt file exactly as edited and never overwrites it. `stage` requires deterministic QA to pass, then delegates to the existing `stage_analysis_artifact()` function. Existing hand-authored `stage-*` commands remain compatible.

## Artifact Contract

Each gate uses `workbench/stages/01-analysis/model-runs/<gate>/`:

```text
source_bundle.json                 # source_analysis only
source_bundle.md                   # source_analysis only, human-readable
chunks/chunk_001.json              # source_analysis only
prompts/<gate>_prompt.md           # human-editable model input
llm/<gate>_raw.json                # exact model response
candidates/<gate>.md               # rendered candidate for review
qa/<gate>_grounding.json           # deterministic blocking QA
qa/<gate>_critic_prompt.md          # inspectable critic input
qa/<gate>_critic_raw.json           # exact critic response
qa/<gate>_critic.json               # normalized non-authoritative findings
run.json                            # model, hashes, dependencies, status
```

`artifact-ledger.json` records the prompt, raw output, candidate, QA, and run manifest with model name, SHA-256 values, upstream dependencies, and resume command.

## Source Analysis Grounding

The source bundle divides the normalized extract into stable units. Each unit contains:

- `unit_id`
- `kind`
- `text`
- `source_path`
- `locator`
- `numbers`

The model returns evidence candidates with source unit IDs and verbatim support. Deterministic validation rejects or flags an item when:

- a cited source unit does not exist;
- verbatim support is not present in the cited unit;
- a number in the claim or structured numeric field is absent from the cited source units;
- the model supplies a source location that conflicts with the source bundle;
- required evidence fields are empty.

Final `E01`, `E02`, and subsequent IDs are assigned by code in source order, not by the model.

## Downstream Gate Grounding

Every downstream prompt contains only approved upstream artifacts plus the frozen evidence registry. Outputs must use registered evidence IDs. The renderer and deterministic QA check:

- all cited evidence IDs exist;
- every content page has evidence, caveat/boundary, meaning, transition, density, and component data;
- visible numbers are present in cited evidence;
- the business script does not introduce unsupported facts or turn boundary items into established facts;
- dependency hashes still match approved artifacts.

## Model Critic

The critic is a second model pass with a different instruction: identify unsupported claims, weak evidence, duplicated pages, narrative gaps, inappropriate external-consulting language, vague titles, density mismatches, and boundary overstatement. It emits findings only and never rewrites the candidate or changes gate state.

Deterministic grounding failures block `phase1 stage`. Critic findings remain advisory and are presented for human review.

## Error Handling

- Model/network failure leaves the prompt and run manifest intact with `status=model_failed` and a resume command.
- Invalid JSON preserves the raw output and records `status=parse_failed`; it does not create a stageable candidate.
- Stale source or approved upstream hashes block generation until `prepare` is rerun.
- Editing a prompt is allowed and expected. `generate` records the current prompt hash rather than restoring generated text.
- No command automatically approves an analysis-expression gate.

## Compatibility

- Existing `stage-*`, `approve-*`, and `analysis-expression-status` behavior remains valid.
- Existing approved projects do not need migration.
- The current `internal_public_sector` and `source_and_task_adaptive` defaults remain authoritative.
- No new runtime dependency is introduced; implementation uses the Python standard library and the existing Codex Responses transport.

## Acceptance Criteria

1. A user can inspect and edit each gate prompt before a model call.
2. The generated candidate can be traced to prompt, model, source, and approved upstream hashes.
3. Unsupported numbers and unknown evidence IDs cannot pass deterministic Stage 1 QA.
4. Each model-generated gate still requires the existing explicit human approval.
5. Network and parse failures are resumable and never silently fall back to low-quality generated content.
6. Existing Stage 1 and Stage 2 tests remain green.

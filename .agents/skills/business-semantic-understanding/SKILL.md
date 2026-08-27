---
name: business-semantic-understanding
description: Use when source materials have already been structurally parsed and the agent must understand business meaning, consolidate repeated assertions, identify concepts and relationships, reconstruct argument logic, or prepare a reliable semantic foundation before proposal writing.
---

# Business Semantic Understanding

## Overview

Turn layer-two source assertions into a traceable semantic model. The model may interpret, normalize and diagnose the source, but it must never blur the boundary between what the source explicitly says and what the agent infers.

## Required inputs

Use a foundation directory containing `structure.json` and `fact-base.json`. If only Word/PDF/PPT/XLSX or Markdown exists, run the earlier source-material layers first.

Read `references/semantic-contract.md` before reasoning.

## Workflow

Run the commands below from this Skill directory with the repository interpreter at `../../../.venv/bin/python3`.

1. Prepare a bounded workpack:

```bash
../../../.venv/bin/python3 scripts/prepare.py <foundation-dir> -o <semantic-dir>
```

2. **Pass 0 — holistic comprehension (lightweight).** Before chunk-by-chunk work, read the whole document once and write a short free-text note to `comprehension-brief.json` in the semantic directory: `overview` (what the material is, who it's for, what problem it addresses), `open_questions` (anything that doesn't add up, is unclear, or is under-evidenced), and `external_notes` (anything you needed domain knowledge or a web check to understand). This file is a personal working note, not a validated artifact — it is not schema-checked, not hashed against upstream, and does not gate `semantic-report.json`. Skip fields that don't apply; there is no coverage requirement over sections.

3. **Pass 1 — section/chunk interpretation.** Read every file listed by `semantic-workpack.json`. For each section/chunk, identify candidate normalized facts, concepts, source-stated relations, possible inferred or externally-informed relations, argument roles, conflicts and ambiguities. Keep the original `fact_id` evidence attached.

4. **Pass 2 — cross-section reconciliation.** Reconcile aliases and duplicates across the whole document. Merge only genuinely equivalent assertions. Preserve conflicting claims and unresolved ambiguity. Reconstruct the original source logic separately from a normalized logical reading order.

5. Write exactly these document-level artifacts in the semantic directory:

- `normalized-facts.json`
- `concept-base.json`
- `relation-graph.json`
- `argument-chain.json`

6. Validate before using the semantic model downstream:

```bash
../../../.venv/bin/python3 scripts/validate.py <foundation-dir> <semantic-dir> --report
```

`semantic-report.json` must report `status: ok`. If validation fails, correct the semantic artifacts; do not bypass the validator.

## Evidence and inference rules

- Keep `verification_status: unverified`; this layer does not externally verify the source's own claims against reality.
- Domain knowledge and active web checks (via `WebSearch`/`WebFetch` or equivalent, where available) may be used to aid understanding and sanity-check the source. Anything not stated by the source itself must carry `basis: external` in `relation-graph.json`, with a one-line `inference_rationale` saying what it relies on (a URL, "industry practice", etc. — as specific as is convenient, no fixed citation format required).
- Every normalized fact must point to one or more layer-two source assertions and exact evidence coordinates.
- Use `basis: source` only when the relationship is stated by the source (previously `explicit`; renamed for clarity — it marks source-grounded content, not a claim about ground truth).
- Use `basis: inferred` for model inference drawn from the source's own evidence, and include `inference_rationale`.
- Use `basis: external` for anything that depends on information outside the source, and include `inference_rationale`. Never let an `external` or `inferred` item upgrade to `basis: source` — `source` means the source text says it, not that the conclusion is correct.
- Keep conflicts and ambiguities visible instead of selecting a convenient interpretation.
- Concept definitions may summarize supported material; they may not add new claims.

## Argument reconstruction

`source_chain` follows the source document's own argumentative order. `reconstructed_chain` may reorder semantic stages to expose the underlying logic. Do not silently repair weak logic. Record repetition, non-MECE overlap, logic gaps, missing bridges, mixed levels, scope shifts, unsupported jumps, contradictions and unbalanced parallelism in `diagnostics`; every diagnostic must record its resolution or deliberate retention. Prefer atomic table-cell assertions when layer two provides them and review every table-parent or composite-statement warning before validation is accepted.

## Stop boundary

Do not draft a proposal, report, PPT script, recommendation, or polished replacement text in this Skill. Its terminal product is the validated semantic foundation. Downstream writing starts only after validation succeeds.

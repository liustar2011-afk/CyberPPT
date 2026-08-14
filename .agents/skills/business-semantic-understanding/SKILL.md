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

1. Prepare a bounded workpack:

```bash
python scripts/prepare.py <foundation-dir> -o <semantic-dir>
```

2. **Pass 1 — section/chunk interpretation.** Read every file listed by `semantic-workpack.json`. For each section/chunk, identify candidate normalized facts, concepts, explicit relations, possible inferred relations, argument roles, conflicts and ambiguities. Keep the original `fact_id` evidence attached.

3. **Pass 2 — cross-section reconciliation.** Reconcile aliases and duplicates across the whole document. Merge only genuinely equivalent assertions. Preserve conflicting claims and unresolved ambiguity. Reconstruct the original source logic separately from a normalized logical reading order.

4. Write exactly these document-level artifacts in the semantic directory:

- `normalized-facts.json`
- `concept-base.json`
- `relation-graph.json`
- `argument-chain.json`

5. Validate before using the semantic model downstream:

```bash
python scripts/validate.py <foundation-dir> <semantic-dir> --report
```

`semantic-report.json` must report `status: ok`. If validation fails, correct the semantic artifacts; do not bypass the validator.

## Evidence and inference rules

- Keep `verification_status: unverified`; this layer does not externally verify truth.
- Do not browse, search external sources, or enrich the source with outside facts.
- Every normalized fact must point to one or more layer-two source assertions and exact evidence coordinates.
- Use `basis: explicit` only when the relationship is stated by the source.
- Use `basis: inferred` for model inference and include `inference_rationale`.
- Keep conflicts and ambiguities visible instead of selecting a convenient interpretation.
- Concept definitions may summarize supported material; they may not add new claims.

## Argument reconstruction

`source_chain` follows the source document's own argumentative order. `reconstructed_chain` may reorder semantic stages to expose the underlying logic. Do not silently repair weak logic. Record repetition, non-MECE overlap, logic gaps, missing bridges, mixed levels, scope shifts, unsupported jumps, contradictions and unbalanced parallelism in `diagnostics`.

## Stop boundary

Do not draft a proposal, report, PPT script, recommendation, or polished replacement text in this Skill. Its terminal product is the validated semantic foundation. Downstream writing starts only after validation succeeds.

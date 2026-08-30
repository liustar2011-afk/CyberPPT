---
name: cyberppt-source-foundation
description: Strict/legacy source-foundation route for contracts, regulation, fact-by-fact verification, Source Truth work, full semantic models, and old-project compatibility.
---

# CyberPPT Source Foundation

## Purpose

Use this Skill by default for new source-to-script projects and for existing
`strict/legacy` projects. It provides contracts, regulation, explicit
fact-by-fact verification, Source Truth compatibility work and full semantic-model
work. Use `cyberppt-script-understand` only when the user explicitly selects the
lightweight `script` profile. For an existing strict project, first determine
whether approved source-foundation outputs can be reused.

Runtime chain:

`source mapping -> semantic understanding -> compatibility projections -> project-foundation -> cyberppt-script-workflow`

Content authority is defined separately in
[`docs/STAGE01_AUTHORITY_MAP.md`](../../../docs/STAGE01_AUTHORITY_MAP.md). A file
can be required by the current compatibility runtime without becoming a second
semantic authority.

## Workflow entry

Before acting, read the repository-wide [CyberPPT workflow overview](../../../docs/CYBERPPT_WORKFLOW.md) and the [Stage 01 Authority Map](../../../docs/STAGE01_AUTHORITY_MAP.md). This Skill is the strict/legacy Stage 01 entry; the overview is the single place to find the complete route, the two human stops, the Stage 01/Stage 02 boundary, and completion criteria. The Authority Map is the single place to determine which content representation may be edited when two artifacts disagree.

## Canonical route

The strict/legacy runtime route is `prepare-source-map` → whole-document semantic
understanding → `compile-source-truth` → `project-foundation` →
`cyberppt-script-workflow` (PLAN/AUTHOR). Legacy Outline/Handoff implementations
remain internal compatibility code and must not run over current validated
semantic outputs.

`semantic-argument-model.json`, `source-truth.json` and `outline.json` may appear
in this runtime route because existing compilers consume them. They are
mechanical/compatibility projections in the strict profile and must not be
hand-edited as an alternative semantic source.

## Required sequence

1. From the repository root, run `.venv/bin/python3 -m cyberppt prepare-source-map <project>`, then `.venv/bin/python3 -m cyberppt source-map-check <project>`. Resolve every blocking extraction issue before continuing.
2. Run `.venv/bin/python3 -m cyberppt prepare-semantic-understanding <project>`. Complete the source-bound whole-document semantic understanding required by the current strict compiler. If the runtime writes `semantic-argument-model.json`, treat it as the compiler-facing projection described by the Authority Map, not as an independently editable semantic source.
3. Run `.venv/bin/python3 -m cyberppt semantic-check <project>` and confirm the semantic report is `ok`.
4. Before planning pages, derive one source-faithful communication-goal direction from the validated semantic understanding and include it in **脚本规划待确认**. Do not add a separate communication-goal approval stop. The user's wording may constrain audience, use, or delivery, but must not be promoted into a source fact, source judgment, or page conclusion without direct source support.
5. Run `.venv/bin/python3 -m cyberppt compile-source-truth <project>` and `.venv/bin/python3 -m cyberppt source-truth-audit <project> --input <project>/workbench/stages/01-analysis/source-truth.json`. `source-truth.json` is a validated transport/projection for current downstream consumers; validation does not promote it to a second authoring authority.
6. Run `.venv/bin/python3 -m cyberppt project-foundation <project>` to mechanically project the validated strict semantic result into `script/foundation.json`.
7. Continue with `cyberppt-script-workflow` for PLAN/AUTHOR. Present the readable deck plan at **脚本规划待确认** before writing the final script.

## Authority rules

- Source Evidence is the authority for exact wording, coordinates and source identity.
- In strict/legacy, `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, and `argument-chain.json` are four field-partitioned files of one logical SemanticIR. They must not maintain competing versions of the same semantic field.
- `script/foundation.json` is the only unified semantic input to PLAN/AUTHOR. In strict/legacy it is mechanically projected; it may not feed edits back into the strict SemanticIR.
- `script/deck-plan.json` is DeckPlanIR. It owns communication structure and page boundaries, not final page wording.
- `script/dist/final-script.md` is FinalScriptIR and the only Stage 02 cross-stage business input. A JSON mirror, when present, must be synchronized and is not a second authoring surface.
- Projected `semantic-argument-model.json`, `source-truth.json`, `outline.json` and historical Handoff files are derived compatibility artifacts in strict/legacy. Do not fix semantic defects by hand-editing them.
- Projection code may map IDs and fields but may not invent claims, merge facts, add page evidence, infer responsibilities, or raise maturity/status.
- After the final script is locked, Stage 02 enters through `.venv/bin/python3 -m cyberppt final-script-pages --production-build ...`; visual prompts, manifests and QA records remain derived runtime outputs.

## Page planning discipline

Every content page must define one audience question, one page mission, one core judgment, one non-substitutable value, one governing argument chain, evidence roles, `must_not_include`, `reserved_for_later`, split risk, and page-to-page transitions. Related evidence is not automatically onscreen evidence.

## Do not use

Do not use this skill for an already approved `script-final.md`, isolated Stage 02 visual work, image generation, SVG reconstruction, or PPTX QA.

---
name: cyberppt-source-foundation
description: Strict/legacy source-foundation route for contracts, regulation, fact-by-fact verification, Source Truth work, full semantic models, and old-project compatibility.
---

# CyberPPT Source Foundation

## Purpose

Use this Skill by default for new source-to-script projects and for existing
`strict/legacy` projects. It provides contracts, regulation, explicit
fact-by-fact verification, Source Truth and full semantic-model work. Use
`cyberppt-script-understand` only when the user explicitly selects the
lightweight `script` profile. For an existing strict project, first determine
whether approved source-foundation outputs can be reused.

Authoritative chain:

`source mapping -> whole-document semantic model -> Source Truth projection -> project-foundation -> cyberppt-script-workflow`

Read `docs/CYBERPPT_AUTHORITY_MAP.md` when deciding which artifact may be edited. The strict whole-document `semantic-argument-model.json` is the single writable semantic authority entering Source Truth compilation. Source Truth and Foundation are downstream projections/contracts; they must never become a second independently authored semantic model.

## Workflow entry

Before acting, read the repository-wide [CyberPPT workflow overview](../../../docs/CYBERPPT_WORKFLOW.md). This Skill is the strict/legacy Stage 01 entry; the overview is the single place to find the complete route, the two human stops, the Stage 01/Stage 02 boundary, and completion criteria.

## Canonical route

The strict/legacy route is `prepare-source-map` → whole-document semantic
understanding → `compile-source-truth` → `project-foundation` →
`cyberppt-script-workflow` (PLAN/AUTHOR). Legacy Outline/Handoff implementations
remain internal compatibility code and must not run over current Source Truth
outputs.

When the project uses the deeper `business-semantic-understanding` preparation,
its `normalized-facts.json`, `concept-base.json`, `relation-graph.json` and
`argument-chain.json` feed the current semantic authority through the existing
projection path. They do not remain parallel writable authorities for PLAN or
AUTHOR.

## Required sequence

1. From the repository root, run `.venv/bin/python3 -m cyberppt prepare-source-map <project>`, then `.venv/bin/python3 -m cyberppt source-map-check <project>`. Resolve every blocking extraction issue before continuing.
2. Run `.venv/bin/python3 -m cyberppt prepare-semantic-understanding <project>`. Use its source-bound authoring task to create the canonical whole-document `semantic-argument-model.json`; this model preserves the document map, semantic nodes, argument relations, source coverage, source-native status and evidence references.
3. Run `.venv/bin/python3 -m cyberppt semantic-check <project>` and confirm the semantic report is `ok`.
4. Before planning pages, derive one source-faithful communication-goal direction from the validated semantic model and include it in **脚本规划待确认**. Do not add a separate communication-goal approval stop. The user's wording may constrain audience, use, or delivery, but must not be promoted into a source fact, source judgment, or page conclusion without direct source support.
5. Run `.venv/bin/python3 -m cyberppt compile-source-truth <project>` and `.venv/bin/python3 -m cyberppt source-truth-audit <project> --input <project>/workbench/stages/01-analysis/source-truth.json`. `source-truth.json` is a deterministic projection and must not be hand-edited as a second semantic source.
6. Run `.venv/bin/python3 -m cyberppt project-foundation <project>` to mechanically project the validated Source Truth into `script/foundation.json`.
7. Continue with `cyberppt-script-workflow` for PLAN/AUTHOR. Present the readable deck plan at **脚本规划待确认** before writing the final script.

## Authority rules

- Original source files and deterministic source units are source authority.
- `semantic-argument-model.json` is the strict route's single writable whole-document semantic authority.
- `source-truth.json` is compiled from the semantic model and source units; audits validate it but do not author new meaning.
- `script/foundation.json` is the PLAN/AUTHOR semantic contract after projection. PLAN and AUTHOR consume it; they do not rebuild whole-document semantics.
- `script/deck-plan.json` is the planning authority for communication goal, sections, page order, page mission and permitted source range.
- `script/dist/final-script.md` is the Stage 02 cross-stage content authority.
- Handoff/projection code may map IDs and fields but may not invent claims, merge facts, add page evidence, infer responsibilities, or raise maturity/status.
- Stage 02 visual prompts, manifests and QA records are derived runtime outputs and may not modify Stage 01 content authority.

## Page planning discipline

Every content page must define one audience question, one page mission, one core judgment, one non-substitutable value, one governing argument chain, evidence roles, `must_not_include`, `reserved_for_later`, split risk, and page-to-page transitions. Related evidence is not automatically onscreen evidence.

## Do not use

Do not use this skill for an already approved `script-final.md`, isolated Stage 02 visual work, image generation, SVG reconstruction, or PPTX QA.

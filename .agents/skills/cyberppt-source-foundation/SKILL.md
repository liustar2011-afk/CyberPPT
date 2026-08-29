---
name: cyberppt-source-foundation
description: Strict/legacy source-foundation route for contracts, regulation, fact-by-fact verification, Source Truth work, full semantic models, and old-project compatibility.
---

# CyberPPT Source Foundation

## Purpose

Use this Skill for `strict/legacy` projects: contracts, regulation, explicit
fact-by-fact verification, Source Truth or full semantic-model work, and old
project migration. New ordinary script projects use `cyberppt-script-understand`
after deterministic source indexing. For an existing strict project, first
determine whether approved source-foundation outputs can be reused.

Authoritative chain:

`source -> source.md -> structure/fact base -> semantic outputs -> deck brief/page plan -> CyberPPT projection -> cyberppt-write-single-page`

The projection is a compatibility artifact only. It must never become a second semantic authority.

## Workflow entry

Before acting, read the repository-wide [CyberPPT workflow overview](../../../docs/CYBERPPT_WORKFLOW.md). This Skill is the mandatory Stage 01 entry and owns the source-to-handoff sequence; the overview is the single place to find the complete route, the four human stops, the Stage 01/Stage 02 boundary, and completion criteria.

## Canonical route

The strict/legacy route is `cyberppt-source-foundation` →
`business-semantic-understanding` → `project-foundation` →
`cyberppt-script-workflow` (PLAN/AUTHOR). Legacy Outline/Handoff implementations
remain internal compatibility code and must not run over current Source Truth
outputs.

## Required sequence

1. From the repository root, run `.venv/bin/python3 scripts/source_foundation_pipeline.py <source> -o <project>/workbench/source-foundation --prepare-semantic --report`.
2. Use `business-semantic-understanding` to author the four semantic outputs in the prepared semantic directory, then run its validator with `--report`.
3. Before planning pages, derive one source-faithful communication-goal direction from the semantic outputs and present it as the recommendation. Do not offer multiple options. The user's wording may constrain audience, use, or delivery, but must not be promoted into a source fact, source judgment, or page conclusion without direct source support. After the user edits or confirms the direction, continue.
4. Run `.venv/bin/python3 -m cyberppt semantic-check <project>` and confirm the semantic report is `ok`.
5. Run `.venv/bin/python3 -m cyberppt compile-source-truth <project>` and `.venv/bin/python3 -m cyberppt source-truth-audit <project> --input <project>/workbench/stages/01-analysis/source-truth.json`.
6. Run `.venv/bin/python3 -m cyberppt project-foundation <project>` to mechanically project the validated Source Truth into `script/foundation.json`.
7. Continue with `cyberppt-script-workflow` for PLAN/AUTHOR. Present the readable deck plan at **脚本规划待确认** before writing the final script.

## Authority rules

- `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, and `argument-chain.json` are semantic-stage authorities; `script/foundation.json`, `script/deck-plan.json`, and `script/dist/final-script.md` are the authoritative PLAN/AUTHOR artifacts.
- Projected `semantic-argument-model.json`, `source-truth.json`, and `outline.json` exist only to satisfy CyberPPT downstream consumers.
- Handoff code may map IDs and fields but may not invent claims, merge facts, add page evidence, infer responsibilities, or raise maturity/status.
- CyberPPT page `source_refs` must equal the page's explicitly authorized normalized-fact set after deterministic ID projection.
- Stage 01 has exactly three authoritative script artifacts: `script/foundation.json`, `script/deck-plan.json`, and `script/dist/final-script.md`.
- After the final script is locked, Stage 02 enters through `.venv/bin/python3 -m cyberppt final-script-pages --production-build ...`; visual prompts, manifests and QA records remain derived runtime outputs.

## Page planning discipline

Every content page must define one audience question, one page mission, one core judgment, one non-substitutable value, one governing argument chain, evidence roles, `must_not_include`, `reserved_for_later`, split risk, and page-to-page transitions. Related evidence is not automatically onscreen evidence.

## Do not use

Do not use this skill for an already approved `script-final.md`, isolated Stage 02 visual work, image generation, SVG reconstruction, or PPTX QA.

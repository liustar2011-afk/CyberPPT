---
name: ppt-outline-planning
description: Use when validated source semantics already exist and the agent must decide how a PPT should be structured, what the deck should prove, how many pages it needs, or what mission and judgment each slide should carry before slide copy is written.
---

# PPT Outline Planning

## Overview

Plan the deck before writing slides. Consume the validated semantic foundation, establish the deck-level argument, then decompose it into evidence-bound page missions. The terminal product is a validated PPT outline and a page-authoring contract; it is not a PPT script.

## Required inputs

Use a layer-three semantic directory containing `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, `argument-chain.json`, and `semantic-report.json` with `status: ok`. Do not reread Word/PDF or restart interpretation from the original source unless a downstream evidence check explicitly requires a trace-back through earlier IDs.

Read `references/outline-contract.md` before planning.

## Workflow

1. Prepare `outline-workpack.json` with `python scripts/prepare.py <semantic-dir> -o <outline-dir>`. The default policy is `government_official` with source structure, titles, order and content locked.
2. 默认采用政府公文式、央企正式交流语体，默认保留源材料章节标题、内容标题和顺序。先按源材料标题体系确定页面归属，再建立 **Deck Thesis**、页面使命和论证链用于说明原文内容；这些内部规划字段不得覆盖源材料标题。仅因单页容量拆页，拆分页使用“源标题（一）”“源标题（二）”；可以合并重复内容，但必须保留全部实质信息、来源归属、事实强度、责任、条件和状态。只有用户明确要求重构叙事、咨询化、路演化、改名或重排时，才可启用 flexible policy。
3. Use the official generator to create the source-locked candidate:

```bash
python scripts/generate.py <semantic-dir> -o <outline-dir> --force
```

   The candidate generator maps source headings and normalized facts but deliberately sets `editorial_authoring_status: "mechanical_draft"`; it is not a professional authoring shortcut.
4. To compile an authored Outline, provide a complete structured spec described in `references/authoring-spec.md`:

   First prepare the source-bound blank authoring input:

```bash
python scripts/prepare-authoring.py <semantic-dir> --outline-dir <outline-dir> -o <authoring-spec.json> --force
```

```bash
python scripts/generate.py <semantic-dir> -o <outline-dir> --authoring-spec <authoring-spec.json> --force
```

   The spec is keyed by source heading ID and can override only page-authoring fields. Source titles, order, headings, evidence IDs, and page types remain generator-owned.
5. Write/compile `deck-brief.json` and `page-plan.json`. Enforce **one page / one core point**.
6. For every content page author both the deck-planning fields and the CyberPPT-ready page boundary contract: `audience_question`, `page_mission`, `key_judgment`, `non_substitutable_value`, one governing `argument_chain`, `evidence_roles`, `must_not_include`, `reserved_for_later`, `split_risk`, `transition_from_previous`, and `transition_to_next`.
7. Classify page evidence by responsibility: `claim`, `reason`, `instance`, `boundary`, or `trace_only`. Related evidence is not automatically onscreen evidence; `trace_only` keeps traceability without creating a visual module. Every content page MUST include at least one direct `normalized_fact_id`; relations and argument nodes may organize or explain those facts but may not replace direct fact grounding.
8. Preserve epistemic boundaries. Use `source_explicit`, `source_synthesis`, or `planning_inference` for `judgment_basis`. `planning_inference` requires `inference_rationale`; a layer-three `basis: inferred` relation requires `evidence.inference_note`. New source facts are forbidden.
9. Keep machine-generated output as a candidate: use `editorial_authoring_mode: "author_driven"` with `editorial_authoring_status: "mechanical_draft"` until the author has made the page-level editorial decisions. Do not set `author_edited` merely because evidence, titles, or page fields were populated.
10. Before setting `editorial_authoring_status: "author_edited"`, every content page must carry `judgment_derivation` (or the compatibility alias `core_message_derivation`), structured `excluded_from_onscreen` items with `source_refs` and a reason, and `authoring_decisions.deletion_test` plus `authoring_decisions.evidence_selection`. `key_judgment` is the canonical layer-four field; an optional `core_message` alias must match it exactly.
11. Attachment pages require `authoring_decisions.attachment_disposition` (`main_deck`, `appendix`, or `trace_only`). `main_deck` requires a business-judgment promotion rationale; source coverage alone never promotes appendix registration fields, checklists, forms, or operating detail to a main-deck module.
12. Validate with `python scripts/validate.py <semantic-dir> <outline-dir> --report`; `outline-report.json` must report `status: ok`. A candidate may be structurally valid, but it is not author-complete until the authoring status and authoring gates both pass.
13. Render `ppt-outline.md` with `python scripts/render.py <outline-dir>`. Do not hand-maintain a divergent Markdown outline.

For the formal single-command route, use:

```bash
python scripts/plan.py <semantic-dir> -o <outline-dir> --force
python scripts/plan.py <semantic-dir> -o <outline-dir> --authoring-spec <authoring-spec.json> --force
```

The command performs generation, validation, report writing and Markdown rendering in that order. A candidate is allowed to render for human review, while `gates.handoff_status` remains `blocked` until both deck and page plan are `author_edited`. The handoff Skill rejects a mechanically generated Outline even when its structural report is `ok`.

The generator consumes layer-three concept and relation artifacts. Each content page records `concept_ids`, source relation IDs and page-level argument node bindings. Relations are selected only when all of their source fact IDs are already direct page evidence; inferred relations retain `evidence.inference_note`. Page budgets and merge groups are explicit authoring constraints. Attachment headings default to `trace_only` and require an explicit author decision before entering the main deck.

## CyberPPT-ready page contract

The fields adopted from CyberPPT's downstream page-authoring practice are boundary and consumption fields, not a return to CyberPPT's upstream semantic pipeline. `audience_question` states the audience-facing question; `page_mission` states the author's internal responsibility. `non_substitutable_value` must pass the deletion test against adjacent pages. `argument_chain` is the one chain that governs reading order. `must_not_include` prevents cross-page leakage; `reserved_for_later` names the later page that owns deferred material. Medium/high `split_risk` requires a reason.

## Planning rules

Use `reconstructed_chain` to understand source-supported relations, while consulting `source_chain` and `diagnostics` to identify duplication or logical weakness. Under the default locked policy, preserve source order and do not invent a chapter logic, problem path, communication path, consulting headline or marketing headline. Logical bridges are allowed only as labeled planning inference and may not rename or reorder source headings. Template pages (`cover`, `agenda`, `section_divider`, `closing`) carry no business evidence or body judgment. The agenda uses the source directory title or `目录` and lists source sections only.

Every locked section-divider and content page records `source_heading_ids` and `primary_source_heading_id`. The primary heading owns the page title and source order. Multiple source IDs may be recorded only for a genuine duplicate-content merge; repeated primary IDs are allowed for capacity splits. `deck-brief.json` must copy the workpack request/policy binding and declare the same `writing_style_mode` and `source_structure_mode` before validation.

`suggested_visual_logic` may describe only an abstract carrier such as `timeline`, `process_chain` or `layered_architecture`; it is not page design.

## Stop boundary

Do not create SCRIPT-FINAL, final on-screen copy, detailed bullets, speaker notes, image prompts, detailed layout, colors, fonts, generated images or PPT files. `cyberppt-handoff` may project this validated contract into CyberPPT-compatible artifacts, but it may not reinterpret it.

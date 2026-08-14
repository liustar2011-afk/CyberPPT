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
3. Write `deck-brief.json` and `page-plan.json`. Enforce **one page / one core point**.
4. For every content page author both the deck-planning fields and the CyberPPT-ready page boundary contract: `audience_question`, `page_mission`, `key_judgment`, `non_substitutable_value`, one governing `argument_chain`, `evidence_roles`, `must_not_include`, `reserved_for_later`, `split_risk`, `transition_from_previous`, and `transition_to_next`.
5. Classify page evidence by responsibility: `claim`, `reason`, `instance`, `boundary`, or `trace_only`. Related evidence is not automatically onscreen evidence; `trace_only` keeps traceability without creating a visual module. Every content page MUST include at least one direct `normalized_fact_id`; relations and argument nodes may organize or explain those facts but may not replace direct fact grounding.
6. Preserve epistemic boundaries. Use `source_explicit`, `source_synthesis`, or `planning_inference` for `judgment_basis`. `planning_inference` requires `inference_rationale`; a layer-three `basis: inferred` relation requires `evidence.inference_note`. New source facts are forbidden.
7. Validate with `python scripts/validate.py <semantic-dir> <outline-dir> --report`; `outline-report.json` must report `status: ok`.
8. Render `ppt-outline.md` with `python scripts/render.py <outline-dir>`. Do not hand-maintain a divergent Markdown outline.

## CyberPPT-ready page contract

The fields adopted from CyberPPT's downstream page-authoring practice are boundary and consumption fields, not a return to CyberPPT's upstream semantic pipeline. `audience_question` states the audience-facing question; `page_mission` states the author's internal responsibility. `non_substitutable_value` must pass the deletion test against adjacent pages. `argument_chain` is the one chain that governs reading order. `must_not_include` prevents cross-page leakage; `reserved_for_later` names the later page that owns deferred material. Medium/high `split_risk` requires a reason.

## Planning rules

Use `reconstructed_chain` to understand source-supported relations, while consulting `source_chain` and `diagnostics` to identify duplication or logical weakness. Under the default locked policy, preserve source order and do not invent a chapter logic, problem path, communication path, consulting headline or marketing headline. Logical bridges are allowed only as labeled planning inference and may not rename or reorder source headings. Template pages (`cover`, `agenda`, `section_divider`, `closing`) carry no business evidence or body judgment. The agenda uses the source directory title or `目录` and lists source sections only.

Every locked section-divider and content page records `source_heading_ids` and `primary_source_heading_id`. The primary heading owns the page title and source order. Multiple source IDs may be recorded only for a genuine duplicate-content merge; repeated primary IDs are allowed for capacity splits. `deck-brief.json` must copy the workpack request/policy binding and declare the same `writing_style_mode` and `source_structure_mode` before validation.

`suggested_visual_logic` may describe only an abstract carrier such as `timeline`, `process_chain` or `layered_architecture`; it is not page design.

## Stop boundary

Do not create SCRIPT-FINAL, final on-screen copy, detailed bullets, speaker notes, image prompts, detailed layout, colors, fonts, generated images or PPT files. `cyberppt-handoff` may project this validated contract into CyberPPT-compatible artifacts, but it may not reinterpret it.

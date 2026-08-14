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

1. Prepare `outline-workpack.json` with `python scripts/prepare.py <semantic-dir> -o <outline-dir>`.
2. Establish the **Deck Thesis** before **page decomposition**. Resolve audience, purpose, core question, narrative route, decision path, page budget and section theses. Source headings are evidence context, not mandatory slide structure; never mechanically copy them into a deck. Reorder and deduplicate supported material when the deck argument requires it.
3. Write `deck-brief.json` and `page-plan.json`. Enforce **one page / one core point**.
4. For every content page author both the deck-planning fields and the CyberPPT-ready page boundary contract: `audience_question`, `page_mission`, `key_judgment`, `non_substitutable_value`, one governing `argument_chain`, `evidence_roles`, `must_not_include`, `reserved_for_later`, `split_risk`, `transition_from_previous`, and `transition_to_next`.
5. Classify page evidence by responsibility: `claim`, `reason`, `instance`, `boundary`, or `trace_only`. Related evidence is not automatically onscreen evidence; `trace_only` keeps traceability without creating a visual module. Every content page MUST include at least one direct `normalized_fact_id`; relations and argument nodes may organize or explain those facts but may not replace direct fact grounding.
6. Preserve epistemic boundaries. Use `source_explicit`, `source_synthesis`, or `planning_inference` for `judgment_basis`. `planning_inference` requires `inference_rationale`; a layer-three `basis: inferred` relation requires `evidence.inference_note`. New source facts are forbidden.
7. Validate with `python scripts/validate.py <semantic-dir> <outline-dir> --report`; `outline-report.json` must report `status: ok`.
8. Render `ppt-outline.md` with `python scripts/render.py <outline-dir>`. Do not hand-maintain a divergent Markdown outline.

## CyberPPT-ready page contract

The fields adopted from CyberPPT's downstream page-authoring practice are boundary and consumption fields, not a return to CyberPPT's upstream semantic pipeline. `audience_question` states the audience-facing question; `page_mission` states the author's internal responsibility. `non_substitutable_value` must pass the deletion test against adjacent pages. `argument_chain` is the one chain that governs reading order. `must_not_include` prevents cross-page leakage; `reserved_for_later` names the later page that owns deferred material. Medium/high `split_risk` requires a reason.

## Planning rules

Use `reconstructed_chain` to understand the clean logical path, while consulting `source_chain` and `diagnostics` to see what was reordered, duplicated or logically weak. Logical bridges are allowed only as labeled planning inference. Template pages (`cover`, `agenda`, `section_divider`, `closing`) carry no business evidence or body judgment.

`suggested_visual_logic` may describe only an abstract carrier such as `timeline`, `process_chain` or `layered_architecture`; it is not page design.

## Stop boundary

Do not create SCRIPT-FINAL, final on-screen copy, detailed bullets, speaker notes, image prompts, detailed layout, colors, fonts, generated images or PPT files. `cyberppt-handoff` may project this validated contract into CyberPPT-compatible artifacts, but it may not reinterpret it.

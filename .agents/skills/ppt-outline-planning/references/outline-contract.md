# Layer-Four PPT Outline Planning Contract

Layer four turns a validated semantic foundation into a stable deck architecture and page-authoring boundary contract. It decides what the PPT must prove, how the argument is sequenced, what each page must accomplish, and what each page must not absorb from neighbors. It does not write final slide copy.

Required semantic inputs are `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, `argument-chain.json`, and `semantic-report.json` with `status: ok`.

Every content page defines `title_intent`, `page_mission`, `audience_question`, `key_judgment`, `non_substitutable_value`, `judgment_basis`, `argument_role`, page evidence, one governing `argument_chain`, `evidence_roles`, non-empty `must_not_include`, `reserved_for_later`, `split_risk`, transitions, content strategy and abstract visual logic.

Evidence responsibilities are `claim`, `reason`, `instance`, `boundary`, and `trace_only`. One evidence ID may have only one page-level responsibility. Every content page must name at least one direct `normalized_fact_id`; relation IDs and argument-node IDs cannot replace direct source-grounded facts.

`source_explicit` follows explicit source support. `source_synthesis` consolidates source-supported items without a new factual claim. `planning_inference` requires `inference_rationale`. Any cited layer-three inferred relation requires `evidence.inference_note`.

The default planning policy is source locked and government-official. The planner preserves source chapter titles, content titles, source order, content coverage, and factual strength. It may split an overloaded source heading only for slide capacity and may consolidate genuinely duplicate content without changing its topic, conditions, responsibility, state, or source order. Reframing, renaming, or reordering requires an explicit user request. It may not invent source facts or upgrade inference strength.

When `outline-workpack.json.planning_policy.source_structure_mode` is `locked`, every section-divider and content page declares `source_heading_ids` and one `primary_source_heading_id`. The primary ID must appear in `source_heading_ids`; every ID must exist in `source_heading_outline`. The page title matches the primary source heading after only mechanical numbering normalization. A capacity split may append `（一）`, `（二）`, and so on, but may not replace the source heading with a newly invented judgment. Multiple source IDs are permitted when duplicate source content is consolidated, while the primary heading remains the page's title and order owner.

The locked agenda page uses the source agenda title recorded in `source_metadata.agenda_title`, defaulting to `目录`. It may not be renamed as a problem path, communication path, or interpretive judgment. Primary source-heading order must be nondecreasing; repeated primary IDs are permitted only as capacity splits or duplicate-content consolidation.

When an outline workpack exists, `deck-brief.json.workpack_binding` must match the workpack request and planning-policy hashes, and `task_understanding.writing_style_mode` / `source_structure_mode` must match the workpack policy. The validator rejects semantic inputs changed after workpack preparation. Projects without an `outline-workpack.json` retain the legacy structural validation path.

The strengthened v0.5 `page-plan.json` contract uses `schema_version: 1.1`. `ppt-outline.md` is generated from validated JSON and is a human view, not an independent authority.

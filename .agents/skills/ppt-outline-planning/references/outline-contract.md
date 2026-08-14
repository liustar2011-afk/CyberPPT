# Layer-Four PPT Outline Planning Contract

Layer four turns a validated semantic foundation into a stable deck architecture and page-authoring boundary contract. It decides what the PPT must prove, how the argument is sequenced, what each page must accomplish, and what each page must not absorb from neighbors. It does not write final slide copy.

Required semantic inputs are `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, `argument-chain.json`, and `semantic-report.json` with `status: ok`.

Every content page defines `title_intent`, `page_mission`, `audience_question`, `key_judgment`, `non_substitutable_value`, `judgment_basis`, `argument_role`, page evidence, one governing `argument_chain`, `evidence_roles`, non-empty `must_not_include`, `reserved_for_later`, `split_risk`, transitions, content strategy and abstract visual logic.

Evidence responsibilities are `claim`, `reason`, `instance`, `boundary`, and `trace_only`. One evidence ID may have only one page-level responsibility. Every content page must name at least one direct `normalized_fact_id`; relation IDs and argument-node IDs cannot replace direct source-grounded facts.

`source_explicit` follows explicit source support. `source_synthesis` consolidates source-supported items without a new factual claim. `planning_inference` requires `inference_rationale`. Any cited layer-three inferred relation requires `evidence.inference_note`.

The planner may reorder arguments, consolidate duplication, split overloaded source sections, combine source sections only when they support one judgment, and bridge a logic gap only as labeled planning inference. It may not invent source facts or upgrade inference strength.

The strengthened v0.5 `page-plan.json` contract uses `schema_version: 1.1`. `ppt-outline.md` is generated from validated JSON and is a human view, not an independent authority.

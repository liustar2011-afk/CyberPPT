# Layer-Four PPT Outline Planning Contract

Layer four turns a validated semantic foundation into a stable deck architecture and page-authoring boundary contract. It decides what the PPT must prove, how the argument is sequenced, what each page must accomplish, and what each page must not absorb from neighbors. It does not write final slide copy.

Required semantic inputs are `normalized-facts.json`, `concept-base.json`, `relation-graph.json`, `argument-chain.json`, and `semantic-report.json` with `status: ok`.

Every content page defines `title_intent`, `page_mission`, `audience_question`, `key_judgment`, `non_substitutable_value`, `judgment_basis`, `argument_role`, page evidence, one governing `argument_chain`, `evidence_roles`, non-empty `must_not_include`, `reserved_for_later`, `split_risk`, transitions, content strategy and abstract visual logic.

The root authoring status is a real gate, not descriptive metadata. A deterministic producer must leave `editorial_authoring_status` at `mechanical_draft`. Only after page-level editorial decisions are complete may it set `author_edited`; at that point every content page must include a judgment derivation, structured `excluded_from_onscreen` items (`source_refs` plus a reason), and `authoring_decisions.deletion_test` / `authoring_decisions.evidence_selection`. `key_judgment` is canonical; a compatibility `core_message` must match it exactly. Pages whose source title begins with `附件` must also declare `authoring_decisions.attachment_disposition`; promoting one to `main_deck` requires a business-judgment rationale.

Evidence responsibilities are `claim`, `reason`, `instance`, `boundary`, and `trace_only`. One evidence ID may have only one page-level responsibility. Every content page must name at least one direct `normalized_fact_id`; relation IDs and argument-node IDs cannot replace direct source-grounded facts.

The outline root may declare `fact_dispositions` for important normalized facts that need an explicit cross-page decision:

```json
[
  {"normalized_fact_id":"nf-005","disposition":"deferred_to","deferred_to":"p11","rationale":"后页承接该事实。"},
  {"normalized_fact_id":"nf-007","disposition":"page","page_ids":["p05"],"rationale":"明确由 p05 承接建设背景中的平台基础。"},
  {"normalized_fact_id":"nf-022","disposition":"shared","page_ids":["p10","p12"],"rationale":"两页分别承担服务定义与重点方向。"}
]
```

`page` and `shared` declarations must match the plan's direct page evidence. `detail` and `trace` retain a fact without promoting it to a peer on-screen module. `deferred_to` must name an existing later page. `intentional_omission` must carry a rationale. Important facts without direct page evidence or one of these explicit dispositions block validation.

`source_explicit` follows explicit source support. `source_synthesis` consolidates source-supported items without a new factual claim. `planning_inference` requires `inference_rationale`. Any cited layer-three inferred relation requires `evidence.inference_note`.

The default planning policy is source locked and government-official. The planner preserves source chapter titles, content titles, source order, content coverage, and factual strength. It may split an overloaded source heading only for slide capacity and may consolidate genuinely duplicate content without changing its topic, conditions, responsibility, state, or source order. Reframing, renaming, or reordering requires an explicit user request. It may not invent source facts or upgrade inference strength.

When `outline-workpack.json.planning_policy.source_structure_mode` is `locked`, every section-divider and content page declares `source_heading_ids` and one `primary_source_heading_id`. The primary ID must appear in `source_heading_ids`; every ID must exist in `source_heading_outline`. The page title matches the primary source heading after only mechanical numbering normalization. A capacity split may append `（一）`, `（二）`, and so on, but may not replace the source heading with a newly invented judgment. Multiple source IDs are permitted when duplicate source content is consolidated, while the primary heading remains the page's title and order owner.

The locked agenda page uses the source agenda title recorded in `source_metadata.agenda_title`, defaulting to `目录`. It may not be renamed as a problem path, communication path, or interpretive judgment. Primary source-heading order must be nondecreasing; repeated primary IDs are permitted only as capacity splits or duplicate-content consolidation.

When an outline workpack exists, `deck-brief.json.workpack_binding` must match the workpack request and planning-policy hashes, and `task_understanding.writing_style_mode` / `source_structure_mode` must match the workpack policy. The validator rejects semantic inputs changed after workpack preparation. Projects without an `outline-workpack.json` retain the legacy structural validation path.

The strengthened v0.5 `page-plan.json` contract uses `schema_version: 1.1`. `ppt-outline.md` is generated from validated JSON and is a human view, not an independent authority.

正式生成器还要求每个内容页声明 `primary_argument_node_id`、`source_argument_node_ids`、`source_evidence_node_ids`、`source_argument_node_roles`、`source_argument_node_weights`、`source_argument_node_statuses` 和 `core_message_derivation.argument_node_ids`。这些字段把页面绑定到层三论点链；`concept_ids` 与 `relation_ids` 必须分别解析到 `concept-base.json` 和 `relation-graph.json`，关系所引用的事实不得超出页面直接事实范围。

根层状态分为结构校验、来源绑定、作者化和交接资格。候选 `mechanical_draft` 可以得到结构 `status: ok`，但 `gates.handoff_status` 必须为 `blocked`。作者编辑完成且校验通过后，才可进入 handoff。附件默认 `trace_only`，主稿升格必须有作者处置和业务判断理由。页面预算和合并组属于作者化规划约束，生成器不得仅依据页数自动合并源主题。

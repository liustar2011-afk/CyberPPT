# Semantic Guardrails v0.4.2

## Purpose

Keep analytical depth while preventing source-faithful analysis from drifting during UNDERSTAND, PLAN, AUTHOR, or final delivery.

These guardrails do not add a new stage or authority. They constrain the existing:

`foundation.json → deck-plan.json → final-script.md`

## 1. PLAN semantics bind AUTHOR

AUTHOR may improve wording, hierarchy, compression, examples, and presentation flow, but must preserve the semantic relationship selected in PLAN.

Examples:

- PLAN `classification / taxonomy` → AUTHOR may use grouping, comparison, coverage, or role differentiation; it may not invent a progression chain.
- PLAN `progression / maturity` → AUTHOR may show sequence only to the degree supported by the source.
- PLAN `inferred` → AUTHOR may state the analysis, but may not strengthen source certainty, add a new necessary condition, or introduce an unsupported baseline comparison.

If AUTHOR discovers that PLAN selected the wrong relationship, repair `deck-plan.json` first and re-run the plan audit. Do not silently reinterpret the page while writing.

## 2. Internal-source visibility is deterministic

Text carrying markers such as `内部测算`, `内部参考`, `仅供内部`, `内部口径`, or `内部审批` is treated as `internal_only` even when an LLM mistakenly labels it `external_ok`.

For an `external` deck:

- internal-only facts/numbers may be used as hidden support only when the page explicitly records `internal_only_used_as_hidden_support`;
- the internal number, ratio, formula, or wording must not appear in the final audience-facing script;
- explicit user approval is required for deliberate exposure.

## 3. Group-strength preservation

A claim about a set (`均`, `全部`, `所有`, `每个`, `都已`) inherits the weakest member evidence.

Before writing a group-level predicate such as:

- `均具有长期积累`;
- `全部已完成`;
- `每个方向均已具备`;

check every supporting member. If one member has a weaker status, rewrite the group claim so that the distinction survives.

## 4. Optionality preservation

When the source says two things at once, both must survive:

`可以独立采用 + 可以逐步深化`

Do not compress this into a single maturity ladder or mandatory upgrade path.

The same rule applies to `按需组合`, `可分别采用`, `可单独实施`, and similar source-side choice structures.

## 5. Classification is not progression

A source taxonomy is a valid analytical result.

Do not create arrows or words such as `依次递进`, `起点`, `进一步加工`, `单向演进`, or `由浅入深` unless PLAN/source evidence actually supports progression.

A better PPT structure may be:

- classification;
- matrix;
- parallel capability system;
- common framework + differentiated functions;
- coverage relationship.

## 6. Baseline-required judgments

Comparative judgments require both sides of the comparison.

Do not write:

- `当前距离目标还有很大缺口`;
- `显著超出现有水平`;
- `明显不足`;
- `大幅提升`;
- `显著领先`;

when the source provides only a target, future value, or one side of the comparison.

Targets may support statements such as `仍需持续扩大供给` when the source itself makes that implication. Prefer `合作空间 / 参与需求 / 新增资源供给需求` over an unmeasured `缺口` when no current baseline exists.

## 7. Chapter-title fidelity

When `source_structure_mode = preserve`, chapter pages use the source chapter title after removing mechanical numbering (`第一章`, `第二章`, etc.).

Within a chapter, content-page titles may be PPT-optimized.

## 8. Analysis labels stay internal

Evidence grade and reasoning taxonomy are machine/authoring metadata:

- `explicit / inferred / speculative`;
- `problem-to-response mapping`;
- `classification / taxonomy`;
- `progression / maturity`;
- `risk-control-protection`;
- similar internal reasoning-model names.

They may remain in Foundation, PLAN, Critic diagnostics, or the machine-readable JSON mirror. Canonical `final-script.md` renders them as clean Chinese semantic labels or omits them from relation annotations.

A delivery relation should read:

`行业资源分散 → 行业节点：问题回应`

not:

`行业资源分散 → 行业节点：问题到响应映射（inferred，源文未逐一显式配对）`.

## 9. Guardrail commentary stays internal

Do not explain to the final reader why a sentence was written defensively.

Remove phrases such as:

- `源文未逐一显式配对`;
- `这是分析性归纳`;
- `这一区别需要如实保留`;
- `不宜为追求页面整齐而抹平`;
- `两层含义均须保留`.

State the business distinction directly. The guardrail belongs in Critic/audit, not in the business prose.

## 10. Page navigation stays out of audience-facing copy

`上一页 / 下一页 / 本页展示 / 第X页 / 后续页面` may appear in `mission` because mission is script workflow metadata. They must not appear in `full_copy`, onscreen copy, visual semantics, relationships, or speaker notes.

After split, merge, deletion or renumbering, re-read the affected page set. Old references such as `进入下一页`, `前三步`, `后三步` are stale-state defects even when the underlying content is still correct.

## 11. Renderer boundary

`dist/final-script.md` is the canonical Stage 02 boundary. `dist/final-script.json` is a machine-readable mirror and may retain internal analysis labels needed for diagnostics.

The renderer:

- maps internal `argument.pattern` labels to short Chinese semantic labels;
- removes evidence-grade annotations from relationship text;
- removes common legacy page-navigation and Critic-commentary residue;
- preserves business facts, source refs and paragraph structure.

Renderer cleanup is a compatibility/safety net. AUTHOR should write clean prose first.

## 12. Required audits

Before final delivery run:

```bash
cyberppt-script audit-foundation <foundation.json>
cyberppt-script audit-plan <deck-plan.json> <foundation.json>
cyberppt-script audit-final <final-script.json> <deck-plan.json> <foundation.json>
cyberppt-script lint <final-script.json>
cyberppt-script check-refs <final-script.json> <foundation.json> [--source-index <source-index.json>]
cyberppt-script render-stage02 <final-script.json> --output dist/final-script.md
```

`lint` checks both JSON-level writing/structure and rendered Markdown cleanliness. `render-stage02` refuses to write when the canonical Markdown still contains a delivery-cleanliness violation.

A failed semantic or delivery audit is a rewrite trigger. Do not deliver the script as complete until the relevant issue is repaired.

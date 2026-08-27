# Script Quality Rubric v0.4.2

Use this rubric in PLAN self-review and AUTHOR Critic. Repair the same draft; do not create a competing final script.

Read `docs/SOURCE_FIDELITY_AND_ANALYSIS.md` and `references/semantic-guardrails.md` first.

## 1. Deck-level quality

### Source-structure fidelity

The deck preserves the source chapter set, order and themes unless the user explicitly authorized restructuring.

### Source-preserving continuity

The plan explains the logic already embedded in the source order and improves transitions without silently replacing the source's content strategy.

### Coverage

Source-critical claims, constraints, numbers, responsibilities, status, rights and boundaries are represented, intentionally reserved, or explicitly excluded for a user-approved reason.

### Analytical depth

The deck surfaces defensible latent relationships inside the source rather than merely copying Word bullets into slide bullets.

### Non-duplication

Repeated pages or modules add a distinct analytical role or should be merged within source boundaries.

### Content-load rhythm

Information load varies when useful, without driving chapter reordering or source-content deletion.

### Final-facing cleanliness

The canonical `final-script.md` contains business content and delivery semantics only. Internal evidence grades, analytical-model names, Critic commentary and stale page-navigation language stay outside the canonical Markdown boundary.

## 2. Chapter-level quality

A chapter passes when:

- it corresponds to the source chapter unless restructuring was authorized;
- its internal pages cover the chapter's source-critical sections;
- its pages expose useful classifications, tensions, mechanisms, mappings or synthesis where supported;
- it preserves explicit source order, optionality and boundaries;
- its final page or transition naturally hands off to the next source chapter without requiring page-number commentary in audience-facing prose.

## 3. Page-level quality

1. **Source scope** — the page identifies the source section(s) from which it is derived.
2. **Structural operation** — preserve / split / merge_within_chapter / user_authorized_cross_chapter is explicit when useful.
3. **Primary question** — one main audience question is resolved.
4. **Core message** — a complete bounded answer or judgment is stated.
5. **Analytical value** — the page improves explanation through classification, tension, mechanism, mapping, interaction, transformation, evidence synthesis or another defensible structure when available.
6. **Relation basis** — material analytical relations are explicit or inferred with support.
7. **Evidence adequacy** — facts and boundaries support the wording used.
8. **Specificity** — concrete objects, actions, responsibilities, mechanisms, conditions and outcomes replace empty abstraction.
9. **Hierarchy** — title, subtitle, core message, modules and details have distinct jobs.
10. **Onscreen economy** — visible text preserves material distinctions without becoming Word prose.
11. **Semantic visualizability** — Stage 02 receives valid objects and relationships, including taxonomy when taxonomy is the correct relationship.
12. **Source fidelity** — no new fact, unsupported current state, group-wide overgeneralization, necessary condition, causal mechanism, status or policy strength is introduced.
13. **Audience visibility** — internal-only or restricted material is handled according to audience scope.
14. **Delivery cleanliness** — evidence grades, source-audit explanations and page-navigation commentary do not leak into audience-facing fields.

## 4. Core tests

### Source-structure test

Compare plan chapters with `foundation.source_structure`. Cross-chapter reordering or movement requires explicit user authorization.

### Section-coverage test

Every source-critical section is assigned, reserved, or explicitly excluded.

### Single-question test

If one page answers independent questions with different proof chains, split or refocus it.

### Relation-basis test

For every material relationship ask: explicit, inferred, or speculative? Keep explicit/inferred; remove speculative. The evidence grade itself remains internal and is not rendered to canonical Markdown.

### Inference-boundary test

Reject analysis that introduces a new fact, ranking, number, forecast, necessary condition, universal claim or commitment.

### Group-strength test

A group claim cannot exceed the weakest member's support unless exceptions are stated.

### Classification-vs-progression test

Peer categories remain peer categories unless source facts support sequence, maturity or dependency.

### Optionality-preservation test

If modes may be independently selected and also progressively deepened, both meanings must survive compression.

### Audience-exposure test

For external audiences, `internal_only` material cannot enter final-facing prose without explicit approval.

### Analysis-depth test

If a page is only a one-to-one conversion of source bullets, test whether a supported analytical model can improve it. Do not force a relationship when taxonomy or parallel classification is already the correct structure.

### Evidence test

Every strong page message identifies how it is established.

### Compression-loss test

Important qualifiers, responsibilities, numbers, rights and distinctions must survive in the correct layer.

### Continuity test

If adjacent pages feel disconnected, strengthen the bridge or page argument first. Reordering across source chapters is not a default repair.

### Thesis-voice test

`core_message` and `visual_thesis` must state the page's actual judgment — the claim the audience should accept or reject — not describe how the author arrived at it. A sentence whose grammatical subject is an analytical action or artifact (识别起点、筛选标准、判断依据、分析框架、归纳结论) rather than a business subject (紫金云、首期MVP、交易员岗位、投入上限) is process narration wearing a thesis's clothes, even without any explicit/inferred/speculative label. Self-test: read the sentence aloud to the decision-maker it is written for — do they receive a business judgment they can act on, or a description of the method that produced one? Only the former passes. `contracts/banned-phrasing.json`'s `analysis-process-as-thesis` rule catches the clearest cases mechanically; less regular phrasing still needs Critic judgment.

### Echo test

Title, subtitle, core message and module headings must perform different roles.

### Count-claim test

When a title/subtitle/core message declares a count, the visible peer modules must match the counted set. Addendum material should be visibly separated.

### Delivery-cleanliness test

Render the canonical Markdown and verify it does not contain:

- `explicit / inferred / speculative`;
- internal model names such as `problem-to-response mapping` or `classification / taxonomy`;
- source-audit/Critic phrases such as `源文未…`, `分析性归纳`, `需要如实保留`;
- audience-facing `上一页 / 下一页 / 本页展示 / 第X页 / 后续页面` navigation.

`页面使命` may describe the page's workflow role because it is script metadata. The ban applies to audience-facing copy, visual semantics and spoken notes.

### Structural-change stale-reference test

After split, merge, deletion or renumbering, re-read every affected page's `full_copy`, `speaker_notes`, `visual_thesis` and relationships. Any reference to an old page boundary, old half-page split (`前三步/后三步`) or a page that no longer exists is a hard rewrite trigger.

### Process-voice test

Same check as the Thesis-voice test above, run at delivery time against the rendered Markdown's `核心结论` line and any visual-thesis text carried into it: the sentence must commit to a judgment, not describe the identification/screening/synthesis work that produced one.

### Argument-label rendering test

Internal `argument.pattern` values may remain machine-oriented in JSON, but canonical Markdown must render a short Chinese semantic label (`问题回应 / 分类结构 / 演进路径 / 风险保障 / 推进流程` etc.). Unknown English model names must not pass through to the delivery boundary.

## 5. Rewrite triggers

Rewrite when:

- chapter order drifts from source without authorization;
- source material is silently front-loaded, delayed or deleted for a new communication strategy;
- a page is a shallow Word-bullet conversion despite available analytical depth;
- an inferred relationship lacks identifiable source support;
- a classification is converted into a process without evidence;
- a group-wide claim overstates one member's evidence;
- internal-only information appears in external-facing prose;
- a plausible implication is written as a source fact;
- `core_message` or `visual_thesis` narrates the analysis process (识别/筛选/归纳 as grammatical subject) instead of stating the judgment itself;
- title/message/modules echo each other;
- evidence-grade or analysis-model language appears in canonical Markdown;
- a structural edit leaves `上一页/下一页/前三步/后三步` residue in affected prose;
- speaker notes read as author instructions or page-navigation commentary;
- final text violates formal register or the mechanical lint rules.

## 6. Critic behavior

The Critic identifies root causes, chooses the smallest repair scope, rewrites in context, and re-runs the relevant tests. Hidden analysis and critique instructions stay out of the deliverable.

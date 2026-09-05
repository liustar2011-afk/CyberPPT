# Source Fidelity and Analytical Enhancement

## Product boundary

CyberPPT-Script is a source-faithful Word-to-PPT pagination and script compiler.

Its default responsibility is to preserve the source document's viewpoints, content boundary and chapter structure while converting the material into presentation-ready pages. Semantic understanding protects actors, facts, status, responsibility, numbers, conditions and explicit relationships; it does not create a stronger thesis for the source.

The governing principle is:

**Source controls viewpoints, content boundary and chapter order. Faithful authoring is the default. Analytical deepening requires explicit user intent. Stage 02 controls rendering.**

Deck Plan and Final Script use `authoring_mode`:

- `faithful` (default): paginate, group, reorder locally and clarify wording while preserving source-explicit propositions and relations. Parallel source statements may remain parallel. Do not add causality, necessity, implication, priority or value judgment merely to create a stronger page thesis.
- `analytical`: available only when the user explicitly requests analysis, insight, argument reconstruction or strategic deepening. Inferred relations remain visibly qualified and source-bounded.

## 1. Three-layer fidelity model

### Layer A — structure fidelity

By default preserve at the source-mapping layer:

- source chapter identity, coverage and order;
- chapter themes and explicit section hierarchy;
- source-defined emphasis and required sections;
- explicit sequences, stages, dependencies, classifications and boundaries.

Presentation chapters may group adjacent source chapters to improve oral
comprehension, provided the mapping covers every source chapter exactly once and
keeps source order. Cross-source reordering, front-loading, deletion or content
strategy change requires explicit user authorization.

### Layer B — semantic fidelity

Protect without semantic drift:

- facts and numbers;
- dates and status;
- actors, responsibilities and authority;
- policy or commitment strength;
- conditions, exclusions, rights and restrictions;
- explicit sequence, causality, dependency and maturity conditions.

Compression may change wording. It must not change meaning or certainty.

At page level, `source_refs` defines the evidence boundary available to AUTHOR.
The author uses the page's core conclusion to restructure those source facts
without abstracting or summarizing away their substance. Full copy preserves
core facts, source-stated conclusions, actors, formal instruments,
implementation status, claim strength, dates, numbers, responsibilities,
conditions and boundaries; it may reorder material, merge repetition and omit
only subordinate content that does not support the page conclusion. The main
compression and display selection occurs when full copy is projected into
onscreen copy. The visible layer keeps the conclusion and decisive evidence
instead of shrinking every source detail proportionally. Deck-level structure
and source-declared priorities still require coverage; page-level evidence
selection does not authorize dropping a source chapter or weakening a material
boundary.

### Layer C — analytical enhancement (explicit opt-in)

When `authoring_mode: analytical` is explicitly authorized, the engine may improve expression depth by identifying latent relationships supported by the source facts, including:

- tension and problem structure;
- cause and mechanism;
- problem-to-response mapping;
- resource-to-product/value transformation;
- actor-responsibility interaction;
- capability hierarchy;
- maturity progression;
- risk-control-protection logic;
- evidence synthesis and value formation.

Analytical enhancement is valid only when it can be traced to source facts without importing a new external fact or assumption.

## 2. Relation basis

Every material relation used for analysis should be classified internally as one of:

- `explicit` — the source directly states the relationship;
- `inferred` — multiple source facts support the relationship without requiring an external assumption;
- `speculative` — the relationship requires an unstated premise, new fact or unsupported generalization.

`speculative` relationships are excluded from authoritative `foundation.json` relations and from final-script argument chains.

An `inferred` relation should record support fact IDs and a confidence level. Inference can strengthen explanation, but it cannot strengthen the underlying factual claim.

PLAN 的 `title`、`question` 和 `logic` 虽然不承担 AUTHOR 的最终判断，仍属于用户可见的规划表达。内容页审计应以该页 `source_refs` 对应的 Foundation 文本为证据范围，阻断证据中不存在的高风险确定性、完成度、协同、因果或主体角色升级。问题句中的高风险表达以及建议、拟议、待确认和规划事项的标题边界进入人工 Critic 提醒；确定性检查只处理高置信词面升级，不承担完整语义蕴含判断。

## 3. Source structure authority

`foundation.json.source_structure` records the source hierarchy. PLAN preserves
it as the traceability boundary and projects it into fewer presentation chapters
when the formal deck benefits from grouping.

Allowed page-level transformations without separate user permission:

- `preserve` — keep the source section as one presentation unit;
- `split` — split one source section into several pages;
- `merge_within_chapter` — merge closely related material within the same source chapter when distinctions remain intact.

Allowed presentation-level transformation without separate user permission:

- `group_adjacent_source_chapters` — place adjacent source chapters under one
  presentation chapter while retaining source order, page scopes and argument
  bindings.

`user_authorized_cross_chapter` is allowed only when the user explicitly requests a structural re-plan.

## 4. Audience role

Audience information may control:

- explanation depth;
- terminology and examples;
- onscreen density;
- which source details are appropriate to expose;
- speaker-note emphasis.

Audience information does not, by default, authorize chapter reordering or a new content strategy.

For internal and mixed audiences, the default authoring position is an internal
expert accountable to the organisation's facts, responsibilities and operating
conditions. Customer, market, transaction, value realisation, growth and
commercialisation remain legitimate source-grounded enterprise topics. External
consultant address (`贵司`), declared consulting viewpoint and unsupported generic
advice are voice drift; business vocabulary itself is not evidence of drift.

Use `visibility` to protect source items:

- `external_ok` — may appear in external-facing material;
- `internal_only` — keep out of external-facing copy unless the user explicitly approves;
- `restricted` — requires explicit handling decision;
- `unspecified` — no special visibility classification has been made.

## 5. Analytical depth requirement

In `faithful` mode, accurate pagination and source-faithful synthesis are successful outputs; the Critic must not demand an extra analytical thesis. In `analytical` mode, the engine should test whether deeper source-supported structure is available.

When a source section contains several material facts, PLAN/AUTHOR should test whether one or more of the following can be made explicit:

- classification;
- common driver or tension;
- causal or enabling mechanism;
- correspondence;
- actor interaction;
- transformation path;
- evidence-to-judgment relationship;
- risk-to-control relationship;
- value formation.

If the page simply maps Word bullets to PPT bullets, the Critic should test whether a deeper source-supported structure is available.

## 6. Inference boundary

Allowed analytical output:

- reorganizes or interprets existing facts;
- makes a source-supported relationship explicit;
- creates a bounded synthesis from several facts;
- creates a page judgment whose strength does not exceed its support.

Disallowed analytical output:

- introduces a new factual state, number, ranking or commitment;
- converts a sufficient condition into a necessary condition;
- converts classification into sequence without support;
- converts temporal adjacency into causality;
- converts one member's evidence into a group-wide claim;
- exposes internal-only material to an external audience by default.

## 7. Stage boundaries

The authoritative artifact chain remains:

`source -> foundation.json -> deck-plan.json -> final-script.md`

No additional semantic authority, storyline file, reasoning file, evidence-plan file or user gate is introduced by this policy.

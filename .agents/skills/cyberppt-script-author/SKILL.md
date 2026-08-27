---
name: cyberppt-script-author
description: Author a complete PPT script from foundation.json and an approved source-constrained deck-plan.json. Preserve approved source scope and fact boundaries, turn explicit/inferred analysis into strong page arguments, compress them into PPT-ready onscreen copy, run whole-deck Critic and rewrite, and deliver renderer-independent final-script.md.
---

# AUTHOR

## Mission

Turn the approved source-constrained plan into a source-faithful, analytically strong, presentation-ready script.

Read:

- `docs/SOURCE_FIDELITY_AND_ANALYSIS.md`;
- `references/semantic-guardrails.md`;
- `references/analysis-models.md`;
- `references/evidence-architecture.md`;
- `references/argument-patterns.md`;
- `references/script-quality-rubric.md`;
- `references/screen-copy-authoring.md`.

## 1. Page contract

Before prose, know:

1. `source_scope` — source section(s) that control the page;
2. **page job** — one primary question;
3. **answer** — bounded `core_message`;
4. **analysis basis** — explicit or inferred relation and its supports;
5. **proof** — facts, mechanisms, numbers and boundaries that earn the answer;
6. **bridge** — how the next source-derived page follows.

When the plan declares `content_route`, use it to arrange the page for internal
reporting. The default sequence is **结论 → 证据 → 解读 → 含义 → 来源**:

- keep the page judgment visible first;
- prove it with the approved source facts and boundaries;
- explain only declared or defensibly inferred relationships;
- express “含义” as a source-grounded internal impact, attention point, work
  requirement, coordination item, risk reminder, or next arrangement;
- keep “来源” in `source_refs` and traceability fields, outside onscreen copy.

This is a composition order, not a fixed external-consulting template. Do not
add a generic “含义” card, and do not upgrade a state, diagnosis, or system page
into an action conclusion. `content_route` does not override `argument_role` or
the approved `page_logic_contract`; when it is `source_native`, preserve the
source's own structure.

When a page carries `stage02_readiness`, preserve its declared complete sentence
signals and container headings verbatim enough for deterministic matching. Do
not turn it into Stage 02 layout instructions: it records what later rendering
must preserve, while Stage 02 decides geometry and verifies the actual output.

If the plan lacks a defensible analysis basis, repair the page plan before polishing copy.

## 2. Whole-deck pass

Read the entire Foundation and approved plan. Preserve approved source chapter order and source scopes. Establish continuity by explaining the source's existing progression; do not redesign chapter strategy unless the plan is explicitly `user_authorized_restructure`.

## 3. Chapter pass

Within each source chapter, identify the dominant page-to-page logic and keep each page's source responsibility distinct. Use latent relationships already validated in Foundation/PLAN.

## 4. Page proof chain

Useful default:

`bounded answer -> supporting claims -> evidence / inferred mechanism / boundary -> implication`

A page may instead use taxonomy, matrix, hierarchy or parallel dimensions when those are the correct source-supported relationships.

### Inferred relation rule

An inferred relation is allowed when:

- support fact IDs are identifiable;
- no external premise is required;
- wording does not strengthen the underlying facts;
- the relationship is useful to explanation.

Never silently convert inferred analysis into a statement that the source explicitly declared the relationship.

## 5. Full page writing

For each content page write:

1. `mission`;
2. `core_message`;
3. `argument`;
4. `full_copy`;
5. `onscreen`;
6. `visual_thesis`;
7. `relationships`;
8. `speaker_notes`;
9. `source_refs`.

### Thesis-voice rule

`core_message` and `visual_thesis` state the page's judgment itself — the claim the audience should accept or reject — never how it was derived. A sentence whose grammatical subject is an analytical action or artifact (识别起点、筛选标准、判断依据、分析框架) instead of a business subject is process narration wearing a thesis's clothes, even when it never uses a labeled evidence grade. Self-test: read the sentence to the decision-maker it is written for — do they receive a judgment they can act on, or a description of the method that produced one? `contracts/banned-phrasing.json`'s `analysis-process-as-thesis` rule catches the clearest cases mechanically; write clean prose rather than relying on it.

### Full-copy policy

`full_copy` should:

- answer the page question early;
- make the reasoning visible;
- explain how facts relate rather than merely list them;
- preserve status, qualifiers, optionality and rights;
- use 2–4 argument-beat paragraphs for standard/dense pages;
- finish on an earned implication or bridge stated as business content.

Analytical writing may reorganize facts and draw supported interpretations. It may not add a new fact, unsupported current state, ranking, forecast, necessary condition or commitment.

When the approved page declares `source_consumption.mode: strict`, treat
`source_refs` as the assigned source inventory. Write every ref into `full_copy`
unless PLAN classifies it under `detail_refs` or a specifically reasoned
`intentional_omissions` entry. Preserve each declared `full_prose_anchors`
threshold. This is a semantic-consumption rule: combine related records into a
coherent argument and retain their objects, conditions, responsibilities,
numbers, and source strength; do not paste one sentence per ref mechanically.

Do not explain the writing process to the reader. Phrases such as `源文未逐一显式配对`, `分析性归纳`, `需要如实保留`, `不宜为追求页面整齐而抹平` belong to Foundation/PLAN/Critic diagnostics, not final prose.

Do not navigate the document inside audience-facing prose. `上一页 / 下一页 / 本页展示 / 后续页面 / 第X页` belong to workflow metadata, not `full_copy`, `onscreen`, `visual_thesis`, `relationships` or `speaker_notes`.

### Group-strength rule

Before a group-wide phrase such as `均已形成`, `全部具备`, `共同构成必要条件`, verify every member. Use the lowest common supported strength or state exceptions.

### Classification/progression rule

Do not convert peer categories into a flow, hierarchy or maturity chain unless the source or a supported inference establishes transition/dependency. Taxonomy is a valid consulting-style structure.

### Optionality rule

If the source says modes may be adopted independently and may also deepen progressively, preserve both meanings.

### Audience visibility

For `audience_scope: external`, do not place `internal_only` material in `core_message`, `full_copy`, `onscreen`, `speaker_notes` or visual semantics unless the plan records explicit user approval. Internal-only evidence may remain hidden support.

## 6. Onscreen-copy policy

Compress only after full copy is sound.

Use the reference rules in `../../../references/screen-copy-authoring.md`. When
the plan declares `onscreen_composition: evidence_first`, keep the page judgment
in `core_message` and write every module as a heading plus source-grounded
evidence items; do not write module `text`. When it declares
`selective_lead`, use module `text` only for distinct source-grounded judgments
and never exceed its `lead_budget`. A plan without this optional policy may use
the normal expression-mode guidance. Do not place terminal punctuation or symbols
on any visible module heading, lead line, or item; the module boundary supplies
the visual pause. Shortening must remove redundancy, not the subject, predicate,
state, condition or business relationship that makes the claim readable.

For `evidence_first`, do not demote a former module lead by placing it as the
first `items` entry. Flat evidence items render at the same level, so every item
under a module must answer the same evidence question at comparable granularity.
Use peer objects, requirements, stages, actors, conditions, or factual results.
When one judgment must govern lighter supporting details, select `selective_lead`
in the plan and keep the judgment in the permitted `text` field.

If the approved page plan contains `onscreen_contract`, treat it as the visible
module contract: preserve the declared relation and module-heading order, keep each
module within its declared evidence scope, retain required signals, and remove
forbidden cross-scope or role content. A `parallel` contract describes a shared
dimension; it does not require equal detail counts or identical wording. Do not
turn a parallel contract into a progression chain through arrows, temporal words or
step language unless the approved plan declares that relation.

Before AUTHOR, require the approved Deck Plan to declare
`evidence_fit_review_mode: strict` and pass `audit-plan`. Do not treat a free-form
Critic explanation as proof that sources fit: page and module reviews must bind
every assigned `evidence_ref` and finish with `verdict: keep`. Any `topic_only`,
`no`, `uncertain`, `rename`, `move`, `split` or `reject` state returns the work
to PLAN. A `counter_case` is optional — write one only when it changes your
`fit`/`verdict` call; it is not machine-checked and not required to pass
`audit-plan`.

Challenge the inherited grouping again before finalizing onscreen copy. For each
module, ask what single question the heading poses, whether every child answers
it, whether siblings have compatible semantic roles, which source ref supports
each answer, and whether paragraph co-location was mistaken for hierarchy.
`No` or `uncertain` requires a PLAN repair before polishing copy. Do not use
AUTHOR wording to conceal an invalid parent-child relation. Keep the
question-and-answer reasoning in Critic; deliver only the repaired script and
deterministic issue codes.

When `source_consumption.onscreen_refs` is present, compress only those selected
representative records into the visible modules mapped by
`onscreen_contract.modules[].evidence_refs`. Their `required_signals` are the
deterministic visible proof. Other fully consumed records may remain in
`full_copy`, speaker explanation, or traceability; they do not become onscreen
items merely because they were assigned to the page.

- Use concrete nouns, numbers, actors, conditions and distinctions.
- In project-positioning, capability, task, responsibility and validation-scene
  groups, do not leave child items as names alone. Write `label: object / role /
  task / boundary` using approved evidence or the approved page relationship,
  for example `绿色低碳：检验标准在该类业务中的适用性`. Keep the colon and omit
  terminal punctuation. A label-only list is allowed only when PLAN explicitly
  declares `detail_policy.label_only_allowed: true` because the source contains
  names without item-level detail.
- Give each permitted `sentence_led` lead module at least one readable
  proposition; use `mixed` when a page needs both sentence-like lead lines and
  compact evidence details.
- Treat preferred character bands as layout guidance, not as a reason to delete
  meaningful syntax. A complete proposition may be longer than a compact phrase
  when it remains one source-grounded sentence and fits the downstream gate.
- Choose the number of semantic modules from the distinct evidence and business meanings the page must carry; no fixed module count is a quality target.
- Do not add a module whose entire content is commentary on how the page's other modules relate to each other — that restates them under a "关系/相互关系/对应关系" heading without a new fact. The relationship itself belongs in `visual_thesis`/`relationships`, not a bonus onscreen card (`../../../references/screen-copy-authoring.md` section 5b). When the source-grounded content is complete, mark genuinely thin source material as `content_load: light` rather than inventing one.
- Do not mechanically map every Word bullet into a card.
- Do not thin a concrete claim into generic labels.
- Keep source refs/citation codes outside onscreen content.
- Ensure title/subtitle/core message/modules form a real hierarchy rather than repetition.

## 7. Visual semantics

`visual_thesis` states the page's judgment (see the Thesis-voice rule above); `relationships` describes the semantic structure that supports it — the two are not the same job, and `visual_thesis` must not collapse into a structure description either.

Every material arrow/dependency must be explicit or inferred with support. If the correct source structure is classification, use grouping/taxonomy semantics instead of arrows.

Evidence grades (`explicit / inferred / speculative`) stay in Foundation/PLAN or machine diagnostics. Do not write them into `visual_thesis`, `relationships.relation`, onscreen copy or speaker notes.

Do not specify fonts, colors, images, layout coordinates or Stage 02 style decisions.

## 8. Default register

Unless the user specifies another house style, use formal Chinese government / central-enterprise report register throughout audience-facing fields.

Prefer direct institutional wording and concrete objects/mechanisms. Avoid literary slogans, consulting-marketing hooks, casual commentary, author-facing instructions and self-reference to page numbers.

Write from an internal expert's position: state the organisation's operating
facts, customer and market conditions, responsibilities, mechanisms, constraints
and next arrangements with accountable subjects. Customer, market, transaction,
value realisation, growth and commercialisation language is permitted when the
approved plan and evidence support it. Do not address the organisation as `贵司`,
declare an external consultant viewpoint, or replace a supported business judgment
with generic advice to the enterprise.

`contracts/banned-phrasing.json` is the deterministic prose rule set. The `不是A，而是B` contrastive-reveal family and its configured variants are prohibited in final prose. Normative boundaries such as `不得`, `未经授权不得` remain valid when they state genuine source requirements.

### Title/subtitle

Use a short functional title (`总体架构`, `建设基础`, `合作价值`) and optional compact subtitle for business-specific content (`五层两贯穿`, `五方面基础`). Do not force every title to carry the full conclusion.

### Speaker notes

Write words a presenter can actually say aloud. No stage-direction labels, third-person `听众/受众`, page-navigation phrases (`这一页/下一页`), conditional presenter instructions or meta-description of the speech.

## 9. Whole-deck Critic

Run the tests in `script-quality-rubric.md`, especially:

- source-structure fidelity;
- section coverage;
- relation basis;
- inference boundary;
- group strength;
- classification vs progression;
- optionality preservation;
- audience exposure;
- analytical depth;
- evidence adequacy;
- compression loss;
- title/message/module echo;
- count claims;
- parent-child exhaustiveness, sibling semantic-axis consistency and source
  co-location mistaken for hierarchy;
- final-facing cleanliness;
- structural-change stale-reference checks;
- formal register and speaker-note quality.

### Analysis-depth requirement

If a page still reads as Word bullets copied into PPT modules, test an analysis model and rewrite when a defensible deeper structure exists.

### Inference ceiling

If an attractive analysis requires a new fact or unsupported premise, remove the link or weaken the conclusion. Analytical elegance never overrides evidence.

## 10. Rewrite

Repair the smallest correct scope. In source-preserve mode, prefer page/chapter-internal repair, better bridges and better analytical structure. Do not reorder source chapters as a default rewrite technique.

After any split, merge, deletion or renumber operation, re-read every affected page's `full_copy`, `speaker_notes`, `visual_thesis` and relationship text. Remove stale phrases such as `上一页`, `下一页`, `前三步/后三步`, or references to pages that no longer exist. A structural edit is incomplete until the affected prose is rewritten in its new context.

## 11. Final-facing cleanliness

The canonical delivery is `dist/final-script.md`. Internal analytical machinery must be invisible there.

Do not expose:

- evidence grades: `explicit / inferred / speculative`;
- internal model names such as `problem-to-response mapping`, `classification / taxonomy`, `risk-control-protection`;
- source-audit or Critic explanations such as `源文未…`, `分析性归纳`, `需要如实保留`;
- page-navigation commentary in audience-facing fields;
- stale pre-merge/pre-split references.

`argument.pattern` may retain an internal model label in `final-script.json`; the renderer converts it to a short Chinese delivery label such as `问题回应 / 分类结构 / 演进路径 / 风险保障 / 推进流程`.

Renderer cleanup is a final safety net for legacy or machine-facing annotations. AUTHOR should still write clean prose first; do not rely on the renderer to repair substantive writing quality.

## 12. Delivery validation

Before delivery run as applicable:

```bash
cyberppt-script validate final <final-script.json>
cyberppt-script audit-final <final-script.json> <deck-plan.json> <foundation.json>
cyberppt-script check-refs <final-script.json> <foundation.json> [--source-index <source-index.json>]
cyberppt-script lint <final-script.json>
cyberppt-script render-stage02 <final-script.json> --output dist/final-script.md
```

`lint` now checks both JSON prose/structure and the rendered Markdown delivery boundary. `render-stage02` refuses to write a canonical Markdown file when delivery-cleanliness checks still fail.

Also confirm the final script matches the approved source-constrained plan and contains no speculative relation or internal-only external leak.

## 13. Canonical delivery

Produce:

- `dist/final-script.md` — canonical Stage 02 boundary;
- `dist/final-script.json` — optional machine-readable mirror.

Required Markdown remains parser-compatible:

```markdown
## P08 页面标题

- 页面类型：内容页
- 页面标题：页面标题
- 页面副标题：可选
- 页面使命：页面在材料逻辑中的职责
- 核心结论：本页的完整判断
- 主论证链：问题回应｜A → B → C

### 完整文字稿
完整页面论证。

### 上屏文字
- 模块标题
  - 差异化细项

### 视觉结构
需要视觉化的真实语义关系或分类结构。

### 演讲者备注
可直接口播的补充内容。

### 内容来源
S1.1、S1.2
```

## Hard boundaries

- No speculative relation in formal argument or visual semantics.
- No silent source-chapter restructuring.
- No image-generation prompts or renderer styling.
- No PPTX geometry or Stage 02 state.
- No hidden reasoning, Critic monologue, evidence-grade label, analysis-model name or author instruction in `final-script.md`.

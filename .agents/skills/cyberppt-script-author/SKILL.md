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

- Use concrete nouns, numbers, actors, conditions and distinctions.
- Prefer 2–4 semantic modules unless the source mandates a larger counted set.
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

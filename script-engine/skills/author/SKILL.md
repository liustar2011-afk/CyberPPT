---
name: cyberppt-script-author
description: Author a complete high-quality PPT script from foundation.json and an approved deck-plan.json. Use as the primary whole-deck writing step. Work whole-deck first, then section by section, then page by page; critique and rewrite before delivery. Produce renderer-independent final-script.md and optional final-script.json. Do not generate images, choose visual styles, or assemble PPTX.
---

# AUTHOR

## Mission

Turn an approved deck plan into a coherent, source-faithful, presentation-ready script.

The default unit of authorship is the **whole deck**, not an isolated page.

## Inputs

- `foundation.json`;
- approved `deck-plan.json`;
- user writing constraints;
- `references/argument-patterns.md`;
- `references/script-quality-rubric.md`;
- `references/screen-copy-authoring.md`.

## Authoring sequence

### Pass 1 — Narrative

Read the complete plan before drafting pages.

Write an internal narrative brief that states:

- the deck's starting point;
- the final judgment or action;
- what each chapter contributes;
- the key transitions;
- where evidence or explanation must accumulate before a conclusion can be made.

Resolve deck-level repetition, missing bridges, and premature conclusions before page prose.

### Pass 2 — Section writing

Draft each chapter as a continuous argument.

For every page, determine:

- the exact audience question;
- the page's final answer;
- the dominant argument pattern;
- the minimum supporting claims and evidence required;
- what belongs on this page and what must remain on adjacent pages.

Use argument patterns as reasoning grammars. Do not force evidence into a preset layout.

### Pass 3 — Page writing

For every content page, write in this order:

1. `mission` — internal responsibility in the deck;
2. `core_message` — the final audience-facing judgment;
3. `argument` — pattern and reasoning chain;
4. `full_copy` — complete page argument in readable prose;
5. `onscreen` — presentation-ready hierarchy and concise copy;
6. `visual_thesis` — the semantic relationship that Stage 02 should make visually dominant;
7. `relationships` — meaningful object-to-object relations when useful;
8. `speaker_notes` — explanation that should be spoken rather than placed onscreen;
9. `source_refs` — traceability for material claims.

### Pass 4 — Whole-deck Critic

Review the entire deck using `references/script-quality-rubric.md`.

The Critic must diagnose root causes, including:

- weak or generic judgments;
- disconnected pages;
- duplicated page missions;
- evidence that does not prove the message;
- source-critical content that disappeared during compression;
- lists presented without a dominant relationship;
- premature conclusions;
- report-style paragraphs that have not been converted to presentation language;
- empty management wording;
- page titles or modules that repeat the body without adding hierarchy.

Do not create a competing second script. Produce rewrite instructions against the current draft.

### Pass 5 — Rewrite

Rewrite all affected sections and pages in context, not as isolated sentence edits.

After rewrite, read the deck linearly from beginning to end and verify that page order remains necessary.

### Pass 6 — Delivery validation

Validate that the final delivery:

- matches the approved deck plan unless an intentional improvement is documented;
- preserves material facts, boundaries, responsibilities, numbers, and source strength;
- answers every required audience question;
- has no unresolved duplicate page missions;
- contains renderer-independent visual semantics only;
- conforms to `contracts/final-script.schema.json` for the machine-readable mirror.

## Canonical delivery

Produce:

- `dist/final-script.md` — canonical human-readable script;
- `dist/final-script.json` — optional machine-readable mirror using contract `cyberppt.final-script` version `1.0`.

The Markdown script is the authoritative final content artifact unless the project explicitly chooses JSON as canonical.

## Required page structure in final-script.md

Each content page should contain:

```markdown
## P08｜页面标题

- 页面类型：...
- 页面使命：...
- 核心判断：...
- 主论证链：...

### 完整文字稿
...

### 上屏文字
- 模块标题：...
  - ...

### 视觉命题
...

### 关系
- A → B：...

### 演讲备注
...

### 来源追溯
- ...
```

Fields may be omitted only when genuinely inapplicable; do not add empty placeholders.

## Hard boundaries

- No image-generation prompts.
- No font, color, icon, photography, illustration, or style-preset instructions.
- No PPTX geometry or renderer coordinates.
- No Stage 02 build or QA state.
- No compatibility projections inside the authoring loop.

The output describes **what the page must communicate and which semantic relationship should be visually dominant**. Stage 02 decides how to render it.

# CyberPPT patterns adopted in v0.5

Inspection basis: `liustar2011-afk/CyberPPT` at commit `f9ce361653a4574f002665233a1099814947baf0` (2026-08-14).

## 吸收的机制

### 1. 页面成立条件与删除测试

Source: `.agents/skills/cyberppt-author-stage01-outline/SKILL.md` and `references/outline-authoring-contract.md`.

Absorbed into layer four:

- `audience_question` is separate from internal `page_mission`;
- `non_substitutable_value` forces a deletion/merge test;
- one governing `argument_chain` per page;
- `must_not_include` and `reserved_for_later` protect cross-page boundaries;
- evidence relevance is not treated as sufficient reason for onscreen display.

### 2. Evidence roles

Source: `.agents/skills/cyberppt-author-stage01-outline/SKILL.md` and `.agents/skills/cyberppt-write-single-page/SKILL.md`.

Absorbed roles: `claim`, `reason`, `instance`, `boundary`, `trace_only`. Layer four requires every page evidence ID to have exactly one responsibility. `trace_only` preserves auditability without becoming an onscreen module.

### 3. Atomic content units for downstream page writing

Source: `cyberppt/stage01_compiler.py`.

CyberPPT's downstream authoring benefits from structured `content_units` carrying `statement`, `source_refs`, `role`, `full_prose_required`, `coverage_anchors`, `argument_duties`, `onscreen_required`, and `onscreen_anchors`. The adapter deterministically generates these from layer-four `argument_chain` + `evidence_roles`; it does not ask a model to invent them again.

### 4. Page-script compiler expects an exact page contract

Source: `cyberppt/commands/compile_page_script_authoring.py`.

The compiler verifies page coverage and carries page fields into receipts. This motivates generating a CyberPPT-compatible `outline.json` instead of handing it an unrelated `page-plan.json` and hoping the page writer guesses the missing contract.

### 5. Human review should be a deterministic view

Source: `cyberppt/commands/outline_review.py`.

The adapter follows the same useful principle: human-readable outline review is rendered from the machine contract and is not an independent editable truth source.

## 明确不吸收的机制

### A. 不吸收“一次模型填超大语义合同”的上游方式

CyberPPT's `cyberppt/semantic_understanding.py` asks one semantic authoring pass to fill document semantics, every section/subsection node, relations, MECE rules, inference register, concept graph, source coverage and atomic items. The user's production experience indicates this Stage 00 quality is insufficient. v0.5 therefore keeps Source Material Foundation layers 1–3 as the reasoning authority.

### B. 不吸收由语义模型再投影 Source Truth 的权威链

CyberPPT's `cyberppt/stage01_compiler.py` deterministically compiles Source Truth from the semantic model's atomic items. Determinism cannot repair an upstream semantic misunderstanding. v0.5 projects Source Truth directly from validated `normalized-facts.json`, preserving layer-two evidence traces.

### C. 不吸收 compile-outline-draft 的页面决定

`cyberppt/stage01_compiler.py` creates an editable candidate outline from its semantic nodes. v0.5 already has an independently validated `page-plan.json`; re-running page decomposition would overwrite the higher-quality deck architecture. The adapter therefore projects the existing page plan exactly.

### D. 不把 CyberPPT audit 通过伪装成实战质量

Local adapter tests validate only our projection logic. Full downstream compatibility is reported as `runtime_validation=not_run` until a real CyberPPT checkout is supplied and its own lightweight `outline-audit` is executed.

### 6. Direct Source Truth consumption must be narrower than semantic context

CyberPPT's page authoring flow ultimately consumes Source Truth records and page `content_units`, while semantic nodes may cover a broader source proposition. v0.5 therefore treats page-level `normalized_fact_ids` as the fact-consumption authority. Relations and argument nodes remain structural context and cannot pull sibling facts into the page.

### 7. Structural `argument_duties` are a downstream contract

CyberPPT's content-unit machinery uses duties such as `premise`, `driver`, `gap`, `response`, `support`, `consequence`, `boundary`, and `detail`. Layer-four authoring roles are mapped deterministically into that vocabulary rather than passed through as arbitrary labels.

### 8. Locator basis must match the actual evidence coordinate system

Source Material Foundation line numbers refer to the standardized Markdown. The adapter therefore points projected line locators at that Markdown and carries the original Office/PDF filename as metadata. It never labels Markdown line numbers as native DOCX paragraph locations.

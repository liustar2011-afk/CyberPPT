# Stage 01 Editorial Delivery and On-Screen Hierarchy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make lightweight Stage 01 visibly deliver authored decisions and enforce business-title plus complete-detail on-screen writing without turning audit into a label generator.

**Architecture:** Existing communication input and autonomous-runner wording will define the delivery boundary. The page-writing Skill and Outline prompt will prescribe one canonical text hierarchy. A narrow script-quality detector will flag only three or more long flat labelled details, while existing relation and length checks remain in force.

**Tech Stack:** Python 3.12, `unittest`, repository CLI, Markdown Skill instructions.

## Global Constraints

- Keep the existing lightweight paths; create no approvals, receipts, manifests, hashes, or parallel directories.
- Do not prescribe title vocabulary, module count, or visual layout.
- Preserve existing source, hierarchy, relation, Markdown, and length checks.
- Run tests as `PYTHONPATH=. pytest -q`.

---

### Task 1: Expose all three editorial deliveries

**Files:**
- Modify: `cyberppt/communication_strategy.py:151-180`
- Modify: `cyberppt/commands/prepare_stage01_input.py:72-220`
- Modify: `cyberppt/commands/run_autonomous.py:288-305`
- Test: `tests/test_communication_strategy.py:71-100`
- Test: `tests/test_prepare_stage01_input.py`

**Interfaces:** consumes `prepare_communication_strategy(project: Path) -> dict[str, Any]`; produces extra instructions in existing prompt strings, no artifacts.

- [ ] **Step 1: Write failing tests**

```python
instructions = "\n".join(prepare_communication_strategy(self.project)["instructions"])
self.assertIn("完成作者编辑后的章节与页面提纲", instructions)
self.assertIn("逐页详细内容", instructions)
```

Add a `prepare_outline_input` fixture assertion that requires `Present the completed chapter/page Outline to the user for review before page-detail authoring.` and `逐页详细内容`.

- [ ] **Step 2: Verify the tests fail**

Run: `PYTHONPATH=. pytest -q tests/test_communication_strategy.py tests/test_prepare_stage01_input.py`  
Expected: the new delivery assertions fail.

- [ ] **Step 3: Implement the boundary text**

Append these instructions to `_lightweight_communication_strategy_input`:

```python
"在用户选择、修改或补充交流目标后，必须展示完成作者编辑后的章节与页面提纲、页面使命和主论证链，再进入逐页详细内容。",
"逐页详细内容完成后，必须向用户展示可阅读的完整稿、上屏文字和讲解逻辑；自动门禁只核验作者产物，不能代替上述内容交付。",
```

Add the same final-page delivery requirement to `prepare_outline_input`. Amend the `run_autonomous` docstring: an autonomous contract authorizes verification; it never waives communication-goal, Outline, or detailed-page delivery.

- [ ] **Step 4: Verify the narrowed tests pass**

Run: `PYTHONPATH=. pytest -q tests/test_communication_strategy.py tests/test_prepare_stage01_input.py`  
Expected: PASS.

- [ ] **Step 5: Commit this isolated change**

Run: `git add cyberppt/communication_strategy.py cyberppt/commands/prepare_stage01_input.py cyberppt/commands/run_autonomous.py tests/test_communication_strategy.py tests/test_prepare_stage01_input.py`  
Then: `git commit -m "fix(stage01): require visible editorial deliveries"`

### Task 2: Canonicalize business-title plus complete-detail writing

**Files:**
- Modify: `.agents/skills/cyberppt-write-single-page/SKILL.md:100-108`
- Modify: `cyberppt/commands/prepare_stage01_input.py` in `required_content_page_contract`
- Test: `tests/test_skill_contract.py`
- Test: `tests/test_prepare_stage01_input.py`

**Interfaces:** consumes the existing Skill and `prepare_outline_input`; produces source-faithful plain text guidance using indentation for hierarchy.

- [ ] **Step 1: Write failing contract tests**

```python
skill = Path(".agents/skills/cyberppt-write-single-page/SKILL.md").read_text(encoding="utf-8")
self.assertIn("业务小标题", skill)
self.assertIn("完整、自然的明细句", skill)
self.assertIn("标签：短语", skill)
```

Add an input-prompt assertion for `业务小标题\n  完整、自然的明细句。`.

- [ ] **Step 2: Verify tests fail**

Run: `PYTHONPATH=. pytest -q tests/test_skill_contract.py tests/test_prepare_stage01_input.py`  
Expected: the Stage 01 prompt assertion fails.

- [ ] **Step 3: Implement the canonical example**

Insert this exact text in the required page contract before audit remediation:

```text
当上屏需要承载长明细时，使用“业务小标题 → 完整、自然的明细句”：
业务小标题
  完整、自然的明细句。
短信息才可使用“标签：短语”。小标题必须概括其下同一业务维度，不能用需求、措施、价值等通用写作标签替代业务对象。
```

Align the existing Skill paragraph to the same wording; retain its source-first and true-relation rules.

- [ ] **Step 4: Verify tests pass**

Run: `PYTHONPATH=. pytest -q tests/test_skill_contract.py tests/test_prepare_stage01_input.py`  
Expected: PASS.

- [ ] **Step 5: Commit this isolated change**

Run: `git add .agents/skills/cyberppt-write-single-page/SKILL.md cyberppt/commands/prepare_stage01_input.py tests/test_skill_contract.py tests/test_prepare_stage01_input.py`  
Then: `git commit -m "fix(stage01): standardize onscreen title-detail writing"`

### Task 3: Flag only long flat labelled detail runs

**Files:**
- Modify: `cyberppt/script_quality_contract.py:3999-4120` and helper area near `_mechanical_onscreen_label_pattern_hits`
- Test: `tests/test_script_quality_contract.py:690-760`

**Interfaces:** consumes `ScriptPage.onscreen_text`; produces `ONSCREEN_BUSINESS_DETAIL_HIERARCHY_MISSING` through existing `_issue` only when a run is long, flat, and labelled.

- [ ] **Step 1: Write three failing tests**

```python
flat = "数据处理：平台需要组织多主体资源并完成质量核验。\n服务交付：服务目录需要面向场景形成可执行交付闭环。\n合作推进：合作机制需要明确主体分工和后续联动安排。"
grouped = "服务形成条件\n  平台组织多主体资源并完成质量核验。\n运营交付闭环\n  服务目录面向场景形成可执行交付闭环。"
compact = "数据目录：统一编目\n服务入口：统一受理"
```

Build otherwise-valid `ScriptPage` objects with each string. Assert the flat case contains the new code and the grouped and compact cases do not.

- [ ] **Step 2: Verify the new flat case fails**

Run: `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py -k 'flat_long_labelled or grouped_business_title or compact_short_label'`  
Expected: flat case fails because the code does not exist.

- [ ] **Step 3: Implement the narrow detector**

Add `_onscreen_flat_long_labelled_detail_hits(text: str) -> tuple[str, ...]` near the mechanical-label helper. Use the least indent among non-empty lines as peer level, select peer lines matching `[^：:]{1,16}[：:]` whose post-colon body length exceeds 18, and return hits only when there are at least three. In `_presentation_issues`, before the mechanical-template check, create:

```python
_issue(
    "ONSCREEN_BUSINESS_DETAIL_HIERARCHY_MISSING", page,
    "Several long on-screen details are flattened into peer labels without a business-title group.",
    "Group related propositions under a source-specific business title, then retain each detail as a complete natural sentence. Do not fix this with generic labels such as 需求、措施 or 价值.",
    evidence=hits,
)
```

Do not inspect anchors, titles, or module counts.

- [ ] **Step 4: Run quality tests**

Run: `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py`  
Expected: PASS, including detail-length and mechanical-label regressions.

- [ ] **Step 5: Commit this isolated change**

Run: `git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py`  
Then: `git commit -m "fix(stage01): flag flat long onscreen labels"`

### Task 4: Verify the real command path

**Files:**
- Modify only if needed: `docs/lightweight-script-generation-path.md`, `docs/run-autonomous.md`
- Verify: all files from Tasks 1–3.

**Interfaces:** consumes the completed rule changes; produces a tested author-first path without rewriting v13 scripts mechanically.

- [ ] **Step 1: Search for contradictory documentation**

Run: `rg -n "autonomous|交流目标|提纲|逐页|上屏" docs/lightweight-script-generation-path.md docs/run-autonomous.md`  
Expected: identify only wording that treats automation as a substitute for content delivery.

- [ ] **Step 2: Correct actual contradictions only**

Where needed, state: `run-autonomous verifies authored artifacts; it does not replace communication-goal, author-edited Outline, or detailed-page delivery.` Do not create a document if none conflicts.

- [ ] **Step 3: Run the complete suite**

Run: `PYTHONPATH=. pytest -q`  
Expected: PASS.

- [ ] **Step 4: Exercise the production input**

Run: `PYTHONPATH=. .venv/bin/python -m cyberppt prepare-communication-strategy projects/power-data-infrastructure-cooperation-v13-20260813 --lightweight`  
Expected: JSON includes all three visible deliveries and creates no project files.

- [ ] **Step 5: Report without mechanical v13 rewrite**

Report exact changed files, tests, and that v13 requires a subsequent authoring pass under the new contract; do not use an audit-only bulk conversion of its existing pages.

# 模型驱动的页面脚本审计 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Stage 01 脚本审计按作者选定的语义表达模型校验可见判断和来源覆盖，同时保持来源、关系、状态和边界硬约束。

**Architecture:** `outline.json` 是模型选择和判断展示策略的唯一权威来源。`script_quality_contract.py` 从单页 Outline 契约读取 `onscreen_judgment_mode` 与 `expression_model_selection`；已选模型用槽位—来源—可见职责校验覆盖，无模型页保持现有锚点规则。

**Tech Stack:** Python 3.12、pytest、CyberPPT Stage 01 JSON/Markdown 契约。

## Global Constraints

- 只使用当前项目的权威 Outline、Source Truth 与页面草稿；不重跑上游阶段，不进入 Stage 02。
- 禁止按页面类型、标题、关键词或来源顺序自动选择模型。
- `locked` 逐字锁定，`semantic_alignment` 仅允许来源忠实压缩，`hidden` 禁止独立上屏结论。
- 无模型页与未映射单元继续执行锚点校验；模型不得放宽完整稿、来源、关系、状态、边界或视觉结构规则。
- 每项提交只能包含明确列出的文件，不得混入工作区其他未跟踪文件。

---

### Task 1: 统一可见判断模式

**Files:**
- Modify: `cyberppt/script_quality_contract.py:256-283,4661-5050`
- Modify: `tests/test_script_quality_contract.py`
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`

**Interfaces:**
- Consumes: `onscreen_judgment_mode`、`core_message`、`onscreen_conclusion`、`onscreen_judgment`。
- Produces: `resolve_judgment_mode(explicit_mode, judgment_role) -> str`，取值为 `locked`、`semantic_alignment`、`hidden`。

- [ ] **Step 1: 写失败测试**

在 `tests/test_script_quality_contract.py` 添加：

```python
def test_semantic_alignment_allows_source_faithful_visible_compression(self) -> None:
    outline = strict_outline({
        "page_id": "p09", "sequence": 9, "page_type": "content",
        "core_message": "平台连接行业资源并组织可信服务供给。",
        "onscreen_judgment_mode": "semantic_alignment", "source_refs": ["S015"],
    })
    script = SCRIPT.replace(
        "- 主判断：初步定位为面向行业的公共能力。\n",
        "- 主判断：平台连接行业资源并组织可信服务供给。\n"
        "- 上屏结论：平台连接资源并形成可信服务供给\n", 1,
    )
    truth = source_truth({"id": "S015", "statement": "平台连接行业资源并组织可信服务供给。"})
    codes = {item.code for item in audit_script_quality(parse_script_markdown(script), outline, truth)}
    assert "SCRIPT_JUDGMENT_INTRODUCED" not in codes
    assert "ONSCREEN_JUDGMENT_CONTRACT_MISMATCH" not in codes
```

补充测试：`locked` 不等文本仍报 `ONSCREEN_JUDGMENT_CONTRACT_MISMATCH`；`hidden` 出现上屏结论报 `SCRIPT_JUDGMENT_INTRODUCED`；无显式模式的遗留契约维持当前行为。

- [ ] **Step 2: 运行失败测试**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py -k 'semantic_alignment or judgment_mode'`

Expected: FAIL；当前模式只包含 `locked` 和 `semantic_only`。

- [ ] **Step 3: 实现模式解析与审计分支**

将正式模式替换为：

```python
ONSCREEN_JUDGMENT_MODES = ("locked", "semantic_alignment", "hidden")

def resolve_judgment_mode(explicit_mode: str = "", judgment_role: str = "") -> str:
    if explicit_mode.strip():
        if explicit_mode.strip() not in ONSCREEN_JUDGMENT_MODES:
            raise ValueError(f"unsupported onscreen_judgment_mode: {explicit_mode.strip()}")
        return explicit_mode.strip()
    if judgment_role in SEMANTIC_ONLY_JUDGMENT_ROLES:
        return "semantic_alignment"
    if judgment_role in LOCKED_JUDGMENT_ROLES or not judgment_role:
        return "locked"
    raise ValueError(f"unsupported judgment_role: {judgment_role}")
```

在 `audit_script_quality()` 解析 `judgment_mode`。`locked` 保留缺失、逐字一致、顺序和标点检查；`semantic_alignment` 要求存在上屏结论且与 `core_message` 的 `text_similarity` 不低于 `VISIBLE_JUDGMENT_MIN_SIMILARITY`，不得报“新增判断”；`hidden` 的非空上屏结论报 `SCRIPT_JUDGMENT_INTRODUCED`。同步将 `_preflight_semantic_issues()` 的旧 `semantic_only` 名称换成 `semantic_alignment`。

- [ ] **Step 4: 更新当前 Outline**

仅在 P04 和 P05 加：

```json
"onscreen_judgment_mode": "semantic_alignment"
```

仅在 P05 加：

```json
"boundary_refs": ["ST0015"]
```

- [ ] **Step 5: 验证并提交**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py`

Expected: PASS。

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json
git commit -m "fix(stage01): support semantic judgment alignment"
```

### Task 2: 以模型槽位校验上屏覆盖

**Files:**
- Modify: `cyberppt/script_quality_contract.py:2983-3047`
- Modify: `tests/test_script_quality_contract.py`
- Read: `cyberppt/semantic_expression_models.py:52-102`

**Interfaces:**
- Consumes: `expression_model_selection`、`load_expression_models()`、`content_units`、`onscreen_judgment`、`onscreen_text`。
- Produces: `_model_slot_coverage_issues(page, contract) -> tuple[set[str], list[ScriptQualityIssue]]`。

- [ ] **Step 1: 写失败测试**

构造 SCQA：`complication -> S002/S003`、`answer -> S004`，可见文字为自然压缩但不包含全部锚点原文。

```python
assert "ONSCREEN_CONTENT_UNIT_GAP" not in codes
assert "EXPRESSION_MODEL_SLOT_ONSCREEN_MISSING" not in codes
```

删除 answer 的可见表达后：

```python
assert "EXPRESSION_MODEL_SLOT_ONSCREEN_MISSING" in codes
```

再加入一个未映射的 `onscreen_required` 单元，断言仍有 `ONSCREEN_CONTENT_UNIT_GAP`。

- [ ] **Step 2: 运行失败测试**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py -k 'expression_model or scqa'`

Expected: FAIL；当前只以 `onscreen_anchors` 子串判断。

- [ ] **Step 3: 实现最小槽位覆盖函数**

在 `script_quality_contract.py` 新增：

```python
def _model_slot_coverage_issues(
    page: ScriptPage, contract: dict[str, object],
) -> tuple[set[str], list[ScriptQualityIssue]]:
    selection = contract.get("expression_model_selection")
    if not isinstance(selection, dict) or selection.get("fit") != "selected":
        return set(), []
    model = load_expression_models().get(str(selection.get("model_id") or ""))
    if model is None:
        return set(), []
    # 对每个非 implicit 槽位检验其全部来源在可见文字中承担表达职责。
```

可见文字为 `"\n".join((page.onscreen_judgment, page.onscreen_text))`。每个来源单元仅在满足以下任一条件时覆盖：

```python
anchor_hit = any(anchor and anchor in visible for anchor in unit.get("onscreen_anchors") or [])
semantic_hit = _source_statement_overlap(str(unit.get("statement") or ""), visible) >= 0.22
```

槽位存在任一未覆盖来源时报告 `EXPRESSION_MODEL_SLOT_ONSCREEN_MISSING`；全覆盖时把该槽位来源加入 `covered_refs`。`implicit: true` 槽位不要求按来源原文覆盖。

- [ ] **Step 4: 与既有单元覆盖组合**

在 `_page_content_unit_coverage_issues()` 开始调用该函数。仅当 `set(source_refs).issubset(model_covered_refs)` 时，跳过该单元的原 `ONSCREEN_CONTENT_UNIT_GAP`；不得跳过完整稿、来源、关系、状态或未映射单元检查。

- [ ] **Step 5: 验证并提交**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py tests/test_stage01_compiler.py`

Expected: PASS；SCQA 压缩通过、answer 缺失失败、无模型页规则不变。

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
git commit -m "fix(stage01): audit visible coverage by model slot"
```

### Task 3: 保留模型中的缺口证据，禁止其成为页面落点

**Files:**
- Modify: `cyberppt/script_quality_contract.py:2164-2242`
- Modify: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes: `expression_model_selection`、页面标题、上屏结论、完整稿、备注、视觉结构。
- Produces: 受限的 `_negative_foreground_issues(page, contract)` 例外。

- [ ] **Step 1: 写失败测试**

设置 SCQA 的 `complication` 与 `answer` 槽位；上屏模块含“服务供给断点”，但上屏结论为“建立统一服务运营基础”。

```python
assert "NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC" not in codes
```

保留无模型且标题直接为“供给缺口”的失败断言。

- [ ] **Step 2: 运行失败测试**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py -k 'negative_foreground or complication'`

Expected: FAIL；当前顶层模块命中“断点/缺口”即失败。

- [ ] **Step 3: 实现受限例外**

新增：

```python
def _selected_problem_slots(contract: dict[str, object]) -> set[str]:
    selection = contract.get("expression_model_selection")
    mappings = selection.get("source_mapping", []) if isinstance(selection, dict) else []
    return {"complication", "problem", "gap"} & {
        str(item.get("slot") or "") for item in mappings
        if isinstance(item, dict) and item.get("implicit") is not True
    }
```

在 `_negative_foreground_issues()` 中，仅对“顶层模块命中负面词”且 `_selected_problem_slots(contract)` 非空时豁免。标题、副标题、上屏结论、完整稿开头、备注开头和视觉焦点仍执行原规则。Task 2 的回答槽位覆盖负责保证页面正向收束。

- [ ] **Step 4: 验证并提交**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py`

Expected: PASS。

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
git commit -m "fix(stage01): preserve modeled gap evidence"
```

### Task 4: 修订 P04/P05 并验证真实项目

**Files:**
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md`
- Modify: `.agents/skills/cyberppt-write-single-page/SKILL.md`
- Test: `tests/test_compile_page_script_authoring.py`

**Interfaces:**
- Consumes: Task 1–3 的审计语义、当前项目 P04/P05 Outline 与 Source Truth。
- Produces: P04/P05 可审阅页面稿与真实项目审计通过结果。

- [ ] **Step 1: 修订 P04**

- 上屏结论以 answer 收束：“统一连接、可信使用和服务运营基础支撑行业资源形成可交付、可计量的服务供给”。
- C 模块保留为“协同需求与服务供给断点”证据，不作为标题、结论或视觉出口。
- 补入已刷新内容单元的必要业务特征；备注拆为 2–3 段，删除“本页先”“下一页”“先说/再说”等元话语。

- [ ] **Step 2: 修订 P05**

- 添加 `- 边界依据：ST0015`。
- 将 ST0010/ST0011 和 ST0012/ST0013 拆为独立完整稿段落，或在映射行加入至少 8 个字符的“合并理由：共同说明……”说明。
- 删除“左侧、右侧、底部”等版式位置；只保留“行业节点连接—资源产品化—多方协同—既有体系与权利保持—行业中枢”的关系与阅读出口。
- 将“协同边界”改为“协同衔接与权利保持”；备注改为“平台与伙伴既有体系协同衔接”。

- [ ] **Step 3: 修正 Skill 命令漂移**

把：

```powershell
python -m cyberppt script-audit '<project>' --input '<authoritative-page-or-chapter-script>' --lightweight
```

改为：

```powershell
python -m cyberppt script-audit '<project>' --input '<authoritative-page-or-chapter-script>'
```

并注明当前 CLI 默认输出 `mode: lightweight`。

- [ ] **Step 4: 运行真实页面审计**

Run: `PYTHONPATH=. python3 -m cyberppt script-audit projects/power-data-infrastructure-cooperation-v16-20260813 --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md`

Expected: P04/P05 无 error；如仍失败，只修对应页面或检查器根因，不继续 P06。

- [ ] **Step 5: 全部回归、图谱检查并提交**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py tests/test_stage01_compiler.py tests/test_compile_page_script_authoring.py`

Expected: PASS。

Run: `git diff --check && npx --no-install graft build && npx --no-install graft check`

Expected: exit 0 且 `graph check: OK`。

```bash
git add projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md .agents/skills/cyberppt-write-single-page/SKILL.md tests/test_compile_page_script_authoring.py
git commit -m "fix(stage01): align model-led page scripts"
```

## Plan Self-Review

- 覆盖性：任务 1–3 实现三种判断模式、模型槽位覆盖和缺口证据；任务 4 修复真实 P04/P05、Skill 命令漂移并执行端到端审计。
- 无占位符：计划没有 TBD、TODO 或“后续处理”项。
- 一致性：所有任务复用现有 `ScriptPage`、`ScriptQualityIssue`、`load_expression_models()`、`_source_statement_overlap()` 和当前 Outline 契约。

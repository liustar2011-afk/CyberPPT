# Stage 02 视觉结构质量门（第一期）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为当前受治理的 Stage 02 决策包增加候选质量、关系覆盖、文本容量、焦点竞争、页间节奏和真实 QA 门，阻止语义失真、不可生成与整套重复的视觉结构进入提示词编译。

**Architecture:** 在“上屏表达结构自适应档案”任务完成后，候选决策包新增质量和覆盖字段；`audit_visual_design_package` 先执行页级硬门，再由 `run_visual_structure_audit` 执行 deck 节奏与 QA 写回。编译器只投影 `pending_audit` 质量合同，不自行宣布通过。

**Tech Stack:** Python 3.12、标准库 dataclasses/hashlib/json、pytest、CyberPPT Stage 02 JSON 合同。

## Global Constraints

- 前置依赖：`docs/superpowers/plans/2026-08-13-onscreen-expression-adaptive-profiles.md` 已完成并通过其定向测试。
- 仅修改当前受治理 Stage 02 合同；不读取、迁移、修改或重跑历史项目产物。
- 不改写锁定文字、事实、主体关系、页面顺序或 Stage 01 内容。
- 不引入颜色、字体、几何坐标、形状、箭头外观、媒介或固定视觉模板。
- `business_relationships` 与 `stage01_relationship_features` 仍是关系权威源。
- 编译器写入 `pending_audit`；只有 `visual-structure-audit` 能写入通过/失败 QA。
- 不提交、推送或创建 PR；仅在用户明确要求时提交。

---

## 文件职责

| 文件 | 改动责任 |
|---|---|
| `cyberppt/visual_structure_contract.py` | 候选质量、关系覆盖、容量、焦点和 spec 一致性的页级审计；deck 节奏审计函数。 |
| `cyberppt/commands/visual_structure_stage.py` | 将已选候选质量投影到 spec；审计后写回真实 QA；生成人读审阅摘要。 |
| `vendor/skills/ppt-visual-structure-designer/SKILL.md` | 要求候选写出选择、淘汰、覆盖、容量、焦点与节奏例外字段。 |
| `vendor/skills/ppt-visual-structure-designer/references/output-contract.md` | 定义决策包和 spec 新字段。 |
| `tests/test_visual_structure_contract.py` | 页级合同、失败码、节奏函数测试。 |
| `tests/test_visual_structure_stage.py` | 编译投影、QA 写回、审阅摘要、提示词阻断测试。 |
| `tests/test_visual_structure_skill_fixtures.py` | Skill fixture 新字段与输出合同验证。 |

### Task 1: 定义候选质量与关系覆盖合同

**Files:**
- Modify: `vendor/skills/ppt-visual-structure-designer/SKILL.md:112-167`
- Modify: `vendor/skills/ppt-visual-structure-designer/references/output-contract.md`
- Modify: `tests/test_visual_structure_contract.py:20-120`

**Interfaces:**
- Requires: `candidate.selection_rationale: dict[str, object]`
- Requires: `candidate.rejection_rationale: str`（仅未选候选）
- Requires: `decision.relationship_coverage: list[dict[str, object]]`

- [ ] **Step 1: 扩展通过 fixture，作为新合同的最小正例**

在 `_payloads()` 中为每个候选加入：

```python
"selection_rationale": {
    "mission_fit": "该关系场直接承接页面使命。",
    "generation_feasibility": {
        "score": 100,
        "dimensions": {
            "single_focus": 20,
            "text_capacity": 20,
            "relation_clarity": 20,
            "composition_stability": 20,
            "anti_pattern_risk": 20,
        },
        "risks": [],
    },
},
"rejection_rationale": "",
```

为 decision 加入至少一条由 `business_relationships` 派生的 `relationship_coverage`，使用 fixture 的已知 evidence key 和锁定 text ID。

- [ ] **Step 2: 写失败测试，锁定缺失和错误合同**

```python
def test_audit_rejects_missing_candidate_quality_rationale(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    del decisions["pages"][0]["candidates"][0]["selection_rationale"]
    assert "CANDIDATE_SELECTION_RATIONALE_MISSING" in _codes(_audit(tmp_path, design, decisions, spec))


def test_audit_rejects_unselected_candidate_without_counterfactual(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    decisions["pages"][0]["candidates"][1]["rejection_rationale"] = "得分更低"
    assert "CANDIDATE_REJECTION_RATIONALE_INVALID" in _codes(_audit(tmp_path, design, decisions, spec))


def test_audit_rejects_uncovered_primary_business_relation(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    decisions["pages"][0]["relationship_coverage"] = []
    assert "RELATIONSHIP_COVERAGE_MISSING" in _codes(_audit(tmp_path, design, decisions, spec))
```

- [ ] **Step 3: 运行测试，确认当前实现失败**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_contract.py`

Expected: FAIL，缺少新阻断码或 fixture 尚不能通过。

- [ ] **Step 4: 更新 Skill 与输出合同**

在 Skill 中规定：候选必须有 5 维、总和为 100 的可生成性评分；未选候选必须写相对选中方案的具体淘汰理由；每页必须将关键 Stage 01 关系标记为 `primary`、`secondary` 或有业务理由的 `not_rendered`。输出合同写入 JSON 样例和字段枚举；不得提及具体视觉形状或位置。

- [ ] **Step 5: 运行 fixture 合同测试**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_skill_fixtures.py`

Expected: PASS。

### Task 2: 实现页级质量、覆盖、容量和焦点审计

**Files:**
- Modify: `cyberppt/visual_structure_contract.py:117-342`
- Modify: `tests/test_visual_structure_contract.py`

**Interfaces:**
- Produces: 页级阻断码 `CANDIDATE_GENERATION_SCORE_INVALID`、`CANDIDATE_REJECTION_RATIONALE_INVALID`、`RELATIONSHIP_COVERAGE_*`、`TEXT_CAPACITY_*`、`FOCUS_COMPETITION_DETECTED`。
- Consumes: 自适应档案任务的 `expression_constraints`、`expression_fit` 与 `expression_contract`。

- [ ] **Step 1: 写容量与焦点竞争失败测试**

```python
def test_audit_rejects_over_capacity_selected_candidate(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    selected = _selected(decisions)
    selected["text_capacity_budget"]["risk_level"] = "blocking"
    assert "TEXT_CAPACITY_BLOCKING" in _codes(_audit(tmp_path, design, decisions, spec))


def test_audit_rejects_competing_primary_focus(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["structural_decision"]["text_bindings"].append(
        {"evidence_id": "E2", "target_ref": "E2", "binding": "result", "text_ids": ["P01-T02"]}
    )
    assert "FOCUS_COMPETITION_DETECTED" in _codes(_audit(tmp_path, design, decisions, spec))
```

- [ ] **Step 2: 实现纯函数化审计帮助器**

在 `visual_structure_contract.py` 增加私有帮助器：

```python
def _audit_generation_feasibility(candidate: dict[str, Any], page_id: str, issue: Callable[..., None]) -> int | None: ...
def _audit_relationship_coverage(source: dict[str, Any], decision: dict[str, Any], page_id: str, issue: Callable[..., None]) -> dict[str, int]: ...
def _audit_text_capacity(candidate: dict[str, Any], expected_text: list[str], page_id: str, issue: Callable[..., None]) -> dict[str, object]: ...
def _audit_focus_competition(page_spec: dict[str, Any], page_id: str, issue: Callable[..., None]) -> dict[str, object]: ...
```

评分帮助器精确要求五个维度、整数 0–20、总分与声明 `score` 均为 100。覆盖帮助器从 `business_relationships` 和 `stage01_relationship_features.actions` 的规范化三元组计算必需关系；核心判断/页面使命中显式出现的主体关系不得标记 `not_rendered`。容量帮助器验证锁定文字 ID 全量分配，`risk_level=blocking` 阻断。焦点帮助器验证焦点有 P0 evidence 和最多主级 `result` 绑定。

- [ ] **Step 3: 将未选候选理由绑定到已选候选**

在候选循环结束后，对非 `selected_candidate` 检查 `rejection_rationale`：至少包含一个具体失败维度、关系、容量或阅读问题；禁止仅使用“较低”“美观”“一般”“不适合”等泛化词且无对象。

- [ ] **Step 4: 运行页级合同测试**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_contract.py`

Expected: PASS。

### Task 3: 编译质量合同并移除预设通过 QA

**Files:**
- Modify: `cyberppt/commands/visual_structure_stage.py:104-208`
- Modify: `cyberppt/commands/visual_structure_stage.py:220-241`
- Modify: `tests/test_visual_structure_stage.py`

**Interfaces:**
- Produces: `page_spec.quality_contract: dict[str, object]`
- Produces: 初始 `page_spec.qa.status == "pending_audit"`
- Produces: 初始 `deck_spec.qa_summary.status == "pending_audit"`

- [ ] **Step 1: 写失败测试，冻结编译前 QA 状态**

```python
def test_executable_spec_is_pending_until_visual_audit() -> None:
    page = _build_executable_page(source, decision)
    assert page["qa"] == {"status": "pending_audit", "score": None, "blocking_issues": [], "warnings": []}
    assert page["quality_contract"]["generation_feasibility"]["score"] == 100
```

- [ ] **Step 2: 运行测试，确认现有预设 94 分不符合合同**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_stage.py`

Expected: FAIL，现有 `qa.status` 为 `passed`。

- [ ] **Step 3: 编译 quality_contract**

从选中候选和已审计 decision 投影：可生成性分数与风险、文本容量摘要、关系覆盖计数、焦点检查摘要、页面使命适配说明。不得复制候选内部推理全文，也不得将这些字段注入 `generation_handoff`。

- [ ] **Step 4: 改写初始 QA**

将 `_build_executable_page` 的 QA 改为：

```python
"qa": {"status": "pending_audit", "score": None, "blocking_issues": [], "warnings": []}
```

将 deck `qa_summary` 同样初始化为 `pending_audit`、无评分。更新 Markdown 渲染，展示质量合同的风险摘要，但不把风险文本作为 ImageGen 文字。

- [ ] **Step 5: 运行定向测试**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_stage.py tests/test_visual_structure_contract.py`

Expected: PASS。

### Task 4: 审计后写回真实 QA 与页间节奏门

**Files:**
- Modify: `cyberppt/visual_structure_contract.py`
- Modify: `cyberppt/commands/visual_structure_stage.py:587-715`
- Modify: `tests/test_visual_structure_contract.py`
- Modify: `tests/test_visual_structure_stage.py`

**Interfaces:**
- Produces: `audit_visual_deck_rhythm(spec: dict[str, Any], decisions: dict[str, Any]) -> dict[str, Any]`
- Produces: validation report 的 `deck_rhythm` 结果
- Produces: 审计后的 `qa` 与 `qa_summary`

- [ ] **Step 1: 写节奏审计测试**

```python
def test_deck_rhythm_blocks_three_identical_content_signatures() -> None:
    spec, decisions = _three_page_deck_with_same_signature()
    report = audit_visual_deck_rhythm(spec, decisions)
    assert report["status"] == "failed"
    assert report["blocking_issues"][0]["code"] == "DECK_RHYTHM_REPETITION_BLOCKING"


def test_deck_rhythm_warns_for_two_similar_pages_with_exception() -> None:
    spec, decisions = _two_similar_page_deck(exception_reason="同一章节需保持连续阅读关系")
    report = audit_visual_deck_rhythm(spec, decisions)
    assert report["status"] == "passed"
    assert report["warnings"][0]["code"] == "DECK_RHYTHM_REPETITION_WARNING"
```

- [ ] **Step 2: 实现稳定的结构签名与节奏规则**

签名仅包括连续内容页的：`visual_intent_type`、排序后的 `spatial_grammar`、语义焦点 kind、主阅读方向、文字绑定模式。连续三页签名相同为阻断；连续两页相同为警告。读取 `decision.rhythm_exception_reason`，它只能降低两页警告的阻断风险，不得消除记录。

- [ ] **Step 3: 在 `run_visual_structure_audit` 中接入节奏和 QA 写回**

在 Markdown/JSON/decision/execution 审计均通过后运行节奏审计。全部通过时，将每页 `qa.status` 写为 `passed`，分数取视觉 spec validator 的实际分数与质量合同摘要；任一页级或 deck 级阻断时写为 `failed`，保留具体 blocking issues。随后原子重写 spec，再构建 prompts。失败时不生成或刷新 prompts。

- [ ] **Step 4: 写审计写回测试**

```python
def test_visual_audit_writes_passed_qa_only_after_all_gates(tmp_path: Path) -> None:
    code, report = run_visual_structure_audit(project, script)
    assert code == 0
    spec = json.loads((project / VISUAL_FILES["spec_json"]).read_text(encoding="utf-8"))
    assert spec["qa_summary"]["status"] == "passed"
    assert all(page["qa"]["status"] == "passed" for page in spec["pages"])
```

另写失败用例，断言节奏阻断时 `generation-prompts.md` 未刷新且 spec 不会保留 `passed`。

- [ ] **Step 5: 运行阶段测试**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_contract.py tests/test_visual_structure_stage.py`

Expected: PASS。

### Task 5: 生成人读质量审阅摘要与全量验证

**Files:**
- Modify: `cyberppt/commands/visual_structure_stage.py:718-757`
- Modify: `tests/test_visual_structure_stage.py`

**Interfaces:**
- Produces: `visual/visual-review-summary.md`
- Produces: validation report 中该文件的 hash 与 artifact 登记。

- [ ] **Step 1: 写摘要输出测试**

```python
def test_visual_audit_writes_review_summary(tmp_path: Path) -> None:
    code, report = run_visual_structure_audit(project, script)
    assert code == 0
    summary = (project / "visual" / "visual-review-summary.md").read_text(encoding="utf-8")
    assert "候选取舍" in summary
    assert "关系覆盖" in summary
    assert "文本容量" in summary
    assert "整套节奏" in summary
```

- [ ] **Step 2: 实现只读人工审阅摘要**

新增 `_render_visual_review_summary(spec, decisions, validation)`，逐页输出：选中候选、未选候选淘汰理由、可生成性风险、关系覆盖统计、文本容量风险、焦点检查；文末输出节奏警告。摘要不包含 prompt、内部证据全文、风格字段或 ImageGen 指令。

- [ ] **Step 3: 注册产物与新鲜度**

将 `review_summary` 加入 `VISUAL_FILES`、验证报告 `artifact_sha256`、`assert_visual_structure_ready` 的完整性检查和 `_register_visual_artifacts`。确保摘要变化会要求重新审计，但摘要本身不参与 prompt 输入哈希。

- [ ] **Step 4: 运行定向回归**

Run: `PYTHONPATH=. pytest -q tests/test_onscreen_expression.py tests/test_visual_structure_contract.py tests/test_visual_structure_stage.py tests/test_visual_structure_skill_fixtures.py`

Expected: PASS。

- [ ] **Step 5: 运行完整仓库回归并报告**

Run: `PYTHONPATH=. pytest -q`

Expected: PASS；若失败，报告精确失败测试，并区分本次变更与既有失败。

## 验收清单

- [ ] 候选有可验证评分、任务适配和具体淘汰理由。
- [ ] 关键 Stage 01 关系均可追溯到视觉证据和锁定文字，且关键关系不得被静默隐藏。
- [ ] 容量超限、竞争焦点、无反馈闭环或无收束关系均不能进入提示词构建。
- [ ] 相邻页重复风险在 validation report 和人工摘要中可见；连续三页重复被阻断。
- [ ] 编译期 QA 始终为 pending，审计通过后才成为 passed。
- [ ] 审阅摘要已登记并参与新鲜度门，但不泄漏到 ImageGen 提示词。
- [ ] 定向测试和完整仓库回归状态均已验证并报告。


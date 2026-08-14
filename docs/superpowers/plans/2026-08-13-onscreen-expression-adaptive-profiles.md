# 上屏表达结构自适应档案 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让十种上屏表达结构以“可修改的默认结构档案”方式约束 Stage 02 候选、可执行视觉规格和审计，而不把它们固化为视觉模板。

**Architecture:** `onscreen_expression.py` 作为默认表达约束的唯一来源；Stage 02 handoff 与视觉设计输入仅传递该派生合同；候选以 `expression_fit` 声明默认适配或基于业务关系的偏离；编译器将选中候选摘要投影为 spec 的 `expression_contract`；审计跨输入、候选和 spec 检查一致性。

**Tech Stack:** Python 3.12、标准库 dataclasses/hashlib/json、pytest、CyberPPT Stage 01/Stage 02 JSON 合同。

## Global Constraints

- `page_type` 继续只承担渲染路由；仅 `content` 页有上屏表达结构合同。
- 表达结构约束不得规定颜色、字体、形状、箭头外观、卡片布局、坐标或视觉媒介。
- `business_relationships` 是业务关系权威源；表达结构只规定阅读关系与信息均衡。
- 保留锁定文字、文字 ID 的值与顺序；不得让表达结构重写 Stage 01 内容。
- `default_profile` 可被 `adapted` 候选修改，但必须保留表达核心并写明偏离理由。
- 本计划不提交、推送或创建 PR；提交仅在用户单独要求时进行。

---

## 文件职责

| 文件 | 改动责任 |
|---|---|
| `cyberppt/onscreen_expression.py` | 定义十种默认表达约束及稳定哈希。 |
| `cyberppt/stage02_handoff.py` | 在内容页 handoff 中投影不可编辑的 `expression_constraints`。 |
| `cyberppt/commands/visual_structure_stage.py` | 将约束带入设计输入；将选中候选的适配摘要编译到 spec/Markdown。 |
| `cyberppt/visual_structure_contract.py` | 审计输入、候选 `expression_fit` 与 spec `expression_contract` 的一致性。 |
| `tests/test_onscreen_expression.py` | 覆盖十种默认档案和哈希稳定性。 |
| `tests/test_visual_structure_stage.py` | 覆盖 handoff/input/spec 投影与人读稿。 |
| `tests/test_visual_structure_contract.py` | 覆盖默认适配、合理偏离、反模式与跨产物漂移。 |
| `vendor/skills/ppt-visual-structure-designer/SKILL.md` | 定义 Skill 对 `expression_constraints`、`expression_fit` 与偏离理由的输出责任。 |
| `vendor/skills/ppt-visual-structure-designer/references/output-contract.md` | 列出候选和 spec 新字段及其机器合同。 |

### Task 1: 建立十种默认表达约束合同

**Files:**
- Modify: `cyberppt/onscreen_expression.py:11-67`
- Test: `tests/test_onscreen_expression.py`

**Interfaces:**
- Produces: `expression_constraints(form: str) -> dict[str, object]`
- Produces: `expression_constraints_sha256(constraints: Mapping[str, object]) -> str`
- Consumes: `VALID_EXPRESSION_FORMS`

- [ ] **Step 1: 写失败测试，冻结十种档案的结构边界**

```python
from cyberppt.onscreen_expression import expression_constraints


def test_expression_constraints_cover_all_registered_forms() -> None:
    assert set(EXPRESSION_SPECS) == set(VALID_EXPRESSION_FORMS)
    for form in VALID_EXPRESSION_FORMS:
        contract = expression_constraints(form)
        assert contract["form"] == form
        assert contract["node_range"][0] <= contract["node_range"][1]
        assert contract["relation_pattern"]
        assert contract["reading_requirement"]
        assert contract["balance_requirement"]
        assert contract["anti_patterns"]


def test_operation_loop_contract_requires_feedback_without_layout_recipe() -> None:
    contract = expression_constraints("operation_loop")
    assert contract["relation_pattern"] == "directed_cycle"
    assert "feedback_edge_required" in contract["required_features"]
    assert "arrow_style" not in contract
    assert "coordinates" not in contract
```

- [ ] **Step 2: 运行测试，确认因接口不存在而失败**

Run: `PYTHONPATH=. pytest -q tests/test_onscreen_expression.py`

Expected: FAIL，提示无法导入 `expression_constraints`。

- [ ] **Step 3: 实现不可变档案与稳定哈希**

在 `ExpressionSpec` 增加 `relation_pattern`、`reading_requirement`、`balance_requirement`、`anti_patterns`、`required_features` 字段；为十种现有 form 填入设计稿中的中性约束。实现：

```python
def expression_constraints(form: str) -> dict[str, object]:
    key = validate_expression_form(form)
    if not key:
        raise ValueError("expression form is required")
    spec = EXPRESSION_SPECS[key]
    return {
        "form": spec.key,
        "node_range": list(spec.module_range),
        "relation_pattern": spec.relation_pattern,
        "reading_requirement": spec.reading_requirement,
        "balance_requirement": spec.balance_requirement,
        "required_features": list(spec.required_features),
        "anti_patterns": list(spec.anti_patterns),
    }


def expression_constraints_sha256(constraints: Mapping[str, object]) -> str:
    stable = json.dumps(constraints, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()
```

新增 `hashlib`、`json` 和 `Mapping` 导入；返回全新 `dict/list`，不得暴露可变注册表对象。

- [ ] **Step 4: 运行定向测试，确认通过**

Run: `PYTHONPATH=. pytest -q tests/test_onscreen_expression.py`

Expected: PASS。

### Task 2: 将表达约束投影到 Stage 02 输入

**Files:**
- Modify: `cyberppt/stage02_handoff.py:14,200-255`
- Modify: `cyberppt/commands/visual_structure_stage.py:244-311`
- Test: `tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: `expression_constraints(expression["form"])`
- Produces: `stage02_visual_input.expression_constraints: dict[str, object]`
- Produces: `visual-design-input.pages[].expression_constraints: dict[str, object]`

- [ ] **Step 1: 写失败测试，验证 handoff 与设计输入保留同一档案**

```python
def test_visual_design_input_carries_expression_constraints() -> None:
    # 使用 form=framework_4 的 content handoff fixture 调用 _write_visual_design_input。
    page = json.loads(output.read_text(encoding="utf-8"))["pages"][0]
    assert page["onscreen_expression"]["form"] == "framework_4"
    assert page["expression_constraints"]["form"] == "framework_4"
    assert page["expression_constraints"]["node_range"] == [4, 4]
```

另加 `_page_record` 测试，断言 `stage02_visual_input["expression_constraints"]` 等于从该 form 派生的值。

- [ ] **Step 2: 运行测试，确认字段尚不存在**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_stage.py`

Expected: FAIL，断言 `expression_constraints` 缺失。

- [ ] **Step 3: 在 handoff 和输入投影中派生字段**

`stage02_handoff.py`：在 `expression = resolve_onscreen_expression(...).to_dict()` 后执行：

```python
constraints = expression_constraints(str(expression["form"]))
```

并将相同的 `constraints` 放入顶层记录和 `stage02_visual_input`。`_write_visual_design_input` 从 `stage02_visual_input` 读取 `expression_constraints`；若缺失则基于 `onscreen_expression.form` 派生，以兼容同一版本内构造的测试 fixture，但不得静默接受 form 为空的内容页。

- [ ] **Step 4: 在 handoff 审计中验证投影不漂移**

新增阻断码 `ONSCREEN_EXPRESSION_CONSTRAINTS_INVALID`：内容页缺字段、form 不一致、或派生结果不等于注册表结果时失败。

- [ ] **Step 5: 运行定向测试，确认通过**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_stage.py tests/test_onscreen_expression.py`

Expected: PASS。

### Task 3: 扩展候选合同与 Skill 指令

**Files:**
- Modify: `vendor/skills/ppt-visual-structure-designer/SKILL.md:96-159`
- Modify: `vendor/skills/ppt-visual-structure-designer/references/output-contract.md`
- Modify: `cyberppt/commands/visual_structure_stage.py:382-449`
- Test: `tests/test_visual_structure_contract.py`

**Interfaces:**
- Consumes: `expression_constraints`
- Requires: `candidate.expression_fit: dict[str, object]`
- Produces: selected `expression_fit` for compiler consumption

- [ ] **Step 1: 写失败测试，定义候选适配的最小合同**

在 `_payloads()` 的每个候选增加合格的 `expression_fit` fixture，并新增：

```python
def test_audit_rejects_candidate_without_expression_fit(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    del decisions["pages"][0]["candidates"][0]["expression_fit"]
    report = _audit(tmp_path, design, decisions, spec)
    assert "CANDIDATE_EXPRESSION_FIT_MISSING" in _codes(report)


def test_audit_rejects_adapted_candidate_without_reason(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    fit = decisions["pages"][0]["candidates"][0]["expression_fit"]
    fit.update({"constraint_status": "adapted", "changed_constraints": ["reading_requirement"], "deviation_reason": ""})
    report = _audit(tmp_path, design, decisions, spec)
    assert "CANDIDATE_EXPRESSION_DEVIATION_INVALID" in _codes(report)
```

- [ ] **Step 2: 运行测试，确认新审计码尚未出现**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_contract.py`

Expected: FAIL。

- [ ] **Step 3: 将候选适配合同写入 Skill 和任务调用说明**

Skill 与 `prepare_visual_structure_stage` 的调用文本必须规定：每个候选写入 `expression_fit`；`constraint_status=default_profile` 时偏离字段为空；`constraint_status=adapted` 时必须列出改动项、业务理由、保留的核心关系。Skill 不得把 form 转化为固定版式。

输出合同写明字段：

```json
{
  "expression_fit": {
    "form": "framework_4",
    "constraint_status": "default_profile",
    "satisfied_constraints": ["four_peer_nodes", "peer_balance"],
    "reading_relation": "four parallel capability groups are read as peers",
    "balance_strategy": "comparable prominence and text capacity",
    "changed_constraints": [],
    "deviation_reason": ""
  }
}
```

- [ ] **Step 4: 实现候选适配字段审计**

在 `audit_visual_design_package` 添加私有帮助函数，检查 form 一致性、状态枚举、必填字符串、默认/偏离字段互斥关系和 `changed_constraints` 非空性。为每个 form 依据 `expression_constraints` 检查最低限度的候选事实：节点范围、阅读序列覆盖、关系方向/闭环/对应/收束等；只读候选数据，不推断视觉坐标或媒介。

- [ ] **Step 5: 运行定向测试，确认通过**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_contract.py`

Expected: PASS。

### Task 4: 将已选候选编译为可追溯 expression contract

**Files:**
- Modify: `cyberppt/commands/visual_structure_stage.py:104-208`
- Modify: `cyberppt/commands/visual_structure_stage.py:211-217`
- Test: `tests/test_visual_structure_stage.py`

**Interfaces:**
- Consumes: `source.expression_constraints`, `decision.selected_candidate`, `candidate.expression_fit`
- Produces: `page_spec.expression_contract: dict[str, object]`

- [ ] **Step 1: 写失败测试，断言选中候选被投影至 spec**

```python
def test_executable_spec_retains_selected_expression_contract() -> None:
    page = _build_executable_page(source, decision)
    assert page["expression_contract"] == {
        "form": "causal_chain",
        "constraints_sha256": expression_constraints_sha256(source["expression_constraints"]),
        "selected_candidate_id": "candidate-b",
        "fit_status": "adapted",
        "reading_relation": "two parallel causes converge before the response",
        "balance_strategy": "parallel causes have equal weight before convergence",
        "deviation_reason": "the convergence preserves the causal core",
    }
```

- [ ] **Step 2: 运行测试，确认 spec 尚无该字段**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_stage.py`

Expected: FAIL，键 `expression_contract` 缺失。

- [ ] **Step 3: 在 `_build_executable_page` 编译表达合同**

新增私有函数：

```python
def _expression_contract(source: dict[str, Any], selected: dict[str, Any]) -> dict[str, object]:
    constraints = source["expression_constraints"]
    fit = selected["expression_fit"]
    return {
        "form": constraints["form"],
        "constraints_sha256": expression_constraints_sha256(constraints),
        "selected_candidate_id": str(selected["id"]),
        "fit_status": str(fit["constraint_status"]),
        "reading_relation": str(fit["reading_relation"]),
        "balance_strategy": str(fit["balance_strategy"]),
        "deviation_reason": str(fit["deviation_reason"]),
    }
```

将返回值加入 page spec，且不把 `satisfied_constraints`、候选内部证据解释或任何布局指令送入 `generation_handoff`。

- [ ] **Step 4: 扩展 Markdown 审阅稿**

`_render_visual_structure_markdown` 每页新增“上屏表达结构与候选取舍”章节，展示 form、核心约束、选中候选 ID、适配状态、阅读关系、均衡策略和非空偏离理由。只展示选中方案；候选 A/B/C 的完整比较留在 `visual-design-decisions.json`，避免 Markdown 成为新的提示词输入。

- [ ] **Step 5: 运行定向测试，确认通过**

Run: `PYTHONPATH=. pytest -q tests/test_visual_structure_stage.py`

Expected: PASS。

### Task 5: 跨产物审计、完整回归与文档验证

**Files:**
- Modify: `cyberppt/visual_structure_contract.py:117-342`
- Modify: `tests/test_visual_structure_contract.py`
- Modify: `tests/test_visual_structure_skill_fixtures.py`（仅在 fixture 需更新时）

**Interfaces:**
- Consumes: 输入约束、候选 `expression_fit`、spec `expression_contract`
- Produces: 阻断码 `SPEC_EXPRESSION_CONTRACT_MISSING`、`SPEC_EXPRESSION_CONTRACT_DRIFTED` 及 form 特有阻断码。

- [ ] **Step 1: 写漂移与非模板化测试**

```python
def test_audit_rejects_expression_contract_drift(tmp_path: Path) -> None:
    design, decisions, spec = _payloads()
    spec["pages"][0]["expression_contract"]["selected_candidate_id"] = "other"
    report = _audit(tmp_path, design, decisions, spec)
    assert "SPEC_EXPRESSION_CONTRACT_DRIFTED" in _codes(report)


def test_same_form_can_select_different_visual_intents(tmp_path: Path) -> None:
    design, decisions, spec = _two_page_same_form_payloads()
    decisions["pages"][0]["selected_candidate"] = "page-1-candidate-a"
    decisions["pages"][1]["selected_candidate"] = "page-2-candidate-b"
    report = _audit(tmp_path, design, decisions, spec)
    assert report["status"] == "passed"
```

- [ ] **Step 2: 实现跨产物一致性审计**

对每页比较 spec `expression_contract` 与输入约束、已选候选 `expression_fit`。精确比较 form、哈希、选中候选 ID、适配状态、阅读关系、均衡策略、偏离理由。缺失和不一致均为阻断，不接受“审阅稿有说明”作为替代。

- [ ] **Step 3: 扩展 Skill fixture 与合同测试**

更新受影响 fixture，使其包含 `expression_constraints`、三个候选的 `expression_fit` 和 spec `expression_contract`；验证 `validate_visual_spec.py` 仍只校验视觉 spec 自身，而跨产物规则仍由 CyberPPT 的 `visual-structure-audit` 执行。

- [ ] **Step 4: 运行完整定向验证**

Run: `PYTHONPATH=. pytest -q tests/test_onscreen_expression.py tests/test_visual_structure_contract.py tests/test_visual_structure_stage.py tests/test_visual_structure_skill_fixtures.py`

Expected: PASS。

- [ ] **Step 5: 运行仓库回归并报告既有失败**

Run: `PYTHONPATH=. pytest -q`

Expected: 全绿，或清楚区分本改动失败与既有失败；不得以定向测试替代完整回归。

## 验收清单

- [ ] 十种 form 均有稳定默认档案与哈希测试。
- [ ] Stage 02 handoff、视觉输入、候选、spec 和 Markdown 审阅稿均可追溯相同 form。
- [ ] 默认档案可被合理偏离，但无理由/矛盾偏离被阻断。
- [ ] 因果、闭环、对照、矩阵、分层、金字塔等关键关系的反模式被阻断。
- [ ] 同一 form 可以选择不同视觉意图，未形成模板路由。
- [ ] `generation_handoff` 不新增任何风格或候选内部说明泄漏。
- [ ] 全部定向测试通过，完整回归状态已报告。


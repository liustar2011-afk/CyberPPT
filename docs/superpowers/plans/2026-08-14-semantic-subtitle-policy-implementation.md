# 语义副标题策略 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 Lightweight Stage 01 仅在结构型内容页需要时，从已确认的语义与来源事实生成短副标题，并使 JSON、Markdown 与审计一致。

**Architecture:** 新增独立的 `subtitle_policy` 纯函数模块，负责判定、压缩和来源归属；`stage01_compiler` 只将结果写入候选提纲。脚本编译器消费该结果，脚本审计验证副标题与主判断、来源状态和上屏职责的一致性，同时保留作者覆盖优先级。

**Tech Stack:** Python 3.12+、标准库、pytest、现有 Lightweight Stage 01 JSON/Markdown 契约。

## Global Constraints

- 只改生成器、消费者、审计和测试；不得重跑当前项目的上游语义、Source Truth 或新建项目。
- 不以页面编号、标题关键词或电力行业词汇触发规则。
- 自动文案只能由 `core_message`、内容单元、上屏模块和其 `source_refs` 压缩得出。
- 无法安全压缩时返回 `author_required`，不得捏造模板文案。
- 作者已有副标题优先，不得被重新编译覆盖。
- JSON 与 Markdown 必须在同一编译链路中同步，不得通过临时转换补写。

---

### Task 1: 建立副标题策略的纯函数和契约

**Files:**
- Create: `cyberppt/subtitle_policy.py`
- Test: `tests/test_subtitle_policy.py`

**Interfaces:**
- Consumes: `core_message: str`、`visual_intent_type: str`、`onscreen_expression_form: str`、`onscreen_modules: list[dict[str, object]]`、`content_units: list[dict[str, object]]`。
- Produces: `SubtitlePolicy` dataclass 和 `resolve_subtitle_policy(...) -> dict[str, object]`。
- Contract: 返回 `mode`（`generated` / `not_needed` / `author_required` / `authored`）、`subtitle`、`rationale`、`source_refs`、`derived_from`。

- [ ] **Step 1: 写失败测试，定义结构页、非结构页、状态保护和无法压缩的预期**

```python
from cyberppt.subtitle_policy import resolve_subtitle_policy


def test_comparison_lifecycle_generates_source_bounded_subtitle() -> None:
    result = resolve_subtitle_policy(
        core_message="平台对产品和场景实行全过程阶段门控，产品和场景分别沿生命周期推进。",
        visual_intent_type="comparison_2col",
        onscreen_expression_form="comparison_2col",
        onscreen_modules=[
            {"display_title": "产品生命周期", "source_refs": ["ST0001"]},
            {"display_title": "场景服务生命周期", "source_refs": ["ST0002"]},
        ],
        content_units=[],
    )

    assert result["mode"] == "generated"
    assert "产品" in result["subtitle"] and "场景" in result["subtitle"]
    assert result["source_refs"] == ["ST0001", "ST0002"]


def test_non_structural_definition_does_not_force_subtitle() -> None:
    result = resolve_subtitle_policy(
        core_message="数据产品是可以独立登记和管理的数据成果。",
        visual_intent_type="concept_definition",
        onscreen_expression_form="",
        onscreen_modules=[{"display_title": "数据产品", "source_refs": ["ST0001"]}],
        content_units=[],
    )

    assert result == {
        "mode": "not_needed", "subtitle": "", "rationale": result["rationale"],
        "source_refs": [], "derived_from": [],
    }


def test_uncertain_or_conditional_relation_requires_author_instead_of_upgrading() -> None:
    result = resolve_subtitle_policy(
        core_message="在条件确认后，拟开展联合试点并验证持续运营可行性。",
        visual_intent_type="phase",
        onscreen_expression_form="flow_3_5",
        onscreen_modules=[
            {"display_title": "条件确认", "source_refs": ["ST0003"]},
            {"display_title": "联合试点", "source_refs": ["ST0004"]},
        ],
        content_units=[],
    )

    assert result["mode"] == "author_required"
    assert result["subtitle"] == ""
```

- [ ] **Step 2: 运行测试，确认缺少模块而失败**

Run: `PYTHONPATH=. pytest -q tests/test_subtitle_policy.py`  
Expected: FAIL with `ModuleNotFoundError: No module named 'cyberppt.subtitle_policy'`.

- [ ] **Step 3: 实现最小、无行业词表的策略模块**

```python
@dataclass(frozen=True)
class SubtitlePolicy:
    mode: str
    subtitle: str
    rationale: str
    source_refs: tuple[str, ...]
    derived_from: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "subtitle": self.subtitle,
            "rationale": self.rationale,
            "source_refs": list(self.source_refs),
            "derived_from": list(self.derived_from),
        }


def resolve_subtitle_policy(*, core_message: str, visual_intent_type: str,
                            onscreen_expression_form: str,
                            onscreen_modules: list[dict[str, object]],
                            content_units: list[dict[str, object]]) -> dict[str, object]:
    """Return a source-bounded subtitle candidate; never invent a claim."""
```

Implementation rules:

- Define structural expressions as the existing expression forms `flow_3_5`、`operation_loop`、`architecture_layers`、`comparison_2col`、`matrix_2x2`、`pyramid_argument`、`grouped_2` and their matching visual intents.
- Treat a short `core_message`, absent modules, or non-structural pages as `not_needed`.
- Extract only subject/relationship/result fragments present in the supplied core message or module titles. Deduplicate source refs in module order.
- Reject a candidate if it drops a conditional/uncertain marker (`拟`, `计划`, `条件`, `待确认`, `风险`) or has no readable relationship phrase; return `author_required`.
- Keep format-neutral helpers private so later refinements do not expand `stage01_compiler.py`.

- [ ] **Step 4: 运行定向测试并补齐四类结构表达的参数化样例**

Run: `PYTHONPATH=. pytest -q tests/test_subtitle_policy.py`  
Expected: PASS.

- [ ] **Step 5: 提交本任务**

```bash
git add cyberppt/subtitle_policy.py tests/test_subtitle_policy.py
git commit -m "feat(stage01): add semantic subtitle policy"
```

### Task 2: 在提纲编译器写入副标题策略并保护人工结果

**Files:**
- Modify: `cyberppt/stage01_compiler.py:718-807, 810-1099`
- Modify: `tests/test_stage01_compiler.py`

**Interfaces:**
- Consumes: `resolve_subtitle_policy()` from Task 1 and existing content units/modules.
- Produces: 每个内容页的 `subtitle_policy`，`generated` 时同时写入 `subtitle`；人工 `authored` 结果保持不变。
- Preserves: `refresh_outline_content_units()` 的现有模块作者覆盖语义。

- [ ] **Step 1: 添加失败测试，验证候选提纲写入策略而非长主判断**

```python
def test_compile_outline_draft_emits_generated_subtitle_for_structural_page(tmp_path: Path) -> None:
    project = _project_with_structural_lifecycle_node(tmp_path)

    outline_path = compile_outline_draft(
        project, communication_goal="形成合作启动共识"
    )
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    page = next(item for item in outline["pages"] if item.get("page_type") == "content")

    assert page["subtitle_policy"]["mode"] == "generated"
    assert page["subtitle"] == page["subtitle_policy"]["subtitle"]
    assert page["subtitle"] != page["core_message"]


def test_refresh_outline_content_units_keeps_authored_subtitle(tmp_path: Path) -> None:
    outline_path = _outline_with_authored_subtitle(tmp_path)

    refresh_outline_content_units(tmp_path, outline_path=outline_path, page_id="p04")

    page = _read_page(outline_path, "p04")
    assert page["subtitle_policy"]["mode"] == "authored"
    assert page["subtitle"] == "作者确认的副标题"
```

- [ ] **Step 2: 运行测试，确认当前提纲缺少 `subtitle_policy`**

Run: `PYTHONPATH=. pytest -q tests/test_stage01_compiler.py -k subtitle`  
Expected: FAIL with missing `subtitle_policy` or missing `subtitle` assertion.

- [ ] **Step 3: 在页面构造和刷新路径接入策略**

```python
policy = resolve_subtitle_policy(
    core_message=core_message,
    visual_intent_type=visual_intent_type,
    onscreen_expression_form=expression_form,
    onscreen_modules=onscreen_modules,
    content_units=content_units,
)
page["subtitle_policy"] = policy
if policy["mode"] == "generated":
    page["subtitle"] = str(policy["subtitle"])
```

In `refresh_outline_content_units()`, retain a pre-existing `subtitle_policy` with `mode == "authored"`; otherwise recompute after modules and content units have been refreshed. Do not derive from `title`.

- [ ] **Step 4: 运行提纲编译器相关测试**

Run: `PYTHONPATH=. pytest -q tests/test_stage01_compiler.py tests/test_subtitle_policy.py`  
Expected: PASS.

- [ ] **Step 5: 提交本任务**

```bash
git add cyberppt/stage01_compiler.py tests/test_stage01_compiler.py
git commit -m "feat(stage01): project subtitle policy into outlines"
```

### Task 3: 让 Markdown 编译与 JSON 策略同步，支持作者覆盖

**Files:**
- Modify: `cyberppt/commands/compile_page_script_authoring.py:286-371`
- Modify: `tests/test_compile_page_script_authoring.py`（若仓库实际测试文件名不同，新增同名测试文件）

**Interfaces:**
- Consumes: `page.subtitle_policy` 和 `page.subtitle`。
- Produces: Markdown 中可选的 `- 副标题：...` 行。
- Priority: `authored["subtitle"]` 非空时优先；否则仅消费 `subtitle_policy.mode in {"generated", "authored"}` 的 `page.subtitle`。

- [ ] **Step 1: 写失败测试，验证 JSON→MD 的同步与 `not_needed` 的省略**

```python
def test_content_page_uses_generated_outline_subtitle_when_author_has_none() -> None:
    page = {
        "page_id": "p04", "title": "生命周期管理", "core_message": "长判断",
        "subtitle": "产品与场景分别在阶段门控下走向运营与复制",
        "subtitle_policy": {"mode": "generated"}, "source_refs": ["ST0001"],
        "visual_intent_type": "comparison_2col",
    }

    markdown = _content_page(page, _authored_without_subtitle(), _records())

    assert "- 副标题：产品与场景分别在阶段门控下走向运营与复制" in markdown


def test_content_page_omits_subtitle_for_not_needed_policy() -> None:
    page = {**_definition_page(), "subtitle": "", "subtitle_policy": {"mode": "not_needed"}}

    markdown = _content_page(page, _authored_without_subtitle(), _records())

    assert "- 副标题：" not in markdown
```

- [ ] **Step 2: 运行测试，确认当前消费者未读取策略**

Run: `PYTHONPATH=. pytest -q tests/test_compile_page_script_authoring.py -k subtitle`  
Expected: FAIL with missing test helper or incorrect subtitle selection.

- [ ] **Step 3: 收敛 `_content_page()` 的副标题解析逻辑**

```python
def _resolved_subtitle(page: dict[str, Any], authored: dict[str, Any]) -> str:
    authored_value = str(authored.get("subtitle") or "").strip()
    if authored_value:
        return authored_value
    policy = page.get("subtitle_policy")
    mode = str(policy.get("mode") or "") if isinstance(policy, dict) else ""
    return str(page.get("subtitle") or "").strip() if mode in {"generated", "authored"} else ""
```

Replace the inline subtitle expression in `_content_page()` with this helper. Leave cover/chapter template rendering unchanged.

- [ ] **Step 4: 运行消费者与解析回归测试**

Run: `PYTHONPATH=. pytest -q tests/test_compile_page_script_authoring.py tests/test_script_quality_contract.py`  
Expected: PASS.

- [ ] **Step 5: 提交本任务**

```bash
git add cyberppt/commands/compile_page_script_authoring.py tests/test_compile_page_script_authoring.py
git commit -m "feat(stage01): synchronize subtitle policy into markdown"
```

### Task 4: 新增副标题契约审计与回归验证

**Files:**
- Modify: `cyberppt/script_quality_contract.py:4921-5447`
- Modify: `tests/test_script_quality_contract.py`
- Modify: `tests/test_script_audit_command.py`

**Interfaces:**
- Consumes: 页面脚本 `subtitle`、Outline `subtitle_policy`、`core_message`、`onscreen_modules` 和来源记录。
- Produces: `SUBTITLE_POLICY_MISMATCH`、`SUBTITLE_UNGROUNDED`、`SUBTITLE_TITLE_REPEAT`、`STRUCTURED_PAGE_LONG_JUDGMENT_ONSCREEN` 等现有 `ScriptQualityIssue` 形式的问题。
- Compatibility: 没有 `subtitle_policy` 的既有 Outline 按兼容路径跳过新规则。

- [ ] **Step 1: 写失败测试，覆盖一致性、可追溯性和不回灌长判断**

```python
def test_generated_subtitle_must_match_outline_policy() -> None:
    issues = audit_script_quality(
        _script_with_subtitle("错误副标题"),
        _outline_with_policy(mode="generated", subtitle="来源副标题"),
        _source_truth(),
    )

    assert "SUBTITLE_POLICY_MISMATCH" in _codes(issues)


def test_generated_subtitle_cannot_introduce_relation_outside_source() -> None:
    issues = audit_script_quality(
        _script_with_subtitle("产品必然带来规模化收入"),
        _outline_with_policy(mode="generated", subtitle="产品必然带来规模化收入"),
        _source_truth(),
    )

    assert "SUBTITLE_UNGROUNDED" in _codes(issues)


def test_structured_not_needed_page_rejects_long_unattributed_judgment_in_onscreen_body() -> None:
    issues = audit_script_quality(
        _script_with_long_judgment_as_first_onscreen_line(),
        _outline_with_policy(mode="not_needed", subtitle=""),
        _source_truth(),
    )

    assert "STRUCTURED_PAGE_LONG_JUDGMENT_ONSCREEN" in _codes(issues)
```

- [ ] **Step 2: 运行测试，确认当前审计不识别策略字段**

Run: `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py -k subtitle_policy`  
Expected: FAIL because expected issue codes are absent.

- [ ] **Step 3: 新增独立的 `_subtitle_policy_issues()` 并在内容页审计中调用**

```python
def _subtitle_policy_issues(page: ScriptPage, contract: dict[str, object],
                            records_by_id: dict[str, dict[str, object]]) -> list[ScriptQualityIssue]:
    policy = contract.get("subtitle_policy")
    if not isinstance(policy, dict):
        return []
    # validate mode, expected subtitle, source-ref grounding, title repetition,
    # and structural-body long-judgment fallback without word-for-word matching.
```

Use normalized token containment and existing source-consumption helpers; compare semantic fragments rather than enforcing whole-string equality except for compiler-generated `generated` text. Reject source-free causal/result additions. For `author_required`, issue no error when the subtitle is blank.

- [ ] **Step 4: 运行定向审计与全量测试**

Run: `PYTHONPATH=. pytest -q tests/test_subtitle_policy.py tests/test_stage01_compiler.py tests/test_compile_page_script_authoring.py tests/test_script_quality_contract.py tests/test_script_audit_command.py`  
Expected: PASS.

Run: `PYTHONPATH=. pytest -q`  
Expected: PASS except clearly pre-existing, documented failures; do not mask them.

- [ ] **Step 5: 对当前项目做受影响产物验证**

Run: `PYTHONPATH=. python3 -c 'from pathlib import Path; from cyberppt.commands.outline_audit import run_outline_audit; p=Path("projects/power-data-infrastructure-cooperation-v16-20260813"); print(run_outline_audit(p, p/"workbench/stages/01-analysis/outline.json", source_truth_path=p/"workbench/stages/01-analysis/source-truth.json")[1]["status"])'`  
Expected: 仅更新现有审计报告；不触发语义、Source Truth 或其他上游阶段。

- [ ] **Step 6: 提交本任务**

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py tests/test_script_audit_command.py
git commit -m "feat(stage01): audit semantic subtitle policy"
```

## Plan Self-Review

- 规格覆盖：策略、生成器投影、Markdown 消费、作者覆盖、审计、测试和当前项目的按需验证均有对应任务。
- 占位符检查：无未完成占位语或“后续补充”步骤；测试文件名如与仓库实际结构不符时，Task 3 明确要求新建指定文件，避免隐式猜测。
- 类型一致性：Task 1 的 `resolve_subtitle_policy()` 输出在 Task 2 以 JSON 词典写入，Task 3/4 读取相同 `mode`、`subtitle` 和 `source_refs` 字段。

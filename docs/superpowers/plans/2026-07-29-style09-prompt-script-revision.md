# Style 09 Prompt Script Revision Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 Style 09 的逐页送图脚本，使 full 图提示词保留完整获批上屏内容，并停止向 ImageGen 泄漏自动版式枚举。

**Architecture:** 保留现有双图、manifest、OCR、editable-overlay 和 PPT 重建链路不变。修改仅发生在 `content-first-v1` 提示词编译：`image_locked_text` 继续标记逐字准确重点，完整 `onscreen_judgment + onscreen_text` 同时作为 full 图必须表达的上屏内容；自动 `PresentationDecision` 仅写 metadata，显式脚本覆盖才进入 prompt。

**Tech Stack:** Python 3、pytest、现有 CyberPPT `imagegen_handoff.py`

## Global Constraints

- 只修改逐页 ImageGen 提示词编译及其测试。
- 不修改双图法、full/background 关系、manifest、production mode、OCR、semantic plan、editable-overlay 或 PPT 重建。
- 不修改终稿脚本的事实、判断、页面结构和审批状态。
- Style 01–08、Style 10 默认行为保持不变。
- P09 先单页验证，未获用户认可前不批量生图。

---

### Task 1: 恢复 full 图的完整上屏内容

**Files:**
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py:59-88`
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py:970-1065`
- Test: `tests/test_imagegen_creative_brief.py`

**Interfaces:**
- Consumes: `ScriptPage.onscreen_judgment: str`、`ScriptPage.onscreen_text: str`、`select_image_locked_text(page, visual_context) -> str`
- Produces: `render_content_first_prompt(...) -> tuple[str, str]`，其中 prompt 同时包含 `【锁定关键文字】` 和 `【完整上屏内容】`

- [ ] **Step 1: 写入失败测试，要求完整正文保留且删除后补文字指令**

```python
def test_content_first_full_reference_keeps_complete_onscreen_content() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        prompt = build_page_prompt(page, lock)

    full = prompt.split("【完整上屏内容】", 1)[1].split(
        "【内容与视觉要求｜不上屏】", 1
    )[0]
    assert "保持滚动验证和误差复盘" in full
    assert "权限、日志和发布审核共同保障运行" in full
    assert "解释性正文由后续 PPT 可编辑文字层承载" not in prompt
    assert "不要求 ImageGen 逐字生成" not in prompt
```

- [ ] **Step 2: 运行测试并确认失败**

Run: `python3 -m pytest tests/test_imagegen_creative_brief.py::test_content_first_full_reference_keeps_complete_onscreen_content -q`  
Expected: FAIL，因为当前 prompt 使用 `【完整页面内容｜用于视觉叙事】`，并要求正文后续补入。

- [ ] **Step 3: 修改提示词合同**

将 Style 09 full 图的正式输出合同改为：

```python
CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT = """【内容与视觉要求｜不上屏】
必须由文字、结构和必要画面共同完整表达【完整上屏内容】中的核心判断、业务对象、逻辑关系、关键限定和正文要点，不得捏造事实、改变判断强度或删除支撑判断成立所必需的内容。
【锁定关键文字】中的每一项都必须逐字准确；数字、单位、专有名词、业务术语和否定边界必须准确。
【完整上屏内容】均需进入 full 图；允许调整换行、文字层级和局部语序，但不得把解释性正文全部替换为场景、图标或抽象视觉隐喻。
不得新增未经页面内容支持的上屏文字；必要的行业场景、业务动作、环境细节和视觉隐喻只能辅助附近文字与业务关系。
以【页面逻辑】组织空间，不使用等权卡片、通用图标流程或逐项配图。
中文使用清晰的现代无衬线黑体。不得生成额外页面标题、Logo、页脚或页码。
【输出要求｜不上屏】
画布尺寸为 2048×1024（2:1）。"""
```

在 `render_content_first_prompt()` 中：

```python
parts = [
    # existing task, judgment and logic sections
    "【锁定关键文字】",
    locked,
    "",
    "【完整上屏内容】",
    complete_semantics,
    # existing story, output and style sections
]
```

保留完整 `onscreen_body`；`select_image_locked_text()` 只决定锁定清单，不再决定正文是否进入 prompt。

- [ ] **Step 4: 更新既有断言并运行提示词测试**

Run: `python3 -m pytest tests/test_imagegen_creative_brief.py -q`  
Expected: PASS。

- [ ] **Step 5: 提交完整内容修复**

```bash
git add scripts/dual_image_overlay/imagegen_handoff.py tests/test_imagegen_creative_brief.py
git commit -m "fix: preserve full onscreen content in ImageGen prompts"
```

---

### Task 2: 自动版式仅保留为 metadata

**Files:**
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py:734-743`
- Modify: `scripts/dual_image_overlay/imagegen_handoff.py:1014-1029`
- Test: `tests/test_imagegen_creative_brief.py`

**Interfaces:**
- Consumes: `PresentationDecision.source: str`、`ScriptPage.layout_motif: str`、`ScriptPage.scene_role: str`
- Produces: `render_presentation_contract(page, decision) -> str`；自动决策返回空字符串，显式脚本覆盖返回人工指令

- [ ] **Step 1: 写入自动枚举不进入 prompt 的失败测试**

```python
def test_auto_presentation_decision_stays_in_metadata_only() -> None:
    page = _page()
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert compiled.presentation is not None
    assert compiled.presentation.source == "auto"
    assert compiled.presentation.layout_motif not in compiled.prompt
    assert compiled.presentation.scene_role not in compiled.prompt
    assert "【版式与场景策略｜不上屏】" not in compiled.prompt
```

同时保留显式覆盖测试：

```python
def test_explicit_presentation_override_reaches_prompt() -> None:
    page = replace(_page(), layout_motif="process_atlas", scene_role="no_scene")
    with TemporaryDirectory() as directory:
        lock = write_project_style_lock(project=Path(directory), style_id=9)
        compiled = compile_page_prompt(page, lock)

    assert "【人工版式覆盖｜不上屏】" in compiled.prompt
    assert "process_atlas" in compiled.prompt
    assert "no_scene" in compiled.prompt
```

- [ ] **Step 2: 运行测试并确认自动决策测试失败**

Run: `python3 -m pytest tests/test_imagegen_creative_brief.py::test_auto_presentation_decision_stays_in_metadata_only tests/test_imagegen_creative_brief.py::test_explicit_presentation_override_reaches_prompt -q`  
Expected: 自动决策测试 FAIL，显式覆盖测试需要新增实现。

- [ ] **Step 3: 仅渲染显式版式覆盖**

```python
def render_presentation_contract(
    page: ScriptPage,
    decision: PresentationDecision,
) -> str:
    if decision.source != "script":
        return ""
    return "\n".join(
        (
            "【人工版式覆盖｜不上屏】",
            f"版式母题：{page.layout_motif.strip() or decision.layout_motif}。",
            f"场景角色：{page.scene_role.strip() or decision.scene_role}。",
            "该覆盖只约束本页表达方式，不得删除完整上屏内容或改变业务关系。",
        )
    )
```

在 `render_content_first_prompt()` 中只在返回值非空时插入该区块：

```python
presentation_contract = render_presentation_contract(page, presentation)
if presentation_contract:
    parts[logic_end:logic_end] = [presentation_contract, ""]
```

自动 `PresentationDecision` 继续写入 `CompiledPagePrompt.build_metadata()`，用于诊断与批次 QA。

- [ ] **Step 4: 运行版式与提示词回归**

Run: `python3 -m pytest tests/test_imagegen_creative_brief.py tests/test_final_script_pages.py -q`  
Expected: PASS。

- [ ] **Step 5: 提交版式边界修复**

```bash
git add scripts/dual_image_overlay/imagegen_handoff.py tests/test_imagegen_creative_brief.py
git commit -m "fix: keep automatic layout motifs out of prompts"
```

---

### Task 3: 重编译 P09–P12 并只送 P09 验证

**Files:**
- Generated review: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/prompts/imagegen/style09-full-content-script-smoke-20260729-imagegen-review.md`
- Generated diagnostics: `projects/power-supply-forecast-warning-prestudy-20260724/workbench/prompts/imagegen/style09-full-content-script-smoke-20260729-imagegen-diagnostics.json`

**Interfaces:**
- Consumes: 已批准终稿脚本、当前 Style 09 lock、修订后的 `content-first-v1`
- Produces: P09–P12 审阅提示词；只生成 P09 测试图

- [ ] **Step 1: 重编译 P09–P12**

Run:

```bash
python3 -m scripts.dual_image_overlay.imagegen_handoff \
  projects/power-supply-forecast-warning-prestudy-20260724 \
  --script projects/power-supply-forecast-warning-prestudy-20260724/workbench/scripts/final/script-final.md \
  --style-lock projects/power-supply-forecast-warning-prestudy-20260724/workbench/locks/visual_style_lock.json \
  --pages 9-12 \
  --batch-name style09-full-content-script-smoke-20260729
```

Expected: 输出 batch review、diagnostics、gate 和 P09–P12 draft 路径。

- [ ] **Step 2: 检查完整内容和内部枚举**

Run:

```bash
rg -n "完整上屏内容|decision_canvas|process_atlas|no_scene|后续 PPT 可编辑文字层" \
  projects/power-supply-forecast-warning-prestudy-20260724/workbench/prompts/imagegen/style09-full-content-script-smoke-20260729-imagegen-review.md
```

Expected:

- 四页均出现 `完整上屏内容`；
- 不出现自动 `decision_canvas`、`process_atlas`、`no_scene`；
- 不出现“后续 PPT 可编辑文字层承载”。

- [ ] **Step 3: 运行全量相关回归**

Run:

```bash
python3 -m pytest \
  tests/test_imagegen_creative_brief.py \
  tests/test_extended_style_9.py \
  tests/test_final_script_pages.py \
  tests/test_script_quality_contract.py::ScriptMarkdownParserTests -q
```

Expected: PASS。

- [ ] **Step 4: 只生成 P09 测试图**

使用 P09 新 draft 原文调用现有 ImageGen 流程。不得改写或手工收紧 prompt；保存为新的版本文件，不覆盖此前失败样本。

- [ ] **Step 5: 人工验收**

验收 P09 是否：

- 是一页完整正式汇报材料；
- 保留定位、服务对象、分析服务链、支撑能力和职责边界；
- 符合 Style 09 的优雅、沉稳和领导演讲气质。

未通过则停止，不生成 P10–P12。

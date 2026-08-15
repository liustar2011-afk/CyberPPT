# ImageGen Handoff Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `scripts/imagegen_pipeline/imagegen_handoff.py` 拆分为职责清晰的 `handoff/` 内部包，同时保持旧导入路径、提示词输出和交付行为完全兼容。

**Architecture:** 保留 `scripts/imagegen_pipeline/imagegen_handoff.py` 作为显式兼容门面，在同级新增 `handoff/` 包。共享契约位于 `contracts.py`，语义、文字和视觉决策处于同一层，提示词编译位于其上，交付和 CLI 位于最外层；所有内部模块禁止导入兼容门面。

**Tech Stack:** Python 3.10+、标准库 `ast`/`dataclasses`/`json`/`pathlib`/`re`/`argparse`、现有 `unittest` 和 `pytest` 测试体系、仓库现有 ImageGen pipeline 工具。

## Global Constraints

- 仅拆分 `scripts/imagegen_pipeline/imagegen_handoff.py`，不同时拆分 `deliverable_prompt.py`、`page_manifest.py` 或 SVG/PPTX 运行时。
- 拆分前后必须保持函数签名、默认参数、返回结构、提示词文本、字段/分节顺序、文件路径、错误行为和退出码一致。
- 保留 `scripts.imagegen_pipeline.imagegen_handoff` 原导入路径。
- 兼容门面显式再导出迁移前公开符号及仓库真实使用的事实私有符号；不得使用 `import *`。
- 内部模块不得导入 `imagegen_handoff.py`；不得通过函数体延迟导入掩盖循环依赖。
- 不修改提示词规则、画布约束、Style 09/10、页面脚本格式、提示词文案、阈值、错误码或输出路径。
- 兼容门面目标不超过 200 行，不含函数、类或规则实现。
- 每个任务必须先写失败测试并观察失败，再迁移代码并运行针对性回归。
- 允许新增小型 `handoff/common.py` 仅承载跨模块纯函数；不得形成新的大杂烩模块。

---

## File Structure

### Create

- `scripts/imagegen_pipeline/handoff/__init__.py`：内部包显式导出，不承担编排。
- `scripts/imagegen_pipeline/handoff/contracts.py`：常量、正则、提示词契约和共享轻量类型。
- `scripts/imagegen_pipeline/handoff/common.py`：仅放跨模块纯文本/规范化原语，避免规则模块互相导入。
- `scripts/imagegen_pipeline/handoff/semantics.py`：页面语义、视觉意图、语义关系和语义审计。
- `scripts/imagegen_pipeline/handoff/text.py`：锁定文字、上屏文字、语义摘要和文字渲染模式。
- `scripts/imagegen_pipeline/handoff/presentation.py`：视觉决策、视觉中心、载体和页面逻辑契约。
- `scripts/imagegen_pipeline/handoff/prompt.py`：ImageGen 页面提示词编译和组装。
- `scripts/imagegen_pipeline/handoff/delivery.py`：章节交接、提示词/诊断文件写入和批处理交付。
- `scripts/imagegen_pipeline/handoff/cli.py`：`main`、参数解析和命令行错误处理。
- `tests/test_imagegen_handoff_modularization.py`：符号兼容、依赖边界、行为快照和门面约束。
- `tests/fixtures/imagegen_handoff_baseline.json`：拆分前固定页面样本的结构化输出。

### Modify

- `scripts/imagegen_pipeline/imagegen_handoff.py`：逐步迁出实现，最终收敛为兼容门面。

### Do Not Modify

- `scripts/imagegen_pipeline/creative_brief.py`
- `scripts/imagegen_pipeline/deliverable_prompt.py`
- `scripts/imagegen_pipeline/prompt_compiler.py`
- `scripts/imagegen_pipeline/page_manifest.py`
- `cyberppt/commands/final_script_pages.py`
- `cyberppt/commands/semantic_intent_audit.py`
- 现有 ImageGen 业务规则和 Style 文件。

---

### Task 1: 冻结 ImageGen Handoff 兼容接口与提示词基线

**Files:**
- Create: `tests/test_imagegen_handoff_modularization.py`
- Create: `tests/fixtures/imagegen_handoff_baseline.json`
- Read: `scripts/imagegen_pipeline/imagegen_handoff.py`
- Read: `tests/test_imagegen_creative_brief.py`
- Read: `tests/test_imagegen_no_visual_structure.py`
- Read: `tests/test_imagegen_page_manifest.py`
- Read: `tests/test_final_script_pages.py`
- Read: `tests/test_extended_style_9.py`
- Read: `tests/test_extended_style_10.py`
- Read: `tests/test_artifact_prompt.py`
- Read: `tests/test_semantic_intent.py`

**Interfaces:**
- Consumes: 当前 `imagegen_handoff.py` 顶层符号、真实导入方、`ScriptPage` 样本和现有 `build_page_prompt(...)` 等函数。
- Produces: `COMPAT_SYMBOLS`、`BASE_PUBLIC_SYMBOLS`、固定页面输入、提示词结构化序列化函数和行为基线 fixture。

- [ ] **Step 1: 写兼容符号和依赖边界测试**

在测试中显式建立迁移前符号快照，不从新门面动态生成兼容清单：

```python
COMPAT_SYMBOLS = (
    "ScriptPage",
    "PresentationDecision",
    "build_page_prompt",
    "compile_page_prompt",
    "audit_page_semantic_intent",
    "render_content_first_style_contract",
    "render_page_logic_contract",
    "select_image_locked_text",
    "_page_semantic_relations",
    "write_chapter_handoff",
    "main",
)


def test_legacy_symbols_exist() -> None:
    module = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    missing = [name for name in COMPAT_SYMBOLS if not hasattr(module, name)]
    assert missing == []
```

测试还应扫描仓库导入语句，将真实导入的名称并入冻结集合；私有符号必须明确列出，不能使用 `dir(module)` 作为基线。

- [ ] **Step 2: 运行测试，确认基线文件缺失时按预期失败**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 新增的基线测试因 `tests/fixtures/imagegen_handoff_baseline.json` 尚不存在而失败；兼容符号测试通过。

- [ ] **Step 3: 建立固定页面样本和结构化序列化**

固定样本覆盖：

- 语义视觉页；
- 内容首要页；
- 含锁定关键文字页；
- 含 Style 09/10 风格锁页；
- 含视觉结构、页面逻辑和演讲备注页。

序列化时只比较稳定字段：

```python
def normalize_prompt(text: str) -> str:
    return text.replace("\r\n", "\n").rstrip() + "\n"


def serialize_result(value: object) -> object:
    if hasattr(value, "to_dict"):
        return serialize_result(value.to_dict())
    if is_dataclass(value):
        return serialize_result(asdict(value))
    if isinstance(value, dict):
        return {str(k): serialize_result(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_result(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    return value
```

基线至少记录 `resolve_page_visual_intent`、`audit_page_semantic_intent`、`select_image_locked_text`、`resolve_presentation_decision` 和 `build_page_prompt` 的结果。

- [ ] **Step 4: 生成并审阅行为基线**

通过当前未拆分模块生成 `imagegen_handoff_baseline.json`，检查无绝对临时路径、时间戳、对象地址和环境相关值。基线必须保留提示词正文、分节顺序和结构化页面结果。

- [ ] **Step 5: 运行基线和现有 ImageGen 定向测试**

Run:

```bash
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_imagegen_no_visual_structure \
  tests.test_imagegen_page_manifest \
  tests.test_final_script_pages \
  tests.test_extended_style_9 \
  tests.test_extended_style_10 \
  tests.test_artifact_prompt \
  tests.test_semantic_intent -v
```

Expected: 当前基线结果作为后续最低标准记录；若 pytest 风格测试未被 `unittest` 执行，另记录 `python -m pytest` 的独立基线，不把既有失败误判为本次回归。

- [ ] **Step 6: 提交基线**

```bash
git add tests/test_imagegen_handoff_modularization.py tests/fixtures/imagegen_handoff_baseline.json
git commit -m "test: freeze imagegen handoff behavior"
```

---

### Task 2: 建立内部包并提取共享契约

**Files:**
- Create: `scripts/imagegen_pipeline/handoff/__init__.py`
- Create: `scripts/imagegen_pipeline/handoff/contracts.py`
- Create: `scripts/imagegen_pipeline/handoff/common.py`
- Modify: `scripts/imagegen_pipeline/imagegen_handoff.py:1-604`
- Modify: `tests/test_imagegen_handoff_modularization.py`

**Interfaces:**
- Consumes: 顶层常量、正则、提示词契约、`EVIDENCE_ID_RE` 及模块级共享类型。
- Produces: `handoff.contracts` 的唯一契约定义；`handoff.common` 的纯函数；原文件仍能继续运行未迁移代码。

- [ ] **Step 1: 写模块导入、常量值和单一实现测试**

```python
def test_contract_constants_are_direct_reexports() -> None:
    legacy = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    contracts = importlib.import_module(
        "scripts.imagegen_pipeline.handoff.contracts"
    )
    assert legacy.IMAGEGEN_CANVAS_CONTRACT == contracts.IMAGEGEN_CANVAS_CONTRACT
    assert legacy.IMAGEGEN_CHROME_BAN_CONTRACT is contracts.IMAGEGEN_CHROME_BAN_CONTRACT


def test_handoff_modules_import_without_running_delivery() -> None:
    importlib.import_module("scripts.imagegen_pipeline.handoff.contracts")
    importlib.import_module("scripts.imagegen_pipeline.handoff.common")
```

- [ ] **Step 2: 运行测试确认新模块尚不存在**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 新模块导入测试失败，原因是 `scripts.imagegen_pipeline.handoff` 尚不存在。

- [ ] **Step 3: 原样迁移契约和纯函数**

将常量、正则和契约片段从原文件迁入 `contracts.py`，保留字符串、转义、换行和定义顺序。把确需多个规则域复用的无业务副作用函数放入 `common.py`；不把页面编排函数放入该文件。原文件通过直接导入引用迁移后的对象，不复制常量。

- [ ] **Step 4: 运行契约和既有定向测试**

Run: `python -m unittest tests.test_imagegen_handoff_modularization tests.test_imagegen_no_visual_structure -v`

Expected: PASS，基线 fixture 不变。

- [ ] **Step 5: 提交契约层**

```bash
git add scripts/imagegen_pipeline/handoff/__init__.py scripts/imagegen_pipeline/handoff/contracts.py scripts/imagegen_pipeline/handoff/common.py scripts/imagegen_pipeline/imagegen_handoff.py tests/test_imagegen_handoff_modularization.py
git commit -m "refactor: extract imagegen handoff contracts"
```

---

### Task 3: 提取页面语义和文字处理

**Files:**
- Create: `scripts/imagegen_pipeline/handoff/semantics.py`
- Create: `scripts/imagegen_pipeline/handoff/text.py`
- Modify: `scripts/imagegen_pipeline/handoff/__init__.py`
- Modify: `scripts/imagegen_pipeline/imagegen_handoff.py:605-1370`
- Modify: `tests/test_imagegen_handoff_modularization.py`

**Interfaces:**
- Consumes: `contracts.py`、`common.py`、现有 `ScriptPage` 和语义/文字依赖。
- Produces: `resolve_page_visual_intent(...)`、`select_page_visual_intent_type(...)`、`resolve_page_semantic_intent(...)`、`audit_page_semantic_intent(...)`、`build_page_visual_intent(...)`、`build_page_creative_brief(...)`、`content_lock_text(...)`、`diagnostic_onscreen_text(...)`、`resolve_onscreen_judgment_mode(...)`、`locked_onscreen_text(...)`、`select_image_locked_text(...)`、`render_semantic_visual_brief(...)`、`resolve_text_render_mode(...)`。

- [ ] **Step 1: 写语义和文字函数对象身份测试**

```python
def test_semantic_and_text_functions_are_direct_reexports() -> None:
    legacy = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    semantics = importlib.import_module(
        "scripts.imagegen_pipeline.handoff.semantics"
    )
    text = importlib.import_module("scripts.imagegen_pipeline.handoff.text")
    assert legacy.audit_page_semantic_intent is semantics.audit_page_semantic_intent
    assert legacy.build_page_visual_intent is semantics.build_page_visual_intent
    assert legacy.select_image_locked_text is text.select_image_locked_text
    assert legacy.content_lock_text is text.content_lock_text
```

- [ ] **Step 2: 运行测试确认目标模块缺失**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 目标模块导入失败。

- [ ] **Step 3: 迁移语义实现并建立单向依赖**

按函数组原样迁移页面关系、视觉意图、语义意图、语义审计、页面视觉意图和创意简报构建。`semantics.py` 只能依赖 `contracts.py`、`common.py` 及已有外部模块，不得导入旧门面或 `prompt.py`。

- [ ] **Step 4: 迁移文字实现并保持可读文字白名单行为**

迁移锁定文字、上屏文字、表格扁平化、语义摘要和文字渲染模式。文字模块必须继续使用原来的 `ONSCREEN_ASIDE_RE`、锁定文本规则和文本模式值，不重新拼接提示词文案。

- [ ] **Step 5: 运行语义、文字和基线测试**

Run:

```bash
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_imagegen_no_visual_structure \
  tests.test_semantic_intent \
  tests.test_imagegen_creative_brief \
  tests.test_final_script_pages -v
```

Expected: 所有当前可由 `unittest` 执行的测试通过，行为基线逐字段一致。

- [ ] **Step 6: 提交语义和文字层**

```bash
git add scripts/imagegen_pipeline/handoff/semantics.py scripts/imagegen_pipeline/handoff/text.py scripts/imagegen_pipeline/handoff/__init__.py scripts/imagegen_pipeline/imagegen_handoff.py tests/test_imagegen_handoff_modularization.py
git commit -m "refactor: extract imagegen handoff semantics and text"
```

---

### Task 4: 提取视觉呈现决策和页面逻辑契约

**Files:**
- Create: `scripts/imagegen_pipeline/handoff/presentation.py`
- Modify: `scripts/imagegen_pipeline/handoff/__init__.py`
- Modify: `scripts/imagegen_pipeline/imagegen_handoff.py:1387-1892`
- Modify: `tests/test_imagegen_handoff_modularization.py`

**Interfaces:**
- Consumes: 语义层、文字层、Style lock 和既有视觉载体解析器。
- Produces: `PresentationDecision`、`resolve_visual_medium(...)`、`select_dense_supporting_facts(...)`、`resolve_presentation_decision(...)`、`render_content_first_style_contract(...)`、`resolve_visual_center(...)`、`render_visual_center_contract(...)`、`resolve_visual_carrier(...)`、`render_visual_carrier_contract(...)`、`compact_visual_structure_for_logic(...)`、`render_page_logic_contract(...)`。

- [ ] **Step 1: 写视觉决策对象身份和字段快照测试**

```python
def test_presentation_decision_is_not_wrapped() -> None:
    legacy = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    presentation = importlib.import_module(
        "scripts.imagegen_pipeline.handoff.presentation"
    )
    assert legacy.PresentationDecision is presentation.PresentationDecision
    assert legacy.resolve_presentation_decision is presentation.resolve_presentation_decision
```

- [ ] **Step 2: 运行测试确认新模块缺失**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 目标模块导入失败。

- [ ] **Step 3: 原样迁移视觉决策和契约渲染**

迁移 `PresentationDecision` 及其相关函数，保持 dataclass 字段顺序、默认值、返回字典键顺序和契约文本不变。若视觉模块需要语义或文字函数，只允许沿既定方向导入，不得反向导入 `prompt.py`。

- [ ] **Step 4: 运行视觉和基线测试**

Run:

```bash
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_extended_style_9 \
  tests.test_extended_style_10 \
  tests.test_imagegen_no_visual_structure \
  tests.test_artifact_prompt -v
```

Expected: PASS，`PresentationDecision` 全字段和页面逻辑契约与基线一致。

- [ ] **Step 5: 提交视觉层**

```bash
git add scripts/imagegen_pipeline/handoff/presentation.py scripts/imagegen_pipeline/handoff/__init__.py scripts/imagegen_pipeline/imagegen_handoff.py tests/test_imagegen_handoff_modularization.py
git commit -m "refactor: extract imagegen handoff presentation"
```

---

### Task 5: 提取提示词编译器

**Files:**
- Create: `scripts/imagegen_pipeline/handoff/prompt.py`
- Modify: `scripts/imagegen_pipeline/handoff/__init__.py`
- Modify: `scripts/imagegen_pipeline/imagegen_handoff.py:1893-2447`
- Modify: `tests/test_imagegen_handoff_modularization.py`

**Interfaces:**
- Consumes: `contracts.py`、语义、文字和视觉决策模块，以及既有 `deliverable_prompt`、`prompt_compiler`、`artifact_prompt` 外部接口。
- Produces: `render_content_first_prompt(...)`、`compile_page_prompt(...)`、`build_page_prompt(...)`。

- [ ] **Step 1: 写提示词结构化等价测试**

```python
def test_page_prompt_matches_baseline() -> None:
    legacy = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    result = legacy.build_page_prompt(BASELINE_PAGE, BASELINE_OPTIONS)
    assert normalize_prompt(result) == BASELINE_PROMPTS["build_page_prompt"]
```

此外，分别断言九段顺序、锁定文字白名单和画布/模板禁绘契约仍存在；不得只比较提示词长度或哈希。

- [ ] **Step 2: 运行测试确认新 prompt 模块缺失**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 目标模块导入失败或对象身份测试失败。

- [ ] **Step 3: 迁移提示词编译实现**

将提示词字段准备、分节拼装和页面提示词入口原样迁入 `prompt.py`。保留函数签名、参数默认值、字段顺序、换行规则和所有提示词片段。提示词模块不得执行文件写入或解析 CLI 参数。

- [ ] **Step 4: 运行提示词和全链路定向测试**

Run:

```bash
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_imagegen_page_manifest \
  tests.test_final_script_pages \
  tests.test_extended_style_9 \
  tests.test_extended_style_10 \
  tests.test_artifact_prompt -v
```

Expected: 所有提示词基线逐字一致；下游调用方仍可从旧路径导入。

- [ ] **Step 5: 提交提示词编译层**

```bash
git add scripts/imagegen_pipeline/handoff/prompt.py scripts/imagegen_pipeline/handoff/__init__.py scripts/imagegen_pipeline/imagegen_handoff.py tests/test_imagegen_handoff_modularization.py
git commit -m "refactor: extract imagegen handoff prompt compiler"
```

---

### Task 6: 提取交付写入和 CLI

**Files:**
- Create: `scripts/imagegen_pipeline/handoff/delivery.py`
- Create: `scripts/imagegen_pipeline/handoff/cli.py`
- Modify: `scripts/imagegen_pipeline/handoff/__init__.py`
- Modify: `scripts/imagegen_pipeline/imagegen_handoff.py:2448-2767`
- Modify: `tests/test_imagegen_handoff_modularization.py`

**Interfaces:**
- Consumes: `prompt.py`、既有 `atomic_write_text`、`build_lock`、诊断写入和脚本交接工具。
- Produces: `write_chapter_handoff(...)`、`main(argv: list[str] | None = None) -> int`，并保持直接脚本运行入口。

- [ ] **Step 1: 写交付路径和 CLI 行为测试**

```python
def test_write_chapter_handoff_preserves_relative_outputs(tmp_path: Path) -> None:
    result = delivery.write_chapter_handoff(BASELINE_HANDOFF_INPUT, tmp_path)
    assert sorted(path.relative_to(tmp_path).as_posix() for path in tmp_path.rglob("*")) == BASELINE_OUTPUTS
    assert result == BASELINE_HANDOFF_RESULT


def test_main_help_and_invalid_input_keep_exit_contract() -> None:
    assert cli.main(["--help"]) == 0
    assert cli.main(["--missing-input"]) == BASELINE_INVALID_EXIT_CODE
```

- [ ] **Step 2: 运行测试确认目标模块缺失**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 目标模块导入失败。

- [ ] **Step 3: 迁移交付和 CLI 实现**

将原写入顺序、目录创建、原子写入、构建锁、诊断文件和章节交接逻辑迁入 `delivery.py`。将 `argparse`、命令分支、错误处理和直接脚本执行迁入 `cli.py`。保留 `if __package__ in {None, ""}` 的 sys.path 兼容行为，但只放在最外层入口。

- [ ] **Step 4: 运行交付、CLI 和完整 ImageGen 定向测试**

Run:

```bash
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_imagegen_page_manifest \
  tests.test_final_script_pages \
  tests.test_artifact_prompt \
  tests.test_semantic_intent -v
```

Expected: 文件相对路径、内容、命令退出码和错误类型与基线一致。

- [ ] **Step 5: 提交交付和 CLI 层**

```bash
git add scripts/imagegen_pipeline/handoff/delivery.py scripts/imagegen_pipeline/handoff/cli.py scripts/imagegen_pipeline/handoff/__init__.py scripts/imagegen_pipeline/imagegen_handoff.py tests/test_imagegen_handoff_modularization.py
git commit -m "refactor: extract imagegen handoff delivery and cli"
```

---

### Task 7: 收敛兼容门面

**Files:**
- Modify: `scripts/imagegen_pipeline/imagegen_handoff.py`
- Modify: `scripts/imagegen_pipeline/handoff/__init__.py`
- Modify: `tests/test_imagegen_handoff_modularization.py`

**Interfaces:**
- Consumes: 全部内部职责模块的迁移后对象。
- Produces: 不超过 200 行、显式导出完整兼容符号的原路径门面。

- [ ] **Step 1: 写门面规模、AST 和完整符号测试**

```python
def test_facade_is_small_and_contains_no_implementation() -> None:
    module = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    source = Path(module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert len(source.splitlines()) <= 200
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        for node in tree.body
    )


def test_facade_exports_frozen_symbols() -> None:
    module = importlib.import_module(
        "scripts.imagegen_pipeline.imagegen_handoff"
    )
    assert set(FROZEN_SYMBOLS) <= set(getattr(module, "__all__", ()))
    assert all(hasattr(module, name) for name in FROZEN_SYMBOLS)
```

- [ ] **Step 2: 运行测试确认当前门面仍超限或含实现**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 在门面尚未收敛时失败。

- [ ] **Step 3: 显式重导出并收敛原文件**

只保留模块说明、直接运行兼容处理、显式 imports、`__all__` 和兼容说明。对测试或内部脚本使用的下划线函数逐项导出，不使用通配导入，不创建包装函数。

- [ ] **Step 4: 运行全套定向测试并比较行为快照**

Run:

```bash
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_imagegen_creative_brief \
  tests.test_imagegen_no_visual_structure \
  tests.test_imagegen_page_manifest \
  tests.test_final_script_pages \
  tests.test_extended_style_9 \
  tests.test_extended_style_10 \
  tests.test_artifact_prompt \
  tests.test_semantic_intent -v
```

Expected: 兼容符号全部可用，提示词和结构化结果 fixture 完全一致。

- [ ] **Step 5: 提交兼容门面**

```bash
git add scripts/imagegen_pipeline/imagegen_handoff.py scripts/imagegen_pipeline/handoff/__init__.py tests/test_imagegen_handoff_modularization.py
git commit -m "refactor: finalize imagegen handoff facade"
```

---

### Task 8: 固化依赖边界并完成全量回归

**Files:**
- Modify: `tests/test_imagegen_handoff_modularization.py`
- Modify: `docs/superpowers/specs/2026-08-15-imagegen-handoff-modularization-design.md`（仅更新状态为“已实施”）

**Interfaces:**
- Consumes: 完整 `scripts.imagegen_pipeline.handoff` 包和兼容门面。
- Produces: 自动防止内部循环依赖、门面回退实现和新增导入期副作用的架构测试。

- [ ] **Step 1: 写依赖图和门面边界测试**

```python
def test_handoff_dependency_graph_has_no_nontrivial_scc() -> None:
    graph = build_internal_dependency_graph(HANDOFF_DIR)
    components = strongly_connected_components(graph)
    assert [component for component in components if len(component) > 1] == []


def test_internal_modules_do_not_import_legacy_facade() -> None:
    offenders = scan_for_text(HANDOFF_DIR, "imagegen_handoff")
    assert offenders == []
```

依赖扫描必须包含模块级和函数体内 `Import`/`ImportFrom`，不能只检查顶层导入。

- [ ] **Step 2: 临时注入反向导入确认测试有效，再撤销临时改动**

Run: `python -m unittest tests.test_imagegen_handoff_modularization -v`

Expected: 临时注入时 SCC 测试失败；撤销临时改动后通过。临时注入不得提交。

- [ ] **Step 3: 运行静态检查和 ImageGen 定向回归**

Run:

```bash
git diff --check
python -m compileall -q scripts/imagegen_pipeline/handoff scripts/imagegen_pipeline/imagegen_handoff.py
python -m unittest \
  tests.test_imagegen_handoff_modularization \
  tests.test_imagegen_creative_brief \
  tests.test_imagegen_no_visual_structure \
  tests.test_imagegen_page_manifest \
  tests.test_final_script_pages \
  tests.test_extended_style_9 \
  tests.test_extended_style_10 \
  tests.test_artifact_prompt \
  tests.test_semantic_intent
```

Expected: 退出码为 0，行为 fixture 一致。

- [ ] **Step 4: 运行仓库完整测试集**

Run: `python -m unittest discover -s tests`

Expected: 不低于拆分前基线，不新增 failure、error 或 skip。若 pytest 风格测试未由 unittest discovery 执行，单独运行 `python -m pytest` 并记录与基线的差异。

- [ ] **Step 5: 检查最终规模和变更范围**

Run:

```bash
wc -l scripts/imagegen_pipeline/imagegen_handoff.py scripts/imagegen_pipeline/handoff/*.py
rg -n "imagegen_handoff" scripts/imagegen_pipeline/handoff || true
git status --short
git diff --check
```

Expected: 门面不超过 200 行；内部包无旧门面导入；工作区没有临时产物。

- [ ] **Step 6: 更新设计状态并提交最终约束**

```bash
git add tests/test_imagegen_handoff_modularization.py docs/superpowers/specs/2026-08-15-imagegen-handoff-modularization-design.md
git commit -m "test: enforce imagegen handoff module boundaries"
```

## Final Verification Checklist

- [ ] 原路径公开符号和事实私有接口均可导入。
- [ ] 页面语义、视觉决策、锁定文字和提示词输出与基线一致。
- [ ] 交付文件路径、文件名、内容和 CLI 退出码与基线一致。
- [ ] `imagegen_handoff.py` 不超过 200 行且不包含业务实现。
- [ ] 内部包无循环依赖、无反向门面导入、无函数体导入掩盖循环。
- [ ] ImageGen 定向测试通过。
- [ ] `python -m unittest discover -s tests` 通过且无新增跳过。
- [ ] 没有修改提示词规则、Style 09/10、页面脚本格式或其他模块。

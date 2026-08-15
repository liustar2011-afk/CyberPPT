# Script Quality Contract Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `cyberppt/script_quality_contract.py` 拆分为职责清晰的内部包，同时保持原导入路径、审计规则、错误顺序和输出结果完全兼容。

**Architecture:** 新建 `cyberppt/script_quality/`，按模型、解析、文字规则、屏显规则、源覆盖、页面呈现、跨页关系、最终稿和审计编排拆分。原 `script_quality_contract.py` 最终只作为显式再导出的兼容门面，内部模块保持单向依赖且不反向导入门面。

**Tech Stack:** Python 3.10+、标准库 `dataclasses`/`pathlib`/`json`/`re`、现有 `unittest` 测试体系、Ruff/现有仓库质量命令（如已配置）。

## Global Constraints

- 仅拆分 `cyberppt/script_quality_contract.py`，不同时处理其他大型模块。
- 拆分前后解析结果、问题数量、问题顺序、错误码、严重级别、页码、说明、修复建议、命令退出状态和序列化结果必须一致。
- 保留 `cyberppt.script_quality_contract` 现有公开导入路径。
- 当前被测试或仓库代码直接使用的下划线辅助函数继续由兼容门面再导出。
- 子模块不得导入 `cyberppt.script_quality_contract`。
- 不修改规则、阈值、事实强度、标题风格、输出文案或命令行接口。
- 兼容门面目标不超过 200 行，且不承载规则实现。
- 每个迁移任务先增加失败测试，再做最小迁移，随后运行针对性测试并提交。

---

## File Structure

### Create

- `cyberppt/script_quality/__init__.py`：内部包稳定入口及显式公共导出。
- `cyberppt/script_quality/models.py`：`ScriptPage`、`ScriptDocument`、`ScriptQualityIssue`、`PageRelationshipSummary` 及纯类型定义。
- `cyberppt/script_quality/parsing.py`：脚本、字段、来源引用、讲稿备注和 sidecar 解析。
- `cyberppt/script_quality/text_rules.py`：政企写作、禁用句式、口语、标题和讲稿文本规则。
- `cyberppt/script_quality/onscreen.py`：上屏层级、密度、并列、流程语言和 ImageGen 上屏准备度。
- `cyberppt/script_quality/source_coverage.py`：来源消费、全文覆盖、段落边界、内容单元和模块来源审查。
- `cyberppt/script_quality/presentation.py`：视觉结构、页面呈现、预检语义和讲稿边界审查。
- `cyberppt/script_quality/relationships.py`：业务关系解析、前置条件和跨页连续性审查。
- `cyberppt/script_quality/final_form.py`：最终脚本路径和最终稿形态审查。
- `cyberppt/script_quality/audit.py`：`audit_script_quality`、通信审查、语义摘要和重试指令编排。
- `tests/test_script_quality_modularization.py`：兼容接口、模块边界、导入方向和行为冻结测试。
- `tests/fixtures/script_quality_contract_baseline.json`：拆分前固定样本的结构化结果基线。

### Modify

- `cyberppt/script_quality_contract.py`：逐步迁出实现，最终改为兼容门面。
- `tests/test_script_quality_contract.py`：仅在需要时补充跨模块回归样本；不迁移现有原路径导入，以持续验证兼容性。

### Do Not Modify

- `cyberppt/commands/*.py`、`cyberppt/stage02_handoff.py`、`cyberppt/semantic_digest.py`；它们继续通过原路径验证兼容性。
- `scripts/imagegen_pipeline/*.py`；现有原路径导入保持不变。
- 任何审计规则常量的值、错误码或消息文案。

---

### Task 1: 冻结公开接口与行为基线

**Files:**
- Create: `tests/test_script_quality_modularization.py`
- Create: `tests/fixtures/script_quality_contract_baseline.json`
- Read: `cyberppt/script_quality_contract.py`
- Read: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes: 当前 `cyberppt.script_quality_contract` 的实际导出符号和 `parse_script_markdown(...)`、`audit_script_quality(...)` 返回结构。
- Produces: `COMPAT_SYMBOLS: tuple[str, ...]`、固定输入 `BASELINE_SCRIPT`、结构化函数 `serialize_document(...)` 和 `serialize_issues(...)`，供后续所有任务验证行为等价。

- [ ] **Step 1: 写兼容符号和结构化结果测试**

在 `tests/test_script_quality_modularization.py` 中明确列出仓库当前使用的符号，不使用动态“导出全部名称”方式：

```python
from __future__ import annotations

from dataclasses import asdict
import importlib
import json
from pathlib import Path
import unittest


COMPAT_SYMBOLS = (
    "ScriptPage", "ScriptDocument", "ScriptQualityIssue",
    "parse_script_markdown", "parse_script_path",
    "audit_script_quality", "audit_final_manuscript_form",
    "assert_imagegen_onscreen_readiness", "build_communication_review",
    "extract_speaker_notes", "meaningful_char_count",
    "onscreen_effective_char_target", "onscreen_semantic_coverage",
    "onscreen_story_roles", "parse_selection_notes",
    "selection_notes_are_structured", "script_retry_directive",
    "text_similarity", "audience_facing_group_label",
    "strip_authoring_group_marker", "resolve_judgment_mode",
    "is_final_script_path", "_prohibited_contrast_hits",
    "_prohibited_colloquial_hits", "_unlabeled_onscreen_bullets",
    "_mechanical_evidence_bullets", "_compound_module_heading_hits",
    "_module_heading_colon_hits", "_negative_foreground_issues",
    "_generic_onscreen_relation_hits",
    "_mechanical_onscreen_label_pattern_hits",
    "_onscreen_detail_phrase_overages", "_onscreen_layout_meta_hits",
    "_onscreen_parent_child_role_mismatches",
    "_onscreen_subordinate_fragments", "_onscreen_false_parallel_semantics",
    "_onscreen_parallel_structure_issues", "_necessity_page_closure_issues",
    "_onscreen_flow_language_issues", "_formulaic_transition_issues",
    "_speaker_placeholder_hits", "_issue", "_presentation_issues",
    "_prohibited_contrast_issues", "_prose_issues",
    "_source_consumption_issues", "_full_prose_source_coverage_issues",
    "_full_prose_paragraph_boundary_issues", "_polarity_dropped_terms",
    "_page_content_unit_coverage_issues", "_model_slot_coverage_issues",
    "_onscreen_module_provenance_issues",
    "_visual_structure_judgment_issues",
    "_page_relationship_continuity_issues",
)


class ScriptQualityCompatibilityTests(unittest.TestCase):
    def test_legacy_module_exports_used_contract(self) -> None:
        module = importlib.import_module("cyberppt.script_quality_contract")
        missing = [name for name in COMPAT_SYMBOLS if not hasattr(module, name)]
        self.assertEqual([], missing)
```

固定样本至少包含内容页、来源引用、上屏文字、视觉结构、讲稿和一项可稳定触发的问题。序列化时使用数据字段，不比较 `repr`：

```python
def json_value(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def serialize_issues(issues: list[object]) -> list[dict[str, object]]:
    return json_value([asdict(issue) for issue in issues])


def test_baseline_fixture_matches_current_contract(self) -> None:
    module = importlib.import_module("cyberppt.script_quality_contract")
    document = module.parse_script_markdown(BASELINE_SCRIPT)
    actual = {
        "document": json_value(asdict(document)),
        "issues": serialize_issues(module.audit_script_quality(document)),
    }
    expected = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    self.assertEqual(expected, actual)
```

- [ ] **Step 2: 运行测试，确认基线文件尚不存在时失败**

Run: `python -m unittest tests.test_script_quality_modularization -v`

Expected: FAIL，原因是 `tests/fixtures/script_quality_contract_baseline.json` 尚不存在。

- [ ] **Step 3: 使用当前未拆分实现生成并审阅固定 JSON 基线**

通过一次性 Python 命令调用测试文件中的固定样本和序列化函数，将结果写入 `tests/fixtures/script_quality_contract_baseline.json`。生成后人工检查 JSON 中包含完整页面字段和完整 issue 顺序，不保留对象地址、绝对临时路径或时间戳。

- [ ] **Step 4: 运行基线和现有核心测试**

Run: `python -m unittest tests.test_script_quality_modularization tests.test_script_quality_contract -v`

Expected: PASS。

- [ ] **Step 5: 提交行为冻结测试**

```bash
git add tests/test_script_quality_modularization.py tests/fixtures/script_quality_contract_baseline.json
git commit -m "test: freeze script quality contract behavior"
```

---

### Task 2: 提取数据模型并建立内部包

**Files:**
- Create: `cyberppt/script_quality/__init__.py`
- Create: `cyberppt/script_quality/models.py`
- Modify: `cyberppt/script_quality_contract.py:278-391,5035-5063`
- Modify: `tests/test_script_quality_modularization.py`

**Interfaces:**
- Consumes: 原 `resolve_judgment_mode(...)`、`ScriptPage`、`ScriptDocument`、`ScriptQualityIssue`、`PageRelationshipSummary` 的字段、默认值和方法。
- Produces: `cyberppt.script_quality.models` 中同名对象；兼容门面再导出相同对象身份。

- [ ] **Step 1: 写内部模型导入与对象身份测试**

```python
def test_models_are_reexported_without_wrapper_types(self) -> None:
    legacy = importlib.import_module("cyberppt.script_quality_contract")
    models = importlib.import_module("cyberppt.script_quality.models")
    self.assertIs(legacy.ScriptPage, models.ScriptPage)
    self.assertIs(legacy.ScriptDocument, models.ScriptDocument)
    self.assertIs(legacy.ScriptQualityIssue, models.ScriptQualityIssue)
```

- [ ] **Step 2: 运行测试，确认内部模型模块不存在**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_models_are_reexported_without_wrapper_types -v`

Expected: ERROR，`ModuleNotFoundError: cyberppt.script_quality`。

- [ ] **Step 3: 原样迁移模型和判定模式函数**

在 `models.py` 中保留原装饰器、字段顺序、默认值、类型注解和方法体；不得重新定义兼容包装类。`__init__.py` 显式导出：

```python
from .models import (
    PageRelationshipSummary,
    ScriptDocument,
    ScriptPage,
    ScriptQualityIssue,
    resolve_judgment_mode,
)

__all__ = [
    "PageRelationshipSummary", "ScriptDocument", "ScriptPage",
    "ScriptQualityIssue", "resolve_judgment_mode",
]
```

在兼容门面当前位置改为从 `models` 导入，后续尚未迁移的函数继续引用这些导入对象。

- [ ] **Step 4: 运行模型、基线和现有核心测试**

Run: `python -m unittest tests.test_script_quality_modularization tests.test_script_quality_contract -v`

Expected: PASS，且基线 JSON 完全一致。

- [ ] **Step 5: 提交模型迁移**

```bash
git add cyberppt/script_quality/__init__.py cyberppt/script_quality/models.py cyberppt/script_quality_contract.py tests/test_script_quality_modularization.py
git commit -m "refactor: extract script quality models"
```

---

### Task 3: 提取脚本解析能力

**Files:**
- Create: `cyberppt/script_quality/parsing.py`
- Modify: `cyberppt/script_quality/__init__.py`
- Modify: `cyberppt/script_quality_contract.py:30-277,393-1213`
- Modify: `tests/test_script_quality_modularization.py`

**Interfaces:**
- Consumes: `ScriptPage`、`ScriptDocument`、解析常量和当前字段规范化逻辑。
- Produces: `parse_script_markdown(text: str, ...) -> ScriptDocument`、`parse_script_path(path: Path) -> ScriptDocument`、`load_page_contract_sidecar(...)`、`extract_speaker_notes(...)`、`extract_page_contract_receipt(...)`、`audience_facing_group_label(...)`、`strip_authoring_group_marker(...)`。

- [ ] **Step 1: 写解析函数对象身份与基线测试**

```python
def test_parsing_functions_are_reexported_directly(self) -> None:
    legacy = importlib.import_module("cyberppt.script_quality_contract")
    parsing = importlib.import_module("cyberppt.script_quality.parsing")
    self.assertIs(legacy.parse_script_markdown, parsing.parse_script_markdown)
    self.assertIs(legacy.parse_script_path, parsing.parse_script_path)
    self.assertIs(legacy.extract_speaker_notes, parsing.extract_speaker_notes)
```

- [ ] **Step 2: 运行测试，确认 parsing 模块不存在**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_parsing_functions_are_reexported_directly -v`

Expected: ERROR，`ModuleNotFoundError: cyberppt.script_quality.parsing`。

- [ ] **Step 3: 迁移解析常量和函数，保持签名与求值顺序**

把模块顶部至 `parse_script_path` 后、以及解析直接使用的私有辅助函数一起迁移。`parsing.py` 只能导入 `models.py` 和既有外部模块，不得导入兼容门面。兼容门面显式导入公开解析函数和当前测试使用的解析辅助函数。

- [ ] **Step 4: 运行解析相关测试和行为基线**

Run:

```bash
python -m unittest \
  tests.test_script_quality_modularization \
  tests.test_script_quality_contract \
  tests.test_semantic_intent \
  tests.test_final_script_pages -v
```

Expected: PASS。

- [ ] **Step 5: 提交解析迁移**

```bash
git add cyberppt/script_quality/parsing.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_modularization.py
git commit -m "refactor: extract script quality parsing"
```

---

### Task 4: 提取文字规则与上屏规则

**Files:**
- Create: `cyberppt/script_quality/text_rules.py`
- Create: `cyberppt/script_quality/onscreen.py`
- Modify: `cyberppt/script_quality/__init__.py`
- Modify: `cyberppt/script_quality_contract.py:1304-1414,1907-2750,3423-3459,3617-4171`
- Modify: `tests/test_script_quality_modularization.py`

**Interfaces:**
- Consumes: `ScriptPage`、`ScriptQualityIssue`、解析模块提供的分组标题和上屏文本辅助能力。
- Produces: `meaningful_char_count(...)`、`onscreen_effective_char_target(...)`、`parse_selection_notes(...)`、`selection_notes_are_structured(...)`、`assert_imagegen_onscreen_readiness(...)`、`onscreen_semantic_coverage(...)`、`onscreen_story_roles(...)`、`_prose_issues(...)` 及现有文字/上屏私有规则函数。

- [ ] **Step 1: 写规则归属与兼容导出测试**

```python
def test_text_and_onscreen_rules_are_direct_reexports(self) -> None:
    legacy = importlib.import_module("cyberppt.script_quality_contract")
    text_rules = importlib.import_module("cyberppt.script_quality.text_rules")
    onscreen = importlib.import_module("cyberppt.script_quality.onscreen")
    self.assertIs(legacy._prohibited_contrast_hits, text_rules._prohibited_contrast_hits)
    self.assertIs(legacy._prohibited_colloquial_hits, text_rules._prohibited_colloquial_hits)
    self.assertIs(legacy._unlabeled_onscreen_bullets, onscreen._unlabeled_onscreen_bullets)
    self.assertIs(legacy.assert_imagegen_onscreen_readiness, onscreen.assert_imagegen_onscreen_readiness)
```

- [ ] **Step 2: 运行测试，确认两个目标模块尚不存在**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_text_and_onscreen_rules_are_direct_reexports -v`

Expected: ERROR，目标模块未创建。

- [ ] **Step 3: 按语义归属迁移函数，不复制共享常量**

将纯措辞检查、讲稿文本问题和 `_prose_issues` 放入 `text_rules.py`；将上屏层级、密度、并列、流程语言及 ImageGen 准备度放入 `onscreen.py`。若两者共享 `_issue(...)`，将 `_issue(...)` 放入 `models.py` 或由 `models.py` 提供单一实现，禁止复制。

- [ ] **Step 4: 运行文字、上屏、命令和基线测试**

Run:

```bash
python -m unittest \
  tests.test_script_quality_modularization \
  tests.test_script_quality_contract \
  tests.test_script_audit_command \
  tests.test_imagegen_no_visual_structure \
  tests.test_imagegen_creative_brief -v
```

Expected: PASS，问题顺序和消息文本与基线一致。

- [ ] **Step 5: 提交文字与上屏迁移**

```bash
git add cyberppt/script_quality/text_rules.py cyberppt/script_quality/onscreen.py cyberppt/script_quality/models.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_modularization.py
git commit -m "refactor: extract script text and onscreen rules"
```

---

### Task 5: 提取来源覆盖与通信审查能力

**Files:**
- Create: `cyberppt/script_quality/source_coverage.py`
- Modify: `cyberppt/script_quality/audit.py`（若尚不存在则在本任务创建，仅先放 `build_communication_review`）
- Modify: `cyberppt/script_quality/__init__.py`
- Modify: `cyberppt/script_quality_contract.py:1214-1303,1415-1906,2751-3422`
- Modify: `tests/test_script_quality_modularization.py`

**Interfaces:**
- Consumes: `ScriptDocument`、`ScriptPage`、`ScriptQualityIssue`、`models._issue(...)`、`onscreen` 的字符计数和故事角色能力。
- Produces: `normalized_tokens(...)`、`text_similarity(...)`、来源消费/全文覆盖/段落边界/内容单元/模块来源/模型槽位检查，以及 `build_communication_review(...)`。

- [ ] **Step 1: 写来源覆盖函数对象身份测试**

```python
def test_source_coverage_functions_are_direct_reexports(self) -> None:
    legacy = importlib.import_module("cyberppt.script_quality_contract")
    coverage = importlib.import_module("cyberppt.script_quality.source_coverage")
    self.assertIs(legacy.text_similarity, coverage.text_similarity)
    self.assertIs(legacy._source_consumption_issues, coverage._source_consumption_issues)
    self.assertIs(legacy._full_prose_source_coverage_issues, coverage._full_prose_source_coverage_issues)
```

- [ ] **Step 2: 运行测试，确认 source_coverage 模块尚不存在**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_source_coverage_functions_are_direct_reexports -v`

Expected: ERROR，目标模块未创建。

- [ ] **Step 3: 迁移来源覆盖函数并保持原调用顺序**

将 token、相似度、极性遗漏、来源消费、全文覆盖、段落边界、内容单元、模块来源、模型槽位覆盖迁入 `source_coverage.py`。`build_communication_review(...)` 放入 `audit.py`，只组合既有结构，不改返回字典键名和顺序。

- [ ] **Step 4: 运行来源忠实链路和基线测试**

Run:

```bash
python -m unittest \
  tests.test_script_quality_modularization \
  tests.test_script_quality_contract \
  tests.test_source_faithful_artifact_chain \
  tests.test_semantic_intent -v
```

Expected: PASS。

- [ ] **Step 5: 提交来源覆盖迁移**

```bash
git add cyberppt/script_quality/source_coverage.py cyberppt/script_quality/audit.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_modularization.py
git commit -m "refactor: extract script source coverage rules"
```

---

### Task 6: 提取页面呈现、最终稿和跨页关系规则

**Files:**
- Create: `cyberppt/script_quality/presentation.py`
- Create: `cyberppt/script_quality/final_form.py`
- Create: `cyberppt/script_quality/relationships.py`
- Modify: `cyberppt/script_quality/__init__.py`
- Modify: `cyberppt/script_quality_contract.py:4111-5283`
- Modify: `tests/test_script_quality_modularization.py`

**Interfaces:**
- Consumes: `ScriptPage`、`ScriptDocument`、`ScriptQualityIssue`、`PageRelationshipSummary` 和来源/文字/上屏模块提供的稳定函数。
- Produces: `_presentation_issues(...)`、`_preflight_semantic_issues(...)`、`_visual_structure_judgment_issues(...)`、`is_final_script_path(...)`、`audit_final_manuscript_form(...)`、`_page_relationship_continuity_issues(...)`。

- [ ] **Step 1: 写三个规则域的对象身份测试**

```python
def test_presentation_final_form_and_relationships_are_reexported(self) -> None:
    legacy = importlib.import_module("cyberppt.script_quality_contract")
    presentation = importlib.import_module("cyberppt.script_quality.presentation")
    final_form = importlib.import_module("cyberppt.script_quality.final_form")
    relationships = importlib.import_module("cyberppt.script_quality.relationships")
    self.assertIs(legacy._presentation_issues, presentation._presentation_issues)
    self.assertIs(legacy.audit_final_manuscript_form, final_form.audit_final_manuscript_form)
    self.assertIs(
        legacy._page_relationship_continuity_issues,
        relationships._page_relationship_continuity_issues,
    )
```

- [ ] **Step 2: 运行测试，确认目标模块尚不存在**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_presentation_final_form_and_relationships_are_reexported -v`

Expected: ERROR，至少一个目标模块未创建。

- [ ] **Step 3: 原样迁移三个规则域并解开反向引用**

视觉结构、呈现和预检语义进入 `presentation.py`；最终路径和稿件形态进入 `final_form.py`；关系解析、关系可见性、前置条件和连续性进入 `relationships.py`。共享模型使用 `models.py`，不得从兼容门面导入。

- [ ] **Step 4: 运行视觉、最终稿、关系和基线测试**

Run:

```bash
python -m unittest \
  tests.test_script_quality_modularization \
  tests.test_script_quality_contract \
  tests.test_visual_proof_preflight_diagnostics \
  tests.test_visual_structure_stage \
  tests.test_assemble_final_script \
  tests.test_final_script_pages -v
```

Expected: PASS。

- [ ] **Step 5: 提交页面呈现、最终稿和关系迁移**

```bash
git add cyberppt/script_quality/presentation.py cyberppt/script_quality/final_form.py cyberppt/script_quality/relationships.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_modularization.py
git commit -m "refactor: extract script presentation and relationship rules"
```

---

### Task 7: 提取总审计编排并收敛兼容门面

**Files:**
- Modify: `cyberppt/script_quality/audit.py`
- Modify: `cyberppt/script_quality/__init__.py`
- Rewrite: `cyberppt/script_quality_contract.py:1-5812`
- Modify: `tests/test_script_quality_modularization.py`

**Interfaces:**
- Consumes: 各规则模块的检查函数及原 `audit_script_quality(...)` 的完整签名和固定调用顺序。
- Produces: `audit_script_quality(...)`、`script_retry_directive(...)` 和不超过 200 行的原路径兼容门面。

- [ ] **Step 1: 写总编排对象身份和门面规模测试**

```python
def test_audit_is_direct_reexport_and_facade_is_small(self) -> None:
    legacy = importlib.import_module("cyberppt.script_quality_contract")
    audit = importlib.import_module("cyberppt.script_quality.audit")
    self.assertIs(legacy.audit_script_quality, audit.audit_script_quality)
    self.assertIs(legacy.script_retry_directive, audit.script_retry_directive)
    facade = Path(legacy.__file__).read_text(encoding="utf-8")
    self.assertLessEqual(len(facade.splitlines()), 200)
```

- [ ] **Step 2: 运行测试，确认门面规模仍超限或函数尚未迁移**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_audit_is_direct_reexport_and_facade_is_small -v`

Expected: FAIL，兼容门面仍超过 200 行或对象身份不同。

- [ ] **Step 3: 将总编排迁入 `audit.py` 并重写兼容门面**

`audit.py` 必须按原 `audit_script_quality(...)` 中的先后顺序调用各规则函数，不使用集合去重或新排序。兼容门面只写模块说明、显式 imports 和 `__all__`；对现有测试直接导入的私有函数逐项显式再导出，不使用 `from ... import *`。

- [ ] **Step 4: 运行行为基线和所有已知调用方测试**

Run:

```bash
python -m unittest \
  tests.test_script_quality_modularization \
  tests.test_script_quality_contract \
  tests.test_script_audit_command \
  tests.test_semantic_intent \
  tests.test_assemble_final_script \
  tests.test_final_script_pages \
  tests.test_visual_proof_preflight_diagnostics \
  tests.test_artifact_prompt \
  tests.test_imagegen_page_manifest -v
```

Expected: PASS，基线 JSON 逐字段一致。

- [ ] **Step 5: 提交编排和兼容门面**

```bash
git add cyberppt/script_quality/audit.py cyberppt/script_quality/__init__.py cyberppt/script_quality_contract.py tests/test_script_quality_modularization.py
git commit -m "refactor: finalize script quality compatibility facade"
```

---

### Task 8: 固化依赖边界并完成全量回归

**Files:**
- Modify: `tests/test_script_quality_modularization.py`
- Modify: `docs/superpowers/specs/2026-08-15-script-quality-contract-modularization-design.md`（仅将状态改为“已实施”，不改设计内容）

**Interfaces:**
- Consumes: 完整 `cyberppt.script_quality` 包和兼容门面。
- Produces: 可自动执行的无反向导入、全模块可导入、门面无实现回归约束。

- [ ] **Step 1: 写架构边界测试**

```python
def test_internal_modules_do_not_import_legacy_facade(self) -> None:
    package_dir = Path(__file__).parents[1] / "cyberppt" / "script_quality"
    offenders = []
    for path in sorted(package_dir.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        if "script_quality_contract" in text:
            offenders.append(path.name)
    self.assertEqual([], offenders)


def test_all_internal_modules_import_cleanly(self) -> None:
    names = (
        "models", "parsing", "text_rules", "onscreen", "source_coverage",
        "presentation", "relationships", "final_form", "audit",
    )
    for name in names:
        with self.subTest(name=name):
            importlib.import_module(f"cyberppt.script_quality.{name}")
```

- [ ] **Step 2: 临时加入反向导入字符串，确认边界测试会失败，再撤销该临时改动**

Run: `python -m unittest tests.test_script_quality_modularization.ScriptQualityCompatibilityTests.test_internal_modules_do_not_import_legacy_facade -v`

Expected: 临时改动存在时 FAIL；撤销临时改动后 PASS。临时改动不得提交。

- [ ] **Step 3: 运行静态检查和针对性回归**

Run:

```bash
git diff --check
python -m compileall -q cyberppt/script_quality cyberppt/script_quality_contract.py
python -m unittest tests.test_script_quality_modularization tests.test_script_quality_contract -v
```

Expected: 全部命令退出码为 0。

- [ ] **Step 4: 运行仓库完整测试集**

Run: `python -m unittest discover -s tests`

Expected: 当前完整基线测试全部通过；允许保持原有 skipped 数量，不允许新增 failure 或 error。

- [ ] **Step 5: 检查变更范围与设计约束**

Run:

```bash
git status --short
git diff --stat HEAD~7..HEAD
wc -l cyberppt/script_quality_contract.py cyberppt/script_quality/*.py
rg -n "script_quality_contract" cyberppt/script_quality
```

Expected: 变更只涉及本计划文件；门面不超过 200 行；最后一条命令无输出；无运行产物或临时文件待提交。

- [ ] **Step 6: 更新设计状态并提交最终验证约束**

```bash
git add tests/test_script_quality_modularization.py docs/superpowers/specs/2026-08-15-script-quality-contract-modularization-design.md
git commit -m "test: enforce script quality module boundaries"
```

---

## Final Verification Checklist

- [ ] 原路径的公开符号和现有事实私有接口均可导入。
- [ ] `tests/fixtures/script_quality_contract_baseline.json` 与实际输出完全一致。
- [ ] issue 数量、顺序、代码、严重级别、页码、消息和修复建议均未变化。
- [ ] `cyberppt/script_quality_contract.py` 不超过 200 行且无规则实现。
- [ ] 内部模块没有导入兼容门面。
- [ ] 所有新增模块可独立导入，无循环依赖。
- [ ] 针对性测试通过。
- [ ] `python -m unittest discover -s tests` 全部通过且无新增跳过。
- [ ] `git diff --check` 通过，工作区无测试产物和临时文件。

# Native Script Quality Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a native `cyberppt script-audit` gate that audits PPT scripts against strict Outline and Source Truth contracts before script approval and Stage 02 production.

**Architecture:** Parse the existing Markdown page-script format into immutable dataclasses, then run deterministic pure-contract checks in `cyberppt/script_quality_contract.py`. Keep persistence, attempts, Markdown rendering, escalation, and artifact-ledger updates in `cyberppt/commands/script_audit.py`; register only a thin adapter in `cyberppt/cli.py`.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `hashlib`, `json`, `pathlib`, `re`, `unicodedata`), `unittest`/pytest-compatible tests, existing CyberPPT CLI and project contracts.

## Global Constraints

- Use solution architecture by default; do not introduce consulting/SCR defaults.
- Reuse `outline.json` and `source-truth.json`; do not create a parallel project lifecycle.
- Keep deterministic auditing separate from script generation; the command reports issues but never rewrites script text.
- Default to three changed-direction attempts; valid `max_attempts` range is 1 through 5.
- Exit codes are `0` passed, `2` input/persistence error, `4` rewrite required, and `5` user decision required.
- A partial batch script is audited only for pages present in that batch.
- Strict Outline mode requires Source Truth and fails closed when it is missing.
- Preserve formal states such as `拟建议`, `首期建议`, `待确认`, `待摸底`, `待基线`, `暂缓`, `后续验证`, and conditional wording.
- Do not migrate `project_manager.py`, dual-reading workspaces, editor/red-team runtimes, case libraries, old assemble/handoff commands, or old directory layouts.
- Before modifying any existing function, class, or method, run `gitnexus impact <symbol> --direction upstream`; warn before HIGH or CRITICAL edits.
- Before every commit, run `gitnexus detect-changes --scope staged`.
- Preserve unrelated dirty-worktree files and stage only files owned by the current task.

---

## File Structure

### New files

- `cyberppt/script_quality_contract.py` — Markdown parser, immutable script model, issue model, deterministic audits, retry strategy.
- `cyberppt/commands/script_audit.py` — command orchestration, reports, attempts, escalation, ledger registration.
- `tests/test_script_quality_contract.py` — parser and pure-rule tests.
- `tests/test_script_audit_command.py` — command, attempts, reports, ledger, and exit-code tests.
- `references/script-quality.md` — authoritative script-writing and audit rules.

### Modified files

- `cyberppt/cli.py` — import command, adapter, parser registration.
- `cyberppt/commands/init_project.py` — create `workbench/scripts/audits/attempts`, expose manifest path, document gate.
- `tests/test_cli.py` — CLI discovery, defaults, exit-code behavior.
- `tests/test_init_project.py` if present; otherwise `tests/test_cli.py` — initialized project scaffold expectations.
- `tests/test_skill_contract.py` — Skill route and script-audit gate assertions.
- `SKILL.md` — concise native script-audit entry and Stage 01→02 gate.

---

### Task 1: Script Markdown Model and Parser

**Files:**
- Create: `cyberppt/script_quality_contract.py`
- Create: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes: UTF-8 Markdown using headings such as `## 第13页：第三章：建设内容与应用安排`.
- Produces:

```python
@dataclass(frozen=True)
class ScriptPage:
    page_id: str
    sequence: int
    heading: str
    page_type: str
    title: str
    main_message: str
    source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]

@dataclass(frozen=True)
class ScriptDocument:
    pages: tuple[ScriptPage, ...]

def parse_script_markdown(text: str) -> ScriptDocument: ...
```

- [ ] **Step 1: Write parser tests for the accepted batch-script format**

```python
from cyberppt.script_quality_contract import parse_script_markdown


SCRIPT = """# 第8—9页脚本审稿稿

## 第8页：第二章：定位、目标与研究边界

- 页面类型：章节过渡页
- 上屏文字：第二章：定位、目标与研究边界

## 第9页：总体定位

- 页面类型：内容页
- 页面标题：总体定位
- 主判断：初步定位为面向行业的公共能力。
- 上屏文字：

  **行业公共能力**

  - 服务行业研判。

  **专业系统边界**

  - 保留专业职责边界。

- 证据：S015、S026、S059
- 边界：正式范围待后续确定。
- 视觉结构：公共能力定位与职责边界图。
"""


def test_parse_script_markdown_extracts_pages_and_fields() -> None:
    document = parse_script_markdown(SCRIPT)
    assert [page.page_id for page in document.pages] == ["p08", "p09"]
    assert document.pages[0].page_type == "chapter"
    assert document.pages[1].title == "总体定位"
    assert document.pages[1].source_refs == ("S015", "S026", "S059")
    assert document.pages[1].module_titles == ("行业公共能力", "专业系统边界")
```

- [ ] **Step 2: Run the parser test and verify RED**

Run:

```powershell
python -m pytest tests/test_script_quality_contract.py::test_parse_script_markdown_extracts_pages_and_fields -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'cyberppt.script_quality_contract'`.

- [ ] **Step 3: Implement immutable models and minimal parser**

Add:

```python
"""Deterministic PPT script parsing and quality contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re


PAGE_HEADING_RE = re.compile(r"^##\s+第(\d+)页[：:](.+?)\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$")
MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
SOURCE_RE = re.compile(r"S\d{3}")


@dataclass(frozen=True)
class ScriptPage:
    page_id: str
    sequence: int
    heading: str
    page_type: str
    title: str
    main_message: str
    source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]


@dataclass(frozen=True)
class ScriptDocument:
    pages: tuple[ScriptPage, ...]


def _normalize_page_type(value: str) -> str:
    if "章节" in value:
        return "chapter"
    if "封面" in value:
        return "cover"
    if "目录" in value:
        return "contents"
    if "封底" in value:
        return "closing"
    return "content"


def _page_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(PAGE_HEADING_RE.finditer(text))
    return [
        (
            int(match.group(1)),
            match.group(2).strip(),
            text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)],
        )
        for index, match in enumerate(matches)
    ]


def _field_blocks(body: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    active = ""
    for raw_line in body.splitlines():
        match = FIELD_RE.match(raw_line)
        if match:
            active = match.group(1).strip()
            blocks[active] = [match.group(2).strip()]
        elif active:
            blocks[active].append(raw_line.rstrip())
    return {key: "\n".join(lines).strip() for key, lines in blocks.items()}


def parse_script_markdown(text: str) -> ScriptDocument:
    pages: list[ScriptPage] = []
    for sequence, heading, body in _page_sections(text):
        fields = _field_blocks(body)
        onscreen = fields.get("上屏文字", "")
        modules = tuple(
            match.group(1).strip()
            for line in onscreen.splitlines()
            if (match := MODULE_RE.match(line))
        )
        pages.append(
            ScriptPage(
                page_id=f"p{sequence:02d}",
                sequence=sequence,
                heading=heading,
                page_type=_normalize_page_type(fields.get("页面类型", "")),
                title=fields.get("页面标题", heading).strip(),
                main_message=fields.get("主判断", "").strip(),
                source_refs=tuple(SOURCE_RE.findall(fields.get("证据", ""))),
                boundary=fields.get("边界", "").strip(),
                visual_structure=fields.get("视觉结构", "").strip(),
                onscreen_text=onscreen,
                module_titles=modules,
            )
        )
    if not pages:
        raise ValueError("script contains no page headings")
    return ScriptDocument(tuple(pages))
```

- [ ] **Step 4: Add malformed-input and multiline-field tests**

```python
import pytest


def test_parse_script_markdown_rejects_document_without_pages() -> None:
    with pytest.raises(ValueError, match="no page headings"):
        parse_script_markdown("# empty")


def test_onscreen_block_stops_at_next_backend_field() -> None:
    page = parse_script_markdown(SCRIPT).pages[1]
    assert "- 证据：" not in page.onscreen_text
    assert "S015" not in page.onscreen_text
```

- [ ] **Step 5: Run parser tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_script_quality_contract.py -q
```

Expected: all parser tests PASS.

- [ ] **Step 6: Stage, inspect with GitNexus, and commit**

Run:

```powershell
git add -- cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
gitnexus detect-changes --scope staged
git commit -m "feat: parse CyberPPT page scripts"
```

Expected: only the new parser and parser tests are staged; GitNexus risk is low or no indexed changes.

---

### Task 2: Page Contract, Source State, and Argument-Order Audits

**Files:**
- Modify: `cyberppt/script_quality_contract.py`
- Modify: `tests/test_script_quality_contract.py`

**Interfaces:**
- Consumes:

```python
def audit_script_quality(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
) -> list[ScriptQualityIssue]: ...
```

- Produces:

```python
@dataclass(frozen=True)
class ScriptQualityIssue:
    code: str
    severity: str
    message: str
    pages: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    suggested_action: str = ""

    def to_dict(self) -> dict[str, object]: ...
```

- [ ] **Step 1: Run required upstream impact analysis before editing the parser symbol**

Run:

```powershell
gitnexus impact parse_script_markdown --direction upstream
```

Expected: direct callers are tests only at this point. If risk is HIGH or CRITICAL, stop and warn the user before editing.

- [ ] **Step 2: Write failing tests for page contracts and partial batches**

```python
from cyberppt.script_quality_contract import audit_script_quality


def strict_outline(*pages: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "pages": list(pages)}


def source_truth(*records: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "records": list(records)}


def test_partial_batch_does_not_require_absent_outline_pages() -> None:
    script = parse_script_markdown(SCRIPT)
    outline = strict_outline(
        {"page_id": "p08", "sequence": 8, "page_type": "chapter", "title": "第二章：定位、目标与研究边界"},
        {"page_id": "p09", "sequence": 9, "page_type": "content", "title": "总体定位",
         "argument_role": "positioning", "source_refs": ["S015", "S026", "S059"],
         "prerequisite_pages": ["p07"], "main_claim_status": "proposed"},
        {"page_id": "p10", "sequence": 10, "page_type": "content", "title": "能力框架",
         "argument_role": "solution", "source_refs": ["S017"], "prerequisite_pages": ["p09"]},
    )
    truth = source_truth(
        {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
        {"id": "S026", "type": "B", "status": "研究边界", "statement": "不替代专业系统。"},
        {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待确定。"},
    )
    assert audit_script_quality(script, outline, truth) == []


def test_chapter_page_with_main_message_is_rejected() -> None:
    bad = SCRIPT.replace(
        "- 上屏文字：第二章：定位、目标与研究边界",
        "- 主判断：本章明确完整建设方案。\\n- 上屏文字：第二章：定位、目标与研究边界",
    )
    issues = audit_script_quality(
        parse_script_markdown(bad),
        strict_outline({"page_id": "p08", "sequence": 8, "page_type": "chapter",
                        "title": "第二章：定位、目标与研究边界"}),
        source_truth(),
    )
    assert "CHAPTER_PAGE_HAS_CONTENT" in {issue.code for issue in issues}
```

- [ ] **Step 3: Write failing regression tests for premature scope and state upgrades**

```python
def test_foundation_page_cannot_claim_first_phase_scope() -> None:
    script = parse_script_markdown("""## 第4页：工作基础
- 页面类型：内容页
- 页面标题：工作基础
- 主判断：现有基础能够直接支撑首期建设全国总盘和定期报告。
- 上屏文字：
  **既有基础**
  - 已具备统计和报告工作。
- 证据：S006
- 边界：本页陈述既有事实。
- 视觉结构：工作基础链。
""")
    outline = strict_outline({
        "page_id": "p04", "sequence": 4, "page_type": "content", "title": "工作基础",
        "argument_role": "foundation", "source_refs": ["S006"],
        "prerequisite_pages": [], "main_claim_status": "confirmed",
    })
    truth = source_truth({
        "id": "S006", "type": "F", "status": "已形成",
        "statement": "具备行业协调基础。",
    })
    codes = {issue.code for issue in audit_script_quality(script, outline, truth)}
    assert "PREMATURE_SCOPE_CLAIM" in codes


def test_proposed_source_cannot_be_upgraded_to_completed() -> None:
    script = parse_script_markdown("""## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：已经建成面向行业的公共能力。
- 上屏文字：
  **公共能力**
  - 已完成建设。
- 证据：S015
- 边界：正式范围待确定。
- 视觉结构：定位图。
""")
    outline = strict_outline({
        "page_id": "p09", "sequence": 9, "page_type": "content", "title": "总体定位",
        "argument_role": "positioning", "source_refs": ["S015"],
        "prerequisite_pages": ["p07"], "main_claim_status": "proposed",
    })
    truth = source_truth({
        "id": "S015", "type": "B", "status": "拟建议",
        "statement": "初步考虑将本项建设定位为公共能力。",
    })
    codes = {issue.code for issue in audit_script_quality(script, outline, truth)}
    assert "SOURCE_STATE_UPGRADED" in codes
```

- [ ] **Step 4: Run focused tests and verify RED**

Run:

```powershell
python -m pytest tests/test_script_quality_contract.py -q
```

Expected: FAIL because `ScriptQualityIssue` and `audit_script_quality` do not exist.

- [ ] **Step 5: Implement issue model and page/source indexes**

Add:

```python
@dataclass(frozen=True)
class ScriptQualityIssue:
    code: str
    severity: str
    message: str
    pages: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    suggested_action: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "pages": list(self.pages),
            "source_ids": list(self.source_ids),
            "evidence": list(self.evidence),
            "suggested_action": self.suggested_action,
        }


def _dict_items(payload: dict[str, object], key: str) -> list[dict[str, object]]:
    value = payload.get(key)
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _outline_pages(outline: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(page.get("page_id")): page for page in _dict_items(outline, "pages")}


def _truth_records(source_truth: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(record.get("id")): record for record in _dict_items(source_truth, "records")}
```

- [ ] **Step 6: Implement deterministic contract checks**

Add constants and checks:

```python
SCOPE_TERMS = ("首期", "一期", "建设范围", "交付范围", "投资", "部署方式", "采购")
IMPLEMENTATION_TERMS = ("实施路线", "建设周期", "前100天", "组织组建", "预算")
COMPLETED_TERMS = ("已经建成", "已建成", "已经形成完整", "已完成建设", "正式确定")
CONDITIONAL_STATUSES = ("拟", "建议", "待", "暂缓", "后续验证", "条件成熟")


def _page_text(page: ScriptPage) -> str:
    return "\n".join((page.title, page.main_message, page.onscreen_text, page.boundary))


def _issue(code: str, page: ScriptPage, message: str, action: str,
           source_ids: tuple[str, ...] = (), evidence: tuple[str, ...] = ()) -> ScriptQualityIssue:
    return ScriptQualityIssue(
        code=code,
        severity="error",
        message=message,
        pages=(page.page_id,),
        source_ids=source_ids,
        evidence=evidence,
        suggested_action=action,
    )


def audit_script_quality(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    pages_by_id = _outline_pages(outline)
    records_by_id = _truth_records(source_truth)
    sequences = [page.sequence for page in script.pages]
    if sequences != list(range(min(sequences), max(sequences) + 1)):
        issues.append(ScriptQualityIssue(
            "SCRIPT_PAGE_SEQUENCE_GAP", "error", "Script batch page numbers must be continuous.",
            tuple(page.page_id for page in script.pages),
            suggested_action="Restore the missing page or split the input into explicit continuous batches.",
        ))
    for page in script.pages:
        contract = pages_by_id.get(page.page_id)
        if contract is None:
            issues.append(_issue(
                "SCRIPT_PAGE_NOT_IN_OUTLINE", page,
                "Script page has no matching Outline contract.",
                "Add the page to the approved Outline or remove it from the script batch.",
            ))
            continue
        expected_type = str(contract.get("page_type") or "")
        if expected_type == "chapter" and (
            page.page_type != "chapter" or page.main_message or page.module_titles
        ):
            issues.append(_issue(
                "CHAPTER_PAGE_HAS_CONTENT", page,
                "Chapter transition pages may contain only the chapter title.",
                "Remove the thesis, modules, methods, and task text from this page.",
            ))
        if expected_type == "content":
            if not page.main_message or not page.source_refs or not page.visual_structure:
                issues.append(_issue(
                    "CONTENT_PAGE_FIELDS_MISSING", page,
                    "Content page requires main judgment, evidence, and visual structure.",
                    "Restore the missing backend fields before review.",
                ))
            expected_refs = tuple(str(item) for item in contract.get("source_refs", []) if item)
            missing = tuple(item for item in expected_refs if item not in page.source_refs)
            if missing:
                issues.append(_issue(
                    "SCRIPT_SOURCE_REF_MISSING", page,
                    "Script does not cite all Source IDs assigned by the Outline.",
                    "Restore the assigned Source IDs or revise the approved Outline contract.",
                    missing,
                ))
        unknown = tuple(item for item in page.source_refs if item not in records_by_id)
        if unknown:
            issues.append(_issue(
                "SCRIPT_SOURCE_REF_UNKNOWN", page,
                "Script cites Source IDs that do not resolve in Source Truth.",
                "Correct the references before script approval.",
                unknown,
            ))
        role = str(contract.get("argument_role") or "")
        text = _page_text(page)
        if role in {"foundation", "change", "gap", "necessity"}:
            matched = tuple(term for term in SCOPE_TERMS if term in text)
            if matched:
                issues.append(_issue(
                    "PREMATURE_SCOPE_CLAIM", page,
                    "Page introduces scope or delivery claims before the scope stage.",
                    "Keep this page within its argument role and move scope claims to the approved scope page.",
                    evidence=matched,
                ))
        if role in {"foundation", "change", "gap", "necessity", "positioning", "solution", "scope"}:
            matched = tuple(term for term in IMPLEMENTATION_TERMS if term in text)
            if matched:
                issues.append(_issue(
                    "PREMATURE_IMPLEMENTATION_CLAIM", page,
                    "Page introduces implementation claims before the implementation stage.",
                    "Move implementation details to pages whose argument role is implementation or assurance.",
                    evidence=matched,
                ))
        conditional_sources = tuple(
            ref for ref in page.source_refs
            if any(token in str(records_by_id.get(ref, {}).get("status") or "") for token in CONDITIONAL_STATUSES)
        )
        completed = tuple(term for term in COMPLETED_TERMS if term in text)
        if conditional_sources and completed:
            issues.append(_issue(
                "SOURCE_STATE_UPGRADED", page,
                "Conditional or proposed evidence is written as completed or formally decided.",
                "Restore proposed, conditional, pending, or deferred wording from Source Truth.",
                conditional_sources,
                completed,
            ))
    return issues
```

- [ ] **Step 7: Run contract tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_script_quality_contract.py -q
```

Expected: all page contract, partial batch, premature scope, and state tests PASS.

- [ ] **Step 8: Stage, detect impact, and commit**

Run:

```powershell
git add -- cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
gitnexus detect-changes --scope staged
git commit -m "feat: audit script contracts and argument order"
```

Expected: changed symbols are limited to script-quality contracts and tests.

---

### Task 3: Repetition, Semantic-Diagram, and Density Audits

**Files:**
- Modify: `cyberppt/script_quality_contract.py`
- Modify: `tests/test_script_quality_contract.py`

**Interfaces:**
- Extends `audit_script_quality(...)` with deterministic presentation checks.
- Adds:

```python
def normalized_tokens(text: str) -> tuple[str, ...]: ...
def text_similarity(left: str, right: str) -> float: ...
```

- [ ] **Step 1: Run upstream impact analysis**

Run:

```powershell
gitnexus impact audit_script_quality --direction upstream
```

Expected: callers are the focused tests. Warn before editing if risk is HIGH or CRITICAL.

- [ ] **Step 2: Write failing repetition tests**

```python
def test_adjacent_pages_with_same_main_message_are_rejected() -> None:
    duplicate = """## 第14页：业务体系
- 页面类型：内容页
- 页面标题：业务体系
- 主判断：统一数据和模型支撑报告生产与审核发布。
- 上屏文字：
  **业务对象**
  - 覆盖供需研判。
- 证据：S017
- 边界：拟建议。
- 视觉结构：对象矩阵。

## 第15页：成果闭环
- 页面类型：内容页
- 页面标题：成果闭环
- 主判断：统一数据和模型支撑报告生产与审核发布。
- 上屏文字：
  **成果生产**
  - 覆盖报告生产。
- 证据：S020
- 边界：拟建议。
- 视觉结构：成果闭环。
"""
    issues = audit_script_quality(
        parse_script_markdown(duplicate),
        strict_outline(
            {"page_id": "p14", "sequence": 14, "page_type": "content", "title": "业务体系",
             "argument_role": "solution", "source_refs": ["S017"], "prerequisite_pages": []},
            {"page_id": "p15", "sequence": 15, "page_type": "content", "title": "成果闭环",
             "argument_role": "solution", "source_refs": ["S020"], "prerequisite_pages": ["p14"]},
        ),
        source_truth(
            {"id": "S017", "type": "R", "status": "拟建议", "statement": "业务体系。"},
            {"id": "S020", "type": "R", "status": "拟建议", "statement": "成果产品。"},
        ),
    )
    assert "ADJACENT_MAIN_MESSAGE_DUPLICATE" in {issue.code for issue in issues}


def test_short_bridge_does_not_trigger_full_text_duplicate() -> None:
    assert text_similarity("承接前页的数据治理基础", "数据治理提供可信输入") < 0.72
```

- [ ] **Step 3: Write failing semantic-diagram tests**

```python
def test_path_visual_requires_order_signal() -> None:
    script = parse_script_markdown("""## 第12页：研究任务
- 页面类型：内容页
- 页面标题：研究任务
- 主判断：四项任务形成研究证据。
- 上屏文字：
  **资源摸底**
  - 形成清单。
  **问题量化**
  - 形成基线。
  **首期设计**
  - 形成方案。
  **原型验证**
  - 形成结果。
- 证据：S014
- 边界：不决定投资。
- 视觉结构：四步任务路径图。
""")
    issues = audit_script_quality(
        script,
        strict_outline({"page_id": "p12", "sequence": 12, "page_type": "content",
                        "title": "研究任务", "argument_role": "decision",
                        "source_refs": ["S014"], "prerequisite_pages": []}),
        source_truth({"id": "S014", "type": "U", "status": "待确认", "statement": "四项研究任务。"}),
    )
    assert "PATH_ORDER_SIGNAL_MISSING" in {issue.code for issue in issues}


def test_declared_count_must_match_modules() -> None:
    text = SCRIPT.replace("初步定位为面向行业的公共能力。", "形成五类能力。")
    issues = audit_script_quality(
        parse_script_markdown(text),
        strict_outline(
            {"page_id": "p08", "sequence": 8, "page_type": "chapter", "title": "第二章：定位、目标与研究边界"},
            {"page_id": "p09", "sequence": 9, "page_type": "content", "title": "总体定位",
             "argument_role": "solution", "source_refs": ["S015", "S026", "S059"],
             "prerequisite_pages": []},
        ),
        source_truth(
            {"id": "S015", "type": "R", "status": "拟建议", "statement": "能力。"},
            {"id": "S026", "type": "B", "status": "研究边界", "statement": "边界。"},
            {"id": "S059", "type": "B", "status": "研究边界", "statement": "边界。"},
        ),
    )
    assert "DECLARED_COUNT_MISMATCH" in {issue.code for issue in issues}
```

- [ ] **Step 4: Write failing density tests**

```python
def test_content_page_with_one_short_module_is_too_sparse() -> None:
    sparse = """## 第10页：能力框架
- 页面类型：内容页
- 页面标题：能力框架
- 主判断：形成能力。
- 上屏文字：
  **能力**
  - 提升研判。
- 证据：S017
- 边界：拟建议。
- 视觉结构：能力图。
"""
    issues = audit_script_quality(
        parse_script_markdown(sparse),
        strict_outline({"page_id": "p10", "sequence": 10, "page_type": "content",
                        "title": "能力框架", "argument_role": "solution",
                        "source_refs": ["S017"], "prerequisite_pages": []}),
        source_truth({"id": "S017", "type": "R", "status": "拟建议", "statement": "能力。"}),
    )
    assert "CONTENT_PAGE_TOO_SPARSE" in {issue.code for issue in issues}
```

- [ ] **Step 5: Run focused tests and verify RED**

Run:

```powershell
python -m pytest tests/test_script_quality_contract.py -q
```

Expected: FAIL because similarity and visual/density checks are absent.

- [ ] **Step 6: Implement token similarity**

Add:

```python
import unicodedata


def normalized_tokens(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"S\d{3}", " ", normalized)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    compact = "".join(normalized.split())
    if len(compact) < 3:
        return tuple(compact)
    return tuple(compact[index : index + 3] for index in range(len(compact) - 2))


def text_similarity(left: str, right: str) -> float:
    left_set = set(normalized_tokens(left))
    right_set = set(normalized_tokens(right))
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)
```

- [ ] **Step 7: Implement repetition, diagram, count, and density helpers**

Add:

```python
COUNT_WORDS = {"二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8}
ORDER_SIGNALS = ("①", "②", "③", "④", "⑤", "→", "随后", "再", "最后")
LOOP_SIGNALS = ("回流", "反馈", "复盘", "闭环", "持续校正")
MATRIX_SIGNALS = ("|---", "×", "矩阵", "行", "列")
LAYER_SIGNALS = ("自下而上", "自上而下", "底座", "层", "贯穿")


def _declared_count(text: str) -> int | None:
    match = re.search(r"([二两三四五六七八])(?:类|项|步|层)", text)
    return COUNT_WORDS.get(match.group(1)) if match else None


def _presentation_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    full_text = _page_text(page)
    visual = page.visual_structure
    if "路径" in visual and not any(signal in page.onscreen_text for signal in ORDER_SIGNALS):
        issues.append(_issue(
            "PATH_ORDER_SIGNAL_MISSING", page,
            "Path visual lacks an on-screen order signal.",
            "Add numbered steps, arrows, or explicit sequence words matching the path.",
        ))
    if "闭环" in visual and not any(signal in full_text for signal in LOOP_SIGNALS):
        issues.append(_issue(
            "LOOP_RETURN_SIGNAL_MISSING", page,
            "Loop visual lacks an on-screen return or feedback relation.",
            "Name the feedback, review, or correction link on screen.",
        ))
    if "矩阵" in visual and not any(signal in page.onscreen_text for signal in MATRIX_SIGNALS):
        issues.append(_issue(
            "MATRIX_AXES_MISSING", page,
            "Matrix visual lacks identifiable rows and columns.",
            "Provide the row objects and column dimensions in the on-screen structure.",
        ))
    if ("分层" in visual or "架构" in visual) and not any(signal in full_text for signal in LAYER_SIGNALS):
        issues.append(_issue(
            "LAYER_HIERARCHY_MISSING", page,
            "Layered visual lacks an explicit hierarchy relation.",
            "Name the layers, support relation, or top-to-bottom reading order.",
        ))
    count = _declared_count(page.main_message + "\n" + page.onscreen_text)
    if count is not None and page.module_titles and len(page.module_titles) != count:
        issues.append(_issue(
            "DECLARED_COUNT_MISMATCH", page,
            f"Declared count {count} does not match {len(page.module_titles)} on-screen modules.",
            "Align the declared count and the visible module structure.",
            evidence=(str(count), str(len(page.module_titles))),
        ))
    visible_chars = len(re.sub(r"\s+", "", page.onscreen_text))
    if page.page_type == "content" and (visible_chars < 80 or len(page.module_titles) < 2):
        issues.append(_issue(
            "CONTENT_PAGE_TOO_SPARSE", page,
            "Content page lacks enough evidence-bearing on-screen structure.",
            "Add source-supported modules or merge this page with the adjacent business question.",
            evidence=(f"chars={visible_chars}", f"modules={len(page.module_titles)}"),
        ))
    if page.page_type == "content" and len(page.module_titles) > 5 and not any(
        signal in page.onscreen_text for signal in ORDER_SIGNALS + LAYER_SIGNALS
    ):
        issues.append(_issue(
            "MODULE_HIERARCHY_MISSING", page,
            "More than five modules are presented without grouping or hierarchy.",
            "Group modules under explicit stages or layers, or split independent conclusions.",
        ))
    return issues
```

Extend `audit_script_quality` after per-page contract checks:

```python
        issues.extend(_presentation_issues(page))

    for left, right in zip(script.pages, script.pages[1:]):
        similarity = text_similarity(left.main_message, right.main_message)
        if similarity >= 0.82:
            issues.append(ScriptQualityIssue(
                "ADJACENT_MAIN_MESSAGE_DUPLICATE",
                "error",
                "Adjacent pages repeat substantially the same main judgment.",
                (left.page_id, right.page_id),
                evidence=(left.main_message, right.main_message, f"similarity={similarity:.3f}"),
                suggested_action="Keep the complete argument on one page and make the adjacent page advance a different business question.",
            ))
```

- [ ] **Step 8: Run all contract tests and calibrate only with explicit fixtures**

Run:

```powershell
python -m pytest tests/test_script_quality_contract.py -q
```

Expected: all tests PASS. If a threshold changes, add one passing and one failing fixture that justify the exact threshold.

- [ ] **Step 9: Stage, detect impact, and commit**

Run:

```powershell
git add -- cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
gitnexus detect-changes --scope staged
git commit -m "feat: audit script composition and repetition"
```

Expected: only the pure contract and its tests are staged.

---

### Task 4: Persistent Script-Audit Command, Attempts, Reports, and Ledger

**Files:**
- Create: `cyberppt/commands/script_audit.py`
- Create: `tests/test_script_audit_command.py`

**Interfaces:**
- Consumes:

```python
def run_script_audit(
    project: Path,
    input_path: Path,
    outline_path: Path | None = None,
    source_truth_path: Path | None = None,
    attempt: int | None = None,
    max_attempts: int = 3,
) -> tuple[int, dict[str, object]]: ...
```

- Produces latest JSON, Markdown, attempt JSON, optional escalation JSON, and artifact-ledger entries.

- [ ] **Step 1: Write failing command success test**

```python
from pathlib import Path
import json

from cyberppt.commands.script_audit import run_script_audit


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def test_run_script_audit_persists_passed_reports_and_ledger(tmp_path: Path) -> None:
    project = tmp_path / "project"
    analysis = project / "workbench" / "stages" / "01-analysis"
    script = project / "workbench" / "scripts" / "drafts" / "p08-p09.md"
    script.parent.mkdir(parents=True)
    script.write_text(SCRIPT, encoding="utf-8")
    write_json(analysis / "outline.json", strict_outline(
        {"page_id": "p08", "sequence": 8, "page_type": "chapter",
         "title": "第二章：定位、目标与研究边界"},
        {"page_id": "p09", "sequence": 9, "page_type": "content",
         "title": "总体定位", "argument_role": "positioning",
         "source_refs": ["S015", "S026", "S059"], "prerequisite_pages": []},
    ))
    write_json(analysis / "source-truth.json", source_truth(
        {"id": "S015", "type": "B", "status": "拟建议", "statement": "初步定位。"},
        {"id": "S026", "type": "B", "status": "研究边界", "statement": "专业边界。"},
        {"id": "S059", "type": "B", "status": "研究边界", "statement": "正式范围待定。"},
    ))
    write_json(project / "workbench" / "artifact-ledger.json",
               {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []})

    code, report = run_script_audit(project, script)

    assert code == 0
    assert report["status"] == "passed"
    audit_dir = project / "workbench" / "scripts" / "audits"
    assert (audit_dir / "script-audit.json").exists()
    assert (audit_dir / "script-audit.md").exists()
    assert (audit_dir / "attempts" / "attempt-01.json").exists()
    ledger = json.loads((project / "workbench" / "artifact-ledger.json").read_text(encoding="utf-8"))
    assert any(item["path"] == "workbench/scripts/audits/script-audit.json"
               for item in ledger["artifacts"])
```

- [ ] **Step 2: Write failing retry and escalation tests**

```python
def test_attempts_auto_increment_and_change_strategy(tmp_path: Path) -> None:
    project, script = failing_foundation_project(tmp_path)
    code1, report1 = run_script_audit(project, script, max_attempts=3)
    code2, report2 = run_script_audit(project, script, max_attempts=3)
    assert code1 == 4 and code2 == 4
    assert report1["attempt"] == 1 and report2["attempt"] == 2
    assert report1["retry_directive"]["strategy"] != report2["retry_directive"]["strategy"]


def test_max_attempt_returns_user_decision_options(tmp_path: Path) -> None:
    project, script = failing_foundation_project(tmp_path)
    code, report = run_script_audit(project, script, attempt=3, max_attempts=3)
    assert code == 5
    assert report["status"] == "user_decision_required"
    assert 2 <= len(report["options"]) <= 3
```

- [ ] **Step 3: Run command tests and verify RED**

Run:

```powershell
python -m pytest tests/test_script_audit_command.py -q
```

Expected: FAIL because `cyberppt.commands.script_audit` does not exist.

- [ ] **Step 4: Implement retry strategy in the pure contract**

Before editing, run:

```powershell
gitnexus impact audit_script_quality --direction upstream
```

Then add:

```python
STRATEGY_ORDER = (
    "mission_restructure",
    "source_state_rebuild",
    "cross_page_dedup",
    "semantic_diagram_realign",
    "density_recompose",
)


def script_retry_directive(
    issues: list[ScriptQualityIssue],
    previous_strategy: str = "",
) -> dict[str, object]:
    codes = sorted({issue.code for issue in issues})
    preferred = (
        "source_state_rebuild"
        if any(code in {"SOURCE_STATE_UPGRADED", "BOUNDARY_DROPPED", "UNRESOLVED_AS_CONFIRMED"} for code in codes)
        else "cross_page_dedup"
        if any("DUPLICATE" in code or "REEXPANDED" in code for code in codes)
        else "semantic_diagram_realign"
        if any(code.endswith(("MISSING", "MISMATCH")) and code.startswith(("PATH_", "LOOP_", "MATRIX_", "LAYER_", "DECLARED_"))
               for code in codes)
        else "density_recompose"
        if any(code in {"CONTENT_PAGE_TOO_SPARSE", "CONTENT_PAGE_TOO_FRAGMENTED", "MODULE_HIERARCHY_MISSING"} for code in codes)
        else "mission_restructure"
    )
    strategy = preferred
    if strategy == previous_strategy:
        index = (STRATEGY_ORDER.index(strategy) + 1) % len(STRATEGY_ORDER)
        strategy = STRATEGY_ORDER[index]
    return {
        "required": bool(issues),
        "issue_codes": codes,
        "strategy": strategy,
        "instruction": "Rewrite only the failed pages using the new strategy; preserve valid evidence, states, and page contracts.",
    }
```

- [ ] **Step 5: Implement command persistence and Markdown renderer**

Create `cyberppt/commands/script_audit.py` with:

```python
"""Persist script quality audits, changed-direction retries, and readable reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cyberppt.outline_contract import load_outline
from cyberppt.script_quality_contract import (
    ScriptQualityIssue,
    audit_script_quality,
    parse_script_markdown,
    script_retry_directive,
)
from cyberppt.source_truth_contract import load_source_truth


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _next_attempt(attempts_dir: Path) -> int:
    numbers = [
        int(path.stem.split("-")[-1])
        for path in attempts_dir.glob("attempt-*.json")
        if path.stem.split("-")[-1].isdigit()
    ]
    return max(numbers, default=0) + 1


def _render_markdown(report: dict[str, object]) -> str:
    lines = [
        "# PPT 脚本质量审计",
        "",
        f"- 状态：`{report['status']}`",
        f"- 尝试：{report['attempt']} / {report['max_attempts']}",
        f"- 页面：{report['coverage']['page_count']}",
        f"- 问题：{len(report['issues'])}",
        "",
        "## 失败页面",
        "",
    ]
    failed = report.get("failed_pages", [])
    lines.append("、".join(failed) if failed else "无。")
    lines.extend(["", "## 问题", ""])
    for issue in report.get("issues", []):
        lines.extend([
            f"### {issue['code']}",
            "",
            f"- 页面：{'、'.join(issue['pages']) or '全局'}",
            f"- 说明：{issue['message']}",
            f"- 证据：{'；'.join(issue['evidence']) or '无'}",
            f"- 建议：{issue['suggested_action']}",
            "",
        ])
    directive = report.get("retry_directive", {})
    lines.extend([
        "## 重试方向",
        "",
        f"- 策略：`{directive.get('strategy', '')}`",
        f"- 指令：{directive.get('instruction', '')}",
    ])
    return "\n".join(lines).rstrip() + "\n"
```

- [ ] **Step 6: Implement ledger registration and escalation**

Add:

```python
def _register_artifacts(project: Path, paths: list[Path], status: str, input_path: Path,
                        outline_path: Path, source_truth_path: Path) -> None:
    ledger_path = project / "workbench" / "artifact-ledger.json"
    ledger = (
        json.loads(ledger_path.read_text(encoding="utf-8-sig"))
        if ledger_path.exists()
        else {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    )
    by_path = {
        str(item.get("path")): item
        for item in ledger.get("artifacts", [])
        if isinstance(item, dict)
    }
    for path in paths:
        relative = path.relative_to(project).as_posix()
        by_path[relative] = {
            "stage": "02-blueprint-dual-image",
            "page": None,
            "path": relative,
            "status": status,
            "depends_on": [
                input_path.relative_to(project).as_posix(),
                outline_path.relative_to(project).as_posix(),
                source_truth_path.relative_to(project).as_posix(),
            ],
            "supersedes": [],
            "resume_command": (
                "python -m cyberppt script-audit "
                f"{project.as_posix()} --input {input_path.as_posix()}"
            ),
            "sha256": _sha256(path),
        }
    ledger["artifacts"] = list(by_path.values())
    _write_json(ledger_path, ledger)


def _escalation_options() -> list[dict[str, str]]:
    return [
        {"id": "merge_pages", "label": "合并重复页面",
         "action": "保留完整业务问题，将重复展开页面合并或改为回指。"},
        {"id": "revise_outline_contract", "label": "调整页面合同",
         "action": "重新批准受影响页面的角色、前置依赖、来源或视觉中心。"},
        {"id": "accept_documented_risk", "label": "保留结构并记录风险",
         "action": "保留当前最佳稿，将未解决问题登记为后续视觉生产风险。"},
    ]
```

Implement `run_script_audit`:

```python
def run_script_audit(
    project: Path,
    input_path: Path,
    outline_path: Path | None = None,
    source_truth_path: Path | None = None,
    attempt: int | None = None,
    max_attempts: int = 3,
) -> tuple[int, dict[str, object]]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    input_path = input_path.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    if not input_path.exists():
        raise FileNotFoundError(f"script does not exist: {input_path}")
    outline_path = (
        outline_path.expanduser().resolve()
        if outline_path is not None
        else project / "workbench" / "stages" / "01-analysis" / "outline.json"
    )
    source_truth_path = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project / "workbench" / "stages" / "01-analysis" / "source-truth.json"
    )
    if not outline_path.exists():
        raise FileNotFoundError(f"outline does not exist: {outline_path}")
    outline = load_outline(outline_path)
    if not source_truth_path.exists() and outline.get("argument_contract_mode") == "strict":
        raise FileNotFoundError(f"strict script audit requires Source Truth: {source_truth_path}")
    source_truth = load_source_truth(source_truth_path)
    document = parse_script_markdown(input_path.read_text(encoding="utf-8-sig"))
    audit_dir = project / "workbench" / "scripts" / "audits"
    attempts_dir = audit_dir / "attempts"
    effective_attempt = attempt if attempt is not None else _next_attempt(attempts_dir)
    if not 1 <= effective_attempt <= max_attempts:
        raise ValueError("attempt must be between 1 and max_attempts")
    previous_strategy = ""
    previous = attempts_dir / f"attempt-{effective_attempt - 1:02d}.json"
    if previous.exists():
        previous_payload = json.loads(previous.read_text(encoding="utf-8-sig"))
        previous_strategy = str(
            previous_payload.get("audit", {}).get("retry_directive", {}).get("strategy", "")
        )
    issues = audit_script_quality(document, outline, source_truth)
    directive = script_retry_directive(issues, previous_strategy)
    failed_pages = sorted({page for issue in issues for page in issue.pages})
    report: dict[str, object] = {
        "schema": "cyberppt.script_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "attempt": effective_attempt,
        "max_attempts": max_attempts,
        "remaining_attempts": max(0, max_attempts - effective_attempt),
        "input": str(input_path),
        "outline": str(outline_path),
        "source_truth": str(source_truth_path),
        "coverage": {
            "page_count": len(document.pages),
            "first_page": document.pages[0].page_id,
            "last_page": document.pages[-1].page_id,
        },
        "issues": [issue.to_dict() for issue in issues],
        "failed_pages": failed_pages,
        "retry_scope": failed_pages,
        "retry_directive": directive,
    }
    if issues and effective_attempt >= max_attempts:
        report["status"] = "user_decision_required"
        report["options"] = _escalation_options()
    latest_json = audit_dir / "script-audit.json"
    latest_md = audit_dir / "script-audit.md"
    attempt_json = attempts_dir / f"attempt-{effective_attempt:02d}.json"
    _write_json(latest_json, report)
    latest_md.parent.mkdir(parents=True, exist_ok=True)
    latest_md.write_text(_render_markdown(report), encoding="utf-8")
    _write_json(attempt_json, {"script_sha256": _sha256(input_path), "audit": report})
    if report["status"] == "user_decision_required":
        _write_json(audit_dir / "script-escalation.json", report)
    _register_artifacts(
        project, [latest_json, latest_md, attempt_json],
        str(report["status"]), input_path, outline_path, source_truth_path,
    )
    return (0 if not issues else 5 if report["status"] == "user_decision_required" else 4), report
```

- [ ] **Step 7: Run command tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_script_audit_command.py -q
```

Expected: all command tests PASS; generated reports and ledger hashes resolve.

- [ ] **Step 8: Stage, detect impact, and commit**

Run:

```powershell
git add -- cyberppt/script_quality_contract.py cyberppt/commands/script_audit.py tests/test_script_audit_command.py
gitnexus detect-changes --scope staged
git commit -m "feat: persist script quality audits"
```

Expected: affected flows are limited to the new script-audit command and pure contract.

---

### Task 5: CLI Registration and New-Project Scaffold

**Files:**
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/init_project.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_init_project.py` if it exists

**Interfaces:**
- Adds `script-audit` subcommand and options:
  - positional `project`
  - required `--input`
  - optional `--outline`
  - optional `--source-truth`
  - optional `--attempt`
  - optional `--max-attempts`
- Adds scaffold directory `workbench/scripts/audits/attempts`.

- [ ] **Step 1: Run impact analysis before editing existing symbols**

Run:

```powershell
gitnexus impact build_parser --direction upstream
gitnexus impact init_project --direction upstream
```

Expected: `build_parser` affects CLI help/dispatch tests; `init_project` affects initialization flow. Warn before edits if either risk is HIGH or CRITICAL.

- [ ] **Step 2: Write failing CLI help and dispatch tests**

Add to `tests/test_cli.py`:

```python
def test_help_lists_script_audit(self) -> None:
    help_text = self.run_cli("--help").stdout
    self.assertIn("script-audit", help_text)


def test_script_audit_input_error_returns_two(self) -> None:
    result = self.run_cli(
        "script-audit", "missing-project",
        "--input", "missing-script.md",
    )
    self.assertEqual(2, result.returncode)
```

Add scaffold assertion to the existing initialization test:

```python
self.assertTrue((project / "workbench" / "scripts" / "audits" / "attempts").is_dir())
self.assertIn("script-audit", (project / "README.md").read_text(encoding="utf-8"))
```

- [ ] **Step 3: Run CLI/init tests and verify RED**

Run:

```powershell
python -m pytest tests/test_cli.py tests/test_init_project.py -q
```

If `tests/test_init_project.py` does not exist, run:

```powershell
python -m pytest tests/test_cli.py -q
```

Expected: FAIL because the parser and scaffold do not contain `script-audit`.

- [ ] **Step 4: Add thin CLI adapter**

Modify imports:

```python
from cyberppt.commands.script_audit import run_script_audit
```

Add:

```python
def _script_audit_command(args: argparse.Namespace) -> int:
    try:
        code, report = run_script_audit(
            Path(args.project),
            Path(args.input),
            outline_path=Path(args.outline) if args.outline else None,
            source_truth_path=Path(args.source_truth) if args.source_truth else None,
            attempt=args.attempt,
            max_attempts=args.max_attempts,
        )
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code
```

Register parser immediately after `outline-audit`:

```python
script_audit = subparsers.add_parser(
    "script-audit",
    help="Audit PPT scripts against Outline, Source Truth, composition, and argument order.",
)
script_audit.add_argument("project", help="CyberPPT project directory.")
script_audit.add_argument("--input", required=True, help="Markdown page script to audit.")
script_audit.add_argument("--outline", help="Outline JSON; defaults to the project Stage 01 artifact.")
script_audit.add_argument("--source-truth", help="Source Truth JSON; defaults to the project Stage 01 artifact.")
script_audit.add_argument("--attempt", type=int, help="Explicit attempt number; defaults to the next persisted attempt.")
script_audit.add_argument(
    "--max-attempts", type=int, default=3,
    help="Maximum changed-direction attempts (1-5; default: 3).",
)
script_audit.set_defaults(func=_script_audit_command)
```

- [ ] **Step 5: Add project scaffold and README gate**

Append to `PROJECT_DIRS`:

```python
"workbench/scripts/audits",
"workbench/scripts/audits/attempts",
```

Add manifest directory:

```yaml
  script_audits: workbench/scripts/audits
```

Replace the script-review steps in generated README with:

```text
7. Draft batch or full scripts under `workbench/scripts/drafts/`, then run `python -m cyberppt script-audit <project> --input <script.md>`.
8. A failed script audit blocks final script approval; rewrite only `retry_scope` pages with the changed `retry_directive` strategy.
9. Stop for user review after the script audit passes. Do not generate images or PPTX until an approval record exists in `workbench/approvals/`.
```

Renumber later README steps.

- [ ] **Step 6: Run CLI/init tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_cli.py tests/test_script_audit_command.py -q
```

Expected: all tests PASS.

- [ ] **Step 7: Stage, detect impact, and commit**

Run:

```powershell
git add -- cyberppt/cli.py cyberppt/commands/init_project.py tests/test_cli.py tests/test_init_project.py
gitnexus detect-changes --scope staged
git commit -m "feat: expose native script audit command"
```

If `tests/test_init_project.py` does not exist, omit it from `git add`.

Expected: GitNexus reports only CLI and initialization flows.

---

### Task 6: CyberPPT Skill and Script-Quality Reference

**Files:**
- Create: `references/script-quality.md`
- Modify: `SKILL.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Makes `references/script-quality.md` the detailed authority for page-script quality.
- Keeps `SKILL.md` concise: when to run the gate, what blocks progress, and where to read details.

- [ ] **Step 1: Write failing Skill contract tests**

Add:

```python
SCRIPT_QUALITY = ROOT / "references" / "script-quality.md"


def test_native_script_audit_gate_precedes_stage02(self) -> None:
    skill = SKILL.read_text(encoding="utf-8-sig")
    reference = SCRIPT_QUALITY.read_text(encoding="utf-8-sig")
    self.assertIn("`script-audit`", skill)
    self.assertIn("脚本审计未通过时不得批准脚本或进入 Stage 02", skill)
    self.assertIn("章内推进", reference)
    self.assertIn("上屏结构与语义图同构", reference)
    self.assertIn("跨页重复", reference)
    self.assertIn("状态升级", reference)


def test_old_ppt_script_runtime_is_not_required(self) -> None:
    text = SKILL.read_text(encoding="utf-8-sig")
    self.assertNotIn("scripts/project_manager.py", text)
    self.assertNotIn("context-pack", text)
```

- [ ] **Step 2: Run Skill tests and verify RED**

Run:

```powershell
python -m pytest tests/test_skill_contract.py -q
```

Expected: FAIL because the native script-audit reference and gate are absent.

- [ ] **Step 3: Create the detailed reference**

Create `references/script-quality.md` with these exact sections:

```markdown
# PPT脚本质量与审计

## 执行时点

在 Outline 通过并获得用户批准后编写批次脚本。每个批次完成后运行 `script-audit`；完整脚本形成后再运行一次全稿审计。脚本审计未通过时不得批准脚本或进入 Stage 02。

## 页面合同

- 封面、目录、章节过渡页和封底使用模板页结构。
- 章节过渡页只写“第X章：XXX”。
- 内容页保留页面标题、主判断、上屏文字、证据、边界和视觉结构。
- 一页只回答一个完整业务问题，并由一个视觉中心承载。

## 章内推进

- 按 Outline 的 `argument_role` 和 `prerequisite_pages` 推进。
- 工作基础页只陈述事实基础。
- 环境变化页说明新要求。
- 断点页说明现有方式与新要求之间的差距。
- 必要性页只推导研究必要性。
- 定位、建设范围、实施、保障和决策内容只在对应前置条件满足后出现。

## 来源、边界与状态升级

- 每个内容页使用 Outline 分配的 Source ID。
- 保留“拟建议、首期建议、待确认、待摸底、待基线、暂缓、后续验证、条件成熟后”等状态。
- 建议、边界和待核事项不得写成已经建成、正式确定或无条件承诺。

## 跨页重复

- 完整业务问题只在一页展开。
- 邻页可以短句回指，不复制前页主判断和论证主体。
- 本页与前页相似时，优先判断是否需要合并、改为承接句或推进到新的业务问题。

## 上屏结构与语义图同构

- 路径图在上屏文字中写出序号、箭头或顺序词。
- 闭环图写出反馈、复盘或持续校正关系。
- 矩阵写出行对象和列维度。
- 分层架构写出层级和支撑关系。
- 声明N类、N项或N步时，上屏模块数与N一致。

## 页面密度

- 内容页默认使用2—5个一级业务模块。
- 超过5个模块时使用明确分组、阶段或层级。
- 只有标题和口号的页面应补足证据或与相邻业务问题合并。
- 筛选条件、评价方法和工作方法只用于解释实际业务取舍，不独立抢占主体页面。

## 失败重试

读取 `retry_scope` 和 `retry_directive`，只重写失败页面并保留有效来源、状态和页面合同。同一问题再次失败时更换重构方向；达到上限后保留最佳稿、缺口清单和决策选项。
```

- [ ] **Step 4: Add concise Skill gate and reference route**

Before editing, run:

```powershell
gitnexus impact "CyberPPT" --direction upstream
```

If GitNexus cannot index the Markdown heading as a symbol, record “no indexed symbol” and proceed with the file-level Skill edit.

In `SKILL.md`, add a section after the Outline audit rules:

```markdown
## 原生脚本质量审计

Outline 通过并获得用户批准后，逐批编写脚本并运行：

```powershell
python -m cyberppt script-audit <project> --input <script.md>
```

`script-audit` 复用 Outline 和 Source Truth，检查页面合同、来源状态、章内推进、跨页重复、上屏结构与语义图同构、页面密度。脚本审计未通过时不得批准脚本或进入 Stage 02；必须读取 `retry_scope` 和 `retry_directive`，换方向重写失败页面。批次通过后仍需在完整脚本形成时执行全稿审计。

详细规则读取 `references/script-quality.md`。不得调用个人目录中的旧 `ppt-script`、`scripts/project_manager.py` 或旧项目生命周期替代本仓库流程。
```

Add `references/script-quality.md` to the Stage 1/Stage 2 transition reference gate.

- [ ] **Step 5: Run Skill contract tests and validation**

Run:

```powershell
python -m pytest tests/test_skill_contract.py -q
python -m cyberppt doctor
```

Expected: Skill tests PASS and doctor reports skill/references/scripts assets as `ok`.

- [ ] **Step 6: Stage, detect impact, and commit**

Run:

```powershell
git add -- SKILL.md references/script-quality.md tests/test_skill_contract.py
gitnexus detect-changes --scope staged
git commit -m "docs: integrate native script audit into CyberPPT skill"
```

Expected: changes are limited to the root Skill, one reference, and Skill tests.

---

### Task 7: Power-Project Regression, Focused Suite, and Final Scope Verification

**Files:**
- Create: `tests/fixtures/script_audit/power_foundation_premature_scope.md`
- Create: `tests/fixtures/script_audit/power_scene_matrix.md`
- Modify: `tests/test_script_quality_contract.py`
- Generated but do not commit unless explicitly requested:
  - `projects/power-supply-demand-forecast-early-warning/workbench/scripts/audits/*`

**Interfaces:**
- Exercises the public CLI and pure contract against the real project contracts.

- [ ] **Step 1: Add a fixture reproducing the original failure**

Create:

```markdown
## 第4页：中电联工作基础

- 页面类型：内容页
- 页面标题：中电联工作基础
- 主判断：首期应从全国总盘和定期报告入手，升级为持续运行闭环。
- 上屏文字：

  **既有工作基础**

  - 已形成统计分析和报告工作。

- 证据：S006
- 边界：本页陈述工作基础。
- 视觉结构：工作基础链。
```

- [ ] **Step 2: Add a valid scene-matrix fixture**

Create:

```markdown
## 第19页：场景布局与分期边界

- 页面类型：内容页
- 页面标题：场景布局与分期边界
- 主判断：首期选择全国月季分析和年度报告自动化，是对履职关联、数据基础、交付形式、技术条件和协同复杂度综合权衡后的阶段安排。
- 上屏文字：

  | 场景 | 业务必要 | 数据可得 | 成果可交付 | 技术成熟 | 协同可控 | 阶段安排 |
  |---|---|---|---|---|---|---|
  | 全国月季分析 | 高 | 较高 | 高 | 较高 | 较高 | 首期主闭环 |
  | 年度报告自动化 | 高 | 高 | 高 | 高 | 高 | 首期并行验证 |
  | 高频专题场景 | 高 | 中低 | 中 | 中 | 中低 | 后续试点 |

  **首期取舍**

  - 两个场景共同验证研判能力、成果生产能力和共性底座。

- 证据：S022、S031、S078
- 边界：排序需在数据与协同摸底后校核。
- 视觉结构：场景筛选矩阵与分期路线。
```

- [ ] **Step 3: Add regression assertions**

```python
def test_power_foundation_regression_is_blocked() -> None:
    text = fixture("power_foundation_premature_scope.md")
    issues = audit_script_quality(
        parse_script_markdown(text),
        load_real_outline(),
        load_real_source_truth(),
    )
    assert "PREMATURE_SCOPE_CLAIM" in {issue.code for issue in issues}


def test_power_scene_matrix_is_not_treated_as_isolated_method_page() -> None:
    text = fixture("power_scene_matrix.md")
    issues = audit_script_quality(
        parse_script_markdown(text),
        load_real_outline(),
        load_real_source_truth(),
    )
    codes = {issue.code for issue in issues}
    assert "MATRIX_AXES_MISSING" not in codes
    assert "MULTIPLE_PAGE_MISSIONS" not in codes
```

- [ ] **Step 4: Run focused feature suite**

Run:

```powershell
python -m pytest `
  tests/test_script_quality_contract.py `
  tests/test_script_audit_command.py `
  tests/test_cli.py `
  tests/test_skill_contract.py `
  tests/test_argument_flow_contract.py `
  tests/test_outline_contract.py `
  tests/test_source_truth_contract.py `
  tests/test_outline_audit_command.py `
  tests/test_source_truth_audit_command.py -q
```

Expected: all focused tests PASS.

- [ ] **Step 5: Run the command on current P01—P23 batches**

Run each batch with an isolated temporary project copy or explicit `--attempt 1` after clearing only the temporary audit directory:

```powershell
python -m cyberppt script-audit projects/power-supply-demand-forecast-early-warning `
  --input projects/power-supply-demand-forecast-early-warning/workbench/scripts/drafts/script-review-p01-p07.md

python -m cyberppt script-audit projects/power-supply-demand-forecast-early-warning `
  --input projects/power-supply-demand-forecast-early-warning/workbench/scripts/drafts/script-review-p08-p12.md

python -m cyberppt script-audit projects/power-supply-demand-forecast-early-warning `
  --input projects/power-supply-demand-forecast-early-warning/workbench/scripts/drafts/script-review-p13-p23.md
```

Expected:

- The command completes and produces page-level reports.
- P04 in the corrected batch does not trigger `PREMATURE_SCOPE_CLAIM`.
- P13 passes the pure chapter-page check.
- P19 does not trigger `MATRIX_AXES_MISSING`.
- Any density or repetition issue is reviewed against the exact evidence before changing thresholds.

- [ ] **Step 6: Run the full repository suite and classify unrelated failures**

Run:

```powershell
python -m pytest -q
```

Expected: no new failures in script-quality, Source Truth, Outline, CLI, initialization, or Skill tests. Record existing unrelated image/platform failures separately; do not weaken the new tests to hide them.

- [ ] **Step 7: Stage only feature-owned files and run final GitNexus verification**

Run:

```powershell
git add -- `
  cyberppt/script_quality_contract.py `
  cyberppt/commands/script_audit.py `
  cyberppt/cli.py `
  cyberppt/commands/init_project.py `
  tests/test_script_quality_contract.py `
  tests/test_script_audit_command.py `
  tests/test_cli.py `
  tests/test_skill_contract.py `
  tests/fixtures/script_audit `
  references/script-quality.md `
  SKILL.md

gitnexus detect-changes --scope staged
git diff --cached --check
```

Expected: staged scope matches the design; no unrelated project scripts, macOS `._*` files, image fixtures, or vendor changes are staged.

- [ ] **Step 8: Commit final regression fixtures or compatibility adjustments**

If Task 7 produced new fixture/test changes:

```powershell
git commit -m "test: cover native script audit regressions"
```

If no new changes remain after earlier commits, do not create an empty commit.

- [ ] **Step 9: Report final deliverables**

Provide clickable links to:

- `SKILL.md`
- `references/script-quality.md`
- `cyberppt/script_quality_contract.py`
- `cyberppt/commands/script_audit.py`
- the design and implementation plan
- the current project audit report when generated
- the containing repository and project folders

Report:

- focused test count and result;
- full-suite result with unrelated failures separated;
- GitNexus final affected flows and risk;
- commit hashes;
- any remaining intentionally deferred scope.


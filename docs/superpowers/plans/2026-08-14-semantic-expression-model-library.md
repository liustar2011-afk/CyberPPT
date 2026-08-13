# Semantic Expression Model Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one versioned Markdown model library and project author-confirmed model selections into Stage 01 pages.

**Architecture:** A single `references/semantic-expression-models.md` contains fixed-field model entries. A stdlib parser reads entries and their slots; Outline stores an author-selected mapping. The compiler groups records from that mapping and the audit verifies that all non-implicit model slots are source cited.

**Tech Stack:** Python standard library, Markdown, existing `pytest` contracts.

## Global Constraints

- No database service, second model table, or external dependency.
- Source Truth remains factual authority; model selections cannot change it.
- Existing Outline pages are valid until `expression_model_selection.fit=selected` is declared.
- Preserve the existing one-primary-unit page hierarchy.

---

### Task 1: Model library reader

**Files:**
- Create: `references/semantic-expression-models.md`
- Create: `cyberppt/semantic_expression_models.py`
- Create: `tests/test_semantic_expression_models.py`

**Interfaces:**
- Produces `ExpressionModel`, `ModelSlot`, and `load_expression_models(path: Path) -> dict[str, ExpressionModel]`.

- [ ] **Step 1: Write failing test**

```python
def test_loads_scqa_from_single_markdown_library(tmp_path: Path) -> None:
    path = tmp_path / "models.md"
    path.write_text(SCQA_LIBRARY, encoding="utf-8")
    model = load_expression_models(path)["scqa"]
    assert [slot.name for slot in model.slots] == ["situation", "complication", "question", "answer"]
```

- [ ] **Step 2: Verify failing test**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_semantic_expression_models.py`

Expected: import failure for `semantic_expression_models`.

- [ ] **Step 3: Implement minimal library and parser**

```python
@dataclass(frozen=True)
class ModelSlot:
    name: str
    required: bool
    implicit_allowed: bool

@dataclass(frozen=True)
class ExpressionModel:
    model_id: str
    family: str
    slots: tuple[ModelSlot, ...]
    expression_structure: str
```

Use one HTML metadata comment per Markdown model heading. Reject duplicate ids and malformed slot declarations.

- [ ] **Step 4: Run tests and commit**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_semantic_expression_models.py`

Expected: all pass.

Commit: `git add references/semantic-expression-models.md cyberppt/semantic_expression_models.py tests/test_semantic_expression_models.py && git commit -m "feat: add semantic expression model library"`

### Task 2: Selected-model audit

**Files:**
- Modify: `cyberppt/outline_audit_semantics.py`
- Modify: `cyberppt/outline_contract.py`
- Modify: `tests/test_outline_contract.py`

**Interfaces:**
- Consumes `page.expression_model_selection` with `model_id`, `fit`, and `source_mapping`.
- Produces `EXPRESSION_MODEL_SLOT_UNCITED` and `EXPRESSION_MODEL_IMPLICIT_UNDECLARED` audit issues.

- [ ] **Step 1: Write failing tests**

```python
def test_selected_scqa_requires_all_required_slots_cited() -> None:
    page["expression_model_selection"] = {"model_id": "scqa", "fit": "selected", "source_mapping": []}
    assert "EXPRESSION_MODEL_SLOT_UNCITED" in audit_codes(outline, truth)
```

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_outline_contract.py`

Expected: assertion failure because the selection is not audited.

- [ ] **Step 3: Implement opt-in audit**

Load the canonical MD library. For selected models, require cited mappings for required slots; only permit `implicit=true` when the model allows it, and require citations to be page source refs.

- [ ] **Step 4: Run tests and commit**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_semantic_expression_models.py tests/test_outline_contract.py`

Expected: all pass.

Commit: `git add cyberppt/outline_audit_semantics.py cyberppt/outline_contract.py tests/test_outline_contract.py && git commit -m "feat: audit expression model selections"`

### Task 3: Model-aware page grouping and P04 projection

**Files:**
- Modify: `cyberppt/stage01_compiler.py`
- Modify: `tests/test_stage01_compiler.py`
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline-audit.json`

**Interfaces:**
- `_page_content_units(..., expression_model_selection: dict[str, Any] | None = None)` groups selected source mappings in model-slot order.

- [ ] **Step 1: Write failing grouping test**

```python
def test_selected_scqa_groups_complication_and_keeps_answer_primary() -> None:
    units, _ = _page_content_units("p04", records, "建设背景", expression_model_selection=SCQA_SELECTION)
    assert [unit["model_slot"] for unit in units] == ["situation", "complication", "answer"]
    assert units[-1]["role"] == "primary"
```

- [ ] **Step 2: Verify failure**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_stage01_compiler.py`

Expected: assertion failure because selections are ignored.

- [ ] **Step 3: Implement selected-model grouping**

Use only author-provided, cited non-implicit slots. Create one unit per slot, make `answer` primary when present, mark other slots supporting and on-screen, then preserve unmapped records through current logic. Do not infer slot membership from keywords, page type, or paragraph order.

- [ ] **Step 4: Add selected P04 SCQA mapping and refresh only P04**

Add mappings `S=ST0006`, `C=ST0007+ST0008`, `Q=implicit(ST0007+ST0008)`, `A=ST0009`. Run:

`PYTHONPATH=. python3 -m cyberppt refresh-outline-content-units projects/power-data-infrastructure-cooperation-v16-20260813 --page-id p04`

Then run:

`PYTHONPATH=. python3 -m cyberppt outline-audit projects/power-data-infrastructure-cooperation-v16-20260813 --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`

Expected: three source-backed P04 units (`situation`, `complication`, `answer`) and no expression-model audit issue.

- [ ] **Step 5: Run regression checks and commit**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_semantic_expression_models.py tests/test_source_argument_model.py tests/test_stage01_compiler.py tests/test_outline_contract.py`

Run: `npx --no-install graft build && npx --no-install graft check`

Expected: all tests pass; graph check reports `OK`.

Commit: `git add cyberppt/stage01_compiler.py tests/test_stage01_compiler.py projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline-audit.json && git commit -m "feat: project selected expression models into pages"`

## Self-review

- The plan covers the single Markdown library, source-cited selection audit, model-aware grouping, and the approved P04 SCQA projection.
- No task adds a database, external dependency, or automatic fact creation.

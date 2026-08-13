# Stage 01 Page Relationship Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing Outline → `script-audit` chain so it blocks duplicate adjacent responsibilities, later-page scope leakage, and unreadable declared relations while preserving legacy pages without relations.

**Architecture:** Keep all analysis in `cyberppt/script_quality_contract.py`. Build an in-memory `PageRelationshipSummary` from each existing outline page contract and parsed `ScriptPage`; return ordinary `ScriptQualityIssue` values so `run_script_audit()` retains its existing `failed_pages` and `retry_scope` behavior. Run this after existing page checks and before the current adjacent-page duplicate loop.

**Tech Stack:** Python 3.12, dataclasses, existing deterministic text helpers, `unittest`, `pytest`.

## Global Constraints

- Enhance only Outline → script-audit; add no approval files, state JSON, hash bindings, manual stops, parallel directories, or second workflow.
- Use only existing `page_mission`, `audience_question`, `must_not_include`, `content_relations`, `argument_role`, `core_message`, `上屏文字`, and `视觉结构`; never infer a business relation from titles alone.
- Emit `error` for duplicate responsibilities, explicit later-page leakage, and declared-but-invisible relations; use `warning` only for an unprovided prerequisite.
- Skip relationship-readability checks for template/chapter pages and legacy content pages with no `content_relations`.

---

## File Structure

- Modify: `cyberppt/script_quality_contract.py` — summary model, deterministic relationship checks, and the existing audit integration.
- Modify: `tests/test_script_quality_contract.py` — focused v2 fixture helpers and blocking/compatibility assertions.
- Create: `docs/superpowers/plans/2026-08-13-stage01-page-relationship-continuity.md` — this TDD plan, not a runtime artifact.

### Task 1: Add the relationship-continuity audit

**Files:**

- Modify: `cyberppt/script_quality_contract.py:after _visual_structure_judgment_issues and before audit_script_quality`
- Modify: `cyberppt/script_quality_contract.py:audit_script_quality`
- Test: `tests/test_script_quality_contract.py:append RelationshipContinuityTests`

**Interfaces:**

- Consumes: `ScriptPage`, Outline page-contract dictionaries, and `text_similarity()`.
- Produces: `PageRelationshipSummary` plus `_page_relationship_continuity_issues(script, pages_by_id) -> list[ScriptQualityIssue]`.
- Integrates: `audit_script_quality()` extends its existing issue list; callers continue deriving report `failed_pages` / `retry_scope` from `ScriptQualityIssue.pages`.

- [x] **Step 1: Write the failing test**

Append a `RelationshipContinuityTests` class with a helper that produces two valid consecutive content pages, valid strict Source Truth records, and embedded page-contract receipts. Add these exact assertions:

```python
codes = self._codes(self._audit(
    first_contract={"page_mission": "说明统一目录如何支撑服务", "core_message": "统一目录支撑服务", "content_relations": [{"relation": "supports", "subject": "统一目录", "objects": ["服务"]}]},
    second_contract={"page_mission": "说明统一目录如何支撑服务", "core_message": "统一目录支撑服务", "content_relations": [{"relation": "supports", "subject": "统一目录", "objects": ["服务"]}]},
))
self.assertIn("ADJACENT_PAGE_RESPONSIBILITY_DUPLICATE", codes)

issues = self._audit(first_onscreen="统一目录；计量结算：形成服务闭环", second_contract={"must_not_include": ["计量结算机制"]})
match = next(issue for issue in issues if issue.code == "PAGE_SCOPE_PREEMPTED")
self.assertEqual(("p01", "p02"), match.pages)

codes = self._codes(self._audit(first_onscreen="数据；模型；成果", first_visual="展示三项能力模块。", first_contract={"content_relations": [{"relation": "flows_to", "subject": "数据", "objects": ["模型", "成果"]}]}))
self.assertIn("DECLARED_RELATION_NOT_VISIBLE", codes)
self.assertIn("ONSCREEN_FALSE_RELATION_PARALLEL", codes)

codes = self._codes(self._audit(first_contract={"content_relations": []}))
self.assertNotIn("DECLARED_RELATION_NOT_VISIBLE", codes)
self.assertNotIn("ONSCREEN_FALSE_RELATION_PARALLEL", codes)
```

Also add a passing process case whose modules form `数据接入 → 模型计算 → 成果发布` and whose visual structure describes the same chain. Assert neither visible-relation code is present.

- [x] **Step 2: Run the focused test class and verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py -k RelationshipContinuityTests`

Expected: FAIL because the new relationship codes are not emitted.

- [x] **Step 3: Implement the minimal in-memory summary and rules**

Add the frozen model and helper signature below the existing visual relation helpers:

```python
@dataclass(frozen=True)
class PageRelationshipSummary:
    page_id: str
    entry_conditions: tuple[str, ...]
    page_transformation: str
    exit_handoffs: tuple[str, ...]
    excluded_scope: tuple[str, ...]
    visible_relation: bool

def _page_relationship_continuity_issues(
    script: ScriptDocument,
    pages_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    content_pages = [
        page for page in script.pages
        if page.page_type == "content" and page.page_id in pages_by_id
    ]
    summaries = {
        page.page_id: _page_relationship_summary(page, pages_by_id[page.page_id])
        for page in content_pages
    }
    for left, right in zip(content_pages, content_pages[1:]):
        issues.extend(_adjacent_relationship_issues(left, right, summaries))
    for page in content_pages:
        issues.extend(_visible_relation_issues(page, summaries[page.page_id]))
    return issues
```

Construct summaries only from structured `content_relations` plus the existing mission/core-message fields. Safely extract only string `subject`, `objects`, optional `inputs`, optional `outputs`, and `must_not_include` values; malformed or absent values produce empty tuples. Require directional verbs, arrows/ordered connectors, or hierarchy/loop signals in both top-level visible modules and visual structure for relation types `causes`, `flows_to`, `supports`, `depends_on`, `composed_of`, `collaborates_with`, and `feedback_to`.

Emit `ADJACENT_PAGE_RESPONSIBILITY_DUPLICATE` only when adjacent content pages have substantially the same normalized mission/core-message/structured relation. Emit `PAGE_SCOPE_PREEMPTED` when the current page's `onscreen_text` or `full_prose` contains a nonempty phrase reserved by the next content page's `must_not_include`. For a content page with declared relations but no visible relation signal, emit `DECLARED_RELATION_NOT_VISIBLE` and `ONSCREEN_FALSE_RELATION_PARALLEL`. Emit `PAGE_PREREQUISITE_UNFORMED` as a warning only when explicit relation inputs are neither prior outputs nor directly assigned to the same page/source references.

Integrate the helper without changing reporting code:

```python
issues.extend(_page_relationship_continuity_issues(script, pages_by_id))
```

- [x] **Step 4: Run the focused test class and verify it passes**

Run: `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py -k RelationshipContinuityTests`

Expected: PASS, including the no-relation legacy compatibility and visible process control.

- [x] **Step 5: Run the audit regression tests**

Run: `PYTHONPATH=. pytest -q tests/test_script_quality_contract.py tests/test_script_audit_command.py`

Expected: PASS. Errors must remain in the unchanged report's `failed_pages` / `retry_scope`; a warning alone remains non-blocking.

- [ ] **Step 6: Rebuild Graft, inspect changed execution scope, and commit**

Run:

```bash
npx --no-install graft build
npx --no-install graft check
git diff --check
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py docs/superpowers/plans/2026-08-13-stage01-page-relationship-continuity.md
git commit -m "feat(stage01): audit page relationship continuity"
```

Expected: Graft reports `graph check: OK`; the diff is whitespace-clean; the commit contains only the relationship audit, its tests, and the plan.

## Self-Review

- Spec coverage: covers adjacent duplicate responsibility, next-page exclusion leakage, unformed prerequisites, invisible relations, false parallelism, severity, and legacy/template compatibility.
- Placeholder scan: no `TBD`, `TODO`, or deferred implementation placeholder is present.
- Type consistency: the summary model, helper signature, and `audit_script_quality()` integration use the interfaces defined above.
- Scope check: only the existing script-quality contract and its established tests change; no Stage 02 field, artifact, or gate changes.

# Style 10 Default Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Style 10 the default CyberPPT visual style whenever callers omit both a style ID and style name.

**Architecture:** Store the default style ID in the canonical JSON style library, then have `resolve_default_style()` load and apply that declared ID only when the caller supplies no explicit selection. Preserve explicit ID/name resolution and project style-lock behavior.

**Tech Stack:** Python 3.12, JSON style library, pytest.

## Global Constraints

- Change only the canonical style library, the resolver, and focused Style 10 tests.
- Preserve explicit style selection and existing project locks.
- Do not modify unrelated dirty-worktree changes.

---

### Task 1: Declare and resolve the Style 10 default

**Files:**
- Modify: `scripts/dual_image_overlay/style_presets/cyberppt_default_styles.json:2-5`
- Modify: `scripts/dual_image_overlay/style_library.py:27-71`
- Test: `tests/test_extended_style_10.py:27-41`

**Interfaces:**
- Consumes: JSON root field `default_style_id: int`.
- Produces: `resolve_default_style(style_id=None, style_name=None) -> dict[str, Any]` returning Style 10.

- [ ] **Step 1: Write the failing test**

```python
assert resolve_default_style()["id"] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest -q tests/test_extended_style_10.py`

Expected: FAIL because no style selection currently raises `ValueError`.

- [ ] **Step 3: Write minimal implementation**

```python
# cyberppt_default_styles.json
"default_style_id": 10,

# style_library.py
library = load_style_library(path)
if style_id is None and not style_name:
    style_id = int(library["default_style_id"])
```

- [ ] **Step 4: Run focused tests**

Run: `PYTHONPATH=. pytest -q tests/test_extended_style_10.py tests/test_extended_style_9.py tests/test_final_script_pages.py`

Expected: PASS.

- [ ] **Step 5: Verify the production entry point consumes the default**

Run: `PYTHONPATH=. python -c 'from scripts.dual_image_overlay.style_library import resolve_default_style; assert resolve_default_style()["id"] == 10'`

Expected: Exit code 0.

# Visual Structure Semantic Audit Generalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the global visual-structure quality audit project-neutral and prove its remaining warnings work across domains.

**Architecture:** Keep `_visual_structure_judgment_issues` as the single local Stage 01 audit entrypoint. Restrict its warnings to relationships established by the current page text and remove checks whose trigger or remediation encodes an education-gateway visual preference.

**Tech Stack:** Python 3.12, `unittest`, repository-local CyberPPT audit code.

## Global Constraints

- Do not add a project profile, configuration file, or new audit artifact.
- Preserve existing issue codes for retained checks.
- Keep remaining warnings non-blocking.

---

### Task 1: Generalize visual-structure semantic warnings

**Files:**

- Modify: `cyberppt/script_quality_contract.py:959-977,3771-3936`
- Modify: `tests/test_script_quality_contract.py:3348-3478`

**Interfaces:**

- Consumes: `ScriptPage.visual_structure`, `main_message`, `onscreen_judgment`, `full_prose`, and `speaker_notes`.
- Produces: existing `ScriptQualityIssue` warnings from `_visual_structure_judgment_issues(page)`.

- [ ] **Step 1: Replace project-specific tests with cross-domain expectations**

```python
def test_does_not_infer_a_gateway_visual_center() -> None:
    page = _judgment_page(
        main_message="统一网关连接身份组织与业务接口",
        visual_structure="双侧协同——以身份组织接口为视觉中心。",
    )
    codes = {issue.code for issue in _visual_structure_judgment_issues(page)}
    self.assertNotIn("VISUAL_CENTER_JUDGMENT_MISMATCH", codes)
```

Also replace the education-specific mechanism fixture with order-fulfilment and risk-review chains plus isolation/degradation controls; retain the expected `VISUAL_STRUCTURE_MECHANISM_AS_LANE` warning.

- [ ] **Step 2: Run the focused tests and verify the former project-specific expectations fail**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_script_quality_contract.py -k 'gateway_center or depth_defense or mechanism_peer_lanes'`

Expected: the gateway and depth-defense tests fail because the old implementation still emits the two project-specific issue codes.

- [ ] **Step 3: Remove unsupported domain inference and make cross-cut detection relation-local**

```python
# A node is cross-cutting only when this page explicitly describes that node
# as crossing, spanning, or governing the primary relation.
marked = any(re.search(pattern, corpus) for pattern in patterns)
if marked and is_primary_chain:
    peer_hits.append(bare)
```

Delete the fixed gateway/engine visual-center branch, the `受控边界` versus `DEPTH_DEFENSE_MARKERS` branch, and constants used only by those branches. Do not add replacement keyword configuration.

- [ ] **Step 4: Run focused and full contract tests**

Run: `PYTHONPATH=. .venv/bin/python -m pytest -q tests/test_script_quality_contract.py`

Expected: all tests in the module pass.

- [ ] **Step 5: Refresh the repository graph after the code change**

Run: `npx --no-install graft build && npx --no-install graft check`

Expected: graph build succeeds and the graph check reports `OK`.

# Stage 01 Onscreen Composition Absorption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Absorb composition discipline from `vendor/ppt-script-visual-redesign` into Stage 01 `script-quality` rules and `script-audit` checks, without a separate Skill or Stage 02 visual layer.

**Architecture:** Keep the existing script field contract. Tighten writing rules for 上屏文字 / 视觉结构 in `references/script-quality.md`. Add deterministic composition checks in `cyberppt/script_quality_contract.py`, with non-blocking `warning` severity first so green projects are not forced into rewrite. Teach `script-audit` to pass when only warnings remain. Leave `imagegen_handoff` field set unchanged.

**Tech Stack:** Python 3.11+, stdlib, existing `unittest` suite, CyberPPT CLI (`python -m cyberppt script-audit`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-25-stage01-onscreen-composition-absorption-design.md` (已决议 2026-07-25).
- Do **not** install or invoke `$ppt-script-visual-redesign` as a production entry.
- Do **not** add Stage 02 `onscreen_visual_layer` or new required script fields (`视觉主张` / `构图原语` / `上屏禁止事项`).
- Do **not** replace `script-audit` with vendor `validate_script.py`.
- Do **not** change `imagegen_handoff` content-lock field set in this plan.
- New composition checks default to `warning` except `VISUAL_STRUCTURE_STYLE_ONLY` which is `error`.
- Preserve complete-prose authority chain and existing fidelity audits.
- Prefer UTF-8; do not touch unrelated dirty-worktree files.

---

## File Structure

### Modified files

- `cyberppt/script_quality_contract.py` — composition lexicons, warning helper, presentation checks, retry routing.
- `cyberppt/commands/script_audit.py` — pass/fail based on error-severity issues only; still report warnings.
- `references/script-quality.md` — onscreen composition rules, primitive table, visual-structure sentence contract, anti-patterns.
- `SKILL.md` — short Stage 01 note that composition rules live in `script-quality.md` (not a separate Skill).
- `tests/test_script_quality_contract.py` — unit tests for new codes and warning severity.
- `tests/test_script_audit_command.py` — command passes with warnings-only.
- `vendor/ppt-script-visual-redesign/README.md` — non-production absorption notice.

### Not modified this plan

- `scripts/dual_image_overlay/imagegen_handoff.py`
- Stage 02 visual-system / style selection flow
- Outline / Source Truth contracts

---

### Task 1: Non-blocking warning severity in script audit

**Files:**
- Modify: `cyberppt/script_quality_contract.py` (`_issue`, optionally add `_warn`)
- Modify: `cyberppt/commands/script_audit.py` (status / exit based on errors)
- Test: `tests/test_script_quality_contract.py`
- Test: `tests/test_script_audit_command.py`

**Interfaces:**
- Consumes: existing `ScriptQualityIssue(severity=...)`
- Produces:

```python
def _issue(
    code: str,
    page: ScriptPage,
    message: str,
    action: str,
    source_ids: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    severity: str = "error",
) -> ScriptQualityIssue: ...
```

- `run_script_audit`: `status == "passed"` when there are zero `severity == "error"` issues; warnings still listed in `issues`.

- [ ] **Step 1: Write the failing unit test for severity parameter**

Add to `tests/test_script_quality_contract.py`:

```python
def test_issue_helper_accepts_warning_severity(self) -> None:
    from cyberppt.script_quality_contract import ScriptPage, _issue

    page = ScriptPage(
        page_id="p01",
        sequence=1,
        heading="示例",
        page_type="content",
        title="示例",
        main_message="判断",
        full_prose="x" * 100,
        selection_notes="取舍",
        evidence_map="点→S001",
        evidence_map_refs=("S001",),
        source_refs=("S001",),
        boundary="",
        visual_structure="业务架构图。",
        onscreen_text="**模块A**\n- a\n**模块B**\n- b",
        module_titles=("模块A", "模块B"),
    )
    issue = _issue(
        "VISUAL_STRUCTURE_TOO_THIN",
        page,
        "thin",
        "expand",
        severity="warning",
    )
    self.assertEqual("warning", issue.severity)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.TestCaseName -q` is wrong; use:

```bash
cd /Volumes/DOC/CyberPPT
python -m unittest tests.test_script_quality_contract.ScriptContractAuditTests.test_issue_helper_accepts_warning_severity -v
```

Expected: FAIL (`_issue` unexpected keyword `severity` or AttributeError). Put the test in a class that can import `_issue` (same module tests already import from contract).

- [ ] **Step 3: Implement severity on `_issue`**

In `cyberppt/script_quality_contract.py`, change `_issue` to:

```python
def _issue(
    code: str,
    page: ScriptPage,
    message: str,
    action: str,
    source_ids: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    severity: str = "error",
) -> ScriptQualityIssue:
    if severity not in {"error", "warning"}:
        raise ValueError(f"unsupported severity: {severity}")
    return ScriptQualityIssue(
        code=code,
        severity=severity,
        message=message,
        pages=(page.page_id,),
        source_ids=source_ids,
        evidence=evidence,
        suggested_action=action,
    )
```

- [ ] **Step 4: Write failing command-level test for warnings-only pass**

In `tests/test_script_audit_command.py`, add a test that monkeypatches or constructs a temporary project whose `audit_script_quality` returns one warning issue (prefer injecting via a script that will trigger a warning after Task 2 — if Task 1 lands first, temporarily construct report logic test by unit-testing a small helper). Prefer extracting:

```python
def audit_status(issues: list[ScriptQualityIssue]) -> str:
    if any(issue.severity == "error" for issue in issues):
        return "rewrite_required"  # caller may still escalate by attempt
    return "passed"
```

Or inline in `run_script_audit`:

```python
errors = [issue for issue in issues if issue.severity == "error"]
warnings = [issue for issue in issues if issue.severity == "warning"]
status = "passed" if not errors else "rewrite_required"
# failed_pages / retry_scope from errors only
# remaining_attempts / escalation still based on errors
# report["issues"] includes errors + warnings
# return 0 when not errors
```

Add test asserting: when only warnings exist, exit code `0` and `status == "passed"`, and warning still present in `report["issues"]`.

- [ ] **Step 5: Implement script_audit pass/fail split**

Modify `cyberppt/commands/script_audit.py` accordingly. Keep Markdown report listing both severities. Escalation (`user_decision_required`) only when **errors** remain at max attempts.

- [ ] **Step 6: Run tests**

```bash
python -m unittest tests.test_script_quality_contract tests.test_script_audit_command -v
```

Expected: PASS for new tests; no regressions.

- [ ] **Step 7: Commit**

```bash
git add cyberppt/script_quality_contract.py cyberppt/commands/script_audit.py tests/test_script_quality_contract.py tests/test_script_audit_command.py
git commit -m "$(cat <<'EOF'
feat(script-audit): allow non-blocking warning severity

EOF
)"
```

---

### Task 2: Composition lexicons and presentation checks

**Files:**
- Modify: `cyberppt/script_quality_contract.py` (`_presentation_issues`, `script_retry_directive`)
- Test: `tests/test_script_quality_contract.py`
- Optional fixture: `tests/fixtures/script_audit/visual_structure_style_only.md`

**Interfaces:**
- Produces issue codes:
  - `VISUAL_STRUCTURE_STYLE_ONLY` (error)
  - `VISUAL_STRUCTURE_TOO_THIN` (warning)
  - `ONSCREEN_ANTI_PATTERN` (warning)
  - `PRIMITIVE_ONSCREEN_MISMATCH` (warning)
- Retry: these codes map to `semantic_diagram_realign` (errors drive retry; warnings do not fail the gate).

- [ ] **Step 1: Write failing tests**

```python
def test_visual_structure_style_only_is_error(self) -> None:
    script = parse_script_markdown(
        """## 第9页：总体定位
- 页面类型：内容页
- 页面标题：总体定位
- 主判断：定位为行业公共能力。
- 完整文字稿：""" + ("论证性正文。" * 20) + """
- 文字稿取舍说明：不展开邻页。
- 证据映射：定位→S015
- 上屏文字：
  **行业公共能力**
  - 服务行业研判。
  **专业系统边界**
  - 保留职责边界。
- 证据：S015
- 边界：范围待定。
- 视觉结构：简洁现代科技感。
"""
    )
    issues = audit_script_quality(
        script,
        strict_outline({
            "page_id": "p09",
            "sequence": 9,
            "page_type": "content",
            "title": "总体定位",
            "argument_role": "positioning",
            "source_refs": ["S015"],
            "prerequisite_pages": [],
        }),
        source_truth({
            "id": "S015",
            "type": "J",
            "status": "拟建议",
            "statement": "公共能力定位。",
        }),
    )
    style_issues = [i for i in issues if i.code == "VISUAL_STRUCTURE_STYLE_ONLY"]
    self.assertTrue(style_issues)
    self.assertEqual("error", style_issues[0].severity)


def test_visual_structure_too_thin_is_warning(self) -> None:
    # 视觉结构：业务架构图。  → warning VISUAL_STRUCTURE_TOO_THIN
    ...


def test_onscreen_anti_pattern_warns_on_card_wall_phrase(self) -> None:
    # 上屏或视觉结构含「六宫格」且无否定语境 → ONSCREEN_ANTI_PATTERN warning
    ...


def test_primitive_matrix_mismatch_warns(self) -> None:
    # 视觉结构含「矩阵筛选」但上屏无 MATRIX_SIGNALS → PRIMITIVE_ONSCREEN_MISMATCH warning
    ...
```

Use the same outline/truth scaffolding pattern as `test_path_visual_requires_order_signal`.

- [ ] **Step 2: Run tests to verify they fail**

```bash
python -m unittest tests.test_script_quality_contract.ScriptContractAuditTests.test_visual_structure_style_only_is_error -v
```

Expected: FAIL (code missing).

- [ ] **Step 3: Add lexicons near existing SIGNAL constants**

```python
COMPOSITION_PRIMITIVES: tuple[str, ...] = (
    "贯穿主链",
    "双侧协同",
    "受控边界",
    "分层剖面",
    "汇聚引擎输出",
    "判断证据支撑",
    "非对称对照",
    "机制作用范围",
    "主体泳道",
    "阶段推进",
    "矩阵筛选",
    "闭环回流",
)

SPATIAL_SIGNALS: tuple[str, ...] = (
    "左", "右", "上", "下", "中央", "中心", "主链", "由左向右",
    "由右向左", "自上而下", "自下而上", "贯穿", "托举", "对照",
    "回流", "边界", "层级", "底座",
)

STYLE_ONLY_TERMS: tuple[str, ...] = (
    "简洁现代", "高级大气", "科技感", "大气磅礴", "高端炫酷",
)

ANTI_PATTERN_TERMS: tuple[str, ...] = (
    "六宫格", "Bento", "Bento Grid", "中心圆", "等宽卡片",
    "卡片墙", "网页后台", "数据大屏", "紫蓝渐变", "霓虹",
)

NEGATION_TERMS: tuple[str, ...] = (
    "不得", "禁止", "避免", "不使用", "不采用", "不做",
)
```

- [ ] **Step 4: Implement helpers and extend `_presentation_issues`**

Only for `page.page_type == "content"`:

1. If `visual_structure` empty → existing sparse paths may already catch; if present:
2. `VISUAL_STRUCTURE_STYLE_ONLY` when any `STYLE_ONLY_TERMS` in visual and no `SPATIAL_SIGNALS` and no `COMPOSITION_PRIMITIVES` → `severity="error"`.
3. `VISUAL_STRUCTURE_TOO_THIN` when compact length of visual &lt; 18 **or** (no primitive and no spatial signal) → `severity="warning"`. Skip emitting TOO_THIN when STYLE_ONLY already emitted.
4. `ONSCREEN_ANTI_PATTERN`: scan `onscreen_text + visual_structure` lines; if anti-pattern term appears and line has no negation term → warning.
5. `PRIMITIVE_ONSCREEN_MISMATCH` examples:
   - visual contains `矩阵筛选` or (`矩阵` and primitive-like) without matrix signals in onscreen → warning
   - visual contains `贯穿主链` or `阶段推进` without order signals in onscreen → warning
   - visual contains `闭环回流` without loop signals → warning
   - visual contains `分层剖面` without layer signals → warning

Also extend existing path/matrix/loop checks: if visual contains primitive aliases (`贯穿主链` counts as path-like for order signals). Keep old substring checks (`"路径" in visual`) working.

- [ ] **Step 5: Route new codes in `script_retry_directive`**

Ensure `semantic_diagram_realign` preferred set includes:

```python
"VISUAL_STRUCTURE_STYLE_ONLY",
"VISUAL_STRUCTURE_TOO_THIN",
"ONSCREEN_ANTI_PATTERN",
"PRIMITIVE_ONSCREEN_MISMATCH",
```

- [ ] **Step 6: Run contract tests**

```bash
python -m unittest tests.test_script_quality_contract -v
```

Expected: PASS. If real project fixtures now fail on STYLE_ONLY error, fix only the fixture/scripts **owned by this task** or loosen detector with clear comments — do not mass-edit production project finals unless a test requires it.

- [ ] **Step 7: Commit**

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py tests/fixtures/script_audit/
git commit -m "$(cat <<'EOF'
feat(script-audit): add onscreen composition structure checks

EOF
)"
```

---

### Task 3: Documentation absorption (`script-quality.md` + `SKILL.md` + vendor notice)

**Files:**
- Modify: `references/script-quality.md`
- Modify: `SKILL.md` (brief)
- Modify: `vendor/ppt-script-visual-redesign/README.md` (top notice)

- [ ] **Step 1: Expand `references/script-quality.md` section「上屏结构与语义图同构」**

Replace/extend that section with content covering:

1. Content-driven composition (do not derive N equal cards from N items).  
2. One visual center aligned to 主判断.  
3. Composition primitive table (the 12 primitives).  
4. `视觉结构` sentence contract: primitive + center/main-chain direction; good/bad examples from the spec.  
5. Default anti-patterns list.  
6. Note: no separate visual-redesign Skill; rules enforced here + `script-audit`.  
7. Note: new checks — style-only is error; thin structure / anti-pattern / primitive mismatch are warnings initially.

Keep「完整文字稿」sections untouched.

- [ ] **Step 2: Patch `SKILL.md` native script-audit blurb**

In the paragraph about `script-audit` / `script-quality.md`, add one sentence:

> 上屏构图纪律（构图原语、视觉结构句式、反卡片墙）已吸收进 `references/script-quality.md` 与 `script-audit`；不得改用 `vendor/ppt-script-visual-redesign` 或旧 `ppt-script` 替代本流程。

- [ ] **Step 3: Vendor README notice**

At top of `vendor/ppt-script-visual-redesign/README.md` after the title:

```markdown
> **CyberPPT 说明：** 本目录仅作构图规则来源对照，**不是**生产入口。
> 上屏/视觉结构纪律已吸收至仓库 `references/script-quality.md` 与 `cyberppt.script_quality_contract`。
> 正式脚本流程请使用根目录 `SKILL.md`（cyber-ppt）与 `python -m cyberppt script-audit`。
```

- [ ] **Step 4: Commit**

```bash
git add references/script-quality.md SKILL.md vendor/ppt-script-visual-redesign/README.md
git commit -m "$(cat <<'EOF'
docs: absorb onscreen composition rules into Stage 01

EOF
)"
```

---

### Task 4: Regression gate and skill-contract touch-up

**Files:**
- Modify if needed: `tests/test_skill_contract.py`
- Run full related suite

- [ ] **Step 1: Check skill-contract expectations**

```bash
python -m unittest tests.test_skill_contract -v
```

If it asserts exact `script-quality.md` snippets or forbids vendor mentions incorrectly, update assertions to require the absorption sentence and/or `构图原语` mention in `script-quality.md`.

- [ ] **Step 2: Run focused regression**

```bash
python -m unittest tests.test_script_quality_contract tests.test_script_audit_command tests.test_skill_contract -v
```

Expected: PASS.

- [ ] **Step 3: Manual smoke (optional but recommended)**

```bash
python -m cyberppt script-audit projects/<any>/ --input tests/fixtures/script_audit/power_scene_matrix.md
```

Confirm command still runs; warnings may appear without forcing exit 4 unless errors exist.

- [ ] **Step 4: Commit only if Task 4 changed files**

```bash
git add tests/test_skill_contract.py
git commit -m "$(cat <<'EOF'
test: align skill contract with onscreen composition absorption

EOF
)"
```

---

## Spec Coverage Check

| Spec item | Task |
|---|---|
| Absorb into Stage 01 only | Tasks 2–3 |
| No independent Skill / no visual layer | Task 3 notices + non-goals |
| No three new required fields | Task 2 uses `视觉结构` only |
| Primitive table + sentence contract in docs | Task 3 |
| Codes: STYLE_ONLY / TOO_THIN / ANTI_PATTERN / MISMATCH | Task 2 |
| Warnings first; STYLE_ONLY error | Tasks 1–2 |
| Retry → `semantic_diagram_realign` | Task 2 |
| handoff unchanged | Explicit non-goal |
| Vendor retained as source, not entry | Task 3 |
| Fidelity rules untouched | Task 3 leaves prose sections alone |

## Placeholder Scan

No TBD/TODO steps. Warning/pass split is explicit in Task 1 because current `script-audit` treats any issue as failure.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-25-stage01-onscreen-composition-absorption.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — fresh subagent per task, review between tasks  
2. **Inline Execution** — run tasks in this session with checkpoints  

Which approach?

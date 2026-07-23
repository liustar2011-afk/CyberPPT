# Solution Outline Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add solution-first material routing, deterministic outline structure auditing, and bounded direction-changing retries to CyberPPT Stage 01.

**Architecture:** A focused `outline_contract` module owns schema loading, route validation, structural rules, and retry directives. A separate command module persists attempts and exposes the workflow through `python -m cyberppt outline-audit`; documentation contracts make solution architecture the default and keep consulting architecture opt-in.

**Tech Stack:** Python 3.11+, standard library (`dataclasses`, `json`, `pathlib`, `re`), `unittest`, existing CyberPPT CLI.

## Global Constraints

- `solution` is the default for research, construction, implementation, feasibility, initiation, government, association, and SOE internal materials.
- `consulting` is allowed only by explicit user request or an unambiguous consulting material type.
- Template and content pages must share one continuous ordered page list.
- Chapter pages contain only chapter number and chapter title; they do not carry content claims or modules.
- Page title and page main message are separate fields.
- Split pages by complete business question and visual center, never one source subsection per page.
- Page count follows content and density; it is neither fixed first nor allowed to grow mechanically.
- Audit failure returns a changed planning direction; retrying the same strategy is invalid.
- Default retry limit is 3; valid configured range is 1 through 5.
- Exhausted retries create an escalation report with 2–3 options instead of abandoning the task.
- Run GitNexus impact analysis before editing every existing function, class, or method.

---

### Task 1: Outline Contract Types and Solution-First Routing

**Files:**
- Create: `cyberppt/outline_contract.py`
- Create: `tests/test_outline_contract.py`

**Interfaces:**
- Produces: `load_outline(path: Path) -> dict[str, object]`
- Produces: `resolve_architecture_mode(outline: dict[str, object]) -> str`
- Produces: `AuditIssue(code: str, message: str, pages: tuple[str, ...], retry_strategy: str)`

- [ ] **Step 1: Write failing routing and schema tests**

```python
def test_solution_material_defaults_to_solution():
    outline = {"material_type": "建设方案", "architecture_mode": "consulting", "user_requested_architecture": False}
    issues = audit_outline(outline)
    assert [issue.code for issue in issues] == ["SOLUTION_ARCHITECTURE_REQUIRED"]

def test_explicit_consulting_request_is_allowed():
    outline = {"material_type": "建设方案", "architecture_mode": "consulting", "user_requested_architecture": True}
    assert resolve_architecture_mode(outline) == "consulting"
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run: `python -m unittest tests.test_outline_contract -v`

Expected: FAIL because `cyberppt.outline_contract` does not exist.

- [ ] **Step 3: Implement strict JSON loading, material classification, and route validation**

Implement immutable issue records, required top-level validation, solution material keyword classification, and explicit override handling. Invalid schemas raise `ValueError` with the missing field name.

- [ ] **Step 4: Run the focused tests and confirm pass**

Run: `python -m unittest tests.test_outline_contract -v`

Expected: PASS.

- [ ] **Step 5: Commit the isolated routing component**

```text
git add cyberppt/outline_contract.py tests/test_outline_contract.py
git commit -m "feat: add solution-first outline routing"
```

### Task 2: Structural Audit Rules

**Files:**
- Modify: `cyberppt/outline_contract.py`
- Modify: `tests/test_outline_contract.py`

**Interfaces:**
- Produces: `audit_outline(outline: dict[str, object]) -> list[AuditIssue]`
- Consumes: normalized `pages` entries from Task 1.

- [ ] **Step 1: Add failing tests for continuous template pages and chapter purity**

Create fixtures where chapter pages are detached from their chapter content and where a chapter page contains `main_message` or `modules`; assert `TEMPLATE_PAGES_DETACHED` and `CHAPTER_PAGE_HAS_CONTENT` respectively.

- [ ] **Step 2: Add failing tests for title/message collapse and mechanical splitting**

Create three adjacent content pages with identical `business_question` and `visual_center`, each containing one same-level module; assert `ATOMIC_SECTION_SPLIT`. Create a page whose `title` equals `main_message`; assert `TITLE_CLAIM_COLLAPSED`.

- [ ] **Step 3: Add failing tests for source-weight distortion and method-page promotion**

Provide `source_section_weights` where the main construction chapter owns 55% of source weight but receives 15% of content-page weight; assert `SOURCE_WEIGHT_DISTORTED`. Provide a one-module page whose only role is a selection principle and lacks source evidence; assert `METHOD_PAGE_OVERPROMOTED`.

- [ ] **Step 4: Run tests to confirm all new cases fail**

Run: `python -m unittest tests.test_outline_contract -v`

Expected: FAIL with missing audit codes.

- [ ] **Step 5: Implement the minimal deterministic rules**

Use stable thresholds documented as module constants: title/message normalized equality; repeated business-question and visual-center runs of at least 3 pages; source-weight deviation greater than 0.20; method-only page with no `source_refs` and at most one module. Return issues in page order and then code order.

- [ ] **Step 6: Run focused tests and confirm pass**

Run: `python -m unittest tests.test_outline_contract -v`

Expected: PASS.

- [ ] **Step 7: Commit the audit rules**

```text
git add cyberppt/outline_contract.py tests/test_outline_contract.py
git commit -m "feat: audit outline structure and page granularity"
```

### Task 3: Retry State and Escalation Reports

**Files:**
- Create: `cyberppt/commands/outline_audit.py`
- Create: `tests/test_outline_audit_command.py`

**Interfaces:**
- Produces: `run_outline_audit(project: Path, input_path: Path, max_attempts: int = 3) -> tuple[int, dict[str, object]]`
- Consumes: `audit_outline()` and `AuditIssue` from Task 2.

- [ ] **Step 1: Write failing persistence and retry tests**

Test that the first failed attempt writes `outline-contract.json`, `outline-audit.json`, and `outline-attempts/attempt-01.json`, returns exit code `4`, and includes a non-empty `retry_directive` with remaining attempts `2`.

- [ ] **Step 2: Write failing unchanged-strategy and exhaustion tests**

Submit the same failing strategy twice and assert an issue that requires a changed strategy. Submit three failed attempts and assert exit code `5` plus `outline-escalation.json` containing 2–3 distinct adjustment options.

- [ ] **Step 3: Run command tests and confirm failure**

Run: `python -m unittest tests.test_outline_audit_command -v`

Expected: FAIL because the command module does not exist.

- [ ] **Step 4: Implement atomic attempt persistence and retry directives**

Write JSON with UTF-8, `ensure_ascii=False`, two-space indentation, and newline termination. Validate `max_attempts` in range 1–5. Derive the next strategy from the ordered unique issue codes; never report the same strategy as the previous attempt.

- [ ] **Step 5: Implement escalation option generation**

Map unresolved issue groups to distinct options: restore source-native chapter order, aggregate by business question, or request explicit user prioritization. Always emit at least 2 and at most 3 options.

- [ ] **Step 6: Run command tests and confirm pass**

Run: `python -m unittest tests.test_outline_audit_command -v`

Expected: PASS.

- [ ] **Step 7: Commit retry workflow**

```text
git add cyberppt/commands/outline_audit.py tests/test_outline_audit_command.py
git commit -m "feat: add bounded outline audit retries"
```

### Task 4: CLI Integration and Project Scaffold

**Files:**
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/init_project.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_container_workspace.py`

**Interfaces:**
- Adds CLI: `outline-audit PROJECT --input FILE [--max-attempts N]`
- Consumes: `run_outline_audit()` from Task 3.

- [ ] **Step 1: Run GitNexus impact analysis for `build_parser`, `main`, and `init_project`**

Record direct callers, affected processes, and risk level in the implementation log. Stop and warn the user before editing if any result is HIGH or CRITICAL.

- [ ] **Step 2: Add failing CLI parser and exit-code tests**

Assert help includes `outline-audit`; a passing input returns `0`; a retryable failure returns `4`; exhausted attempts return `5`; malformed input returns `2` on stderr.

- [ ] **Step 3: Add failing scaffold tests**

Assert newly initialized projects contain `workbench/stages/01-analysis/outline-attempts/` and README instructions for the command and artifacts.

- [ ] **Step 4: Run focused integration tests and confirm failure**

Run: `python -m unittest tests.test_cli tests.test_container_workspace -v`

Expected: FAIL because the command and scaffold directory are absent.

- [ ] **Step 5: Wire the command into the parser and scaffold**

Add one parser branch and one command handler; preserve existing command behavior. Add the attempt directory to project initialization and the generated README flow.

- [ ] **Step 6: Run focused integration tests and confirm pass**

Run: `python -m unittest tests.test_cli tests.test_container_workspace -v`

Expected: PASS.

- [ ] **Step 7: Commit CLI integration**

```text
git add cyberppt/cli.py cyberppt/commands/init_project.py tests/test_cli.py tests/test_container_workspace.py
git commit -m "feat: expose outline audit workflow"
```

### Task 5: Workflow Contract Documentation

**Files:**
- Modify: `SKILL.md`
- Modify: `references/source-analysis.md`
- Modify: `references/storyline.md`
- Modify: `README.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Documents the JSON and CLI interfaces from Tasks 1–4.

- [ ] **Step 1: Add failing contract tests**

Assert the canonical Skill contains `solution` as the default architecture, `consulting` as explicit opt-in, the `SOLUTION_ARCHITECTURE_REQUIRED` gate, continuous template-page ordering, title/message separation, business-question aggregation, and three-attempt retry escalation.

- [ ] **Step 2: Run contract tests and confirm failure**

Run: `python -m unittest tests.test_skill_contract -v`

Expected: FAIL because the current Skill requires MBB/SCR as the universal default.

- [ ] **Step 3: Update the canonical first-stage workflow**

Replace universal SCR language with material routing. Keep evidence traceability mandatory. State that solution materials preserve formal work order and that MBB/SCR remains available only on the consulting route.

- [ ] **Step 4: Update source analysis and storyline references**

Keep evidence extraction architecture-neutral. Add separate solution and consulting planning sections, the structured outline fields, template-page rules, title/message separation, page aggregation criteria, and retry protocol.

- [ ] **Step 5: Update README usage**

Document `outline-audit`, exit codes, artifact locations, and the fact that the generating agent—not the CLI—performs the rewrite.

- [ ] **Step 6: Run contract tests and confirm pass**

Run: `python -m unittest tests.test_skill_contract -v`

Expected: PASS.

- [ ] **Step 7: Commit workflow documentation**

```text
git add SKILL.md references/source-analysis.md references/storyline.md README.md tests/test_skill_contract.py
git commit -m "docs: make solution architecture the default"
```

### Task 6: Full Verification and GitNexus Change Detection

**Files:**
- Verify only; modify prior task files only when a failing test identifies a defect.

**Interfaces:**
- Verifies all interfaces and contracts from Tasks 1–5.

- [ ] **Step 1: Run the new focused suite**

Run: `python -m unittest tests.test_outline_contract tests.test_outline_audit_command tests.test_cli tests.test_container_workspace tests.test_skill_contract -v`

Expected: PASS.

- [ ] **Step 2: Run the complete repository test suite**

Run: `python -m unittest discover -s tests -v`

Expected: PASS with no new failures.

- [ ] **Step 3: Run product health checks**

Run: `python -m cyberppt doctor`

Expected: all checks report `ok`.

- [ ] **Step 4: Exercise the CLI with one passing and one failing fixture**

Confirm exit codes `0` and `4`, inspect written UTF-8 JSON, then run failures to exhaustion and confirm exit code `5` with 2–3 escalation options.

- [ ] **Step 5: Run GitNexus `detect_changes({scope: "compare", base_ref: "main"})`**

Confirm only the outline planning flow, CLI registration, scaffold, and workflow contracts are affected. Report any unexpected execution flow before committing further changes.

- [ ] **Step 6: Review the diff for generated or unrelated files**

Run: `git status --short` and `git diff --check`.

Expected: only planned files are present; no whitespace errors.

- [ ] **Step 7: Commit any verification-only corrections**

If verification reveals a defect, stage the exact corrected paths from Tasks 1–5 and commit them with:

```text
git commit -m "test: verify solution outline audit workflow"
```

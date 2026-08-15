# Source Foundation Route Enforcement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Source Foundation the verified precondition for autonomous production while clearly separating the Foundation-native Outline route from the legacy compatibility route.

**Architecture:** `run_autonomous` will fail closed unless the project contains a valid `integration/cyberppt-handoff-report.json` whose `projection_validation.status` is `ok`. The autonomous runner will audit the projected Source Truth without rerunning legacy Source Truth compilation. Documentation and contract tests will describe two mutually exclusive Outline authoring routes: Foundation-native planning/handoff, or explicit legacy compatibility projection followed by `cyberppt-author-stage01-outline`.

**Tech Stack:** Python 3.12, `unittest`, JSON handoff reports, repository Markdown Skills and AGENTS rules.

## Global Constraints

- Do not modify `docs/superpowers/plans/2026-08-15-source-fact-coverage-gate.md`.
- Do not add Stage 01 approval, receipt, attempt, hash-binding, manifest, ledger, or parallel-run control artifacts.
- Treat Source Foundation outputs as authoritative; compatibility files remain projections.
- Do not manually patch generated project artifacts; only change generators, gates, rules, and tests.
- Preserve the current `OUTLINE_AUTHOR_EDIT_REQUIRED` human authoring gate.

### Task 1: Define the autonomous Source Foundation preflight contract

**Files:**
- Modify: `tests/test_run_autonomous.py`
- Modify: `cyberppt/commands/run_autonomous.py`
- Modify: `cyberppt/autonomous_contract.py` only if the implementation needs a shared path/schema constant.

**Interfaces:**
- Consume: `<project>/integration/cyberppt-handoff-report.json`.
- Require: `report.projection_validation.status == "ok"`.
- Produce: a passed `source-foundation` gate in `run-report.json`, or a `source-foundation` failure before legacy preparation.

- [x] **Step 1: Write the failing tests**

Add to `RunAutonomousTests`:

```python
def test_missing_source_foundation_handoff_blocks_before_legacy_preparation(self) -> None:
    self._write_stage01_inputs()
    handoff = self.project / "integration" / "cyberppt-handoff-report.json"
    handoff.parent.mkdir(parents=True, exist_ok=True)
    handoff.write_text(json.dumps({"projection_validation": {"status": "error"}}), encoding="utf-8")
    with patch("cyberppt.commands.run_autonomous.prepare_source_map") as prepare:
        code, report = run_autonomous(self._contract())
    self.assertEqual(1, code)
    self.assertEqual("source-foundation", report["failed_gate"])
    prepare.assert_not_called()

def test_valid_source_foundation_handoff_prevents_source_truth_recompilation(self) -> None:
    self._write_stage01_inputs()
    self._write_valid_source_foundation_handoff()
    with (
        patch("cyberppt.commands.run_autonomous.prepare_source_map"),
        patch("cyberppt.commands.run_autonomous.run_source_map_audit", return_value=(1, {"status": "rewrite_required"})),
        patch("cyberppt.commands.run_autonomous.compile_source_truth") as compile_truth,
    ):
        code, report = run_autonomous(self._contract())
    self.assertEqual(1, code)
    self.assertEqual("source-map-check", report["failed_gate"])
    compile_truth.assert_not_called()
```

Update the shared test fixture helper to create a valid projection report for existing autonomous-flow tests, keeping the new gate from obscuring their intended failure.

- [x] **Step 2: Run the focused tests and verify the expected RED failure**

Run:

```bash
PYTHONPATH=.:tests /opt/homebrew/bin/python3.12 -m unittest \
  tests.test_run_autonomous.RunAutonomousTests.test_missing_source_foundation_handoff_blocks_before_legacy_preparation \
  tests.test_run_autonomous.RunAutonomousTests.test_valid_source_foundation_handoff_prevents_source_truth_recompilation
```

Expected: both tests fail because `run_autonomous` currently has no `source-foundation` gate and still calls `compile_source_truth`.

- [x] **Step 3: Implement the minimal gate**

Add a private helper in `cyberppt/commands/run_autonomous.py`:

```python
def _source_foundation_report(project: Path) -> Path:
    report = project / "integration" / "cyberppt-handoff-report.json"
    if not report.is_file():
        raise GateBlocked("source-foundation", "validated Source Foundation handoff is missing", report)
    try:
        payload = json.loads(report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GateBlocked("source-foundation", f"invalid Source Foundation handoff: {exc.msg}", report) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("projection_validation"), dict) or payload["projection_validation"].get("status") != "ok":
        raise GateBlocked("source-foundation", "Source Foundation projection validation is not ok", report)
    return report
```

At the beginning of `run_autonomous`, append the passed `source-foundation` gate before `prepare_source_map`. Remove the `compile_source_truth(contract.project)` call so the runner audits the handoff-projected Source Truth rather than overwriting it with the legacy compiler.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run the two tests from Step 2, then:

```bash
PYTHONPATH=.:tests /opt/homebrew/bin/python3.12 -m unittest tests.test_run_autonomous
```

Expected: all autonomous contract and runner tests pass.

### Task 2: Make the two Outline authoring routes mutually exclusive in rules

**Files:**
- Modify: `AGENTS.md`
- Modify: `projects/AGENTS.md`
- Modify: `SKILL.md`
- Modify: `.agents/skills/cyberppt-source-foundation/SKILL.md` only where the route distinction is necessary.
- Test: `tests/test_skill_contract.py`

**Interfaces:**
- Foundation-native route: `ppt-outline-planning` authors `deck-brief.json`/`page-plan.json`, then `cyberppt-handoff` projects them.
- Legacy compatibility route: after Source Foundation preflight/reuse, `compile-outline-draft` produces a candidate, `cyberppt-author-stage01-outline` authors it, and `outline-audit` validates it.

- [x] **Step 1: Write the failing rule-contract tests**

Add assertions that the repository rules state both route names, explicitly prohibit running `cyberppt-author-stage01-outline` over an approved Foundation-native outline, and limit `compile-outline-draft` to compatibility regeneration.

- [x] **Step 2: Run the focused contract test and verify RED**

Run:

```bash
PYTHONPATH=.:tests /opt/homebrew/bin/python3.12 -m unittest tests.test_skill_contract.SkillContractTests.test_outline_routes_are_mutually_exclusive
```

Expected: FAIL because the current rules require the legacy authoring step without describing the Foundation-native exception.

- [x] **Step 3: Update the rules**

State the route decision tree in all applicable instructions, keeping deterministic audits and compilers as code-owned steps and preserving the existing authoring gate.

- [x] **Step 4: Run the Skill and integration contract suites**

```bash
PYTHONPATH=.:tests /opt/homebrew/bin/python3.12 -m unittest tests.test_skill_contract tests.test_source_foundation_integration
```

Expected: all tests pass.

### Task 3: Verify the complete affected chain and merge

**Files:**
- No additional production files.
- Verify: `docs/superpowers/plans/2026-08-15-source-foundation-route-enforcement.md` and the protected existing plan remain distinct.

- [x] **Step 1: Run all focused Stage 01/autonomous tests**

```bash
PYTHONPATH=.:tests /opt/homebrew/bin/python3.12 -m unittest \
  tests.test_run_autonomous \
  tests.test_skill_contract \
  tests.test_source_foundation_integration \
  tests.test_stage01_compiler tests.test_source_argument_model \
  tests.test_source_truth_audit_command tests.test_outline_review
```

- [x] **Step 2: Run syntax and whitespace checks**

```bash
PYTHONDONTWRITEBYTECODE=1 /opt/homebrew/bin/python3.12 -c 'import ast, pathlib; ast.parse(pathlib.Path("cyberppt/commands/run_autonomous.py").read_text())'
git diff --check
```

- [x] **Step 3: Inspect the diff and confirm only scoped files changed**

```bash
git status --short --branch
git diff --stat
```

- [x] **Step 4: Commit and merge to local `main`**

```bash
git add cyberppt/commands/run_autonomous.py tests/test_run_autonomous.py AGENTS.md projects/AGENTS.md SKILL.md .agents/skills/cyberppt-source-foundation/SKILL.md tests/test_skill_contract.py
git commit -m "fix(workflow): gate autonomous runs on source foundation"
git switch main
git merge --no-ff <feature-branch> -m "Merge branch '<feature-branch>'"
```

- [x] **Step 5: Re-run the focused suite on merged `main` and report the exact commit and merge hashes.**

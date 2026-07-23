# Source Truth Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an auditable Source Truth contract, changed-direction retry workflow, Markdown renderer, and use them to replace the coarse evidence map in the power-supply-demand project.

**Architecture:** Keep validation and issue generation in a pure `source_truth_contract` module. Put filesystem persistence, retry state, escalation, and rendering in a `source_truth_audit` command module, then expose it through the existing CLI and project scaffold. Project evidence is stored as JSON and rendered to the existing analysis Markdown.

**Tech Stack:** Python 3.10+, standard library (`dataclasses`, `hashlib`, `json`, `pathlib`, `re`), `unittest`, existing CyberPPT CLI conventions.

## Global Constraints

- `source-truth.json` is the authoritative structured artifact; Markdown is a generated readable view.
- Evidence types are exactly `F`, `J`, `R`, `B`, and `U`.
- Completeness is determined by coverage targets, precise locators, atomicity, and traceability—not by a fixed Source ID count.
- Audit failure changes extraction direction and preserves the best current result; it never silently abandons the task.
- Existing unrelated working-tree changes must not be modified or reverted.
- Before editing an existing function, run or document the best available GitNexus upstream impact check.

---

### Task 1: Pure Source Truth contract and issue model

**Files:**
- Create: `cyberppt/source_truth_contract.py`
- Create: `tests/test_source_truth_contract.py`

**Interfaces:**
- Produces: `load_source_truth(path: Path) -> dict[str, object]`
- Produces: `audit_source_truth(payload: dict[str, object]) -> list[SourceTruthIssue]`
- Produces: `source_truth_retry_directive(issues: list[SourceTruthIssue], previous_strategy: str = "") -> dict[str, object]`
- Produces: `SourceTruthIssue.to_dict() -> dict[str, object]`

- [ ] **Step 1: Write failing schema and atomicity tests**

```python
def test_rejects_unknown_schema(self) -> None:
    path = self._write({"schema": "wrong"})
    with self.assertRaisesRegex(ValueError, "cyberppt.source_truth.v1"):
        load_source_truth(path)

def test_flags_composite_record_and_imprecise_locator(self) -> None:
    payload = valid_payload()
    payload["records"][0]["type"] = ["F", "R"]
    payload["records"][0]["source_locator"] = {
        "file": "source.docx",
        "section": "第一章",
    }
    codes = {item.code for item in audit_source_truth(payload)}
    self.assertIn("SOURCE_RECORD_COMPOSITE", codes)
    self.assertIn("SOURCE_LOCATOR_IMPRECISE", codes)
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```powershell
python -m pytest tests/test_source_truth_contract.py -q
```

Expected: collection fails because `cyberppt.source_truth_contract` does not exist.

- [ ] **Step 3: Implement schema loading and issue primitives**

```python
SCHEMA = "cyberppt.source_truth.v1"
EVIDENCE_TYPES = frozenset({"F", "J", "R", "B", "U"})
PRIORITIES = frozenset({"P0", "P1", "P2"})

@dataclass(frozen=True)
class SourceTruthIssue:
    code: str
    message: str
    source_ids: tuple[str, ...] = ()
    retry_strategy: str = "section_sweep"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

def load_source_truth(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("source truth root must be an object")
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    for field in ("sources", "coverage_targets", "records", "conclusions", "pages", "retry"):
        if field not in payload:
            raise ValueError(f"missing required field: {field}")
    return payload
```

Implement record checks so a record has one valid type, stable unique ID, valid priority, quote, precise locator (`paragraph`, `table`, or `table_row` in addition to file/section), and consistent type/status.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run:

```powershell
python -m pytest tests/test_source_truth_contract.py -q
```

Expected: all current contract tests pass.

- [ ] **Step 5: Add failing coverage, numeric, and traceability tests**

```python
def test_flags_numeric_table_boundary_priority_and_traceability_gaps(self) -> None:
    payload = valid_payload()
    payload["coverage_targets"] = [
        {"id": "T1", "kind": "table", "priority": "P0", "required": True, "record_refs": []},
        {"id": "T2", "kind": "boundary", "priority": "P1", "required": True, "record_refs": []},
    ]
    payload["records"][0]["numeric"] = {"raw_value": "100"}
    payload["records"][0]["supports"] = ["C404"]
    payload["records"][0]["page_refs"] = ["p404"]
    codes = {item.code for item in audit_source_truth(payload)}
    self.assertTrue({
        "SOURCE_NUMERIC_FIELDS_MISSING",
        "SOURCE_TABLE_COVERAGE_MISSING",
        "SOURCE_BOUNDARY_COVERAGE_MISSING",
        "SOURCE_PRIORITY_COVERAGE_MISSING",
        "SOURCE_TRACEABILITY_BROKEN",
    }.issubset(codes))
```

- [ ] **Step 6: Run the new test and verify RED**

Run:

```powershell
python -m pytest tests/test_source_truth_contract.py -q
```

Expected: assertions fail because coverage and traceability checks are missing.

- [ ] **Step 7: Implement remaining audit checks and retry direction**

`audit_source_truth` must:

- validate numeric `raw_value`, `raw_unit`, `period`, and `scope`;
- require every required coverage target to resolve to existing records;
- emit kind-specific table and boundary codes plus P0/P1 coverage code;
- verify record `supports` and `page_refs` against declared conclusion/page IDs;
- verify conclusions and pages refer back to existing record IDs;
- return issues sorted by issue code and first Source ID.

`source_truth_retry_directive` must select:

```python
strategies = ("section_sweep", "structured_fact_sweep", "traceability_rebuild")
```

It must advance away from `previous_strategy`, prioritizing `structured_fact_sweep` for numeric/table/boundary gaps and `traceability_rebuild` for broken references.

- [ ] **Step 8: Run contract tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_source_truth_contract.py -q
```

Expected: all tests pass with no warnings.

### Task 2: Audit command, persistence, retries, and Markdown renderer

**Files:**
- Create: `cyberppt/commands/source_truth_audit.py`
- Create: `tests/test_source_truth_audit_command.py`

**Interfaces:**
- Consumes: `load_source_truth`, `audit_source_truth`, `source_truth_retry_directive`
- Produces: `run_source_truth_audit(project: Path, input_path: Path, max_attempts: int = 3) -> tuple[int, dict[str, object]]`
- Produces: `render_source_truth_markdown(payload: dict[str, object], report: dict[str, object]) -> str`

- [ ] **Step 1: Write failing persistence and retry tests**

```python
def test_failed_attempt_persists_and_changes_direction(self) -> None:
    payload = invalid_payload(attempt=1, strategy="section_sweep")
    code, report = run_source_truth_audit(self.project, self._write(payload))
    stage = self.project / "workbench" / "stages" / "01-analysis"
    self.assertEqual(4, code)
    self.assertEqual("structured_fact_sweep", report["retry_directive"]["strategy"])
    self.assertTrue((stage / "source-truth.json").exists())
    self.assertTrue((stage / "source-truth-audit.json").exists())
    self.assertTrue((stage / "source-truth-attempts" / "attempt-01.json").exists())

def test_third_failure_preserves_best_result_and_escalates(self) -> None:
    payload = invalid_payload(attempt=3, strategy="traceability_rebuild")
    code, report = run_source_truth_audit(self.project, self._write(payload))
    self.assertEqual(5, code)
    self.assertEqual("user_decision_required", report["status"])
    self.assertTrue((self.stage / "source-truth-escalation.json").exists())
    self.assertTrue((self.stage / "source-truth.json").exists())
```

- [ ] **Step 2: Run command tests and verify RED**

Run:

```powershell
python -m pytest tests/test_source_truth_audit_command.py -q
```

Expected: collection fails because the audit command module does not exist.

- [ ] **Step 3: Implement persistence and bounded retry**

Use the existing outline-audit return convention:

- `0`: passed;
- `4`: rewrite required with attempts remaining;
- `5`: current best result preserved and user decision required;
- invalid input raises `ValueError` or `FileNotFoundError`.

Persist JSON with UTF-8 and `ensure_ascii=False`. Report schema is `cyberppt.source_truth_audit.v1`; include status, attempt, maximum, remaining attempts, coverage summary, serialized issues, and one retry directive.

- [ ] **Step 4: Run command tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_source_truth_audit_command.py -q
```

Expected: persistence and escalation tests pass.

- [ ] **Step 5: Write failing renderer test**

```python
def test_passed_contract_generates_readable_markdown(self) -> None:
    code, report = run_source_truth_audit(self.project, self._write(valid_payload()))
    rendered = (self.stage / "00-source-analysis.md").read_text(encoding="utf-8")
    self.assertEqual(0, code)
    self.assertIn("# 源材料分析与 Source Truth Map", rendered)
    self.assertIn("| Source ID | 类型 | 优先级 |", rendered)
    self.assertIn("## 覆盖与审计结论", rendered)
    self.assertIn("S001", rendered)
```

- [ ] **Step 6: Run renderer test and verify RED**

Run:

```powershell
python -m pytest tests/test_source_truth_audit_command.py -q
```

Expected: Markdown file assertion fails.

- [ ] **Step 7: Implement deterministic Markdown rendering**

Render source inventory, source records, coverage status, conflicts/unknowns, conclusion traceability, page traceability, and audit status. Escape Markdown table pipes and convert arrays to `；`-separated text. Do not infer new claims during rendering.

- [ ] **Step 8: Run command tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_source_truth_audit_command.py -q
```

Expected: all command and renderer tests pass.

### Task 3: CLI and project scaffold integration

**Files:**
- Modify: `cyberppt/cli.py`
- Modify: `cyberppt/commands/init_project.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_outline_audit_command.py`

**Interfaces:**
- Consumes: `run_source_truth_audit`
- Produces: CLI command `source-truth-audit`
- Produces: scaffold directory `workbench/stages/01-analysis/source-truth-attempts`

- [ ] **Step 1: Run GitNexus impact checks before editing existing symbols**

Targets:

```text
build_parser
main
init_project
```

If the MCP impact tool remains unavailable, record static direct callers/importers from the indexed repository and treat the CLI and initializer as medium-risk public entry points.

- [ ] **Step 2: Write failing CLI and scaffold tests**

```python
def test_help_lists_source_truth_audit(self) -> None:
    parser = build_parser()
    self.assertIn("source-truth-audit", parser.format_help())

def test_source_truth_audit_cli_returns_audit_code(self) -> None:
    with patch("cyberppt.cli.run_source_truth_audit", return_value=(4, {"status": "rewrite_required"})):
        code = main(["source-truth-audit", "project", "--input", "source-truth.json"])
    self.assertEqual(4, code)

def test_project_scaffold_contains_source_truth_attempt_directory(self) -> None:
    init_project(self.project)
    self.assertTrue((self.project / "workbench/stages/01-analysis/source-truth-attempts").is_dir())
    self.assertIn("source-truth-audit", (self.project / "README.md").read_text(encoding="utf-8"))
```

- [ ] **Step 3: Run integration tests and verify RED**

Run:

```powershell
python -m pytest tests/test_cli.py tests/test_outline_audit_command.py -q
```

Expected: new command and directory assertions fail.

- [ ] **Step 4: Register the command and update the scaffold**

Add:

```python
from cyberppt.commands.source_truth_audit import run_source_truth_audit
```

Add `_source_truth_audit_command` using the same exception and JSON-output behavior as `_outline_audit_command`. Register `source-truth-audit` with `project`, required `--input`, and bounded `--max-attempts`. Add the attempts directory to `PROJECT_DIRS`, manifest mapping, and README flow before outline audit.

- [ ] **Step 5: Run integration tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_cli.py tests/test_outline_audit_command.py tests/test_source_truth_audit_command.py -q
```

Expected: all tests pass.

### Task 4: Repository workflow contract and reference guidance

**Files:**
- Modify: `references/source-analysis.md`
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Produces: workflow requirement that Source Truth JSON passes or escalates before outline planning
- Produces: documented evidence taxonomy, exact locator standard, coverage targets, and changed-direction retry behavior

- [ ] **Step 1: Identify impacted documentation contracts**

Review static references to Stage 01, `source-analysis.md`, and `outline-audit`. No function/class symbol is edited in this task.

- [ ] **Step 2: Write failing contract tests**

```python
def test_source_truth_contract_precedes_outline(self) -> None:
    skill = SKILL_FILE.read_text(encoding="utf-8")
    reference = (REFERENCES_DIR / "source-analysis.md").read_text(encoding="utf-8")
    self.assertIn("source-truth.json", skill)
    self.assertIn("source-truth-audit", skill)
    self.assertIn("F / J / R / B / U", reference)
    self.assertIn("structured_fact_sweep", reference)
```

- [ ] **Step 3: Run documentation contract test and verify RED**

Run:

```powershell
python -m pytest tests/test_skill_contract.py -q
```

Expected: new Source Truth contract assertions fail.

- [ ] **Step 4: Update repository instructions**

Document:

- JSON authority and Markdown rendering;
- atomic evidence types;
- paragraph/table-row locators;
- source inventories and coverage targets;
- audit codes and retry directions;
- requirement to finish or escalate Source Truth before outline planning.

Keep solution architecture as the default for formal scheme/research materials.

- [ ] **Step 5: Run documentation tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_skill_contract.py -q
```

Expected: all documentation contract tests pass.

### Task 5: Rebuild the power-supply-demand Source Truth with the new contract

**Files:**
- Create: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth.json`
- Modify (generated): `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/00-source-analysis.md`
- Create (generated): `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth-audit.json`
- Create (generated): `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth-attempts/attempt-01.json`
- Modify if Source IDs change: `projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/outline.json`
- Modify: `projects/power-supply-demand-forecast-early-warning/workbench/artifact-ledger.json`

**Interfaces:**
- Consumes: source DOCX and completed Source Truth audit command
- Produces: complete project evidence map and rendered Markdown

- [ ] **Step 1: Inventory the source document deterministically**

Extract and number every non-empty paragraph, heading, table, table row, and cell from:

```text
projects/power-supply-demand-forecast-early-warning/source/电力供需形势预测与预警能力建设前期研究方案-无摘要版.docx
```

Record counts and a stable locator for each extracted unit. Preserve original wording and do not silently correct source numbers.

- [ ] **Step 2: Build atomic coverage targets and records**

Create coverage targets for all 75 headings, 4 tables, key numeric/investment/time/personnel items, boundary expressions, initial/deferred scenarios, data responsibility, acceptance, risk, and initiation conditions. Split evidence into approximately 50–80 records only as a working expectation; permit more or fewer when semantic atomicity requires it.

- [ ] **Step 3: Run the new audit**

Run:

```powershell
python -m cyberppt source-truth-audit projects/power-supply-demand-forecast-early-warning --input projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/source-truth.json
```

Expected: exit `0`, or exit `4` with a concrete changed-direction retry directive.

- [ ] **Step 4: Follow retry directions until pass or bounded escalation**

For exit `4`, increment `retry.attempt`, set `retry.strategy` to the emitted strategy, correct evidence—not audit rules—and rerun. If exit `5`, preserve the best result and report every remaining issue instead of claiming completeness.

- [ ] **Step 5: Repair downstream references and ledger**

Ensure every `outline.json` `source_refs` value resolves to an existing Source ID. Update the artifact ledger with relative path, SHA-256, producing command, and status for JSON, Markdown, and audit report.

- [ ] **Step 6: Re-run outline audit**

Run:

```powershell
python -m cyberppt outline-audit projects/power-supply-demand-forecast-early-warning --input projects/power-supply-demand-forecast-early-warning/workbench/stages/01-analysis/outline.json
```

Expected: exit `0`, or preserve and report the existing outline-specific failure without weakening Source Truth rules.

### Task 6: Full verification and change-impact review

**Files:**
- Verify all files changed in Tasks 1–5

**Interfaces:**
- Consumes: implemented code and project artifacts
- Produces: fresh evidence for completion claims

- [ ] **Step 1: Run focused tests**

```powershell
python -m pytest tests/test_source_truth_contract.py tests/test_source_truth_audit_command.py tests/test_cli.py tests/test_outline_audit_command.py tests/test_skill_contract.py -q
```

Expected: zero failures and zero errors.

- [ ] **Step 2: Run the full test suite**

```powershell
python -m pytest -q
```

Expected: zero failures and zero errors. If unrelated pre-existing tests fail, record exact test names and verify the focused suite remains green.

- [ ] **Step 3: Run CLI smoke checks**

```powershell
python -m cyberppt --help
python -m cyberppt source-truth-audit --help
```

Expected: both return exit `0` and show the new command/options.

- [ ] **Step 4: Run GitNexus change detection**

Run `detect_changes({scope: "compare", base_ref: "main"})` when the MCP tool is available. Confirm only Source Truth, CLI initialization, documentation contracts, and the named project flow are affected. If unavailable, report that limitation and use explicit file/symbol diff plus focused regression results; do not claim GitNexus verification occurred.

- [ ] **Step 5: Inspect the final diff**

Verify no unrelated modified or untracked files are staged or included. Do not delete or normalize the repository’s pre-existing AppleDouble `._*` files as part of this feature.

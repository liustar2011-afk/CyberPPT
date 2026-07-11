# Stage 1 LLM Quality Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a prompt-first, evidence-grounded, model-assisted generation workflow for all five CyberPPT Stage 1 analysis-expression gates without weakening existing human approvals.

**Architecture:** Add a focused `cyberppt.phase1` package for source bundling, prompt preparation, strict model-output parsing, deterministic grounding, rendering, provenance, and orchestration. Reuse the existing Codex Responses transport with configurable text instructions, expose the workflow through nested `cyberppt phase1` commands, and delegate final staging to the existing analysis-expression gate.

**Tech Stack:** Python 3.10+ standard library, argparse, dataclasses, JSON/Markdown artifacts, existing Codex OAuth Responses transport, pytest/unittest-compatible tests.

## Global Constraints

- Read `SKILL.md`, `references/source-analysis.md`, `references/storyline.md`, and `references/internal-reporting-style.md` before implementing prompt content.
- Before editing each existing symbol, run GitNexus upstream impact analysis. The MCP transport was unavailable while this plan was written, so implementation must rerun impact for `_build_text_responses_body`, `run_codex_vision_text`, `build_parser`, `init_project`, `validate_analysis_artifact`, and `stage_analysis_artifact` after restarting the GitNexus MCP service.
- Warn and stop for review if any impact result is HIGH or CRITICAL.
- Keep `stage-*`, `approve-*`, and `analysis-expression-status` backward compatible.
- Do not automatically stage or approve a model-generated candidate.
- `phase1 generate` must consume the current reviewable prompt MD exactly as edited and must not overwrite it.
- Deterministic QA owns evidence IDs, source locators, number fidelity, hashes, and stale-dependency checks.
- Critic findings are advisory; deterministic grounding failures block model-assisted staging.
- Do not add a runtime dependency to `pyproject.toml`.
- Do not productize raw DOCX/PDF/XLSX extraction in this plan; consume a normalized Markdown/JSON source extract.
- Do not modify Stage 2 generation or delivery behavior.
- Before every commit, run GitNexus `detect_changes({scope: "staged", repo: "CyberPPT"})` and inspect affected flows.

---

### Task 1: Stage 1 Artifact Paths And Run Contracts

**Files:**
- Create: `cyberppt/phase1/__init__.py`
- Create: `cyberppt/phase1/artifacts.py`
- Modify: `cyberppt/commands/init_project.py`
- Test: `tests/test_phase1_artifacts.py`
- Test: `tests/test_script_gate.py`

**Interfaces:**
- Produces: `Phase1Paths`, `Phase1Run`, `phase1_paths(project: Path, gate: str) -> Phase1Paths`, `write_phase1_run(run: Phase1Run) -> Path`, `append_phase1_ledger_records(project: Path, records: list[dict[str, object]]) -> Path`.
- Consumes later: every Stage 1 preparation, generation, critic, status, and staging task.

- [ ] **Step 1: Write the failing artifact-path tests**

```python
def test_phase1_paths_are_gate_scoped(tmp_path: Path) -> None:
    paths = phase1_paths(tmp_path / "project", "source_analysis")
    assert paths.root.name == "source_analysis"
    assert paths.source_bundle_json.name == "source_bundle.json"
    assert paths.source_bundle_markdown.name == "source_bundle.md"
    assert paths.chunks_dir.name == "chunks"
    assert paths.prompt.name == "source_analysis_prompt.md"
    assert paths.raw_output.name == "source_analysis_raw.json"
    assert paths.candidate.name == "source_analysis.md"
    assert paths.grounding_report.name == "source_analysis_grounding.json"
    assert paths.run_manifest.name == "run.json"


def test_init_project_creates_phase1_model_run_directories(tmp_path: Path) -> None:
    project = tmp_path / "project"
    init_project(project)
    root = project / "workbench/stages/01-analysis/model-runs"
    assert root.is_dir()
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_artifacts.py tests/test_script_gate.py -q`

Expected: FAIL because `cyberppt.phase1.artifacts` and the scaffold directories do not exist.

- [ ] **Step 3: Implement immutable path and run dataclasses**

```python
@dataclass(frozen=True)
class Phase1Paths:
    root: Path
    source_bundle_json: Path
    source_bundle_markdown: Path
    chunks_dir: Path
    prompt: Path
    raw_output: Path
    candidate: Path
    grounding_report: Path
    critic_prompt: Path
    critic_raw: Path
    critic_report: Path
    run_manifest: Path


@dataclass(frozen=True)
class Phase1Run:
    gate: str
    status: str
    prompt_path: str
    prompt_sha256: str
    dependency_hashes: dict[str, str]
    model: str | None = None
    raw_output_path: str | None = None
    candidate_path: str | None = None
    grounding_report_path: str | None = None
    error: str | None = None
```

Implement JSON serialization with `schema="cyberppt.phase1_run.v1"`, UTC timestamps, SHA-256 helpers, path creation, and ledger records that preserve existing ledger fields while adding a nested `generator` object.

- [ ] **Step 4: Add scaffold directories and manifest entries**

Add this path to `PROJECT_DIRS` and `_project_manifest()`; gate-specific child directories are created by `phase1_paths()` when used:

```text
workbench/stages/01-analysis/model-runs
```

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_phase1_artifacts.py tests/test_script_gate.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/phase1/__init__.py cyberppt/phase1/artifacts.py cyberppt/commands/init_project.py tests/test_phase1_artifacts.py tests/test_script_gate.py
git commit -m "feat: add stage one model artifact contracts"
```

### Task 2: Configurable Text Instructions In The Existing Model Transport

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/codex_oauth_image.py`
- Test: `tests/test_codex_responses_text.py`
- Test: `tests/test_speaker_notes.py`
- Test: `tests/test_ocr_text_locator.py`

**Interfaces:**
- Produces: `run_codex_text(*, prompt: str, instructions: str, model: str | None = None, dry_run: bool = False, timeout: int = DEFAULT_TIMEOUT) -> str`.
- Preserves: `run_codex_vision_text(...) -> str` with its current defaults and callers.

- [ ] **Step 1: Run GitNexus impact analysis**

Run MCP impact for `_build_text_responses_body` and `run_codex_vision_text`. Confirm direct callers include `scripts/speaker_notes.py` and `scripts/dual_image_overlay/rebuild_engine/ocr_text_locator.py`; stop and warn if risk is HIGH or CRITICAL.

- [ ] **Step 2: Write failing transport tests**

```python
def test_text_response_body_uses_caller_instructions() -> None:
    body = _build_text_responses_body(
        prompt="Return JSON",
        image_paths=[],
        model="gpt-test",
        instructions="You are a grounded report analyst.",
    )
    assert body["instructions"] == "You are a grounded report analyst."


def test_run_codex_vision_text_keeps_vision_default(monkeypatch) -> None:
    captured = {}
    monkeypatch.setattr(module, "_post_codex_sse", lambda body, timeout: captured.setdefault("body", body) or "")
    monkeypatch.setattr(module, "_extract_responses_text", lambda body: "{}")
    assert run_codex_vision_text(prompt="x", image_paths=[]) == "{}"
    assert "slide image analysis" in captured["body"]["instructions"]
```

- [ ] **Step 3: Run tests and verify failure**

Run: `python3 -m pytest tests/test_codex_responses_text.py -q`

Expected: FAIL because `instructions` and `run_codex_text` are not implemented.

- [ ] **Step 4: Implement the generic wrapper without changing existing defaults**

```python
def run_codex_text(
    *,
    prompt: str,
    instructions: str,
    model: str | None = None,
    dry_run: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
) -> str:
    return _run_codex_responses_text(
        prompt=prompt,
        image_paths=[],
        instructions=instructions,
        model=model,
        dry_run=dry_run,
        timeout=timeout,
    )
```

Refactor `run_codex_vision_text()` to delegate to the same private function using its existing vision instruction. Keep dry-run JSON fields compatible.

- [ ] **Step 5: Run transport and caller regressions**

Run: `python3 -m pytest tests/test_codex_responses_text.py tests/test_speaker_notes.py tests/test_ocr_text_locator.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/codex_oauth_image.py tests/test_codex_responses_text.py tests/test_speaker_notes.py tests/test_ocr_text_locator.py
git commit -m "refactor: expose generic codex text responses"
```

### Task 3: Normalize Source Extracts Into Groundable Units

**Files:**
- Create: `cyberppt/phase1/source_bundle.py`
- Test: `tests/test_phase1_source_bundle.py`

**Interfaces:**
- Produces: `SourceUnit`, `SourceBundle`, `build_source_bundle(source: Path, *, max_chunk_chars: int = 40000) -> SourceBundle`, `write_source_bundle(bundle: SourceBundle, paths: Phase1Paths) -> tuple[Path, Path]`.
- Consumes: UTF-8 `.md`, `.txt`, or the Markdown sibling of an existing normalized `.json` extract.

- [ ] **Step 1: Write failing tests for stable units, locators, numbers, and chunks**

```python
def test_source_bundle_preserves_locator_and_numbers(tmp_path: Path) -> None:
    source = tmp_path / "source_extract.md"
    source.write_text("## P26\n2025年用电量103682亿千瓦时，同比增长5.0%。\n", encoding="utf-8")
    bundle = build_source_bundle(source, max_chunk_chars=20)
    unit = bundle.units[0]
    assert unit.unit_id == "U0001"
    assert unit.locator == "P26"
    assert "103682" in unit.numbers
    assert "5.0" in unit.numbers
    assert bundle.chunks[0].unit_ids == ("U0001",)
```

Add tests for Markdown tables, repeated headings, blank sections, overlong units split only at paragraph/table-row boundaries, and stable output across repeated runs.

- [ ] **Step 2: Run the tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_source_bundle.py -q`

Expected: FAIL because the module does not exist.

- [ ] **Step 3: Implement source dataclasses and deterministic parsing**

```python
@dataclass(frozen=True)
class SourceUnit:
    unit_id: str
    kind: str
    text: str
    source_path: str
    locator: str
    numbers: tuple[str, ...]


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    unit_ids: tuple[str, ...]
    character_count: int


@dataclass(frozen=True)
class SourceBundle:
    source_path: str
    source_sha256: str
    units: tuple[SourceUnit, ...]
    chunks: tuple[SourceChunk, ...]
```

Use source order for IDs. Extract numbers with one centralized regex that preserves decimal values and units in the unit text. Do not infer facts or rewrite source text.

- [ ] **Step 4: Render machine and human bundle artifacts**

Write `source_bundle.json` with schema `cyberppt.phase1_source_bundle.v1` and `source_bundle.md` containing unit ID, locator, kind, numbers, and verbatim text.

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_phase1_source_bundle.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/phase1/source_bundle.py tests/test_phase1_source_bundle.py
git commit -m "feat: build grounded stage one source bundles"
```

### Task 4: Source Analysis Prompt, Strict Schema, And Grounding

**Files:**
- Create: `cyberppt/phase1/schemas.py`
- Create: `cyberppt/phase1/prompts.py`
- Create: `cyberppt/phase1/grounding.py`
- Create: `cyberppt/phase1/renderers.py`
- Test: `tests/test_phase1_source_analysis.py`

**Interfaces:**
- Produces: `EvidenceCandidate`, `SourceAnalysisDraft`, `parse_source_analysis_output(text: str) -> SourceAnalysisDraft`, `build_source_analysis_prompt(bundle: SourceBundle, references: dict[str, str]) -> str`, `ground_source_analysis(draft: SourceAnalysisDraft, bundle: SourceBundle) -> GroundingReport`, `render_source_analysis(draft: SourceAnalysisDraft, report: GroundingReport) -> str`.

- [ ] **Step 1: Write failing strict-parse and grounding tests**

```python
def test_grounding_rejects_number_missing_from_cited_units() -> None:
    bundle = bundle_with_unit("U0001", "2025年用电量103682亿千瓦时", numbers=("2025", "103682"))
    draft = SourceAnalysisDraft(
        material_type="工作方案",
        reporting_task="领导审定",
        audience="分管领导",
        evidence=(EvidenceCandidate(
            claim="2025年用电量达到120000亿千瓦时",
            verbatim_support="2025年用电量103682亿千瓦时",
            source_unit_ids=("U0001",),
            numbers=("120000",),
            confidence="high",
            caveat="",
            meaning="说明运行规模",
            visual="KPI",
        ),),
        storylines=(),
        material_pool=(),
        confirmation_questions=(),
    )
    report = ground_source_analysis(draft, bundle)
    assert report.blocking
    assert report.issues[0].code == "number_not_in_source"
```

Add tests for unknown unit IDs, non-verbatim support, missing caveat fields, invalid JSON, fenced JSON, duplicate evidence, and deterministic E-ID assignment.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_source_analysis.py -q`

Expected: FAIL because the schemas and grounding functions do not exist.

- [ ] **Step 3: Implement strict standard-library schemas**

Use frozen dataclasses and explicit `from_payload()` methods. Reject unknown top-level shapes, missing required arrays, non-string IDs, and non-list evidence. Do not silently coerce malformed model output.

- [ ] **Step 4: Build the reviewable prompt from repository references**

The prompt must include:

```text
【任务】生成 source_analysis 严格 JSON
【事实边界】不得新增事实、数字、来源或外部知识
【输出结构】material_type/reporting_task/audience/evidence/storylines/material_pool/confirmation_questions
【证据要求】每条证据引用 source_unit_ids 和 verbatim_support
【文风】internal_public_sector + source_and_task_adaptive
【源材料单元】
{rendered_source_units}
```

Load the full current text of the three Stage 1 references. Record their hashes in the run dependencies.

- [ ] **Step 5: Implement deterministic grounding and Markdown rendering**

Assign E IDs after accepted evidence is sorted by first cited source unit. Render all headings required by `validate_analysis_artifact("source_analysis", text)` and include rejected/uncertain evidence in a non-authoritative QA appendix, not the evidence table.

- [ ] **Step 6: Run tests**

Run: `python3 -m pytest tests/test_phase1_source_analysis.py tests/test_analysis_expression_gate.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add cyberppt/phase1/schemas.py cyberppt/phase1/prompts.py cyberppt/phase1/grounding.py cyberppt/phase1/renderers.py tests/test_phase1_source_analysis.py
git commit -m "feat: ground model generated source analysis"
```

### Task 5: Downstream Gate Prompts, Schemas, And Renderers

**Files:**
- Modify: `cyberppt/phase1/schemas.py`
- Modify: `cyberppt/phase1/prompts.py`
- Modify: `cyberppt/phase1/grounding.py`
- Modify: `cyberppt/phase1/renderers.py`
- Test: `tests/test_phase1_downstream_gates.py`

**Interfaces:**
- Produces: `build_gate_prompt(gate: str, approved: dict[str, str], evidence_registry: str, references: dict[str, str]) -> str`, `parse_gate_output(gate: str, text: str) -> object`, `ground_gate_output(gate: str, draft: object, evidence_ids: set[str]) -> GroundingReport`, `render_gate_output(gate: str, draft: object) -> str`.
- Supports exactly: `reporting_direction`, `report_structure`, `page_design`, `business_script`.

- [ ] **Step 1: Write failing tests for all four gates**

```python
@pytest.mark.parametrize("gate", ["reporting_direction", "report_structure", "page_design", "business_script"])
def test_unknown_evidence_ids_block_downstream_gate(gate: str) -> None:
    draft = valid_draft_for(gate, evidence_ids=("E99",))
    report = ground_gate_output(gate, draft, {"E01", "E02"})
    assert any(issue.code == "unknown_evidence_id" for issue in report.issues)


def test_business_script_visible_numbers_must_exist_in_cited_evidence() -> None:
    draft = business_page(number="120000", evidence_ids=("E01",))
    report = ground_gate_output("business_script", draft, {"E01"}, evidence_numbers={"E01": {"103682"}})
    assert any(issue.code == "visible_number_not_grounded" for issue in report.issues)
```

Add tests that every content page has a caveat/boundary, meaning, transition, density target, component list, and evidence IDs; navigation pages are exempt from business evidence requirements.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_downstream_gates.py -q`

Expected: FAIL because downstream schemas are not implemented.

- [ ] **Step 3: Implement gate-specific dataclasses**

Define explicit types for direction options, report modules, page plans, and business pages. Keep their fields aligned with the current reference contracts and existing Markdown gate headings.

- [ ] **Step 4: Implement dependency-aware prompts**

Each prompt must include approved upstream text and hashes, the frozen evidence registry, output JSON schema, prohibited unsupported inference, and the internal-reporting style contract. `report_structure` must be task-adaptive; prompt examples may use 4-6 modules but must not require that count semantically.

- [ ] **Step 5: Implement rendering and grounding**

Render Markdown accepted by the existing gates. For business pages, render separate visible content and non-visible evidence, source, completeness, density, meaning, and transition sections.

- [ ] **Step 6: Run downstream and existing gate tests**

Run: `python3 -m pytest tests/test_phase1_downstream_gates.py tests/test_analysis_expression_gate.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add cyberppt/phase1/schemas.py cyberppt/phase1/prompts.py cyberppt/phase1/grounding.py cyberppt/phase1/renderers.py tests/test_phase1_downstream_gates.py
git commit -m "feat: generate grounded stage one gate candidates"
```

### Task 6: Prompt-First Stage 1 Workflow Orchestration

**Files:**
- Create: `cyberppt/phase1/workflow.py`
- Test: `tests/test_phase1_workflow.py`

**Interfaces:**
- Produces: `prepare_phase1_prompt(project: Path, gate: str, input_path: Path | None = None) -> dict[str, object]`, `generate_phase1_candidate(project: Path, gate: str, model: str | None = None, dry_run: bool = False) -> dict[str, object]`, `stage_phase1_candidate(project: Path, gate: str, recommendation: str, options: list[dict[str, object]], question: str | None = None) -> Path`, `get_phase1_status(project: Path) -> dict[str, object]`.
- Calls: `run_codex_text`, source/prompt/schema/grounding/rendering helpers, and `stage_analysis_artifact` only after blocking QA passes.

- [ ] **Step 1: Write failing workflow tests with a stub model**

```python
def test_generate_consumes_edited_prompt_without_overwriting_it(tmp_path: Path, monkeypatch) -> None:
    prepared = prepare_fixture_project(tmp_path)
    result = prepare_phase1_prompt(prepared.project, "source_analysis", prepared.source)
    prompt = Path(result["prompt"])
    prompt.write_text(prompt.read_text(encoding="utf-8") + "\n人工补充约束。\n", encoding="utf-8")
    monkeypatch.setattr(workflow, "run_codex_text", lambda **kwargs: VALID_SOURCE_ANALYSIS_JSON)
    generated = generate_phase1_candidate(prepared.project, "source_analysis", model="test-model")
    assert "人工补充约束" in prompt.read_text(encoding="utf-8")
    assert generated["prompt_sha256"] == sha256_file(prompt)


def test_model_failure_preserves_prompt_and_writes_resumable_run(tmp_path: Path, monkeypatch) -> None:
    prepared = prepare_fixture_project(tmp_path)
    prepare_phase1_prompt(prepared.project, "source_analysis", prepared.source)
    monkeypatch.setattr(workflow, "run_codex_text", Mock(side_effect=RuntimeError("SSL EOF")))
    with pytest.raises(RuntimeError, match="SSL EOF"):
        generate_phase1_candidate(prepared.project, "source_analysis")
    run = json.loads(phase1_paths(prepared.project, "source_analysis").run_manifest.read_text())
    assert run["status"] == "model_failed"
    assert run["resume_command"].startswith("python3 -m cyberppt phase1 generate")
```

Add tests for stale source hash, stale approved predecessor, parse failure, blocking grounding, successful candidate, and refusal to stage without a passing grounding report.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_workflow.py -q`

Expected: FAIL because workflow functions do not exist.

- [ ] **Step 3: Implement `prepare_phase1_prompt`**

For `source_analysis`, require `input_path`; build and persist the source bundle and prompt. For later gates, require all predecessors to be approved and current, infer approved artifact paths, and write a prompt containing their frozen contents. Record dependency hashes and `status=prompt_ready`.

- [ ] **Step 4: Implement `generate_phase1_candidate`**

Read the existing prompt without regenerating it, call the model, save raw output before parsing, parse strictly, run grounding, save QA, render a candidate only when parsing succeeds, and append ledger records. Use statuses `model_failed`, `parse_failed`, `grounding_failed`, or `candidate_ready`.

- [ ] **Step 5: Implement model-assisted staging and status**

`stage_phase1_candidate` must require `candidate_ready`, current dependency hashes, and `grounding_report.blocking == false`, then call:

```python
return stage_analysis_artifact(
    project,
    gate,
    candidate.read_text(encoding="utf-8"),
    recommendation,
    options,
    question,
)
```

It must add the phase1 run path and hashes to the pending confirmation record without changing existing required fields.

- [ ] **Step 6: Run tests**

Run: `python3 -m pytest tests/test_phase1_workflow.py tests/test_analysis_expression_gate.py -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add cyberppt/phase1/workflow.py tests/test_phase1_workflow.py
git commit -m "feat: orchestrate prompt first stage one generation"
```

### Task 7: Independent Model Critic

**Files:**
- Create: `cyberppt/phase1/critic.py`
- Modify: `cyberppt/phase1/workflow.py`
- Test: `tests/test_phase1_critic.py`

**Interfaces:**
- Produces: `build_critic_prompt(gate: str, candidate: str, grounding_report: dict[str, object], approved: dict[str, str]) -> str`, `parse_critic_output(text: str) -> dict[str, object]`, `critique_phase1_candidate(project: Path, gate: str, model: str | None = None) -> dict[str, object]`.

- [ ] **Step 1: Write failing critic tests**

```python
def test_critic_findings_do_not_rewrite_candidate(tmp_path: Path, monkeypatch) -> None:
    project, candidate = candidate_ready_project(tmp_path, "business_script")
    original = candidate.read_text(encoding="utf-8")
    monkeypatch.setattr(critic, "run_codex_text", lambda **kwargs: CRITIC_FINDINGS_JSON)
    report = critique_phase1_candidate(project, "business_script", model="critic-model")
    assert candidate.read_text(encoding="utf-8") == original
    assert report["findings"][0]["category"] == "duplicate_page"
```

Add tests for malformed critic JSON, unknown categories, model failure, and critic prompt persistence.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_critic.py -q`

Expected: FAIL because critic functions do not exist.

- [ ] **Step 3: Implement critic prompt and normalized findings**

Allow only these categories: `unsupported_claim`, `weak_evidence`, `duplicate_page`, `narrative_gap`, `vague_title`, `style_violation`, `density_mismatch`, `boundary_overstatement`. Require page/evidence references and a concise remediation for every finding.

- [ ] **Step 4: Persist critic artifacts without changing candidate or gate state**

Write prompt, raw output, normalized report, hashes, model, and ledger entries. Critic status may be `critic_ready`, `critic_parse_failed`, or `critic_model_failed`; it must not alter deterministic grounding status.

- [ ] **Step 5: Run tests**

Run: `python3 -m pytest tests/test_phase1_critic.py tests/test_phase1_workflow.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/phase1/critic.py cyberppt/phase1/workflow.py tests/test_phase1_critic.py
git commit -m "feat: add advisory stage one model critic"
```

### Task 8: Add The Nested `phase1` CLI

**Files:**
- Modify: `cyberppt/cli.py`
- Test: `tests/test_phase1_cli.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces CLI subcommands: `phase1 prepare`, `phase1 generate`, `phase1 critique`, `phase1 stage`, `phase1 status`.
- Calls the workflow interfaces from Tasks 6 and 7.

- [ ] **Step 1: Run GitNexus impact analysis for `build_parser`**

Review direct callers and CLI process flows. Stop and warn if risk is HIGH or CRITICAL.

- [ ] **Step 2: Write failing CLI tests**

```python
def test_phase1_prepare_routes_to_workflow(tmp_path: Path) -> None:
    with patch("cyberppt.cli.prepare_phase1_prompt", return_value={"status": "prompt_ready"}) as prepare:
        code = main([
            "phase1", "prepare", str(tmp_path),
            "--gate", "source_analysis",
            "--input", str(tmp_path / "source_extract.md"),
        ])
    assert code == 0
    prepare.assert_called_once_with(tmp_path, "source_analysis", tmp_path / "source_extract.md")


def test_phase1_generate_model_failure_returns_two(tmp_path: Path) -> None:
    with patch("cyberppt.cli.generate_phase1_candidate", side_effect=RuntimeError("model failed")):
        assert main(["phase1", "generate", str(tmp_path), "--gate", "source_analysis"]) == 2
```

- [ ] **Step 3: Run tests and verify failure**

Run: `python3 -m pytest tests/test_phase1_cli.py tests/test_cli.py -q`

Expected: FAIL because the nested parser is absent.

- [ ] **Step 4: Implement parser and command handlers**

Use `choices=GATE_ORDER`. `prepare --input` is required only for `source_analysis`; reject it for later gates. Parse `--options-json` as a JSON array using the same failure behavior as existing stage commands. Print machine-readable JSON for prepare, generate, critique, and status.

- [ ] **Step 5: Run CLI tests**

Run: `python3 -m pytest tests/test_phase1_cli.py tests/test_cli.py -q`

Expected: PASS and `python3 -m cyberppt phase1 --help` lists all five subcommands.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/cli.py tests/test_phase1_cli.py tests/test_cli.py
git commit -m "feat: expose stage one model workflow cli"
```

### Task 9: Strengthen Model-Assisted Gate Quality Without Breaking Manual Inputs

**Files:**
- Modify: `cyberppt/commands/analysis_expression_gate.py`
- Modify: `cyberppt/phase1/workflow.py`
- Test: `tests/test_analysis_expression_gate.py`
- Test: `tests/test_phase1_workflow.py`

**Interfaces:**
- Produces: optional `generation_run` provenance in pending confirmation records and model-assisted QA validation in `stage_phase1_candidate`.
- Preserves: direct hand-authored `stage_analysis_artifact(...)` behavior and existing project approvals.

- [ ] **Step 1: Run GitNexus impact analysis**

Run upstream impact for `validate_analysis_artifact` and `stage_analysis_artifact`. Review affected Stage 1, blueprint, final-script, and production tests before editing.

- [ ] **Step 2: Write failing compatibility and provenance tests**

```python
def test_manual_stage_remains_valid_without_generation_run(tmp_path: Path) -> None:
    project = initialized_project(tmp_path)
    pending = stage_analysis_artifact(project, "source_analysis", SOURCE_ANALYSIS, "complete", OPTIONS)
    assert "generation_run" not in json.loads(pending.read_text(encoding="utf-8"))


def test_model_assisted_stage_records_generation_run_hash(tmp_path: Path) -> None:
    project, run_path = candidate_ready_project(tmp_path, "source_analysis")
    pending = stage_phase1_candidate(project, "source_analysis", "complete", OPTIONS)
    data = json.loads(pending.read_text(encoding="utf-8"))
    assert data["generation_run"] == str(run_path)
    assert data["generation_run_sha256"] == sha256_file(run_path)


@pytest.mark.parametrize("module_count", [2, 3, 4, 6, 8])
def test_report_structure_allows_task_adaptive_module_counts(module_count: int) -> None:
    text = render_structure_with_modules(module_count)
    assert not any("module count" in error for error in validate_analysis_artifact("report_structure", text))


@pytest.mark.parametrize("module_count", [0, 1, 9])
def test_report_structure_rejects_unusable_module_counts(module_count: int) -> None:
    text = render_structure_with_modules(module_count)
    assert "report_structure module count must be between 2 and 8" in validate_analysis_artifact("report_structure", text)
```

- [ ] **Step 3: Run tests and verify failure**

Run: `python3 -m pytest tests/test_analysis_expression_gate.py tests/test_phase1_workflow.py -q`

Expected: FAIL for the new provenance behavior and task-adaptive module-count behavior.

- [ ] **Step 4: Add an optional provenance parameter**

Extend `stage_analysis_artifact` with a keyword-only optional argument:

```python
def stage_analysis_artifact(
    project: Path,
    gate: str,
    source: str,
    recommendation: str,
    options: list[dict[str, Any]],
    question: str | None = None,
    *,
    generation_run: Path | None = None,
) -> Path:
```

When provided, verify the run exists, gate matches, status is `candidate_ready`, dependency hashes are current, candidate hash matches `source`, and grounding is non-blocking. Then record run and hash in pending JSON. When omitted, preserve current behavior.

Also remove the fixed four-module heading requirement from `REQUIRED_HEADINGS["report_structure"]`. Replace the current 4-6 count check with a 2-8 operational bound, while retaining the prohibitions on page count, page title, and visual-form fields. Update the existing invalid-module-count test so nine modules fail and two, three, four, six, and eight modules pass.

- [ ] **Step 5: Run the full Stage 1 and downstream gate suite**

Run: `python3 -m pytest tests/test_analysis_expression_gate.py tests/test_phase1_workflow.py tests/test_final_script_pages.py tests/test_produce.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add cyberppt/commands/analysis_expression_gate.py cyberppt/phase1/workflow.py tests/test_analysis_expression_gate.py tests/test_phase1_workflow.py
git commit -m "feat: bind model provenance to stage one approvals"
```

### Task 10: Document The Workflow And Add End-To-End Fixtures

**Files:**
- Modify: `SKILL.md`
- Modify: `README.md`
- Modify: `docs/repository-layout.md`
- Create: `tests/fixtures/phase1/source_extract.md`
- Create: `tests/fixtures/phase1/source_analysis_response.json`
- Create: `tests/fixtures/phase1/reporting_direction_response.json`
- Create: `tests/fixtures/phase1/report_structure_response.json`
- Create: `tests/fixtures/phase1/page_design_response.json`
- Create: `tests/fixtures/phase1/business_script_response.json`
- Create: `tests/test_phase1_end_to_end.py`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Produces: documented operator workflow and a network-free fixture path through all five candidate-generation and approval gates.

- [ ] **Step 1: Write the failing end-to-end test**

```python
def test_phase1_five_gate_fixture_flow(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "project"
    init_project(project)
    responses = fixture_responses_by_gate()
    monkeypatch.setattr(workflow, "run_codex_text", lambda **kwargs: responses.pop(0))
    for gate in GATE_ORDER:
        input_path = FIXTURES / "source_extract.md" if gate == "source_analysis" else None
        prepare_phase1_prompt(project, gate, input_path)
        result = generate_phase1_candidate(project, gate, model="fixture-model")
        assert result["status"] == "candidate_ready"
        pending = stage_phase1_candidate(project, gate, result["recommendation"], result["options"])
        option_id = result["options"][0]["id"]
        approve_analysis_artifact(project, gate, option_id)
    assert get_analysis_expression_status(project).next_gate is None
```

- [ ] **Step 2: Run the test and verify failure**

Run: `python3 -m pytest tests/test_phase1_end_to_end.py -q`

Expected: FAIL until fixtures, documentation contract, and result recommendation/options are complete.

- [ ] **Step 3: Document exact pause points and commands**

Document this required sequence:

```bash
PROJECT=/Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709
SOURCE="$PROJECT/workbench/stages/01-analysis/source_extract.md"
OPTIONS_JSON='[{"id":"confirm_source_analysis","label":"确认证据分析"},{"id":"revise_source_analysis","label":"修改证据分析"}]'

python3 -m cyberppt phase1 prepare "$PROJECT" --gate source_analysis --input "$SOURCE"
# inspect/edit workbench/stages/01-analysis/model-runs/source_analysis/prompts/source_analysis_prompt.md
python3 -m cyberppt phase1 generate "$PROJECT" --gate source_analysis
# inspect candidate and deterministic QA
python3 -m cyberppt phase1 critique "$PROJECT" --gate source_analysis
python3 -m cyberppt phase1 stage "$PROJECT" --gate source_analysis --recommendation confirm_source_analysis --options-json "$OPTIONS_JSON"
python3 -m cyberppt approve-source-analysis "$PROJECT" --option-id confirm_source_analysis
```

State that the same prepare/generate/critique/stage/approve cycle repeats for each gate and that no model result is an approval.

- [ ] **Step 4: Add contract assertions**

Update `tests/test_skill_contract.py` to require `phase1 prepare`, reviewable prompt MD, deterministic grounding, critic advisory status, and explicit approval language in `SKILL.md`.

- [ ] **Step 5: Run focused and full tests**

Run:

```bash
python3 -m pytest tests/test_phase1_end_to_end.py tests/test_skill_contract.py -q
python3 -m pytest tests/test_phase1_*.py tests/test_analysis_expression_gate.py tests/test_cli.py tests/test_script_gate.py tests/test_speaker_notes.py tests/test_final_script_pages.py tests/test_produce.py -q
python3 -m cyberppt doctor
git diff --check
```

Expected: all tests pass, doctor reports required assets/commands available, and `git diff --check` is clean.

- [ ] **Step 6: Commit**

```bash
git add SKILL.md README.md docs/repository-layout.md tests/fixtures/phase1 tests/test_phase1_end_to_end.py tests/test_skill_contract.py
git commit -m "docs: define model assisted stage one workflow"
```

### Task 11: Shadow-Run The Current Power-Supply Project

**Files:**
- Create during acceptance only: `projects/power-supply-demand-forecast-0709/workbench/stages/01-analysis/model-runs/**`
- Do not modify: existing `workbench/analysis_expression/*.approved.json` or approved Markdown artifacts.

**Interfaces:**
- Consumes: current `source_extract.md`, approved Stage 1 artifacts, and the new CLI.
- Produces: side-by-side candidate, grounding, critic, and comparison artifacts without changing approval state.

- [ ] **Step 1: Prepare the source-analysis prompt**

Run:

```bash
python3 -m cyberppt phase1 prepare \
  /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 \
  --gate source_analysis \
  --input /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709/workbench/stages/01-analysis/source_extract.md
```

Expected: prompt, source bundle, run manifest, and ledger records are created; no model call occurs.

- [ ] **Step 2: Review the prompt before generation**

Verify it contains the current source hash, all three Stage 1 reference hashes, strict JSON schema, internal-reporting constraints, and source-unit locators. Make any desired edits directly in the prompt MD.

- [ ] **Step 3: Generate and critique the shadow candidate**

Run:

```bash
python3 -m cyberppt phase1 generate \
  /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 \
  --gate source_analysis
python3 -m cyberppt phase1 critique \
  /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 \
  --gate source_analysis
```

Expected: candidate and deterministic QA are written; critic findings do not modify the candidate.

- [ ] **Step 4: Compare without staging**

Compare the shadow candidate with the existing approved `workbench/analysis_expression/source_analysis.md` for evidence coverage, unsupported claims, title/task fit, story-line differentiation, and confirmation-question quality. Do not call `phase1 stage` during this acceptance task.

- [ ] **Step 5: Run final verification and GitNexus change detection**

Run:

```bash
python3 -m pytest tests/test_phase1_*.py tests/test_analysis_expression_gate.py tests/test_cli.py tests/test_speaker_notes.py tests/test_final_script_pages.py tests/test_produce.py -q
python3 -m cyberppt analysis-expression-status /Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-0709 --json
git diff --check
```

Expected: tests pass; the project remains fully approved; approved hashes are unchanged; only shadow-run and ledger artifacts are new or modified.

- [ ] **Step 6: Review before committing project artifacts**

Run GitNexus `detect_changes({scope: "all", repo: "CyberPPT"})`, inspect unrelated dirty-worktree deletions, and stage only implementation files plus explicitly approved shadow-run artifacts. Do not include unrelated project deletions.

## Plan Self-Review

- Spec coverage: prompt-first editing, five gates, grounding, critic, provenance, errors, compatibility, CLI, docs, and current-project acceptance are each assigned to a task.
- Scope: raw Office/PDF extraction and Stage 2 are explicitly excluded.
- Type consistency: `Phase1Paths`, `Phase1Run`, source bundle types, prompt/generation/staging interfaces, and artifact names are consistent across tasks.
- Placeholder scan: no `TBD`, `TODO`, deferred implementation instruction, or unnamed validation step remains.

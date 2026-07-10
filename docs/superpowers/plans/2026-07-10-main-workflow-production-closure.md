# Main Workflow Production Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project-scoped `cyberppt produce` state machine that consumes approved locks and images, assembles a verifiable image-based PPTX, runs render and strict QA, and writes `deliverable_ready` only after all gates pass.

**Architecture:** `cyberppt/commands/produce.py` owns production transitions and durable state; `blueprint_gate.py` owns speaker-notes approval; `template_image_ppt_export.py` consumes approved image, template-text, and notes manifests without regenerating assets; `production_qa.py` validates, renders, compares, and promotes delivery. Existing helper commands remain diagnostic surfaces but production-capable aliases require an explicit valid project.

**Tech Stack:** Python 3.11+, `argparse`, `dataclasses`, `hashlib`, `json`, `pathlib`, `subprocess`, `zipfile`, Pillow, LibreOffice/Poppler, `unittest`, GitNexus CLI/MCP.

## Global Constraints

- The default production mode remains `full_image_ppt`; content-region text is intentionally image-based.
- Never execute OCR, overlay, semantic-plan, source-capture, or template-rebuild from the main production path.
- Never infer project identity from arbitrary input paths; production-capable CLI aliases require explicit `--project`.
- Never infer title-layer truth from full images, OCR, filenames, or drawing-script headings in project production.
- Never approve speaker notes, blueprint images, or QA automatically.
- Never write `production_ready` or `deliverable_ready` from subprocess return code alone.
- All code-symbol edits require `gitnexus impact <symbol> --direction upstream --repo CyberPPT` before editing; stop and warn on HIGH or CRITICAL risk.
- Every commit requires `gitnexus detect-changes --scope staged --repo CyberPPT` and review of affected flows.
- Preserve unrelated dirty-worktree changes and keep generated test assets in temporary directories.

## File Structure

- Create `cyberppt/commands/produce.py`: production state machine, artifact discovery, transition checks, ledger writes, and CLI-facing orchestration functions.
- Create `cyberppt/commands/production_qa.py`: assembly-bundle validation, PPTX package checks, rendering, body-region comparison, strict validation, and readiness report.
- Create `tests/test_produce.py`: state-machine, assembly, verification, stale dependency, and CLI tests.
- Create `tests/test_production_qa.py`: real fixture-level assembly and QA validation tests.
- Modify `cyberppt/commands/blueprint_gate.py`: speaker-notes stage/approve/assert functions.
- Modify `cyberppt/commands/script_runner.py`: explicit-project enforcement for production-capable aliases.
- Modify `cyberppt/commands/final_script_pages.py`: preparation-only status and approved notes staging.
- Modify `cyberppt/cli.py`: `produce` subcommands and speaker-notes approval commands.
- Modify `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`: consume template lock and approved full-image manifest; reject project-production fallbacks.
- Modify `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`: retain module-import compatibility after exporter import cleanup.
- Modify `scripts/validate_pptx.py`: recognize the `full_image_ppt` delivery manifest without imposing legacy editable-overlay rules.
- Modify `tests/test_final_script_pages.py`, `tests/test_script_runner.py`, `tests/test_dual_image_overlay_template_rebuild.py`, and `tests/test_skill_contract.py`: regression expectations.
- Modify `SKILL.md`, `README.md`, and `docs/repository-layout.md`: one documented default mainline.

---

### Task 1: Require Explicit Project Context For Production Aliases

**Files:**
- Modify: `cyberppt/commands/script_runner.py:33-85`
- Modify: `cyberppt/cli.py:476-478`
- Test: `tests/test_script_runner.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `assert_analysis_expression_ready(project: Path) -> None`.
- Produces: `generation_project(args: list[str]) -> Path` and fail-closed `run_script(script_name: str, args: list[str]) -> int` behavior.

- [ ] **Step 1: Run symbol impact analysis**

Run:

```bash
gitnexus impact run_script --direction upstream --repo CyberPPT
gitnexus impact _assert_generation_alias_ready --direction upstream --repo CyberPPT
gitnexus impact build_parser --direction upstream --repo CyberPPT
```

Expected: review direct CLI callers and script-runner tests; stop before editing if risk is HIGH or CRITICAL.

- [ ] **Step 2: Write failing explicit-project tests**

Add tests equivalent to:

```python
def test_generation_alias_requires_explicit_project(self) -> None:
    with self.assertRaisesRegex(ValueError, "--project is required"):
        run_script("image-ppt", ["run", "--script", "outside.md", "-o", "new-output"])

def test_generation_alias_rejects_non_project_path(self) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        with self.assertRaisesRegex(ValueError, "CyberPPT project contract"):
            run_script("image-ppt", ["--project", tmp, "run", "--script", "outside.md", "-o", "out"])
```

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_script_runner tests.test_cli`

Expected: FAIL because path inference currently allows missing `--project` and aliases do not strip the project option before forwarding.

- [ ] **Step 4: Implement explicit project parsing**

Implement this contract in `script_runner.py`:

```python
def generation_project(args: list[str]) -> Path:
    values = _option_values(args, "--project")
    if len(values) != 1:
        raise ValueError("production-capable aliases require exactly one --project <path>")
    project = Path(values[0]).expanduser().resolve()
    contract = project / "workbench" / "analysis_expression" / "contract.json"
    if not contract.is_file():
        raise ValueError(f"CyberPPT project contract not found: {contract}")
    return project

def _assert_generation_alias_ready(script_name: str, args: list[str]) -> list[str]:
    if script_name not in _STAGE_2_PLUS_GENERATION_ALIASES:
        return args
    project = generation_project(args)
    assert_analysis_expression_ready(project)
    return _without_option(args, "--project")
```

Change `run_script` to execute the returned forwarded arguments. Keep direct files under `scripts/` untouched as the advanced/debug surface.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_script_runner tests.test_cli`

Expected: PASS.

- [ ] **Step 6: Detect changes and commit**

```bash
git add cyberppt/commands/script_runner.py cyberppt/cli.py tests/test_script_runner.py tests/test_cli.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "feat: require project context for production commands"
```

### Task 2: Add Speaker Notes Review And Approval

**Files:**
- Modify: `cyberppt/commands/blueprint_gate.py:20-360`
- Modify: `cyberppt/cli.py:216-414`
- Test: `tests/test_final_script_pages.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: approved business-script record and `speaker_notes_manifest.json`.
- Produces: `stage_speaker_notes_review(project: Path, manifest_path: Path, pages_raw: str) -> Path`, `approve_speaker_notes_review(project: Path, option_id: str, note: str = "") -> Path`, and `assert_speaker_notes_review_ready(project: Path, pages_raw: str) -> Path`.

- [ ] **Step 1: Run symbol impact analysis**

```bash
gitnexus impact stage_blueprint_image_review --direction upstream --repo CyberPPT
gitnexus impact approve_blueprint_image_review --direction upstream --repo CyberPPT
gitnexus impact _approved_business --direction upstream --repo CyberPPT
gitnexus impact build_parser --direction upstream --repo CyberPPT
```

Expected: MEDIUM or lower; review direct test and CLI callers.

- [ ] **Step 2: Write failing notes-gate tests**

Add tests equivalent to:

```python
pending = stage_speaker_notes_review(project, manifest, "1-3")
self.assertTrue(pending.is_file())
with self.assertRaisesRegex(ValueError, "speaker notes approval is required"):
    assert_speaker_notes_review_ready(project, "1-3")
approve_speaker_notes_review(project, "confirm_speaker_notes")
self.assertEqual(manifest.resolve(), assert_speaker_notes_review_ready(project, "1-3"))

manifest.write_text('{"notes": []}\n', encoding="utf-8")
with self.assertRaisesRegex(ValueError, "speaker notes changed"):
    assert_speaker_notes_review_ready(project, "1-3")
```

Also test that a changed business script and a different page range invalidate approval.

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_final_script_pages tests.test_cli`

Expected: ERROR importing undefined speaker-notes gate functions.

- [ ] **Step 4: Implement the gate records**

Use these paths and fields:

```python
speaker_notes_review.json
speaker_notes_review.pending-confirmation.json
speaker_notes_review.approved.json
```

The pending and approval payloads must include `manifest`, `manifest_sha256`, `business_script`, `business_script_sha256`, `pages_raw`, `option_id`, and timestamps. Accepted options are exactly `confirm_speaker_notes` and `revise_speaker_notes`; only the confirmation option produces `approved: true`.

- [ ] **Step 5: Add CLI commands**

Add:

```text
stage-speaker-notes-review <project> --manifest <path> --pages <range>
approve-speaker-notes-review <project> --option-id confirm_speaker_notes [--note ...]
```

The stage command prints the pending JSON path; the approve command prints the approval path.

- [ ] **Step 6: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_final_script_pages tests.test_cli`

Expected: PASS.

- [ ] **Step 7: Detect changes and commit**

```bash
git add cyberppt/commands/blueprint_gate.py cyberppt/cli.py tests/test_final_script_pages.py tests/test_cli.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "feat: require speaker notes approval"
```

### Task 3: Make Template Text Lock And Approved Images Real Exporter Inputs

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py:130-1064`
- Modify: `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py:1-30`
- Test: `tests/test_dual_image_rebuild_engine_assets.py`
- Test: `tests/test_dual_image_overlay_template_rebuild.py`

**Interfaces:**
- Consumes: `template_text_lock.json`, `page_image_pairs.json`, approved speaker-notes manifest, script body content.
- Produces: `load_template_text_lock(path: Path, pages: list[int]) -> dict[int, dict]`, `load_approved_full_images(path: Path, pages: list[int]) -> dict[int, Path]`, and extended `build_manifest(...) -> dict`.

- [ ] **Step 1: Run symbol impact analysis**

```bash
gitnexus impact build_manifest --direction upstream --repo CyberPPT
gitnexus impact extract_content --direction upstream --repo CyberPPT
gitnexus impact command_run --direction upstream --repo CyberPPT
gitnexus impact build_parser --direction upstream --repo CyberPPT
```

Expected: report all direct exporter, CLI, and legacy overlay callers; warn before proceeding if HIGH or CRITICAL.

- [ ] **Step 2: Write failing lock and approved-image tests**

Add fixture tests that assert:

```python
manifest = build_manifest(
    script_path=script,
    selected_pages=[1],
    output_dir=output,
    template_text_lock=template_lock,
    page_image_manifest=pair_manifest,
    speaker_notes_manifest=notes_manifest,
    project_production=True,
)
self.assertEqual("Locked title", manifest["tasks"][0]["title"])
self.assertEqual(str(full_image.resolve()), manifest["tasks"][0]["image_path"])
self.assertEqual("approved_speaker_notes", manifest["tasks"][0]["notes_source"])
```

Add negative cases for missing page lock, unapproved lock record, page-set mismatch, missing full image, and missing notes manifest. Add a regression test for `python3 -m scripts.dual_image_overlay.rebuild_engine.script_text_overlay --help`.

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_dual_image_rebuild_engine_assets tests.test_dual_image_overlay_template_rebuild`

Expected: FAIL because `build_manifest` lacks these inputs and module import currently raises `ModuleNotFoundError`.

- [ ] **Step 4: Implement project-production input loaders**

Use project-production validation equivalent to:

```python
if project_production:
    if template_text_lock is None:
        raise ValueError("metadata_required: --template-text-lock is required")
    if page_image_manifest is None:
        raise ValueError("approved page image manifest is required")
    if speaker_notes_manifest is None:
        raise ValueError("approved speaker notes manifest is required")
```

Map titles, subtitles, template switches, and variants from the lock. Map content-page image paths from each pair's `full.path`. Do not invoke image generation when approved images are supplied.

- [ ] **Step 5: Fix package/script import compatibility**

Replace the unconditional import with:

```python
try:
    from .codex_oauth_image import run_codex_image
except ImportError:
    from codex_oauth_image import run_codex_image
```

Retain direct-script help execution and package-module imports.

- [ ] **Step 6: Extend exporter CLI**

Add `--project-production`, `--template-text-lock`, and `--page-image-manifest` to `plan` and `run`. In project-production `run`, skip `command_generate`; write the project and export directly from approved images.

- [ ] **Step 7: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_dual_image_rebuild_engine_assets tests.test_dual_image_overlay_template_rebuild`

Expected: PASS, including module-help execution.

- [ ] **Step 8: Detect changes and commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py tests/test_dual_image_rebuild_engine_assets.py tests/test_dual_image_overlay_template_rebuild.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "feat: bind image export to approved inputs"
```

### Task 4: Add Produce Prepare And Status Transitions

**Files:**
- Create: `cyberppt/commands/produce.py`
- Create: `tests/test_produce.py`
- Modify: `cyberppt/cli.py:236-483`
- Modify: `cyberppt/commands/final_script_pages.py:424-617`

**Interfaces:**
- Consumes: approved blueprint input, approved visual style, analysis contract, page range.
- Produces: `prepare_production(project: Path, pages_raw: str) -> dict[str, Any]`, `get_production_status(project: Path, pages_raw: str) -> dict[str, Any]`, and `produce prepare|status` CLI commands.

- [ ] **Step 1: Run symbol impact analysis**

```bash
gitnexus impact run_final_script_pages --direction upstream --repo CyberPPT
gitnexus impact _run_speaker_notes_build --direction upstream --repo CyberPPT
gitnexus impact _append_ledger --direction upstream --repo CyberPPT
gitnexus impact build_parser --direction upstream --repo CyberPPT
```

Expected: review the final-script-pages flow and all affected tests before editing.

- [ ] **Step 2: Write failing prepare/status tests**

Test the desired API:

```python
summary = prepare_production(project, "1-3")
self.assertEqual("production_inputs_prepared", summary["status"])
self.assertTrue(Path(summary["artifacts"]["template_text_lock"]).is_file())
self.assertTrue(Path(summary["artifacts"]["speaker_notes_pending_confirmation"]).is_file())
self.assertEqual("speaker_notes_approval_required", get_production_status(project, "1-3")["next_gate"])
```

Also assert that `final-script-pages --production-build` is rejected with a recovery message pointing to `produce assemble`, and that its preparation status is never `production_ready`.

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_produce tests.test_final_script_pages tests.test_cli`

Expected: FAIL because `produce.py` and produce CLI commands do not exist.

- [ ] **Step 4: Implement preparation and calculated status**

`prepare_production` must read the approved blueprint artifact path from `blueprint_input.approved.json`, call `run_final_script_pages(..., production_build=False)`, stage the resulting notes manifest through Task 2, and write `production_prepare.json` under the page-range Stage 02 directory.

`get_production_status` must calculate, in order:

```python
GATES = (
    "analysis_approved",
    "visual_style_approved",
    "blueprint_input_approved",
    "production_inputs_prepared",
    "speaker_notes_approved",
    "blueprint_images_approved",
    "image_ppt_assembled",
    "render_qa_passed",
    "strict_qa_passed",
    "deliverable_ready",
)
```

Return `status`, `next_gate`, `next_command`, validation failures, and current artifact paths. Recompute hashes on every call.

- [ ] **Step 5: Add CLI parser and handlers**

Add:

```text
produce prepare <project> --pages <range>
produce status <project> --pages <range> [--json]
```

- [ ] **Step 6: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_produce tests.test_final_script_pages tests.test_cli`

Expected: PASS.

- [ ] **Step 7: Detect changes and commit**

```bash
git add cyberppt/commands/produce.py cyberppt/commands/final_script_pages.py cyberppt/cli.py tests/test_produce.py tests/test_final_script_pages.py tests/test_cli.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "feat: add production preparation state machine"
```

### Task 5: Add Fail-Closed Assembly

**Files:**
- Modify: `cyberppt/commands/produce.py`
- Create: `cyberppt/commands/production_qa.py`
- Modify: `tests/test_produce.py`
- Create: `tests/test_production_qa.py`

**Interfaces:**
- Consumes: current preparation summary, approved notes manifest, approved image manifest, template lock, style lock.
- Produces: `assemble_production(project: Path, pages_raw: str) -> dict[str, Any]` and `validate_assembly_bundle(bundle: dict[str, Any], expected_pages: list[int]) -> dict[str, Any]`.

- [ ] **Step 1: Run symbol impact analysis**

```bash
gitnexus impact _run_image_ppt_build --direction upstream --repo CyberPPT
gitnexus impact _image_ppt_artifacts --direction upstream --repo CyberPPT
gitnexus impact run_export --direction upstream --repo CyberPPT
```

Expected: inspect direct production-build and exporter callers; warn on HIGH or CRITICAL.

- [ ] **Step 2: Write failing assembly tests**

Cover the false-success case:

```python
with patch("cyberppt.commands.produce.subprocess.run", return_value=Mock(returncode=0)):
    with self.assertRaisesRegex(RuntimeError, "assembly_artifact_missing"):
        assemble_production(project, "1")
```

Add a fixture that creates a non-empty PPTX ZIP with expected slide and notes parts and assert `image_ppt_assembled`. Add failures for page mismatch, missing approved image, stale image hash, missing notes part, output outside project, and unreadable PPTX ZIP.

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_produce tests.test_production_qa`

Expected: FAIL because assembly functions do not exist.

- [ ] **Step 4: Implement assembly command construction**

Call the exporter with all truth inputs:

```text
python3 -m cyberppt image-ppt --project <project> run
  --project-production
  --script <approved-blueprint-input>
  --pages <range>
  --template-text-lock <lock>
  --page-image-manifest <approved-pairs>
  --speaker-notes-manifest <approved-notes>
  --output-dir <project-stage-output>
  --name <page-range>
```

Do not pass `--force`; production assembly must not regenerate images.

- [ ] **Step 5: Implement assembly bundle validation**

Use `zipfile.ZipFile` and manifest JSON to require a readable, non-empty PPTX, exact slide count, exact page set, notes-part count, current full-image hashes, complete lock and notes coverage, and project-contained output paths. Write `assembly_report.json` with `valid`, `checks`, `artifacts`, and `failures`.

- [ ] **Step 6: Add `produce assemble` CLI**

The command requires both `assert_speaker_notes_review_ready` and `assert_blueprint_image_review_ready` before launching the exporter. On success it writes `image_ppt_assembled`; it never writes a delivery state.

- [ ] **Step 7: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_produce tests.test_production_qa`

Expected: PASS.

- [ ] **Step 8: Detect changes and commit**

```bash
git add cyberppt/commands/produce.py cyberppt/commands/production_qa.py tests/test_produce.py tests/test_production_qa.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "feat: validate image ppt assembly artifacts"
```

### Task 6: Add Render, Visual, Strict, And Delivery Gates

**Files:**
- Modify: `cyberppt/commands/production_qa.py`
- Modify: `cyberppt/commands/produce.py`
- Modify: `cyberppt/cli.py`
- Modify: `scripts/validate_pptx.py:341-480,2014-2175`
- Modify: `tests/test_production_qa.py`
- Modify: `tests/test_produce.py`

**Interfaces:**
- Consumes: valid assembly report, approved full images, template-image manifest, template lock.
- Produces: `verify_production(project: Path, pages_raw: str) -> dict[str, Any]`, `render_and_compare(...) -> dict[str, Any]`, and `produce verify`.

- [ ] **Step 1: Run symbol impact analysis**

```bash
gitnexus impact validate_pptx --direction upstream --repo CyberPPT
gitnexus impact render_to_png --direction upstream --repo CyberPPT
gitnexus impact validate_manifest --direction upstream --repo CyberPPT
gitnexus impact build_parser --direction upstream --repo CyberPPT
```

Expected: likely MEDIUM/HIGH because validator is shared; if HIGH, report the blast radius and proceed only after reviewing d=1 callers and affected validation flows.

- [ ] **Step 2: Write failing verification tests**

Add tests for:

```python
with patch("cyberppt.commands.production_qa.render_to_png", return_value=[]):
    with self.assertRaisesRegex(RuntimeError, "render_tool_unavailable"):
        verify_production(project, "1")

report = verify_production(project, "1")
self.assertEqual("deliverable_ready", report["status"])
self.assertTrue(Path(report["delivery_pptx"]).is_file())
```

Fixture tests must cover body-region comparison above tolerance, strict validator errors, missing native title text, missing notes, page count mismatch, and stale assembly hash.

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_production_qa tests.test_produce`

Expected: FAIL because verification and full-image manifest handling are absent.

- [ ] **Step 4: Implement full-image QA bundle**

Render through `scripts.dual_image_overlay.qa_render_page.render_to_png`. Empty output is blocking. For each content page, crop the manifest body region from the render, resize the approved full image to the crop size, and compute mean absolute RGB difference with Pillow. Record `mean_abs_diff`, `threshold`, `passed`, input hashes, and evidence paths. Use `12.0` as the initial default threshold and keep it explicit in the report.

- [ ] **Step 5: Add mode-specific strict manifest handling**

Recognize:

```json
{
  "schema": "cyberppt.full_image_delivery_manifest.v1",
  "delivery_mode": "full_image_ppt",
  "body_content_editable": false,
  "template_text_editable": true,
  "speaker_notes_required": true
}
```

In this mode, strict validation must not apply legacy editable-overlay requirements to body content. It must require native template title/chrome, expected slide dimensions and count, non-empty speaker notes, referenced full-image assets, and a passed production visual report.

- [ ] **Step 6: Implement promotion to delivery**

Write the QA bundle under `workbench/stages/05-qa-delivery/<range>/`. Copy the assembled PPTX to `delivery/<project-name>_<range>.pptx` only when assembly, render comparison, template checks, notes checks, and strict validation all pass. Register the dependency chain and SHA-256 in `artifact-ledger.json`.

- [ ] **Step 7: Add `produce verify` CLI and status integration**

`produce verify` prints the readiness report path and delivery PPTX. `produce status --json` must report `deliverable_ready` only while all recorded hashes remain current.

- [ ] **Step 8: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_production_qa tests.test_produce tests.test_cli`

Expected: PASS.

- [ ] **Step 9: Detect changes and commit**

```bash
git add cyberppt/commands/production_qa.py cyberppt/commands/produce.py cyberppt/cli.py scripts/validate_pptx.py tests/test_production_qa.py tests/test_produce.py tests/test_cli.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "feat: gate delivery on render and strict qa"
```

### Task 7: Align Contracts And Remove Mainline Ambiguity

**Files:**
- Modify: `SKILL.md:10-82,215-340,1022-1154`
- Modify: `README.md:10-26,41-63,86-125`
- Modify: `docs/repository-layout.md:37-80`
- Modify: `cyberppt/commands/init_project.py:14-109`
- Modify: `tests/test_skill_contract.py`
- Modify: `tests/test_script_gate.py`

**Interfaces:**
- Consumes: implemented `produce` commands and current project layout.
- Produces: one documented `full_image_ppt` mainline and matching new-project README/manifest contract.

- [ ] **Step 1: Run symbol impact analysis for scaffold code**

```bash
gitnexus impact _project_manifest --direction upstream --repo CyberPPT
gitnexus impact init_project --direction upstream --repo CyberPPT
```

Expected: review scaffold tests and project initialization flow.

- [ ] **Step 2: Write failing contract tests**

Assert that the canonical documents and generated project README contain `produce prepare`, `produce assemble`, and `produce verify`; assert that default sections do not claim `dual_image_editable_overlay`, full/background pairs, no-text backgrounds, or editable body content.

Use exact assertions:

```python
self.assertIn("python3 -m cyberppt produce prepare", skill)
self.assertNotIn("第三阶段默认使用 `dual_image_editable_overlay`", readme)
self.assertNotIn("full/background pair manifests", layout)
```

- [ ] **Step 3: Run tests and verify RED**

Run: `python3 -m unittest tests.test_skill_contract tests.test_script_gate`

Expected: FAIL on stale README/layout/mainline wording.

- [ ] **Step 4: Rewrite the default contract sections**

Keep the first-stage internal-reporting contract and move editable-overlay rules under one clearly marked `Legacy/Advanced: editable rebuild` section. Document the exact state sequence, human stop points, lower-level debug boundary, mode-specific editability, and delivery criteria.

Rename new Stage 02 scaffold directory metadata from the misleading semantic role to `stage_full_image_ppt` while preserving the physical `02-blueprint-dual-image` path for backward compatibility. State explicitly that the path name is historical.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `python3 -m unittest tests.test_skill_contract tests.test_script_gate`

Expected: PASS.

- [ ] **Step 6: Detect changes and commit**

```bash
git add SKILL.md README.md docs/repository-layout.md cyberppt/commands/init_project.py tests/test_skill_contract.py tests/test_script_gate.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "docs: align contracts with image ppt production"
```

### Task 8: Full Regression, Test Isolation, And Final Change Review

**Files:**
- Modify: `tests/test_dual_image_rebuild_engine_assets.py` if exporter tests write outside their temporary directory.
- Modify: `tests/test_production_qa.py` if production fixtures write outside their temporary directory.
- Test: all files under `tests/`.

**Interfaces:**
- Consumes: all prior task commits.
- Produces: a clean, reproducible full test run and GitNexus scope report.

- [ ] **Step 1: Run focused mainline verification**

```bash
python3 -m cyberppt doctor
python3 -m unittest tests.test_cli tests.test_analysis_expression_gate tests.test_final_script_pages tests.test_script_gate tests.test_script_runner tests.test_produce tests.test_production_qa tests.test_skill_contract tests.test_speaker_notes tests.test_dual_image_rebuild_engine_assets
```

Expected: PASS with no warnings or tracked-worktree changes.

- [ ] **Step 2: Run the complete test suite**

Run: `python3 -m unittest discover -s tests -p 'test*.py'`

Expected: all tests PASS, including `test_script_text_overlay_supports_module_help_execution`.

- [ ] **Step 3: Verify test isolation**

Capture `git status --short` before and after the full suite. Expected: no new or modified tracked files and no generated files outside temporary directories. If the suite changes a tracked project template, identify the responsible test, rewrite it to use `TemporaryDirectory`, rerun that test RED/GREEN, then rerun the suite.

- [ ] **Step 4: Exercise a temporary end-to-end production fixture**

Create a project under `TemporaryDirectory`, stage and approve all analysis, style, blueprint, notes, and image gates, then run `produce assemble` and `produce verify` using deterministic fixture images. Expected artifacts:

```text
workbench/stages/02-blueprint-dual-image/<range>/assembly_report.json
workbench/stages/05-qa-delivery/<range>/production_readiness.json
delivery/<project>_<range>.pptx
```

Expected final status: `deliverable_ready`.

- [ ] **Step 5: Review complete change scope**

```bash
gitnexus detect-changes --scope compare --base-ref bba74ae8 --repo CyberPPT
git diff --check bba74ae8..HEAD
git status --short
```

Expected: only intended production-flow symbols, tests, and contracts are affected; no unrelated project artifacts are staged.

- [ ] **Step 6: Commit any final test-isolation corrections**

If Task 8 changed either isolation test, run exactly:

```bash
git add tests/test_dual_image_rebuild_engine_assets.py tests/test_production_qa.py
gitnexus detect-changes --scope staged --repo CyberPPT
git commit -m "test: isolate production workflow fixtures"
```

If neither file changed, verify `git diff --exit-code -- tests/test_dual_image_rebuild_engine_assets.py tests/test_production_qa.py` and skip the commit.

# Editable-Text Three-Image Production Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an opt-in CyberPPT production branch that converts three approved page images into a template-based PPTX with editable body text.

**Architecture:** Keep the current Stage 1, blueprint, speaker-notes, and delivery gates. Add a compact adapter over the vendored three-image pipeline that writes project-local batch jobs and consumes passed `page.json` output. Extend the template exporter with an editable-body input that places BACKGROUND in the body region and writes one native textbox per vendor line; the existing full-image path is unchanged.

**Tech Stack:** Python 3, python-pptx, Pillow, JSON manifests, existing CyberPPT CLI/state machine, vendored three-image Python and Node scripts.

## Global Constraints

- `full_image_ppt` remains the default production mode and its CLI behavior must not change.
- `editable_text_three_image` requires matching FULL, BACKGROUND, and TEXT images for every selected content-image page.
- Vendor `page.json` and `qa.json` own body text and coordinates; OCR never supplies template title/subtitle text.
- Only vendor `passed` pages enter assembly. `review` is a human approval stop; `failed` blocks that page without discarding other batch results.
- Image dimensions must match and coordinate conversion maps source canvas into the template body region without distortion.
- All artifacts must be project-local and ledgered with status, hashes, dependencies, and resume command.
- Before editing a symbol, run GitNexus upstream impact; before every commit, run GitNexus detect-changes.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `cyberppt/commands/editable_text_three_image.py` | Build vendor batch manifest, execute it, validate page artifacts, and record approvals. |
| `cyberppt/commands/produce.py` | Select mode, drive editable-text transitions, and maintain freshness/delivery truth. |
| `cyberppt/cli.py` | Expose the explicit editable-text production transition. |
| `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py` | Render BACKGROUND plus one native text box per vendor line in template body region. |
| `tests/test_editable_text_three_image.py` | Adapter, page isolation, review gate, and stale-input tests. |
| `tests/test_produce.py` | CLI/state-machine/default-compatibility tests. |
| `tests/test_dual_image_overlay_template_rebuild.py` | Exporter-level editable body object tests. |
| `SKILL.md`, `docs/repository-layout.md` | Optional-flow contract and artifact documentation. |

### Task 1: Add the mode contract and deterministic vendor job manifest

**Files:**

- Create: `cyberppt/commands/editable_text_three_image.py`
- Create: `tests/test_editable_text_three_image.py`
- Modify: `cyberppt/commands/init_project.py:41-84`
- Test: `tests/test_cli.py`

**Interfaces:**

- Consumes: `project: Path`, `pages_raw: str`, and the prepared `page_image_pairs.json`.
- Produces: `get_production_mode(project: Path) -> str` and `build_three_image_batch(project: Path, pages_raw: str, pairs_path: Path) -> dict[str, object]`.

- [ ] **Step 1: Write failing tests**

```python
def test_default_production_mode_is_full_image_ppt(tmp_path: Path) -> None:
    project = tmp_path / "project"
    init_project(project)
    assert get_production_mode(project) == "full_image_ppt"

def test_three_image_batch_requires_full_background_and_text(tmp_path: Path) -> None:
    pairs = tmp_path / "page_image_pairs.json"
    pairs.write_text(json.dumps({"pairs": [{"page_number": 4, "full": {"path": "full.png"}}]}), encoding="utf-8")
    with pytest.raises(ValueError, match="BACKGROUND.*TEXT"):
        build_three_image_batch(tmp_path, "4", pairs)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_editable_text_three_image.py -q`

Expected: FAIL because the adapter module and mode contract do not exist.

- [ ] **Step 3: Implement the minimal contract**

```python
FULL_IMAGE_MODE = "full_image_ppt"
EDITABLE_TEXT_MODE = "editable_text_three_image"

def get_production_mode(project: Path) -> str:
    mode = str(_load_project_manifest(project).get("production_mode", FULL_IMAGE_MODE))
    if mode not in {FULL_IMAGE_MODE, EDITABLE_TEXT_MODE}:
        raise ValueError(f"unsupported production_mode: {mode}")
    return mode

def build_three_image_batch(project: Path, pages_raw: str, pairs_path: Path) -> dict[str, object]:
    return {"schema": "cyberppt.editable_text_batch.v1", "input_mode": "three-image",
            "pages": [_three_image_job(project, pair) for pair in _load_pairs(pairs_path, _parse_pages(pages_raw))]}
```

Add `production_mode: full_image_ppt` to a new project manifest. `_three_image_job` resolves and hashes FULL/BACKGROUND/TEXT inputs, requires readable same-size images, supplies OCR/registration paths, and places output in `workbench/stages/02-blueprint-dual-image/<pages>/editable_text/page_<n>/`.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_editable_text_three_image.py tests/test_cli.py -q`

Expected: PASS; defaults are unchanged and incomplete assets are rejected.

- [ ] **Step 5: Commit**

Run: `mcp__gitnexus__detect_changes({repo: "CyberPPT", scope: "all"})`

```bash
git add cyberppt/commands/editable_text_three_image.py cyberppt/commands/init_project.py tests/test_editable_text_three_image.py tests/test_cli.py
git commit -m "feat: add editable text three-image contract"
```

### Task 2: Run vendor batches and enforce page-level review/approval

**Files:**

- Modify: `cyberppt/commands/editable_text_three_image.py`
- Modify: `tests/test_editable_text_three_image.py`

**Interfaces:**

- Consumes: Task 1 batch manifest and `vendor/three-image-to-ppt/scripts/run_pipeline.py --mode batch --manifest`.
- Produces: `run_three_image_batch(project: Path, pages_raw: str) -> dict[str, object]`, `stage_editable_text_review(project: Path, pages_raw: str) -> Path`, `approve_editable_text_review(project: Path, pages_raw: str) -> Path`, and `assert_editable_text_batch_ready(project: Path, pages_raw: str) -> Path`.

- [ ] **Step 1: Write failing page-isolation tests**

```python
def test_review_result_requires_approval(project: Path, monkeypatch) -> None:
    monkeypatch.setattr(adapter.subprocess, "run", fake_vendor_review_run)
    assert run_three_image_batch(project, "4")["status"] == "review_required"
    with pytest.raises(ValueError, match="editable-text review approval"):
        assert_editable_text_batch_ready(project, "4")

def test_failed_page_preserves_other_results(project: Path, monkeypatch) -> None:
    monkeypatch.setattr(adapter.subprocess, "run", fake_vendor_mixed_run)
    pages = run_three_image_batch(project, "4-5")["pages"]
    assert pages["4"]["status"] == "failed"
    assert pages["5"]["status"] == "passed"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m pytest tests/test_editable_text_three_image.py -q`

Expected: FAIL because vendor results are not collected and approval records do not exist.

- [ ] **Step 3: Implement the result collector**

```python
def run_three_image_batch(project: Path, pages_raw: str) -> dict[str, object]:
    batch = build_three_image_batch(project, pages_raw, _prepared_pairs(project, pages_raw))
    manifest_path = _write_batch_manifest(project, pages_raw, batch)
    completed = subprocess.run([sys.executable, str(VENDOR_RUNNER), "--mode", "batch", "--manifest", str(manifest_path)], check=False)
    return _collect_vendor_results(project, pages_raw, batch, completed.returncode)

def assert_editable_text_batch_ready(project: Path, pages_raw: str) -> Path:
    result_path = _result_path(project, pages_raw)
    result = _read_json(result_path)
    if result["status"] == "review_required" and not _approval_is_current(project, pages_raw, result_path):
        raise ValueError("editable-text review approval is required")
    if result["status"] != "passed":
        raise ValueError("editable-text batch has failed pages")
    return result_path
```

Require each job to provide readable `page.json`, `qa.json`, and a review render. Record their hashes plus image/OCR/registration dependencies in both result manifest and ledger. Approval pins the result-manifest hash; changed inputs invalidate it.

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/test_editable_text_three_image.py -q`

Expected: PASS; passed/review/failed behavior is deterministic and recoverable.

- [ ] **Step 5: Commit**

Run: `mcp__gitnexus__detect_changes({repo: "CyberPPT", scope: "all"})`

```bash
git add cyberppt/commands/editable_text_three_image.py tests/test_editable_text_three_image.py
git commit -m "feat: gate three-image editable text batches"
```

### Task 3: Render editable body lines inside the existing template exporter

**Files:**

- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py:835-1000,1309-1409`
- Modify: `tests/test_dual_image_overlay_template_rebuild.py`

**Interfaces:**

- Consumes: passed result manifest page records containing `background_path`, `page_json_path`, and source canvas dimensions.
- Produces: `load_editable_body_pages(result_manifest: Path, pages: list[int]) -> dict[int, dict]` and `add_editable_body(slide, page: dict, body_region: dict, canvas: dict) -> None`.

- [ ] **Step 1: Run mandatory upstream impact**

Run: `mcp__gitnexus__impact({repo: "CyberPPT", target: "run_export", file_path: "scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py", direction: "upstream", minConfidence: 0.8, maxDepth: 3})`

Expected: Review direct callers/processes; report and resolve HIGH or CRITICAL risk before editing.

- [ ] **Step 2: Write the failing exporter test**

```python
def test_editable_body_uses_background_and_one_named_shape_per_line(tmp_path: Path) -> None:
    manifest = write_passed_editable_result(tmp_path, page=4, lines=["第一行", "第二行"])
    output = module.export_project_with_editable_body(manifest)
    shapes = inspect_slide_shapes(output, 1)
    assert shape_named(shapes, "text-4-T01-L01").text == "第一行"
    assert shape_named(shapes, "text-4-T01-L02").text == "第二行"
    assert image_shape_source(shapes) == manifest.parent / "background.png"
```

- [ ] **Step 3: Run the focused test to verify it fails**

Run: `python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py -k editable_body -q`

Expected: FAIL because only the full-image manifest is accepted.

- [ ] **Step 4: Implement template-native body rendering**

```python
def add_editable_body(slide, page: dict, body_region: dict, canvas: dict) -> None:
    slide.shapes.add_picture(str(page["background_path"]), body_region["x"], body_region["y"], body_region["width"], body_region["height"])
    for line in page["text_lines"]:
        left, top, width, height = _map_canvas_bbox_to_body(line["target"]["bbox_px"], canvas, body_region)
        shape = slide.shapes.add_textbox(left, top, width, height)
        shape.name = f"text-{page['page_id']}-{line['line_id']}"
        _configure_editable_line(shape, line)
```

Implement `_configure_editable_line` with Microsoft YaHei, zero margins, no wrap/autofit, exact text, alignment, and rotation. Reject CR/LF, absent target bbox, or a line whose geometry is outside the body canvas. Add `--editable-body-manifest`; reject use with `--page-image-manifest`.

- [ ] **Step 5: Run exporter regression tests**

Run: `python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_template_body_region.py -q`

Expected: PASS; full-image behavior remains unchanged and editable text has stable object names.

- [ ] **Step 6: Commit**

Run: `mcp__gitnexus__detect_changes({repo: "CyberPPT", scope: "all"})`

```bash
git add scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py tests/test_dual_image_overlay_template_rebuild.py
git commit -m "feat: render editable three-image bodies in templates"
```

### Task 4: Add explicit production state-machine and CLI transitions

**Files:**

- Modify: `cyberppt/commands/produce.py:223-735`
- Modify: `cyberppt/cli.py:356-719`
- Modify: `tests/test_produce.py`
- Modify: `tests/test_cli.py`

**Interfaces:**

- Consumes: Task 1 mode lookup, Task 2 vendor-gate APIs, and Task 3 exporter argument.
- Produces: `prepare_editable_text_production(project: Path, pages_raw: str) -> dict[str, object]` and a mode-aware `assemble_production(project: Path, pages_raw: str) -> dict[str, object]`.

- [ ] **Step 1: Run mandatory upstream impact**

Run: `mcp__gitnexus__impact({repo: "CyberPPT", target: "assemble_production", file_path: "cyberppt/commands/produce.py", direction: "upstream", minConfidence: 0.8, maxDepth: 3})`

Expected: Report direct callers, affected production processes, and HIGH/CRITICAL risk before editing.

- [ ] **Step 2: Write failing state-machine tests**

```python
def test_editable_mode_requires_vendor_review_before_assembly(project: Path) -> None:
    set_production_mode(project, "editable_text_three_image")
    prepare_production(project, "1")
    approve_speaker_notes_review(project, "1", "confirm_speaker_notes")
    assert get_production_status(project, "1")["next_gate"] == "editable_text_assets_required"
    with pytest.raises(ValueError, match="editable-text"):
        assemble_production(project, "1")

def test_default_mode_still_assembles_full_image(project: Path) -> None:
    assert get_production_mode(project) == "full_image_ppt"
    assert assemble_production(project, "1")["status"] == "image_ppt_assembled"
```

- [ ] **Step 3: Run focused tests to verify they fail**

Run: `python3 -m pytest tests/test_produce.py -k 'editable_mode or default_mode' -q`

Expected: FAIL because the state machine has no editable-text transition.

- [ ] **Step 4: Implement the transitions**

```python
if get_production_mode(root) == EDITABLE_TEXT_MODE:
    result.update(status="speaker_notes_approved", next_gate="editable_text_assets_required",
                  next_command=f"produce editable-text {root} --pages {pages_raw}")
    return result
```

Add `produce editable-text <project> --pages <range>` to run Task 2 and stage its review. Mode-aware `assemble_production` requires its current approved result and invokes `image-ppt run --editable-body-manifest <result>`. Its assembly report records result manifest, page JSONs, backgrounds, full references, and exported PPTX. Preserve the current command vector for default mode.

- [ ] **Step 5: Run production/CLI tests**

Run: `python3 -m pytest tests/test_produce.py tests/test_cli.py -q`

Expected: PASS; the new path is explicit and existing full-image callers are unchanged.

- [ ] **Step 6: Commit**

Run: `mcp__gitnexus__detect_changes({repo: "CyberPPT", scope: "all"})`

```bash
git add cyberppt/commands/produce.py cyberppt/cli.py tests/test_produce.py tests/test_cli.py
git commit -m "feat: add editable text production branch"
```

### Task 5: Make verification, delivery truth, and documentation mode-aware

**Files:**

- Modify: `cyberppt/commands/produce.py:485-735`
- Modify: `tests/test_produce.py`
- Modify: `SKILL.md`
- Modify: `docs/repository-layout.md`
- Test: `tests/test_skill_contract.py`

**Interfaces:**

- Consumes: Task 4 assembly reports and Task 2 result manifests.
- Produces: `editable_text_three_image` delivery manifest with `body_content_editable: true`, mode-aware freshness dependencies, and a normal `deliverable_ready` record.

- [ ] **Step 1: Run mandatory upstream impact**

Run: `mcp__gitnexus__impact({repo: "CyberPPT", target: "verify_production", file_path: "cyberppt/commands/produce.py", direction: "upstream", minConfidence: 0.8, maxDepth: 3})`

Expected: Review affected verification/delivery processes before editing.

- [ ] **Step 2: Write failing delivery tests**

```python
def test_editable_delivery_manifest_records_native_body_text(project: Path) -> None:
    finish_editable_text_assembly(project, "1")
    result = verify_production(project, "1")
    manifest = json.loads(Path(result["artifacts"]["editable_text_delivery_manifest"]).read_text())
    assert manifest["delivery_mode"] == "editable_text_three_image"
    assert manifest["body_content_editable"] is True
    assert manifest["slides"][0]["image_assets"][0]["role"] == "approved_background"

def test_changed_page_json_invalidates_editable_delivery(project: Path) -> None:
    finish_editable_text_assembly(project, "1")
    verify_production(project, "1")
    page_json = editable_page_json(project, 1)
    page_json.write_text(page_json.read_text() + "\n", encoding="utf-8")
    assert get_production_status(project, "1")["status"] != "deliverable_ready"
```

- [ ] **Step 3: Run focused tests to verify they fail**

Run: `python3 -m pytest tests/test_produce.py -k editable_delivery -q`

Expected: FAIL because verification only produces a full-image delivery manifest.

- [ ] **Step 4: Implement delivery branching**

```python
def _delivery_manifest_for_mode(mode: str, **kwargs: object) -> dict[str, object]:
    if mode == EDITABLE_TEXT_MODE:
        return _editable_text_delivery_manifest(**kwargs)
    return _full_image_delivery_manifest(**kwargs)
```

The editable manifest records approved BACKGROUND, FULL visual reference, TEXT OCR source, page JSON, vendor QA, and native editable line count. Add all of them to readiness dependency hashes. Preserve visual comparison against FULL and strict-PPTX validation, but set `body_content_editable: true`.

- [ ] **Step 5: Update canonical docs and test contract text**

Document the opt-in `editable_text_three_image` branch, vendor `review` stop, no OCR-derived template text, and artifacts in `SKILL.md` and `docs/repository-layout.md`. Extend `tests/test_skill_contract.py` only for exact new contract wording.

- [ ] **Step 6: Run the complete relevant suite**

Run: `python3 -m pytest tests/test_editable_text_three_image.py tests/test_produce.py tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_template_body_region.py tests/test_cli.py tests/test_skill_contract.py -q`

Expected: PASS with unchanged default full-image behavior.

- [ ] **Step 7: Commit**

Run: `mcp__gitnexus__detect_changes({repo: "CyberPPT", scope: "all"})`

```bash
git add cyberppt/commands/produce.py tests/test_produce.py SKILL.md docs/repository-layout.md tests/test_skill_contract.py
git commit -m "feat: verify editable three-image deliveries"
```

## Final Acceptance

- [ ] Run `python3 -m cyberppt --help` and confirm `produce editable-text` is listed.
- [ ] Run the complete suite in Task 5, Step 6.
- [ ] Run `mcp__gitnexus__detect_changes({repo: "CyberPPT", scope: "all"})` and verify only expected symbols/processes changed.
- [ ] Run `git status --short` and leave all unrelated pre-existing changes untouched.

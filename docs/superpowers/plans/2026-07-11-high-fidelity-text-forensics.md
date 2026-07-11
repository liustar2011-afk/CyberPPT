# High-Fidelity Text Forensics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repository-contained, single-image high-fidelity text information extractor that returns per-line text, corrections, geometry, font candidates, size, weight, color, and evidence for any caller.

**Architecture:** Keep `full_image_ppt` unchanged. Add a subprocess-isolated `paddleocr-local` single-image extractor with a stable line-level JSON contract. Keep page pairing, script comparison, multi-image OCR, and final PPT/render QA outside the extractor; legacy rebuild is only one optional consumer.

**Tech Stack:** Python 3.12 virtual environment, PaddlePaddle/PaddleOCR pinned from `/Volumes/DOC/PaddleOCR`, JSON Schema-like validation using existing Python code, Pillow/OpenCV-compatible image inspection, unittest/pytest, existing CyberPPT CLI and render QA.

## Global Constraints

- Input is GPT-generated page PNG only; do not enable orientation correction, unwarping, or perspective correction by default.
- PaddleOCR must be installed and invoked from a repository-controlled runtime; the main CyberPPT interpreter must not import it.
- `paddleocr-local` is legacy/advanced only; `full_image_ppt` must never invoke OCR.
- Preserve `observed_text` and every automatic replacement; replacements must be reversible.
- Protect institution names, project names, numbers, dates, IDs, and Latin abbreviations from automatic replacement unless explicitly configured.
- Save model/config hashes and raw/visual evidence for every OCR run.
- Do not claim definitive font identity in OCR; emit glyph, color, line-height, and crop evidence for `style-fit`.
- The extractor accepts one source image at a time and does not know whether it is full/background.
- The extractor itself owns typo detection/correction and complete line-level visual attributes; caller-specific page QA remains external.

---

### Task 1: Lock the repository runtime and model manifest

**Files:**
- Create: `tools/paddleocr_runtime/requirements-paddleocr.txt`
- Create: `tools/paddleocr_runtime/runtime_manifest.json`
- Create: `tools/paddleocr_runtime/README.md`
- Create: `tools/paddleocr_runtime/bootstrap.sh`
- Test: `tests/test_paddleocr_runtime_manifest.py`

**Interfaces:**
- `runtime_manifest.json` contains `python_version`, `paddleocr_version`, `paddle_version`, `models`, `sha256`, and `device`.
- `bootstrap.sh` accepts no positional arguments, creates `.venv` below `tools/paddleocr_runtime`, installs the pinned requirements, and exits nonzero if the interpreter is not Python 3.12.

- [ ] **Step 1: Write the manifest validation test**

```python
def test_runtime_manifest_has_pinned_versions_and_model_hashes():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["python_version"] == "3.12"
    assert data["paddleocr_version"]
    assert data["paddle_version"]
    assert data["models"]
    assert all(item["sha256"] for item in data["models"])
```

- [ ] **Step 2: Run the test and verify it fails because the manifest is absent**

Run: `python3 -m pytest tests/test_paddleocr_runtime_manifest.py -q`

Expected: FAIL with a missing manifest path.

- [ ] **Step 3: Add pinned runtime metadata and bootstrap instructions**

Use the PaddleOCR checkout's current release-compatible package versions after a Python 3.12 installation probe. Do not commit model binaries; commit the exact download URLs and SHA-256 values in `runtime_manifest.json`. `bootstrap.sh` must use `"$VIRTUAL_ENV/bin/python" -m pip`, never bare `pip`.

- [ ] **Step 4: Run the test and verify it passes**

Run: `python3 -m pytest tests/test_paddleocr_runtime_manifest.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add tools/paddleocr_runtime tests/test_paddleocr_runtime_manifest.py
git commit -m "build: pin repository PaddleOCR runtime"
```

### Task 2: Add the local PaddleOCR adapter

**Files:**
- Create: `scripts/dual_image_overlay/rebuild_engine/paddleocr_local.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/ocr_text_locator.py:1-220`
- Test: `tests/test_paddleocr_local.py`
- Modify: `tests/test_ocr_text_locator.py`

**Interfaces:**
- `paddleocr_local.py` exposes `run_local_ocr(image_path: Path, *, runtime_dir: Path, model_dir: Path | None = None, scale: float = 1.0) -> dict[str, Any]`.
- `run_local_ocr` returns `{image_size, items, raw_items, backend, runtime}` and never calls a network endpoint.
- `locate_text(..., backend="paddleocr-local")` invokes the adapter and normalizes its output through the existing contract.

- [ ] **Step 1: Write adapter tests with a fake runtime result**

```python
def test_adapter_maps_rec_boxes_and_scores(monkeypatch, tmp_path):
    monkeypatch.setattr(paddleocr_local, "_invoke_runtime", lambda **_: {
        "rec_texts": ["经营管理能力"],
        "rec_scores": [0.98],
        "rec_boxes": [[112, 237, 418, 276]],
        "dt_polys": [[[112, 237], [418, 237], [418, 276], [112, 276]]],
    })
    result = paddleocr_local.run_local_ocr(tmp_path / "page.png", runtime_dir=tmp_path)
    assert result["items"][0]["text"] == "经营管理能力"
    assert result["items"][0]["bbox"] == [112.0, 237.0, 418.0, 276.0]
    assert result["items"][0]["confidence"] == 0.98
```

- [ ] **Step 2: Run tests and verify they fail because the adapter is absent**

Run: `python3 -m pytest tests/test_paddleocr_local.py -q`

Expected: FAIL with an import or missing function error.

- [ ] **Step 3: Implement the adapter and backend dispatch**

Run the pinned runtime with `subprocess.run(..., check=True, timeout=...)`; pass the image path and a JSON output path; set `use_doc_orientation_classify=False`, `use_doc_unwarping=False`, and `use_textline_orientation=False`. Map every returned polygon and box to original coordinates, clip to image bounds, reject invalid boxes, and attach `source="paddleocr-local"`.

- [ ] **Step 4: Run focused OCR tests**

Run: `python3 -m pytest tests/test_paddleocr_local.py tests/test_ocr_text_locator.py -q`

Expected: PASS, including the existing remote retry tests and a test proving `paddleocr-local` does not call `run_codex_vision_text`.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/paddleocr_local.py scripts/dual_image_overlay/rebuild_engine/ocr_text_locator.py tests/test_paddleocr_local.py tests/test_ocr_text_locator.py
git commit -m "feat: add local PaddleOCR text locator"
```

### Task 3: Reconstruct visual lines and preserve forensic evidence

**Files:**
- Create: `scripts/dual_image_overlay/rebuild_engine/text_forensics.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/ocr_text_locator.py`
- Test: `tests/test_text_forensics.py`

**Interfaces:**
- `build_line_evidence(layout: dict[str, Any], image_path: Path, *, evidence_dir: Path) -> dict[str, Any]`.
- Output includes `schema_version`, `image`, `model`, `lines`, `quality`, and `artifacts`.
- Each line includes `observed_text`, `polygon`, `bbox`, `confidence`, `reading_order`, `glyph_crop`, `dominant_fill`, and `line_height_px`.

- [ ] **Step 1: Write tests for same-line merging, reading order, and evidence paths**

```python
def test_build_line_evidence_merges_adjacent_words_on_one_baseline(tmp_path):
    layout = {"image_size": {"width": 1000, "height": 600}, "items": [
        {"text": "经营", "bbox": [10, 20, 60, 50], "confidence": .98},
        {"text": "管理", "bbox": [64, 20, 114, 50], "confidence": .97},
    ]}
    result = build_line_evidence(layout, make_test_image(tmp_path), evidence_dir=tmp_path / "evidence")
    assert result["lines"][0]["observed_text"] == "经营管理"
    assert Path(result["lines"][0]["glyph_crop"]).is_file()
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python3 -m pytest tests/test_text_forensics.py -q`

Expected: FAIL because `build_line_evidence` is absent.

- [ ] **Step 3: Implement deterministic line clustering and evidence extraction**

Cluster boxes by baseline overlap and normalized vertical distance; sort left-to-right within a line and top-to-bottom across lines. Preserve raw item order and polygons. Crop each line with a bounded padding, sample interior text pixels for dominant fill, and record the exact image size and scale used.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_text_forensics.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/text_forensics.py scripts/dual_image_overlay/rebuild_engine/ocr_text_locator.py tests/test_text_forensics.py
git commit -m "feat: record line-level OCR forensic evidence"
```

### Task 4: Implement controlled automatic correction

**Files:**
- Create: `scripts/dual_image_overlay/rebuild_engine/controlled_correction.py`
- Create: `config/ocr/protected_terms.json`
- Create: `config/ocr/correction_policy.json`
- Modify: `scripts/dual_image_overlay/rebuild_engine/text_forensics.py`
- Test: `tests/test_controlled_correction.py`

**Interfaces:**
- `correct_lines(lines: list[dict[str, Any]], *, policy_path: Path, protected_terms_path: Path) -> list[dict[str, Any]]`.
- Each changed line receives `final_text`, `correction.applied`, `correction.changes`, `correction.reason`, `correction.confidence`, and `correction.reversible=True`.
- Protected terms are matched before any candidate replacement.

- [ ] **Step 1: Write tests for accepted correction, protected term, and low-confidence preservation**

```python
def test_correction_is_reversible_and_protected_term_is_unchanged(tmp_path):
    lines = [{"observed_text": "经菅管理", "char_candidates": [{"from": "菅", "to": "营", "confidence": .997}]}]
    corrected = correct_lines(lines, policy_path=POLICY, protected_terms_path=PROTECTED)
    assert corrected[0]["final_text"] == "经营管理"
    assert corrected[0]["correction"]["reversible"] is True
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python3 -m pytest tests/test_controlled_correction.py -q`

Expected: FAIL because the correction module is absent.

- [ ] **Step 3: Implement policy-driven correction**

Require multi-scale agreement and configured confidence thresholds; reject candidates touching protected spans; preserve the original string and exact character changes; write `review_required=true` when the threshold is not met. Do not use a remote language model in this path.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_controlled_correction.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/controlled_correction.py config/ocr tests/test_controlled_correction.py scripts/dual_image_overlay/rebuild_engine/text_forensics.py
git commit -m "feat: add reversible OCR correction policy"
```

### Task 5: Add quality gates and legacy rebuild integration

**Files:**
- Create: `scripts/dual_image_overlay/rebuild_engine/ocr_quality_gate.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py:720-750`
- Test: `tests/test_ocr_quality_gate.py`
- Test: `tests/test_dual_image_overlay_template_rebuild.py`

**Interfaces:**
- `evaluate_ocr_quality(forensics: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]` returns `status`, `failures`, `metrics`, and `recovery_command`.
- `editable_overlay_rebuild` writes `analysis/ocr/page_<n>_text_forensics.json` and refuses high-quality editable output when the gate is failed.

- [ ] **Step 1: Write tests for pass, low recall, and protected replacement failure**

```python
def test_quality_gate_rejects_missing_lines():
    report = evaluate_ocr_quality({"quality": {"line_recall": .72, "low_confidence_ratio": .04}}, policy={"min_line_recall": .95})
    assert report["status"] == "failed"
    assert "line_recall" in report["failures"]
```

- [ ] **Step 2: Run tests and verify they fail**

Run: `python3 -m pytest tests/test_ocr_quality_gate.py -q`

Expected: FAIL because the quality gate is absent.

- [ ] **Step 3: Implement the gate and wire the legacy path**

Add explicit CLI choices `paddleocr-local`, `vision-json`, and `none`; keep `full_image_ppt` command paths unchanged. Write forensic artifacts before text overlay. On failure, retain raw evidence, emit a recovery command for forced 2×/region rerun, and stop before claiming an approved editable text layer.

- [ ] **Step 4: Run the legacy regression suite**

Run: `python3 -m pytest tests/test_ocr_quality_gate.py tests/test_ocr_text_locator.py tests/test_dual_image_overlay_template_rebuild.py -q`

Expected: PASS; existing `vision-json` behavior remains compatible.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/rebuild_engine/ocr_quality_gate.py scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py scripts/dual_image_overlay/template_rebuild.py tests/test_ocr_quality_gate.py tests/test_dual_image_overlay_template_rebuild.py
git commit -m "feat: gate legacy rebuild on OCR quality"
```

### Task 6: Add golden fixtures, render verification, and documentation

**Files:**
- Create: `tests/fixtures/ocr_golden/README.md`
- Create: `tests/test_ocr_golden_contract.py`
- Modify: `SKILL.md`
- Modify: `docs/repository-layout.md`
- Modify: `docs/superpowers/specs/2026-07-11-high-fidelity-text-forensics-design.md`

**Interfaces:**
- Golden fixtures contain only approved GPT-generated page images, expected line boxes/text, and expected correction audit records; no secret or external service credential.
- The documented verification command is `python3 -m pytest tests/test_ocr_golden_contract.py -q`.

- [ ] **Step 1: Add a schema/fixture contract test**

```python
def test_golden_forensics_has_required_audit_fields():
    for path in GOLDEN_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_version"]
        assert all("observed_text" in line and "final_text" in line for line in data["lines"])
```

- [ ] **Step 2: Run the test and verify the fixture contract is initially absent**

Run: `python3 -m pytest tests/test_ocr_golden_contract.py -q`

Expected: FAIL because no approved golden fixture exists.

- [ ] **Step 3: Add approved fixtures and document the workflow**

Use repository-approved GPT page images only. Update `SKILL.md` to state when legacy OCR is allowed, which artifacts are mandatory, and which command verifies them. Document runtime setup, offline model verification, artifact paths, and recovery behavior in `docs/repository-layout.md`.

- [ ] **Step 4: Run full verification**

Run: `python3 -m pytest tests/test_paddleocr_runtime_manifest.py tests/test_paddleocr_local.py tests/test_ocr_text_locator.py tests/test_text_forensics.py tests/test_controlled_correction.py tests/test_ocr_quality_gate.py tests/test_ocr_golden_contract.py -q`

Expected: PASS with no network OCR call. Run one legacy end-to-end rebuild and render its output for visual inspection.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/ocr_golden tests/test_ocr_golden_contract.py SKILL.md docs/repository-layout.md docs/superpowers/specs/2026-07-11-high-fidelity-text-forensics-design.md
git commit -m "docs: document high-fidelity OCR quality workflow"
```

## Self-review

- Runtime isolation and model provenance are covered by Task 1.
- The local adapter and no-network guarantee are covered by Task 2.
- Per-line geometry, color, glyph evidence, and reading order are covered by Task 3.
- Reversible, protected, policy-driven correction is covered by Task 4.
- Legacy integration, quality refusal, and recovery are covered by Task 5.
- Golden fixtures, render verification, and SKILL documentation are covered by Task 6.
- The current `full_image_ppt` mainline is explicitly protected in Tasks 2 and 5.
- No task relies on a remote OCR service or unversioned model files.

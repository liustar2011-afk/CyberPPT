# Stage 02 Image-to-Editable-SVG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the dual-image Stage 02 editable-overlay route with PPT Master-equivalent, single-audited-full-image reconstruction to editable SVG and native PPTX.

**Architecture:** The manifest keeps `full-image` as the sole image-generation variant and records the audited full image. A new `scripts/image_to_editable_svg` package normalizes page frames, inventories visible regions, prepares registered layers, author SVG pages, and runs evidence-based page gates. `final-script-pages` calls this package, then the existing SVG-to-DrawingML compiler and postflight QA.

**Tech Stack:** Python 3.12, Pillow, existing OCR/layout/scene-graph helpers, SVG, python-pptx/DrawingML exporter, pytest.

## Global Constraints

- Remove `editable-overlay` and `editable-overlay-text-reference`; do not leave compatibility execution paths.
- Require a generated `full` image with a valid existing image-text/typo receipt before reconstruction.
- Script text is authoritative; OCR is locator evidence only.
- Never package the complete canonical source page as a hidden slide image with text overlaid above it.
- Do not generatively recreate charts, tables, numeric data, logos, or wordmarks unless the required identity/data is verified; otherwise emit `manual_required` and block delivery.
- Every generated/reconstructed layer originates from the canonical page and must retain canvas registration evidence.
- Preserve unrelated dirty-worktree changes and stage only the files listed in each task.

---

## Target file structure

| File | Responsibility |
| --- | --- |
| `scripts/image_to_editable_svg/contracts.py` | Typed schemas and validation for roster, inventory, layers, page QA, and run readiness. |
| `scripts/image_to_editable_svg/roster.py` | Archive/normalize full images into one ordered page frame per slide. |
| `scripts/image_to_editable_svg/reconstruct.py` | Per-page inspection, truth binding, asset/layer decisions, SVG authoring, and page gate. |
| `scripts/image_to_editable_svg/orchestrator.py` | Batch reconstruction, SVG/PPTX assembly, text readback, render comparison, and readiness report. |
| `scripts/image_to_editable_svg/__main__.py` | CLI for direct reconstruction and testable subprocess integration. |
| `scripts/dual_image_overlay/cyberppt_pair_manifest.py` | Retain only `full-image`; reject removed manifest modes. |
| `cyberppt/commands/final_script_pages.py` | Replace image-PPT/dual-rebuild branch selection with the new production build. |
| `cyberppt/cli.py` | Remove `rebuild-dual-image`; expose `image-to-editable-svg`. |
| `tests/test_image_to_editable_svg_*.py` | Unit and end-to-end coverage for the new production contract. |

### Task 1: Replace the Stage 02 mode contract

**Files:**
- Modify: `scripts/dual_image_overlay/cyberppt_pair_manifest.py:44-67,174-224,336-757,760-815`
- Modify: `cyberppt/commands/final_script_pages.py:603-749,752-772,775-1181`
- Modify: `cyberppt/cli.py:447-500,build_parser`
- Modify: `tests/test_dual_image_overlay_pair_manifest.py`
- Modify: `tests/test_final_script_pages.py`

**Interfaces:**
- Consumes: approved script, Stage 02 handoff, current image-text audit receipt.
- Produces: `page_image_pairs.json` with `production_mode == "image-to-editable-svg"`, `output_variants == ["full"]`, and `pairs[*].full.text_audit.valid is True`.

- [ ] **Step 1: Write failing mode-contract tests**

```python
def test_image_to_editable_svg_has_only_audited_full_variant(tmp_path):
    manifest, *_ = build_manifest(
        script=write_approved_script(tmp_path), pages_raw="1", output_dir=tmp_path / "build",
        project_path=make_stage02_project(tmp_path), style_lock=None,
        production_mode="image-to-editable-svg",
    )
    assert manifest["output_variants"] == ["full"]
    assert manifest["production_mode"] == "image-to-editable-svg"

def test_removed_dual_mode_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="image-to-editable-svg"):
        build_manifest(script=write_approved_script(tmp_path), pages_raw="1",
                       output_dir=tmp_path / "build", project_path=None,
                       style_lock=None, production_mode="editable-overlay")
```

- [ ] **Step 2: Run the focused tests and verify failure**

Run: `PYTHONPATH=. pytest -q tests/test_dual_image_overlay_pair_manifest.py tests/test_final_script_pages.py -k 'editable_svg or dual_mode'`

Expected: FAIL because the old modes remain supported.

- [ ] **Step 3: Implement the one-mode manifest contract**

```python
FULL_IMAGE_MODE = "image-to-editable-svg"
PRODUCTION_MODES = (FULL_IMAGE_MODE,)

def output_variants_for_mode(production_mode: str) -> list[str]:
    if production_mode != FULL_IMAGE_MODE:
        raise ValueError("unsupported production mode; expected image-to-editable-svg")
    return ["full"]
```

Remove background/text-reference prompts, generation methods, CLI choices, and
all branch conditions that request them. Require the valid `full.text_audit`
receipt before a production build, while retaining the existing audit/retry
logic in `_generate_manifest_images`.

- [ ] **Step 4: Update the final-script command surface**

Delete `_run_editable_rebuild` and `_run_image_ppt_build` selection from this
route. Define a single internal call shape for Task 5:

```python
def _run_image_to_editable_svg_build(*, project: Path, manifest_path: Path,
                                     output_dir: Path, pages_raw: str) -> dict[str, Any]:
    return run_image_to_editable_svg(
        project=project, manifest_path=manifest_path, output_dir=output_dir,
        requested_pages=[int(value) for value in pages_raw.split(",")],
    )
```

Remove the `rebuild-dual-image` subcommand. Add an `image-to-editable-svg`
subcommand that dispatches `python -m scripts.image_to_editable_svg` for
diagnostic/direct use; `final-script-pages --production-build` remains the
normal production entrypoint.

- [ ] **Step 5: Run regression tests**

Run: `PYTHONPATH=. pytest -q tests/test_dual_image_overlay_pair_manifest.py tests/test_final_script_pages.py`

Expected: PASS, with no test accepting dual/triple variants.

- [ ] **Step 6: Commit**

```bash
git add scripts/dual_image_overlay/cyberppt_pair_manifest.py cyberppt/commands/final_script_pages.py cyberppt/cli.py tests/test_dual_image_overlay_pair_manifest.py tests/test_final_script_pages.py
git commit -m "refactor(stage02): replace dual image mode contract"
```

### Task 2: Create canonical roster and reconstruction evidence contracts

**Files:**
- Create: `scripts/image_to_editable_svg/__init__.py`
- Create: `scripts/image_to_editable_svg/contracts.py`
- Create: `scripts/image_to_editable_svg/roster.py`
- Test: `tests/test_image_to_editable_svg_roster.py`
- Test: `tests/test_image_to_editable_svg_contracts.py`

**Interfaces:**
- Consumes: manifest `pairs[*].full.path`, full-image hash, and requested page number.
- Produces: `NormalizedFrame`, `ReconstructionInventory`, and JSON-safe `PageGate` mappings.

- [ ] **Step 1: Write failing roster and validation tests**

```python
def test_normalize_frame_preserves_order_hash_and_canvas(tmp_path):
    frame = normalize_full_page(page_number=4, source=image, output_dir=tmp_path)
    assert frame.page_number == 4
    assert Path(frame.normalized_path).is_file()
    assert frame.source_sha256 == sha256_file(image)

def test_manual_required_region_blocks_page_gate():
    gate = page_gate([{"id": "chart", "realization": "manual_required"}])
    assert gate["valid"] is False
    assert gate["blocking_errors"][0]["code"] == "manual_required"
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_roster.py tests/test_image_to_editable_svg_contracts.py`

Expected: FAIL because the package does not exist.

- [ ] **Step 3: Implement closed, JSON-safe contracts**

```python
@dataclass(frozen=True)
class NormalizedFrame:
    page_number: int
    source_path: str
    source_sha256: str
    normalized_path: str
    pixel_size: tuple[int, int]

def build_inventory(frame: NormalizedFrame, regions: list[dict[str, Any]]) -> dict[str, Any]:
    return {"schema": "cyberppt.image_to_editable_svg.inventory.v1", "frame": asdict(frame), "regions": regions}
```

Copy, never overwrite, the full-image source into the project-local source
evidence root. Normalize without trimming canvas pixels. Accept one full image
per selected Stage 02 page; frame/contact-sheet splitting is deliberately
implemented as reusable roster API but rejected by the Stage 02 manifest when
the requested page mapping is ambiguous.

- [ ] **Step 4: Run tests and static syntax check**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_roster.py tests/test_image_to_editable_svg_contracts.py && python -m compileall -q scripts/image_to_editable_svg`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/image_to_editable_svg tests/test_image_to_editable_svg_roster.py tests/test_image_to_editable_svg_contracts.py
git commit -m "feat(stage02): add editable SVG reconstruction contracts"
```

### Task 3: Implement complete page inspection and registered-layer preparation

**Files:**
- Create: `scripts/image_to_editable_svg/reconstruct.py`
- Modify: `scripts/image_to_editable_svg/contracts.py`
- Test: `tests/test_image_to_editable_svg_reconstruct.py`

**Interfaces:**
- Consumes: `NormalizedFrame`, script truth lines, OCR/layout evidence, and Stage 02 visual registry.
- Produces: `{inventory, layers, page_gate}` where each layer has `id`, `family`, `bbox`, `z_index`, `realization`, `source_hash`, `registration_group`, and `status`.

- [ ] **Step 1: Write failing fidelity tests**

```python
def test_text_is_bound_to_script_truth_not_ocr_guess(tmp_path):
    result = inspect_page(frame, script_text=["核心结论"], ocr_layout=ocr)
    assert result.layers[-1].text == "核心结论"
    assert result.layers[-1].truth_source == "script"

def test_unverified_data_and_identity_regions_require_manual_work(tmp_path):
    result = inspect_page(frame, script_text=[], ocr_layout=ocr_with_chart_and_logo)
    assert {r["id"] for r in result.manual_required} == {"chart", "logo"}

def test_registered_scene_layers_keep_the_source_canvas(tmp_path):
    layers = prepare_scene_layers(frame, regions)
    assert all(layer.registration_group == "page-004" for layer in layers)
    assert all(layer.canvas == frame.pixel_size for layer in layers)
```

- [ ] **Step 2: Run the tests and verify failure**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_reconstruct.py`

Expected: FAIL because inspection and layer preparation do not exist.

- [ ] **Step 3: Implement the PPT Master realization rules**

Implement `inspect_page()` with explicit region classifications: `text`,
`simple_geometry`, `source_graphic`, `data_graphic`, `scene`, and `unknown`.
Use the approved script as text truth and existing OCR only for coordinates.
Implement `prepare_scene_layers()` so a separable scene receives a clean base
and independently placeable subject/foreground layers; batch only disjoint
objects into a `shared_plate`, then split deterministically while retaining
full-canvas registration. Record `manual_required` instead of inventing any
unverified text, numeric value, chart/table, logo, or wordmark.

```python
def require_verified_region(region: dict[str, Any]) -> None:
    if region["family"] in {"data_graphic", "source_graphic"} and not region["identity_verified"]:
        region.update(realization="manual_required", status="manual_required")
```

For reference reconstruction, use the canonical full image as every input,
write prompt/model/output-hash evidence, set `text_policy` to `none`, inspect
the output, and verify registration before the layer becomes usable. Do not
call the removed background-image generator.

- [ ] **Step 4: Run the reconstruction tests**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_reconstruct.py`

Expected: PASS, including manual-required and shared-plate cases.

- [ ] **Step 5: Commit**

```bash
git add scripts/image_to_editable_svg/reconstruct.py scripts/image_to_editable_svg/contracts.py tests/test_image_to_editable_svg_reconstruct.py
git commit -m "feat(stage02): reconstruct audited images into registered layers"
```

### Task 4: Author editable SVG and enforce per-page fidelity gates

**Files:**
- Modify: `scripts/image_to_editable_svg/reconstruct.py`
- Create: `scripts/image_to_editable_svg/svg_quality.py`
- Test: `tests/test_image_to_editable_svg_svg.py`

**Interfaces:**
- Consumes: verified inventory/layers plus script truth.
- Produces: `svg_output/pNN.svg` and `analysis/pNN-reconstruction-quality.json`.

- [ ] **Step 1: Write failing SVG tests**

```python
def test_svg_uses_native_text_and_excludes_full_source_image(tmp_path):
    svg = author_page_svg(result, out_dir)
    assert "核心结论" in svg.read_text(encoding="utf-8")
    assert str(frame.normalized_path) not in svg.read_text(encoding="utf-8")

def test_quality_gate_rejects_unregistered_or_manual_layer(tmp_path):
    report = check_page_svg(svg, inventory_with_bad_layer)
    assert report["valid"] is False
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_svg.py`

Expected: FAIL because no SVG author/gate is available.

- [ ] **Step 3: Implement SVG realization**

Reuse `build_page_scene_graph` and `compile_scene_graph_to_page_svg_ir` only
for semantic text geometry and relationship binding. Supply the new prepared
layer list rather than `background_href`; render ordinary text as SVG `<text>`
objects, simple geometry as paths/shapes, and layer assets as individually
identified `<image>` elements. Add `check_page_svg()` predicates for native
text truth, reference exclusion, verified source/data graphics, registered
layer canvas/bboxes, z-order, no `manual_required`, and existing SVG parser
quality.

- [ ] **Step 4: Run SVG tests**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_svg.py tests/test_dual_image_overlay_qa.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/image_to_editable_svg/reconstruct.py scripts/image_to_editable_svg/svg_quality.py tests/test_image_to_editable_svg_svg.py
git commit -m "feat(stage02): author fidelity-gated editable SVG pages"
```

### Task 5: Orchestrate SVG-to-PPTX assembly and Stage 02 delivery readiness

**Files:**
- Create: `scripts/image_to_editable_svg/orchestrator.py`
- Create: `scripts/image_to_editable_svg/__main__.py`
- Modify: `cyberppt/commands/final_script_pages.py:461-600,920-1181`
- Modify: `scripts/dual_image_overlay/production_readiness.py`
- Test: `tests/test_image_to_editable_svg_orchestrator.py`
- Test: `tests/test_final_script_pages.py`

**Interfaces:**
- Consumes: valid one-variant manifest and approved script.
- Produces: `{status, artifacts, reports}` with exported PPTX only when all page gates pass.

- [ ] **Step 1: Write failing end-to-end tests**

```python
def test_production_build_runs_full_audit_svg_pptx_and_readback(project, manifest):
    result = run_image_to_editable_svg(project=project, manifest_path=manifest)
    assert result["status"] == "production_ready"
    assert Path(result["artifacts"]["exported_pptx"]).is_file()
    assert result["reports"]["text_content_qa"]["valid"] is True

def test_manual_required_page_prevents_pptx_assembly(project, manifest):
    result = run_image_to_editable_svg(project=project, manifest_path=manifest)
    assert result["status"] == "production_rework_required"
    assert result["artifacts"]["exported_pptx"] is None
```

- [ ] **Step 2: Run tests and verify failure**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_orchestrator.py tests/test_final_script_pages.py -k 'editable_svg or manual_required'`

Expected: FAIL because production still delegates to image-ppt or the dual rebuild.

- [ ] **Step 3: Implement the orchestrator and production integration**

```python
def run_image_to_editable_svg(*, project: Path, manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest = load_and_require_audited_full_manifest(manifest_path)
    pages = [reconstruct_page(project, pair, output_dir) for pair in manifest["pairs"]]
    if any(not page["quality"]["valid"] for page in pages):
        return blocked_readiness(pages)
    pptx = assemble_svg_pages([Path(page["svg"]) for page in pages], output_dir)
    return finalize_readiness(pages, pptx)
```

Call `create_pptx_with_native_svg()` exactly once for the ordered SVG roster.
Run existing `build_text_content_qa()` against approved script text and render
the PPTX for page-reference comparison. Extend readiness to require inventory,
page quality, SVG quality, text readback, render comparison, and exported
PPTX. Return the new artifact paths from `final-script-pages`, including
`reconstruction_inventory`, `svg_output`, `reconstruction_quality`,
`exported_pptx`, and `delivery_readiness`.

- [ ] **Step 4: Run focused end-to-end tests**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_orchestrator.py tests/test_final_script_pages.py`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/image_to_editable_svg cyberppt/commands/final_script_pages.py scripts/dual_image_overlay/production_readiness.py tests/test_image_to_editable_svg_orchestrator.py tests/test_final_script_pages.py
git commit -m "feat(stage02): assemble editable SVG production builds"
```

### Task 6: Remove the legacy dual-image implementation and complete regression QA

**Files:**
- Delete: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
- Delete: tests dedicated solely to removed background/text-reference behavior
- Modify: references/workflow documentation that names dual-image production
- Modify: `tests/test_skill_contract.py`
- Test: retained Stage 02, image-text audit, SVG exporter, and autonomous-run suites

**Interfaces:**
- Consumes: no legacy manifest or command.
- Produces: a repository with only the audited-full-image editable production route.

- [ ] **Step 1: Write deletion/absence regression tests**

```python
def test_cli_has_no_dual_image_rebuild_command(capsys):
    with pytest.raises(SystemExit):
        cli.main(["rebuild-dual-image"])

def test_stage02_docs_do_not_advertise_dual_image_production():
    assert "editable-overlay-text-reference" not in documentation_text()
```

- [ ] **Step 2: Run them and verify failure**

Run: `PYTHONPATH=. pytest -q tests/test_skill_contract.py -k 'dual_image or editable_svg'`

Expected: FAIL while stale entrypoints or contract language remain.

- [ ] **Step 3: Delete only obsolete implementation and update contracts**

Remove the legacy executable and tests that assert background/text-reference
generation. Keep shared, proven utilities under `scripts/dual_image_overlay`
(SVG-to-PPTX, image-text QA, scene graph, text QA) when the new package imports
them. Update all user-facing Stage 02 guidance to describe the audited-full
image → editable SVG → PPTX chain and explicitly state no screenshot-skin
fallback.

- [ ] **Step 4: Run complete verification**

Run: `PYTHONPATH=. pytest -q tests/test_image_to_editable_svg_*.py tests/test_final_script_pages.py tests/test_imagegen_handoff tests/test_imagegen_run tests/test_dual_image_overlay_qa.py tests/test_skill_contract.py`

Expected: PASS. Then run `PYTHONPATH=. pytest -q` and report any pre-existing
failure separately from this change.

- [ ] **Step 5: Render a representative generated PPTX**

Run: `python scripts/office/soffice.py --headless --convert-to pdf <exported.pptx>` followed by `pdftoppm -jpeg -r 150 <exported.pdf> <output-prefix>`.

Expected: one image per exported slide; inspect the rendered pages for text
placement, layer registration, clipping, and visual drift before delivery.

- [ ] **Step 6: Commit**

```bash
git add -u scripts/dual_image_overlay/rebuild_engine tests references cyberppt scripts
git add tests/test_skill_contract.py
git commit -m "refactor(stage02): retire dual image editable overlay"
```

## Final review checklist

- Every legacy mode, manifest variant, command, and test acceptance path is removed.
- A passing typo-audit receipt is mandatory before all reconstruction work.
- Each page has inventory, layer evidence, SVG QA, PPTX text readback, and render comparison.
- No unresolved page produces a final PPTX.
- The existing SVG→PPTX compiler remains the only final exporter.

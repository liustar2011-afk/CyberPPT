# Dual Image Rebuild Mode And Scene Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make dual-image rebuild mode explicit, make QA reference metadata mode-aware, and preserve semantic layout item slots through scene graph layout while preserving the ingress `1280×720` coordinate contract.

**Architecture:** Keep the existing rebuild pipeline intact after its normalized-image ingress. `editable_overlay_rebuild.py` must continue to generate `images/normalized/*_1280x720.png` as the first processing step, and all later semantic, scene graph, layout, and QA work must consume only `1280×720` coordinates. Add small mode/reference helpers in `template_rebuild.py`, pass semantic layout item bbox evidence into scene graph text node styles in `scene_graph/builder.py`, and make `scene_graph/layout.py` prefer that explicit item bbox over coarse container safe areas.

**Tech Stack:** Python 3, pytest/unittest, existing CyberPPT dual-image overlay modules, JSON artifacts.

---

## File Structure

- Preserve `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
  - Keep `_prepare_page_images()` as the first per-page processing step.
  - Keep normalized full/background files under `ppt_project/images/normalized/`.
  - Do not reintroduce source-size, registry-size, or stale semantic-plan-size coordinates into downstream layout.
- Modify `scripts/dual_image_overlay/scene_graph/builder.py`
  - Add semantic layout item lookup keyed by normalized text and container target.
  - Attach `layout_bbox`, `layout_strategy`, and `layout_source` into matching `TextNode.style`.
- Modify `scripts/dual_image_overlay/scene_graph/layout.py`
  - Resolve bbox from `TextNode.style["layout_bbox"]` before container fallback.
  - Emit `layout_strategy` and `layout_source` in page layout items.
- Modify `scripts/dual_image_overlay/template_rebuild.py`
  - Add rebuild-mode resolution helpers.
  - Add `visual_reference_mode` and `visual_reference` metadata to readiness.
  - Distinguish `visual_qa_setup_required` when mode/reference evidence is inconsistent.
- Modify `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
  - Propagate `rebuild_mode` into `rebuild_quality.json`.
  - Preserve existing ingress normalization behavior while adding mode metadata.
- Modify `tests/test_scene_graph_layout.py`
  - Add failing test for preserving semantic item bboxes.
- Modify `tests/test_dual_image_overlay_template_rebuild.py`
  - Add failing tests for `template_body_region` and `full_slide` visual reference metadata.

## Already Completed Prerequisite

Commit `fe10af44 fix: normalize dual image inputs at rebuild ingress` completed the coordinate prerequisite after this plan was first drafted.

Do not redo or weaken this prerequisite. Treat it as a hard contract:

- Raw full/background images may have any source resolution.
- The first rebuild step creates normalized intermediates at exactly `1280×720`.
- `semantic_plan.image_size`, scene graph `image_size`, and scene graph `semantic_input_space` must be `1280×720` after ingress.
- Source dimensions such as `1672×941` may only appear as provenance fields like `source_full_size` or `coordinate_normalization.input_space`.
- Stale semantic metadata such as `1920×941` must not drive any downstream bbox math.

## Task 1: Preserve Semantic Layout Item Bboxes

**Files:**
- Modify: `tests/test_scene_graph_layout.py`
- Modify: `scripts/dual_image_overlay/scene_graph/builder.py`
- Modify: `scripts/dual_image_overlay/scene_graph/layout.py`

**Coordinate precondition:** All test bboxes in this task are already in normalized `1280×720` space. Do not add source-resolution scaling to these tests or implementation code.

- [ ] **Step 1: Write the failing test**

Append this test to `tests/test_scene_graph_layout.py`:

```python
def test_scene_graph_layout_preserves_semantic_item_bbox():
    graph = PageSceneGraph(
        page=6,
        coordinate_context={"coordinate_space": {"width": 1280, "height": 720}},
        truth_sources={},
        visual_nodes=[
            VisualNode("ability_1", "container", "ability_card", BBox(300, 100, 520, 260), {"kind": "semantic_plan"})
        ],
        text_nodes=[
            TextNode(
                "text_1",
                "1",
                {"kind": "script"},
                "index",
                TextBinding("container_text", target_id="ability_1", safe_bbox=BBox(330, 120, 500, 240)),
                style={
                    "layout_bbox": [332.0, 122.0, 348.0, 138.0],
                    "layout_strategy": "ability_card_slots",
                    "layout_source": "semantic_layout_plan",
                    "font_size": 13,
                },
            ),
            TextNode(
                "text_2",
                "目录管理",
                {"kind": "script"},
                "ability_title",
                TextBinding("container_text", target_id="ability_1", safe_bbox=BBox(330, 120, 500, 240)),
                style={
                    "layout_bbox": [380.0, 121.0, 450.0, 140.0],
                    "layout_strategy": "ability_card_slots",
                    "layout_source": "semantic_layout_plan",
                    "font_size": 15,
                },
            ),
            TextNode(
                "text_3",
                "• 指标/能力目录",
                {"kind": "script"},
                "body",
                TextBinding("container_text", target_id="ability_1", safe_bbox=BBox(330, 120, 500, 240)),
                style={
                    "layout_bbox": [380.0, 146.0, 470.0, 156.0],
                    "layout_strategy": "ability_card_slots",
                    "layout_source": "semantic_layout_plan",
                    "font_size": 11,
                },
            ),
        ],
    )

    plan = build_layout_plan_from_scene_graph(graph)
    by_text = {item["text"]: item for item in plan["items"]}

    assert by_text["1"]["bbox"] == [332.0, 122.0, 348.0, 138.0]
    assert by_text["目录管理"]["bbox"] == [380.0, 121.0, 450.0, 140.0]
    assert by_text["• 指标/能力目录"]["bbox"] == [380.0, 146.0, 470.0, 156.0]
    assert by_text["目录管理"]["layout_strategy"] == "ability_card_slots"
    assert by_text["目录管理"]["layout_source"] == "semantic_layout_plan"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_scene_graph_layout.py::test_scene_graph_layout_preserves_semantic_item_bbox
```

Expected: FAIL because `layout_strategy` is missing or the bbox falls back to `[330.0, 120.0, 500.0, 240.0]`.

- [ ] **Step 3: Add explicit layout bbox support to layout executor**

In `scripts/dual_image_overlay/scene_graph/layout.py`, add:

```python
def _style_bbox(style: dict[str, object], key: str) -> BBox | None:
    value = style.get(key)
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        x1, y1, x2, y2 = [float(item) for item in value]
    except (TypeError, ValueError):
        return None
    return BBox(x1, y1, x2, y2)
```

Change bbox resolution in `build_layout_plan_from_scene_graph()` to:

```python
explicit_bbox = _style_bbox(style, "layout_bbox")
if explicit_bbox is not None:
    bbox = explicit_bbox
elif binding_type == "edge_label":
    bbox = _bbox_for_edge_label(text, nodes)
else:
    bbox = _bbox_for_container_text(graph, text, nodes)
```

Add these fields to the emitted item:

```python
"layout_strategy": style.get("layout_strategy"),
"layout_source": style.get("layout_source") or "scene_graph_fallback",
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_scene_graph_layout.py::test_scene_graph_layout_preserves_semantic_item_bbox
```

Expected: PASS.

- [ ] **Step 5: Add semantic layout item evidence in builder**

In `scripts/dual_image_overlay/scene_graph/builder.py`, add helpers near `_text_by_capture_key()`:

```python
def _semantic_layout_item_key(text: str, target_id: str | None) -> tuple[str, str]:
    return (_normalize_text(text), str(target_id or ""))


def _semantic_layout_items_by_key(semantic_layout_plan: Mapping[str, Any] | None) -> dict[tuple[str, str], Mapping[str, Any]]:
    result: dict[tuple[str, str], Mapping[str, Any]] = {}
    if not semantic_layout_plan:
        return result
    items = semantic_layout_plan.get("items", [])
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or item.get("display_text") or "").strip()
        target_id = item.get("container_id") or item.get("target_id")
        if text and target_id:
            result[_semantic_layout_item_key(text, str(target_id))] = item
    return result


def _merge_semantic_layout_style(
    style: dict[str, Any],
    text: str,
    target_id: str | None,
    semantic_layout_items: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    item = semantic_layout_items.get(_semantic_layout_item_key(text, target_id))
    if not item:
        return style
    merged = dict(style)
    bbox = item.get("bbox")
    if isinstance(bbox, list) and len(bbox) == 4:
        merged["layout_bbox"] = [float(value) for value in bbox]
        merged["layout_source"] = "semantic_layout_plan"
    if item.get("layout_strategy"):
        merged["layout_strategy"] = item.get("layout_strategy")
    return merged
```

In `_text_nodes()`, compute:

```python
semantic_layout_items = _semantic_layout_items_by_key(semantic_layout_plan)
```

This requires adding `semantic_layout_plan: Mapping[str, Any] | None = None` to `_text_nodes()` parameters and passing it from `build_page_scene_graph()`.

Before constructing each `TextNode` with a container `target_id`, call:

```python
style = _merge_semantic_layout_style(style, text, target_id, semantic_layout_items)
```

For edge labels, call it with `str(item["target_id"])`.

- [ ] **Step 6: Add builder-level regression test if needed**

If Task 1 only tests manual `TextNode.style`, add this test to `tests/test_scene_graph_builder.py`:

```python
def test_builder_attaches_semantic_layout_item_bbox_to_text_node():
    graph = build_page_scene_graph(
        page_number=6,
        script_sections={},
        semantic_plan={
            "image_size": {"width": 1280, "height": 720},
            "containers": [{"id": "ability_1", "role": "ability_card", "bbox": [300, 100, 520, 260]}],
            "items": [{"display_text": "目录管理", "role": "ability_title", "container_id": "ability_1"}],
        },
        visual_registry={"blueprint_canvas_px": {"w": 1280, "h": 720}, "elements": []},
        image_size={"width": 1280, "height": 720},
        semantic_layout_plan={
            "schema": "cyberppt.dual_image.semantic_layout_plan.v1",
            "items": [
                {
                    "text": "目录管理",
                    "container_id": "ability_1",
                    "bbox": [380.0, 121.0, 450.0, 140.0],
                    "layout_strategy": "ability_card_slots",
                }
            ],
        },
    )

    assert graph.text_nodes[0].style["layout_bbox"] == [380.0, 121.0, 450.0, 140.0]
    assert graph.text_nodes[0].style["layout_strategy"] == "ability_card_slots"
```

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_scene_graph_builder.py::test_builder_attaches_semantic_layout_item_bbox_to_text_node
```

Expected before implementation: FAIL with missing `layout_bbox`. Expected after implementation: PASS.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
git add tests/test_scene_graph_layout.py tests/test_scene_graph_builder.py scripts/dual_image_overlay/scene_graph/builder.py scripts/dual_image_overlay/scene_graph/layout.py
git diff --cached --check
git commit -m "fix: preserve semantic layout slots in scene graph"
```

## Task 2: Add Rebuild Mode And Visual Reference Metadata

**Files:**
- Modify: `tests/test_dual_image_overlay_template_rebuild.py`
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`

**Coordinate precondition:** Do not replace `_prepare_page_images()` or route QA/reference generation back to raw source images for layout. Raw source image paths may be referenced only as `full_slide` visual QA references or provenance, not as downstream coordinate truth.

- [ ] **Step 1: Write failing tests for visual reference mode**

Append these tests to `DualImageOverlayTemplateRebuildTests` in `tests/test_dual_image_overlay_template_rebuild.py`:

```python
    def test_template_body_region_uses_template_normalized_visual_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project, rebuild_mode="template_body_region")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))

        self.assertEqual("template_body_region", readiness["rebuild_mode"])
        self.assertEqual("template_normalized_reference", readiness["visual_reference_mode"])
        self.assertIn("visual_reference", readiness["artifacts"])

    def test_full_slide_uses_raw_full_visual_reference(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            project = root / "template-project"
            _write_template_project(project)
            manifest = _write_pair_manifest(root, project, rebuild_mode="full_slide")

            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/dual_image_overlay/template_rebuild.py"),
                    str(manifest),
                    "--skip-rebuild",
                    "--no-export",
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(3, result.returncode, result.stdout + result.stderr)
            readiness = json.loads((project / "analysis/template_rebuild_readiness.json").read_text(encoding="utf-8"))

        self.assertEqual("full_slide", readiness["rebuild_mode"])
        self.assertEqual("raw_full_image", readiness["visual_reference_mode"])
        self.assertTrue(str(readiness["artifacts"]["visual_reference"]).endswith("page_002_full.png"))
```

Change `_write_pair_manifest()` signature to:

```python
def _write_pair_manifest(root: Path, project: Path, *, rebuild_mode: str = "template_body_region") -> Path:
```

Add the mode to the manifest:

```python
"rebuild_mode": rebuild_mode,
"generation_contract": {
    "mode": "template-content-region",
    "rebuild_mode": rebuild_mode,
    ...
},
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_template_body_region_uses_template_normalized_visual_reference tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_full_slide_uses_raw_full_visual_reference
```

Expected: FAIL because `rebuild_mode`, `visual_reference_mode`, and `artifacts.visual_reference` are missing.

- [ ] **Step 3: Implement mode helpers**

In `scripts/dual_image_overlay/template_rebuild.py`, add near `_latest_pptx()`:

```python
VALID_REBUILD_MODES = {"full_slide", "template_body_region"}


def _resolve_rebuild_mode(manifest: dict[str, Any]) -> str:
    raw = manifest.get("rebuild_mode")
    if not raw:
        contract = manifest.get("generation_contract")
        if isinstance(contract, dict):
            raw = contract.get("rebuild_mode")
    mode = str(raw or "template_body_region")
    if mode not in VALID_REBUILD_MODES:
        raise ValueError(f"Unsupported rebuild_mode: {mode}")
    return mode


def _first_full_image(manifest: dict[str, Any]) -> str | None:
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        return None
    full = pairs[0].get("full") if isinstance(pairs[0], dict) else None
    if not isinstance(full, dict):
        return None
    path = full.get("path")
    return str(Path(path).expanduser().resolve()) if isinstance(path, str) and path else None


def _visual_reference_for_mode(project_path: Path, manifest: dict[str, Any], rebuild_mode: str) -> tuple[str, str | None]:
    if rebuild_mode == "full_slide":
        return "raw_full_image", _first_full_image(manifest)
    reference = project_path / "qa" / "visual-reference" / "template-normalized-reference.png"
    return "template_normalized_reference", str(reference)
```

The `template-normalized-reference.png` may not exist when `--skip-rebuild` is used. At this stage the helper records the intended reference path; generation can be added later without breaking metadata consumers.

- [ ] **Step 4: Wire mode into readiness**

In `build_template_rebuild_readiness()`, after `manifest = _read_json(manifest_path)`, add:

```python
rebuild_mode = _resolve_rebuild_mode(manifest)
visual_reference_mode, visual_reference = _visual_reference_for_mode(project_path, manifest, rebuild_mode)
```

Add these fields to the readiness object:

```python
"rebuild_mode": rebuild_mode,
"visual_reference_mode": visual_reference_mode,
```

Add artifact:

```python
"visual_reference": visual_reference,
```

- [ ] **Step 5: Run tests to verify they pass**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_template_body_region_uses_template_normalized_visual_reference tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_full_slide_uses_raw_full_visual_reference
```

Expected: PASS.

- [ ] **Step 6: Propagate rebuild mode into rebuild quality**

In `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`, add mode propagation without changing the normalized-image ingress. Keep this flow intact:

```python
source_full_image = _require_image(pair["full"], "full")
source_background_image = _require_image(pair["background"], "background")
normalized_full, normalized_background, image_size_check = _prepare_page_images(
    full_image=source_full_image,
    background_image=source_background_image,
    project_path=project_path,
)
full_image = normalized_full
background_image = normalized_background
prepared_background = full_image if visible_image_variant == "full" else background_image
```

Then add:

```python
def _resolve_rebuild_mode(manifest: dict[str, Any]) -> str:
    contract = manifest.get("generation_contract")
    raw = manifest.get("rebuild_mode")
    if not raw and isinstance(contract, dict):
        raw = contract.get("rebuild_mode")
    mode = str(raw or "template_body_region")
    if mode not in {"full_slide", "template_body_region"}:
        raise ValueError(f"Unsupported rebuild_mode: {mode}")
    return mode
```

In `rebuild_from_manifest()`, after `manifest = load_pair_manifest(manifest_path)`, add:

```python
rebuild_mode = _resolve_rebuild_mode(manifest)
```

Add to each `quality_pages.append({...})` dict:

```python
"rebuild_mode": rebuild_mode,
```

- [ ] **Step 7: Add a focused rebuild-quality test if practical**

If a direct subprocess test is too expensive, add a small unit-style test for `_resolve_rebuild_mode()` by importing it from `scripts.dual_image_overlay.template_rebuild`. Use this code in `tests/test_dual_image_overlay_template_rebuild.py`:

```python
    def test_rebuild_mode_defaults_to_template_body_region(self) -> None:
        from scripts.dual_image_overlay.template_rebuild import _resolve_rebuild_mode

        self.assertEqual("template_body_region", _resolve_rebuild_mode({}))
        self.assertEqual("full_slide", _resolve_rebuild_mode({"rebuild_mode": "full_slide"}))
        self.assertEqual(
            "template_body_region",
            _resolve_rebuild_mode({"generation_contract": {"rebuild_mode": "template_body_region"}}),
        )
```

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_rebuild_mode_defaults_to_template_body_region
```

Expected: PASS.

- [ ] **Step 8: Commit Task 2**

Run:

```bash
git add tests/test_dual_image_overlay_template_rebuild.py scripts/dual_image_overlay/template_rebuild.py scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py
git diff --cached --check
git commit -m "feat: record dual image rebuild mode"
```

## Task 3: Verify Page 006 Behavior

**Files:**
- Read: `projects/dual-image-page006-rebuild-20260705-101012/ppt_project/analysis/page_layout_plan/page_006_layout_plan.json`
- Read: `projects/dual-image-page006-rebuild-20260705-101012/images/page_image_pairs.json`
- No production file changes expected.

- [ ] **Step 1: Run focused test suite**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q tests/test_scene_graph_layout.py tests/test_scene_graph_builder.py tests/test_scene_graph_workflow.py tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_overlay_semantic_plan.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Re-run page 006 rebuild with existing project inputs and verify normalized ingress**

Run:

```bash
PYTHONPATH=. python3 scripts/dual_image_overlay/template_rebuild.py projects/dual-image-page006-rebuild-20260705-101012/images/page_image_pairs.json --ocr-backend none --semantic-plan-dir projects/dual-image-page006-rebuild-20260705-101012/semantic_plan --visual-registry-dir projects/dual-image-page006-rebuild-20260705-101012/registry --export
```

Expected: rebuild reaches export or a later strict gate. If a later gate blocks, still verify ingress with:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from PIL import Image
project = Path("projects/dual-image-page006-rebuild-20260705-101012/ppt_project")
for path in sorted((project / "images/normalized").glob("*.png")):
    with Image.open(path) as image:
        print(path, image.size)
        assert image.size == (1280, 720)
semantic = json.loads((project / "analysis/semantic_plan/page_006_semantic_plan.json").read_text())
assert semantic["image_size"] == {"width": 1280.0, "height": 720.0}
graph_path = project / "analysis/scene_graph/page_006_scene_graph.json"
if graph_path.exists():
    context = json.loads(graph_path.read_text())["coordinate_context"]
    assert context["semantic_input_space"] == {"width": 1280.0, "height": 720.0}
    assert context["image_size"] == {"width": 1280.0, "height": 720.0}
PY
```

If readiness remains nonzero only because render preview is not attached, continue to Step 3. If it fails because `scene_graph_gate` reports unbound registry text zones, treat that as a separate strict-binding task, not a coordinate normalization failure.

- [ ] **Step 3: Attach render preview if needed**

Render latest PPTX using the same commands used previously:

```bash
PROJECT="projects/dual-image-page006-rebuild-20260705-101012/ppt_project"
PPTX="$(ls -t "$PROJECT"/exports/*.pptx | head -1)"
QA="$PROJECT/qa/render-preview"
mkdir -p "$QA/tmp"
soffice --headless --convert-to pdf --outdir "$QA/tmp" "$PPTX"
PDF="$(find "$QA/tmp" -maxdepth 1 -name '*.pdf' | head -1)"
pdftoppm -png -singlefile -r 144 "$PDF" "$QA/page-render"
cp "$PDF" "$QA/page-render.pdf"
PYTHONPATH=. python3 scripts/dual_image_overlay/template_rebuild.py projects/dual-image-page006-rebuild-20260705-101012/images/page_image_pairs.json --skip-rebuild --semantic-plan-dir projects/dual-image-page006-rebuild-20260705-101012/semantic_plan --visual-registry-dir projects/dual-image-page006-rebuild-20260705-101012/registry --rendered-preview "$QA/page-render.png"
```

Expected: `template_rebuild_readiness.json` includes `rebuild_mode` and `visual_reference_mode`.

- [ ] **Step 4: Confirm ability-card bboxes are no longer duplicated**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
path = Path("projects/dual-image-page006-rebuild-20260705-101012/ppt_project/analysis/page_layout_plan/page_006_layout_plan.json")
plan = json.loads(path.read_text())
texts = ["1", "目录管理", "• 指标/能力目录", "• 评估维度管理", "• 分类与标签管理", "• 目录版本管理"]
items = {item["text"]: item for item in plan["items"] if item.get("text") in texts}
for text in texts:
    print(text, items[text]["bbox"], items[text].get("layout_strategy"), items[text].get("layout_source"))
assert len({tuple(items[text]["bbox"]) for text in texts}) == len(texts)
assert all(items[text].get("layout_source") == "semantic_layout_plan" for text in texts)
PY
```

Expected: no assertion error; each text has a distinct bbox and `layout_source == "semantic_layout_plan"`.

- [ ] **Step 5: Run final verification**

Run:

```bash
PYTHONPATH=scripts/dual_image_overlay/rebuild_engine:. pytest -q
git status --short
```

Expected: tests pass. Git status contains only intentional changes and any explicitly excluded page 006 run artifacts.

- [ ] **Step 6: Commit verification-related tracked changes only**

If page 006 artifacts are intentionally not committed, do not stage them. Commit code/test changes if any remain:

```bash
git add scripts/dual_image_overlay/scene_graph/builder.py scripts/dual_image_overlay/scene_graph/layout.py scripts/dual_image_overlay/template_rebuild.py scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py tests/test_scene_graph_layout.py tests/test_scene_graph_builder.py tests/test_dual_image_overlay_template_rebuild.py
git diff --cached --check
git commit -m "test: verify dual image scene graph rebuild"
```

If all code changes were already committed in Tasks 1 and 2, skip this commit and report the verification evidence.

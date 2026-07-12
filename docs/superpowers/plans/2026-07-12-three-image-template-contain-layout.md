# Three Image Template Contain Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make editable three-image body pages place FULL/BACKGROUND/TEXT into a fixed template body maximum boundary with one shared contain transform and no distortion.

**Architecture:** Keep the change inside the existing template export module. Add a pure placement helper that validates the FULL canvas and maximum body boundary, returns one `x/y/width/height/scale` transform, and make both background image placement and editable text mapping consume that same transform.

**Tech Stack:** Python 3, stdlib `unittest`, PIL-based fixture images, existing SVG-to-PPTX conversion helpers.

## Global Constraints

- Scope is only `editable_text_three_image` body page template assembly.
- The fixed maximum body boundary in 1280x720 template coordinates is `x=100, y=96, width=1080, height=608`.
- FULL remains the only canonical coordinate system for the page.
- BACKGROUND image and all TEXT boxes must share one `placed_x`, `placed_y`, and uniform `scale`.
- Do not crop, pad, resample, rewrite, or otherwise modify input image files during template assembly.
- Do not use `preserveAspectRatio="none"` for editable three-image body background SVG.
- Do not silently fall back to the old independent x/y scaling behavior when canvas or body dimensions are invalid.
- Preserve ordinary non-three-image image flow, template-only pages, image generation, three-image normalization, OCR, and supplier batch behavior.
- Before editing any function, run GitNexus impact analysis for that symbol and report direct callers, affected processes, and risk.
- Before committing, run full tests, `git diff --cached --check`, and GitNexus `detect_changes()`.

---

## File Structure

- Modify `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`.
  - Add constants for the editable three-image body maximum boundary.
  - Add a pure helper `_editable_body_contain_placement(canvas, body_region)` returning a shared placement dictionary.
  - Change `_map_editable_bbox` to use a placement dictionary and uniform scale.
  - Change `render_editable_body_svg` to place the background and text from one shared placement and remove `preserveAspectRatio="none"`.
- Modify `tests/test_dual_image_template_body_region.py`.
  - Replace the old independent-scaling bbox expectation with contain-placement expectations.
  - Add SVG assertions for the fixed maximum boundary, shared transform, no distortion, and no `preserveAspectRatio="none"`.
  - Add invalid-canvas and invalid-body failure tests.

### Task 1: Shared Contain Placement Helper

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`
- Test: `tests/test_dual_image_template_body_region.py`

**Interfaces:**
- Consumes: `canvas: dict[str, int]` with `width` and `height`; `body_region: dict[str, int]`.
- Produces: `_editable_body_contain_placement(canvas: dict[str, int], body_region: dict[str, int]) -> dict[str, float]` with keys `x`, `y`, `width`, `height`, and `scale`.
- Produces: `_map_editable_bbox(bbox: dict[str, float], placement: dict[str, float]) -> dict[str, float]`.

- [ ] **Step 1: Run GitNexus impact analysis before editing symbols**

Run:

```bash
node .gitnexus/run.cjs impact --target _map_editable_bbox --direction upstream
node .gitnexus/run.cjs impact --target render_editable_body_svg --direction upstream
```

Expected: report the direct callers, affected processes, and risk level to the user. If either result is HIGH or CRITICAL, stop and get explicit permission before editing.

- [ ] **Step 2: Write failing tests for contain placement and validation**

In `tests/test_dual_image_template_body_region.py`, replace `test_editable_bbox_maps_to_full_body_region_without_letterboxing` with:

```python
    def test_editable_body_contain_placement_uses_fixed_maximum_region(self) -> None:
        module = load_template_image_ppt_export()

        placement = module._editable_body_contain_placement(
            {"width": 1680, "height": 944},
            {"x": 20, "y": 104, "width": 1240, "height": 592},
        )

        self.assertEqual(100.0, placement["x"])
        self.assertAlmostEqual(96.5714285714, placement["y"], places=6)
        self.assertEqual(1080.0, placement["width"])
        self.assertAlmostEqual(606.8571428571, placement["height"], places=6)
        self.assertAlmostEqual(1080 / 1680, placement["scale"], places=10)
```

Add this test immediately after it:

```python
    def test_editable_bbox_maps_with_shared_uniform_contain_scale(self) -> None:
        module = load_template_image_ppt_export()
        placement = module._editable_body_contain_placement(
            {"width": 1680, "height": 944},
            {"x": 20, "y": 104, "width": 1240, "height": 592},
        )

        mapped = module._map_editable_bbox(
            {"x": 100, "y": 120, "width": 300, "height": 80},
            placement,
        )

        scale = 1080 / 1680
        self.assertEqual(
            {
                "x": 100.0 + 100 * scale,
                "y": 96.5714285714 + 120 * scale,
                "width": 300 * scale,
                "height": 80 * scale,
            },
            mapped,
        )
```

Add validation tests near the mapping tests:

```python
    def test_editable_body_contain_placement_rejects_invalid_full_canvas(self) -> None:
        module = load_template_image_ppt_export()

        with self.assertRaisesRegex(ValueError, "invalid editable canvas"):
            module._editable_body_contain_placement(
                {"width": 0, "height": 944},
                {"x": 20, "y": 104, "width": 1240, "height": 592},
            )

    def test_editable_body_contain_placement_rejects_invalid_body_region(self) -> None:
        module = load_template_image_ppt_export()

        with self.assertRaisesRegex(ValueError, "invalid editable body region"):
            module._editable_body_contain_placement(
                {"width": 1680, "height": 944},
                {"x": 20, "y": 104, "width": 0, "height": 592},
            )
```

- [ ] **Step 3: Run tests and verify they fail for missing helper/signature**

Run:

```bash
python3 -m pytest tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_contain_placement_uses_fixed_maximum_region tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_bbox_maps_with_shared_uniform_contain_scale tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_contain_placement_rejects_invalid_full_canvas tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_contain_placement_rejects_invalid_body_region -q
```

Expected: FAIL because `_editable_body_contain_placement` is not defined and `_map_editable_bbox` still expects `(bbox, canvas, body)`.

- [ ] **Step 4: Implement the pure helper and shared bbox mapper**

In `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`, add the constant near the other layout constants:

```python
EDITABLE_BODY_MAX_REGION = {"x": 100, "y": 96, "width": 1080, "height": 608}
```

Replace `_map_editable_bbox` with:

```python
def _editable_body_contain_placement(canvas: dict[str, int], body_region: dict[str, int]) -> dict[str, float]:
    canvas_width = float(canvas.get("width", 0) or 0)
    canvas_height = float(canvas.get("height", 0) or 0)
    if canvas_width <= 0 or canvas_height <= 0:
        raise ValueError("invalid editable canvas: width and height must be positive")

    max_region = {
        "x": float(EDITABLE_BODY_MAX_REGION["x"]),
        "y": float(EDITABLE_BODY_MAX_REGION["y"]),
        "width": float(EDITABLE_BODY_MAX_REGION["width"]),
        "height": float(EDITABLE_BODY_MAX_REGION["height"]),
    }
    if max_region["width"] <= 0 or max_region["height"] <= 0:
        raise ValueError("invalid editable body region: width and height must be positive")

    scale = min(max_region["width"] / canvas_width, max_region["height"] / canvas_height)
    placed_width = canvas_width * scale
    placed_height = canvas_height * scale
    return {
        "x": max_region["x"] + (max_region["width"] - placed_width) / 2,
        "y": max_region["y"] + (max_region["height"] - placed_height) / 2,
        "width": placed_width,
        "height": placed_height,
        "scale": scale,
    }


def _map_editable_bbox(bbox: dict[str, float], placement: dict[str, float]) -> dict[str, float]:
    scale = placement["scale"]
    return {
        "x": placement["x"] + bbox["x"] * scale,
        "y": placement["y"] + bbox["y"] * scale,
        "width": bbox["width"] * scale,
        "height": bbox["height"] * scale,
    }
```

- [ ] **Step 5: Run focused helper tests and verify pass**

Run:

```bash
python3 -m pytest tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_contain_placement_uses_fixed_maximum_region tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_bbox_maps_with_shared_uniform_contain_scale tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_contain_placement_rejects_invalid_full_canvas tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_contain_placement_rejects_invalid_body_region -q
```

Expected: PASS.

### Task 2: Render Editable SVG With One Shared Transform

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`
- Test: `tests/test_dual_image_template_body_region.py`

**Interfaces:**
- Consumes: `_editable_body_contain_placement(canvas, body_region)` from Task 1.
- Consumes: `_map_editable_bbox(bbox, placement)` from Task 1.
- Produces: `render_editable_body_svg(page, body_region, canvas) -> str` where the background image and all text boxes share the same uniform transform.

- [ ] **Step 1: Write failing SVG behavior tests**

Add this test after `test_editable_body_svg_uses_json_run_style`:

```python
    def test_editable_body_svg_places_background_with_contain_not_stretch(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            background = Path(tmp) / "background.png"
            Image.new("RGB", (1680, 944), "white").save(background)
            svg = module.render_editable_body_svg(
                {
                    "page_number": 4,
                    "background_path": background,
                    "canvas": {"width": 1680, "height": 944},
                    "text_lines": [
                        {
                            "line_id": "L1",
                            "text": "对齐文字",
                            "bbox_px": {"x": 100, "y": 120, "width": 300, "height": 80},
                            "runs": [
                                {
                                    "text": "对齐文字",
                                    "style": {"font_size_px": 40, "color": "#12355B"},
                                }
                            ],
                        }
                    ],
                },
                {"x": 20, "y": 104, "width": 1240, "height": 592},
                {"width": 1680, "height": 944},
            )

        self.assertIn('x="100"', svg)
        self.assertIn('y="96.571"', svg)
        self.assertIn('width="1080"', svg)
        self.assertIn('height="606.857"', svg)
        self.assertNotIn('preserveAspectRatio="none"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn('data-pptx-width="192.857"', svg)
        self.assertIn('font-size="25.714"', svg)
```

Add this test near `test_write_project_marks_editable_body_pages_without_changing_default_tasks`:

```python
    def test_write_project_editable_body_uses_fixed_contain_region(self) -> None:
        module = load_template_image_ppt_export()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            full_path = root / "full.png"
            background_path = root / "background.png"
            Image.new("RGB", (1680, 944), "#ffffff").save(full_path)
            Image.new("RGB", (1680, 944), "#12355b").save(background_path)
            before_hash = full_path.read_bytes()
            page_json = root / "page.json"
            page_json.write_text(
                json.dumps(
                    {
                        "page": {"page_id": "page-004", "width_px": 1680, "height_px": 944},
                        "images": {"background": {"path": str(background_path), "width_px": 1680, "height_px": 944}},
                        "text_lines": [{"line_id": "T01-L01", "text": "可编辑", "bbox": {"x": 100, "y": 120, "width": 300, "height": 80}}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            editable_manifest = root / "editable_text_result.json"
            editable_manifest.write_text(
                json.dumps({"pages": {"4": {"page_number": 4, "status": "passed", "page_json": str(page_json), "background_path": str(background_path)}}}),
                encoding="utf-8",
            )
            output = module.write_project(
                {
                    "canvas": {"width": 1280, "height": 720},
                    "body_region": {"x": 20, "y": 104, "width": 1240, "height": 592},
                    "tasks": [
                        {
                            "page_number": 4,
                            "page_role": "body",
                            "title": "测试页",
                            "slide_title": "测试页",
                            "subtitle": "",
                            "body_text": "",
                            "render_mode": "content-image",
                            "editable_body": True,
                            "image_path": str(full_path),
                            "prompt": "正文",
                            "size": "1240x592",
                            "notes_text": "备注",
                        }
                    ],
                    "editable_body_manifest": str(editable_manifest),
                },
                root / "output",
                "editable",
            )
            svg_text = (output / "svg_output" / "page_004_测试页.svg").read_text(encoding="utf-8")

        self.assertEqual(before_hash, full_path.read_bytes())
        self.assertIn('x="100"', svg_text)
        self.assertIn('width="1080"', svg_text)
        self.assertNotIn('preserveAspectRatio="none"', svg_text)
```

- [ ] **Step 2: Run SVG tests and verify they fail on old stretching behavior**

Run:

```bash
python3 -m pytest tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_svg_places_background_with_contain_not_stretch tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_write_project_editable_body_uses_fixed_contain_region -q
```

Expected: FAIL because current SVG uses body region `20,104,1240,592`, includes `preserveAspectRatio="none"`, and uses independent `scale_x`/`scale_y`.

- [ ] **Step 3: Update SVG rendering to consume shared placement**

In `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`, replace the start of `render_editable_body_svg` through the text mapping setup with:

```python
def render_editable_body_svg(page: dict, body_region: dict[str, int], canvas: dict[str, int]) -> str:
    """Render a background plus stable, native-convertible SVG text boxes."""

    background = Path(page["background_path"])
    if not background.is_file():
        raise FileNotFoundError(f"editable background is missing: {background}")
    image_href = "../images/" + background.name
    placement = _editable_body_contain_placement(canvas, body_region)
    parts = [
        f'<image x="{fmt(placement["x"])}" y="{fmt(placement["y"])}" '
        f'width="{fmt(placement["width"])}" height="{fmt(placement["height"])}" '
        f'href={quoteattr(image_href)} xlink:href={quoteattr(image_href)} '
        f'preserveAspectRatio="xMidYMid meet"/>',
    ]
    scale = placement["scale"]
    for line in page["text_lines"]:
        mapped = _map_editable_bbox(line["bbox_px"], placement)
```

In the same function, replace the existing `scale_y` multiplier in `run_font_sizes` with the shared scale:

```python
        run_font_sizes = [
            max(6.5, _editable_style_font_size_px(style, mapped["height"] * 0.75) * scale)
            for style in run_styles
        ]
```

- [ ] **Step 4: Run focused SVG tests and verify pass**

Run:

```bash
python3 -m pytest tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_editable_body_svg_places_background_with_contain_not_stretch tests/test_dual_image_template_body_region.py::DualImageTemplateBodyRegionTest::test_write_project_editable_body_uses_fixed_contain_region -q
```

Expected: PASS.

- [ ] **Step 5: Run the full affected test file**

Run:

```bash
python3 -m pytest tests/test_dual_image_template_body_region.py -q
```

Expected: PASS for the full file. If old tests assert the former `20,104,1240,592` editable body SVG behavior, update only the editable three-image expectations to the fixed contain region; do not change non-editable content image crop tests.

### Task 3: Final Verification and Commit

**Files:**
- Verify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`
- Verify: `tests/test_dual_image_template_body_region.py`

**Interfaces:**
- Consumes: completed Task 1 and Task 2.
- Produces: one focused commit containing only the template contain layout implementation and tests.

- [ ] **Step 1: Run full test suite**

Run:

```bash
python3 -m pytest
```

Expected: PASS.

- [ ] **Step 2: Check staged diff whitespace before commit**

Run:

```bash
git add scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py tests/test_dual_image_template_body_region.py docs/superpowers/plans/2026-07-12-three-image-template-contain-layout.md
git diff --cached --check
```

Expected: no output and exit code 0.

- [ ] **Step 3: Run GitNexus change detection**

Run:

```bash
node .gitnexus/run.cjs detect_changes --scope staged
```

Expected: changed symbols limited to the editable body placement/rendering helper area and the related tests. If unrelated files or flows appear, unstage them and inspect before committing.

- [ ] **Step 4: Commit only the intended files**

Run:

```bash
git commit -m "fix: contain editable three-image template body"
```

Expected: one commit on `codex/three-image-style-recovery` containing only:

```text
docs/superpowers/plans/2026-07-12-three-image-template-contain-layout.md
scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py
tests/test_dual_image_template_body_region.py
```

## Self-Review

- Spec coverage: the plan covers fixed maximum boundary, FULL canonical coordinate use, shared contain transform, no background/text independent scaling, no `preserveAspectRatio="none"`, no crop/pad/rewrite, invalid-dimension failure, and unchanged non-editable/template flows.
- Placeholder scan: no TODO/TBD/implement-later placeholders remain.
- Type consistency: `_editable_body_contain_placement` returns the same `placement` shape consumed by `_map_editable_bbox` and `render_editable_body_svg`.

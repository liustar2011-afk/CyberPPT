# Three-Image Joint Text Style Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the existing three-image pipeline so FULL, BACKGROUND, TEXT, and OCR jointly produce style-enriched JSON and native editable PowerPoint text with recovered color, font size, weight, runs, and alignment.

**Architecture:** Keep the existing `TEXT -> OCR -> page.json -> PPTX` flow. Insert one deterministic style-recovery stage after OCR normalization and before `build_page_spec`; it uses TEXT for glyph geometry, `FULL - BACKGROUND` for visible text pixels and color, BACKGROUND containers for alignment, and installed Microsoft YaHei faces for font fitting. Emit backward-compatible page JSON, then make both the vendored renderer and CyberPPT template assembler consume the same enriched fields.

**Tech Stack:** Python 3, Pillow (`Image`, `ImageChops`, `ImageDraw`, `ImageFont`), JSON Schema, PptxGenJS, existing SVG-to-DrawingML converter, pytest.

## Global Constraints

- Do not change canvas resolution or aspect-ratio handling; that work is owned by a separate task/window.
- FULL, BACKGROUND, and TEXT must already be registered to the same pixel coordinate system.
- BACKGROUND remains one flattened raster image; recognized text is native and editable.
- Preserve one visual line per editable text object unless the JSON explicitly groups paragraphs.
- Use Microsoft YaHei as the default font family and resolve Light, Regular, and Bold faces by weight.
- No OpenCV or NumPy dependency; use Pillow and standard-library code only.
- Every inferred style field must include method, confidence, and fallback provenance.
- Low-confidence style recovery produces `review`, not silent fallback approval.
- Existing `page.json` files without enriched layout/style fields must remain readable.

---

## File Structure

- Create `vendor/three-image-to-ppt/scripts/recover_text_styles.py`: image differencing, foreground masks, color recovery, font fitting, run segmentation, and alignment recovery.
- Create `vendor/three-image-to-ppt/scripts/font_resolver.py`: resolve Microsoft YaHei Light/Regular/Bold files without hardcoding a single TTC index.
- Modify `vendor/three-image-to-ppt/scripts/models.py`: add optional line layout and style-evidence fields while retaining v1.0 loading.
- Modify `vendor/three-image-to-ppt/assets/schemas/text-line.schema.json`: validate canonical layout, run style, and evidence fields.
- Modify `vendor/three-image-to-ppt/assets/schemas/page.schema.json`: validate enriched lines and accept schema versions 1.0 and 1.1.
- Modify `vendor/three-image-to-ppt/scripts/build_page_json.py`: serialize the enriched text lines without discarding mapping/correction evidence.
- Modify `vendor/three-image-to-ppt/scripts/run_pipeline.py`: call style recovery only in three-image mode and record review findings.
- Modify `vendor/three-image-to-ppt/scripts/render_ppt.mjs`: consume line alignment, vertical alignment, margins, rotation, and mixed run styles.
- Modify `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`: consume the same enriched JSON in CyberPPT assembly, including mixed `<tspan>` styles and alignment.
- Create `vendor/three-image-to-ppt/scripts/qa_text_style.py`: per-line color, mask, fit, contrast, and overflow QA.
- Add tests under `vendor/three-image-to-ppt/tests/` and `tests/test_dual_image_template_body_region.py`.

---

### Task 1: Extend the JSON Contract Without Breaking Existing Pages

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/models.py`
- Modify: `vendor/three-image-to-ppt/assets/schemas/text-line.schema.json`
- Modify: `vendor/three-image-to-ppt/assets/schemas/page.schema.json`
- Modify: `vendor/three-image-to-ppt/tests/test_page_json.py`

**Interfaces:**
- Consumes: existing `TextLine`, `TextRun`, and page schema v1.0.
- Produces: `TextLayout`, `StyleEvidence`, `TextLine.layout`, `TextLine.style_evidence`, and page schema v1.1.

- [ ] **Step 1: Write failing model round-trip tests**

```python
def test_page_json_round_trips_enriched_layout_and_style_evidence(tmp_path, sample_page):
    line = replace(
        sample_page.text_lines[0],
        layout={
            "align": "center",
            "valign": "top",
            "wrap": False,
            "margin_px": 0,
            "rotation_deg": 0,
        },
        style_evidence={
            "color": {"method": "full_background_delta", "confidence": 0.94},
            "font": {"method": "glyph_fit", "confidence": 0.88},
        },
    )
    path = write_page_spec(replace(sample_page, text_lines=(line,), schema_version="1.1"), tmp_path / "page.json")
    loaded = load_page_spec(path)
    assert loaded.text_lines[0].layout["align"] == "center"
    assert loaded.text_lines[0].style_evidence["color"]["method"] == "full_background_delta"
```

- [ ] **Step 2: Run the test and verify the contract is missing**

Run:

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_page_json.py::test_page_json_round_trips_enriched_layout_and_style_evidence
```

Expected: FAIL because `TextLine` has no `layout` or `style_evidence` fields.

- [ ] **Step 3: Add optional fields to `TextLine`**

```python
@dataclass(frozen=True)
class TextLine:
    line_id: str
    group_id: str
    line_index: int
    text: str
    bbox: BBox
    polygon: tuple[tuple[int, int], ...]
    confidence: float
    runs: tuple[TextRun, ...] = ()
    layout: Mapping[str, Any] = field(default_factory=dict)
    style_evidence: Mapping[str, Any] = field(default_factory=dict)
```

Update `to_dict()` and `_text_line_from_dict()` to preserve both optional mappings. Keep missing fields as `{}`.

- [ ] **Step 4: Extend schemas with exact allowed layout values**

Add optional `layout` with:

```json
{
  "align": {"enum": ["left", "center", "right"]},
  "valign": {"enum": ["top", "middle", "bottom"]},
  "wrap": {"type": "boolean"},
  "margin_px": {"type": "number", "minimum": 0},
  "rotation_deg": {"type": "number", "minimum": -360, "maximum": 360}
}
```

Allow `schema_version` values `1.0` and `1.1`; emit `1.1` only when enrichment runs.

- [ ] **Step 5: Run page JSON tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_page_json.py
```

Expected: all tests PASS, including existing v1.0 fixture round trips.

- [ ] **Step 6: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/models.py vendor/three-image-to-ppt/assets/schemas vendor/three-image-to-ppt/tests/test_page_json.py
git commit -m "feat: extend three-image text style schema"
```

---

### Task 2: Resolve Microsoft YaHei Faces by Requested Weight

**Files:**
- Create: `vendor/three-image-to-ppt/scripts/font_resolver.py`
- Create: `vendor/three-image-to-ppt/tests/test_font_resolver.py`

**Interfaces:**
- Consumes: font family and weight.
- Produces: `resolve_font_face(family: str, weight: str) -> Path`.

- [ ] **Step 1: Write failing resolver tests**

```python
def test_resolve_yahei_faces_selects_distinct_regular_and_bold_files():
    regular = resolve_font_face("Microsoft YaHei", "regular")
    bold = resolve_font_face("Microsoft YaHei", "bold")
    assert regular.is_file()
    assert bold.is_file()
    assert regular != bold
```

Add a mocked `fc-match` test that maps regular to `msyh.ttc`, light to `msyhl.ttc`, and bold to `msyhbd.ttc`.

- [ ] **Step 2: Verify failure**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_font_resolver.py
```

Expected: FAIL because `font_resolver.py` does not exist.

- [ ] **Step 3: Implement resolver with cache and explicit failure**

```python
@lru_cache(maxsize=32)
def resolve_font_face(family: str, weight: str) -> Path:
    query = f"{family}:weight={weight}"
    result = subprocess.run(
        ["fc-match", "-f", "%{file}\n", query],
        check=True,
        text=True,
        capture_output=True,
    )
    path = Path(result.stdout.splitlines()[0]).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"font face is unavailable: {family} {weight}")
    return path
```

Do not silently substitute another family; style recovery must mark a review item when the requested family is unavailable.

- [ ] **Step 4: Run tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_font_resolver.py
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/font_resolver.py vendor/three-image-to-ppt/tests/test_font_resolver.py
git commit -m "feat: resolve Chinese font faces by weight"
```

---

### Task 3: Recover Foreground Masks and Text Color from FULL/BACKGROUND/TEXT

**Files:**
- Create: `vendor/three-image-to-ppt/scripts/recover_text_styles.py`
- Create: `vendor/three-image-to-ppt/tests/test_recover_text_styles.py`
- Create: `vendor/three-image-to-ppt/tests/fixtures/style-recovery/README.md`

**Interfaces:**
- Consumes: registered RGB/RGBA FULL, BACKGROUND, TEXT images and one line bbox.
- Produces: `recover_line_color(...) -> RecoveredColor` and `build_text_mask(...) -> Image.Image`.

- [ ] **Step 1: Create deterministic synthetic fixture tests**

Generate fixtures inside the test with Pillow: a navy rectangle with white text, a white card with navy text, and a white card with green highlighted numbers. Do not commit binary fixtures.

```python
def test_color_recovery_uses_full_background_delta_for_white_on_blue(tmp_path):
    full, background, text = make_fixture(tmp_path, background="#12355B", text_color="#FFFFFF")
    recovered = recover_line_color(full, background, text, BBox(20, 20, 240, 50))
    assert recovered.hex_color == "#FFFFFF"
    assert recovered.method == "full_background_delta"
    assert recovered.confidence >= 0.85
```

Add equivalent tests for `#12355B` and `#2A7F2E`.

- [ ] **Step 2: Verify failure**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_recover_text_styles.py -k color
```

Expected: FAIL because recovery functions do not exist.

- [ ] **Step 3: Implement the TEXT geometry mask**

Use grayscale distance from the dominant TEXT crop background, remove isolated one-pixel noise, and return an `L` mask. Use `ImageChops.difference`, `Image.point`, and a 3x3 median filter; no NumPy.

```python
def build_text_mask(text_image: Image.Image, bbox: BBox) -> Image.Image:
    crop = text_image.crop((bbox.x, bbox.y, bbox.x + bbox.width, bbox.y + bbox.height)).convert("RGB")
    background = dominant_border_color(crop)
    flat = Image.new("RGB", crop.size, background)
    delta = ImageChops.difference(crop, flat).convert("L")
    return delta.point(lambda value: 255 if value >= 18 else 0).filter(ImageFilter.MedianFilter(3))
```

- [ ] **Step 4: Implement FULL/BACKGROUND color recovery**

Within the mask, keep pixels where `ImageChops.difference(FULL, BACKGROUND)` exceeds 18. Quantize those FULL pixels to at most four colors, discard clusters covering under 5%, and select the cluster with the highest mask coverage. Return confidence from coverage, cluster dominance, and contrast against the BACKGROUND crop.

If fewer than 20 valid pixels remain, fall back to the TEXT foreground color with method `text_fallback` and confidence below 0.60 so QA requires review.

- [ ] **Step 5: Run color tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_recover_text_styles.py -k color
```

Expected: PASS for white, navy, and green text; fallback test reports confidence below 0.60.

- [ ] **Step 6: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/recover_text_styles.py vendor/three-image-to-ppt/tests/test_recover_text_styles.py vendor/three-image-to-ppt/tests/fixtures/style-recovery/README.md
git commit -m "feat: recover text colors from three registered images"
```

---

### Task 4: Fit Font Size, Weight, Runs, and Alignment

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/recover_text_styles.py`
- Modify: `vendor/three-image-to-ppt/tests/test_recover_text_styles.py`

**Interfaces:**
- Consumes: OCR text, glyph mask, bbox, recovered foreground colors, container bbox, and font face resolver.
- Produces: `recover_line_style(...) -> TextLine` with canonical runs and layout.

- [ ] **Step 1: Write failing font-fit tests**

```python
def test_font_fit_distinguishes_regular_and_bold_yahei(tmp_path):
    fixture = render_text_fixture(tmp_path, "103682", size_px=48, weight="bold", color="#12355B")
    result = fit_font_style("103682", fixture.mask, fixture.bbox, "Microsoft YaHei")
    assert result.weight == "bold"
    assert abs(result.font_size_px - 48) <= 2
    assert result.confidence >= 0.80
```

Add a regular-body test and a light-face test.

- [ ] **Step 2: Implement bounded candidate fitting**

Search font size from `0.55 * bbox.height` through `1.05 * bbox.height` in one-pixel steps for Light, Regular, and Bold. Render each candidate into the bbox and score:

```python
score = 0.55 * mask_iou + 0.25 * width_similarity + 0.20 * height_similarity
```

Choose the highest score. Record all three components in `style_evidence.font`.

- [ ] **Step 3: Write failing alignment tests**

```python
@pytest.mark.parametrize(
    ("bbox", "container", "expected"),
    [
        (BBox(110, 20, 80, 20), BBox(0, 0, 300, 80), "center"),
        (BBox(16, 20, 180, 20), BBox(0, 0, 300, 80), "left"),
        (BBox(104, 20, 180, 20), BBox(0, 0, 300, 80), "right"),
    ],
)
def test_recover_alignment(bbox, container, expected):
    assert recover_alignment(bbox, container).align == expected
```

- [ ] **Step 4: Implement alignment against the containing BACKGROUND region**

Use normalized edge/center distances with a tolerance of 6% of container width. Prefer center when center distance is within tolerance; otherwise choose the nearer padded edge. Emit confidence from the gap between the best and second-best candidate.

- [ ] **Step 5: Write and implement mixed-run recovery tests**

Use the reference pattern `103682 亿千瓦时，`: numeric foreground is 48px navy bold, suffix is 22px dark regular. Segment connected glyph components left-to-right, map OCR character spans by cumulative rendered width, and split a run only when color distance exceeds 24 RGB units, fitted size changes by at least 20%, or weight changes.

Expected JSON:

```json
[
  {"text": "103682", "style": {"font_family": "Microsoft YaHei", "font_size_px": 48, "weight": "bold", "color": "#12355B"}},
  {"text": " 亿千瓦时，", "style": {"font_family": "Microsoft YaHei", "font_size_px": 22, "weight": "regular", "color": "#101820"}}
]
```

- [ ] **Step 6: Run recovery tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_recover_text_styles.py
```

Expected: all color, font, run, and alignment tests PASS.

- [ ] **Step 7: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/recover_text_styles.py vendor/three-image-to-ppt/tests/test_recover_text_styles.py
git commit -m "feat: recover editable text typography and alignment"
```

---

### Task 5: Integrate Recovery into the Three-Image Pipeline

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/run_pipeline.py`
- Modify: `vendor/three-image-to-ppt/scripts/build_page_json.py`
- Modify: `vendor/three-image-to-ppt/tests/test_pipeline.py`

**Interfaces:**
- Consumes: `recover_page_styles(full, background, text, lines, containers) -> StyleRecoveryResult`.
- Produces: schema v1.1 `page.json` and style-related QA review items.

- [ ] **Step 1: Write failing integration test**

```python
def test_three_image_pipeline_enriches_page_json_with_style_and_layout(tmp_path):
    result = run_three_image_fixture(tmp_path)
    page = json.loads(result.page_json.read_text(encoding="utf-8"))
    line = page["text_lines"][0]
    assert page["schema_version"] == "1.1"
    assert line["layout"]["align"] in {"left", "center", "right"}
    assert line["runs"][0]["style"]["color"].startswith("#")
    assert "style_evidence" in line
```

- [ ] **Step 2: Verify failure**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_pipeline.py::test_three_image_pipeline_enriches_page_json_with_style_and_layout
```

Expected: FAIL because the pipeline currently passes normalized OCR directly to `build_page_spec`.

- [ ] **Step 3: Insert the recovery call**

After `normalize_ocr(...)` and container creation:

```python
recovery = recover_page_styles(
    full_path=args.full,
    background_path=args.background,
    text_path=ocr_image,
    lines=lines,
    containers=[canvas_container],
)
lines = recovery.lines
```

Use schema v1.1 in three-image mode. Keep two-image mode on v1.0 unless style data is already present in OCR runs.

- [ ] **Step 4: Add review routing**

Append one QA review item per line when color, font, or alignment confidence is below 0.70. Mark failed only for invalid data, empty runs, non-finite geometry, or text mismatch; low visual confidence remains reviewable.

- [ ] **Step 5: Run pipeline tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_pipeline.py vendor/three-image-to-ppt/tests/test_page_json.py
```

Expected: PASS, and existing two-image tests remain unchanged.

- [ ] **Step 6: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/run_pipeline.py vendor/three-image-to-ppt/scripts/build_page_json.py vendor/three-image-to-ppt/tests/test_pipeline.py
git commit -m "feat: enrich three-image page JSON before rendering"
```

---

### Task 6: Render the Enriched JSON in Both PPTX Paths

**Files:**
- Modify: `vendor/three-image-to-ppt/scripts/render_ppt.mjs`
- Modify: `vendor/three-image-to-ppt/tests/test_pipeline.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py`
- Modify: `tests/test_dual_image_template_body_region.py`

**Interfaces:**
- Consumes: enriched `TextLine.layout` and `TextLine.runs[].style`.
- Produces: native PPT text boxes with stable object names, zero margin, no wrap, alignment, rotation, and mixed run formatting.

- [ ] **Step 1: Write failing vendored renderer assertions**

Extend the existing mixed-run PPTX test to inspect XML and require:

```python
assert '<a:pPr algn="ctr"' in slide_xml
assert '<a:latin typeface="Microsoft YaHei"' in slide_xml
assert '<a:srgbClr val="12355B"' in slide_xml
assert '<a:srgbClr val="101820"' in slide_xml
assert 'sz="3600"' in slide_xml
assert 'sz="1620"' in slide_xml
```

- [ ] **Step 2: Update `render_ppt.mjs`**

Map canonical fields:

```javascript
const alignment = { left: "left", center: "center", right: "right" };
const vertical = { top: "top", middle: "mid", bottom: "bottom" };

slide.addText(textRuns(line), {
  ...linePosition(line, pageSpec.page),
  align: alignment[line.layout?.align ?? "left"],
  valign: vertical[line.layout?.valign ?? "top"],
  margin: line.layout?.margin_px ?? 0,
  rotate: line.layout?.rotation_deg ?? 0,
  wrap: line.layout?.wrap ?? false,
  fit: "none",
});
```

- [ ] **Step 3: Write failing CyberPPT SVG assertions**

```python
def test_editable_body_svg_renders_mixed_runs_and_center_alignment():
    svg = render_fixture_line(
        layout={"align": "center", "valign": "top", "wrap": False, "margin_px": 0},
        runs=[
            {"text": "103682", "style": {"font_size_px": 48, "weight": "bold", "color": "#12355B"}},
            {"text": " 亿千瓦时", "style": {"font_size_px": 22, "weight": "regular", "color": "#101820"}},
        ],
    )
    assert 'text-anchor="middle"' in svg
    assert '<tspan' in svg
    assert 'fill="#12355B"' in svg
    assert 'fill="#101820"' in svg
```

- [ ] **Step 4: Update the CyberPPT assembler**

Preserve all runs instead of applying only the first run style. For center/right alignment, set the parent x coordinate to bbox center/right and use SVG `text-anchor="middle"`/`"end"`. Emit one `<tspan>` per run with its own family, size, weight, and fill. Keep `data-pptx-width`, stable object name, zero inset, and no wrapping.

- [ ] **Step 5: Run renderer tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_pipeline.py
PYTHONPATH=. pytest -q tests/test_dual_image_template_body_region.py
```

Expected: PASS in both vendor and CyberPPT assembly paths.

- [ ] **Step 6: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/render_ppt.mjs vendor/three-image-to-ppt/tests/test_pipeline.py scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py tests/test_dual_image_template_body_region.py
git commit -m "feat: render recovered native text styles"
```

---

### Task 7: Add Text-Specific QA and Manual-Correction Evidence

**Files:**
- Create: `vendor/three-image-to-ppt/scripts/qa_text_style.py`
- Create: `vendor/three-image-to-ppt/tests/test_qa_text_style.py`
- Modify: `vendor/three-image-to-ppt/scripts/run_pipeline.py`
- Modify: `vendor/three-image-to-ppt/references/qa-rules.md`

**Interfaces:**
- Consumes: rendered slide PNG, FULL, BACKGROUND, and enriched page JSON.
- Produces: per-line QA metrics and page `passed`/`review`/`failed` status.

- [ ] **Step 1: Write failing QA tests**

```python
def test_text_style_qa_reports_color_and_mask_similarity():
    report = compare_text_line(rendered, full, background, line)
    assert report["mask_iou"] >= 0.55
    assert report["color_distance_rgb"] <= 24
    assert report["contrast_ratio"] >= 3.0
    assert report["overflow"] is False
```

Add tests where a dark-on-dark line becomes `review` and an overflowing text box becomes `failed`.

- [ ] **Step 2: Implement per-line metrics**

For each target bbox:

- extract rendered and FULL text foreground relative to BACKGROUND;
- calculate binary mask IoU;
- calculate dominant RGB distance;
- calculate WCAG-style foreground/background contrast;
- reuse the existing PowerPoint overflow test result;
- record inferred style confidence and manual corrections.

- [ ] **Step 3: Define exact routing**

Use:

```text
passed: mask_iou >= 0.55, color_distance_rgb <= 24, contrast_ratio >= 3.0, no overflow
review: valid editable text but one visual metric misses its pass threshold
failed: missing text, text mismatch, invalid bbox, unreadable image, or overflow
```

Do not replace the existing full-page visual diff; add this report beside it so manual reviewers know which line to adjust.

- [ ] **Step 4: Integrate into `run_pipeline.py`**

Write `text_style_qa.json` next to `page.json` and merge its review/failed items into `qa.json`, keyed by stable `line_id`.

- [ ] **Step 5: Run QA tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests/test_qa_text_style.py vendor/three-image-to-ppt/tests/test_pipeline.py
```

Expected: PASS; review output names the exact affected line.

- [ ] **Step 6: Commit**

```bash
git add vendor/three-image-to-ppt/scripts/qa_text_style.py vendor/three-image-to-ppt/tests/test_qa_text_style.py vendor/three-image-to-ppt/scripts/run_pipeline.py vendor/three-image-to-ppt/references/qa-rules.md
git commit -m "feat: add line-level editable text visual QA"
```

---

### Task 8: Validate Against the User Reference and Current Project

**Files:**
- Modify only if failures require targeted fixes from Tasks 1-7.
- Read-only reference: `/Volumes/DOC/page_004_editable_text_overlay.pptx`
- Project assets: `projects/power-supply-demand-forecast-0712/workbench/stages/02-blueprint-dual-image/editable_text/`

**Interfaces:**
- Consumes: completed style-recovery pipeline.
- Produces: evidence that the enriched JSON and assembled PPTX are usable before manual adjustment.

- [ ] **Step 1: Run all focused tests**

```bash
PYTHONPATH=vendor/three-image-to-ppt pytest -q vendor/three-image-to-ppt/tests
PYTHONPATH=. pytest -q tests/test_editable_text_three_image.py tests/test_dual_image_template_body_region.py tests/test_produce.py tests/test_qa_render_page.py
```

Expected: all tests PASS.

- [ ] **Step 2: Re-run the existing three-image assets without regenerating images**

```bash
python3 -m cyberppt produce editable-text projects/power-supply-demand-forecast-0712 --pages 1-19 --input-mode three-image
python3 -m cyberppt produce assemble projects/power-supply-demand-forecast-0712 --pages 1-19
python3 -m cyberppt produce verify projects/power-supply-demand-forecast-0712 --pages 1-19
```

Expected: page JSON schema v1.1, native editable text, no overflow, and review findings tied to line IDs. Existing FULL/BACKGROUND/TEXT files are reused.

- [ ] **Step 3: Compare recovered style distribution with the reference PPTX**

The reference contains one raster background and 37 native text boxes. Confirm the produced page supports:

- mixed numeric/unit runs;
- Microsoft YaHei Regular/Bold selection;
- navy `#12355B`, dark `#101820`/`#202020`, green `#2A7F2E`, and white `#FFFFFF` text;
- left and center alignment;
- zero margin and no wrap.

- [ ] **Step 4: Inspect rendered slides**

Render the delivery PPTX with the workspace LibreOffice wrapper and inspect every editable body page for overlaps, low contrast, and misplaced text. Record remaining manual adjustments by `page`, `line_id`, and recommended correction.

- [ ] **Step 5: Run repository-wide tests and change detection**

```bash
PYTHONPATH=. pytest -q
node .gitnexus/run.cjs detect-changes
```

Expected: tests PASS; affected flows are limited to three-image conversion, editable body assembly, and production verification.

- [ ] **Step 6: Final commit**

```bash
git add vendor/three-image-to-ppt scripts/dual_image_overlay/rebuild_engine/template_image_ppt_export.py tests docs/superpowers/plans/2026-07-12-three-image-joint-text-style-recovery.md
git commit -m "feat: recover editable text styles from three images"
```

---

## Plan Self-Review

- Spec coverage: FULL/BACKGROUND/TEXT color recovery, font size, weight, run segmentation, alignment, enriched JSON, both renderers, QA, bounded review, and manual-correction evidence are covered.
- Canvas handling: explicitly excluded from every task.
- Backward compatibility: v1.0 page JSON remains loadable; three-image enrichment emits v1.1.
- Dependency check: no new runtime dependency beyond Pillow and existing Node/PPTX tooling.
- Type consistency: `TextLine.layout`, `TextLine.style_evidence`, `recover_page_styles`, and canonical run style keys are used consistently across tasks.
- Placeholder scan: no placeholder or unspecified implementation steps remain.

# Dual Image Editable Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build CyberPPT's `dual_image_editable_overlay` mode by vendoring the relevant `ppt-master` dual-image assets into this repository, then wrapping and adapting them into a PptxGenJS-based CyberPPT production path.

**Architecture:** Keep a complete vendored snapshot under `vendor/ppt_master_dual_image/` for source parity and regression reference. Build the formal CyberPPT implementation under `scripts/dual_image_overlay/`, using Python for normalization, semantic-plan handling, and QA, and PptxGenJS for accepted PPTX generation. Extend CyberPPT QA so full-slide no-text backgrounds are legal only when `delivery_mode="dual_image_editable_overlay"` and the required text/editability gates pass.

**Tech Stack:** Python 3.14, Pillow, Node 26, npm 11, PptxGenJS 4.0.1, PowerPoint-compatible OpenXML inspection, `unittest`.

## Global Constraints

- Source repository: `/Volumes/DOC/ppt-master`.
- Target repository: `/Volumes/DOC/CyberPPT`.
- Delivery mode: `dual_image_editable_overlay`.
- Canvas normalization: all full/background images and layout coordinates normalize to `1280x720`.
- Formal PPTX generation engine: PptxGenJS 4.0.1. Any non-PptxGenJS output is diagnostic-only and cannot be accepted as a CyberPPT final page.
- Copy all dual-image runtime assets into this repository, excluding only transient files: `.DS_Store`, `__pycache__/`, `.pytest_cache/`, `.uuid.LCK`, `.uuid.TMP-*`, generated project outputs, and git metadata.
- After vendoring, formal CyberPPT runtime must not import from or read `/Volumes/DOC/ppt-master`.
- Final text truth is `slide_content_lock` / `semantic_plan`, never OCR text from the generated full image.
- Existing CyberPPT `native_rebuild` QA remains unchanged; all full-slide-background relaxations must be scoped to `delivery_mode="dual_image_editable_overlay"`.

---

## File Structure

Create these new areas:

- `vendor/ppt_master_dual_image/README.md` — provenance, copy commands, excluded transient files, and source commit notes.
- `vendor/ppt_master_dual_image/vendor_manifest.json` — machine-readable list of copied source roots and required files.
- `vendor/ppt_master_dual_image/slide-image-rebuild/` — copied dual-image workflow, scripts, fixtures, tests, fonts, and docs from `ppt-master/slide-image-rebuild`.
- `vendor/ppt_master_dual_image/ppt-master-scripts/` — copied script-imagegen bridge scripts, workflows, tests, and templates from `ppt-master/skills/ppt-master` plus `ppt-master/tests`.
- `scripts/dual_image_overlay/` — CyberPPT native implementation.
- `scripts/dual_image_overlay/render_overlay.mjs` — PptxGenJS renderer.
- `scripts/dual_image_overlay/models.py` — shared dataclasses and JSON loading helpers.
- `scripts/dual_image_overlay/normalize.py` — image and bbox normalization.
- `scripts/dual_image_overlay/semantic_plan.py` — semantic-plan validation and conversion helpers.
- `scripts/dual_image_overlay/layout_qa.py` — bbox, overlap, and font-floor checks.
- `scripts/dual_image_overlay/text_content_qa.py` — exported PPTX text-vs-lock check.
- `scripts/dual_image_overlay/background_text_scan.py` — background no-text scan based on OCR/vision layout JSON.
- `scripts/dual_image_overlay/build_page.py` — single-page orchestrator.
- `tests/test_dual_image_vendor_assets.py` — copied asset completeness and isolation checks.
- `tests/test_dual_image_overlay_*.py` — CyberPPT native mode unit tests.
- `references/dual-image-editable-overlay.md` — user-facing workflow reference.

Modify these existing files:

- `scripts/validate_pptx.py` — mode-aware acceptance for declared no-text full-slide background pictures.
- `scripts/build_visual_qa_gate.py` — mode-aware `background_snapshot_declared_and_no_text` field.
- `scripts/test_validate_pptx.py` — validator regression tests.
- `SKILL.md` — route third-stage requests to the new mode only when the user accepts background snapshot + editable text as the delivery contract.
- `README.md` — mention the new mode as a delivery option, not the default native-rebuild path.

---

### Task 1: Vendor ppt-master Dual-Image Assets

**Files:**
- Create: `vendor/ppt_master_dual_image/README.md`
- Create: `vendor/ppt_master_dual_image/vendor_manifest.json`
- Create: `tests/test_dual_image_vendor_assets.py`
- Copy into: `vendor/ppt_master_dual_image/slide-image-rebuild/`
- Copy into: `vendor/ppt_master_dual_image/ppt-master-scripts/`

**Interfaces:**
- Consumes: `/Volumes/DOC/ppt-master/slide-image-rebuild`, `/Volumes/DOC/ppt-master/skills/ppt-master`, `/Volumes/DOC/ppt-master/tests`.
- Produces: vendored files used by later tasks as source reference and regression fixtures.

- [ ] **Step 1: Copy the runtime asset snapshot**

Run from `/Volumes/DOC/CyberPPT`:

```bash
mkdir -p vendor/ppt_master_dual_image/slide-image-rebuild
mkdir -p vendor/ppt_master_dual_image/ppt-master-scripts

rsync -a \
  --exclude '.git/' \
  --exclude '.DS_Store' \
  --exclude '__pycache__/' \
  --exclude '.pytest_cache/' \
  --exclude 'projects/' \
  --exclude 'exports/' \
  --exclude 'qa_pdf/' \
  --exclude '.uuid.LCK' \
  --exclude '.uuid.TMP-*' \
  /Volumes/DOC/ppt-master/slide-image-rebuild/ \
  vendor/ppt_master_dual_image/slide-image-rebuild/

mkdir -p vendor/ppt_master_dual_image/ppt-master-scripts/scripts
mkdir -p vendor/ppt_master_dual_image/ppt-master-scripts/templates
mkdir -p vendor/ppt_master_dual_image/ppt-master-scripts/workflows
mkdir -p vendor/ppt_master_dual_image/ppt-master-scripts/tests

rsync -a \
  --exclude '__pycache__/' \
  /Volumes/DOC/ppt-master/skills/ppt-master/scripts/ \
  vendor/ppt_master_dual_image/ppt-master-scripts/scripts/

rsync -a \
  --exclude '.DS_Store' \
  /Volumes/DOC/ppt-master/skills/ppt-master/templates/ \
  vendor/ppt_master_dual_image/ppt-master-scripts/templates/

rsync -a \
  /Volumes/DOC/ppt-master/skills/ppt-master/workflows/script-imagegen-to-ppt.md \
  vendor/ppt_master_dual_image/ppt-master-scripts/workflows/

rsync -a \
  /Volumes/DOC/ppt-master/tests/test_ocr_text_locator.py \
  /Volumes/DOC/ppt-master/tests/test_page_image_pair_batch.py \
  /Volumes/DOC/ppt-master/tests/test_script_imagegen_rebuild_template.py \
  /Volumes/DOC/ppt-master/tests/test_script_text_overlay.py \
  /Volumes/DOC/ppt-master/tests/test_template_image_ppt_export.py \
  vendor/ppt_master_dual_image/ppt-master-scripts/tests/
```

Expected: copied directories exist and contain `dual_image_rebuild_pptx.py`, `dual-image-rebuild-ppt.md`, `page_image_pair_batch.py`, `script_imagegen_rebuild_template.py`, `script_text_overlay.py`, `ocr_text_locator.py`, real dual-image fixtures, and font/template assets.

- [ ] **Step 2: Write vendor provenance**

Create `vendor/ppt_master_dual_image/README.md`:

```markdown
# ppt-master Dual Image Vendor Snapshot

This directory vendors the dual-image rebuild assets copied from `/Volumes/DOC/ppt-master` for CyberPPT's `dual_image_editable_overlay` mode.

Copied source roots:

- `/Volumes/DOC/ppt-master/slide-image-rebuild/`
- `/Volumes/DOC/ppt-master/skills/ppt-master/scripts/`
- `/Volumes/DOC/ppt-master/skills/ppt-master/templates/`
- `/Volumes/DOC/ppt-master/skills/ppt-master/workflows/script-imagegen-to-ppt.md`
- selected tests from `/Volumes/DOC/ppt-master/tests/`

Excluded transient files:

- `.git/`
- `.DS_Store`
- `__pycache__/`
- `.pytest_cache/`
- generated project/export/QA output directories
- `.uuid.LCK`
- `.uuid.TMP-*`

This snapshot is not the formal CyberPPT runtime. Formal output must be generated through `scripts/dual_image_overlay/` and PptxGenJS.
```

Create `vendor/ppt_master_dual_image/vendor_manifest.json`:

```json
{
  "schema": "cyberppt.vendor_snapshot.v1",
  "name": "ppt_master_dual_image",
  "source_repo": "/Volumes/DOC/ppt-master",
  "purpose": "Source parity and regression reference for CyberPPT dual_image_editable_overlay mode",
  "formal_runtime": false,
  "copied_roots": [
    {
      "source": "/Volumes/DOC/ppt-master/slide-image-rebuild",
      "target": "vendor/ppt_master_dual_image/slide-image-rebuild"
    },
    {
      "source": "/Volumes/DOC/ppt-master/skills/ppt-master/scripts",
      "target": "vendor/ppt_master_dual_image/ppt-master-scripts/scripts"
    },
    {
      "source": "/Volumes/DOC/ppt-master/skills/ppt-master/templates",
      "target": "vendor/ppt_master_dual_image/ppt-master-scripts/templates"
    },
    {
      "source": "/Volumes/DOC/ppt-master/skills/ppt-master/workflows/script-imagegen-to-ppt.md",
      "target": "vendor/ppt_master_dual_image/ppt-master-scripts/workflows/script-imagegen-to-ppt.md"
    },
    {
      "source": "/Volumes/DOC/ppt-master/tests",
      "target": "vendor/ppt_master_dual_image/ppt-master-scripts/tests"
    }
  ],
  "required_files": [
    "slide-image-rebuild/workflows/dual-image-rebuild-ppt.md",
    "slide-image-rebuild/scripts/dual_image_rebuild_pptx.py",
    "slide-image-rebuild/scripts/dual_image_similarity_report.py",
    "slide-image-rebuild/scripts/project_manager.py",
    "slide-image-rebuild/scripts/image_to_editable_pptx_lib.py",
    "slide-image-rebuild/scripts/svg_to_pptx/pptx_notes.py",
    "slide-image-rebuild/fixtures/dual_image_rebuild/page012/full.png",
    "slide-image-rebuild/fixtures/dual_image_rebuild/page012/background.png",
    "slide-image-rebuild/fixtures/dual_image_rebuild/page012/semantic_plan.json",
    "ppt-master-scripts/scripts/page_image_pair_batch.py",
    "ppt-master-scripts/scripts/script_imagegen_rebuild_template.py",
    "ppt-master-scripts/scripts/script_text_overlay.py",
    "ppt-master-scripts/scripts/ocr_text_locator.py",
    "ppt-master-scripts/scripts/image_prompt_styles.py",
    "ppt-master-scripts/scripts/template_image_ppt_export.py",
    "ppt-master-scripts/templates/image_styles/象牙白深蓝强调.json",
    "ppt-master-scripts/workflows/script-imagegen-to-ppt.md"
  ],
  "excluded_patterns": [
    ".git/",
    ".DS_Store",
    "__pycache__/",
    ".pytest_cache/",
    "projects/",
    "exports/",
    "qa_pdf/",
    ".uuid.LCK",
    ".uuid.TMP-*"
  ]
}
```

- [ ] **Step 3: Write failing vendor asset tests**

Create `tests/test_dual_image_vendor_assets.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "ppt_master_dual_image"


def test_vendor_manifest_required_files_exist() -> None:
    manifest = json.loads((VENDOR / "vendor_manifest.json").read_text(encoding="utf-8"))
    missing = [path for path in manifest["required_files"] if not (VENDOR / path).is_file()]
    assert missing == []


def test_vendor_snapshot_excludes_transient_files() -> None:
    forbidden_names = {".DS_Store", ".uuid.LCK"}
    forbidden_parts = {"__pycache__", ".pytest_cache"}
    offenders = []
    for path in VENDOR.rglob("*"):
        if path.name in forbidden_names:
            offenders.append(str(path.relative_to(ROOT)))
        if any(part in forbidden_parts for part in path.parts):
            offenders.append(str(path.relative_to(ROOT)))
        if path.name.startswith(".uuid.TMP-"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_formal_runtime_does_not_import_vendor_modules() -> None:
    runtime = ROOT / "scripts" / "dual_image_overlay"
    if not runtime.exists():
        return
    offenders = []
    for path in runtime.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "/Volumes/DOC/ppt-master" in text or "vendor.ppt_master_dual_image" in text:
            offenders.append(str(path.relative_to(ROOT)))
    for path in runtime.rglob("*.mjs"):
        text = path.read_text(encoding="utf-8")
        if "/Volumes/DOC/ppt-master" in text or "vendor/ppt_master_dual_image" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
```

- [ ] **Step 4: Run tests and verify they pass**

Run:

```bash
python3 -m unittest tests/test_dual_image_vendor_assets.py
```

Expected: `OK`.

- [ ] **Step 5: Force-add ignored binary assets and commit**

Run:

```bash
git add -f vendor/ppt_master_dual_image tests/test_dual_image_vendor_assets.py
git diff --cached --check
git commit -m "vendor: copy ppt-master dual image assets"
```

Expected: commit succeeds. The force-add is required because the repository ignores image and SVG assets globally.

---

### Task 2: Add PptxGenJS Rendering Foundation

**Files:**
- Create: `package.json`
- Create: `package-lock.json`
- Create: `scripts/dual_image_overlay/render_overlay.mjs`
- Create: `tests/test_dual_image_overlay_renderer.py`

**Interfaces:**
- Consumes: render job JSON with `canvas`, `background`, `boxes`, and `output_pptx`.
- Produces: a PPTX containing one full-slide background image and editable text boxes.

- [ ] **Step 1: Install PptxGenJS**

Create `package.json`:

```json
{
  "name": "cyberppt",
  "private": true,
  "type": "module",
  "scripts": {
    "render:dual-image-overlay": "node scripts/dual_image_overlay/render_overlay.mjs"
  },
  "dependencies": {
    "pptxgenjs": "4.0.1"
  }
}
```

Run:

```bash
npm install
```

Expected: `package-lock.json` is created and `node_modules/` remains ignored.

- [ ] **Step 2: Write failing renderer test**

Create `tests/test_dual_image_overlay_renderer.py`:

```python
from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def _pptx_texts(path: Path) -> list[str]:
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    texts: list[str] = []
    with zipfile.ZipFile(path) as package:
        slide_xml = package.read("ppt/slides/slide1.xml")
    root = ET.fromstring(slide_xml)
    for node in root.findall(".//a:t", ns):
        if node.text:
            texts.append(node.text)
    return texts


def test_renderer_writes_background_and_editable_text(tmp_path: Path) -> None:
    background = tmp_path / "background.png"
    Image.new("RGB", (1280, 720), "#F2F3EF").save(background)
    output = tmp_path / "overlay.pptx"
    job = tmp_path / "job.json"
    job.write_text(
        json.dumps(
            {
                "canvas": {"width": 1280, "height": 720},
                "slide": {"width_in": 13.333, "height_in": 7.5},
                "background": str(background),
                "output_pptx": str(output),
                "boxes": [
                    {
                        "text": "核心结论",
                        "bbox": [80, 40, 600, 110],
                        "font_size": 24,
                        "font_family": "Arial",
                        "fill": "#111111",
                        "bold": true,
                        "align": "left",
                        "v_align": "mid"
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    subprocess.run(
        ["node", str(ROOT / "scripts" / "dual_image_overlay" / "render_overlay.mjs"), str(job)],
        cwd=ROOT,
        check=True,
    )

    assert output.is_file()
    with zipfile.ZipFile(output) as package:
        names = package.namelist()
        assert "ppt/slides/slide1.xml" in names
        assert any(name.startswith("ppt/media/") for name in names)
    assert _pptx_texts(output) == ["核心结论"]
```

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_renderer.py
```

Expected: FAIL because `render_overlay.mjs` does not exist.

- [ ] **Step 3: Implement renderer**

Create `scripts/dual_image_overlay/render_overlay.mjs`:

```javascript
import fs from "node:fs";
import path from "node:path";
import pptxgen from "pptxgenjs";

function readJob(jobPath) {
  return JSON.parse(fs.readFileSync(jobPath, "utf8"));
}

function requireFile(filePath, label) {
  if (!filePath || !fs.existsSync(filePath)) {
    throw new Error(`${label} not found: ${filePath}`);
  }
}

function pxBoxToInches(box, canvas, slide) {
  const [x1, y1, x2, y2] = box;
  return {
    x: (x1 / canvas.width) * slide.width_in,
    y: (y1 / canvas.height) * slide.height_in,
    w: ((x2 - x1) / canvas.width) * slide.width_in,
    h: ((y2 - y1) / canvas.height) * slide.height_in
  };
}

function normalizeColor(value) {
  return String(value || "#111111").replace("#", "").toUpperCase();
}

async function main() {
  const jobPath = process.argv[2];
  if (!jobPath) {
    throw new Error("Usage: node render_overlay.mjs <job.json>");
  }
  const job = readJob(jobPath);
  const canvas = job.canvas || { width: 1280, height: 720 };
  const slideSize = job.slide || { width_in: 13.333, height_in: 7.5 };
  requireFile(job.background, "background");

  const pptx = new pptxgen();
  pptx.author = "CyberPPT";
  pptx.subject = "dual_image_editable_overlay";
  pptx.title = "CyberPPT dual image editable overlay";
  pptx.company = "CyberPPT";
  pptx.lang = "zh-CN";
  pptx.layout = "LAYOUT_CUSTOM";
  pptx.defineLayout({ name: "LAYOUT_CUSTOM", width: slideSize.width_in, height: slideSize.height_in });

  const slide = pptx.addSlide();
  slide.background = { color: "FFFFFF" };
  slide.addImage({
    path: job.background,
    x: 0,
    y: 0,
    w: slideSize.width_in,
    h: slideSize.height_in
  });

  for (const box of job.boxes || []) {
    const rect = pxBoxToInches(box.bbox, canvas, slideSize);
    slide.addText(String(box.text || ""), {
      x: rect.x,
      y: rect.y,
      w: rect.w,
      h: rect.h,
      margin: 0,
      fontFace: box.font_family || "Arial",
      fontSize: Number(box.font_size || 12),
      color: normalizeColor(box.fill),
      bold: box.bold === true,
      align: box.align || "left",
      valign: box.v_align || "top",
      fit: "shrink",
      breakLine: false
    });
  }

  const outPath = path.resolve(job.output_pptx);
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  await pptx.writeFile({ fileName: outPath });
}

main().catch((error) => {
  console.error(JSON.stringify({ valid: false, error: error.message }, null, 2));
  process.exit(1);
});
```

- [ ] **Step 4: Run renderer tests**

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_renderer.py
```

Expected: `OK`.

- [ ] **Step 5: Commit**

Run:

```bash
git add package.json package-lock.json scripts/dual_image_overlay/render_overlay.mjs tests/test_dual_image_overlay_renderer.py
git diff --cached --check
git commit -m "feat: add dual image overlay renderer"
```

Expected: commit succeeds.

---

### Task 3: Add Normalization and Semantic Plan Models

**Files:**
- Create: `scripts/dual_image_overlay/__init__.py`
- Create: `scripts/dual_image_overlay/models.py`
- Create: `scripts/dual_image_overlay/normalize.py`
- Create: `scripts/dual_image_overlay/semantic_plan.py`
- Create: `tests/test_dual_image_overlay_semantic_plan.py`

**Interfaces:**
- Consumes: source images and semantic plan JSON.
- Produces: normalized images and validated semantic-plan records with bboxes in `1280x720`.

- [ ] **Step 1: Write failing model and normalization tests**

Create `tests/test_dual_image_overlay_semantic_plan.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts.dual_image_overlay.normalize import CANVAS, normalize_image, scale_bbox
from scripts.dual_image_overlay.semantic_plan import load_semantic_plan


def test_scale_bbox_from_generated_image_to_canvas() -> None:
    assert CANVAS == (1280, 720)
    bbox = scale_bbox([167.2, 94.1, 334.4, 188.2], source_size=(1672, 941))
    assert bbox == [128.0, 72.0, 256.0, 144.0]


def test_normalize_image_writes_1280x720(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    target = tmp_path / "target.png"
    Image.new("RGB", (1672, 941), "#FFFFFF").save(source)
    normalize_image(source, target)
    with Image.open(target) as image:
        assert image.size == (1280, 720)


def test_load_semantic_plan_requires_explicit_containers(tmp_path: Path) -> None:
    path = tmp_path / "semantic_plan.json"
    path.write_text(
        json.dumps(
            {
                "image_size": {"width": 1672, "height": 941},
                "containers": [
                    {
                        "id": "title_bar",
                        "role": "title_container",
                        "bbox": [80, 40, 1592, 160],
                        "text_safe_bbox": [100, 60, 1570, 140]
                    }
                ],
                "items": [
                    {
                        "source_text": "建议由中电联牵头",
                        "display_text": "建议由中电联牵头",
                        "role": "title",
                        "container_id": "title_bar",
                        "relative_bbox": [0, 0, 1, 1],
                        "font_size": 22,
                        "fill": "#FFFFFF"
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    plan = load_semantic_plan(path)
    assert plan.image_size == {"width": 1280, "height": 720}
    assert plan.containers[0].bbox == [61.244, 30.606, 1219.139, 122.423]
    assert plan.items[0].bbox == [61.244, 30.606, 1219.139, 122.423]
    assert plan.items[0].container_id == "title_bar"
```

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_semantic_plan.py
```

Expected: FAIL because modules do not exist.

- [ ] **Step 2: Implement models**

Create `scripts/dual_image_overlay/__init__.py`:

```python
"""CyberPPT dual image editable overlay mode."""
```

Create `scripts/dual_image_overlay/models.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import json


BBox = list[float]


@dataclass(frozen=True)
class Container:
    id: str
    role: str
    bbox: BBox
    text_safe_bbox: BBox


@dataclass(frozen=True)
class TextItem:
    source_text: str
    display_text: str
    role: str
    container_id: str
    bbox: BBox
    font_size: float
    fill: str
    font_family: str = "Arial"
    bold: bool = False
    align: str = "left"
    v_align: str = "top"


@dataclass(frozen=True)
class SemanticPlan:
    image_size: dict[str, int]
    containers: list[Container]
    items: list[TextItem]


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload
```

- [ ] **Step 3: Implement normalization**

Create `scripts/dual_image_overlay/normalize.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PIL import Image


CANVAS = (1280, 720)


def scale_bbox(
    bbox: Sequence[float],
    *,
    source_size: tuple[int | float, int | float],
    canvas: tuple[int, int] = CANVAS,
) -> list[float]:
    if len(bbox) != 4:
        raise ValueError("bbox must contain four values")
    src_w, src_h = float(source_size[0]), float(source_size[1])
    if src_w <= 0 or src_h <= 0:
        raise ValueError("source_size must be positive")
    sx = canvas[0] / src_w
    sy = canvas[1] / src_h
    x1, y1, x2, y2 = [float(value) for value in bbox]
    if x2 <= x1 or y2 <= y1:
        raise ValueError("bbox must satisfy x2>x1 and y2>y1")
    return [round(x1 * sx, 3), round(y1 * sy, 3), round(x2 * sx, 3), round(y2 * sy, 3)]


def relative_bbox(container_bbox: Sequence[float], rel: Sequence[float]) -> list[float]:
    if len(rel) != 4:
        raise ValueError("relative_bbox must contain four values")
    cx1, cy1, cx2, cy2 = [float(value) for value in container_bbox]
    rx1, ry1, rx2, ry2 = [float(value) for value in rel]
    width = cx2 - cx1
    height = cy2 - cy1
    return [
        round(cx1 + rx1 * width, 3),
        round(cy1 + ry1 * height, 3),
        round(cx1 + rx2 * width, 3),
        round(cy1 + ry2 * height, 3),
    ]


def normalize_image(source: Path, target: Path, canvas: tuple[int, int] = CANVAS) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        image.convert("RGB").resize(canvas, Image.Resampling.LANCZOS).save(target)
```

- [ ] **Step 4: Implement semantic plan loader**

Create `scripts/dual_image_overlay/semantic_plan.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import Container, SemanticPlan, TextItem, read_json
from .normalize import CANVAS, relative_bbox, scale_bbox


def _image_size(payload: dict[str, Any]) -> tuple[int, int]:
    size = payload.get("image_size")
    if isinstance(size, dict) and "width" in size and "height" in size:
        return int(size["width"]), int(size["height"])
    return CANVAS


def load_semantic_plan(path: Path) -> SemanticPlan:
    payload = read_json(path)
    source_size = _image_size(payload)
    raw_containers = payload.get("containers")
    raw_items = payload.get("items")
    if not isinstance(raw_containers, list) or not raw_containers:
        raise ValueError("semantic_plan.containers must be a non-empty array")
    if not isinstance(raw_items, list) or not raw_items:
        raise ValueError("semantic_plan.items must be a non-empty array")

    containers: list[Container] = []
    by_id: dict[str, Container] = {}
    for index, raw in enumerate(raw_containers):
        if not isinstance(raw, dict):
            raise ValueError(f"containers[{index}] must be an object")
        container_id = str(raw.get("id") or "").strip()
        if not container_id:
            raise ValueError(f"containers[{index}].id is required")
        bbox = scale_bbox(raw["bbox"], source_size=source_size)
        safe = scale_bbox(raw.get("text_safe_bbox", raw["bbox"]), source_size=source_size)
        container = Container(
            id=container_id,
            role=str(raw.get("role") or ""),
            bbox=bbox,
            text_safe_bbox=safe,
        )
        containers.append(container)
        by_id[container_id] = container

    items: list[TextItem] = []
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            raise ValueError(f"items[{index}] must be an object")
        container_id = str(raw.get("container_id") or "").strip()
        container = by_id.get(container_id)
        if container is None:
            raise ValueError(f"items[{index}] references unknown container_id: {container_id}")
        if "relative_bbox" in raw:
            bbox = relative_bbox(container.text_safe_bbox, raw["relative_bbox"])
        else:
            bbox = scale_bbox(raw["bbox"], source_size=source_size)
        source_text = str(raw.get("source_text") or raw.get("display_text") or "").strip()
        display_text = str(raw.get("display_text") or source_text).strip()
        if not display_text:
            raise ValueError(f"items[{index}] display_text is required")
        items.append(
            TextItem(
                source_text=source_text,
                display_text=display_text,
                role=str(raw.get("role") or "body"),
                container_id=container_id,
                bbox=bbox,
                font_size=float(raw.get("font_size") or 12),
                fill=str(raw.get("fill") or "#111111"),
                font_family=str(raw.get("font_family") or "Arial"),
                bold=bool(raw.get("bold", False)),
                align=str(raw.get("align") or "left"),
                v_align=str(raw.get("v_align") or "top"),
            )
        )

    return SemanticPlan(
        image_size={"width": CANVAS[0], "height": CANVAS[1]},
        containers=containers,
        items=items,
    )
```

- [ ] **Step 5: Run tests**

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_semantic_plan.py
```

Expected: `OK`.

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/dual_image_overlay tests/test_dual_image_overlay_semantic_plan.py
git diff --cached --check
git commit -m "feat: add dual image semantic plan models"
```

Expected: commit succeeds.

---

### Task 4: Add Overlay QA Helpers

**Files:**
- Create: `scripts/dual_image_overlay/text_content_qa.py`
- Create: `scripts/dual_image_overlay/background_text_scan.py`
- Create: `scripts/dual_image_overlay/layout_qa.py`
- Create: `tests/test_dual_image_overlay_qa.py`

**Interfaces:**
- Consumes: PPTX, expected text list, OCR/vision layout JSON, and semantic plan items.
- Produces: JSON reports with `valid`, `error_count`, and `issues`.

- [ ] **Step 1: Write failing QA tests**

Create `tests/test_dual_image_overlay_qa.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image

from scripts.dual_image_overlay.background_text_scan import scan_background_text
from scripts.dual_image_overlay.layout_qa import check_layout
from scripts.dual_image_overlay.semantic_plan import load_semantic_plan
from scripts.dual_image_overlay.text_content_qa import build_text_content_qa


ROOT = Path(__file__).resolve().parents[1]


def _render_fixture(tmp_path: Path, text: str) -> Path:
    background = tmp_path / "background.png"
    Image.new("RGB", (1280, 720), "#FFFFFF").save(background)
    output = tmp_path / "out.pptx"
    job = tmp_path / "job.json"
    job.write_text(
        json.dumps(
            {
                "canvas": {"width": 1280, "height": 720},
                "slide": {"width_in": 13.333, "height_in": 7.5},
                "background": str(background),
                "output_pptx": str(output),
                "boxes": [
                    {
                        "text": text,
                        "bbox": [80, 40, 500, 100],
                        "font_size": 18,
                        "font_family": "Arial",
                        "fill": "#111111"
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    subprocess.run(["node", str(ROOT / "scripts/dual_image_overlay/render_overlay.mjs"), str(job)], cwd=ROOT, check=True)
    return output


def test_text_content_qa_compares_pptx_text_to_expected(tmp_path: Path) -> None:
    pptx = _render_fixture(tmp_path, "核心结论")
    report = build_text_content_qa(pptx, ["核心结论"])
    assert report["valid"] is True
    assert report["checks"]["pptx_text_matches_expected"] is True


def test_background_text_scan_fails_when_ocr_items_exist(tmp_path: Path) -> None:
    layout = tmp_path / "background_layout.json"
    layout.write_text(
        json.dumps({"image_size": {"width": 1280, "height": 720}, "items": [{"text": "残字", "bbox": [1, 1, 20, 20]}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    report = scan_background_text(layout)
    assert report["valid"] is False
    assert report["error_count"] == 1


def test_layout_qa_detects_container_overflow(tmp_path: Path) -> None:
    semantic = tmp_path / "semantic_plan.json"
    semantic.write_text(
        json.dumps(
            {
                "image_size": {"width": 1280, "height": 720},
                "containers": [{"id": "c1", "role": "body", "bbox": [100, 100, 300, 200], "text_safe_bbox": [100, 100, 300, 200]}],
                "items": [{"display_text": "正文", "source_text": "正文", "role": "body", "container_id": "c1", "bbox": [90, 100, 310, 200], "font_size": 12}]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    report = check_layout(load_semantic_plan(semantic))
    assert report["valid"] is False
    assert any(issue["code"] == "text_box_outside_container" for issue in report["issues"])
```

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_qa.py
```

Expected: FAIL because QA modules do not exist.

- [ ] **Step 2: Implement text-content QA**

Create `scripts/dual_image_overlay/text_content_qa.py`:

```python
from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def _normalize(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def pptx_texts(path: Path) -> list[str]:
    texts: list[str] = []
    with zipfile.ZipFile(path) as package:
        slide_names = sorted(name for name in package.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
        for name in slide_names:
            root = ET.fromstring(package.read(name))
            current: list[str] = []
            for node in root.findall(".//a:t", NS):
                if node.text:
                    current.append(node.text)
            if current:
                texts.append(_normalize("".join(current)))
    return texts


def build_text_content_qa(pptx_path: Path, expected_texts: list[str]) -> dict:
    expected = [_normalize(text) for text in expected_texts if _normalize(text)]
    actual = pptx_texts(pptx_path)
    mismatches = []
    for index in range(max(len(expected), len(actual))):
        left = expected[index] if index < len(expected) else None
        right = actual[index] if index < len(actual) else None
        if left != right:
            mismatches.append({"index": index, "expected": left, "actual": right, "code": "pptx_text_differs_from_expected"})
    return {
        "schema": "cyberppt.dual_image.text_content_qa.v1",
        "valid": not mismatches,
        "checks": {
            "text_count_matches": len(expected) == len(actual),
            "pptx_text_matches_expected": not mismatches
        },
        "expected_texts": expected,
        "actual_texts": actual,
        "mismatches": mismatches,
        "error_count": len(mismatches)
    }
```

- [ ] **Step 3: Implement background text scan**

Create `scripts/dual_image_overlay/background_text_scan.py`:

```python
from __future__ import annotations

import json
from pathlib import Path


def scan_background_text(layout_path: Path) -> dict:
    payload = json.loads(layout_path.read_text(encoding="utf-8"))
    items = payload.get("items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        items = []
    text_items = [item for item in items if isinstance(item, dict) and str(item.get("text") or "").strip()]
    issues = [
        {
            "severity": "error",
            "code": "background_contains_text",
            "text": str(item.get("text") or ""),
            "bbox": item.get("bbox"),
        }
        for item in text_items
    ]
    return {
        "schema": "cyberppt.dual_image.background_text_scan.v1",
        "valid": not issues,
        "policy": "no readable primary text may remain in the no-text background",
        "checked_layout": str(layout_path),
        "issues": issues,
        "error_count": len(issues)
    }
```

- [ ] **Step 4: Implement layout QA**

Create `scripts/dual_image_overlay/layout_qa.py`:

```python
from __future__ import annotations

from .models import SemanticPlan


ROLE_MIN_FONT = {
    "title": 14.0,
    "subtitle": 10.0,
    "body": 9.0,
    "kpi": 14.0,
    "evidence": 6.5,
    "caveat": 6.5,
    "so_what": 9.5,
}


def _inside(inner: list[float], outer: list[float]) -> bool:
    return inner[0] >= outer[0] and inner[1] >= outer[1] and inner[2] <= outer[2] and inner[3] <= outer[3]


def _overlap(a: list[float], b: list[float]) -> float:
    x1 = max(a[0], b[0])
    y1 = max(a[1], b[1])
    x2 = min(a[2], b[2])
    y2 = min(a[3], b[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    return (x2 - x1) * (y2 - y1)


def check_layout(plan: SemanticPlan) -> dict:
    containers = {container.id: container for container in plan.containers}
    issues = []
    for index, item in enumerate(plan.items):
        container = containers[item.container_id]
        if not _inside(item.bbox, container.text_safe_bbox):
            issues.append(
                {
                    "severity": "error",
                    "code": "text_box_outside_container",
                    "item_index": index,
                    "container_id": item.container_id,
                    "bbox": item.bbox,
                    "text_safe_bbox": container.text_safe_bbox,
                }
            )
        minimum = ROLE_MIN_FONT.get(item.role, 7.5)
        if item.font_size < minimum:
            issues.append(
                {
                    "severity": "error",
                    "code": "font_below_role_floor",
                    "item_index": index,
                    "role": item.role,
                    "font_size": item.font_size,
                    "minimum": minimum,
                }
            )
    for left_index, left in enumerate(plan.items):
        for right_index, right in enumerate(plan.items[left_index + 1 :], start=left_index + 1):
            if _overlap(left.bbox, right.bbox) > 4.0:
                issues.append(
                    {
                        "severity": "error",
                        "code": "text_boxes_overlap",
                        "left_index": left_index,
                        "right_index": right_index,
                    }
                )
    return {
        "schema": "cyberppt.dual_image.layout_qa.v1",
        "valid": not issues,
        "issues": issues,
        "error_count": len(issues),
    }
```

- [ ] **Step 5: Run QA tests**

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_qa.py
```

Expected: `OK`.

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/dual_image_overlay tests/test_dual_image_overlay_qa.py
git diff --cached --check
git commit -m "feat: add dual image overlay QA helpers"
```

Expected: commit succeeds.

---

### Task 5: Add Single-Page Build Orchestrator

**Files:**
- Create: `scripts/dual_image_overlay/build_page.py`
- Create: `tests/test_dual_image_overlay_build_page.py`

**Interfaces:**
- Consumes: `--full`, `--background`, `--semantic-plan`, optional `--background-layout`, and `--out-dir`.
- Produces: normalized images, render job, PPTX, `text_mapping.json`, `text_content_qa.json`, `layout_qa.json`, optional `background_text_scan.json`, and `production_readiness.json`.

- [ ] **Step 1: Write failing orchestrator test**

Create `tests/test_dual_image_overlay_build_page.py`:

```python
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def test_build_page_creates_pptx_and_qa_artifacts(tmp_path: Path) -> None:
    full = tmp_path / "full.png"
    background = tmp_path / "background.png"
    Image.new("RGB", (1672, 941), "#F2F3EF").save(full)
    Image.new("RGB", (1672, 941), "#F2F3EF").save(background)
    semantic = tmp_path / "semantic_plan.json"
    semantic.write_text(
        json.dumps(
            {
                "image_size": {"width": 1672, "height": 941},
                "containers": [{"id": "title", "role": "title", "bbox": [80, 40, 900, 150], "text_safe_bbox": [90, 50, 880, 140]}],
                "items": [{"source_text": "核心结论", "display_text": "核心结论", "role": "title", "container_id": "title", "relative_bbox": [0, 0, 1, 1], "font_size": 18}]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    out_dir = tmp_path / "page"
    subprocess.run(
        [
            "python3",
            str(ROOT / "scripts/dual_image_overlay/build_page.py"),
            "--full",
            str(full),
            "--background",
            str(background),
            "--semantic-plan",
            str(semantic),
            "--out-dir",
            str(out_dir),
        ],
        cwd=ROOT,
        check=True,
    )
    assert (out_dir / "normalized/full-1280x720.png").is_file()
    assert (out_dir / "normalized/background-1280x720.png").is_file()
    assert (out_dir / "exports/page.pptx").is_file()
    readiness = json.loads((out_dir / "analysis/production_readiness.json").read_text(encoding="utf-8"))
    assert readiness["valid"] is True
    assert readiness["checks"]["text_content_matches_lock"] is True
    assert readiness["checks"]["layout_qa_pass"] is True
```

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_build_page.py
```

Expected: FAIL because `build_page.py` does not exist.

- [ ] **Step 2: Implement build orchestrator**

Create `scripts/dual_image_overlay/build_page.py`:

```python
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict
from pathlib import Path

from .background_text_scan import scan_background_text
from .layout_qa import check_layout
from .normalize import normalize_image
from .semantic_plan import load_semantic_plan
from .text_content_qa import build_text_content_qa


ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _render_boxes(plan) -> list[dict]:
    boxes = []
    for item in plan.items:
        boxes.append(
            {
                "text": item.display_text,
                "bbox": item.bbox,
                "font_size": item.font_size,
                "font_family": item.font_family,
                "fill": item.fill,
                "bold": item.bold,
                "align": item.align,
                "v_align": "mid" if item.v_align == "middle" else item.v_align,
                "role": item.role,
                "container_id": item.container_id,
            }
        )
    return boxes


def build_page(args: argparse.Namespace) -> dict:
    out_dir = args.out_dir.resolve()
    normalized = out_dir / "normalized"
    analysis = out_dir / "analysis"
    exports = out_dir / "exports"
    full_norm = normalized / "full-1280x720.png"
    background_norm = normalized / "background-1280x720.png"
    normalize_image(args.full.resolve(), full_norm)
    normalize_image(args.background.resolve(), background_norm)

    plan = load_semantic_plan(args.semantic_plan.resolve())
    layout_qa = check_layout(plan)
    _write_json(analysis / "layout_qa.json", layout_qa)

    background_scan = {"valid": True, "skipped": True, "reason": "no_background_layout_supplied", "error_count": 0}
    if args.background_layout:
        background_scan = scan_background_text(args.background_layout.resolve())
    _write_json(analysis / "background_text_scan.json", background_scan)

    boxes = _render_boxes(plan)
    mapping = {
        "schema": "cyberppt.dual_image.text_mapping.v1",
        "delivery_mode": "dual_image_editable_overlay",
        "canvas": {"width": 1280, "height": 720},
        "background": str(background_norm),
        "semantic_plan": str(args.semantic_plan.resolve()),
        "boxes": boxes,
    }
    _write_json(analysis / "text_mapping.json", mapping)

    pptx_path = exports / "page.pptx"
    job = {
        "canvas": {"width": 1280, "height": 720},
        "slide": {"width_in": 13.333, "height_in": 7.5},
        "background": str(background_norm),
        "output_pptx": str(pptx_path),
        "boxes": boxes,
    }
    job_path = analysis / "render_job.json"
    _write_json(job_path, job)
    subprocess.run(["node", str(ROOT / "scripts/dual_image_overlay/render_overlay.mjs"), str(job_path)], cwd=ROOT, check=True)

    expected = [item.display_text for item in plan.items]
    text_content_qa = build_text_content_qa(pptx_path, expected)
    _write_json(analysis / "text_content_qa.json", text_content_qa)

    readiness = {
        "schema": "cyberppt.dual_image.production_readiness.v1",
        "valid": bool(layout_qa["valid"] and text_content_qa["valid"] and background_scan["valid"]),
        "checks": {
            "delivery_mode": "dual_image_editable_overlay",
            "background_snapshot_editable_text": True,
            "background_has_no_text": bool(background_scan["valid"]),
            "background_image_declared": True,
            "all_key_text_editable": bool(text_content_qa["valid"]),
            "text_content_matches_lock": bool(text_content_qa["valid"]),
            "layout_qa_pass": bool(layout_qa["valid"]),
        },
        "artifacts": {
            "normalized_full": str(full_norm),
            "normalized_background": str(background_norm),
            "pptx": str(pptx_path),
            "text_mapping": str(analysis / "text_mapping.json"),
            "text_content_qa": str(analysis / "text_content_qa.json"),
            "layout_qa": str(analysis / "layout_qa.json"),
            "background_text_scan": str(analysis / "background_text_scan.json"),
        },
    }
    _write_json(analysis / "production_readiness.json", readiness)
    return readiness


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build one CyberPPT dual image editable overlay page.")
    parser.add_argument("--full", type=Path, required=True)
    parser.add_argument("--background", type=Path, required=True)
    parser.add_argument("--semantic-plan", type=Path, required=True)
    parser.add_argument("--background-layout", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    return parser


def main() -> int:
    result = build_page(build_parser().parse_args())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["valid"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Fix direct script imports**

If direct execution fails with `ImportError: attempted relative import with no known parent package`, add this block at the top of `build_page.py` after imports of `Path`:

```python
if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "scripts.dual_image_overlay"
```

Then keep the existing relative imports unchanged.

- [ ] **Step 4: Run orchestrator test**

Run:

```bash
python3 -m unittest tests/test_dual_image_overlay_build_page.py
```

Expected: `OK`.

- [ ] **Step 5: Commit**

Run:

```bash
git add scripts/dual_image_overlay/build_page.py tests/test_dual_image_overlay_build_page.py
git diff --cached --check
git commit -m "feat: build dual image overlay pages"
```

Expected: commit succeeds.

---

### Task 6: Make CyberPPT Validator Mode-Aware

**Files:**
- Modify: `scripts/validate_pptx.py`
- Modify: `scripts/build_visual_qa_gate.py`
- Modify: `scripts/test_validate_pptx.py`

**Interfaces:**
- Consumes: `slide_manifest.json` entries with `delivery_mode`.
- Produces: strict QA behavior where full-slide background pictures are allowed only for declared and passing `dual_image_editable_overlay` pages.

- [ ] **Step 1: Add validator tests for dual-image mode**

Append these tests to `scripts/test_validate_pptx.py`:

```python
def test_dual_image_overlay_manifest_allows_declared_background_snapshot(self):
    entry = {
        "slide": 1,
        "delivery_mode": "dual_image_editable_overlay",
        "expected_pictures": 1,
        "image_assets": [
            {
                "role": "no_text_background",
                "covers_full_slide": True,
                "background_image_declared": True,
                "background_has_no_text": True,
                "editable_text_overlay": True
            }
        ],
        "qa_expectations": {
            "background_snapshot_editable_text": True,
            "background_has_no_text": True,
            "all_key_text_editable": True,
            "text_content_matches_lock": True,
            "container_overflow_pass": True,
            "layout_qa_error_count": 0,
            "visual_semantics_preserved": True,
            "background_image_declared": True
        },
        "generation_engine": {
            "tool": "pptxgenjs",
            "visual_fidelity_not_reduced": True
        }
    }
    self.assertTrue(self.module.is_dual_image_overlay_entry(entry))
    self.assertTrue(self.module.dual_image_background_exception_allowed(entry))


def test_dual_image_overlay_requires_no_text_background(self):
    entry = {
        "slide": 1,
        "delivery_mode": "dual_image_editable_overlay",
        "image_assets": [],
        "qa_expectations": {
            "background_snapshot_editable_text": True,
            "background_has_no_text": False,
            "all_key_text_editable": True,
            "text_content_matches_lock": True,
            "container_overflow_pass": True,
            "layout_qa_error_count": 0,
            "visual_semantics_preserved": True,
            "background_image_declared": True
        }
    }
    self.assertTrue(self.module.is_dual_image_overlay_entry(entry))
    self.assertFalse(self.module.dual_image_background_exception_allowed(entry))
```

Run:

```bash
python3 -m unittest scripts/test_validate_pptx.py
```

Expected: FAIL because helper functions do not exist.

- [ ] **Step 2: Add mode helpers to validator**

Add this near the constants in `scripts/validate_pptx.py`:

```python
DUAL_IMAGE_OVERLAY_MODE = "dual_image_editable_overlay"
DUAL_IMAGE_REQUIRED_QA = (
    "background_snapshot_editable_text",
    "background_has_no_text",
    "all_key_text_editable",
    "text_content_matches_lock",
    "container_overflow_pass",
    "visual_semantics_preserved",
    "background_image_declared",
)
```

Add these helpers near other manifest helper functions:

```python
def is_dual_image_overlay_entry(entry: dict[str, Any]) -> bool:
    return str(entry.get("delivery_mode") or "") == DUAL_IMAGE_OVERLAY_MODE


def dual_image_background_exception_allowed(entry: dict[str, Any]) -> bool:
    if not is_dual_image_overlay_entry(entry):
        return False
    qa = entry.get("qa_expectations")
    if not isinstance(qa, dict):
        return False
    if any(qa.get(field) is not True for field in DUAL_IMAGE_REQUIRED_QA):
        return False
    if int(qa.get("layout_qa_error_count", 0) or 0) != 0:
        return False
    image_assets = entry.get("image_assets")
    if not isinstance(image_assets, list) or len(image_assets) != 1:
        return False
    asset = image_assets[0]
    if not isinstance(asset, dict):
        return False
    return (
        asset.get("role") == "no_text_background"
        and asset.get("covers_full_slide") is True
        and asset.get("background_image_declared") is True
        and asset.get("background_has_no_text") is True
        and asset.get("editable_text_overlay") is True
    )
```

- [ ] **Step 3: Scope full-slide background risk to the new exception**

Find the code path that raises or preserves `FULL_SLIDE_BACKGROUND_RISK` for large images. Keep the default behavior unchanged. When manifest entry satisfies `dual_image_background_exception_allowed(entry)`, downgrade that specific full-slide image risk to an informational note instead of a strict error.

Use this exact branch shape in the relevant validation block:

```python
if code == "FULL_SLIDE_BACKGROUND_RISK" and dual_image_background_exception_allowed(entry):
    warnings.append(
        {
            "code": "DECLARED_DUAL_IMAGE_BACKGROUND",
            "message": "Full-slide no-text background is allowed for dual_image_editable_overlay mode.",
            "slide": slide_number,
        }
    )
else:
    errors.append(issue)
```

If the validator stores issues in a different local variable name, keep the same condition and message while adapting only the variable names.

- [ ] **Step 4: Update visual QA builder**

Modify `scripts/build_visual_qa_gate.py`:

- keep `blueprint_background_not_used` for native mode
- add `background_snapshot_declared_and_no_text`
- set `blueprint_background_not_used` to `False` only when building a dual-image overlay gate
- set `background_snapshot_declared_and_no_text` from the background text scan result

Add this field to `VISUAL_TRUE_FIELDS`:

```python
"background_snapshot_declared_and_no_text",
```

When no mode argument exists yet, add:

```python
parser.add_argument("--delivery-mode", default="native_rebuild")
```

Set the field values with:

```python
if args.delivery_mode == "dual_image_editable_overlay":
    entry["blueprint_background_not_used"] = False
    entry["background_snapshot_declared_and_no_text"] = passed
else:
    entry["blueprint_background_not_used"] = passed
    entry["background_snapshot_declared_and_no_text"] = False
```

- [ ] **Step 5: Run validator tests**

Run:

```bash
python3 -m unittest scripts/test_validate_pptx.py
```

Expected: `OK`.

- [ ] **Step 6: Commit**

Run:

```bash
git add scripts/validate_pptx.py scripts/build_visual_qa_gate.py scripts/test_validate_pptx.py
git diff --cached --check
git commit -m "feat: allow declared dual image overlay QA mode"
```

Expected: commit succeeds.

---

### Task 7: Document Workflow Routing and Run a P2/P3 Pilot

**Files:**
- Create: `references/dual-image-editable-overlay.md`
- Modify: `SKILL.md`
- Modify: `README.md`
- Create project artifacts under: `projects/power-overseas-capability/workbench/dual-image/page-02/`
- Create project artifacts under: `projects/power-overseas-capability/workbench/dual-image/page-03/`

**Interfaces:**
- Consumes: current project assets under `projects/power-overseas-capability/workbench/prototype-text-overlay/`.
- Produces: P2/P3 pilot artifacts proving the mode works in the current project.

- [ ] **Step 1: Write workflow reference**

Create `references/dual-image-editable-overlay.md`:

```markdown
# 双图底图 + 可编辑文字模式

`dual_image_editable_overlay` 是 CyberPPT 第三阶段的一个显式交付模式。

它适用于用户接受以下交付边界的场景：

- 无文字底图作为整页视觉背景；
- 主要文字、数字、证据标签、caveat 和 SO WHAT 使用可编辑 PPT 文本框；
- 背景中的图形、图标、曲线、表格结构和装饰不可编辑；
- 最终文字 truth 来自 `slide_content_lock` / `semantic_plan`，不是 OCR。

它不适用于用户要求图表、表格、箭头、图标、背景形状也可编辑的场景；这些请求仍走 `native_rebuild`。

生产要求：

- full/background 图像和坐标统一归一化到 `1280x720`；
- background 必须通过无文字扫描；
- `semantic_plan.containers[]` 必须存在；
- 每个文本项必须有 `container_id`；
- PptxGenJS 是正式 PPTX 生成器；
- `text_content_qa.json`、`layout_qa.json` 和 `production_readiness.json` 必须通过；
- 先跑 P2/P3 pilot，再批量跑全套页面。
```

- [ ] **Step 2: Update SKILL routing**

In `SKILL.md`, add a short subsection under the third-stage section:

```markdown
### 双图底图 + 可编辑文字模式

当用户明确接受“底图不编辑，只编辑主要文字”或要求“用完整图定位文字，用无字图做底稿”时，可启用 `dual_image_editable_overlay`。该模式允许一张无文字整页背景图，但必须声明 `delivery_mode=dual_image_editable_overlay`，并通过 background no-text scan、text-content QA、layout QA 和 visual QA。若用户要求图表、表格、箭头、图标或背景对象可编辑，必须回到默认 `native_rebuild`。
```

- [ ] **Step 3: Update README**

In `README.md`, add one bullet under core capabilities:

```markdown
- 在用户接受“无文字底图 + 主要文字可编辑”的交付边界时，可使用 `dual_image_editable_overlay` 快线，保留复杂视觉质感并显著减少原生重建工作量。
```

- [ ] **Step 4: Create P2/P3 pilot semantic plans**

Create `projects/power-overseas-capability/workbench/dual-image/page-02/analysis/semantic_plan.json`:

```json
{
  "image_size": {"width": 1280, "height": 720},
  "containers": [
    {"id": "title_bar", "role": "title", "bbox": [48, 24, 1232, 98], "text_safe_bbox": [72, 36, 1208, 86]},
    {"id": "main_judgement", "role": "body", "bbox": [70, 118, 1210, 222], "text_safe_bbox": [92, 136, 1188, 204]},
    {"id": "so_what", "role": "so_what", "bbox": [70, 632, 1210, 696], "text_safe_bbox": [92, 646, 1188, 682]}
  ],
  "items": [
    {
      "source_text": "建议由中电联牵头，用“六位一体”体系和四阶段试点，把电力产业链企业出海能力证明从“自证”转向“可信证据”",
      "display_text": "建议由中电联牵头，用“六位一体”体系和四阶段试点，把电力产业链企业出海能力证明从“自证”转向“可信证据”",
      "role": "title",
      "container_id": "title_bar",
      "relative_bbox": [0, 0, 1, 1],
      "font_size": 17,
      "fill": "#FFFFFF",
      "bold": true
    },
    {
      "source_text": "电力产业链企业出海能力证明体系建设已具备推进必要性，应坚持场景牵引、证据支撑、分角色建模、分层产品化、数据化运营和边界清晰原则",
      "display_text": "电力产业链企业出海能力证明体系建设已具备推进必要性，应坚持场景牵引、证据支撑、分角色建模、分层产品化、数据化运营和边界清晰原则",
      "role": "body",
      "container_id": "main_judgement",
      "relative_bbox": [0, 0, 1, 1],
      "font_size": 12,
      "fill": "#111111"
    },
    {
      "source_text": "建议按“规则先行—试点验证—常态运营—规模推广”路径启动首阶段工作",
      "display_text": "建议按“规则先行—试点验证—常态运营—规模推广”路径启动首阶段工作",
      "role": "so_what",
      "container_id": "so_what",
      "relative_bbox": [0, 0, 1, 1],
      "font_size": 13,
      "fill": "#FFFFFF",
      "bold": true
    }
  ]
}
```

Create `projects/power-overseas-capability/workbench/dual-image/page-03/analysis/semantic_plan.json`:

```json
{
  "image_size": {"width": 1280, "height": 720},
  "containers": [
    {"id": "title_bar", "role": "title", "bbox": [48, 24, 1232, 98], "text_safe_bbox": [72, 36, 1208, 86]},
    {"id": "flow", "role": "body", "bbox": [70, 270, 1210, 486], "text_safe_bbox": [92, 300, 1188, 456]},
    {"id": "so_what", "role": "so_what", "bbox": [70, 632, 1210, 696], "text_safe_bbox": [92, 646, 1188, 682]}
  ],
  "items": [
    {
      "source_text": "全球能源转型叠加海外规则趋严，审查方式正从“资质审查”转向“持续证据审查”",
      "display_text": "全球能源转型叠加海外规则趋严，审查方式正从“资质审查”转向“持续证据审查”",
      "role": "title",
      "container_id": "title_bar",
      "relative_bbox": [0, 0, 1, 1],
      "font_size": 18,
      "fill": "#FFFFFF",
      "bold": true
    },
    {
      "source_text": "审查对象扩展 → 审查材料扩展为证据链 → 审查方式扩展为持续监测",
      "display_text": "审查对象扩展 → 审查材料扩展为证据链 → 审查方式扩展为持续监测",
      "role": "body",
      "container_id": "flow",
      "relative_bbox": [0, 0.2, 1, 0.8],
      "font_size": 14,
      "fill": "#111111"
    },
    {
      "source_text": "这一趋势是建设行业化能力证明体系的根本动因",
      "display_text": "这一趋势是建设行业化能力证明体系的根本动因",
      "role": "so_what",
      "container_id": "so_what",
      "relative_bbox": [0, 0, 1, 1],
      "font_size": 14,
      "fill": "#FFFFFF",
      "bold": true
    }
  ]
}
```

- [ ] **Step 5: Run P2/P3 pilot builds**

Run:

```bash
python3 scripts/dual_image_overlay/build_page.py \
  --full projects/power-overseas-capability/workbench/blueprints/page-02-executive-summary.png \
  --background projects/power-overseas-capability/workbench/prototype-text-overlay/backgrounds/page-02-bg-no-text.png \
  --semantic-plan projects/power-overseas-capability/workbench/dual-image/page-02/analysis/semantic_plan.json \
  --out-dir projects/power-overseas-capability/workbench/dual-image/page-02

python3 scripts/dual_image_overlay/build_page.py \
  --full projects/power-overseas-capability/workbench/blueprints/page-03-environment-shift.png \
  --background projects/power-overseas-capability/workbench/prototype-text-overlay/backgrounds/page-03-bg-no-text.png \
  --semantic-plan projects/power-overseas-capability/workbench/dual-image/page-03/analysis/semantic_plan.json \
  --out-dir projects/power-overseas-capability/workbench/dual-image/page-03
```

Expected: both commands exit `0` and create `exports/page.pptx` plus QA JSON artifacts.

- [ ] **Step 6: Run focused regression tests**

Run:

```bash
python3 -m unittest \
  tests/test_dual_image_vendor_assets.py \
  tests/test_dual_image_overlay_renderer.py \
  tests/test_dual_image_overlay_semantic_plan.py \
  tests/test_dual_image_overlay_qa.py \
  tests/test_dual_image_overlay_build_page.py \
  scripts/test_validate_pptx.py
```

Expected: `OK`.

- [ ] **Step 7: Commit docs and pilot metadata**

Run:

```bash
git add references/dual-image-editable-overlay.md SKILL.md README.md
git add -f projects/power-overseas-capability/workbench/dual-image/page-02/analysis/semantic_plan.json
git add -f projects/power-overseas-capability/workbench/dual-image/page-03/analysis/semantic_plan.json
git diff --cached --check
git commit -m "docs: route dual image editable overlay mode"
```

Expected: commit succeeds. Do not commit generated PPTX or PNG pilot outputs unless the user explicitly asks to preserve generated artifacts in git.

---

## Final Verification

Run from `/Volumes/DOC/CyberPPT`:

```bash
python3 -m unittest \
  tests/test_dual_image_vendor_assets.py \
  tests/test_dual_image_overlay_renderer.py \
  tests/test_dual_image_overlay_semantic_plan.py \
  tests/test_dual_image_overlay_qa.py \
  tests/test_dual_image_overlay_build_page.py \
  scripts/test_validate_pptx.py

npm run render:dual-image-overlay -- --help
```

Expected:

- Python tests report `OK`.
- The npm command may exit nonzero because the renderer expects a job JSON, but it must print a usage/error mentioning `render_overlay.mjs <job.json>` and must not fail with `Cannot find module`.

## Self-Review

Spec coverage:

- Vendoring all relevant dual-image assets is covered by Task 1.
- `1280x720` normalization is covered by Task 3 and Task 5.
- PptxGenJS formal generation is covered by Task 2 and Task 5.
- Content truth from semantic plan is covered by Task 3, Task 4, and Task 5.
- Background no-text QA is covered by Task 4 and Task 6.
- Mode-aware validator behavior is covered by Task 6.
- P2/P3 pilot flow is covered by Task 7.

Known implementation boundary:

- The P2/P3 semantic plans in Task 7 are pilot-safe starting points, not final layout-polished plans. If visual review shows crowding or misalignment, revise the semantic plan bboxes and rerun only the affected page.

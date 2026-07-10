# Dual Image Page Understanding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable page-understanding layer for the dual-image rebuild flow so containers, writable regions, text styles, alignment relations, layout policies, caching, and QA feedback are inferred once and consumed consistently downstream.

**Architecture:** Introduce `page_understanding.json` as the evidence-fusion contract between full/background image pairs and `page_scene_graph.json`. The new layer normalizes coordinates, mines text/style/container evidence from existing artifacts, fuses writable and reserved regions, emits layout intents, and gives `scene_graph`, `container_workspace`, `workspace_assignment`, and `office_textbox_fit` a single source of page geometry truth.

**Tech Stack:** Python 3.14, existing `scripts/dual_image_overlay` modules, Pillow, pytest, JSON artifacts under `analysis/`, current CyberPPT `dual_image_editable_overlay` flow.

## Global Constraints

- Do not treat OCR text as final content truth; OCR and image-derived text are locator/style evidence only.
- Do not bypass `dual_image_editable_overlay`, `template_rebuild`, or current production readiness gates.
- Do not add a new OCR dependency in this revision.
- Normalize all production coordinates to `1672x941`.
- Existing `page_scene_graph.json` remains the layout-facing contract; `page_understanding.json` feeds it instead of replacing it.
- Prefer reusable rules over page-specific fixes.
- Keep 9pt as preferred text size floor, but allow fit policies to go below 9pt down to the existing absolute floor when container evidence requires it.

---

## File Structure

- Create: `scripts/dual_image_overlay/page_understanding.py`
  - Owns the `cyberppt.dual_image.page_understanding.v1` schema, artifact loading, evidence fusion, cache signatures, and report writing.
- Create: `tests/test_dual_image_overlay_page_understanding.py`
  - Unit tests for page-understanding schema, style extraction, container fusion, writable/reserved region decisions, cache signatures, and QA feedback ingestion.
- Modify: `scripts/dual_image_overlay/build_page.py`
  - Writes overlay-stage page understanding from normalized full/background images, semantic plan, boxes, container workspace, visual registry, and typography evidence.
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
  - Builds template-stage page understanding once per page and passes it into container workspace / semantic binding / scene graph construction instead of letting each stage rediscover the same structures.
- Modify: `scripts/dual_image_overlay/scene_graph/builder.py`
  - Consumes `page_understanding` to create visual nodes, text style evidence, relations, and layout intents.
- Modify: `scripts/dual_image_overlay/container_workspace.py`
  - Accepts precomputed writable/reserved zones from page understanding while preserving current direct inputs for compatibility.
- Modify: `scripts/dual_image_overlay/workspace_assignment.py`
  - Prefers page-understanding work slots and alignment groups when available.
- Modify: `scripts/dual_image_overlay/office_textbox_fit.py`
  - Consumes fit policy hints from page understanding instead of hardcoding all fit order decisions locally.
- Modify: `scripts/dual_image_overlay/source_capture.py`
  - Records page-understanding artifact paths and cache signatures in `source_capture.json`.
- Modify: `scripts/dual_image_overlay/production_readiness.py`
  - Adds `page_understanding` as a required consumed artifact for production readiness.
- Modify: `scripts/dual_image_overlay/default_quality_rules.json`, `build_quality_rules.json`, `postflight_quality_rules.json`
  - Adds quality rules for page-understanding validity and downstream consumption.

---

### Task 1: Page Understanding Contract And Artifact Builder

**Files:**
- Create: `scripts/dual_image_overlay/page_understanding.py`
- Create: `tests/test_dual_image_overlay_page_understanding.py`

**Interfaces:**
- Produces: `build_page_understanding(*, page_number: int, full_image: Path | None, background_image: Path | None, text_items: list[dict[str, Any]], containers: list[dict[str, Any]], visual_elements: list[dict[str, Any]], typography: list[dict[str, Any]] | None = None, scene_graph: dict[str, Any] | None = None, render_qa: dict[str, Any] | None = None, canvas: dict[str, float] | None = None) -> dict[str, Any]`
- Produces: `write_page_understanding(path: Path, payload: dict[str, Any]) -> dict[str, Any]`
- Produces schema: `cyberppt.dual_image.page_understanding.v1`
- Consumes: existing text item dictionaries with `text`, `bbox`, `container_id`, `role`, `font_size`, `fill`, `font_weight`, `align`.

- [ ] **Step 1: Write failing schema test**

Add to `tests/test_dual_image_overlay_page_understanding.py`:

```python
from __future__ import annotations

from scripts.dual_image_overlay.page_understanding import build_page_understanding


def test_page_understanding_builds_normalized_contract() -> None:
    result = build_page_understanding(
        page_number=11,
        full_image=None,
        background_image=None,
        text_items=[
            {
                "text": "空间运营方",
                "bbox": [810.0, 260.0, 910.0, 282.0],
                "container_id": "operator_card",
                "role": "title",
                "font_size": 10.0,
                "fill": "#0B1F3D",
                "font_weight": "700",
                "align": "left",
            }
        ],
        containers=[
            {
                "id": "operator_card",
                "role": "service_card",
                "bbox": [790.0, 240.0, 940.0, 560.0],
                "text_safe_bbox": [805.0, 255.0, 925.0, 545.0],
            }
        ],
        visual_elements=[],
    )

    assert result["schema"] == "cyberppt.dual_image.page_understanding.v1"
    assert result["page_number"] == 11
    assert result["coordinate_context"]["normalized_canvas"] == {"width": 1672.0, "height": 941.0}
    assert result["containers"][0]["id"] == "operator_card"
    assert result["text_evidence"][0]["truth_role"] == "locator_and_style_evidence"
    assert result["valid"] is True
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_page_understanding_builds_normalized_contract -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.dual_image_overlay.page_understanding'`.

- [ ] **Step 3: Implement minimal contract builder**

Create `scripts/dual_image_overlay/page_understanding.py`:

```python
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "cyberppt.dual_image.page_understanding.v1"
DEFAULT_CANVAS = {"width": 1672.0, "height": 941.0}


def _bbox_xyxy(value: Any) -> list[float] | None:
    if isinstance(value, list) and len(value) == 4:
        try:
            return [float(item) for item in value]
        except (TypeError, ValueError):
            return None
    if isinstance(value, dict):
        if isinstance(value.get("bbox"), list):
            return _bbox_xyxy(value["bbox"])
        try:
            x = float(value.get("x", 0.0) or 0.0)
            y = float(value.get("y", 0.0) or 0.0)
            w = float(value.get("w", value.get("width", 0.0)) or 0.0)
            h = float(value.get("h", value.get("height", 0.0)) or 0.0)
        except (TypeError, ValueError):
            return None
        return [x, y, x + w, y + h]
    return None


def _hash_path(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _container_payload(container: dict[str, Any]) -> dict[str, Any] | None:
    bbox = _bbox_xyxy(container.get("bbox") or container)
    if not bbox:
        return None
    safe = _bbox_xyxy(container.get("text_safe_bbox") or container.get("text_safe_bbox_px") or bbox) or bbox
    return {
        "id": str(container.get("id") or ""),
        "role": str(container.get("role") or "container"),
        "bbox": bbox,
        "text_safe_bbox": safe,
        "evidence": ["semantic_container"],
    }


def _text_payload(item: dict[str, Any], index: int) -> dict[str, Any] | None:
    bbox = _bbox_xyxy(item.get("bbox") or item)
    text = str(item.get("rendered_text") or item.get("text") or "").strip()
    if not bbox or not text:
        return None
    return {
        "id": str(item.get("id") or f"text_{index:03d}"),
        "text": text,
        "bbox": bbox,
        "container_id": item.get("container_id"),
        "role": item.get("role") or item.get("semantic_role"),
        "truth_role": "locator_and_style_evidence",
        "style": {
            "font_size": item.get("font_size"),
            "fill": item.get("fill"),
            "font_weight": item.get("font_weight"),
            "align": item.get("align"),
            "word_wrap": bool(item.get("word_wrap") or "\n" in text),
        },
        "evidence": [str(item.get("source") or "text_item")],
    }


def build_page_understanding(
    *,
    page_number: int,
    full_image: Path | None,
    background_image: Path | None,
    text_items: list[dict[str, Any]],
    containers: list[dict[str, Any]],
    visual_elements: list[dict[str, Any]],
    typography: list[dict[str, Any]] | None = None,
    scene_graph: dict[str, Any] | None = None,
    render_qa: dict[str, Any] | None = None,
    canvas: dict[str, float] | None = None,
) -> dict[str, Any]:
    normalized_canvas = {
        "width": float((canvas or DEFAULT_CANVAS).get("width", 1672.0)),
        "height": float((canvas or DEFAULT_CANVAS).get("height", 941.0)),
    }
    container_payloads = [payload for item in containers if (payload := _container_payload(item))]
    text_payloads = [payload for index, item in enumerate(text_items, start=1) if (payload := _text_payload(item, index))]
    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "valid": bool(container_payloads or text_payloads),
        "coordinate_context": {"normalized_canvas": normalized_canvas},
        "cache_signature": {
            "full_sha256": _hash_path(full_image),
            "background_sha256": _hash_path(background_image),
            "text_count": len(text_payloads),
            "container_count": len(container_payloads),
            "visual_element_count": len(visual_elements),
        },
        "containers": container_payloads,
        "text_evidence": text_payloads,
        "visual_evidence": visual_elements,
        "typography_evidence": typography or [],
        "scene_graph_evidence_available": bool(scene_graph),
        "render_qa_evidence_available": bool(render_qa),
        "writable_regions": [],
        "reserved_regions": [],
        "alignment_groups": [],
        "layout_intents": [],
        "issues": [],
        "error_count": 0,
    }


def write_page_understanding(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
```

- [ ] **Step 4: Run task tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/page_understanding.py tests/test_dual_image_overlay_page_understanding.py
git commit -m "feat: add dual-image page understanding contract"
```

---

### Task 2: Text Style And Alignment Evidence Extraction

**Files:**
- Modify: `scripts/dual_image_overlay/page_understanding.py`
- Modify: `tests/test_dual_image_overlay_page_understanding.py`

**Interfaces:**
- Produces text evidence fields: `style.font_size`, `style.fill`, `style.font_weight`, `style.align`, `style.word_wrap`, `style.line_count`, `style.estimated_line_height`, `style.text_units`
- Produces: `alignment_groups[]` with `axis`, `member_ids`, `anchor`, `spread`

- [ ] **Step 1: Write failing tests for style samples and alignment grouping**

Append:

```python
def test_page_understanding_extracts_text_style_samples_and_alignment_groups() -> None:
    result = build_page_understanding(
        page_number=11,
        full_image=None,
        background_image=None,
        containers=[],
        visual_elements=[],
        text_items=[
            {"id": "a", "text": "目录发布\n（非本场景原文展开重点）", "bbox": [220, 480, 285, 515], "font_size": 8.6, "font_weight": "400", "fill": "#0B1F3D", "align": "center"},
            {"id": "b", "text": "主体认证\n（非本场景原文展开重点）", "bbox": [318, 480, 383, 515], "font_size": 8.6, "font_weight": "400", "fill": "#0B1F3D", "align": "center"},
            {"id": "c", "text": "数据授权\n（非本场景原文展开重点）", "bbox": [414, 480, 479, 515], "font_size": 8.6, "font_weight": "400", "fill": "#0B1F3D", "align": "center"},
        ],
    )

    first_style = result["text_evidence"][0]["style"]
    assert first_style["line_count"] == 2
    assert first_style["estimated_line_height"] > 0
    assert first_style["text_units"] > 0
    assert any(group["axis"] == "row" and set(group["member_ids"]) == {"a", "b", "c"} for group in result["alignment_groups"])
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_page_understanding_extracts_text_style_samples_and_alignment_groups -q
```

Expected: FAIL with missing `line_count` or missing row alignment group.

- [ ] **Step 3: Implement style and alignment helpers**

In `page_understanding.py`, add:

```python
def _text_units(text: str) -> float:
    units = 0.0
    for char in str(text):
        if ord(char) > 127:
            units += 1.0
        elif char.isspace():
            units += 0.3
        elif char.isdigit() or char in ".%":
            units += 0.58
        else:
            units += 0.56
    return round(max(units, 1.0), 3)


def _center(bbox: list[float]) -> tuple[float, float]:
    return ((bbox[0] + bbox[2]) / 2.0, (bbox[1] + bbox[3]) / 2.0)


def _alignment_groups(text_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    rows: list[list[dict[str, Any]]] = []
    for item in sorted(text_payloads, key=lambda payload: _center(payload["bbox"])[1]):
        center_y = _center(item["bbox"])[1]
        row = next((candidate for candidate in rows if abs(_center(candidate[0]["bbox"])[1] - center_y) <= 6.0), None)
        if row is None:
            rows.append([item])
        else:
            row.append(item)
    for index, row in enumerate(rows, start=1):
        if len(row) < 3:
            continue
        centers = [_center(item["bbox"])[1] for item in row]
        groups.append(
            {
                "id": f"row_alignment_{index:03d}",
                "axis": "row",
                "member_ids": [str(item["id"]) for item in row],
                "anchor": round(sum(centers) / len(centers), 3),
                "spread": round(max(centers) - min(centers), 3),
            }
        )
    return groups
```

Update `_text_payload()` style block:

```python
line_count = max(1, len(text.splitlines()))
font_size = item.get("font_size")
try:
    font_size_value = float(font_size)
except (TypeError, ValueError):
    font_size_value = 9.0
style = {
    "font_size": item.get("font_size"),
    "fill": item.get("fill"),
    "font_weight": item.get("font_weight"),
    "align": item.get("align"),
    "word_wrap": bool(item.get("word_wrap") or "\n" in text),
    "line_count": line_count,
    "estimated_line_height": round(font_size_value * 1.6, 3),
    "text_units": _text_units(text),
}
```

Update return payload:

```python
"alignment_groups": _alignment_groups(text_payloads),
```

- [ ] **Step 4: Run tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/page_understanding.py tests/test_dual_image_overlay_page_understanding.py
git commit -m "feat: extract text style and alignment evidence"
```

---

### Task 3: Writable And Reserved Region Fusion

**Files:**
- Modify: `scripts/dual_image_overlay/page_understanding.py`
- Modify: `scripts/dual_image_overlay/container_workspace.py`
- Modify: `tests/test_dual_image_overlay_page_understanding.py`
- Modify: `tests/test_container_workspace.py`

**Interfaces:**
- Produces `writable_regions[]`: `{id, container_id, bbox, source, evidence, confidence}`
- Produces `reserved_regions[]`: `{id, container_id, bbox, kind, source, evidence, confidence}`
- Consumes in `build_container_workspace(..., page_understanding: dict[str, Any] | None = None)`

- [ ] **Step 1: Write failing page-understanding fusion test**

Append:

```python
def test_page_understanding_marks_source_text_overlap_as_writable_region() -> None:
    result = build_page_understanding(
        page_number=11,
        full_image=None,
        background_image=None,
        containers=[
            {"id": "service_card", "role": "card", "bbox": [620, 205, 808, 560], "text_safe_bbox": [622, 388, 792, 556]}
        ],
        text_items=[
            {"id": "body", "text": "公证合同：对接公证处实现合同公证", "bbox": [631, 471, 790, 538], "container_id": "service_card", "role": "body"}
        ],
        visual_elements=[
            {"element_id": "text_surface", "element_type": "shape", "blueprint_bbox_px": [626, 460, 794, 546], "source": {"inventory_source": "background_visual_component"}},
            {"element_id": "side_icon", "element_type": "icon", "blueprint_bbox_px": [622, 410, 646, 442], "source": {"inventory_source": "background_visual_component"}},
        ],
    )

    assert any(region["id"] == "text_surface" for region in result["writable_regions"])
    assert any(region["id"] == "side_icon" for region in result["reserved_regions"])
```

- [ ] **Step 2: Write failing container workspace consumption test**

Append to `tests/test_container_workspace.py`:

```python
def test_container_workspace_consumes_page_understanding_regions() -> None:
    workspace = build_container_workspace(
        page_number=11,
        stage="template",
        containers=[
            {"id": "card", "role": "card", "bbox": [100, 100, 250, 220], "text_safe_bbox": [110, 110, 240, 210]}
        ],
        text_items=[{"text": "长文本", "role": "body", "container_id": "card", "bbox": [115, 150, 235, 190]}],
        visual_elements=[],
        page_understanding={
            "writable_regions": [{"id": "text_surface", "container_id": "card", "bbox": [112, 145, 238, 195]}],
            "reserved_regions": [{"id": "icon", "container_id": "card", "bbox": [112, 112, 140, 140], "kind": "icon"}],
        },
    )

    container = workspace["containers"][0]
    assert any(zone["element_id"] == "icon" for zone in container["occupied_zones"])
    assert all(zone["element_id"] != "text_surface" for zone in container["occupied_zones"])
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_page_understanding_marks_source_text_overlap_as_writable_region tests/test_container_workspace.py::test_container_workspace_consumes_page_understanding_regions -q
```

Expected: FAIL because writable/reserved fusion and container workspace parameter do not exist.

- [ ] **Step 4: Implement fusion in page understanding**

Add helpers in `page_understanding.py`:

```python
def _area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _intersection(a: list[float], b: list[float]) -> float:
    return max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))


def _visual_bbox(element: dict[str, Any]) -> list[float] | None:
    return _bbox_xyxy(element.get("blueprint_bbox_px") or element.get("render_bbox_px") or element.get("bbox"))


def _container_for_bbox(bbox: list[float], containers: list[dict[str, Any]]) -> str | None:
    center_x = (bbox[0] + bbox[2]) / 2.0
    center_y = (bbox[1] + bbox[3]) / 2.0
    for container in containers:
        cb = container["bbox"]
        if cb[0] <= center_x <= cb[2] and cb[1] <= center_y <= cb[3]:
            return str(container["id"])
    return None


def _regions(
    visual_elements: list[dict[str, Any]],
    text_payloads: list[dict[str, Any]],
    container_payloads: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    writable: list[dict[str, Any]] = []
    reserved: list[dict[str, Any]] = []
    for index, element in enumerate(visual_elements, start=1):
        bbox = _visual_bbox(element)
        if not bbox:
            continue
        kind = str(element.get("element_type") or element.get("type") or element.get("kind") or "visual").lower()
        element_id = str(element.get("element_id") or element.get("id") or f"visual_{index:03d}")
        container_id = _container_for_bbox(bbox, container_payloads)
        text_overlap = any(
            payload.get("container_id") == container_id
            and _area(bbox) > 0
            and _area(payload["bbox"]) > 0
            and _intersection(bbox, payload["bbox"]) / min(_area(bbox), _area(payload["bbox"])) >= 0.55
            for payload in text_payloads
        )
        if kind in {"shape", "visual", "decoration"} and text_overlap:
            writable.append({"id": element_id, "container_id": container_id, "bbox": bbox, "source": "source_text_overlap", "evidence": ["text_overlap"], "confidence": 0.8})
        elif kind not in {"container", "text", "text_box", "text_zone", "label_zone"}:
            reserved.append({"id": element_id, "container_id": container_id, "bbox": bbox, "kind": kind, "source": "visual_element", "evidence": ["visual_registry"], "confidence": 0.8})
    return writable, reserved
```

Update `build_page_understanding()` before return:

```python
writable_regions, reserved_regions = _regions(visual_elements, text_payloads, container_payloads)
```

Update return:

```python
"writable_regions": writable_regions,
"reserved_regions": reserved_regions,
```

- [ ] **Step 5: Implement container workspace consumption**

Update `build_container_workspace()` signature in `container_workspace.py`:

```python
def build_container_workspace(
    *,
    page_number: int | None,
    containers: list[Any],
    text_items: list[dict[str, Any]],
    stage: str,
    visual_elements: list[dict[str, Any]] | None = None,
    background_image: Path | None = None,
    page_understanding: dict[str, Any] | None = None,
) -> dict[str, Any]:
```

Add helper:

```python
def _understanding_reserved_zones(container_id: str, page_understanding: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(page_understanding, dict):
        return []
    zones: list[dict[str, Any]] = []
    for index, region in enumerate(page_understanding.get("reserved_regions", []), start=1):
        if not isinstance(region, dict) or str(region.get("container_id") or "") != container_id:
            continue
        rect = _rect_from_xyxy(_bbox_xyxy(region.get("bbox")))
        if _rect_area(rect) <= 0:
            continue
        zones.append({"id": f"{container_id}_understanding_reserved_{index:03d}", "kind": region.get("kind") or "reserved", "source": "page_understanding", "element_id": region.get("id"), "bbox": rect})
    return zones
```

Include in `occupied_zones` after `_text_occupied_zones(...)`:

```python
*_understanding_reserved_zones(container_id, page_understanding),
```

- [ ] **Step 6: Run task tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py tests/test_container_workspace.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/dual_image_overlay/page_understanding.py scripts/dual_image_overlay/container_workspace.py tests/test_dual_image_overlay_page_understanding.py tests/test_container_workspace.py
git commit -m "feat: fuse writable and reserved page regions"
```

---

### Task 4: Layout Intents And Fit Policy Handoff

**Files:**
- Modify: `scripts/dual_image_overlay/page_understanding.py`
- Modify: `scripts/dual_image_overlay/scene_graph/builder.py`
- Modify: `scripts/dual_image_overlay/office_textbox_fit.py`
- Modify: `tests/test_dual_image_overlay_page_understanding.py`
- Modify: `tests/test_scene_graph_builder.py`
- Modify: `tests/test_office_textbox_fit.py`

**Interfaces:**
- Produces `layout_intents[]` with `{id, text_id, container_id, intent, policy}`
- `policy.fit_order`: `["wrap", "shrink_font", "tighten_line_height", "fail"]`
- `policy.preferred_min_font_size_pt`: `9.0`
- `policy.absolute_min_font_size_pt`: `6.5`
- `office_textbox_fit.apply_office_textbox_fit(..., page_understanding: dict[str, Any] | None = None)`

- [ ] **Step 1: Write failing layout intent test**

Append:

```python
def test_page_understanding_emits_wrap_then_shrink_layout_intent_for_container_text() -> None:
    result = build_page_understanding(
        page_number=11,
        full_image=None,
        background_image=None,
        containers=[{"id": "node", "role": "process_node", "bbox": [200, 380, 280, 450], "text_safe_bbox": [205, 400, 275, 440]}],
        text_items=[{"id": "node_body", "text": "履约节点自动触发合同条款代码化执行", "bbox": [206, 406, 274, 434], "container_id": "node", "role": "body", "font_size": 12.0}],
        visual_elements=[],
    )

    intent = result["layout_intents"][0]
    assert intent["text_id"] == "node_body"
    assert intent["intent"] == "fit_inside_container"
    assert intent["policy"]["fit_order"] == ["wrap", "shrink_font", "tighten_line_height", "fail"]
    assert intent["policy"]["absolute_min_font_size_pt"] == 6.5
```

- [ ] **Step 2: Write failing Office fit policy consumption test**

Append to `tests/test_office_textbox_fit.py`:

```python
def test_office_textbox_fit_consumes_page_understanding_fit_policy() -> None:
    boxes = [{"id": "node_body", "text": "履约节点自动触发合同条款代码化执行", "role": "body", "bbox": [205, 400, 275, 414], "font_size": 12.0, "align": "left"}]
    page_understanding = {
        "layout_intents": [
            {
                "text_id": "node_body",
                "container_id": "node",
                "intent": "fit_inside_container",
                "policy": {
                    "fit_order": ["wrap", "shrink_font", "tighten_line_height", "fail"],
                    "preferred_min_font_size_pt": 9.0,
                    "absolute_min_font_size_pt": 6.5,
                },
            }
        ]
    }
    assignment = {"assignments": [{"text_index": 0, "assigned_slot": "slot", "slot_bbox": {"x": 205, "y": 400, "w": 70, "h": 42}}]}

    fitted, report = apply_office_textbox_fit(
        boxes,
        canvas={"width": 1672, "height": 941},
        workspace_assignment=assignment,
        page_understanding=page_understanding,
    )

    assert fitted[0]["wrap"] is True
    assert fitted[0]["font_size"] >= 6.5
    assert report["checks"]["page_understanding_fit_policy_consumed"] is True
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_page_understanding_emits_wrap_then_shrink_layout_intent_for_container_text tests/test_office_textbox_fit.py::test_office_textbox_fit_consumes_page_understanding_fit_policy -q
```

Expected: FAIL due missing layout intent and missing `page_understanding` argument.

- [ ] **Step 4: Emit layout intents**

Add in `page_understanding.py`:

```python
def _layout_intents(text_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    intents: list[dict[str, Any]] = []
    for index, text in enumerate(text_payloads, start=1):
        container_id = text.get("container_id")
        if not container_id:
            continue
        intents.append(
            {
                "id": f"layout_intent_{index:03d}",
                "text_id": text["id"],
                "container_id": container_id,
                "intent": "fit_inside_container",
                "policy": {
                    "fit_order": ["wrap", "shrink_font", "tighten_line_height", "fail"],
                    "preferred_min_font_size_pt": 9.0,
                    "absolute_min_font_size_pt": 6.5,
                },
            }
        )
    return intents
```

Update return:

```python
"layout_intents": _layout_intents(text_payloads),
```

- [ ] **Step 5: Consume fit policy in Office fit**

Modify `apply_office_textbox_fit()` signature:

```python
page_understanding: dict[str, Any] | None = None,
```

Add helper:

```python
def _fit_policy_by_text_id(page_understanding: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(page_understanding, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for intent in page_understanding.get("layout_intents", []):
        if isinstance(intent, dict) and isinstance(intent.get("policy"), dict) and intent.get("text_id"):
            result[str(intent["text_id"])] = intent["policy"]
    return result
```

Inside `apply_office_textbox_fit()` before loop:

```python
fit_policy_map = _fit_policy_by_text_id(page_understanding)
fit_policy_consumed = False
```

Inside loop after `text = ...`:

```python
policy = fit_policy_map.get(str(box.get("id") or ""))
local_min_font_size = float(policy.get("preferred_min_font_size_pt", min_font_size)) if policy else min_font_size
local_absolute_min_font_size = float(policy.get("absolute_min_font_size_pt", absolute_min_font_size)) if policy else absolute_min_font_size
local_allow_wrap = allow_wrap and (not policy or "wrap" in policy.get("fit_order", []))
fit_policy_consumed = fit_policy_consumed or bool(policy)
```

Replace uses of `min_font_size`, `absolute_min_font_size`, and `allow_wrap` in the per-box fit block with the local variables.

Update report checks:

```python
"page_understanding_fit_policy_consumed": fit_policy_consumed,
```

- [ ] **Step 6: Run tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py tests/test_office_textbox_fit.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add scripts/dual_image_overlay/page_understanding.py scripts/dual_image_overlay/office_textbox_fit.py tests/test_dual_image_overlay_page_understanding.py tests/test_office_textbox_fit.py
git commit -m "feat: hand off layout fit policies from page understanding"
```

---

### Task 5: Wire Page Understanding Into Overlay And Template Rebuild

**Files:**
- Modify: `scripts/dual_image_overlay/build_page.py`
- Modify: `scripts/dual_image_overlay/template_rebuild.py`
- Modify: `scripts/dual_image_overlay/source_capture.py`
- Modify: `scripts/dual_image_overlay/production_readiness.py`
- Modify: `scripts/dual_image_overlay/default_quality_rules.json`
- Modify: `scripts/dual_image_overlay/build_quality_rules.json`
- Modify: `scripts/dual_image_overlay/postflight_quality_rules.json`
- Modify: `tests/test_dual_image_overlay_build_page.py`
- Modify: `tests/test_dual_image_overlay_template_rebuild.py`
- Modify: `tests/test_production_readiness.py`

**Interfaces:**
- Overlay writes: `analysis/page_understanding/page_XXX_page_understanding.json`
- Template rebuild writes: `analysis/page_understanding/page_XXX_page_understanding.json` and `analysis/page_understanding/page_understanding_index.json`
- `source_capture.json.inputs.page_understanding_available: true`
- `production_readiness.checks.page_understanding_consumed: true`

- [ ] **Step 1: Write failing overlay build test**

Modify `tests/test_dual_image_overlay_build_page.py` existing build-page test to assert:

```python
self.assertTrue((out_dir / "analysis/page_understanding/page_001_page_understanding.json").is_file())
page_understanding = json.loads((out_dir / "analysis/page_understanding/page_001_page_understanding.json").read_text(encoding="utf-8"))
self.assertEqual("cyberppt.dual_image.page_understanding.v1", page_understanding["schema"])
self.assertTrue(page_understanding["valid"])
```

- [ ] **Step 2: Write failing template rebuild test**

Modify `tests/test_dual_image_overlay_template_rebuild.py` template source-capture test to assert:

```python
understanding_index = project / "analysis/page_understanding/page_understanding_index.json"
self.assertTrue(understanding_index.is_file())
payload = json.loads(understanding_index.read_text(encoding="utf-8"))
self.assertEqual("cyberppt.dual_image.page_understanding_set.v1", payload["schema"])
self.assertTrue(payload["valid"])
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_build_page.py tests/test_dual_image_overlay_template_rebuild.py -q
```

Expected: FAIL due missing page-understanding artifacts.

- [ ] **Step 4: Wire overlay build_page**

In `build_page.py`, import:

```python
from .page_understanding import build_page_understanding, write_page_understanding
```

After `workspace_assignment` is written and before `apply_office_textbox_fit()`, add:

```python
page_understanding = build_page_understanding(
    page_number=args.page_number,
    full_image=full_norm,
    background_image=background_norm,
    text_items=boxes,
    containers=[container.__dict__ if hasattr(container, "__dict__") else container for container in plan.containers],
    visual_elements=[],
    typography=None,
)
page_understanding_path = analysis / "page_understanding" / f"page_{args.page_number:03d}_page_understanding.json"
write_page_understanding(page_understanding_path, page_understanding)
```

Pass into fit:

```python
page_understanding=page_understanding,
```

Update mapping:

```python
"page_understanding": str(page_understanding_path),
```

- [ ] **Step 5: Wire template_rebuild**

In `template_rebuild.py`, import:

```python
from .page_understanding import build_page_understanding, write_page_understanding
```

In `_build_template_container_workspaces()`, before `build_container_workspace(...)`, build and write:

```python
understanding = build_page_understanding(
    page_number=page_number if isinstance(page_number, int) else 0,
    full_image=None,
    background_image=None,
    text_items=text_items,
    containers=containers,
    visual_elements=visual_elements,
    scene_graph=page.get("scene_graph") if isinstance(page.get("scene_graph"), dict) else None,
)
if isinstance(page_number, int):
    write_page_understanding(
        project_path / "analysis" / "page_understanding" / f"page_{page_number:03d}_page_understanding.json",
        understanding,
    )
```

Pass into `build_container_workspace()`:

```python
page_understanding=understanding,
```

After page loop, write index:

```python
_write_json(
    project_path / "analysis" / "page_understanding" / "page_understanding_index.json",
    {
        "schema": "cyberppt.dual_image.page_understanding_set.v1",
        "valid": bool(pages),
        "page_count": len(pages),
        "pages": [
            str(path)
            for path in sorted((project_path / "analysis" / "page_understanding").glob("page_*_page_understanding.json"))
        ],
    },
)
```

- [ ] **Step 6: Wire source capture and readiness**

In `source_capture.py`, include the page-understanding index/path under `inputs` when `analysis/page_understanding` exists:

```python
"page_understanding_available": (project_dir / "analysis" / "page_understanding").exists(),
"page_understanding_dir": str(project_dir / "analysis" / "page_understanding"),
```

In `production_readiness.py`, add `page_understanding` to required artifacts/checks:

```python
REQUIRED_ARTIFACTS = [
    "source_capture",
    "semantic_plan",
    "visual_registry",
    "container_workspace",
    "workspace_assignment",
    "office_textbox_fit",
    "page_understanding",
]
```

Add quality rule entries with kind `report_valid` for the page-understanding report/index in the three quality rules JSON files.

- [ ] **Step 7: Run integration tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_build_page.py tests/test_dual_image_overlay_template_rebuild.py tests/test_production_readiness.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add scripts/dual_image_overlay/build_page.py scripts/dual_image_overlay/template_rebuild.py scripts/dual_image_overlay/source_capture.py scripts/dual_image_overlay/production_readiness.py scripts/dual_image_overlay/default_quality_rules.json scripts/dual_image_overlay/build_quality_rules.json scripts/dual_image_overlay/postflight_quality_rules.json tests/test_dual_image_overlay_build_page.py tests/test_dual_image_overlay_template_rebuild.py tests/test_production_readiness.py
git commit -m "feat: wire page understanding into dual-image rebuild"
```

---

### Task 6: Cache Signatures And QA Feedback Ingestion

**Files:**
- Modify: `scripts/dual_image_overlay/page_understanding.py`
- Modify: `scripts/dual_image_overlay/source_capture.py`
- Modify: `tests/test_dual_image_overlay_page_understanding.py`
- Modify: `tests/test_dual_image_overlay_source_capture.py`

**Interfaces:**
- Produces `cache_signature.inputs_sha256`
- Produces `qa_feedback[]` from render QA or visual QA issues
- Produces invalidation rules: if image hash and text/container/visual counts match, expensive image-derived evidence can be reused.

- [ ] **Step 1: Write failing cache and QA feedback test**

Append:

```python
def test_page_understanding_records_cache_signature_and_qa_feedback() -> None:
    result = build_page_understanding(
        page_number=11,
        full_image=None,
        background_image=None,
        containers=[],
        text_items=[],
        visual_elements=[],
        render_qa={
            "issues": [
                {"code": "text_overflow", "text_id": "body", "message": "Text overflowed container"},
                {"code": "style_mismatch", "text_id": "title", "message": "Font size too large"},
            ]
        },
    )

    assert "inputs_sha256" in result["cache_signature"]
    assert result["qa_feedback"][0]["code"] == "text_overflow"
    assert result["qa_feedback"][0]["recommended_hint"] == "wrap_or_shrink_inside_container"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_page_understanding_records_cache_signature_and_qa_feedback -q
```

Expected: FAIL due missing `inputs_sha256` and `qa_feedback`.

- [ ] **Step 3: Implement deterministic signature and QA feedback mapping**

Add in `page_understanding.py`:

```python
def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _qa_feedback(render_qa: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(render_qa, dict):
        return []
    feedback: list[dict[str, Any]] = []
    hint_by_code = {
        "text_overflow": "wrap_or_shrink_inside_container",
        "text_outside_container": "rebind_to_writable_region",
        "style_mismatch": "resample_source_text_style",
        "text_overlap_reserved_zone": "subtract_reserved_zone_or_move_text",
    }
    for issue in render_qa.get("issues", []):
        if not isinstance(issue, dict):
            continue
        code = str(issue.get("code") or "")
        feedback.append(
            {
                "code": code,
                "text_id": issue.get("text_id"),
                "message": issue.get("message"),
                "recommended_hint": hint_by_code.get(code, "review_layout_intent"),
            }
        )
    return feedback
```

Update `cache_signature` after building the dict:

```python
signature = {
    "full_sha256": _hash_path(full_image),
    "background_sha256": _hash_path(background_image),
    "text_count": len(text_payloads),
    "container_count": len(container_payloads),
    "visual_element_count": len(visual_elements),
}
signature["inputs_sha256"] = _stable_hash(signature)
```

Update return:

```python
"cache_signature": signature,
"qa_feedback": _qa_feedback(render_qa),
```

- [ ] **Step 4: Run tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py tests/test_dual_image_overlay_source_capture.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/dual_image_overlay/page_understanding.py scripts/dual_image_overlay/source_capture.py tests/test_dual_image_overlay_page_understanding.py tests/test_dual_image_overlay_source_capture.py
git commit -m "feat: add page-understanding cache and QA feedback"
```

---

## Final Verification

- [ ] Run targeted unit and integration tests:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py tests/test_container_workspace.py tests/test_workspace_assignment.py tests/test_office_textbox_fit.py tests/test_dual_image_overlay_build_page.py tests/test_dual_image_overlay_template_rebuild.py tests/test_production_readiness.py tests/test_dual_image_overlay_qa_registry.py -q
```

Expected: PASS.

- [ ] Run GitNexus change detection before commit or PR:

```text
mcp__gitnexus.detect_changes(repo="CyberPPT", scope="all")
```

Expected: risk is not HIGH/CRITICAL. If HIGH/CRITICAL, pause and review affected processes before continuing.

- [ ] Run one real page rebuild smoke test on the P11 project or a small fixture project:

```bash
python3 scripts/dual_image_overlay/rebuild_engine/svg_to_pptx.py projects/power-trusted-data-space-p11
```

Expected: PPTX export succeeds and existing page-understanding artifacts remain valid.

## Self-Review

- Spec coverage: The plan covers unified page understanding, text style extraction, container/writable-region fusion, layout fit policies, cache reuse, QA feedback, and downstream wiring.
- Placeholder scan: No `TBD`, `TODO`, or open-ended implementation placeholders remain.
- Type consistency: `build_page_understanding`, `write_page_understanding`, `page_understanding`, `layout_intents`, `writable_regions`, and `reserved_regions` are named consistently across tasks.
- Scope check: This is one subsystem: the page-understanding layer for the existing dual-image rebuild path. Native object reconstruction remains out of scope.

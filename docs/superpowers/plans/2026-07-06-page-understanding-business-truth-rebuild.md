# Page Understanding Business Truth Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-grade dual-image page-understanding pipeline that uses the text-bearing full image for text location/style evidence, the strict no-text background image for visual/container structure, and the script as the business truth used to verify and correct OCR candidates before generating editable PPT text blocks.

**Architecture:** Introduce `page_understanding.json` as the single geometry and text-truth contract consumed by `scene_graph`, `container_workspace`, `workspace_assignment`, `office_textbox_fit`, `source_capture`, and `template_rebuild`. The pipeline explicitly separates full-image text evidence, background-image structural evidence, script business truth, explicit/implicit containers, block-level fit policy, and human-review triggers.

**Tech Stack:** Python 3.14, existing `scripts/dual_image_overlay` modules, Pillow, pytest, JSON artifacts under `analysis/`, current CyberPPT `dual_image_editable_overlay` and `template-rebuild` flow.

## Global Constraints

- Background images are expected to be strictly text-free; if text remains, mark the page-understanding artifact invalid.
- Do not modify business input text to improve recognition.
- OCR text is allowed as an initial candidate, locator, line-structure, and style source, but final editable text must be verified or corrected against script business truth.
- Preserve full-image line structure by default; do not rewrap business text unless the source image already wraps it or manual review approves.
- If a text block does not fit, apply block-level uniform scaling to font size, line height, and internal line offsets.
- A text block is a grouped editable object: all internal text lines must move together, scale together, and preserve their relative offsets.
- If block-level scale falls below configured review thresholds, add a review item instead of silently accepting an unreadable result.
- Explicit containers come from the no-text background image; implicit text containers come from full-image text evidence when no visible background container exists.
- Normalize all production coordinates to `1672x941`.
- Existing `page_scene_graph.json` remains the layout-facing contract; `page_understanding.json` feeds it instead of replacing it.
- Do not add a new OCR dependency in this revision; consume the existing OCR/layout artifacts already produced by the workflow.
- Preserve current production readiness gates; add consumed-artifact evidence rather than bypassing gates.

---

## File Structure

- Create: `scripts/dual_image_overlay/page_understanding.py`
  - Owns schema construction, image registration metadata, text-block normalization, explicit/implicit container synthesis, container-text binding, fit policies, review queue, artifact writing, and index writing.
- Create: `scripts/dual_image_overlay/text_truth.py`
  - Owns OCR candidate to script-truth alignment, correction decisions, similarity scoring, and review reasons for unmatched or ambiguous business text.
- Create: `scripts/dual_image_overlay/block_fit.py`
  - Owns text-block-level fit calculation and scale thresholds independent of Office export details.
- Create: `scripts/dual_image_overlay/text_block_group.py`
  - Owns conversion from verified text blocks into grouped editable objects with shared transform, line members, relative offsets, and group-level scale.
- Create: `tests/test_dual_image_overlay_page_understanding.py`
  - Unit tests for schema, registration, text evidence, explicit/implicit containers, bindings, review items, and index output.
- Create: `tests/test_dual_image_overlay_text_truth.py`
  - Unit tests for OCR/script alignment, typo correction, line-structure preservation, ambiguity detection, and script-missing review items.
- Create: `tests/test_dual_image_overlay_block_fit.py`
  - Unit tests for uniform text-block scaling, warning/review thresholds, and no per-line independent scaling.
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
  - Builds template-stage page understanding for each page after OCR/layout and semantic/container evidence are available.
- Modify: `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`
  - Uses page-understanding text blocks when available; keeps current OCR/script overlay path as fallback.
- Modify: `scripts/dual_image_overlay/container_workspace.py`
  - Consumes explicit and implicit containers from page understanding before falling back to current inferred containers.
- Modify: `scripts/dual_image_overlay/workspace_assignment.py`
  - Uses page-understanding `container_text_bindings` and fit slots as authoritative assignment evidence.
- Modify: `scripts/dual_image_overlay/office_textbox_fit.py`
  - Applies block-level fit policies and records scale/review status in fit reports.
- Modify: `scripts/dual_image_overlay/source_capture.py`
  - Records page-understanding artifact paths, hashes, and consumption status.
- Modify: `scripts/dual_image_overlay/production_readiness.py`
  - Adds page-understanding validity and consumption checks.
- Modify: `scripts/dual_image_overlay/default_quality_rules.json`, `build_quality_rules.json`, `postflight_quality_rules.json`
  - Adds rules for page-understanding validity, script-truth verification, fit scale, and review queue severity.
- Modify: `tests/test_dual_image_overlay_template_rebuild.py`
  - Adds end-to-end regression around page 13-style OCR fragments becoming one verified editable text block.
- Modify: `tests/test_dual_image_overlay_source_capture.py`
  - Adds consumed-artifact evidence assertions.
- Modify: `tests/test_production_readiness.py`
  - Adds readiness checks for page-understanding artifacts.

---

### Task 1: Page Understanding Contract

**Files:**
- Create: `scripts/dual_image_overlay/page_understanding.py`
- Create: `tests/test_dual_image_overlay_page_understanding.py`

**Interfaces:**
- Produces: `build_page_understanding(...) -> dict[str, Any]`
- Produces: `write_page_understanding(path: Path, payload: dict[str, Any]) -> dict[str, Any]`
- Produces schema: `cyberppt.dual_image.page_understanding.v1`
- Consumes: normalized full/background paths, OCR text items, explicit container candidates, script-truth verification payloads, and visual elements.

- [ ] **Step 1: Write failing schema test**

Add to `tests/test_dual_image_overlay_page_understanding.py`:

```python
from __future__ import annotations

from scripts.dual_image_overlay.page_understanding import build_page_understanding


def test_page_understanding_builds_business_truth_contract() -> None:
    payload = build_page_understanding(
        page_number=13,
        full_image=None,
        background_image=None,
        registration={"valid": True, "transform": "identity"},
        text_blocks=[
            {
                "id": "text_block_001",
                "ocr_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
                "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
                "bbox": [630.0, 464.0, 709.0, 506.0],
                "line_boxes": [
                    [630.0, 464.0, 708.0, 475.0],
                    [643.0, 480.0, 704.0, 491.0],
                    [646.0, 496.0, 708.0, 506.0],
                ],
                "style": {"font_size": 8.5, "font_weight": "700", "fill": "#0B1F3D", "align": "left"},
                "truth": {"status": "script_verified", "similarity": 1.0},
            }
        ],
        explicit_containers=[
            {"id": "stage_6_card", "bbox": [624.0, 420.0, 714.0, 530.0], "source": "background_image"}
        ],
        implicit_containers=[],
        visual_elements=[],
        canvas={"width": 1672.0, "height": 941.0},
    )

    assert payload["schema"] == "cyberppt.dual_image.page_understanding.v1"
    assert payload["valid"] is True
    assert payload["registration"]["valid"] is True
    assert payload["text_blocks"][0]["truth"]["status"] == "script_verified"
    assert payload["containers"][0]["kind"] == "explicit_container"
    assert payload["container_text_bindings"][0]["text_block_id"] == "text_block_001"
    assert payload["container_text_bindings"][0]["container_id"] == "stage_6_card"
    assert payload["review_items"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_page_understanding_builds_business_truth_contract -q
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


def _hash_path(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _xyxy(raw: Any) -> list[float] | None:
    if isinstance(raw, list) and len(raw) == 4:
        try:
            return [float(value) for value in raw]
        except (TypeError, ValueError):
            return None
    if isinstance(raw, dict):
        if isinstance(raw.get("bbox"), list):
            return _xyxy(raw["bbox"])
        try:
            x = float(raw.get("x", 0.0) or 0.0)
            y = float(raw.get("y", 0.0) or 0.0)
            w = float(raw.get("w", raw.get("width", 0.0)) or 0.0)
            h = float(raw.get("h", raw.get("height", 0.0)) or 0.0)
        except (TypeError, ValueError):
            return None
        return [x, y, x + w, y + h]
    return None


def _area(bbox: list[float]) -> float:
    return max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])


def _intersection_ratio(inner: list[float], outer: list[float]) -> float:
    left = max(inner[0], outer[0])
    top = max(inner[1], outer[1])
    right = min(inner[2], outer[2])
    bottom = min(inner[3], outer[3])
    inter = _area([left, top, right, bottom])
    base = max(1.0, _area(inner))
    return inter / base


def _container_payload(raw: dict[str, Any], *, kind: str) -> dict[str, Any] | None:
    bbox = _xyxy(raw.get("bbox") or raw)
    if bbox is None:
        return None
    return {
        "id": str(raw.get("id") or f"{kind}_{len(str(raw))}"),
        "kind": kind,
        "role": str(raw.get("role") or raw.get("kind") or "container"),
        "bbox": bbox,
        "text_safe_bbox": _xyxy(raw.get("text_safe_bbox") or raw.get("text_safe_bbox_px") or bbox) or bbox,
        "source": str(raw.get("source") or ("background_image" if kind == "explicit_container" else "full_image_text_block")),
        "confidence": float(raw.get("confidence", 0.8) or 0.8),
    }


def _text_block_payload(raw: dict[str, Any], index: int) -> dict[str, Any] | None:
    bbox = _xyxy(raw.get("bbox") or raw)
    final_text = str(raw.get("final_text") or raw.get("text") or raw.get("ocr_text") or "").strip()
    if bbox is None or not final_text:
        return None
    line_boxes = [_xyxy(item) for item in raw.get("line_boxes", []) if _xyxy(item) is not None]
    return {
        "id": str(raw.get("id") or f"text_block_{index:03d}"),
        "ocr_text": str(raw.get("ocr_text") or final_text),
        "final_text": final_text,
        "bbox": bbox,
        "line_boxes": line_boxes,
        "style": dict(raw.get("style") or {}),
        "truth": dict(raw.get("truth") or {"status": "ocr_unverified", "similarity": 0.0}),
        "fit_policy": dict(raw.get("fit_policy") or {"mode": "preserve_lines_then_uniform_scale"}),
        "source": str(raw.get("source") or "full_image_ocr"),
    }


def _bind_text_to_containers(text_blocks: list[dict[str, Any]], containers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    bindings: list[dict[str, Any]] = []
    for text in text_blocks:
        text_bbox = text["bbox"]
        ranked = sorted(
            (
                (_intersection_ratio(text_bbox, container["text_safe_bbox"]), container)
                for container in containers
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if ranked and ranked[0][0] >= 0.55:
            bindings.append(
                {
                    "text_block_id": text["id"],
                    "container_id": ranked[0][1]["id"],
                    "method": "bbox_intersection",
                    "confidence": round(ranked[0][0], 3),
                }
            )
    return bindings


def build_page_understanding(
    *,
    page_number: int,
    full_image: Path | None,
    background_image: Path | None,
    registration: dict[str, Any],
    text_blocks: list[dict[str, Any]],
    explicit_containers: list[dict[str, Any]],
    implicit_containers: list[dict[str, Any]],
    visual_elements: list[dict[str, Any]],
    canvas: dict[str, float] | None = None,
) -> dict[str, Any]:
    normalized_canvas = {
        "width": float((canvas or DEFAULT_CANVAS).get("width", 1672.0)),
        "height": float((canvas or DEFAULT_CANVAS).get("height", 941.0)),
    }
    containers = [
        item
        for item in (
            [_container_payload(raw, kind="explicit_container") for raw in explicit_containers]
            + [_container_payload(raw, kind="implicit_text_container") for raw in implicit_containers]
        )
        if item is not None
    ]
    normalized_text_blocks = [
        item
        for item in (_text_block_payload(raw, index) for index, raw in enumerate(text_blocks, start=1))
        if item is not None
    ]
    bindings = _bind_text_to_containers(normalized_text_blocks, containers)
    review_items = [
        {
            "type": "unbound_text_block",
            "text_block_id": text["id"],
            "text": text["final_text"],
            "severity": "warning",
        }
        for text in normalized_text_blocks
        if text["id"] not in {binding["text_block_id"] for binding in bindings}
    ]
    valid = bool(registration.get("valid", False)) and bool(normalized_text_blocks) and not any(
        item["severity"] == "error" for item in review_items
    )
    return {
        "schema": SCHEMA,
        "page_number": page_number,
        "valid": valid,
        "coordinate_context": {"normalized_canvas": normalized_canvas},
        "cache_signature": {
            "full_sha256": _hash_path(full_image),
            "background_sha256": _hash_path(background_image),
            "text_block_count": len(normalized_text_blocks),
            "container_count": len(containers),
            "visual_element_count": len(visual_elements),
        },
        "registration": registration,
        "containers": containers,
        "text_blocks": normalized_text_blocks,
        "container_text_bindings": bindings,
        "visual_elements": visual_elements,
        "review_items": review_items,
        "error_count": sum(1 for item in review_items if item["severity"] == "error"),
        "warning_count": sum(1 for item in review_items if item["severity"] == "warning"),
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

- [ ] **Step 5: Commit task**

```bash
git add scripts/dual_image_overlay/page_understanding.py tests/test_dual_image_overlay_page_understanding.py
git commit -m "feat: add page understanding contract"
```

---

### Task 2: OCR Candidate To Script Truth Verification

**Files:**
- Create: `scripts/dual_image_overlay/text_truth.py`
- Create: `tests/test_dual_image_overlay_text_truth.py`

**Interfaces:**
- Produces: `verify_text_blocks_against_script(text_blocks: list[dict[str, Any]], script_truth_lines: list[str]) -> list[dict[str, Any]]`
- Consumes: text blocks with `ocr_text`, `bbox`, `line_boxes`, and `style`
- Produces text blocks with `final_text`, `truth.status`, `truth.similarity`, and review-ready `truth.reason`

- [ ] **Step 1: Write failing typo-correction test**

Create `tests/test_dual_image_overlay_text_truth.py`:

```python
from __future__ import annotations

from scripts.dual_image_overlay.text_truth import verify_text_blocks_against_script


def test_text_truth_corrects_ocr_typo_using_script_truth() -> None:
    result = verify_text_blocks_against_script(
        [
            {
                "id": "text_block_001",
                "ocr_text": "融资申请→风控审孩\n→放款→还款\n全流程线上化",
                "bbox": [630.0, 464.0, 709.0, 506.0],
                "line_boxes": [
                    [630.0, 464.0, 708.0, 475.0],
                    [643.0, 480.0, 704.0, 491.0],
                    [646.0, 496.0, 708.0, 506.0],
                ],
                "style": {"font_size": 8.5, "font_weight": "700"},
            }
        ],
        ["融资申请→风控审核→放款→还款，全流程线上化"],
    )

    assert result[0]["final_text"] == "融资申请→风控审核\n→放款→还款\n全流程线上化"
    assert result[0]["truth"]["status"] == "script_verified"
    assert result[0]["truth"]["similarity"] >= 0.8
    assert result[0]["line_boxes"][1] == [643.0, 480.0, 704.0, 491.0]
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_text_truth.py::test_text_truth_corrects_ocr_typo_using_script_truth -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement script-truth verifier**

Create `scripts/dual_image_overlay/text_truth.py`:

```python
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


def normalize_text(text: str) -> str:
    return re.sub(r"[\s,，。:：;；、（）()【】\\[\\]\"'“”‘’]+", "", str(text)).lower()


def _line_lengths(lines: list[str]) -> list[int]:
    return [len(normalize_text(line)) for line in lines]


def _split_script_text_to_ocr_lines(script_text: str, ocr_lines: list[str]) -> str:
    normalized_script = str(script_text).replace("，", "").replace(",", "")
    if len(ocr_lines) <= 1:
        return normalized_script
    lengths = _line_lengths(ocr_lines)
    normalized = normalize_text(normalized_script)
    lines: list[str] = []
    cursor = 0
    for index, length in enumerate(lengths):
        if index == len(lengths) - 1:
            lines.append(normalized[cursor:])
        else:
            lines.append(normalized[cursor : cursor + length])
            cursor += length
    return "\n".join(line for line in lines if line)


def _best_script_match(ocr_text: str, script_truth_lines: list[str]) -> tuple[str, float]:
    ocr_key = normalize_text(ocr_text)
    best_text = ""
    best_score = 0.0
    for line in script_truth_lines:
        line_key = normalize_text(line)
        if not line_key:
            continue
        score = SequenceMatcher(None, ocr_key, line_key).ratio()
        if ocr_key in line_key or line_key in ocr_key:
            score = max(score, min(len(ocr_key), len(line_key)) / max(len(ocr_key), len(line_key)))
        if score > best_score:
            best_text = line
            best_score = score
    return best_text, best_score


def verify_text_blocks_against_script(
    text_blocks: list[dict[str, Any]],
    script_truth_lines: list[str],
    *,
    match_threshold: float = 0.62,
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for block in text_blocks:
        current = dict(block)
        ocr_text = str(block.get("ocr_text") or block.get("text") or "")
        match, score = _best_script_match(ocr_text, script_truth_lines)
        if match and score >= match_threshold:
            ocr_lines = [line for line in ocr_text.splitlines() if line.strip()]
            current["final_text"] = _split_script_text_to_ocr_lines(match, ocr_lines)
            current["truth"] = {
                "status": "script_verified",
                "source": "script_truth",
                "matched_text": match,
                "similarity": round(score, 3),
            }
        else:
            current["final_text"] = ocr_text
            current["truth"] = {
                "status": "review_required",
                "source": "ocr_candidate",
                "matched_text": match,
                "similarity": round(score, 3),
                "reason": "script_truth_match_below_threshold",
            }
        verified.append(current)
    return verified
```

- [ ] **Step 4: Run text truth tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_text_truth.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add scripts/dual_image_overlay/text_truth.py tests/test_dual_image_overlay_text_truth.py
git commit -m "feat: verify OCR candidates against script truth"
```

---

### Task 3: Implicit Text Containers

**Files:**
- Modify: `scripts/dual_image_overlay/page_understanding.py`
- Modify: `tests/test_dual_image_overlay_page_understanding.py`

**Interfaces:**
- Produces: `build_implicit_text_containers(text_blocks: list[dict[str, Any]], explicit_containers: list[dict[str, Any]], visual_elements: list[dict[str, Any]]) -> list[dict[str, Any]]`
- Consumes: verified text blocks, explicit background containers, visual elements
- Produces: implicit containers with `kind="implicit_text_container"` and `source="full_image_text_block"`

- [ ] **Step 1: Write failing implicit-container test**

Append to `tests/test_dual_image_overlay_page_understanding.py`:

```python
from scripts.dual_image_overlay.page_understanding import build_implicit_text_containers


def test_builds_implicit_container_when_background_has_no_visible_box() -> None:
    implicit = build_implicit_text_containers(
        text_blocks=[
            {
                "id": "text_block_note",
                "final_text": "可信机制贯穿全程",
                "bbox": [120.0, 630.0, 310.0, 654.0],
                "line_boxes": [[120.0, 630.0, 310.0, 654.0]],
                "style": {"font_size": 14},
            }
        ],
        explicit_containers=[],
        visual_elements=[{"id": "shield_icon", "bbox": [60.0, 615.0, 105.0, 665.0], "kind": "icon"}],
    )

    assert len(implicit) == 1
    assert implicit[0]["id"] == "implicit_text_block_note"
    assert implicit[0]["kind"] == "implicit_text_container"
    assert implicit[0]["source"] == "full_image_text_block"
    assert implicit[0]["bbox"][0] >= 108.0
    assert implicit[0]["bbox"][1] <= 626.0
    assert implicit[0]["bbox"][2] >= 322.0
    assert implicit[0]["bbox"][3] >= 658.0
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py::test_builds_implicit_container_when_background_has_no_visible_box -q
```

Expected: FAIL with `ImportError: cannot import name 'build_implicit_text_containers'`.

- [ ] **Step 3: Implement implicit container builder**

Add to `scripts/dual_image_overlay/page_understanding.py`:

```python
def _expanded_bbox(bbox: list[float], *, x_pad: float = 12.0, y_pad: float = 6.0) -> list[float]:
    return [
        max(0.0, bbox[0] - x_pad),
        max(0.0, bbox[1] - y_pad),
        min(DEFAULT_CANVAS["width"], bbox[2] + x_pad),
        min(DEFAULT_CANVAS["height"], bbox[3] + y_pad),
    ]


def build_implicit_text_containers(
    text_blocks: list[dict[str, Any]],
    explicit_containers: list[dict[str, Any]],
    visual_elements: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    normalized_explicit = [
        item for item in (_container_payload(container, kind="explicit_container") for container in explicit_containers) if item
    ]
    implicit: list[dict[str, Any]] = []
    for block in text_blocks:
        bbox = _xyxy(block.get("bbox"))
        if bbox is None:
            continue
        if any(_intersection_ratio(bbox, container["text_safe_bbox"]) >= 0.55 for container in normalized_explicit):
            continue
        block_id = str(block.get("id") or f"text_{len(implicit) + 1:03d}")
        implicit.append(
            {
                "id": f"implicit_{block_id}",
                "kind": "implicit_text_container",
                "role": "text_safe_zone",
                "bbox": _expanded_bbox(bbox),
                "text_safe_bbox": _expanded_bbox(bbox),
                "source": "full_image_text_block",
                "text_block_id": block_id,
                "confidence": 0.82,
            }
        )
    return implicit
```

- [ ] **Step 4: Run task tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_page_understanding.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add scripts/dual_image_overlay/page_understanding.py tests/test_dual_image_overlay_page_understanding.py
git commit -m "feat: synthesize implicit text containers"
```

---

### Task 4: Block-Level Fit Policy

**Files:**
- Create: `scripts/dual_image_overlay/block_fit.py`
- Create: `tests/test_dual_image_overlay_block_fit.py`

**Interfaces:**
- Produces: `fit_text_block_to_container(text_block: dict[str, Any], container: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]`
- Consumes: `text_block.final_text`, `text_block.style.font_size`, line boxes, and container `text_safe_bbox`
- Produces: `scale`, `status`, `review_required`, `fitted_style`

- [ ] **Step 1: Write failing uniform-scale test**

Create `tests/test_dual_image_overlay_block_fit.py`:

```python
from __future__ import annotations

from scripts.dual_image_overlay.block_fit import fit_text_block_to_container


def test_fit_text_block_uses_uniform_scale_and_review_threshold() -> None:
    result = fit_text_block_to_container(
        {
            "id": "text_block_001",
            "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
            "bbox": [630.0, 464.0, 709.0, 506.0],
            "line_boxes": [
                [630.0, 464.0, 708.0, 475.0],
                [643.0, 480.0, 704.0, 491.0],
                [646.0, 496.0, 708.0, 506.0],
            ],
            "style": {"font_size": 8.5, "line_height": 1.36},
        },
        {"id": "stage_6_card", "text_safe_bbox": [626.0, 458.0, 714.0, 512.0]},
    )

    assert result["mode"] == "uniform_block_scale"
    assert result["scale"] <= 1.0
    assert result["fitted_style"]["font_size"] <= 8.5
    assert result["review_required"] is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_block_fit.py::test_fit_text_block_uses_uniform_scale_and_review_threshold -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement block fit**

Create `scripts/dual_image_overlay/block_fit.py`:

```python
from __future__ import annotations

from typing import Any


DEFAULT_THRESHOLDS = {
    "auto_pass": 0.85,
    "warning": 0.70,
    "review": 0.60,
}


def _text_width(text: str, font_size: float) -> float:
    width = 0.0
    for char in text:
        width += font_size if ord(char) > 127 else font_size * 0.56
    return width


def _container_size(container: dict[str, Any]) -> tuple[float, float]:
    bbox = container.get("text_safe_bbox") or container.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        return 1.0, 1.0
    return max(1.0, float(bbox[2]) - float(bbox[0])), max(1.0, float(bbox[3]) - float(bbox[1]))


def fit_text_block_to_container(
    text_block: dict[str, Any],
    container: dict[str, Any],
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    active_thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    style = dict(text_block.get("style") or {})
    font_size = float(style.get("font_size") or 12.0)
    line_height = float(style.get("line_height") or 1.36)
    lines = [line for line in str(text_block.get("final_text") or "").splitlines() if line.strip()] or [""]
    container_w, container_h = _container_size(container)
    text_w = max(_text_width(line, font_size) for line in lines)
    text_h = font_size + max(0, len(lines) - 1) * font_size * line_height
    scale = min(1.0, container_w / max(1.0, text_w), container_h / max(1.0, text_h))
    if scale >= active_thresholds["auto_pass"]:
        status = "auto_pass"
        review_required = False
    elif scale >= active_thresholds["warning"]:
        status = "warning"
        review_required = False
    elif scale >= active_thresholds["review"]:
        status = "review_recommended"
        review_required = True
    else:
        status = "blocked_too_small"
        review_required = True
    fitted_style = dict(style)
    fitted_style["font_size"] = round(font_size * scale, 2)
    fitted_style["line_height"] = line_height
    return {
        "mode": "uniform_block_scale",
        "scale": round(scale, 3),
        "status": status,
        "review_required": review_required,
        "fitted_style": fitted_style,
    }
```

- [ ] **Step 4: Run block-fit tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_block_fit.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add scripts/dual_image_overlay/block_fit.py tests/test_dual_image_overlay_block_fit.py
git commit -m "feat: add block-level text fitting"
```

---

### Task 5: Grouped Editable Text Blocks

**Files:**
- Create: `scripts/dual_image_overlay/text_block_group.py`
- Create: `tests/test_dual_image_overlay_text_block_group.py`

**Interfaces:**
- Produces: `build_text_block_group(text_block: dict[str, Any], fit: dict[str, Any] | None = None) -> dict[str, Any]`
- Consumes: `text_block.final_text`, `text_block.line_boxes`, `text_block.style`, and optional block-fit result
- Produces: grouped editable object with `group_id`, `bbox`, `transform`, `members`, `scale`, and `edit_behavior`

- [ ] **Step 1: Write failing group behavior test**

Create `tests/test_dual_image_overlay_text_block_group.py`:

```python
from __future__ import annotations

from scripts.dual_image_overlay.text_block_group import build_text_block_group


def test_text_block_group_preserves_relative_line_offsets_under_scale() -> None:
    group = build_text_block_group(
        {
            "id": "stage_6_flow",
            "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
            "bbox": [630.0, 464.0, 709.0, 506.0],
            "line_boxes": [
                [630.0, 464.0, 708.0, 475.0],
                [643.0, 480.0, 704.0, 491.0],
                [646.0, 496.0, 708.0, 506.0],
            ],
            "style": {"font_size": 8.5, "font_weight": "700", "line_height": 1.36},
        },
        fit={"scale": 0.8, "fitted_style": {"font_size": 6.8, "line_height": 1.36}},
    )

    assert group["group_id"] == "group_stage_6_flow"
    assert group["edit_behavior"] == "move_and_scale_as_group"
    assert group["scale"] == 0.8
    assert group["members"][0]["relative_bbox"] == [0.0, 0.0, 78.0, 11.0]
    assert group["members"][1]["relative_bbox"] == [13.0, 16.0, 74.0, 27.0]
    assert group["members"][2]["relative_bbox"] == [16.0, 32.0, 78.0, 42.0]
    assert group["members"][0]["style"]["font_size"] == 6.8
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_text_block_group.py::test_text_block_group_preserves_relative_line_offsets_under_scale -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement grouped text block builder**

Create `scripts/dual_image_overlay/text_block_group.py`:

```python
from __future__ import annotations

from typing import Any


def _xyxy(raw: Any) -> list[float]:
    if not isinstance(raw, list) or len(raw) != 4:
        return [0.0, 0.0, 1.0, 1.0]
    return [float(value) for value in raw]


def _relative_bbox(line_bbox: list[float], root_bbox: list[float]) -> list[float]:
    return [
        round(line_bbox[0] - root_bbox[0], 2),
        round(line_bbox[1] - root_bbox[1], 2),
        round(line_bbox[2] - root_bbox[0], 2),
        round(line_bbox[3] - root_bbox[1], 2),
    ]


def build_text_block_group(text_block: dict[str, Any], fit: dict[str, Any] | None = None) -> dict[str, Any]:
    block_id = str(text_block.get("id") or "text_block")
    root_bbox = _xyxy(text_block.get("bbox"))
    base_style = dict(text_block.get("style") or {})
    fitted_style = dict((fit or {}).get("fitted_style") or base_style)
    scale = float((fit or {}).get("scale", 1.0) or 1.0)
    lines = [line for line in str(text_block.get("final_text") or "").splitlines() if line.strip()]
    line_boxes = [_xyxy(item) for item in text_block.get("line_boxes", [])]
    if len(line_boxes) != len(lines):
        line_boxes = [root_bbox for _line in lines]
    members = []
    for index, line in enumerate(lines):
        members.append(
            {
                "member_id": f"{block_id}_line_{index + 1:02d}",
                "text": line,
                "relative_bbox": _relative_bbox(line_boxes[index], root_bbox),
                "style": fitted_style,
            }
        )
    return {
        "group_id": f"group_{block_id}",
        "text_block_id": block_id,
        "edit_behavior": "move_and_scale_as_group",
        "bbox": root_bbox,
        "scale": round(scale, 3),
        "transform": {
            "x": root_bbox[0],
            "y": root_bbox[1],
            "scale_x": round(scale, 3),
            "scale_y": round(scale, 3),
        },
        "members": members,
    }
```

- [ ] **Step 4: Run group tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_text_block_group.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit task**

```bash
git add scripts/dual_image_overlay/text_block_group.py tests/test_dual_image_overlay_text_block_group.py
git commit -m "feat: represent text blocks as grouped editable objects"
```

---

### Task 6: Template Rebuild Integration

**Files:**
- Modify: `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`
- Modify: `scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py`
- Modify: `tests/test_dual_image_overlay_template_rebuild.py`

**Interfaces:**
- Consumes: `build_page_understanding`, `verify_text_blocks_against_script`, `build_implicit_text_containers`, `fit_text_block_to_container`, `build_text_block_group`
- Produces: `analysis/page_understanding/page_XXX_page_understanding.json`
- Produces: text mapping boxes with `source="page_understanding_script_verified"`
- Produces: grouped text metadata with `edit_behavior="move_and_scale_as_group"`

- [ ] **Step 1: Write integration regression**

Append to `tests/test_dual_image_overlay_template_rebuild.py`:

```python
def test_template_rebuild_page_understanding_merges_ocr_fragments_with_script_truth() -> None:
    from scripts.dual_image_overlay.text_truth import verify_text_blocks_against_script
    from scripts.dual_image_overlay.page_understanding import build_page_understanding

    verified = verify_text_blocks_against_script(
        [
            {
                "id": "stage_6_flow",
                "ocr_text": "融资申请→风控审孩\n→放款→还款\n全流程线上化",
                "bbox": [630.0, 464.0, 709.0, 506.0],
                "line_boxes": [
                    [630.0, 464.0, 708.0, 475.0],
                    [643.0, 480.0, 704.0, 491.0],
                    [646.0, 496.0, 708.0, 506.0],
                ],
                "style": {"font_size": 8.5, "font_weight": "700"},
            }
        ],
        ["融资申请→风控审核→放款→还款，全流程线上化"],
    )
    payload = build_page_understanding(
        page_number=13,
        full_image=None,
        background_image=None,
        registration={"valid": True, "transform": "identity"},
        text_blocks=verified,
        explicit_containers=[
            {"id": "stage_6_card", "bbox": [624.0, 420.0, 714.0, 530.0], "source": "background_image"}
        ],
        implicit_containers=[],
        visual_elements=[],
    )

    assert payload["text_blocks"][0]["final_text"] == "融资申请→风控审核\n→放款→还款\n全流程线上化"
    assert payload["text_blocks"][0]["truth"]["status"] == "script_verified"
    assert payload["container_text_bindings"][0]["container_id"] == "stage_6_card"
```

- [ ] **Step 2: Run integration regression**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_template_rebuild_page_understanding_merges_ocr_fragments_with_script_truth -q
```

Expected: PASS if Tasks 1-4 are complete.

- [ ] **Step 3: Wire artifact writing in rebuild**

In `scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py`, after `boxes, editable_text_layout_source = _editable_boxes_from_scene_graph_or_recognition(...)`, call page-understanding helpers and write:

```python
page_understanding_dir = project_path / "analysis" / "page_understanding"
page_understanding_path = page_understanding_dir / f"page_{page_number:03d}_page_understanding.json"
```

The artifact must consume:
- `full_image`
- `background_image`
- OCR-derived `boxes_to_json(boxes)`
- current `containers_to_json(containers)`
- `visual_registry.get("elements", [])`
- script truth lines from `extract_script_truth_lines(source_script, page_number)`

The produced mapping must add:

```json
"page_understanding": "/absolute/path/to/page_013_page_understanding.json"
```

- [ ] **Step 4: Prefer page-understanding text boxes**

In `script_text_overlay.py`, add a conversion helper:

```python
def overlay_boxes_from_page_understanding(payload: dict[str, Any], *, font_family: str, fill: str) -> list[OverlayTextBox]:
    ...
```

For every `text_block`, create one `OverlayTextBox`:
- `text=final_text`
- `x/y/w/h` from bound container `text_safe_bbox` if available, else text block bbox
- `font_size` from block fit `fitted_style.font_size` when available, else style `font_size`
- `source="page_understanding_script_verified"` when truth is script verified
- `group_id` and line-member metadata must be written into text mapping JSON even if the current PPTX exporter still materializes it as a multi-line text box; the edit contract is group-level movement/scaling.

- [ ] **Step 5: Run targeted tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_overlay_page_understanding.py tests/test_dual_image_overlay_text_truth.py tests/test_dual_image_overlay_block_fit.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit task**

```bash
git add scripts/dual_image_overlay/rebuild_engine/editable_overlay_rebuild.py scripts/dual_image_overlay/rebuild_engine/script_text_overlay.py tests/test_dual_image_overlay_template_rebuild.py
git commit -m "feat: consume page understanding in template rebuild"
```

---

### Task 7: Workspace, Assignment, And Fit Consumption

**Files:**
- Modify: `scripts/dual_image_overlay/container_workspace.py`
- Modify: `scripts/dual_image_overlay/workspace_assignment.py`
- Modify: `scripts/dual_image_overlay/office_textbox_fit.py`
- Modify: `tests/test_container_workspace.py`
- Modify: `tests/test_workspace_assignment.py`
- Modify: `tests/test_office_textbox_fit.py`

**Interfaces:**
- Consumes: page-understanding `containers`, `container_text_bindings`, `fit_policy`, and block-fit results
- Produces: workspace slots and assignment evidence that reference page-understanding IDs

- [ ] **Step 1: Add container workspace test**

Add to `tests/test_container_workspace.py`:

```python
def test_container_workspace_prefers_page_understanding_text_safe_regions() -> None:
    from scripts.dual_image_overlay.container_workspace import build_container_workspace

    workspace = build_container_workspace(
        page_number=13,
        containers=[],
        text_objects=[],
        visual_elements=[],
        page_understanding={
            "containers": [
                {
                    "id": "stage_6_card",
                    "kind": "explicit_container",
                    "bbox": [624.0, 420.0, 714.0, 530.0],
                    "text_safe_bbox": [630.0, 464.0, 709.0, 506.0],
                }
            ]
        },
    )

    assert workspace["slot_count"] == 1
    assert workspace["slots"][0]["container_id"] == "stage_6_card"
    assert workspace["slots"][0]["source"] == "page_understanding"
```

- [ ] **Step 2: Update `build_container_workspace` signature**

Add optional argument:

```python
page_understanding: dict[str, Any] | None = None
```

When provided, create slots from `page_understanding["containers"]` before current inference.

- [ ] **Step 3: Add workspace assignment test**

Add to `tests/test_workspace_assignment.py`:

```python
def test_workspace_assignment_consumes_page_understanding_binding() -> None:
    from scripts.dual_image_overlay.workspace_assignment import build_workspace_assignment

    assignment = build_workspace_assignment(
        page_number=13,
        text_objects=[{"id": "stage_6_flow", "text": "融资申请→风控审核\n→放款→还款\n全流程线上化"}],
        workspaces={"slots": [{"id": "stage_6_slot", "container_id": "stage_6_card"}]},
        page_understanding={
            "container_text_bindings": [
                {"text_block_id": "stage_6_flow", "container_id": "stage_6_card", "confidence": 0.95}
            ]
        },
    )

    assert assignment["assignments"][0]["text_id"] == "stage_6_flow"
    assert assignment["assignments"][0]["assigned_slot"] == "stage_6_slot"
    assert assignment["assignments"][0]["source"] == "page_understanding"
```

- [ ] **Step 4: Add office fit test**

Add to `tests/test_office_textbox_fit.py`:

```python
def test_office_textbox_fit_applies_page_understanding_block_scale() -> None:
    from scripts.dual_image_overlay.office_textbox_fit import apply_office_textbox_fit

    fitted, report = apply_office_textbox_fit(
        [{"id": "stage_6_flow", "text": "融资申请→风控审核\n→放款→还款\n全流程线上化", "font_size": 8.5}],
        workspace_assignment={
            "assignments": [{"text_id": "stage_6_flow", "assigned_slot": "stage_6_slot"}],
            "slots": [{"id": "stage_6_slot", "bbox": [630.0, 464.0, 709.0, 506.0]}],
        },
        page_understanding={
            "text_blocks": [
                {
                    "id": "stage_6_flow",
                    "final_text": "融资申请→风控审核\n→放款→还款\n全流程线上化",
                    "style": {"font_size": 8.5, "line_height": 1.36},
                }
            ]
        },
    )

    assert fitted[0]["font_size"] <= 8.5
    assert report["checks"]["page_understanding_fit_consumed"] is True
```

- [ ] **Step 5: Implement consumption paths**

Implement only optional consumption paths. Existing call sites without `page_understanding` must behave unchanged.

- [ ] **Step 6: Run tests**

Run:

```bash
python3 -m pytest tests/test_container_workspace.py tests/test_workspace_assignment.py tests/test_office_textbox_fit.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit task**

```bash
git add scripts/dual_image_overlay/container_workspace.py scripts/dual_image_overlay/workspace_assignment.py scripts/dual_image_overlay/office_textbox_fit.py tests/test_container_workspace.py tests/test_workspace_assignment.py tests/test_office_textbox_fit.py
git commit -m "feat: consume page understanding in workspace and fit"
```

---

### Task 8: Source Capture And Readiness Gates

**Files:**
- Modify: `scripts/dual_image_overlay/source_capture.py`
- Modify: `scripts/dual_image_overlay/production_readiness.py`
- Modify: `scripts/dual_image_overlay/default_quality_rules.json`
- Modify: `scripts/dual_image_overlay/build_quality_rules.json`
- Modify: `scripts/dual_image_overlay/postflight_quality_rules.json`
- Modify: `tests/test_dual_image_overlay_source_capture.py`
- Modify: `tests/test_production_readiness.py`

**Interfaces:**
- Consumes: `analysis/page_understanding/page_XXX_page_understanding.json`
- Produces: `source_capture.inputs.page_understanding_available`
- Produces readiness checks:
  - `page_understanding_available`
  - `page_understanding_consumed`
  - `script_truth_verified`
  - `fit_review_queue_clear`

- [ ] **Step 1: Add source capture test**

Add to `tests/test_dual_image_overlay_source_capture.py`:

```python
def test_source_capture_records_page_understanding_artifacts(tmp_path: Path) -> None:
    analysis = tmp_path / "analysis"
    page_understanding_dir = analysis / "page_understanding"
    page_understanding_dir.mkdir(parents=True)
    (page_understanding_dir / "page_013_page_understanding.json").write_text(
        '{"schema":"cyberppt.dual_image.page_understanding.v1","valid":true}\\n',
        encoding="utf-8",
    )

    from scripts.dual_image_overlay.source_capture import discover_page_understanding

    discovered = discover_page_understanding(analysis)

    assert discovered["available"] is True
    assert discovered["count"] == 1
    assert discovered["paths"][0].endswith("page_013_page_understanding.json")
```

- [ ] **Step 2: Implement discovery helper**

In `source_capture.py`, add:

```python
def discover_page_understanding(analysis_dir: Path) -> dict[str, Any]:
    root = analysis_dir / "page_understanding"
    paths = sorted(str(path.resolve()) for path in root.glob("page_*_page_understanding.json")) if root.is_dir() else []
    return {"available": bool(paths), "count": len(paths), "paths": paths}
```

Include it in `source_capture["inputs"]`.

- [ ] **Step 3: Add readiness tests**

Add to `tests/test_production_readiness.py`:

```python
def test_production_readiness_requires_page_understanding_consumption() -> None:
    from scripts.dual_image_overlay.production_readiness import summarize_page_understanding_readiness

    summary = summarize_page_understanding_readiness(
        {
            "inputs": {"page_understanding_available": True, "page_understanding_count": 2},
            "pages": [{"page_number": 12}, {"page_number": 13}],
        }
    )

    assert summary["page_understanding_available"] is True
    assert summary["page_understanding_consumed"] is True
```

- [ ] **Step 4: Implement readiness summary**

Add the helper and wire it into existing readiness payloads without removing existing gates.

- [ ] **Step 5: Add quality rules**

Add rules to JSON files:

```json
{
  "id": "template.page_understanding_consumed",
  "stage": "template",
  "severity": "error",
  "description": "Template rebuild must consume page_understanding artifacts for dual-image editable overlay pages.",
  "kind": "page_understanding_consumed"
}
```

Add corresponding build/postflight variants with the same `kind`.

- [ ] **Step 6: Run tests**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_source_capture.py tests/test_production_readiness.py tests/test_dual_image_overlay_template_rebuild.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit task**

```bash
git add scripts/dual_image_overlay/source_capture.py scripts/dual_image_overlay/production_readiness.py scripts/dual_image_overlay/default_quality_rules.json scripts/dual_image_overlay/build_quality_rules.json scripts/dual_image_overlay/postflight_quality_rules.json tests/test_dual_image_overlay_source_capture.py tests/test_production_readiness.py
git commit -m "feat: gate page understanding consumption"
```

---

### Task 9: End-To-End Regression On Pages 12-13

**Files:**
- Modify: `tests/test_dual_image_overlay_template_rebuild.py`
- No new production files unless Task 5-7 missed integration points.

**Interfaces:**
- Consumes: real `projects/power-trusted-data-space-p12-p13/.../page_image_pairs.json` when present
- Produces: exported PPTX, text mapping, page understanding, and render evidence

- [ ] **Step 1: Add optional fixture-safe regression**

Add a test guarded by file existence:

```python
def test_pages_12_13_page_understanding_rebuild_regression() -> None:
    manifest = ROOT / "projects/power-trusted-data-space-p12-p13/workbench/stages/02-blueprint-dual-image/pages_012_013/page_image_pairs.json"
    if not manifest.is_file():
        raise unittest.SkipTest("local pages 12-13 project fixture is not available")

    result = subprocess.run(
        ["python3", "-m", "cyberppt", "template-rebuild", str(manifest), "--export"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode in (0, 3), result.stdout + result.stderr
    mapping = json.loads(
        (ROOT / "projects/power-trusted-data-space-p12-p13/analysis/ocr/page_013_text_mapping.json").read_text(
            encoding="utf-8"
        )
    )
    texts = [box["text"] for box in mapping["boxes"]]
    assert "融资申请→风控审核\n→放款→还款\n全流程线上化" in texts
```

- [ ] **Step 2: Run regression**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py::DualImageOverlayTemplateRebuildTests::test_pages_12_13_page_understanding_rebuild_regression -q
```

Expected: PASS or SKIP if local generated project is absent.

- [ ] **Step 3: Run full targeted suite**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_overlay_page_understanding.py tests/test_dual_image_overlay_text_truth.py tests/test_dual_image_overlay_block_fit.py tests/test_container_workspace.py tests/test_workspace_assignment.py tests/test_office_textbox_fit.py tests/test_dual_image_overlay_source_capture.py tests/test_production_readiness.py -q
```

Expected: PASS.

- [ ] **Step 4: Manual render verification**

Run:

```bash
python3 -m cyberppt template-rebuild projects/power-trusted-data-space-p12-p13/workbench/stages/02-blueprint-dual-image/pages_012_013/page_image_pairs.json --export
```

Expected: PPTX exported; exit code may remain `3` only for existing postflight evidence gates such as `render_delta_not_measured`, not for text/container/page-understanding failure.

Render:

```bash
mkdir -p projects/power-trusted-data-space-p12-p13/outputs/renders/page_understanding_regression
/opt/homebrew/bin/soffice --headless --convert-to pdf --outdir projects/power-trusted-data-space-p12-p13/outputs/renders/page_understanding_regression "$(ls -t projects/power-trusted-data-space-p12-p13/exports/*.pptx | head -n 1)"
pdftoppm -png -r 150 projects/power-trusted-data-space-p12-p13/outputs/renders/page_understanding_regression/*.pdf projects/power-trusted-data-space-p12-p13/outputs/renders/page_understanding_regression/page
```

Expected: page 13 stage-6 flow text remains one editable text block, with no overlap and no business text mutation.

- [ ] **Step 5: GitNexus final scope check**

Run:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_overlay_page_understanding.py tests/test_dual_image_overlay_text_truth.py tests/test_dual_image_overlay_block_fit.py -q
```

Then run GitNexus `detect_changes(scope="all", repo="CyberPPT", worktree="/Volumes/DOC/CyberPPT")` before commit.

- [ ] **Step 6: Commit task**

```bash
git add tests/test_dual_image_overlay_template_rebuild.py
git commit -m "test: cover page understanding rebuild regression"
```

---

## Acceptance Criteria

- `page_understanding.json` exists for every rebuilt dual-image page.
- Each text block records OCR candidate text, script-verified final text, line boxes, style evidence, fit policy, and review status.
- Each text block has a grouped editable representation with shared transform, member lines, relative offsets, and `edit_behavior="move_and_scale_as_group"`.
- OCR typo examples are corrected from script truth without altering script business input.
- OCR line structure is preserved unless the text block is marked for manual review.
- Text without a visible background container receives an implicit text container.
- `container_workspace`, `workspace_assignment`, and `office_textbox_fit` consume page-understanding evidence when present.
- Text fitting uses uniform block-level scaling; no line is independently squeezed.
- Moving or scaling a text block preserves all internal line-member relative positions.
- Scale thresholds produce warnings/review items according to:
  - `scale >= 0.85`: automatic pass
  - `0.70 <= scale < 0.85`: warning
  - `0.60 <= scale < 0.70`: review recommended
  - `scale < 0.60`: blocked/manual review required
- Existing fallback path continues to work when page-understanding is absent.
- Targeted tests pass:

```bash
python3 -m pytest tests/test_dual_image_overlay_template_rebuild.py tests/test_dual_image_overlay_page_understanding.py tests/test_dual_image_overlay_text_truth.py tests/test_dual_image_overlay_block_fit.py tests/test_dual_image_overlay_text_block_group.py tests/test_container_workspace.py tests/test_workspace_assignment.py tests/test_office_textbox_fit.py tests/test_dual_image_overlay_source_capture.py tests/test_production_readiness.py -q
```

## Rollout Strategy

1. Add page-understanding behind optional consumption paths.
2. Keep current OCR/script overlay fallback active.
3. Enable template rebuild to write page-understanding artifacts.
4. Make downstream modules prefer page-understanding when present.
5. Add readiness gates as warnings first if existing project fixtures are noisy.
6. Promote gates to blocking after pages 12/13 and at least one additional deck pass visual verification.

## Known Non-Goals

- Do not replace the existing `page_scene_graph.json` contract in this revision.
- Do not introduce new OCR services or image-recognition dependencies.
- Do not rebuild background images or change script business text.
- Do not solve all postflight visual QA artifact gates in this plan.
- Do not convert the full slide to fully editable vector shapes; this remains background image plus editable text overlay.

## Self-Review

- Spec coverage: covers strict no-text background, OCR-as-candidate, script truth correction, implicit containers, whole-block scaling, review thresholds, and downstream artifact consumption.
- Placeholder scan: no `TBD`, `TODO`, or unspecified test steps remain.
- Type consistency: `text_block`, `container`, `container_text_bindings`, `fit_policy`, and `review_items` names are consistent across tasks.

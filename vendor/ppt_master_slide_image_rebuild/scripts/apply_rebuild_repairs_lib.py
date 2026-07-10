#!/usr/bin/env python3
"""
Apply auto-fix patches from exports/qa/repair_tasks.json to svg_output/ pages.

Patches are produced by repair_tasks_lib.enrich_tasks_with_patches(). Only
coordinate drift (<=5px), text overflow reflow, and repeat-group y spacing are
supported in v1.
"""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from xml.etree import ElementTree as ET

try:
    from layout_reference_components import fit_text_box
except ImportError:  # pragma: no cover
    from scripts.layout_reference_components import fit_text_box  # type: ignore

try:
    from repair_tasks_lib import load_json, write_repair_tasks
except ImportError:  # pragma: no cover
    from scripts.repair_tasks_lib import load_json, write_repair_tasks  # type: ignore

try:
    from slide_image_rebuild_manifest_lib import resolve_text_layout_policy
except ImportError:  # pragma: no cover
    from scripts.slide_image_rebuild_manifest_lib import resolve_text_layout_policy  # type: ignore

try:
    from svg_page_discovery import find_page_svg
except ImportError:  # pragma: no cover
    from scripts.svg_page_discovery import find_page_svg  # type: ignore

SVG_NS = "{http://www.w3.org/2000/svg}"
REPORT_VERSION = "1.0"
MAX_BBOX_DELTA_PX = 5.0
AUTO_APPLY_TYPES = frozenset({
    "coordinate_drift",
    "text_reflow",
    "size_deviation",
})


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _strip_ns(tag: str) -> str:
    return tag.replace(SVG_NS, "")


def _float(value: str | None) -> float | None:
    if value is None:
        return None
    match = re.match(r"\s*(-?\d+(?:\.\d+)?)", value)
    return float(match.group(1)) if match else None


def _selector_match(elem: ET.Element, selector: dict[str, Any]) -> bool:
    for key, expected in selector.items():
        if elem.get(key) != str(expected):
            return False
    return True


def find_elements(root: ET.Element, selector: dict[str, Any]) -> list[ET.Element]:
    if not selector:
        return []
    return [elem for elem in root.iter() if _selector_match(elem, selector)]


def write_svg_utf8(path: Path, root: ET.Element) -> None:
    tree = ET.ElementTree(root)
    if hasattr(ET, "indent"):
        ET.indent(tree, space="  ")  # type: ignore[attr-defined]
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _clamp_delta(value: float, limit: float = MAX_BBOX_DELTA_PX) -> float:
    return max(-limit, min(limit, value))


def _first_rect(group: ET.Element) -> ET.Element | None:
    for child in group.iter():
        if _strip_ns(child.tag) == "rect" and child is not group:
            return child
    return None


def apply_bbox_delta(root: ET.Element, patch: dict[str, Any]) -> tuple[bool, str]:
    selector = patch.get("selector", {})
    if not isinstance(selector, dict) or not selector:
        return False, "patch missing selector"
    targets = find_elements(root, selector)
    if not targets:
        return False, "selector not found"
    x_delta = _clamp_delta(float(patch.get("x_delta", 0.0)))
    y_delta = _clamp_delta(float(patch.get("y_delta", 0.0)))
    w_delta = _clamp_delta(float(patch.get("w_delta", 0.0)))
    h_delta = _clamp_delta(float(patch.get("h_delta", 0.0)))
    target = targets[0]
    rect = _first_rect(target) if _strip_ns(target.tag) == "g" else (
        target if _strip_ns(target.tag) == "rect" else None
    )
    if rect is None:
        transform = target.get("transform", "")
        translate = f"translate({x_delta:.2f},{y_delta:.2f})"
        target.set("transform", f"{transform} {translate}".strip())
        return True, "applied group translate"
    for attr, delta in (("x", x_delta), ("y", y_delta), ("width", w_delta), ("height", h_delta)):
        current = _float(rect.get(attr))
        if current is None:
            continue
        rect.set(attr, f"{current + delta:.2f}")
    return True, "applied rect bbox delta"


def _text_elem_lines(elem: ET.Element) -> list[str]:
    tspans = [child for child in list(elem) if _strip_ns(child.tag) == "tspan"]
    if not tspans:
        text = "".join(elem.itertext()).strip()
        return [text] if text else []
    return ["".join(child.itertext()).strip() for child in tspans if "".join(child.itertext()).strip()]


def _rewrite_text_elem(
    elem: ET.Element,
    lines: Sequence[str],
    *,
    font_size: float,
    line_height: float,
) -> None:
    for child in list(elem):
        if _strip_ns(child.tag) == "tspan":
            elem.remove(child)
    base_x = _float(elem.get("x")) or 0.0
    base_y = _float(elem.get("y")) or 0.0
    elem.set("font-size", f"{font_size:.2f}")
    elem.set("data-paragraph-line-height", f"{line_height:.2f}")
    for index, line in enumerate(lines):
        tspan = ET.SubElement(elem, f"{SVG_NS}tspan")
        tspan.set("x", f"{base_x:.2f}")
        tspan.set("dy", "0" if index == 0 else f"{line_height:.2f}")
        tspan.text = line


def apply_fit_text_patch(
    root: ET.Element,
    patch: dict[str, Any],
    *,
    policy: dict[str, Any],
) -> tuple[bool, str]:
    selector = patch.get("selector", {})
    if not isinstance(selector, dict) or not selector:
        return False, "patch missing selector"
    targets = find_elements(root, selector)
    if not targets:
        return False, "text selector not found"
    elem = targets[0]
    if _strip_ns(elem.tag) != "text":
        return False, "selector did not match text element"
    box = patch.get("box_px")
    if not isinstance(box, list) or len(box) < 4:
        return False, "patch missing box_px"
    source_text = patch.get("text") or " ".join(_text_elem_lines(elem))
    fitted = fit_text_box(
        str(source_text),
        (float(box[0]), float(box[1]), float(box[2]), float(box[3])),
        min_size=float(policy.get("min_font_size_pt", 7.5)),
        max_size=float(policy.get("max_font_size_pt", 12.0)),
        max_lines=int(patch.get("max_lines", policy.get("max_lines", 3))),
        line_height_ratio=float(policy.get("line_height_ratio", 1.12)),
        fit_strategy=str(policy.get("fit_strategy", "shrink_then_wrap_then_truncate")),
    )
    if not fitted.lines:
        return False, "fit_text_box returned no lines"
    _rewrite_text_elem(
        elem,
        fitted.lines,
        font_size=fitted.font_size,
        line_height=fitted.line_height,
    )
    return True, "reflowed text"


def apply_repeat_group_y_spacing(
    root: ET.Element,
    patch: dict[str, Any],
) -> tuple[bool, str]:
    zone_ids = patch.get("zone_ids")
    if not isinstance(zone_ids, list) or len(zone_ids) < 2:
        return False, "repeat_group patch missing zone_ids"
    boxes: list[tuple[ET.Element, float, float]] = []
    for zone_id in zone_ids:
        selector = {"data-zone-id": str(zone_id)}
        elems = find_elements(root, selector)
        if not elems:
            return False, f"zone not found: {zone_id}"
        elem = elems[0]
        rect = _first_rect(elem) if _strip_ns(elem.tag) == "g" else elem
        y_val = _float(rect.get("y") if rect is not None else elem.get("y"))
        h_val = _float(rect.get("height") if rect is not None else elem.get("height"))
        if y_val is None or h_val is None:
            return False, f"could not read y/height for {zone_id}"
        boxes.append((elem, y_val, h_val))
    boxes.sort(key=lambda item: item[1])
    start_y = float(patch.get("start_y_px", boxes[0][1]))
    gap = float(patch.get("gap_px", 8.0))
    cursor = start_y
    for elem, _old_y, height in boxes:
        rect = _first_rect(elem) if _strip_ns(elem.tag) == "g" else elem
        if rect is None:
            return False, "repeat_group target has no rect"
        rect.set("y", f"{cursor:.2f}")
        cursor += height + gap
    return True, f"spaced {len(boxes)} zones"


def apply_patch_to_svg(svg_path: Path, patch: dict[str, Any], *, policy: dict[str, Any]) -> dict[str, Any]:
    kind = str(patch.get("kind", ""))
    try:
        root = ET.parse(svg_path).getroot()
    except (ET.ParseError, OSError) as exc:
        return {"ok": False, "message": f"svg parse error: {exc}"}
    if kind == "bbox_delta":
        ok, message = apply_bbox_delta(root, patch)
    elif kind == "fit_text_box":
        ok, message = apply_fit_text_patch(root, patch, policy=policy)
    elif kind == "repeat_group_y_spacing":
        ok, message = apply_repeat_group_y_spacing(root, patch)
    else:
        return {"ok": False, "message": f"unsupported patch kind: {kind}"}
    if ok:
        write_svg_utf8(svg_path, root)
    return {"ok": ok, "message": message}


def _page_svg(project: Path, page_id: str) -> Path | None:
    return find_page_svg(project, page_id, prefer_final=False)


def apply_repair_tasks(
    project: Path,
    payload: dict[str, Any],
    *,
    dry_run: bool = False,
    task_ids: set[str] | None = None,
    max_tasks: int | None = None,
) -> dict[str, Any]:
    manifest = load_json(project / "slide_image_rebuild_manifest.json")
    policy = resolve_text_layout_policy(manifest).policy
    results: list[dict[str, Any]] = []
    applied = 0
    for task in payload.get("tasks", []):
        if not isinstance(task, dict):
            continue
        if task.get("status") != "open":
            continue
        if task_ids and str(task.get("id", "")) not in task_ids:
            continue
        if max_tasks is not None and applied >= max_tasks:
            break
        patch = task.get("patch")
        if not isinstance(patch, dict):
            continue
        if task.get("auto_apply") is not True:
            continue
        if str(task.get("issue_type", "")) not in AUTO_APPLY_TYPES:
            continue
        page_id = str(task.get("page_id", "01"))
        svg_path = _page_svg(project, page_id)
        if svg_path is None:
            results.append({
                "task_id": task.get("id"),
                "ok": False,
                "message": f"svg not found for page {page_id}",
            })
            continue
        if dry_run:
            results.append({
                "task_id": task.get("id"),
                "ok": True,
                "message": "dry-run",
                "patch": patch,
                "svg": str(svg_path.relative_to(project)),
            })
            applied += 1
            continue
        outcome = apply_patch_to_svg(svg_path, patch, policy=policy)
        outcome["task_id"] = task.get("id")
        outcome["svg"] = str(svg_path.relative_to(project))
        results.append(outcome)
        if outcome.get("ok"):
            task["status"] = "applied"
            task["resolved_at"] = utc_now()
            applied += 1
    payload["applied_count"] = applied
    payload["apply_results"] = results
    payload["apply_generated_at"] = utc_now()
    return {
        "workflow": "slide-image-rebuild",
        "version": REPORT_VERSION,
        "generated_at": utc_now(),
        "project": str(project.resolve()),
        "dry_run": dry_run,
        "applied_count": applied,
        "results": results,
        "valid": all(item.get("ok") for item in results) if results else True,
    }


def apply_from_project(
    project: Path,
    *,
    dry_run: bool = False,
    write_tasks: bool = False,
    task_ids: set[str] | None = None,
    max_tasks: int | None = None,
) -> dict[str, Any]:
    tasks_path = project / "exports" / "qa" / "repair_tasks.json"
    payload = load_json(tasks_path)
    if not payload:
        return {
            "valid": False,
            "errors": [f"missing repair_tasks.json: {tasks_path}"],
            "applied_count": 0,
            "results": [],
        }
    report = apply_repair_tasks(
        project,
        payload,
        dry_run=dry_run,
        task_ids=task_ids,
        max_tasks=max_tasks,
    )
    if write_tasks and not dry_run:
        write_repair_tasks(project, payload)
        report["tasks_path"] = "exports/qa/repair_tasks.json"
    return report

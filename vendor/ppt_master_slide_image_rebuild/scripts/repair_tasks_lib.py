#!/usr/bin/env python3
"""
Aggregate slide-image-rebuild QA failures into actionable repair_tasks.json.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORT_VERSION = "1.1"
MAX_AUTO_DELTA_PX = 5.0

ISSUE_TYPES = frozenset({
    "coordinate_drift",
    "size_deviation",
    "color_deviation",
    "text_reflow",
    "icon_style_mismatch",
    "residual_object",
    "connector_geometry",
    "geometry_lock_violation",
    "contract_violation",
    "other",
})

ISSUE_CODE_MAP = {
    "ZONE_MEAN_DIFF_HIGH": "color_deviation",
    "ANCHOR_DRIFT": "coordinate_drift",
    "ICON_SHAPE_SIMPLIFIED": "icon_style_mismatch",
    "ICON_NOT_VISIBLE": "icon_style_mismatch",
    "ICON_POSITION_DRIFT": "coordinate_drift",
    "ICON_SIZE_DRIFT": "size_deviation",
    "BBOX_TOO_SMALL": "size_deviation",
    "LINE_COUNT_MISMATCH": "text_reflow",
    "BASELINE_DRIFT": "text_reflow",
    "BBOX_DRIFT": "coordinate_drift",
    "EDGE_MARGIN_LOW": "text_reflow",
    "svg_selector_not_found": "geometry_lock_violation",
    "position_drift": "coordinate_drift",
    "size_drift": "size_deviation",
    "y_drift": "coordinate_drift",
    "stroke_width": "icon_style_mismatch",
    "icon_stroke_too_heavy": "icon_style_mismatch",
    "icon_stroke_inconsistent": "icon_style_mismatch",
    "icon_stroke_mismatch": "icon_style_mismatch",
    "icon_bbox_fill_low": "icon_style_mismatch",
    "icon_bbox_fill_high": "icon_style_mismatch",
    "icon_padding_low": "icon_style_mismatch",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


try:  # shared helper; see scripts/json_io.py
    from json_io import load_json
except ImportError:  # pragma: no cover - package-context import
    from scripts.json_io import load_json  # type: ignore


def _issue_type(*candidates: str) -> str:
    for candidate in candidates:
        if not candidate:
            continue
        mapped = ISSUE_CODE_MAP.get(candidate)
        if mapped:
            return mapped
        lowered = candidate.lower()
        for token, mapped_type in ISSUE_CODE_MAP.items():
            if token.lower() in lowered:
                return mapped_type
        if "connector" in lowered or "chain" in lowered:
            return "connector_geometry"
        if "residual" in lowered or "chrome" in lowered:
            return "residual_object"
        if "color" in lowered or "fill" in lowered or "stroke" in lowered:
            return "color_deviation"
        if "icon" in lowered:
            return "icon_style_mismatch"
        if "text" in lowered or "wrap" in lowered or "line" in lowered:
            return "text_reflow"
        if "size" in lowered or "bbox" in lowered:
            return "size_deviation"
        if "drift" in lowered or "offset" in lowered:
            return "coordinate_drift"
    return "other"


def _task_id(index: int) -> str:
    return f"repair-{index:03d}"


def _append_task(
    tasks: list[dict[str, Any]],
    *,
    page_id: str,
    region_id: str,
    issue_type: str,
    severity: str,
    source_check: str,
    source_report: str,
    message: str,
    bbox_px: list[float] | None = None,
    suggested_action: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    if issue_type not in ISSUE_TYPES:
        issue_type = "other"
    tasks.append({
        "id": _task_id(len(tasks) + 1),
        "page_id": page_id,
        "region_id": region_id,
        "issue_type": issue_type,
        "severity": severity,
        "status": "open",
        "source_check": source_check,
        "source_report": source_report,
        "message": message,
        "bbox_px": bbox_px,
        "suggested_action": suggested_action,
        "metadata": metadata or {},
        "resolved_at": None,
    })


def _tasks_from_object_similarity(project: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    rel = "exports/qa/object_similarity_report.json"
    for page in report.get("pages", []) if isinstance(report.get("pages"), list) else []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id", "01"))
        for failure in page.get("failures", []) if isinstance(page.get("failures"), list) else []:
            if not isinstance(failure, dict):
                continue
            issue_code = str(failure.get("issue_code", failure.get("issue", "")))
            obj_type = str(failure.get("type", "zone"))
            _append_task(
                tasks,
                page_id=page_id,
                region_id=str(failure.get("id", "")),
                issue_type=_issue_type(issue_code, obj_type),
                severity="warning",  # advisory: object-similarity drift no longer blocks export
                source_check="verify_reference_object_similarity",
                source_report=rel,
                message=str(failure.get("message", issue_code)),
                bbox_px=failure.get("reference_bbox_px") if isinstance(failure.get("reference_bbox_px"), list) else None,
                suggested_action=str(failure.get("action", "")),
                metadata={"issue_code": issue_code, "metrics": failure.get("metrics", {})},
            )
    return tasks


def _tasks_from_text_wrap(project: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    rel = "exports/qa/text_wrap_similarity_report.json"
    for page in report.get("pages", []) if isinstance(report.get("pages"), list) else []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id", "01"))
        for failure in page.get("failures", []) if isinstance(page.get("failures"), list) else []:
            if not isinstance(failure, dict):
                continue
            issue_code = str(failure.get("issue_code", failure.get("issue", "")))
            _append_task(
                tasks,
                page_id=page_id,
                region_id=str(failure.get("id", failure.get("region_id", ""))),
                issue_type=_issue_type(issue_code, "text_reflow"),
                severity="warning",  # advisory: text-wrap drift no longer blocks export
                source_check="verify_text_wrap_similarity",
                source_report=rel,
                message=str(failure.get("message", issue_code)),
                bbox_px=failure.get("expected_bbox_px") if isinstance(failure.get("expected_bbox_px"), list) else None,
                suggested_action="Split or realign SVG text lines to match reference visual rows.",
                metadata={"issue_code": issue_code},
            )
    return tasks


def _tasks_from_geometry_locks(project: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    rel = "exports/qa/geometry_locks_report.json"
    for page in report.get("pages", []) if isinstance(report.get("pages"), list) else []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id", "01"))
        for result in page.get("results", []) if isinstance(page.get("results"), list) else []:
            if not isinstance(result, dict) or result.get("valid"):
                continue
            lock_id = str(result.get("id", ""))
            issues = result.get("issues", [])
            issue_text = ", ".join(str(item) for item in issues) if isinstance(issues, list) else ""
            primary_issue = issues[0] if isinstance(issues, list) and issues else "geometry_lock_violation"
            _append_task(
                tasks,
                page_id=page_id,
                region_id=lock_id,
                issue_type=_issue_type(str(primary_issue), "geometry_lock_violation"),
                severity="warning",  # advisory: geometry-lock drift no longer blocks export
                source_check="verify_geometry_locks",
                source_report=rel,
                message=f"Geometry lock `{lock_id}` failed: {issue_text}",
                bbox_px=result.get("expected_bbox_px") if isinstance(result.get("expected_bbox_px"), list) else None,
                suggested_action="Adjust SVG coordinates/style to satisfy geometry_locks[] before export.",
                metadata={
                    "issues": issues,
                    "expected_bbox_px": result.get("expected_bbox_px"),
                    "actual_bbox_px": result.get("actual_bbox_px"),
                },
            )
    return tasks


def _tasks_from_layout_family(project: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    rel = "exports/qa/layout_family_contract_report.json"
    for page in report.get("pages", []) if isinstance(report.get("pages"), list) else []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id", "01"))
        for message in page.get("errors", []) if isinstance(page.get("errors"), list) else []:
            _append_task(
                tasks,
                page_id=page_id,
                region_id=str(page.get("layout_family", "layout_family")),
                issue_type="connector_geometry",
                severity="blocking",
                source_check="verify_layout_family_contract",
                source_report=rel,
                message=str(message),
                suggested_action="Restore required layout-family components and connectors.",
            )
    return tasks


def _tasks_from_icon_contract(project: Path, report: dict[str, Any]) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    rel = "exports/qa/icon_contract_report.json"
    error_items: list[dict[str, Any]] = []
    style_errors = report.get("style_errors")
    if isinstance(style_errors, list) and style_errors:
        error_items.extend(item for item in style_errors if isinstance(item, dict))
    else:
        errors = report.get("errors")
        if isinstance(errors, list):
            error_items.extend(item for item in errors if isinstance(item, dict))
    for item in error_items:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", ""))
        icon_issue_type = _issue_type(code, "icon")
        # Icon position/size drift is reference-fidelity (advisory); only true
        # contract violations (missing/garbage icon, style mismatch) block export.
        icon_severity = "warning" if icon_issue_type in {"coordinate_drift", "size_deviation"} else "blocking"
        _append_task(
            tasks,
            page_id=str(item.get("page_id", "01")),
            region_id=str(item.get("icon_id") or item.get("path", "icon")),
            issue_type=icon_issue_type,
            severity=icon_severity,
            source_check="verify_icon_contract",
            source_report=rel,
            message=str(item.get("message", code)),
            suggested_action="Rebuild the icon using the three-tier icon strategy and unified stroke metrics.",
            metadata={"code": code, "metrics": item.get("metrics", {})},
        )
    return tasks


def _clamp_delta(value: float) -> float:
    return max(-MAX_AUTO_DELTA_PX, min(MAX_AUTO_DELTA_PX, value))


def _lock_selector(project: Path, lock_id: str) -> dict[str, str]:
    layout = load_json(project / "layout_reference.json")
    for lock in layout.get("geometry_locks", []) if isinstance(layout.get("geometry_locks"), list) else []:
        if not isinstance(lock, dict):
            continue
        if str(lock.get("id", "")) == lock_id:
            selector = lock.get("svg_selector", {})
            if isinstance(selector, dict):
                return {str(key): str(value) for key, value in selector.items()}
    zone_id = lock_id.removeprefix("lock_").removeprefix("anchor_")
    if zone_id:
        return {"data-zone-id": zone_id}
    return {}


def _patch_for_coordinate_task(project: Path, task: dict[str, Any]) -> dict[str, Any] | None:
    metadata = task.get("metadata", {})
    if not isinstance(metadata, dict):
        return None
    expected = metadata.get("expected_bbox_px")
    actual = metadata.get("actual_bbox_px")
    if not (isinstance(expected, list) and isinstance(actual, list) and len(expected) >= 4 and len(actual) >= 4):
        return None
    x_delta = _clamp_delta(float(expected[0]) - float(actual[0]))
    y_delta = _clamp_delta(float(expected[1]) - float(actual[1]))
    w_delta = _clamp_delta(float(expected[2]) - float(actual[2]))
    h_delta = _clamp_delta(float(expected[3]) - float(actual[3]))
    if all(abs(value) < 0.05 for value in (x_delta, y_delta, w_delta, h_delta)):
        return None
    selector = _lock_selector(project, str(task.get("region_id", "")))
    if not selector:
        region_id = str(task.get("region_id", ""))
        if region_id:
            selector = {"data-zone-id": region_id}
    if not selector:
        return None
    return {
        "kind": "bbox_delta",
        "selector": selector,
        "x_delta": round(x_delta, 2),
        "y_delta": round(y_delta, 2),
        "w_delta": round(w_delta, 2),
        "h_delta": round(h_delta, 2),
        "max_abs_delta_px": MAX_AUTO_DELTA_PX,
    }


def _patch_for_text_task(project: Path, task: dict[str, Any]) -> dict[str, Any] | None:
    bbox = task.get("bbox_px")
    if not isinstance(bbox, list) or len(bbox) < 4:
        return None
    region_id = str(task.get("region_id", ""))
    if not region_id:
        return None
    selector = {"data-text-region-id": region_id}
    return {
        "kind": "fit_text_box",
        "selector": selector,
        "box_px": [float(value) for value in bbox[:4]],
        "max_lines": 4,
    }


def _patch_for_repeat_group(project: Path, task: dict[str, Any]) -> dict[str, Any] | None:
    layout = load_json(project / "layout_reference.json")
    hints = layout.get("layout_family_hints", {})
    if not isinstance(hints, dict):
        return None
    groups = hints.get("repeat_groups", [])
    if not isinstance(groups, list):
        return None
    region_id = str(task.get("region_id", ""))
    for group in groups:
        if not isinstance(group, dict):
            continue
        zone_ids = group.get("zone_ids") or group.get("member_zone_ids")
        if not isinstance(zone_ids, list):
            continue
        if region_id and region_id not in {str(item) for item in zone_ids}:
            continue
        gap = group.get("gap_px", 8.0)
        return {
            "kind": "repeat_group_y_spacing",
            "zone_ids": [str(item) for item in zone_ids],
            "gap_px": float(gap),
            "start_y_px": group.get("start_y_px"),
        }
    return None


def enrich_task_with_patch(project: Path, task: dict[str, Any]) -> None:
    if task.get("patch"):
        return
    issue_type = str(task.get("issue_type", ""))
    patch: dict[str, Any] | None = None
    auto_apply = False
    if issue_type in {"coordinate_drift", "size_deviation"}:
        patch = _patch_for_coordinate_task(project, task)
        auto_apply = patch is not None
    elif issue_type == "text_reflow":
        patch = _patch_for_text_task(project, task)
        auto_apply = patch is not None
    elif issue_type == "connector_geometry":
        patch = _patch_for_repeat_group(project, task)
        auto_apply = patch is not None
    if patch:
        task["patch"] = patch
        task["auto_apply"] = auto_apply


def enrich_tasks_with_patches(project: Path, tasks: list[dict[str, Any]]) -> int:
    enriched = 0
    for task in tasks:
        before = task.get("patch")
        enrich_task_with_patch(project, task)
        if task.get("patch") and not before:
            enriched += 1
    return enriched


def aggregate_repair_tasks(project: Path) -> dict[str, Any]:
    qa_dir = project / "exports" / "qa"
    tasks: list[dict[str, Any]] = []

    object_report = load_json(qa_dir / "object_similarity_report.json")
    if object_report:
        tasks.extend(_tasks_from_object_similarity(project, object_report))

    text_wrap_report = load_json(qa_dir / "text_wrap_similarity_report.json")
    if text_wrap_report:
        tasks.extend(_tasks_from_text_wrap(project, text_wrap_report))

    geometry_report = load_json(qa_dir / "geometry_locks_report.json")
    if geometry_report:
        tasks.extend(_tasks_from_geometry_locks(project, geometry_report))

    layout_family_report = load_json(qa_dir / "layout_family_contract_report.json")
    if layout_family_report:
        tasks.extend(_tasks_from_layout_family(project, layout_family_report))

    icon_report = load_json(qa_dir / "icon_contract_report.json")
    if icon_report:
        tasks.extend(_tasks_from_icon_contract(project, icon_report))

    # Re-number task ids after merge.
    for index, task in enumerate(tasks, start=1):
        task["id"] = _task_id(index)

    enrich_tasks_with_patches(project, tasks)

    blocking_open = [
        task for task in tasks
        if task.get("status") == "open" and task.get("severity") == "blocking"
    ]
    return {
        "workflow": "slide-image-rebuild",
        "version": REPORT_VERSION,
        "generated_at": utc_now(),
        "project": str(project.resolve()),
        "status": "open" if blocking_open else "clear",
        "valid": not blocking_open,
        "task_count": len(tasks),
        "blocking_open_count": len(blocking_open),
        "tasks": tasks,
    }


def write_repair_tasks(project: Path, payload: dict[str, Any]) -> Path:
    out = project / "exports" / "qa" / "repair_tasks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out

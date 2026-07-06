from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RULES_PATH = Path(__file__).with_name("default_quality_rules.json")
REPORT_SCHEMA = "cyberppt.dual_image.page_quality_report.v1"


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def load_quality_rules(path: Path = RULES_PATH) -> list[dict[str, Any]]:
    payload = _read_json(path)
    rules = payload.get("rules", [])
    if not isinstance(rules, list):
        raise ValueError(f"Quality rules must be a list: {path}")
    return [rule for rule in rules if isinstance(rule, dict)]


def _is_truthy_report(report: Any) -> bool:
    return isinstance(report, dict) and bool(report.get("valid"))


def _artifact_exists(value: Any) -> bool:
    if not isinstance(value, str) or not value:
        return False
    return Path(value).expanduser().exists()


def _rect_from_mapping(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        if all(key in value for key in ("x", "y", "width", "height")):
            return {
                "x": float(value["x"]),
                "y": float(value["y"]),
                "w": float(value["width"]),
                "h": float(value["height"]),
            }
        if all(key in value for key in ("x", "y", "w", "h")):
            return {
                "x": float(value["x"]),
                "y": float(value["y"]),
                "w": float(value["w"]),
                "h": float(value["h"]),
            }
    except (TypeError, ValueError):
        return None
    return None


def _pair_image_path(item: Any) -> str:
    if not isinstance(item, dict):
        return ""
    path = item.get("path")
    return str(path) if isinstance(path, str) else ""


def _check_dual_image_pair_required(manifest: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(manifest, dict):
        return False, {"reason": "pair_manifest_missing"}
    pairs = manifest.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        return False, {"reason": "pairs_missing_or_empty"}
    failures: list[dict[str, Any]] = []
    for pair in pairs:
        if not isinstance(pair, dict):
            failures.append({"reason": "pair_not_object"})
            continue
        page_number = pair.get("page_number")
        full_path = _pair_image_path(pair.get("full"))
        background_path = _pair_image_path(pair.get("background"))
        page_failures = []
        if not full_path:
            page_failures.append("full_path_missing")
        elif not _artifact_exists(full_path):
            page_failures.append("full_path_not_found")
        if not background_path:
            page_failures.append("background_path_missing")
        elif not _artifact_exists(background_path):
            page_failures.append("background_path_not_found")
        if full_path and background_path and full_path == background_path:
            page_failures.append("full_background_same_file")
        if page_failures:
            failures.append({"page_number": page_number, "failures": page_failures})
    return not failures, {"pair_count": len(pairs), "failures": failures}


def _check_source_capture_required(source_capture: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(source_capture, dict):
        return False, {"reason": "source_capture_missing"}
    pages = [page for page in source_capture.get("pages", []) if isinstance(page, dict)]
    page_failures: list[dict[str, Any]] = []
    for page in pages:
        page_number = page.get("page_number")
        source_images = page.get("source_images") if isinstance(page.get("source_images"), dict) else {}
        text_objects = [item for item in page.get("text_objects", []) if isinstance(item, dict)]
        failures = []
        if not source_images.get("full") or not source_images.get("background"):
            failures.append("dual_image_source_missing")
        if not text_objects:
            failures.append("text_objects_missing")
        if failures:
            page_failures.append({"page_number": page_number, "failures": failures})
    return bool(pages) and not page_failures, {"page_count": len(pages), "failures": page_failures}


def _safe_non_negative_int(value: Any, *, reason: str) -> tuple[int, str | None]:
    if isinstance(value, bool):
        return 0, reason
    if isinstance(value, int):
        return (value, None) if value >= 0 else (0, reason)
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value), None
    return 0, reason


def _check_page_understanding_consumed(source_capture_evidence: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(source_capture_evidence, dict):
        return False, {"reason": "source_capture_evidence_missing"}
    page_understanding = (
        source_capture_evidence.get("page_understanding")
        if isinstance(source_capture_evidence.get("page_understanding"), dict)
        else {}
    )
    checks = source_capture_evidence.get("checks") if isinstance(source_capture_evidence.get("checks"), dict) else {}

    available = bool(page_understanding.get("available") or checks.get("page_understanding_available"))
    consumed = bool(page_understanding.get("consumed") or checks.get("page_understanding_consumed"))
    script_truth_verified = bool(
        page_understanding.get("script_truth_verified") or checks.get("script_truth_verified")
    )
    fit_review_queue_clear = bool(
        page_understanding.get("fit_review_queue_clear") or checks.get("fit_review_queue_clear")
    )
    consumed_count, consumed_count_reason = _safe_non_negative_int(
        page_understanding.get("consumed_count", 0),
        reason="invalid_page_understanding_consumed_count",
    )
    count, count_reason = _safe_non_negative_int(
        page_understanding.get("count", 0),
        reason="invalid_page_understanding_count",
    )
    reason = count_reason or consumed_count_reason

    if not page_understanding:
        inputs = source_capture_evidence.get("inputs") if isinstance(source_capture_evidence.get("inputs"), dict) else {}
        pages = [page for page in source_capture_evidence.get("pages", []) if isinstance(page, dict)]
        summaries = [
            page.get("page_understanding")
            for page in pages
            if isinstance(page.get("page_understanding"), dict)
        ]
        paths = inputs.get("page_understanding_paths", [])
        count, count_reason = _safe_non_negative_int(
            inputs.get("page_understanding_count", 0),
            reason="invalid_page_understanding_count",
        )
        reason = count_reason
        available = bool(inputs.get("page_understanding_available") or count > 0 or paths)
        consumed_count = len(summaries)
        consumed = bool(available and count > 0 and consumed_count >= count)
        script_truth_verified = bool(summaries) and all(
            summary.get("script_truth_verified") is True for summary in summaries
        )
        fit_review_queue_clear = bool(summaries) and all(
            summary.get("fit_review_queue_clear") is True for summary in summaries
        )

    not_applicable = not available and count == 0 and consumed_count == 0
    passed = bool(
        reason is None
        and (
            not_applicable
            or (
                available
                and consumed
                and script_truth_verified
                and fit_review_queue_clear
                and consumed_count > 0
                and (count == 0 or consumed_count >= count)
            )
        )
    )
    observed = {
        "available": available,
        "not_applicable": not_applicable,
        "count": count,
        "consumed": consumed,
        "consumed_count": consumed_count,
        "script_truth_verified": script_truth_verified,
        "fit_review_queue_clear": fit_review_queue_clear,
        "paths": page_understanding.get("paths", []),
    }
    if reason is not None:
        observed["reason"] = reason
    return passed, observed


def _check_template_region_declared(manifest: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(manifest, dict):
        return False, {"reason": "pair_manifest_missing"}
    contract = manifest.get("generation_contract")
    if not isinstance(contract, dict):
        return False, {"reason": "generation_contract_missing"}
    content_region = _rect_from_mapping(contract.get("content_region") or contract.get("brand_body_region"))
    slide_canvas = contract.get("slide_canvas") if isinstance(contract.get("slide_canvas"), dict) else {}
    canvas_width = float(slide_canvas.get("width", 1280) or 1280)
    canvas_height = float(slide_canvas.get("height", 720) or 720)
    if content_region is None:
        return False, {"reason": "content_region_missing"}
    inside_canvas = (
        content_region["x"] >= 0
        and content_region["y"] >= 0
        and content_region["w"] > 0
        and content_region["h"] > 0
        and content_region["x"] + content_region["w"] <= canvas_width
        and content_region["y"] + content_region["h"] <= canvas_height
    )
    return inside_canvas, {"content_region": content_region, "canvas": {"width": canvas_width, "height": canvas_height}}


def _iter_text_objects(source_capture: Any) -> list[dict[str, Any]]:
    if not isinstance(source_capture, dict):
        return []
    objects: list[dict[str, Any]] = []
    for page in source_capture.get("pages", []):
        if not isinstance(page, dict):
            continue
        for item in page.get("text_objects", []):
            if isinstance(item, dict):
                copied = dict(item)
                copied.setdefault("page_number", page.get("page_number"))
                objects.append(copied)
    return objects


def _text_font_size(item: dict[str, Any]) -> float | None:
    pt_candidates = [
        item.get("font_size_pt"),
        item.get("applied_pt"),
    ]
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    pt_candidates.extend(
        [
            style.get("font_size_pt"),
            style.get("applied_pt"),
            style.get("applied_font_size_pt"),
        ]
    )
    for value in pt_candidates:
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    px_candidates = [
        item.get("font_size_px"),
        item.get("applied_font_size_px"),
        style.get("font_size_px"),
        style.get("applied_font_size_px"),
        item.get("font_size"),
        style.get("font_size"),
    ]
    for value in px_candidates:
        try:
            if value is not None:
                return round(float(value) * 0.75, 2)
        except (TypeError, ValueError):
            continue
    return None


def _positive_bbox(item: dict[str, Any]) -> bool:
    bbox = item.get("bbox") if isinstance(item.get("bbox"), dict) else {}
    try:
        return float(bbox.get("w", 0) or 0) > 0 and float(bbox.get("h", 0) or 0) > 0
    except (TypeError, ValueError):
        return False


def _fit_allowed_below_minimum(item: dict[str, Any], size: float, absolute_minimum: float) -> bool:
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    if size < absolute_minimum:
        return False
    if not _positive_bbox(item):
        return False
    if bool(style.get("word_wrap")):
        return True
    layout = item.get("layout") if isinstance(item.get("layout"), dict) else {}
    return bool(layout.get("needs_wrapping")) or int(layout.get("line_count") or 0) > 1


def _check_min_font_size(source_capture: Any, minimum: float, *, absolute_minimum: float = 4.5) -> tuple[bool, dict[str, Any]]:
    text_objects = _iter_text_objects(source_capture)
    below: list[dict[str, Any]] = []
    fitted_below: list[dict[str, Any]] = []
    missing = 0
    for item in text_objects:
        size = _text_font_size(item)
        if size is None:
            missing += 1
            continue
        if size < minimum:
            record = {
                "page_number": item.get("page_number"),
                "text": item.get("rendered_text") or item.get("text"),
                "font_size": size,
                "minimum": minimum,
            }
            if _fit_allowed_below_minimum(item, size, absolute_minimum):
                fitted_below.append(record)
            else:
                below.append(record)
    return bool(text_objects) and not below and missing == 0, {
        "minimum": minimum,
        "absolute_minimum": absolute_minimum,
        "text_object_count": len(text_objects),
        "below_minimum": below,
        "fitted_below_minimum": fitted_below,
        "missing_font_size_count": missing,
    }


def _style_value(item: dict[str, Any], field: str) -> Any:
    if field in item:
        return item.get(field)
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    return style.get(field)


def _role_value(item: dict[str, Any]) -> str:
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    for value in (
        item.get("role"),
        item.get("semantic_role"),
        item.get("typography_role"),
        style.get("typography_role"),
        style.get("role"),
    ):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return "text"


def _explicit_role_value(item: dict[str, Any]) -> str | None:
    role = _role_value(item)
    return None if role == "text" else role


def _check_semantic_peer_style(source_capture: Any, field: str) -> tuple[bool, dict[str, Any]]:
    groups: dict[str, set[str]] = {}
    for item in _iter_text_objects(source_capture):
        role = _explicit_role_value(item)
        if role is None:
            continue
        value = _style_value(item, field)
        if value is None:
            continue
        groups.setdefault(role, set()).add(str(value))
    inconsistent = {
        role: sorted(values)
        for role, values in groups.items()
        if len(values) > 1
    }
    return not inconsistent, {"field": field, "groups": {key: sorted(value) for key, value in groups.items()}, "inconsistent": inconsistent}


def _check_office_render(value: Any) -> tuple[bool, dict[str, Any]]:
    exists = _artifact_exists(value)
    return exists, {"render_path": value, "exists": exists, "accepted_sources": ["office", "wps", "explicit_render_artifact"]}


def _check_container_workspace_required(workspace: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(workspace, dict):
        return False, {"reason": "container_workspace_missing"}
    pages = workspace.get("pages")
    if isinstance(pages, list):
        page_reports = [page for page in pages if isinstance(page, dict)]
        failures = [
            {
                "page_number": page.get("page_number"),
                "valid": page.get("valid"),
                "container_count": page.get("container_count"),
                "slot_count": page.get("slot_count"),
                "error_count": page.get("error_count"),
            }
            for page in page_reports
            if not page.get("valid") or int(page.get("slot_count", 0) or 0) <= 0
        ]
        return bool(page_reports) and not failures, {
            "page_count": len(page_reports),
            "container_count": sum(int(page.get("container_count", 0) or 0) for page in page_reports),
            "slot_count": sum(int(page.get("slot_count", 0) or 0) for page in page_reports),
            "failures": failures,
        }
    container_count = int(workspace.get("container_count", 0) or 0)
    slot_count = int(workspace.get("slot_count", 0) or 0)
    error_count = int(workspace.get("error_count", 0) or 0)
    passed = bool(workspace.get("valid")) and container_count > 0 and slot_count > 0 and error_count == 0
    return passed, {
        "container_count": container_count,
        "slot_count": slot_count,
        "error_count": error_count,
        "issues": workspace.get("issues", []),
    }


def _check_workspace_assignment_required(assignment: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(assignment, dict):
        return False, {"reason": "workspace_assignment_missing"}
    pages = assignment.get("pages")
    if isinstance(pages, list):
        page_reports = [page for page in pages if isinstance(page, dict)]
        failures = [
            {
                "page_number": page.get("page_number"),
                "valid": page.get("valid"),
                "assignment_count": page.get("assignment_count"),
                "error_count": page.get("error_count"),
                "issues": page.get("issues", []),
            }
            for page in page_reports
            if not page.get("valid") or int(page.get("assignment_count", 0) or 0) <= 0
        ]
        return bool(page_reports) and not failures, {
            "page_count": len(page_reports),
            "assignment_count": sum(int(page.get("assignment_count", 0) or 0) for page in page_reports),
            "failures": failures,
        }
    assignments = [item for item in assignment.get("assignments", []) if isinstance(item, dict)]
    failures = [
        {
            "text_index": item.get("text_index"),
            "text": item.get("text"),
            "assigned_slot": item.get("assigned_slot"),
            "inside_slot": item.get("inside_slot"),
        }
        for item in assignments
        if not item.get("assigned_slot") or item.get("inside_slot") is not True
    ]
    error_count = int(assignment.get("error_count", 0) or 0)
    passed = bool(assignment.get("valid")) and bool(assignments) and not failures and error_count == 0
    return passed, {
        "assignment_count": len(assignments),
        "error_count": error_count,
        "failures": failures,
        "issues": assignment.get("issues", []),
    }


def _rect_xyxy(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, dict):
        return None
    try:
        x = float(value.get("x", 0.0) or 0.0)
        y = float(value.get("y", 0.0) or 0.0)
        w = float(value.get("w", value.get("width", 0.0)) or 0.0)
        h = float(value.get("h", value.get("height", 0.0)) or 0.0)
    except (TypeError, ValueError):
        return None
    return x, y, x + w, y + h


def _rects_intersect(a: Any, b: Any) -> bool:
    axy = _rect_xyxy(a)
    bxy = _rect_xyxy(b)
    if axy is None or bxy is None:
        return False
    ax1, ay1, ax2, ay2 = axy
    bx1, by1, bx2, by2 = bxy
    return min(ax2, bx2) > max(ax1, bx1) and min(ay2, by2) > max(ay1, by1)


def _workspace_occupied_slot_failures(workspace: dict[str, Any]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    containers = workspace.get("containers", [])
    if not isinstance(containers, list):
        return failures
    for container in containers:
        if not isinstance(container, dict):
            continue
        container_id = container.get("id")
        zones = [item for item in container.get("occupied_zones", []) if isinstance(item, dict)]
        slots = [item for item in container.get("work_slots", []) if isinstance(item, dict)]
        for slot in slots:
            slot_bbox = slot.get("bbox")
            for zone in zones:
                if _rects_intersect(slot_bbox, zone.get("bbox")):
                    failures.append(
                        {
                            "container_id": container_id,
                            "slot_id": slot.get("id"),
                            "occupied_zone": zone.get("id"),
                            "source": zone.get("source"),
                        }
                    )
    return failures


def _check_occupied_zone_avoidance(workspace: Any) -> tuple[bool, dict[str, Any]]:
    if not isinstance(workspace, dict):
        return False, {"reason": "container_workspace_missing"}
    pages = workspace.get("pages")
    if isinstance(pages, list):
        page_reports = [page for page in pages if isinstance(page, dict)]
        failures = []
        for page in page_reports:
            page_failures = _workspace_occupied_slot_failures(page)
            if page_failures:
                failures.append({"page_number": page.get("page_number"), "failures": page_failures})
        return bool(page_reports) and not failures, {
            "page_count": len(page_reports),
            "failures": failures,
        }
    failures = _workspace_occupied_slot_failures(workspace)
    return not failures, {
        "failure_count": len(failures),
        "failures": failures,
        "issues": workspace.get("issues", []),
    }


def _evidence_for_rule(rule: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    report_key = rule.get("report")
    artifact_key = rule.get("artifact")
    if isinstance(report_key, str) and report_key in artifacts:
        path = artifacts[report_key]
        evidence["report_path"] = path
        evidence["report_path_exists"] = _artifact_exists(path)
    if isinstance(artifact_key, str) and artifact_key in artifacts:
        path = artifacts[artifact_key]
        evidence["artifact_path"] = path
        evidence["artifact_path_exists"] = _artifact_exists(path)
    return evidence


def _has_required_evidence(evidence: dict[str, Any]) -> bool:
    if not evidence:
        return False
    exists_flags = [value for key, value in evidence.items() if key.endswith("_exists")]
    return bool(exists_flags) and all(bool(value) for value in exists_flags)


def _evaluate_rule(
    rule: dict[str, Any],
    *,
    reports: dict[str, Any],
    artifacts: dict[str, Any],
) -> dict[str, Any]:
    kind = str(rule.get("kind") or "")
    report_key = str(rule.get("report") or "")
    artifact_key = str(rule.get("artifact") or "")
    passed = False
    observed: Any = None

    if kind == "report_valid":
        observed = reports.get(report_key)
        passed = _is_truthy_report(observed)
    elif kind == "all_reports_valid":
        observed = reports.get(report_key)
        if isinstance(observed, list):
            require_non_empty = bool(rule.get("require_non_empty"))
            passed = (bool(observed) or not require_non_empty) and all(_is_truthy_report(item) for item in observed)
        else:
            passed = False
    elif kind == "artifact_exists":
        observed = artifacts.get(artifact_key)
        passed = _artifact_exists(observed)
    elif kind == "dual_image_pair_required":
        observed = reports.get(report_key)
        passed, observed = _check_dual_image_pair_required(observed)
    elif kind == "source_capture_required":
        observed = reports.get(report_key)
        passed, observed = _check_source_capture_required(observed)
    elif kind == "page_understanding_consumed":
        observed = reports.get(report_key)
        passed, observed = _check_page_understanding_consumed(observed)
    elif kind == "template_region_declared":
        observed = reports.get(report_key)
        passed, observed = _check_template_region_declared(observed)
    elif kind == "min_font_size":
        observed = reports.get(report_key)
        minimum = float(rule.get("minimum_pt", 9.0) or 9.0)
        absolute_minimum = float(rule.get("absolute_minimum_pt", 4.5) or 4.5)
        passed, observed = _check_min_font_size(observed, minimum, absolute_minimum=absolute_minimum)
    elif kind == "semantic_peer_style":
        observed = reports.get(report_key)
        field = str(rule.get("style_field") or "font_weight")
        passed, observed = _check_semantic_peer_style(observed, field)
    elif kind == "office_render_required":
        observed = artifacts.get(artifact_key)
        passed, observed = _check_office_render(observed)
    elif kind == "container_workspace_required":
        observed = reports.get(report_key)
        passed, observed = _check_container_workspace_required(observed)
    elif kind == "workspace_assignment_required":
        observed = reports.get(report_key)
        passed, observed = _check_workspace_assignment_required(observed)
    elif kind == "occupied_zone_avoidance":
        observed = reports.get(report_key)
        passed, observed = _check_occupied_zone_avoidance(observed)
    else:
        observed = {"error": f"Unsupported rule kind: {kind}"}
        passed = False

    evidence = _evidence_for_rule(rule, artifacts)
    evidence_required = bool(rule.get("evidence_required"))
    if evidence_required and not _has_required_evidence(evidence):
        passed = False

    severity = str(rule.get("severity") or "error")
    return {
        "id": rule.get("id"),
        "stage": rule.get("stage"),
        "severity": severity,
        "description": rule.get("description"),
        "kind": kind,
        "passed": passed,
        "blocking": severity == "error" and not passed,
        "evidence_required": evidence_required,
        "evidence": evidence,
        "observed": _summarize_observed(observed),
    }


def _summarize_observed(observed: Any) -> Any:
    if isinstance(observed, dict):
        summary: dict[str, Any] = {}
        for key in (
            "schema",
            "valid",
            "status",
            "error_count",
            "issue_count",
            "below_minimum_count",
            "gap_counts",
            "checks",
            "reason",
            "pair_count",
            "page_count",
            "failure_count",
            "failures",
            "content_region",
            "canvas",
            "minimum",
            "absolute_minimum",
            "text_object_count",
            "below_minimum",
            "fitted_below_minimum",
            "missing_font_size_count",
            "field",
            "groups",
            "inconsistent",
            "render_path",
            "exists",
            "accepted_sources",
            "slot_count",
            "container_count",
            "issues",
            "assignment_count",
            "available",
            "not_applicable",
            "count",
            "consumed",
            "consumed_count",
            "script_truth_verified",
            "fit_review_queue_clear",
            "paths",
        ):
            if key in observed:
                summary[key] = observed[key]
        return summary
    if isinstance(observed, list):
        return {
            "count": len(observed),
            "valid_count": sum(1 for item in observed if _is_truthy_report(item)),
        }
    return observed


def build_page_quality_report(
    *,
    stage: str,
    page_number: int | None,
    project_path: Path,
    artifacts: dict[str, Any],
    reports: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_rules = [rule for rule in (rules or load_quality_rules()) if rule.get("stage") == stage]
    checks = [_evaluate_rule(rule, reports=reports, artifacts=artifacts) for rule in selected_rules]
    blocking_errors = [check for check in checks if check["blocking"]]
    warning_failures = [check for check in checks if check["severity"] == "warning" and not check["passed"]]
    valid = not blocking_errors
    report = {
        "schema": REPORT_SCHEMA,
        "stage": stage,
        "page_number": page_number,
        "project_path": str(project_path),
        "valid": valid,
        "status": "passed" if valid else "rework_required",
        "rule_count": len(checks),
        "passed_count": sum(1 for check in checks if check["passed"]),
        "blocking_error_count": len(blocking_errors),
        "warning_count": len(warning_failures),
        "checks": checks,
        "blocking_errors": blocking_errors,
        "warnings": warning_failures,
        "artifacts": artifacts,
    }
    if extra:
        report["extra"] = extra
    return report


def write_page_quality_report(
    path: Path,
    *,
    stage: str,
    page_number: int | None,
    project_path: Path,
    artifacts: dict[str, Any],
    reports: dict[str, Any],
    rules: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    report = build_page_quality_report(
        stage=stage,
        page_number=page_number,
        project_path=project_path,
        artifacts=artifacts,
        reports=reports,
        rules=rules,
        extra=extra,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report

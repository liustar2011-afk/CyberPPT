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
    candidates = [
        item.get("font_size"),
        item.get("font_size_pt"),
        item.get("applied_pt"),
        item.get("font_size_px"),
        item.get("applied_font_size_px"),
    ]
    style = item.get("style") if isinstance(item.get("style"), dict) else {}
    candidates.extend(
        [
            style.get("font_size"),
            style.get("font_size_pt"),
            style.get("applied_pt"),
            style.get("font_size_px"),
            style.get("applied_font_size_px"),
        ]
    )
    for value in candidates:
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _check_min_font_size(source_capture: Any, minimum: float) -> tuple[bool, dict[str, Any]]:
    text_objects = _iter_text_objects(source_capture)
    below: list[dict[str, Any]] = []
    missing = 0
    for item in text_objects:
        size = _text_font_size(item)
        if size is None:
            missing += 1
            continue
        if size < minimum:
            below.append(
                {
                    "page_number": item.get("page_number"),
                    "text": item.get("rendered_text") or item.get("text"),
                    "font_size": size,
                    "minimum": minimum,
                }
            )
    return bool(text_objects) and not below and missing == 0, {
        "minimum": minimum,
        "text_object_count": len(text_objects),
        "below_minimum": below,
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


def _check_semantic_peer_style(source_capture: Any, field: str) -> tuple[bool, dict[str, Any]]:
    groups: dict[str, set[str]] = {}
    for item in _iter_text_objects(source_capture):
        role = _role_value(item)
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
    elif kind == "template_region_declared":
        observed = reports.get(report_key)
        passed, observed = _check_template_region_declared(observed)
    elif kind == "min_font_size":
        observed = reports.get(report_key)
        minimum = float(rule.get("minimum_pt", 9.0) or 9.0)
        passed, observed = _check_min_font_size(observed, minimum)
    elif kind == "semantic_peer_style":
        observed = reports.get(report_key)
        field = str(rule.get("style_field") or "font_weight")
        passed, observed = _check_semantic_peer_style(observed, field)
    elif kind == "office_render_required":
        observed = artifacts.get(artifact_key)
        passed, observed = _check_office_render(observed)
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
            "failures",
            "content_region",
            "canvas",
            "minimum",
            "text_object_count",
            "below_minimum",
            "missing_font_size_count",
            "field",
            "groups",
            "inconsistent",
            "render_path",
            "exists",
            "accepted_sources",
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

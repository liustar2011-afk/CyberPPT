from __future__ import annotations

from typing import Any


REQUIRED_TOOLS = (
    "source_capture",
    "semantic_binding",
    "semantic_plan",
    "scene_graph",
    "visual_registry",
    "container_workspace",
    "workspace_assignment",
    "office_textbox_fit",
    "editable_pptx",
    "render_compare",
    "qa_registry",
)


def _report_passes(tool_name: str, report: dict[str, Any]) -> bool:
    if tool_name == "render_compare":
        if "passed" in report:
            return bool(report.get("passed"))
    if "valid" in report:
        return bool(report.get("valid"))
    if "status" in report:
        return str(report.get("status")) in {"ok", "pass", "passed", "ready", "ready_for_delivery"}
    return True


def _safe_non_negative_int(value: Any, reason: str = "invalid_page_understanding_count") -> tuple[int, str | None]:
    if isinstance(value, bool):
        return 0, reason
    if isinstance(value, int):
        return (value, None) if value >= 0 else (0, reason)
    if isinstance(value, str) and value.isascii() and value.isdecimal():
        return int(value), None
    return 0, reason


def summarize_page_understanding_readiness(source_capture: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(source_capture, dict):
        return {
            "page_understanding_available": False,
            "page_understanding_count": 0,
            "page_understanding_consumed": False,
            "page_understanding_consumed_count": 0,
            "script_truth_verified": False,
            "fit_review_queue_clear": False,
        }
    inputs = source_capture.get("inputs") if isinstance(source_capture.get("inputs"), dict) else {}
    pages = [page for page in source_capture.get("pages", []) if isinstance(page, dict)]
    count, reason = _safe_non_negative_int(inputs.get("page_understanding_count", 0))
    paths = inputs.get("page_understanding_paths", [])
    available = bool(inputs.get("page_understanding_available") or count > 0 or paths)
    page_summaries = [
        page.get("page_understanding")
        for page in pages
        if isinstance(page.get("page_understanding"), dict)
    ]
    consumed_count = len(page_summaries)
    consumed = bool(available and count > 0 and consumed_count >= count)
    script_truth_checks: list[bool] = []
    issues = [reason] if reason is not None else []
    for summary in page_summaries:
        text_block_count, text_block_reason = _safe_non_negative_int(
            summary.get("text_block_count", 0),
            "invalid_page_understanding_text_block_count",
        )
        if text_block_reason is not None:
            issues.append(text_block_reason)
            script_truth_checks.append(False)
            continue
        if text_block_count > 0:
            script_truth_checks.append(summary.get("script_truth_verified") is True)
    fit_review_checks = [
        summary.get("fit_review_queue_clear") is True
        for summary in page_summaries
    ]
    readiness = {
        "page_understanding_available": available,
        "page_understanding_count": count,
        "page_understanding_consumed": consumed,
        "page_understanding_consumed_count": consumed_count,
        "page_understanding_paths": paths,
        "script_truth_verified": bool(script_truth_checks) and all(script_truth_checks),
        "fit_review_queue_clear": bool(fit_review_checks) and all(fit_review_checks),
    }
    if reason is not None:
        readiness["reason"] = reason
    if issues:
        readiness["issues"] = [{"code": code} for code in dict.fromkeys(issues)]
    return readiness


def _page_understanding_blocking_errors(readiness: dict[str, Any]) -> list[dict[str, str]]:
    if not readiness.get("page_understanding_available"):
        return []
    blocking: list[dict[str, str]] = []
    if not readiness.get("page_understanding_consumed"):
        blocking.append({"tool": "source_capture", "code": "page_understanding_not_consumed"})
    if not readiness.get("script_truth_verified"):
        blocking.append({"tool": "source_capture", "code": "script_truth_not_verified"})
    if not readiness.get("fit_review_queue_clear"):
        blocking.append({"tool": "source_capture", "code": "page_understanding_fit_review_queue_not_clear"})
    return blocking


def build_production_readiness(
    *,
    stage: str,
    artifacts: dict[str, str | None],
    reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    page_understanding = summarize_page_understanding_readiness(reports.get("source_capture"))
    tool_consumption = {}
    for name in REQUIRED_TOOLS:
        artifact = artifacts.get(name)
        tool_consumption[name] = {
            "ran": bool(artifact),
            "artifact": artifact,
        }
    all_consumed = all(item["ran"] for item in tool_consumption.values())
    blocking = [
        {"tool": name, "code": "tool_not_consumed"}
        for name, item in tool_consumption.items()
        if not item["ran"]
    ]
    failed_reports = [
        {"tool": name, "code": "tool_report_failed"}
        for name, report in reports.items()
        if name in REQUIRED_TOOLS and isinstance(report, dict) and not _report_passes(name, report)
    ]
    blocking.extend(failed_reports)
    page_understanding_blocking = _page_understanding_blocking_errors(page_understanding)
    blocking.extend(page_understanding_blocking)
    reports_pass = not failed_reports
    production_ready = all_consumed and reports_pass and not page_understanding_blocking
    return {
        "schema": "cyberppt.stage02.production_readiness.v1",
        "stage": stage,
        "status": "production_ready" if production_ready else "production_rework_required",
        "valid": production_ready,
        "checks": {
            "all_required_tools_consumed": all_consumed,
            "all_consumed_reports_pass": reports_pass,
            "blocking_count": len(blocking),
            "page_understanding_available": page_understanding["page_understanding_available"],
            "page_understanding_consumed": page_understanding["page_understanding_consumed"],
            "script_truth_verified": page_understanding["script_truth_verified"],
            "fit_review_queue_clear": page_understanding["fit_review_queue_clear"],
        },
        "page_understanding_readiness": page_understanding,
        "tool_consumption": tool_consumption,
        "blocking_errors": blocking,
        "reports": reports,
    }

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


def build_production_readiness(
    *,
    stage: str,
    artifacts: dict[str, str | None],
    reports: dict[str, dict[str, Any]],
) -> dict[str, Any]:
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
    reports_pass = not failed_reports
    production_ready = all_consumed and reports_pass
    return {
        "schema": "cyberppt.stage02.production_readiness.v1",
        "stage": stage,
        "status": "production_ready" if production_ready else "production_rework_required",
        "valid": production_ready,
        "checks": {
            "all_required_tools_consumed": all_consumed,
            "all_consumed_reports_pass": reports_pass,
            "blocking_count": len(blocking),
        },
        "tool_consumption": tool_consumption,
        "blocking_errors": blocking,
        "reports": reports,
    }

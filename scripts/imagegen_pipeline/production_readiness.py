from __future__ import annotations

from typing import Any, Iterable


REQUIRED_TOOLS = (
    "reconstruction_inventory",
    "svg_output",
    "reconstruction_quality",
    "text_content_qa",
    "render_compare",
    "exported_pptx",
)


def _report_passes(tool_name: str, report: dict[str, Any]) -> bool:
    if tool_name == "render_compare" and "passed" in report:
        return bool(report.get("passed"))
    if "valid" in report:
        return bool(report.get("valid"))
    if "status" in report:
        return str(report.get("status")) in {
            "ok", "pass", "passed", "ready", "ready_for_delivery",
        }
    return True


def build_production_readiness(
    *,
    stage: str,
    artifacts: dict[str, str | None],
    reports: dict[str, dict[str, Any]],
    required_tools: Iterable[str] = REQUIRED_TOOLS,
) -> dict[str, Any]:
    required = tuple(required_tools)
    tool_consumption = {
        name: {"ran": bool(artifacts.get(name)), "artifact": artifacts.get(name)}
        for name in required
    }
    missing = [
        {"tool": name, "code": "tool_not_consumed"}
        for name, item in tool_consumption.items()
        if not item["ran"]
    ]
    failed = [
        {"tool": name, "code": "tool_report_failed"}
        for name, report in reports.items()
        if name in required and isinstance(report, dict) and not _report_passes(name, report)
    ]
    blocking = [*missing, *failed]
    production_ready = not blocking
    return {
        "schema": "cyberppt.stage02.production_readiness.v1",
        "stage": stage,
        "status": "production_ready" if production_ready else "production_rework_required",
        "valid": production_ready,
        "checks": {
            "all_required_tools_consumed": not missing,
            "all_consumed_reports_pass": not failed,
            "blocking_count": len(blocking),
        },
        "tool_consumption": tool_consumption,
        "blocking_errors": blocking,
        "reports": reports,
    }

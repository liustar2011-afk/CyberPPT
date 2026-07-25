"""Persist outline audit attempts and bounded retry directions."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.argument_flow_contract import (
    argument_graph_summary,
    audit_argument_flow,
)
from cyberppt.outline_contract import audit_outline, load_outline, retry_directive
from cyberppt.source_truth_contract import load_source_truth
from cyberppt.stage01_controls import (
    assert_escalation_resolved,
    snapshot_reference_gate,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _escalation_options(codes: list[str]) -> list[dict[str, str]]:
    options = [
        {"id": "source_native", "label": "恢复源材料方案顺序", "action": "按材料角色和正式章节使命重建连续页面序列。"},
        {"id": "business_aggregation", "label": "按业务问题聚合", "action": "合并重复业务问题与视觉中心，重新分配页面密度。"},
    ]
    if "SOURCE_WEIGHT_DISTORTED" in codes or "SOLUTION_ARCHITECTURE_REQUIRED" in codes:
        options.append({"id": "user_priority", "label": "由用户明确优先级", "action": "提交主体内容权重冲突，请用户选择优先方向。"})
    return options[:3]


def run_outline_audit(
    project: Path,
    input_path: Path,
    max_attempts: int = 3,
    source_truth_path: Path | None = None,
) -> tuple[int, dict[str, object]]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    assert_escalation_resolved(project, "source_truth")
    payload = load_outline(input_path.expanduser().resolve())
    resolved_source_truth = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "source-truth.json"
    )
    source_truth = (
        load_source_truth(resolved_source_truth)
        if resolved_source_truth.exists()
        else None
    )
    if source_truth_path is not None and source_truth is None:
        raise FileNotFoundError(f"source truth does not exist: {resolved_source_truth}")
    retry = payload.get("retry") if isinstance(payload.get("retry"), dict) else {}
    attempt = int(retry.get("attempt", 1))
    effective_max = int(retry.get("max_attempts", max_attempts))
    if not 1 <= effective_max <= 5:
        raise ValueError("retry.max_attempts must be between 1 through 5")
    stage = project / "workbench" / "stages" / "01-analysis"
    argument_issues = (
        audit_argument_flow(payload, source_truth)
        if source_truth is not None
        else []
    )
    issues = audit_outline(payload, source_truth)
    directive = retry_directive(issues, str(retry.get("strategy") or ""))
    report: dict[str, object] = {
        "schema": "cyberppt.outline_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "attempt": attempt,
        "max_attempts": effective_max,
        "remaining_attempts": max(0, effective_max - attempt),
        "issues": [issue.to_dict() for issue in issues],
        "retry_directive": directive,
        "argument_contract_mode": str(
            payload.get("argument_contract_mode") or "legacy"
        ),
        "checked_source_truth": (
            str(resolved_source_truth) if source_truth is not None else None
        ),
        "argument_graph": argument_graph_summary(payload, source_truth),
        "failed_edges": [
            list(edge)
            for issue in argument_issues
            for edge in issue.failed_edges
        ],
        "retry_scope": sorted(
            {
                page
                for issue in argument_issues
                for page in issue.pages
                if page
            }
        ),
        "reference_gate": snapshot_reference_gate("outline"),
    }
    _write_json(stage / "outline-contract.json", payload)
    _write_json(stage / "outline-audit.json", report)
    _write_json(stage / "outline-attempts" / f"attempt-{attempt:02d}.json", {"outline": payload, "audit": report})
    if not issues:
        return 0, report
    if attempt < effective_max:
        return 4, report
    codes = list(directive["issue_codes"])
    report["status"] = "user_decision_required"
    report["options"] = _escalation_options(codes)
    _write_json(stage / "outline-audit.json", report)
    _write_json(stage / "outline-escalation.json", report)
    return 5, report

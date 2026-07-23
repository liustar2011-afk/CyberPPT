"""Persist outline audit attempts and bounded retry directions."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.outline_contract import audit_outline, load_outline, retry_directive


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
) -> tuple[int, dict[str, object]]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    payload = load_outline(input_path.expanduser().resolve())
    retry = payload.get("retry") if isinstance(payload.get("retry"), dict) else {}
    attempt = int(retry.get("attempt", 1))
    effective_max = int(retry.get("max_attempts", max_attempts))
    if not 1 <= effective_max <= 5:
        raise ValueError("retry.max_attempts must be between 1 through 5")
    stage = project / "workbench" / "stages" / "01-analysis"
    issues = audit_outline(payload)
    directive = retry_directive(issues, str(retry.get("strategy") or ""))
    report: dict[str, object] = {
        "schema": "cyberppt.outline_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "attempt": attempt,
        "max_attempts": effective_max,
        "remaining_attempts": max(0, effective_max - attempt),
        "issues": [issue.to_dict() for issue in issues],
        "retry_directive": directive,
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

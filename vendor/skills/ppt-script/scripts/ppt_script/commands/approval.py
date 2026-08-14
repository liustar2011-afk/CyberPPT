from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from ..pages_index import is_active_page_file
from ..workflow import assert_page_approval_allowed, editorial_gate_required


STEP_FILE_MAP = {
    "analysis": "analysis/00-analysis.md",
    "truth": "analysis/01-source-truth-map.md",
    "decision": "decision/01-decision.md",
    "outline": "outline/02-outline.md",
    "expression": "decision/02-expression-logic.md",
    "evaluation": "review/05-evaluation.md",
    "review": "review/04-review.md",
}

AUTHORING_APPROVAL_STEPS = ("decision", "outline", "expression")
PLAN_AUDIT_JSON = "outline/02-plan-audit.json"


def approval_record_path(project: Path, step: str) -> Path:
    return project / "approvals" / f"{step}-approval.json"


def load_approval(project: Path, step: str) -> dict | None:
    path = approval_record_path(project, step)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def approval_is_fresh(project: Path, step: str) -> bool:
    record = load_approval(project, step)
    if not record:
        return False
    relative = STEP_FILE_MAP.get(step)
    if not relative:
        return False
    target = project / relative
    if not target.is_file():
        return False
    expected = record.get("sha256")
    if not isinstance(expected, str) or not expected:
        return False
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    return actual == expected


def required_authoring_approvals(project: Path) -> tuple[str, ...]:
    if editorial_gate_required(project):
        return AUTHORING_APPROVAL_STEPS
    return ()


def assert_plan_check_fresh_for_expression(project: Path) -> None:
    """expression approve requires a passing plan-check bound to current outline SHA."""
    outline = project / "outline/02-outline.md"
    if not outline.is_file():
        raise ValueError("approve expression 前缺少 outline/02-outline.md。")
    audit_path = project / PLAN_AUDIT_JSON
    if not audit_path.is_file():
        raise ValueError(
            "approve expression 前须先通过 plan-check。"
            '请运行：python scripts/project_manager.py plan-check "<项目>"'
        )
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"无法读取 {PLAN_AUDIT_JSON}：{exc}") from exc
    if not isinstance(payload, dict) or not payload.get("passed"):
        raise ValueError(
            "plan-check 未通过，不能批准 expression。"
            "请先修正提纲结论先行问题并重跑 plan-check。"
        )
    recorded = payload.get("outline_sha256")
    actual = hashlib.sha256(outline.read_bytes()).hexdigest()
    if not isinstance(recorded, str) or recorded != actual:
        raise ValueError(
            "plan-check 已过期（提纲已变更）。"
            '请重新运行：python scripts/project_manager.py plan-check "<项目>"'
        )


def assert_authoring_approvals(project: Path) -> None:
    steps = required_authoring_approvals(project)
    if not steps:
        return

    missing_targets: list[str] = []
    missing_approvals: list[str] = []
    stale_approvals: list[str] = []

    for step in steps:
        relative = STEP_FILE_MAP[step]
        target = project / relative
        if not target.exists() or target.stat().st_size <= 80:
            missing_targets.append(step)
            continue
        if load_approval(project, step) is None:
            missing_approvals.append(step)
        elif not approval_is_fresh(project, step):
            stale_approvals.append(step)

    if not missing_targets and not missing_approvals and not stale_approvals:
        return

    parts: list[str] = ["写页前人审批准未通过。"]
    if missing_targets:
        details = []
        for step in missing_targets:
            path = STEP_FILE_MAP[step]
            if step == "expression":
                details.append(f"{step}（先生成 {path}）")
            else:
                details.append(f"{step}（缺少有效 {path}）")
        parts.append("缺少目标文件：" + "、".join(details) + "。")
    if missing_approvals:
        commands = "；".join(
            f'python scripts/project_manager.py approve "<项目>" {step}'
            for step in missing_approvals
        )
        parts.append(
            "缺少批准凭证："
            + "、".join(missing_approvals)
            + f"。请运行：{commands}。"
        )
    if stale_approvals:
        commands = "；".join(
            f'python scripts/project_manager.py approve "<项目>" {step}'
            for step in stale_approvals
        )
        parts.append(
            "批准已过期（文件已改、SHA 不匹配）："
            + "、".join(stale_approvals)
            + f"。请重新运行：{commands}。"
        )
    parts.append(
        "正式项目写页前须对 decision、outline、expression 完成仍有效的人审 approve；"
        "也可先运行 authoring-check 查看缺口。"
    )
    raise ValueError("".join(parts))


def approve_artifact(project: Path, step: str, note: str = "") -> Path:
    assert_page_approval_allowed(project, step)
    if step == "expression" and editorial_gate_required(project):
        assert_plan_check_fresh_for_expression(project)
    if step in STEP_FILE_MAP:
        target = project / STEP_FILE_MAP[step]
        step_id = step
    else:
        matches = sorted(
            path
            for path in (project / "pages").glob("*.md")
            if is_active_page_file(path) and step.lower() in path.stem.lower()
        )
        if not matches:
            raise ValueError(f"未知确认步骤或页面：{step}")
        target = matches[0]
        step_id = target.stem
    if not target.exists() or target.stat().st_size <= 80:
        raise ValueError(f"目标文件不存在或仍是占位内容：{target}")
    record = {
        "step": step_id,
        "file": str(target.relative_to(project)),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "approved_at": datetime.now().isoformat(timespec="seconds"),
        "note": note,
    }
    output = approval_record_path(project, step_id)
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return output

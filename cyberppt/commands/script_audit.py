"""Persist script quality audits, changed-direction retries, and reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from cyberppt.outline_contract import load_outline
from cyberppt.script_quality_contract import (
    audit_script_quality,
    parse_script_markdown,
    script_retry_directive,
)
from cyberppt.source_truth_contract import load_source_truth


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _next_attempt(attempts_dir: Path) -> int:
    numbers = [
        int(path.stem.split("-")[-1])
        for path in attempts_dir.glob("attempt-*.json")
        if path.stem.split("-")[-1].isdigit()
    ]
    return max(numbers, default=0) + 1


def _render_markdown(report: dict[str, object]) -> str:
    coverage = (
        report.get("coverage")
        if isinstance(report.get("coverage"), dict)
        else {}
    )
    issue_items = (
        report.get("issues")
        if isinstance(report.get("issues"), list)
        else []
    )
    lines = [
        "# PPT 脚本质量审计",
        "",
        f"- 状态：`{report.get('status', '')}`",
        f"- 尝试：{report.get('attempt', '')} / {report.get('max_attempts', '')}",
        f"- 页面：{coverage.get('page_count', 0)}",
        f"- 问题：{len(issue_items)}",
        "",
        "## 失败页面",
        "",
    ]
    failed = report.get("failed_pages")
    failed_pages = failed if isinstance(failed, list) else []
    lines.append("、".join(str(item) for item in failed_pages) or "无。")
    lines.extend(["", "## 问题", ""])
    for issue in issue_items:
        if not isinstance(issue, dict):
            continue
        pages = issue.get("pages")
        evidence = issue.get("evidence")
        page_text = "、".join(str(item) for item in pages) if isinstance(pages, list) else ""
        evidence_text = (
            "；".join(str(item) for item in evidence)
            if isinstance(evidence, list)
            else ""
        )
        lines.extend(
            [
                f"### {issue.get('code', '')}",
                "",
                f"- 页面：{page_text or '全局'}",
                f"- 说明：{issue.get('message', '')}",
                f"- 证据：{evidence_text or '无'}",
                f"- 建议：{issue.get('suggested_action', '')}",
                "",
            ]
        )
    directive = (
        report.get("retry_directive")
        if isinstance(report.get("retry_directive"), dict)
        else {}
    )
    lines.extend(
        [
            "## 重试方向",
            "",
            f"- 策略：`{directive.get('strategy', '')}`",
            f"- 指令：{directive.get('instruction', '')}",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _relative(project: Path, path: Path) -> str:
    try:
        return path.relative_to(project).as_posix()
    except ValueError as exc:
        raise ValueError(
            f"script audit artifacts and dependencies must be inside project: {path}"
        ) from exc


def _register_artifacts(
    project: Path,
    paths: list[Path],
    status: str,
    input_path: Path,
    outline_path: Path,
    source_truth_path: Path,
) -> None:
    ledger_path = project / "workbench" / "artifact-ledger.json"
    ledger = (
        json.loads(ledger_path.read_text(encoding="utf-8-sig"))
        if ledger_path.exists()
        else {"schema": "cyberppt.artifact_ledger.v1", "artifacts": []}
    )
    artifacts = ledger.get("artifacts")
    current = artifacts if isinstance(artifacts, list) else []
    by_path = {
        str(item.get("path")): item
        for item in current
        if isinstance(item, dict)
    }
    dependencies = [
        _relative(project, input_path),
        _relative(project, outline_path),
        _relative(project, source_truth_path),
    ]
    for path in paths:
        relative = _relative(project, path)
        by_path[relative] = {
            "stage": "02-blueprint-dual-image",
            "page": None,
            "path": relative,
            "status": status,
            "depends_on": dependencies,
            "supersedes": [],
            "resume_command": (
                "python -m cyberppt script-audit "
                f"{project.as_posix()} --input {input_path.as_posix()}"
            ),
            "sha256": _sha256(path),
        }
    ledger["artifacts"] = list(by_path.values())
    _write_json(ledger_path, ledger)


def _escalation_options() -> list[dict[str, str]]:
    return [
        {
            "id": "merge_pages",
            "label": "合并重复页面",
            "action": "保留完整业务问题，将重复展开页面合并或改为回指。",
        },
        {
            "id": "revise_outline_contract",
            "label": "调整页面合同",
            "action": "重新批准受影响页面的角色、前置依赖、来源或视觉中心。",
        },
        {
            "id": "accept_documented_risk",
            "label": "保留结构并记录风险",
            "action": "保留当前最佳稿，将未解决问题登记为后续视觉生产风险。",
        },
    ]


def run_script_audit(
    project: Path,
    input_path: Path,
    outline_path: Path | None = None,
    source_truth_path: Path | None = None,
    attempt: int | None = None,
    max_attempts: int = 3,
) -> tuple[int, dict[str, object]]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    input_path = input_path.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    if not input_path.exists():
        raise FileNotFoundError(f"script does not exist: {input_path}")
    outline_path = (
        outline_path.expanduser().resolve()
        if outline_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "outline.json"
    )
    source_truth_path = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "source-truth.json"
    )
    if not outline_path.exists():
        raise FileNotFoundError(f"outline does not exist: {outline_path}")
    outline = load_outline(outline_path)
    if (
        not source_truth_path.exists()
        and outline.get("argument_contract_mode") == "strict"
    ):
        raise FileNotFoundError(
            f"strict script audit requires Source Truth: {source_truth_path}"
        )
    if not source_truth_path.exists():
        raise FileNotFoundError(
            f"source truth does not exist: {source_truth_path}"
        )
    source_truth = load_source_truth(source_truth_path)
    document = parse_script_markdown(
        input_path.read_text(encoding="utf-8-sig")
    )
    audit_dir = project / "workbench" / "scripts" / "audits"
    attempts_dir = audit_dir / "attempts"
    effective_attempt = (
        attempt if attempt is not None else _next_attempt(attempts_dir)
    )
    if not 1 <= effective_attempt <= max_attempts:
        raise ValueError("attempt must be between 1 and max_attempts")
    previous_strategy = ""
    previous = attempts_dir / f"attempt-{effective_attempt - 1:02d}.json"
    if previous.exists():
        previous_payload = json.loads(
            previous.read_text(encoding="utf-8-sig")
        )
        previous_audit = previous_payload.get("audit")
        if isinstance(previous_audit, dict):
            previous_directive = previous_audit.get("retry_directive")
            if isinstance(previous_directive, dict):
                previous_strategy = str(
                    previous_directive.get("strategy") or ""
                )
    issues = audit_script_quality(document, outline, source_truth)
    directive = script_retry_directive(issues, previous_strategy)
    failed_pages = sorted(
        {page for issue in issues for page in issue.pages}
    )
    report: dict[str, object] = {
        "schema": "cyberppt.script_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "attempt": effective_attempt,
        "max_attempts": max_attempts,
        "remaining_attempts": max(0, max_attempts - effective_attempt),
        "input": str(input_path),
        "outline": str(outline_path),
        "source_truth": str(source_truth_path),
        "coverage": {
            "page_count": len(document.pages),
            "first_page": document.pages[0].page_id,
            "last_page": document.pages[-1].page_id,
        },
        "issues": [issue.to_dict() for issue in issues],
        "failed_pages": failed_pages,
        "retry_scope": failed_pages,
        "retry_directive": directive,
    }
    if issues and effective_attempt >= max_attempts:
        report["status"] = "user_decision_required"
        report["options"] = _escalation_options()
    latest_json = audit_dir / "script-audit.json"
    latest_md = audit_dir / "script-audit.md"
    attempt_json = (
        attempts_dir / f"attempt-{effective_attempt:02d}.json"
    )
    _write_json(latest_json, report)
    latest_md.parent.mkdir(parents=True, exist_ok=True)
    latest_md.write_text(_render_markdown(report), encoding="utf-8")
    _write_json(
        attempt_json,
        {"script_sha256": _sha256(input_path), "audit": report},
    )
    artifact_paths = [latest_json, latest_md, attempt_json]
    if report["status"] == "user_decision_required":
        escalation = audit_dir / "script-escalation.json"
        _write_json(escalation, report)
        artifact_paths.append(escalation)
    _register_artifacts(
        project,
        artifact_paths,
        str(report["status"]),
        input_path,
        outline_path,
        source_truth_path,
    )
    if not issues:
        return 0, report
    if report["status"] == "user_decision_required":
        return 5, report
    return 4, report

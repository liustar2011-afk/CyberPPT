"""Persist script quality audits, changed-direction retries, and reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from uuid import uuid4

from cyberppt.artifact_ledger import append_artifacts
from cyberppt.outline_contract import load_outline
from cyberppt.script_quality_contract import (
    audit_final_manuscript_form,
    audit_script_quality,
    build_communication_review,
    is_final_script_path,
    parse_script_markdown,
    script_retry_directive,
)
from cyberppt.source_truth_contract import load_source_truth
from cyberppt.stage01_controls import (
    assert_escalation_resolved,
    snapshot_reference_gate,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


CONTENT_REVIEW_DECISIONS = (
    "single_mission",
    "module_same_dimension",
    "nonessential_information_removed",
    "cross_page_new_value",
)


def _content_review_status(project: Path, script_sha256: str) -> dict[str, object]:
    path = project / "workbench" / "scripts" / "audits" / "content-review.json"
    if not path.exists():
        return {"status": "missing", "path": str(path), "decisions": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {"status": "invalid", "path": str(path), "decisions": {}}
    decisions = payload.get("decisions")
    decision_map = decisions if isinstance(decisions, dict) else {}
    page_reviews = payload.get("pages")
    page_map = page_reviews if isinstance(page_reviews, dict) else {}
    outline_path = project / "workbench/stages/01-analysis/outline.json"
    outline = json.loads(outline_path.read_text(encoding="utf-8-sig"))
    required_pages = [
        str(item.get("page_id"))
        for item in outline.get("pages", [])
        if isinstance(item, dict) and item.get("page_type") == "content"
    ]
    pages_approved = all(
        isinstance(page_map.get(page_id), dict)
        and all(page_map[page_id].get(key) is True for key in CONTENT_REVIEW_DECISIONS)
        and bool(str(page_map[page_id].get("note") or "").strip())
        for page_id in required_pages
    )
    if str(payload.get("script_sha256") or "").upper() != script_sha256.upper():
        status = "stale"
    elif not all(decision_map.get(key) is True for key in CONTENT_REVIEW_DECISIONS) or not pages_approved:
        status = "incomplete"
    else:
        status = "approved"
    return {
        "status": status,
        "path": str(path),
        "decisions": decision_map,
        "reviewed_pages": len(page_map),
        "required_pages": len(required_pages),
    }


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
        f"- 内容复核：{report.get('content_review', {}).get('status', 'missing') if isinstance(report.get('content_review'), dict) else 'missing'}",
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
    communication = (
        report.get("communication_review")
        if isinstance(report.get("communication_review"), dict)
        else {}
    )
    communication_pages = communication.get("pages")
    lines.extend(
        [
            "## 上屏文字六问",
            "",
            f"- 页面使命覆盖：{communication.get('mission_coverage', 0)} / {communication.get('content_pages', 0)}",
            f"- 可选上屏结论：已呈现 {communication.get('lead_coverage_count', 0)} 页；未声明上屏结论的页面不计缺失",
            f"- 阅读型信息密度：默认高密度；低于自适应基线的页面 {communication.get('reading_density_low_count', 0)} 页；不以补写结论代替补充事实与关系。",
            f"- 自动提醒：{communication.get('warning_count', 0)} 条；优先核对关系骨架同构与三段式取舍说明（必留上屏/仅讲解/仅追溯），不得用重复字句刷密度。",
            "",
        ]
    )
    if isinstance(communication_pages, list):
        for page in communication_pages:
            if not isinstance(page, dict):
                continue
            findings = page.get("findings")
            finding_codes = [
                str(item.get("code"))
                for item in findings
                if isinstance(item, dict) and item.get("code")
            ] if isinstance(findings, list) else []
            lines.extend(
                [
                    f"### 第{page.get('sequence', '')}页：{page.get('title', '')}",
                    "",
                    f"- 页面使命：{page.get('mission') or '未提供'}",
                    f"- 核心结论：{page.get('core_message') or page.get('main_message') or '未提供'}",
                    f"- 上屏结论状态：{page.get('lead_status', 'check')}（可选）",
                    f"- 阅读密度：{page.get('reading_density_status', 'check')}（{page.get('effective_chars', 0)} / {page.get('effective_char_target', 0)}）",
                    f"- 六问状态：单一使命=人工复核；模块同维度=人工复核；信息取舍=人工复核；领导展开={'通过' if page.get('review_questions', {}).get('leadership_expandability') == 'pass' else '待检查'}；视觉表达={'通过' if page.get('review_questions', {}).get('visual_expression_ready') == 'pass' else '待检查'}",
                    f"- 自动提醒：{'、'.join(finding_codes) or '无'}",
                    "",
                ]
            )
    lines.extend(["## 页面质量表", "", "| 页面 | 唯一任务 | 新增价值 | 状态 |", "|---|---|---|---|"])
    outline_path = report.get("outline")
    if isinstance(outline_path, str) and Path(outline_path).exists():
        outline = json.loads(Path(outline_path).read_text(encoding="utf-8-sig"))
        review_status = (
            report.get("content_review", {}).get("status", "missing")
            if isinstance(report.get("content_review"), dict)
            else "missing"
        )
        for page in outline.get("pages", []):
            if isinstance(page, dict) and page.get("page_type") == "content":
                lines.append(
                    f"| {page.get('page_id')} | {page.get('page_job', '')} | "
                    f"{page.get('new_value_vs_previous', '')} | {review_status} |"
                )
    lines.append("")
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
    dependencies = [
        _relative(project, input_path),
        _relative(project, outline_path),
        _relative(project, source_truth_path),
    ]
    records: list[dict[str, object]] = []
    for path in paths:
        relative = _relative(project, path)
        records.append(
            {
                "stage": "02-blueprint-dual-image",
                "page": None,
                "path": relative,
                "status": status,
                "depends_on": dependencies,
                "resume_command": (
                    "python -m cyberppt script-audit "
                    f"{project.as_posix()} --input {input_path.as_posix()}"
                ),
                "sha256": _sha256(path),
            }
        )
    append_artifacts(
        project / "workbench" / "artifact-ledger.json",
        records,
        build_id=f"script-audit-{_sha256(input_path)[:10]}-{uuid4().hex[:8]}",
    )


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
    assert_escalation_resolved(project, "outline")
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
    script_text = input_path.read_text(encoding="utf-8-sig")
    script_sha256 = _sha256(input_path)
    document = parse_script_markdown(script_text)
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
    if is_final_script_path(input_path):
        issues.extend(audit_final_manuscript_form(script_text))
    communication_review = build_communication_review(document, outline)
    errors = [issue for issue in issues if issue.severity == "error"]
    content_review = _content_review_status(project, script_sha256)
    directive = script_retry_directive(errors, previous_strategy)
    failed_pages = sorted(
        {page for issue in errors for page in issue.pages}
    )
    report: dict[str, object] = {
        "schema": "cyberppt.script_audit.v1",
        "status": (
            "rewrite_required"
            if errors
            else "passed"
            if content_review["status"] == "approved"
            else "content_review_required"
        ),
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
        "communication_review": communication_review,
        "content_review": content_review,
        "failed_pages": failed_pages,
        "retry_scope": failed_pages,
        "retry_directive": directive,
        "reference_gate": snapshot_reference_gate("script", project),
    }
    if errors and effective_attempt >= max_attempts:
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
        {"script_sha256": script_sha256, "audit": report},
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
    if not errors and report["status"] == "passed":
        return 0, report
    if not errors:
        return 4, report
    if report["status"] == "user_decision_required":
        return 5, report
    return 4, report

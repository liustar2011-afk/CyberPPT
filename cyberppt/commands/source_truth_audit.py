"""Persist Source Truth audits, changed-direction retries, and readable views."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.source_truth_contract import (
    audit_source_receipts,
    audit_source_truth,
    collect_source_receipts,
    load_source_truth,
    source_truth_retry_directive,
)
from cyberppt.stage01_controls import snapshot_reference_gate


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _escape(value: object) -> str:
    if isinstance(value, list):
        value = "；".join(str(item) for item in value)
    return str(value or "").replace("|", r"\|").replace("\r", " ").replace("\n", " ")


def _locator_text(record: dict[str, object]) -> str:
    locator = record.get("source_locator")
    if not isinstance(locator, dict):
        return ""
    parts = [locator.get("file"), locator.get("section")]
    for field, label in (
        ("paragraph", "段落"),
        ("table", "表"),
        ("table_row", "行"),
        ("cell", "单元格"),
    ):
        value = locator.get(field)
        if value not in (None, ""):
            parts.append(f"{label}{value}")
    return " / ".join(str(item) for item in parts if item not in (None, ""))


def _coverage_summary(payload: dict[str, object]) -> dict[str, int]:
    targets = payload.get("coverage_targets")
    records = payload.get("records")
    target_items = [item for item in targets if isinstance(item, dict)] if isinstance(targets, list) else []
    record_items = [item for item in records if isinstance(item, dict)] if isinstance(records, list) else []
    required = [item for item in target_items if item.get("required") is True]
    covered = [
        item
        for item in required
        if isinstance(item.get("record_refs"), list) and bool(item.get("record_refs"))
    ]
    return {
        "source_count": len(payload.get("sources", [])) if isinstance(payload.get("sources"), list) else 0,
        "record_count": len(record_items),
        "required_targets": len(required),
        "covered_targets": len(covered),
    }


def render_source_truth_markdown(
    payload: dict[str, object],
    report: dict[str, object],
) -> str:
    project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
    lines = [
        "# 源材料分析与 Source Truth Map",
        "",
        "## 材料定位",
        "",
        f"- 项目：{_escape(project.get('title'))}",
        f"- 材料类型：{_escape(project.get('material_type'))}",
        f"- 汇报对象：{_escape(project.get('audience'))}",
        "",
        "## 源材料盘点",
        "",
        "| 来源ID | 文件 | 角色 | 非空段落 | 标题 | 表格 |",
        "|---|---|---|---:|---:|---:|",
    ]
    sources = payload.get("sources")
    for source in sources if isinstance(sources, list) else []:
        if not isinstance(source, dict):
            continue
        lines.append(
            "| {id} | {file} | {role} | {paragraphs} | {headings} | {tables} |".format(
                id=_escape(source.get("id")),
                file=_escape(source.get("file")),
                role=_escape(source.get("role")),
                paragraphs=_escape(source.get("non_empty_paragraphs")),
                headings=_escape(source.get("headings")),
                tables=_escape(source.get("tables")),
            )
        )
    lines.extend(
        [
            "",
            "## Source Truth Map",
            "",
            "| Source ID | 类型 | 优先级 | 状态 | 精确位置 | 准确表述 | 条件与边界 | 结论 | 页面 |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    records = payload.get("records")
    for record in records if isinstance(records, list) else []:
        if not isinstance(record, dict):
            continue
        lines.append(
            "| {id} | {type} | {priority} | {status} | {locator} | {statement} | {conditions} | {supports} | {pages} |".format(
                id=_escape(record.get("id")),
                type=_escape(record.get("type")),
                priority=_escape(record.get("priority")),
                status=_escape(record.get("status")),
                locator=_escape(_locator_text(record)),
                statement=_escape(record.get("statement")),
                conditions=_escape(record.get("conditions")),
                supports=_escape(record.get("supports")),
                pages=_escape(record.get("page_refs")),
            )
        )
    summary = report.get("coverage") if isinstance(report.get("coverage"), dict) else {}
    lines.extend(
        [
            "",
            "## 覆盖与审计结论",
            "",
            f"- 审计状态：`{_escape(report.get('status'))}`",
            f"- Source 记录：{_escape(summary.get('record_count'))}",
            f"- 必须覆盖目标：{_escape(summary.get('required_targets'))}",
            f"- 已建立映射：{_escape(summary.get('covered_targets'))}",
            f"- 审计问题数：{len(report.get('issues', [])) if isinstance(report.get('issues'), list) else 0}",
            "",
            "## 冲突、边界与待核事项",
            "",
        ]
    )
    boundary_records = [
        item
        for item in (records if isinstance(records, list) else [])
        if isinstance(item, dict) and item.get("type") in {"B", "U"}
    ]
    if boundary_records:
        for record in boundary_records:
            lines.append(f"- `{_escape(record.get('id'))}` {_escape(record.get('statement'))}")
    else:
        lines.append("- 无独立登记项。")
    lines.extend(["", "## 双向追溯", ""])
    conclusions = payload.get("conclusions")
    for conclusion in conclusions if isinstance(conclusions, list) else []:
        if isinstance(conclusion, dict):
            lines.append(
                f"- 结论 `{_escape(conclusion.get('id'))}` ← {_escape(conclusion.get('source_refs'))}："
                f"{_escape(conclusion.get('statement'))}"
            )
    pages = payload.get("pages")
    for page in pages if isinstance(pages, list) else []:
        if isinstance(page, dict):
            lines.append(f"- 页面 `{_escape(page.get('id'))}` ← {_escape(page.get('source_refs'))}")
    receipts = report.get("source_receipts")
    if isinstance(receipts, list):
        lines.extend(["", "## 源材料凭据", "", "| 来源ID | 文件 | 状态 | 字节数 | SHA-256 |", "|---|---|---|---:|---|"])
        for receipt in receipts:
            if not isinstance(receipt, dict):
                continue
            lines.append(
                "| {source_id} | {declared_file} | {status} | {bytes} | {sha256} |".format(
                    source_id=_escape(receipt.get("source_id")),
                    declared_file=_escape(receipt.get("declared_file")),
                    status=_escape(receipt.get("status")),
                    bytes=_escape(receipt.get("bytes")),
                    sha256=_escape(receipt.get("sha256")),
                )
            )
    return "\n".join(lines).rstrip() + "\n"


def _escalation_options() -> list[dict[str, str]]:
    return [
        {
            "id": "accept_documented_gaps",
            "label": "保留缺口继续规划",
            "action": "保留当前最佳证据底稿，并在后续成果中持续披露缺口。",
        },
        {
            "id": "targeted_manual_review",
            "label": "专项人工复核",
            "action": "按剩余问题代码复核原文段落、表格和引用。",
        },
        {
            "id": "request_missing_inputs",
            "label": "补充源材料",
            "action": "向项目组补充索取无法从现有材料核验的输入。",
        },
    ]


def run_source_truth_audit(
    project: Path,
    input_path: Path,
    max_attempts: int = 3,
) -> tuple[int, dict[str, object]]:
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 through 5")
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    payload = load_source_truth(input_path.expanduser().resolve())
    retry = payload.get("retry") if isinstance(payload.get("retry"), dict) else {}
    attempt = int(retry.get("attempt", 1))
    effective_max = int(retry.get("max_attempts", max_attempts))
    if not 1 <= effective_max <= 5:
        raise ValueError("retry.max_attempts must be between 1 through 5")
    receipt_roots = (project, project / "source", input_path.expanduser().resolve().parent)
    receipts = collect_source_receipts(payload, receipt_roots)
    issues = audit_source_truth(payload)
    issues.extend(
        audit_source_receipts(
            receipts,
            required=payload.get("source_receipt_policy") == "required",
            expected=payload.get("source_receipts"),
        )
    )
    directive = source_truth_retry_directive(issues, str(retry.get("strategy") or ""))
    report: dict[str, object] = {
        "schema": "cyberppt.source_truth_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "attempt": attempt,
        "max_attempts": effective_max,
        "remaining_attempts": max(0, effective_max - attempt),
        "coverage": _coverage_summary(payload),
        "issues": [issue.to_dict() for issue in issues],
        "retry_directive": directive,
        "reference_gate": snapshot_reference_gate("source_truth"),
        "source_receipts": receipts,
    }
    stage = project / "workbench" / "stages" / "01-analysis"
    _write_json(stage / "source-truth.json", payload)
    _write_json(stage / "source-truth-audit.json", report)
    _write_json(
        stage / "source-truth-attempts" / f"attempt-{attempt:02d}.json",
        {"source_truth": payload, "audit": report},
    )
    (stage / "00-source-analysis.md").write_text(
        render_source_truth_markdown(payload, report),
        encoding="utf-8",
    )
    if not issues:
        return 0, report
    if attempt < effective_max:
        return 4, report
    report["status"] = "user_decision_required"
    report["options"] = _escalation_options()
    _write_json(stage / "source-truth-audit.json", report)
    _write_json(stage / "source-truth-escalation.json", report)
    (stage / "00-source-analysis.md").write_text(
        render_source_truth_markdown(payload, report),
        encoding="utf-8",
    )
    return 5, report

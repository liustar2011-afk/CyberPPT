"""Stage 01 control-point helpers: reference gate, escalation decisions, confirmations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.communication_strategy import assert_communication_strategy_ready
from cyberppt.outline_contract import load_outline
from cyberppt.paths import REFERENCES_DIR
from cyberppt.script_quality_contract import parse_script_path
from cyberppt.semantic_understanding import assert_semantic_understanding_ready
from cyberppt.semantic_digest import (
    outline_semantic_digest,
    script_semantic_digest,
)

REFERENCE_GATE_FILES: dict[str, tuple[str, ...]] = {
    "source_truth": ("source-analysis.md",),
    "outline": ("source-analysis.md", "storyline.md"),
    "script": ("script-quality.md", "storyline.md"),
}

ESCALATION_FILES: dict[str, Path] = {
    "source_truth": Path("workbench/stages/01-analysis/source-truth-escalation.json"),
    "outline": Path("workbench/stages/01-analysis/outline-escalation.json"),
    "script": Path("workbench/scripts/audits/script-escalation.json"),
}

LATEST_AUDIT_FILES: dict[str, Path] = {
    "source_truth": Path("workbench/stages/01-analysis/source-truth-audit.json"),
    "outline": Path("workbench/stages/01-analysis/outline-audit.json"),
    "script": Path("workbench/scripts/audits/script-audit.json"),
}

CHAPTER_REVIEW_AUDIT_FILES: dict[str, Path] = {
    "outline": Path("workbench/stages/01-analysis/chapter-review-audit.json"),
    "script": Path("workbench/scripts/audits/chapter-review-audit.json"),
}

CONFIRMATION_REQUEST_FILES: dict[str, Path] = {
    "outline": Path("workbench/stages/01-analysis/stage01-confirmation-request.md"),
    "script": Path(
        "workbench/stages/01-analysis/stage01-script-confirmation-request.md"
    ),
}

APPROVAL_FILES: dict[str, Path] = {
    "outline": Path("workbench/approvals/stage01-outline-approved.md"),
    "script": Path("workbench/approvals/stage01-script-approved.md"),
}

SCRIPT_APPROVABLE_ESCALATION_OPTIONS = frozenset({"accept_documented_risk"})

# Accept both canonical and legacy Chinese headings used in existing projects.
_AUDIT_SUMMARY_HEADINGS = ("## 审计摘要", "## 审计状态")
_OPEN_QUESTIONS_HEADINGS = ("## 开放问题", "## 缺口与 caveat", "## 开放缺口")
_REPLY_HEADINGS = ("## 请回复",)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _semantic_or_raw(path: Path, semantic_fn: Any) -> str:
    """Return a semantic digest, with a narrow legacy fallback.

    Old approvals and a few external integrations may point at placeholder or
    pre-contract artifacts that cannot be parsed as current Stage 01 authority
    documents.  They remain raw-hash bound; valid current artifacts always use
    their semantic digest.
    """
    try:
        return semantic_fn(path)
    except (ValueError, json.JSONDecodeError):
        return _sha256_path(path)


def assert_stage01_script_approval(project: Path, script: Path) -> Path:
    project = project.expanduser().resolve()
    semantic_gate = assert_semantic_understanding_ready(project)
    communication_gate = assert_communication_strategy_ready(project)
    approval = project / APPROVAL_FILES["script"]
    if not approval.is_file():
        raise FileNotFoundError(f"missing Stage 01 script approval: {approval}")
    audit = _read_json(project / LATEST_AUDIT_FILES["script"])
    audited_semantic_gate = audit.get("semantic_gate")
    if semantic_gate is not None and (
        not isinstance(audited_semantic_gate, dict)
        or audited_semantic_gate.get("semantic_understanding_sha256")
        != semantic_gate.get("semantic_understanding_sha256")
        or audited_semantic_gate.get("source_bundle_sha256")
        != semantic_gate.get("source_bundle_sha256")
    ):
        raise ValueError(
            "Stage 01 script audit is stale relative to the current semantic understanding; "
            "rerun script-audit before Stage 02"
        )
    audited_communication_gate = audit.get("communication_strategy_gate")
    if communication_gate is not None and (
        not isinstance(audited_communication_gate, dict)
        or audited_communication_gate.get("communication_strategy_sha256")
        != communication_gate.get("communication_strategy_sha256")
        or audited_communication_gate.get("option_id")
        != communication_gate.get("option_id")
    ):
        raise ValueError(
            "Stage 01 script audit is stale relative to the approved communication strategy; "
            "rerun script-audit before Stage 02"
        )
    escalation_decision = _script_approval_escalation_decision(project, audit)
    if audit.get("status") != "passed" and escalation_decision is None:
        raise ValueError(
            "current Stage 01 script audit is neither passed nor covered by a valid "
            "accepted-risk escalation; rerun audit or resolve the escalation before Stage 02"
        )
    for artifact_key, label in (
        ("input", "script"),
        ("outline", "outline"),
        ("source_truth", "source truth"),
    ):
        artifact_value = audit.get(artifact_key)
        if not artifact_value:
            raise ValueError(f"Stage 01 script audit is missing its {label} path")
        artifact_path = Path(str(artifact_value)).expanduser().resolve()
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Stage 01 script audit artifact does not exist: {artifact_path}")
    return approval


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _script_approval_escalation_decision(
    project: Path, audit: dict[str, Any]
) -> tuple[Path, dict[str, Any]] | None:
    """Return a validated terminal script-risk decision, if one permits approval."""

    if audit.get("status") == "passed":
        return None
    if audit.get("status") != "user_decision_required":
        return None

    escalation_path = (project / ESCALATION_FILES["script"]).resolve()
    decision_path = escalation_decision_path(project, "script").resolve()
    if not escalation_path.is_file() or not decision_path.is_file():
        return None

    escalation = _read_json(escalation_path)
    decision = _read_json(decision_path)
    if decision.get("schema") != "cyberppt.escalation_decision.v1":
        return None
    if decision.get("gate") != "script":
        return None
    recorded_escalation = decision.get("escalation_path")
    if not recorded_escalation:
        return None
    if Path(str(recorded_escalation)).expanduser().resolve() != escalation_path:
        return None

    option_id = str(decision.get("option_id") or "")
    options = escalation.get("options")
    offered_option_ids = {
        str(item.get("id"))
        for item in options
        if isinstance(item, dict) and item.get("id")
    } if isinstance(options, list) else set()
    if option_id not in offered_option_ids:
        return None
    if option_id not in SCRIPT_APPROVABLE_ESCALATION_OPTIONS:
        return None
    return decision_path, decision


def snapshot_reference_gate(stage_key: str, project: Path | None = None) -> dict[str, Any]:
    """Record which Stage 01 reference files were present and their digests."""

    names = REFERENCE_GATE_FILES.get(stage_key)
    if not names:
        raise ValueError(
            f"unknown reference-gate stage: {stage_key!r}; "
            f"expected one of {sorted(REFERENCE_GATE_FILES)}"
        )
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    reference_dir = (
        project.expanduser().resolve() / "workbench" / "references"
        if project is not None
        else REFERENCES_DIR
    )
    for name in names:
        path = reference_dir / name
        if not path.is_file():
            missing.append(name)
            files.append(
                {
                    "name": name,
                    "path": str(path),
                    "present": False,
                }
            )
            continue
        raw = path.read_bytes()
        files.append(
            {
                "name": name,
                "path": str(path),
                "present": True,
                "bytes": len(raw),
                "sha256": _sha256_bytes(raw),
            }
        )
    return {
        "schema": "cyberppt.reference_gate.v1",
        "stage": stage_key,
        "scope": "project" if project is not None else "repository",
        "status": "complete" if not missing else "missing_references",
        "missing": missing,
        "files": files,
        "captured_at": _utc_now(),
    }


def escalation_decision_path(project: Path, gate: str) -> Path:
    if gate not in ESCALATION_FILES:
        raise ValueError(f"unknown escalation gate: {gate!r}")
    return (
        project.expanduser().resolve()
        / "workbench"
        / "approvals"
        / f"escalation-{gate.replace('_', '-')}-decided.json"
    )


def assert_escalation_resolved(project: Path, gate: str) -> None:
    """Block downstream work when exit-5 escalation exists without a decision."""

    if gate not in ESCALATION_FILES:
        raise ValueError(f"unknown escalation gate: {gate!r}")
    project = project.expanduser().resolve()
    escalation = project / ESCALATION_FILES[gate]
    if not escalation.is_file():
        return
    latest_path = project / LATEST_AUDIT_FILES[gate]
    if latest_path.is_file():
        latest = _read_json(latest_path)
        if latest.get("status") == "passed":
            return
    decision = escalation_decision_path(project, gate)
    if decision.is_file():
        return
    raise ValueError(
        f"open Stage 01 escalation for `{gate}` blocks this command. "
        f"Escalation: {escalation.as_posix()}. "
        f"Record a decision with: python -m cyberppt resolve-escalation "
        f"<project> --gate {gate} --option <option_id> "
        f"(see options in the escalation JSON)."
    )


def write_escalation_decision(
    project: Path,
    *,
    gate: str,
    option_id: str,
    note: str = "",
) -> Path:
    project = project.expanduser().resolve()
    if gate not in ESCALATION_FILES:
        raise ValueError(f"unknown escalation gate: {gate!r}")
    escalation = project / ESCALATION_FILES[gate]
    if not escalation.is_file():
        raise FileNotFoundError(f"no escalation file for gate `{gate}`: {escalation}")
    payload = _read_json(escalation)
    options = payload.get("options")
    option_ids = {
        str(item.get("id"))
        for item in options
        if isinstance(item, dict) and item.get("id")
    } if isinstance(options, list) else set()
    if option_ids and option_id not in option_ids:
        raise ValueError(
            f"option_id {option_id!r} is not in escalation options: "
            f"{sorted(option_ids)}"
        )
    decision = {
        "schema": "cyberppt.escalation_decision.v1",
        "gate": gate,
        "option_id": option_id,
        "note": note or "",
        "decided_at": _utc_now(),
        "escalation_path": str(escalation),
        "escalation_status": payload.get("status"),
    }
    path = escalation_decision_path(project, gate)
    _write_json(path, decision)
    return path


def _has_heading(text: str, headings: tuple[str, ...]) -> bool:
    normalized = text.replace("\r\n", "\n")
    return any(
        re.search(rf"^{re.escape(heading)}\s*$", normalized, flags=re.M)
        for heading in headings
    )


def validate_confirmation_request(text: str) -> list[str]:
    """Return missing required sections for a Stage 01 confirmation request."""

    missing: list[str] = []
    if not _has_heading(text, _AUDIT_SUMMARY_HEADINGS):
        missing.append("审计摘要（或 审计状态）")
    if not _has_heading(text, _OPEN_QUESTIONS_HEADINGS):
        missing.append("开放问题（或 缺口与 caveat / 开放缺口）")
    if not _has_heading(text, _REPLY_HEADINGS):
        missing.append("请回复")
    return missing


def _audit_line(project: Path, gate: str, label: str) -> str:
    path = project / LATEST_AUDIT_FILES[gate]
    if not path.is_file():
        return f"| `{label}` | missing |"
    report = _read_json(path)
    status = report.get("status", "unknown")
    issues = report.get("issues")
    issue_count = len(issues) if isinstance(issues, list) else 0
    attempt = report.get("attempt", "-")
    return (
        f"| `{label}` | **{status}** "
        f"（attempt {attempt}, issues {issue_count}） |"
    )


def _chapter_review_required(project: Path, kind: str) -> bool:
    manifest = project / "manifest.yml"
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8-sig")
    match = re.search(r"(?ms)^chapter_review:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)", text)
    if not match:
        return False
    return bool(re.search(rf"(?m)^\s+{re.escape(kind)}:\s*required\s*$", match.group("body")))


def _chapter_review_line(project: Path, kind: str) -> str:
    path = project / CHAPTER_REVIEW_AUDIT_FILES[kind]
    if not path.is_file():
        return "| `chapter-structure-review` | missing |"
    report = _read_json(path)
    return (
        f"| `chapter-structure-review` | **{report.get('status', 'unknown')}** "
        f"（pages {report.get('page_count', '-')}, issues {len(report.get('issues') or [])}） |"
    )


def _chapter_review_markdown_lines(project: Path, kind: str) -> list[str]:
    manifest_path = project / "review/chapter-review-manifest.json"
    if not manifest_path.is_file():
        return []
    manifest = _read_json(manifest_path)
    if manifest.get("level") != kind:
        return []
    lines: list[str] = []
    for entry in manifest.get("reviews", []):
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        chapter_ids = [str(value) for value in entry.get("chapter_ids", [])]
        chapter_label = "、".join(
            f"第{int(match.group(1))}章" if (match := re.search(r"(\d+)", value)) else value
            for value in chapter_ids
        )
        review_path = project / str(entry["path"])
        lines.append(f"- {chapter_label}：`{review_path.as_posix()}`")
    return lines


def _truncate(text: str, limit: int = 160) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _outline_deliverable_lines(project: Path) -> list[str]:
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    if not outline_path.is_file():
        return []
    try:
        outline = load_outline(outline_path)
    except ValueError:
        return []
    pages = [page for page in outline.get("pages", []) if isinstance(page, dict)]
    if not pages:
        return []
    lines: list[str] = []
    current_chapter: str | None = None
    for page in sorted(pages, key=lambda item: item.get("sequence", 0)):
        chapter_id = str(page.get("chapter_id") or "")
        if chapter_id and chapter_id != current_chapter:
            current_chapter = chapter_id
            lines.append(f"**{chapter_id}**")
        page_id = str(page.get("page_id") or "")
        title = str(page.get("title") or "")
        core_message = _truncate(page.get("core_message") or page.get("subtitle") or "")
        if core_message:
            lines.append(f"- `{page_id}` {title} — {core_message}")
        else:
            lines.append(f"- `{page_id}` {title}")
    return lines


def _script_deliverable_lines(project: Path) -> list[str]:
    script_path = project / "workbench" / "scripts" / "final" / "script-final.md"
    if not script_path.is_file():
        return []
    try:
        document = parse_script_path(script_path)
    except (ValueError, OSError):
        return []
    lines: list[str] = []
    for page in sorted(document.pages, key=lambda item: item.sequence):
        if page.page_type != "content":
            continue
        judgment = _truncate(page.core_message or page.onscreen_judgment or "")
        lines.append(f"**`{page.page_id}` {page.title}**")
        if judgment:
            lines.append(f"- 主判断：{judgment}")
        onscreen_lines = [line for line in page.onscreen_text.splitlines() if line.strip()]
        if onscreen_lines:
            # A single flattened line (joining all whitespace, including the
            # newlines that carry the bullet hierarchy) reads as an
            # unreadable run-on and hides exactly the parent/child structure
            # this project spent a session fixing — render as a fenced block
            # so indentation and line breaks survive verbatim for the human
            # reviewer, capped by line count rather than character count.
            preview_lines = onscreen_lines[:14]
            lines.append("- 上屏文字预览：")
            lines.append("  ```text")
            lines.extend(f"  {line}" for line in preview_lines)
            if len(onscreen_lines) > len(preview_lines):
                lines.append(f"  …（还有 {len(onscreen_lines) - len(preview_lines)} 行，完整内容见 script-final.md）")
            lines.append("  ```")
        lines.append("")
    return lines


def assert_chapter_review_ready(project: Path, kind: str) -> Path | None:
    project = project.expanduser().resolve()
    if not _chapter_review_required(project, kind):
        return None
    path = project / CHAPTER_REVIEW_AUDIT_FILES[kind]
    if not path.is_file():
        raise FileNotFoundError(
            f"required chapter structure review audit is missing: {path}. "
            f"Run prepare-chapter-review and chapter-review-audit --level {kind}."
        )
    report = _read_json(path)
    if report.get("status") != "passed":
        raise ValueError(f"required chapter structure review is not passed: {path}")
    input_path = Path(str(report.get("input") or "")).expanduser().resolve()
    expected_semantic = str(report.get("input_semantic_sha256") or "")
    semantic_digest = (
        outline_semantic_digest(input_path)
        if kind == "outline"
        else script_semantic_digest(input_path)
    ) if expected_semantic and input_path.is_file() else ""
    matches = (
        expected_semantic == semantic_digest
        if expected_semantic
        else report.get("input_sha256") == _sha256_path(input_path)
        if input_path.is_file()
        else False
    )
    if not input_path.is_file() or not matches:
        raise ValueError("chapter structure review is stale; rerun preparation, review, and audit")
    return path


def _open_questions_from_audits(project: Path, kind: str) -> list[str]:
    questions: list[str] = []
    gates = ("source_truth", "outline") if kind == "outline" else ("script",)
    for gate in gates:
        path = project / LATEST_AUDIT_FILES[gate]
        if not path.is_file():
            questions.append(f"{gate} 审计文件缺失，需先完成审计。")
            continue
        report = _read_json(path)
        if report.get("status") == "user_decision_required":
            questions.append(
                f"{gate} 已升级为用户决策（exit 5），须先 "
                f"`resolve-escalation --gate {gate}`。"
            )
        issues = report.get("issues")
        if isinstance(issues, list):
            for issue in issues[:8]:
                if not isinstance(issue, dict):
                    continue
                code = issue.get("code") or "ISSUE"
                message = issue.get("message") or ""
                questions.append(f"{code}: {message}")
        options = report.get("options")
        if isinstance(options, list):
            for option in options:
                if isinstance(option, dict) and option.get("label"):
                    questions.append(f"待决选项：{option.get('label')}")
        communication = report.get("communication_review")
        if isinstance(communication, dict):
            content_pages = int(communication.get("content_pages") or 0)
            mission_coverage = int(communication.get("mission_coverage") or 0)
            lead_coverage_count = int(
                communication.get("lead_coverage_count")
                or communication.get("lead_match_count")
                or 0
            )
            warning_count = int(communication.get("warning_count") or 0)
            density_low_count = int(
                communication.get("reading_density_low_count") or 0
            )
            if mission_coverage < content_pages:
                questions.append(
                    f"上屏文字审阅：页面使命覆盖 {mission_coverage}/{content_pages}，需补齐 Outline business_question。"
                )
            if lead_coverage_count < content_pages and any(
                isinstance(page, dict)
                and (page.get("onscreen_conclusion") or page.get("onscreen_judgment"))
                for page in communication.get("pages", [])
            ):
                questions.append(
                    "上屏文字审阅：存在已批准的上屏结论尚未忠实呈现；仅修复这些页面，不给其他页面补写结论。"
                )
            if density_low_count:
                questions.append(
                    f"上屏文字审阅：有 {density_low_count} 页低于阅读型高密度基线；补回源材料事实与关系，不以机械补写结论或重复字句刷密度。"
                )
            if warning_count:
                questions.append(
                    f"上屏文字审阅：有 {warning_count} 条自动提醒；模块同维度、信息取舍等仍需人工复核。"
                )
    if not questions:
        questions.append("无未关闭审计问题；请确认架构/页数/边界是否仍符合业务意图。")
    # de-dupe while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for item in questions:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique[:12]


def render_confirmation_request(project: Path, kind: str) -> str:
    if kind not in CONFIRMATION_REQUEST_FILES:
        raise ValueError(f"unknown confirmation kind: {kind!r}")
    project = project.expanduser().resolve()
    title = "大纲确认请求" if kind == "outline" else "脚本确认请求"
    lines = [
        f"# Stage 01 {title}",
        "",
        f"> 项目：`{project.as_posix()}`",
        f"> 生成时间：{_utc_now()}",
        "> 本文件由 `cyberppt confirmation-request` 生成；批准前必须含审计摘要、开放问题与请回复。",
        "",
        "## 审计摘要",
        "",
        "| 门禁 | 结果 |",
        "|---|---|",
    ]
    if kind == "outline":
        lines.append(_audit_line(project, "source_truth", "source-truth-audit"))
        lines.append(_audit_line(project, "outline", "outline-audit"))
        lines.append(_chapter_review_line(project, "outline"))
        lines.append("| 脚本 | 未开始（须大纲批准后编写） |")
        readable = (
            project
            / "workbench"
            / "stages"
            / "01-analysis"
            / "01-outline-readable.md"
        )
        lines.extend(
            [
                "",
                "## 人类审阅稿",
                "",
                f"- **总提纲**：`{readable.as_posix()}`",
                "- `outline.json` 仅供机器审计，不作为人工确认稿。",
            ]
        )
        chapter_reviews = _chapter_review_markdown_lines(project, "outline")
        if chapter_reviews:
            lines.extend([
                "",
                "### 分章审阅稿",
                "",
                "> 建议按章节逐一审阅；每章可单独提出保留、修改或通过意见。",
                "",
                *chapter_reviews,
            ])
        outline_deliverable = _outline_deliverable_lines(project)
        if outline_deliverable:
            lines.extend(
                [
                    "",
                    "## 成果物内容（逐页大纲）",
                    "",
                    "> 以下为 `outline.json` 的实际页面内容摘要，供直接审阅，无需另行打开文件。",
                    "",
                    *outline_deliverable,
                ]
            )
    else:
        lines.append(_audit_line(project, "source_truth", "source-truth-audit"))
        lines.append(_audit_line(project, "outline", "outline-audit"))
        lines.append(_audit_line(project, "script", "script-audit"))
        lines.append(_chapter_review_line(project, "script"))
        script_path = (
            project / "workbench" / "scripts" / "final" / "script-final.md"
        )
        lines.extend(
            [
                "",
                "## 人类审阅稿",
                "",
                f"- **完整讲稿**：`{script_path.as_posix()}`",
            ]
        )
        chapter_reviews = _chapter_review_markdown_lines(project, "script")
        if chapter_reviews:
            lines.extend([
                "",
                "### 分章审阅稿",
                "",
                "> 建议按章节逐一审阅；每章可单独提出保留、修改或通过意见。",
                "",
                *chapter_reviews,
            ])
        script_deliverable = _script_deliverable_lines(project)
        if script_deliverable:
            lines.extend(
                [
                    "",
                    "## 成果物内容（逐页讲稿）",
                    "",
                    "> 以下为 `script-final.md` 的实际页面主判断与上屏文字预览，供直接审阅，无需另行打开文件。",
                    "",
                    *script_deliverable,
                ]
            )
    lines.extend(["", "## 开放问题", ""])
    for index, question in enumerate(_open_questions_from_audits(project, kind), start=1):
        lines.append(f"{index}. {question}")
    if kind == "outline":
        lines.extend(
            [
                "",
                "## 请回复",
                "",
                "1. **批准大纲** → `python -m cyberppt approve-stage01 <project> --kind outline`",
                "2. **修改后重跑** → 说明要改的页数/章节/边界后重做 outline-audit",
                "3. **升级决策** → 若审计为 user_decision_required，先 resolve-escalation",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## 请回复",
                "",
                "1. **批准脚本** → `python -m cyberppt approve-stage01 <project> --kind script`",
                "2. **修改后重跑** → 按 retry_scope 改写后重做 script-audit",
                "3. **升级决策** → 若审计为 user_decision_required，先 resolve-escalation",
                "",
            ]
        )
    return "\n".join(lines)


def write_confirmation_request(project: Path, kind: str) -> Path:
    project = project.expanduser().resolve()
    text = render_confirmation_request(project, kind)
    missing = validate_confirmation_request(text)
    if missing:
        raise RuntimeError(
            f"generated confirmation request missing sections: {missing}"
        )
    path = project / CONFIRMATION_REQUEST_FILES[kind]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def assert_confirmation_request_ready(project: Path, kind: str) -> Path:
    project = project.expanduser().resolve()
    path = project / CONFIRMATION_REQUEST_FILES[kind]
    if not path.is_file():
        raise FileNotFoundError(
            f"missing confirmation request: {path}. "
            f"Generate with: python -m cyberppt confirmation-request "
            f"<project> --kind {kind}"
        )
    missing = validate_confirmation_request(path.read_text(encoding="utf-8-sig"))
    if missing:
        raise ValueError(
            f"confirmation request incomplete at {path}: missing {missing}. "
            "Regenerate with confirmation-request or add the required headings."
        )
    return path


def write_stage01_approval(
    project: Path,
    *,
    kind: str,
    note: str = "",
) -> Path:
    project = project.expanduser().resolve()
    semantic_gate = assert_semantic_understanding_ready(project)
    communication_gate = assert_communication_strategy_ready(project)
    if kind not in APPROVAL_FILES:
        raise ValueError(f"unknown approval kind: {kind!r}")
    current_audit = _read_json(project / LATEST_AUDIT_FILES[kind])
    audited_communication_gate = current_audit.get("communication_strategy_gate")
    if communication_gate is not None and (
        not isinstance(audited_communication_gate, dict)
        or audited_communication_gate.get("communication_strategy_sha256")
        != communication_gate.get("communication_strategy_sha256")
        or audited_communication_gate.get("option_id")
        != communication_gate.get("option_id")
    ):
        raise ValueError(
            f"{kind} audit is stale relative to the approved communication strategy; rerun {kind}-audit"
        )
    request_path = assert_confirmation_request_ready(project, kind)
    # Chapter-structure review is an optional editorial diagnostic. The
    # mechanical audit plus affirmative human approval remain the authoritative
    # Stage 01 production gates, so a missing or stale chapter review must not
    # block confirmation or approval.
    chapter_review_audit = None
    if kind == "outline":
        assert_escalation_resolved(project, "source_truth")
        assert_escalation_resolved(project, "outline")
        if current_audit.get("status") != "passed":
            raise ValueError(
                "outline approval requires a passed mechanical outline-audit; "
                "fix its blocking issues and rerun outline-audit"
            )
    else:
        assert_escalation_resolved(project, "script")
        outline_approval = project / APPROVAL_FILES["outline"]
        if not outline_approval.is_file():
            raise FileNotFoundError(
                f"script approval requires outline approval first: {outline_approval}"
            )
        audit = current_audit
        audited_semantic_gate = audit.get("semantic_gate")
        if semantic_gate is not None and (
            not isinstance(audited_semantic_gate, dict)
            or audited_semantic_gate.get("semantic_understanding_sha256")
            != semantic_gate.get("semantic_understanding_sha256")
            or audited_semantic_gate.get("source_bundle_sha256")
            != semantic_gate.get("source_bundle_sha256")
        ):
            raise ValueError(
                "script audit is stale relative to the current semantic understanding; rerun script-audit"
            )
        escalation_decision = _script_approval_escalation_decision(project, audit)
        if audit.get("status") != "passed" and escalation_decision is None:
            raise ValueError(
                "script approval requires a passed script audit or a valid "
                f"accepted-risk escalation decision (audit status: {audit.get('status')!r}); "
                "fix blocking mechanical issues and rerun script-audit"
            )
        script_path = Path(str(audit["input"])).expanduser().resolve()
    path = project / APPROVAL_FILES[kind]
    path.parent.mkdir(parents=True, exist_ok=True)
    label = "Outline" if kind == "outline" else "Script"
    body = "\n".join(
        [
            f"# Stage 01 {label} Approval",
            "",
            f"- project: {project.name}",
            f"- approved_at: {_utc_now()}",
            f"- decision: approve_{kind}",
            f"- confirmation_request: {request_path.as_posix()}",
            f"- notes: {note or 'User approved Stage 01 ' + kind + '.'}",
            *([
                f"- script: {script_path}",
                f"- script_audit_status: {audit.get('status', 'unknown')}",
                *([
                    f"- escalation_decision: {escalation_decision[0]}",
                    f"- escalation_option_id: {escalation_decision[1].get('option_id')}",
                ] if escalation_decision is not None else []),
            ] if kind == "script" else []),
            *([
                f"- chapter_review_audit: {chapter_review_audit}",
            ] if chapter_review_audit else []),
            (
                "- next: draft scripts by chapter batches and run script-audit"
                if kind == "outline"
                else "- next: Stage 02 style / ImageGen / template assembly"
            ),
            "",
        ]
    )
    path.write_text(body, encoding="utf-8")
    return path

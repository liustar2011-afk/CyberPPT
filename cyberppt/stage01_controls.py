"""Stage 01 control-point helpers: reference gate, escalation decisions, confirmations."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.paths import REFERENCES_DIR

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


def _approval_fields(path: Path) -> dict[str, str]:
    return {
        key.strip(): value.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.startswith("- ") and ":" in line
        for key, value in [line[2:].split(":", 1)]
    }


def assert_stage01_script_approval(project: Path, script: Path) -> Path:
    project = project.expanduser().resolve()
    approval = project / APPROVAL_FILES["script"]
    if not approval.is_file():
        raise FileNotFoundError(f"missing Stage 01 script approval: {approval}")
    fields = _approval_fields(approval)
    audit = _read_json(project / LATEST_AUDIT_FILES["script"])
    if audit.get("status") != "passed":
        raise ValueError("current Stage 01 script audit is not passed; rerun audit before Stage 02")
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
        expected = fields.get(f"{label.replace(' ', '_')}_sha256")
        if not expected:
            raise ValueError(
                "Stage 01 script approval is not hash-bound; reapprove the current final script and its inputs"
            )
        if expected != _sha256_path(artifact_path):
            raise ValueError(
                f"Stage 01 script approval does not match the current {label}; "
                "rerun Stage 01 audit and reapprove before Stage 02"
            )
    current_script = script.expanduser().resolve()
    if fields.get("script") and Path(fields["script"]).expanduser().resolve() != current_script:
        raise ValueError("Stage 01 script approval points to a different final script")
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


def snapshot_reference_gate(stage_key: str) -> dict[str, Any]:
    """Record which Stage 01 reference files were present and their digests."""

    names = REFERENCE_GATE_FILES.get(stage_key)
    if not names:
        raise ValueError(
            f"unknown reference-gate stage: {stage_key!r}; "
            f"expected one of {sorted(REFERENCE_GATE_FILES)}"
        )
    files: list[dict[str, Any]] = []
    missing: list[str] = []
    for name in names:
        path = REFERENCES_DIR / name
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
        lines.append("| 脚本 | 未开始（须大纲批准后编写） |")
    else:
        lines.append(_audit_line(project, "source_truth", "source-truth-audit"))
        lines.append(_audit_line(project, "outline", "outline-audit"))
        lines.append(_audit_line(project, "script", "script-audit"))
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
    if kind not in APPROVAL_FILES:
        raise ValueError(f"unknown approval kind: {kind!r}")
    request_path = assert_confirmation_request_ready(project, kind)
    if kind == "outline":
        assert_escalation_resolved(project, "source_truth")
        assert_escalation_resolved(project, "outline")
    else:
        assert_escalation_resolved(project, "script")
        outline_approval = project / APPROVAL_FILES["outline"]
        if not outline_approval.is_file():
            raise FileNotFoundError(
                f"script approval requires outline approval first: {outline_approval}"
            )
        audit = _read_json(project / LATEST_AUDIT_FILES["script"])
        if audit.get("status") != "passed":
            raise ValueError("script approval requires a passed script audit")
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
                f"- script_sha256: {_sha256_path(script_path)}",
                f"- outline_sha256: {_sha256_path(Path(str(audit['outline'])).expanduser().resolve())}",
                f"- source_truth_sha256: {_sha256_path(Path(str(audit['source_truth'])).expanduser().resolve())}",
            ] if kind == "script" else []),
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

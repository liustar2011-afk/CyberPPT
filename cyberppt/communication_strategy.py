"""Human-approved communication strategy gate before outline authoring."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.semantic_understanding import (
    SEMANTIC_ARTIFACT,
    assert_semantic_understanding_ready,
)


COMMUNICATION_STAGE = Path("workbench/stages/00-communication-strategy")
COMMUNICATION_ARTIFACT = COMMUNICATION_STAGE / "communication-strategy.json"
COMMUNICATION_INPUT = COMMUNICATION_STAGE / "communication-strategy-input.md"
COMMUNICATION_INPUT_JSON = COMMUNICATION_STAGE / "communication-strategy-input.json"
COMMUNICATION_AUDIT = COMMUNICATION_STAGE / "communication-strategy-audit.json"
COMMUNICATION_AUDIT_MD = COMMUNICATION_STAGE / "communication-strategy-audit.md"
COMMUNICATION_CONFIRMATION = COMMUNICATION_STAGE / "communication-strategy-confirmation.md"
COMMUNICATION_APPROVAL = Path("workbench/approvals/communication-strategy-approved.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def communication_strategy_required(project: Path) -> bool:
    manifest = project.expanduser().resolve() / "manifest.yml"
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8-sig")
    match = re.search(r"(?ms)^gates:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)", text)
    if not match:
        return False
    return bool(
        re.search(
            r"(?m)^\s+communication_strategy:\s*required\s*$",
            match.group("body"),
        )
    )


def _candidate_template(semantic_gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "cyberppt.communication_strategy.v1",
        "semantic_understanding_sha256": semantic_gate["semantic_understanding_sha256"],
        "semantic_source_bundle_sha256": semantic_gate["source_bundle_sha256"],
        "audience": "",
        "communication_purpose": "",
        "decision_task": "",
        "content_focus": [],
        "options": [
            {
                "id": "",
                "label": "",
                "architecture_mode": "solution",
                "structure_principle": "",
            },
            {
                "id": "",
                "label": "",
                "architecture_mode": "solution",
                "structure_principle": "",
            },
        ],
        "recommendation": "",
    }


def _render_authoring_input(
    project: Path,
    semantic_gate: dict[str, Any],
) -> str:
    semantic_text = (project / SEMANTIC_ARTIFACT).read_text(encoding="utf-8-sig")
    return "\n".join(
        [
            "# Communication strategy authoring input",
            "",
            "This gate runs after approved whole-document semantic understanding and before Outline authoring.",
            "Determine who the deck communicates with, what that audience must decide or do, and how the chapter order should change for that audience.",
            "Do not create pages or an outline here. Do not replace source meaning with a generic consulting storyline.",
            "",
            "Write `communication-strategy.json` with schema `cyberppt.communication_strategy.v1`.",
            "Copy both semantic hashes below exactly. Supply a concrete audience, communication purpose, decision task, and 1-5 content-focus items.",
            "Supply 2-3 materially different reporting-direction options. Each option needs `id`, `label`, `architecture_mode` (`solution` or `consulting`), and a concrete `structure_principle` describing chapter logic and order.",
            "The options may share an architecture mode, but their structure principles must differ. Set `recommendation` to one option id.",
            "If the audience cannot be established from the source, describe the most likely audience but make the ambiguity explicit in the option labels; the human confirmation step remains mandatory.",
            "",
            "## Required binding",
            "",
            f"- semantic_understanding_sha256: {semantic_gate['semantic_understanding_sha256']}",
            f"- semantic_source_bundle_sha256: {semantic_gate['source_bundle_sha256']}",
            "",
            "## Approved semantic understanding",
            "",
            semantic_text.rstrip(),
            "",
        ]
    )


def prepare_communication_strategy(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    semantic_gate = assert_semantic_understanding_ready(project)
    if semantic_gate is None:
        raise ValueError("communication strategy requires the semantic-understanding gate")
    stage = project / COMMUNICATION_STAGE
    stage.mkdir(parents=True, exist_ok=True)
    model_input = project / COMMUNICATION_INPUT
    model_input.write_text(
        _render_authoring_input(project, semantic_gate),
        encoding="utf-8",
    )
    artifact = project / COMMUNICATION_ARTIFACT
    if not artifact.exists():
        artifact.write_text(
            json.dumps(_candidate_template(semantic_gate), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    payload = {
        "schema": "cyberppt.communication_strategy_input.v1",
        "model_input": str(model_input),
        "model_input_sha256": _sha256_path(model_input),
        "output": str(artifact),
        "semantic_understanding_sha256": semantic_gate["semantic_understanding_sha256"],
        "semantic_source_bundle_sha256": semantic_gate["source_bundle_sha256"],
        "prepared_at": _utc_now(),
    }
    (project / COMMUNICATION_INPUT_JSON).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return payload


def _load_candidate(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid communication strategy JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("communication strategy root must be an object")
    return payload


def _text(value: object) -> str:
    return str(value or "").strip()


def _audit_issues(payload: dict[str, Any], semantic_gate: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if payload.get("schema") != "cyberppt.communication_strategy.v1":
        issues.append({"code": "COMMUNICATION_SCHEMA_INVALID", "message": "schema must be cyberppt.communication_strategy.v1"})
    for field in ("audience", "communication_purpose", "decision_task"):
        if not _text(payload.get(field)):
            issues.append({"code": f"{field.upper()}_MISSING", "message": f"{field} must be concrete and non-empty"})
    focus = payload.get("content_focus")
    if not isinstance(focus, list) or not 1 <= len([item for item in focus if _text(item)]) <= 5:
        issues.append({"code": "CONTENT_FOCUS_INVALID", "message": "content_focus must contain 1-5 non-empty items"})
    for field, expected in (
        ("semantic_understanding_sha256", semantic_gate["semantic_understanding_sha256"]),
        ("semantic_source_bundle_sha256", semantic_gate["source_bundle_sha256"]),
    ):
        if _text(payload.get(field)).casefold() != _text(expected).casefold():
            issues.append({"code": "COMMUNICATION_SEMANTIC_BINDING_STALE", "message": f"{field} must match the approved semantic gate"})
    options = payload.get("options")
    valid_options = options if isinstance(options, list) else []
    if not 2 <= len(valid_options) <= 3 or any(not isinstance(item, dict) for item in valid_options):
        issues.append({"code": "COMMUNICATION_OPTIONS_INVALID", "message": "options must contain 2-3 objects"})
        return issues
    ids: list[str] = []
    principles: list[str] = []
    for index, option in enumerate(valid_options, 1):
        option_id = _text(option.get("id"))
        label = _text(option.get("label"))
        mode = _text(option.get("architecture_mode"))
        principle = _text(option.get("structure_principle"))
        if not option_id or not label or not principle or mode not in {"solution", "consulting"}:
            issues.append({"code": "COMMUNICATION_OPTION_INCOMPLETE", "message": f"option {index} requires id, label, valid architecture_mode, and structure_principle"})
        ids.append(option_id)
        principles.append(re.sub(r"\s+", "", principle).casefold())
    if len(set(ids)) != len(ids) or "" in ids:
        issues.append({"code": "COMMUNICATION_OPTION_IDS_INVALID", "message": "option ids must be non-empty and unique"})
    if len(set(principles)) != len(principles) or "" in principles:
        issues.append({"code": "COMMUNICATION_OPTIONS_NOT_DISTINCT", "message": "reporting directions must use materially different structure principles"})
    if _text(payload.get("recommendation")) not in ids:
        issues.append({"code": "COMMUNICATION_RECOMMENDATION_INVALID", "message": "recommendation must match one option id"})
    return issues


def run_communication_strategy_audit(project: Path) -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    semantic_gate = assert_semantic_understanding_ready(project)
    if semantic_gate is None:
        raise ValueError("communication strategy requires the semantic-understanding gate")
    artifact = project / COMMUNICATION_ARTIFACT
    if not artifact.is_file():
        raise FileNotFoundError(
            f"communication strategy does not exist: {artifact}; run prepare-communication-strategy"
        )
    payload = _load_candidate(artifact)
    issues = _audit_issues(payload, semantic_gate)
    report = {
        "schema": "cyberppt.communication_strategy_audit.v1",
        "status": "rewrite_required" if issues else "confirmation_required",
        "artifact": str(artifact),
        "communication_strategy_sha256": _sha256_path(artifact),
        "semantic_understanding_sha256": semantic_gate["semantic_understanding_sha256"],
        "semantic_source_bundle_sha256": semantic_gate["source_bundle_sha256"],
        "issues": issues,
        "audited_at": _utc_now(),
    }
    audit_path = project / COMMUNICATION_AUDIT
    audit_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# 沟通策略检查",
        "",
        f"- 状态：**{report['status']}**",
        f"- 沟通对象：{_text(payload.get('audience')) or '待补充'}",
        f"- 沟通目的：{_text(payload.get('communication_purpose')) or '待补充'}",
        f"- 决策任务：{_text(payload.get('decision_task')) or '待补充'}",
        "",
        "## 问题",
        "",
    ]
    lines += ([f"- `{item['code']}`：{item['message']}" for item in issues] or ["- 无。必须由用户选择汇报方向后，才能形成提纲。"])
    (project / COMMUNICATION_AUDIT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    confirmation = project / COMMUNICATION_CONFIRMATION
    if not issues:
        option_lines = []
        for option in payload["options"]:
            recommended = "（推荐）" if option["id"] == payload["recommendation"] else ""
            option_lines += [
                f"### {option['label']}{recommended}",
                "",
                f"- option_id: `{option['id']}`",
                f"- 结构模式：{option['architecture_mode']}",
                f"- 章节组织：{option['structure_principle']}",
                "",
            ]
        confirmation.write_text(
            "\n".join(
                [
                    "# 提纲生成前：沟通策略确认",
                    "",
                    "## 请确认这套材料主要与谁沟通？",
                    "",
                    f"当前识别：**{payload['audience']}**",
                    "",
                    "## 沟通目的与决策任务",
                    "",
                    f"- 沟通目的：{payload['communication_purpose']}",
                    f"- 决策任务：{payload['decision_task']}",
                    "",
                    "## 请选择汇报方向",
                    "",
                    *option_lines,
                    "确认命令：`python -m cyberppt approve-communication-strategy <project> --option <option_id>`",
                    "",
                    "未经选择和审批，不得生成提纲。",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    elif confirmation.exists():
        confirmation.unlink()
    return (4 if issues else 0), report


def approve_communication_strategy(project: Path, option_id: str, note: str = "") -> Path:
    project = project.expanduser().resolve()
    semantic_gate = assert_semantic_understanding_ready(project)
    if semantic_gate is None:
        raise ValueError("communication strategy requires the semantic-understanding gate")
    audit_path = project / COMMUNICATION_AUDIT
    artifact = project / COMMUNICATION_ARTIFACT
    if not audit_path.is_file():
        raise FileNotFoundError("communication strategy audit is missing; run communication-strategy-check")
    audit = _load_candidate(audit_path)
    if audit.get("status") != "confirmation_required":
        raise ValueError("communication strategy must pass its audit before approval")
    if audit.get("communication_strategy_sha256") != _sha256_path(artifact):
        raise ValueError("communication strategy audit is stale; rerun communication-strategy-check")
    payload = _load_candidate(artifact)
    options = {str(item.get("id")): item for item in payload.get("options", []) if isinstance(item, dict)}
    if option_id not in options:
        raise ValueError(f"unknown communication strategy option: {option_id}")
    selected = options[option_id]
    approval = {
        "schema": "cyberppt.communication_strategy_approval.v1",
        "decision": "approved",
        "option_id": option_id,
        "selected_option": selected,
        "audience": payload["audience"],
        "communication_purpose": payload["communication_purpose"],
        "decision_task": payload["decision_task"],
        "content_focus": payload["content_focus"],
        "communication_strategy_sha256": _sha256_path(artifact),
        "communication_audit_sha256": _sha256_path(audit_path),
        "semantic_understanding_sha256": semantic_gate["semantic_understanding_sha256"],
        "semantic_source_bundle_sha256": semantic_gate["source_bundle_sha256"],
        "approved_at": _utc_now(),
        "note": note.strip(),
    }
    output = project / COMMUNICATION_APPROVAL
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(approval, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def assert_communication_strategy_ready(project: Path) -> dict[str, Any] | None:
    project = project.expanduser().resolve()
    if not communication_strategy_required(project):
        return None
    semantic_gate = assert_semantic_understanding_ready(project)
    artifact = project / COMMUNICATION_ARTIFACT
    audit_path = project / COMMUNICATION_AUDIT
    approval_path = project / COMMUNICATION_APPROVAL
    if not artifact.is_file():
        raise FileNotFoundError(
            "required communication-strategy gate is missing. Run: "
            f"python -m cyberppt prepare-communication-strategy {project}"
        )
    if not audit_path.is_file():
        raise FileNotFoundError(
            "communication strategy has not been checked. Complete communication-strategy.json and run: "
            f"python -m cyberppt communication-strategy-check {project}"
        )
    audit = _load_candidate(audit_path)
    if audit.get("status") != "confirmation_required" or audit.get("communication_strategy_sha256") != _sha256_path(artifact):
        raise ValueError("communication-strategy gate is not passed or is stale; rerun communication-strategy-check")
    if not approval_path.is_file():
        raise FileNotFoundError(
            "communication strategy is awaiting user choice. Review communication-strategy-confirmation.md and run: "
            f"python -m cyberppt approve-communication-strategy {project} --option <option_id>"
        )
    approval = _load_candidate(approval_path)
    expectations = (
        ("communication_strategy_sha256", _sha256_path(artifact)),
        ("communication_audit_sha256", _sha256_path(audit_path)),
        ("semantic_understanding_sha256", semantic_gate["semantic_understanding_sha256"] if semantic_gate else ""),
        ("semantic_source_bundle_sha256", semantic_gate["source_bundle_sha256"] if semantic_gate else ""),
    )
    if approval.get("decision") != "approved" or any(
        _text(approval.get(field)).casefold() != _text(expected).casefold()
        for field, expected in expectations
    ):
        raise ValueError("communication-strategy approval is stale; recheck and reapprove")
    approval["communication_strategy_approval_sha256"] = _sha256_path(approval_path)
    approval["communication_strategy_path"] = str(artifact)
    approval["communication_strategy_approval_path"] = str(approval_path)
    return approval


def communication_strategy_binding_issues(
    outline: dict[str, Any], gate: dict[str, Any] | None
) -> list[dict[str, str]]:
    if gate is None:
        return []
    selected = gate.get("selected_option") if isinstance(gate.get("selected_option"), dict) else {}
    expected = {
        "communication_strategy_sha256": gate.get("communication_strategy_sha256"),
        "communication_strategy_approval_sha256": gate.get("communication_strategy_approval_sha256"),
        "audience": gate.get("audience"),
        "communication_purpose": gate.get("communication_purpose"),
        "decision_task": gate.get("decision_task"),
        "reporting_direction": gate.get("option_id"),
        "architecture_mode": selected.get("architecture_mode"),
        "structure_principle": selected.get("structure_principle"),
    }
    issues: list[dict[str, str]] = []
    for field, value in expected.items():
        if _text(outline.get(field)) != _text(value):
            issues.append(
                {
                    "code": "COMMUNICATION_STRATEGY_NOT_BOUND",
                    "message": f"Outline field {field} must equal the approved communication strategy.",
                    "retry_strategy": "rebuild_from_approved_communication_strategy",
                }
            )
    return issues

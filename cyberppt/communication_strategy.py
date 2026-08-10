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
from cyberppt.user_decisions import record_user_decision
from cyberppt.user_decisions import load_user_decisions


COMMUNICATION_STAGE = Path("workbench/stages/00-communication-strategy")
COMMUNICATION_ARTIFACT = COMMUNICATION_STAGE / "communication-strategy.json"
COMMUNICATION_INPUT = COMMUNICATION_STAGE / "communication-strategy-input.md"
COMMUNICATION_INPUT_JSON = COMMUNICATION_STAGE / "communication-strategy-input.json"
COMMUNICATION_AUDIT = COMMUNICATION_STAGE / "communication-strategy-audit.json"
COMMUNICATION_AUDIT_MD = COMMUNICATION_STAGE / "communication-strategy-audit.md"
COMMUNICATION_CONFIRMATION = COMMUNICATION_STAGE / "communication-strategy-confirmation.md"
COMMUNICATION_APPROVAL = Path("workbench/approvals/communication-strategy-approved.json")

COMMUNICATION_SCHEMAS = {
    "cyberppt.communication_strategy.v1",
    "cyberppt.communication_strategy.v2",
}
INTERACTION_POSTURES = {
    "decision_request",
    "peer_exchange",
    "internal_briefing",
    "working_session",
}
POSTURE_DEFAULT_FORBIDDEN_FRAMES = {
    "peer_exchange": (
        "共同决策",
        "当场决策",
        "批准哪些",
        "先批准",
        "请求批准",
        "请予批准",
        "原则批准",
        "批准建立",
        "授权启动",
        "决策请求",
        "建议形成的原则性意见",
        "请求合作",
        "寻求合作",
        "争取合作",
        "恳请合作",
        "达成合作决定",
        "作出合作决定",
    ),
}
POSTURE_FIELDS = (
    "frontstage_purpose",
    "backstage_intent",
    "interaction_posture",
    "explicit_audience_action",
    "forbidden_frontstage_frames",
)


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
        "schema": "cyberppt.communication_strategy.v2",
        "semantic_understanding_sha256": semantic_gate["semantic_understanding_sha256"],
        "semantic_source_bundle_sha256": semantic_gate["source_bundle_sha256"],
        "semantic_argument_model_sha256": semantic_gate.get("semantic_argument_model_sha256"),
        "audience": "",
        "communication_purpose": "",
        "decision_task": "",
        "content_focus": [],
        "options": [
            {
                "id": "",
                "label": "",
                "audience": "",
                "communication_purpose": "",
                "decision_task": "",
                "frontstage_purpose": "",
                "backstage_intent": "",
                "interaction_posture": "peer_exchange",
                "explicit_audience_action": "",
                "forbidden_frontstage_frames": [],
                "architecture_mode": "solution",
                "structure_principle": "",
                "audience_concerns": [],
            },
            {
                "id": "",
                "label": "",
                "audience": "",
                "communication_purpose": "",
                "decision_task": "",
                "frontstage_purpose": "",
                "backstage_intent": "",
                "interaction_posture": "decision_request",
                "explicit_audience_action": "",
                "forbidden_frontstage_frames": [],
                "architecture_mode": "solution",
                "structure_principle": "",
                "audience_concerns": [],
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
            "Determine who the deck communicates with, what it explicitly introduces or discusses, what the audience is visibly invited to do, and what strategic intent must remain backstage.",
            "Do not create pages or an outline here. Do not replace source meaning with a generic consulting storyline.",
            "",
            "Write `communication-strategy.json` with schema `cyberppt.communication_strategy.v2`.",
            "Copy all current semantic hashes below exactly. Supply a concrete audience, communication purpose, decision task, and 1-5 content-focus items.",
            "`decision_task` is retained as a compatibility field. It means the audience response expected from this communication; for `peer_exchange`, write understanding, questions, opinions, or supplementary conditions rather than an approval decision.",
            "Supply 2-3 materially different reporting-direction options. Each option needs `id`, `label`, its concrete `audience`, `communication_purpose`, `decision_task`, `architecture_mode` (`solution` or `consulting`), a concrete `structure_principle` describing chapter logic and order, and 2-8 source-anchored `audience_concerns` describing the questions this audience must have answered.",
            "Each v2 option must also define `frontstage_purpose`, `backstage_intent`, `interaction_posture`, `explicit_audience_action`, and 1-12 literal `forbidden_frontstage_frames`.",
            "`frontstage_purpose` controls visible agenda, chapter framing, titles, questions, and closing language. `backstage_intent` is strategic context only and must never be promoted into those visible fields.",
            "Use `interaction_posture=peer_exchange` when the visible relationship is introduction and exchange among peers; do not turn a possible future cooperation outcome into an on-screen approval request.",
            "The options may share an architecture mode, but their structure principles must differ. Set `recommendation` to one option id.",
            "If the audience cannot be established from the source, describe the most likely audience but make the ambiguity explicit in the option labels; the human confirmation step remains mandatory.",
            "",
            "## Required binding",
            "",
            f"- semantic_understanding_sha256: {semantic_gate['semantic_understanding_sha256']}",
            f"- semantic_source_bundle_sha256: {semantic_gate['source_bundle_sha256']}",
            f"- semantic_argument_model_sha256: {semantic_gate.get('semantic_argument_model_sha256', '')}",
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
        "semantic_argument_model_sha256": semantic_gate.get("semantic_argument_model_sha256"),
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


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_text(item) for item in value if _text(item)]


def communication_posture(value: object) -> dict[str, Any]:
    option = value if isinstance(value, dict) else {}
    return {
        "frontstage_purpose": _text(option.get("frontstage_purpose")),
        "backstage_intent": _text(option.get("backstage_intent")),
        "interaction_posture": _text(option.get("interaction_posture")),
        "explicit_audience_action": _text(option.get("explicit_audience_action")),
        "forbidden_frontstage_frames": _string_list(
            option.get("forbidden_frontstage_frames")
        ),
    }


def _normalized_phrase(value: object) -> str:
    return re.sub(r"[\s，。；：、,.!?！？—_\-（）()]+", "", _text(value)).casefold()


def _flatten_text(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [text for item in value for text in _flatten_text(item)]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _flatten_text(item)]
    return []


def forbidden_frontstage_hits(value: object, forbidden: object) -> list[str]:
    """Return literal posture frames found in a nested frontstage value."""

    phrases = _string_list(forbidden)
    hits: list[str] = []
    for visible_text in _flatten_text(value):
        normalized = _normalized_phrase(visible_text)
        for phrase in phrases:
            normalized_phrase = _normalized_phrase(phrase)
            if normalized_phrase and normalized_phrase in normalized and phrase not in hits:
                hits.append(phrase)
    return hits


def effective_forbidden_frontstage_frames(posture: object) -> list[str]:
    """Return project-specific frames plus non-optional posture policy.

    The authoring model may add source- or audience-specific frames, but it may
    not weaken the platform-role policy.  In particular, a peer exchange is an
    introduction/discussion posture, not a request for approval or cooperation.
    """

    contract = posture if isinstance(posture, dict) else {}
    frames = [
        *POSTURE_DEFAULT_FORBIDDEN_FRAMES.get(
            _text(contract.get("interaction_posture")), ()
        ),
        *_string_list(contract.get("forbidden_frontstage_frames")),
    ]
    unique: list[str] = []
    normalized: set[str] = set()
    for frame in frames:
        key = _normalized_phrase(frame)
        if key and key not in normalized:
            unique.append(frame)
            normalized.add(key)
    return unique


def frontstage_posture_issues(
    outline: dict[str, Any], gate: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """Reject visible outline rhetoric that surfaces a backstage-only intent.

    The strategy author supplies literal forbidden frames because the same word
    (for example, 合作) may be a legitimate source topic while an approval-seeking
    phrase (for example, 批准合作) may violate the selected peer-exchange posture.
    """

    if gate is None:
        return []
    forbidden = effective_forbidden_frontstage_frames(gate)
    if not forbidden:
        return []
    page_fields = (
        "title",
        "subtitle",
        "agenda_items",
        "sections",
        "page_mission",
        "page_necessity",
        "audience_question",
        "business_question",
        "core_message",
        "storyline_role",
        "transition_from_previous",
        "transition_to_next",
        "decision_request",
        "closing_note",
        "discussion_topics",
    )
    issues: list[dict[str, Any]] = []
    pages = outline.get("pages") if isinstance(outline.get("pages"), list) else []
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = _text(page.get("page_id"))
        for field in page_fields:
            for visible_text in _flatten_text(page.get(field)):
                for phrase in forbidden_frontstage_hits(visible_text, forbidden):
                    issues.append(
                        {
                            "code": "BACKSTAGE_INTENT_SURFACED",
                            "message": (
                                f"{page_id or 'outline'} field {field} surfaces forbidden "
                                f"frontstage frame {phrase!r} under the approved "
                                f"{gate.get('interaction_posture') or 'communication'} posture."
                            ),
                            "pages": [page_id] if page_id else [],
                            "retry_strategy": "restore_frontstage_communication_posture",
                        }
                    )
    return issues


def _audience_concerns(value: object) -> list[dict[str, Any]]:
    """Return the concrete questions this audience needs answered.

    ``audience`` alone is only metadata.  A concern contract makes the chosen
    communication direction consumable by the director and page auditor.
    """

    if not isinstance(value, list):
        return []
    concerns: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        concern_id = _text(item.get("id"))
        question = _text(item.get("question"))
        anchors = item.get("source_anchors")
        if not isinstance(anchors, list):
            anchors = []
        anchors = [_text(anchor) for anchor in anchors if _text(anchor)]
        if concern_id and question and anchors:
            concerns.append(
                {
                    "id": concern_id,
                    "question": question,
                    "source_anchors": anchors,
                    "importance": _text(item.get("importance")) or "required",
                }
            )
    return concerns


def _audit_issues(payload: dict[str, Any], semantic_gate: dict[str, Any]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    schema = _text(payload.get("schema"))
    if schema not in COMMUNICATION_SCHEMAS:
        issues.append({"code": "COMMUNICATION_SCHEMA_INVALID", "message": "schema must be cyberppt.communication_strategy.v1 or v2"})
    for field in ("audience", "communication_purpose", "decision_task"):
        if not _text(payload.get(field)):
            issues.append({"code": f"{field.upper()}_MISSING", "message": f"{field} must be concrete and non-empty"})
    focus = payload.get("content_focus")
    if not isinstance(focus, list) or not 1 <= len([item for item in focus if _text(item)]) <= 5:
        issues.append({"code": "CONTENT_FOCUS_INVALID", "message": "content_focus must contain 1-5 non-empty items"})
    for field, expected in (
        ("semantic_understanding_sha256", semantic_gate["semantic_understanding_sha256"]),
        ("semantic_source_bundle_sha256", semantic_gate["source_bundle_sha256"]),
        ("semantic_argument_model_sha256", semantic_gate.get("semantic_argument_model_sha256")),
    ):
        if expected is None:
            continue
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
        audience = _text(option.get("audience"))
        purpose = _text(option.get("communication_purpose"))
        task = _text(option.get("decision_task"))
        mode = _text(option.get("architecture_mode"))
        principle = _text(option.get("structure_principle"))
        concerns = _audience_concerns(option.get("audience_concerns"))
        if not option_id or not label or not audience or not purpose or not task or not principle or mode not in {"solution", "consulting"}:
            issues.append({"code": "COMMUNICATION_OPTION_INCOMPLETE", "message": f"option {index} requires id, label, audience, communication_purpose, decision_task, valid architecture_mode, and structure_principle"})
        if not 2 <= len(concerns) <= 8:
            issues.append({"code": "AUDIENCE_CONCERNS_INVALID", "message": f"option {index} requires 2-8 concrete audience concerns; each needs id, question, and source_anchors"})
        concern_ids = [item["id"] for item in concerns]
        if len(set(concern_ids)) != len(concern_ids):
            issues.append({"code": "AUDIENCE_CONCERN_IDS_INVALID", "message": f"option {index} audience concern ids must be unique"})
        if schema == "cyberppt.communication_strategy.v2":
            posture = communication_posture(option)
            if any(
                not posture[field]
                for field in (
                    "frontstage_purpose",
                    "backstage_intent",
                    "interaction_posture",
                    "explicit_audience_action",
                )
            ):
                issues.append({
                    "code": "COMMUNICATION_POSTURE_INCOMPLETE",
                    "message": f"option {index} requires concrete frontstage purpose, backstage intent, interaction posture, and explicit audience action",
                })
            if posture["interaction_posture"] not in INTERACTION_POSTURES:
                issues.append({
                    "code": "COMMUNICATION_POSTURE_INVALID",
                    "message": f"option {index} interaction_posture must be one of {sorted(INTERACTION_POSTURES)}",
                })
            forbidden = posture["forbidden_frontstage_frames"]
            if not 1 <= len(forbidden) <= 12 or len({_normalized_phrase(item) for item in forbidden}) != len(forbidden):
                issues.append({
                    "code": "FRONTSTAGE_FORBIDDEN_FRAMES_INVALID",
                    "message": f"option {index} requires 1-12 unique literal forbidden_frontstage_frames",
                })
            if _normalized_phrase(posture["frontstage_purpose"]) == _normalized_phrase(posture["backstage_intent"]):
                issues.append({
                    "code": "FRONTSTAGE_BACKSTAGE_NOT_DISTINCT",
                    "message": f"option {index} must distinguish visible communication purpose from latent strategic intent",
                })
            if posture["interaction_posture"] == "peer_exchange":
                posture_hits = forbidden_frontstage_hits(
                    [
                        option.get("communication_purpose"),
                        option.get("decision_task"),
                        posture["frontstage_purpose"],
                        posture["explicit_audience_action"],
                        [item["question"] for item in concerns],
                    ],
                    effective_forbidden_frontstage_frames(posture),
                )
                if posture_hits:
                    issues.append({
                        "code": "COMMUNICATION_POSTURE_SELF_CONTRADICTORY",
                        "message": (
                            f"option {index} declares peer_exchange but surfaces "
                            f"approval/cooperation-seeking frames: {', '.join(posture_hits)}"
                        ),
                    })
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
        "semantic_argument_model_sha256": semantic_gate.get("semantic_argument_model_sha256"),
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
        f"- 沟通任务：{_text(payload.get('decision_task')) or '待补充'}",
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
            posture = communication_posture(option)
            option_lines += [
                f"### {option['label']}{recommended}",
                "",
                f"- option_id: `{option['id']}`",
                f"- 沟通对象：{option['audience']}",
                f"- 沟通目的：{option['communication_purpose']}",
                f"- 沟通任务：{option['decision_task']}",
                f"- 结构模式：{option['architecture_mode']}",
                f"- 章节组织：{option['structure_principle']}",
                *(
                    [
                        f"- 明线目的：{posture['frontstage_purpose']}",
                        f"- 隐含意图（不得直接上屏）：{posture['backstage_intent']}",
                        f"- 沟通姿态：{posture['interaction_posture']}",
                        f"- 明示受众动作：{posture['explicit_audience_action']}",
                        "- 禁止显性化话术：" + "、".join(posture["forbidden_frontstage_frames"]),
                    ]
                    if payload.get("schema") == "cyberppt.communication_strategy.v2"
                    else []
                ),
                "- 受众必须得到回答的问题：",
                *[
                    f"  - `{concern.get('id')}` {concern.get('question')}（依据：{'、'.join(str(anchor) for anchor in concern.get('source_anchors', []))}）"
                    for concern in _audience_concerns(option.get('audience_concerns'))
                ],
                "",
            ]
        confirmation.write_text(
            "\n".join(
                [
                    "# 提纲生成前：沟通策略确认",
                    "",
                    "## 成果物",
                    "",
                    f"- **候选沟通策略**：`{artifact.as_posix()}`",
                    f"- **全文语义理解文档**：`{(project / SEMANTIC_ARTIFACT).as_posix()}`",
                    "",
                    "## 请确认这套材料主要与谁沟通？",
                    "",
                    f"当前识别：**{payload['audience']}**",
                    "",
                    "## 沟通目的与受众任务",
                    "",
                    f"- 沟通目的：{payload['communication_purpose']}",
                    f"- 沟通任务：{payload['decision_task']}",
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
    prior_communication_decisions = [
        _text(item.get("id"))
        for item in load_user_decisions(project)
        if isinstance(item, dict)
        and item.get("status") == "approved"
        and _text(item.get("id")).startswith("communication_strategy:")
        and _text(item.get("id")) != f"communication_strategy:{option_id}"
    ]
    decision = record_user_decision(
        project,
        decision_id=f"communication_strategy:{option_id}",
        question="本材料主要与谁沟通、以什么方向组织？",
        answer=f"选择 {selected.get('label') or option_id}：{selected.get('audience')}",
        applies_to=[
            "audience_concerns",
            "chapter_emphasis",
            "page_selection",
            "decision_destination",
            "frontstage_framing",
            "backstage_intent",
        ],
        supersedes=prior_communication_decisions,
    )
    approval = {
        "schema": "cyberppt.communication_strategy_approval.v1",
        "decision": "approved",
        "option_id": option_id,
        "selected_option": selected,
        "audience": selected["audience"],
        "communication_purpose": selected["communication_purpose"],
        "decision_task": selected["decision_task"],
        "audience_concerns": _audience_concerns(selected.get("audience_concerns")),
        "user_decision_id": decision["id"],
        "content_focus": payload["content_focus"],
        "approved_at": _utc_now(),
        "note": note.strip(),
    }
    if payload.get("schema") == "cyberppt.communication_strategy.v2":
        approval["communication_strategy_schema"] = payload["schema"]
        approval.update(communication_posture(selected))
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
    if approval.get("decision") != "approved":
        raise ValueError("communication-strategy human approval is invalid")
    if not 2 <= len(_audience_concerns(approval.get("audience_concerns"))) <= 8:
        raise ValueError("communication-strategy approval lacks a source-anchored audience concern contract; rerun communication-strategy-check and reapprove")
    if approval.get("communication_strategy_schema") == "cyberppt.communication_strategy.v2":
        posture = communication_posture(approval)
        if (
            any(not posture[field] for field in POSTURE_FIELDS[:-1])
            or posture["interaction_posture"] not in INTERACTION_POSTURES
            or not posture["forbidden_frontstage_frames"]
        ):
            raise ValueError("communication-strategy approval lacks a valid frontstage/backstage posture contract; reapprove the selected option")
    decision_id = _text(approval.get("user_decision_id"))
    if not decision_id or decision_id not in {
        _text(item.get("id")) for item in load_user_decisions(project)
        if isinstance(item, dict)
    }:
        raise ValueError("communication-strategy approval lacks its durable user-decision record; reapprove the selected option")
    approval["communication_strategy_sha256"] = _sha256_path(artifact)
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
        "audience": gate.get("audience"),
        "communication_purpose": gate.get("communication_purpose"),
        "decision_task": gate.get("decision_task"),
        "reporting_direction": gate.get("option_id"),
        "architecture_mode": selected.get("architecture_mode"),
        "structure_principle": selected.get("structure_principle"),
        "user_decision_id": gate.get("user_decision_id"),
        "audience_concerns": gate.get("audience_concerns"),
    }
    for field in POSTURE_FIELDS:
        if gate.get(field) not in (None, "", []):
            expected[field] = gate.get(field)
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


def audience_concern_binding_issues(
    outline: dict[str, Any], gate: dict[str, Any] | None
) -> list[dict[str, str]]:
    """Ensure page contracts consume the selected audience concerns.

    This deliberately lives beside the root strategy binding: copying the
    audience label is insufficient evidence that the selected lens changed
    page selection.
    """

    if gate is None:
        return []
    selected = gate.get("audience_concerns")
    if not isinstance(selected, list) or not selected:
        return [{
            "code": "AUDIENCE_CONCERNS_NOT_BOUND",
            "message": "The approved communication strategy has no consumable audience concern contract.",
            "retry_strategy": "rebuild_communication_strategy",
        }]
    allowed = {
        _text(item.get("id"))
        for item in selected
        if isinstance(item, dict) and _text(item.get("id"))
    }
    pages = outline.get("pages") if isinstance(outline.get("pages"), list) else []
    issues: list[dict[str, str]] = []
    consumed: set[str] = set()
    for page in pages:
        if not isinstance(page, dict) or page.get("page_type") != "content":
            continue
        page_id = _text(page.get("page_id")) or f"sequence-{page.get('sequence', '?')}"
        ids = page.get("audience_concern_ids")
        if not isinstance(ids, list) or not ids or any(not _text(item) for item in ids):
            issues.append({
                "code": "PAGE_AUDIENCE_CONCERNS_MISSING",
                "message": f"Content page {page_id} must map to at least one approved audience concern.",
                "retry_strategy": "map_page_to_audience_concerns",
            })
            continue
        unknown = {_text(item) for item in ids} - allowed
        if unknown:
            issues.append({
                "code": "PAGE_AUDIENCE_CONCERN_UNKNOWN",
                "message": f"Content page {page_id} references unknown audience concerns: {', '.join(sorted(unknown))}.",
                "retry_strategy": "map_page_to_audience_concerns",
            })
        consumed.update({_text(item) for item in ids} & allowed)
        if not _text(page.get("audience_relevance")):
            issues.append({
                "code": "PAGE_AUDIENCE_RELEVANCE_MISSING",
                "message": f"Content page {page_id} must explain why this page matters to the selected audience.",
                "retry_strategy": "state_audience_relevance",
            })
    required = {
        _text(item.get("id"))
        for item in selected
        if isinstance(item, dict) and _text(item.get("importance")) != "optional"
    }
    if required - consumed:
        issues.append({
            "code": "AUDIENCE_CONCERN_UNMAPPED",
            "message": f"Approved audience concerns are not mapped to content pages: {', '.join(sorted(required - consumed))}.",
            "retry_strategy": "map_audience_concerns_to_pages",
        })
    return issues

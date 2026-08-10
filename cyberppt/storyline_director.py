"""Story-first directing gate between communication strategy and Outline authoring."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.communication_strategy import (
    _audience_concerns,
    assert_communication_strategy_ready,
    communication_posture,
    effective_forbidden_frontstage_frames,
    forbidden_frontstage_hits,
)
from cyberppt.semantic_understanding import (
    SEMANTIC_ARTIFACT,
    SEMANTIC_ARGUMENT_MODEL,
    assert_semantic_understanding_ready,
)
from cyberppt.source_argument_model import load_model
from cyberppt.user_decisions import decision_consumption_issues, load_user_decisions


DIRECTOR_STAGE = Path("workbench/stages/00-storyline-director")
DIRECTOR_INPUT = DIRECTOR_STAGE / "storyline-director-input.md"
DIRECTOR_ARTIFACT = DIRECTOR_STAGE / "storyline-director.json"
DIRECTOR_AUDIT = DIRECTOR_STAGE / "storyline-director-audit.json"
SOURCE_TRUTH = Path("workbench/stages/01-analysis/source-truth.json")
SOURCE_TRUTH_AUDIT = Path("workbench/stages/01-analysis/source-truth-audit.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact root must be an object: {path}")
    return payload


def _text(value: object) -> str:
    return str(value or "").strip()


def storyline_director_required(project: Path) -> bool:
    manifest = project.expanduser().resolve() / "manifest.yml"
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8-sig")
    match = re.search(r"(?ms)^gates:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)", text)
    return bool(
        match
        and re.search(
            r"(?m)^\s+storyline_director:\s*required\s*$",
            match.group("body"),
        )
    )


def _outline_contract(payload: dict[str, Any]) -> dict[str, Any]:
    contract = {
        "theme": payload.get("theme"),
        "decision_destination": payload.get("decision_destination"),
        "story_arc": payload.get("story_arc"),
        "chapter_missions": payload.get("chapter_missions"),
        "selection_rules": payload.get("selection_rules"),
        "exclusion_rules": payload.get("exclusion_rules"),
        "page_rules": payload.get("page_rules"),
        "pacing": payload.get("pacing"),
        "semantic_understanding_sha256": payload.get("semantic_understanding_sha256"),
        "semantic_source_bundle_sha256": payload.get("semantic_source_bundle_sha256"),
        "semantic_source_map_bundle_sha256": payload.get("semantic_source_map_bundle_sha256"),
        "semantic_argument_model_sha256": payload.get("semantic_argument_model_sha256"),
        "audience_concerns": payload.get("audience_concerns"),
        "consumed_user_decisions": payload.get("consumed_user_decisions"),
    }
    for field in (
        "frontstage_purpose",
        "backstage_intent",
        "interaction_posture",
        "explicit_audience_action",
        "forbidden_frontstage_frames",
    ):
        if field in payload:
            contract[field] = payload.get(field)
    return contract


def storyline_director_authoring_contract() -> str:
    return "\n".join(
        [
            "You are the Outline Director. Do not create pages. First define the directed story that the Outline author must follow.",
            "The source is evidence, not a page inventory. Select and organize evidence around the approved theme and decision destination; preserve all traceability but never give every source item equal narrative or visual weight.",
            "Separate frontstage communication from backstage strategy. Visible story beats, chapter questions, and the communication destination must follow the approved frontstage purpose and audience action. The backstage intent may guide selection but must not become a visible approval request or decision-seeking headline.",
            "Every chapter must answer one question and hand a necessary unresolved question to the next chapter. Every future page must have one storyline role, one self-contained core meaning, and explicit transitions from the preceding page and to the following page.",
            "Do not promote generic value, constraints, boundaries, background, or technical inventories into the main line unless they are the actual subject of the approved communication strategy.",
            "Use the source argument model's explicit `argument_weight` as the authority for narrative importance. `core` means an independent source proposition and must remain a visible story beat; `supporting`, `detail`, and `constraint` describe subordinate material. A semantic relation explains how propositions connect and has `weight_effect=none`; it never changes either endpoint's argument weight or role. Determine the story beat from the approved proposition, not from a project-specific keyword or a generic layer label.",
            "Treat `editorial_hypothesis` entries only as candidates. A candidate framing may be selected, rejected, or tested here, but it may not be relabeled as source-explicit, overwrite the source thesis, or retroactively change Stage 00.",
        ]
    )


def prepare_storyline_director(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    communication = assert_communication_strategy_ready(project)
    if communication is None:
        raise ValueError("storyline director requires the communication-strategy gate")
    semantic = assert_semantic_understanding_ready(project)
    if semantic is None:
        raise ValueError("storyline director requires the semantic-understanding gate")
    truth_path = project / SOURCE_TRUTH
    truth_audit_path = project / SOURCE_TRUTH_AUDIT
    if not truth_path.is_file() or not truth_audit_path.is_file():
        raise FileNotFoundError("storyline director requires a passed Source Truth audit")
    truth_audit = _load(truth_audit_path)
    if truth_audit.get("status") != "passed":
        raise ValueError("storyline director requires source-truth-audit status passed")
    truth = _load(truth_path)
    argument_model = None
    if semantic.get("semantic_argument_model_sha256"):
        argument_model = load_model(project / SEMANTIC_ARGUMENT_MODEL)
    stage = project / DIRECTOR_STAGE
    stage.mkdir(parents=True, exist_ok=True)
    input_path = project / DIRECTOR_INPUT
    selected = communication.get("selected_option") or {}
    weighted_records = [
        {
            "id": record.get("id"),
            "priority": record.get("priority"),
            "claim_role": record.get("claim_role"),
            "status": record.get("status"),
            "statement": record.get("statement"),
            "source_locator": record.get("source_locator"),
        }
        for record in truth.get("records", [])
        if isinstance(record, dict) and record.get("priority") in {"P0", "P1"}
    ]
    source_sections = sorted({
        _text(record.get("source_locator", {}).get("section"))
        for record in truth.get("records", [])
        if isinstance(record, dict)
        and isinstance(record.get("source_locator"), dict)
        and _text(record.get("source_locator", {}).get("section"))
    })
    lines = [
        "# Storyline director authoring input",
        "",
        storyline_director_authoring_contract(),
        "",
        "Write `storyline-director.json` with schema `cyberppt.storyline_director.v2` and copy all artifact binding hashes exactly.",
        "Required fields: theme, decision_destination, story_arc (3-6 steps), chapter_missions (2-6 entries), selection_rules (3-8), exclusion_rules (3-8), page_rules (4-10), pacing, audience_concerns, consumed_user_decisions, and the complete approved frontstage/backstage posture contract.",
        "`decision_destination` is a compatibility field. When `interaction_posture=peer_exchange`, it must describe the intended understanding or exchange outcome, never an approval request or cooperation decision.",
        "Each chapter mission requires chapter_id, title, question, contribution, transition_to_next, max_content_pages, source_mission, source_question, source_section_refs, source_claim_ids, source_argument_node_ids, source_argument_node_roles, source_argument_node_weights, audience_concern_ids, and editorial_operation (select, compress, merge, split, or reframe). A reframe must not change the source subject, argument_role, argument_weight, or status.",
        "Pacing requires target_total_pages, min_total_pages, and max_total_pages.",
        "",
        "## Binding",
        "",
        f"- source_truth_sha256: {_sha256(truth_path)}",
        f"- communication_strategy_sha256: {communication['communication_strategy_sha256']}",
        f"- semantic_understanding_sha256: {semantic['semantic_understanding_sha256']}",
        f"- semantic_source_bundle_sha256: {semantic['source_bundle_sha256']}",
        f"- semantic_source_map_bundle_sha256: {semantic.get('source_map_bundle_sha256', '')}",
        f"- semantic_argument_model_sha256: {semantic.get('semantic_argument_model_sha256', '')}",
        "",
        "## Approved communication strategy",
        "",
        f"- audience: {communication.get('audience')}",
        f"- communication_purpose: {communication.get('communication_purpose')}",
        f"- decision_task: {communication.get('decision_task')}",
        f"- structure_principle: {selected.get('structure_principle')}",
        f"- frontstage_purpose: {communication.get('frontstage_purpose', '')}",
        f"- backstage_intent: {communication.get('backstage_intent', '')}",
        f"- interaction_posture: {communication.get('interaction_posture', '')}",
        f"- explicit_audience_action: {communication.get('explicit_audience_action', '')}",
        "- forbidden_frontstage_frames: " + json.dumps(
            communication.get("forbidden_frontstage_frames", []), ensure_ascii=False
        ),
        "- audience_concerns: " + json.dumps(
            _audience_concerns(communication.get("audience_concerns")),
            ensure_ascii=False,
        ),
        "- user_decision_id: " + _text(communication.get("user_decision_id")),
        "",
        "## Document semantics",
        "",
        json.dumps(truth.get("document_semantics", {}), ensure_ascii=False),
        "",
        "## Authoritative whole-document semantic understanding",
        "",
        "The approved semantic artifact is binding. The audience lens may select and reorder evidence, but may not replace the source business subject, chapter order, actor roles, status distinctions, or forbidden inferences.",
        "",
        (project / SEMANTIC_ARTIFACT).read_text(encoding="utf-8-sig").rstrip(),
        "",
        "## Authoritative source argument model",
        "",
        json.dumps(argument_model, ensure_ascii=False, indent=2) if argument_model is not None else "- legacy semantic artifact has no structured model",
        "",
        "## P0/P1 evidence available for directed selection",
        "",
        json.dumps(weighted_records, ensure_ascii=False, indent=2),
        "",
        "## Allowed source section references",
        "",
        json.dumps(source_sections, ensure_ascii=False),
        "",
    ]
    input_path.write_text("\n".join(lines), encoding="utf-8")
    artifact = project / DIRECTOR_ARTIFACT
    if not artifact.exists():
        template = {
            "schema": "cyberppt.storyline_director.v2",
            "source_truth_sha256": _sha256(truth_path),
            "communication_strategy_sha256": communication["communication_strategy_sha256"],
            "semantic_understanding_sha256": semantic["semantic_understanding_sha256"],
            "semantic_source_bundle_sha256": semantic["source_bundle_sha256"],
            "semantic_source_map_bundle_sha256": semantic.get("source_map_bundle_sha256"),
            "semantic_argument_model_sha256": semantic.get("semantic_argument_model_sha256"),
            **communication_posture(communication),
            "theme": "",
            "decision_destination": "",
            "story_arc": [],
            "chapter_missions": [],
            "selection_rules": [],
            "exclusion_rules": [],
            "page_rules": [],
            "pacing": {"target_total_pages": 0, "min_total_pages": 0, "max_total_pages": 0},
            "audience_concerns": _audience_concerns(communication.get("audience_concerns")),
            "consumed_user_decisions": [
                {
                    "decision_id": communication.get("user_decision_id"),
                    "effect": "Use the selected audience concerns to organize chapter order and page selection.",
                }
            ] if _text(communication.get("user_decision_id")) else [],
        }
        artifact.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema": "cyberppt.storyline_director_input.v1",
        "model_input": str(input_path),
        "model_input_sha256": _sha256(input_path),
        "output": str(artifact),
        "source_truth_sha256": _sha256(truth_path),
        "communication_strategy_sha256": communication["communication_strategy_sha256"],
        "semantic_understanding_sha256": semantic["semantic_understanding_sha256"],
        "semantic_source_bundle_sha256": semantic["source_bundle_sha256"],
        "semantic_source_map_bundle_sha256": semantic.get("source_map_bundle_sha256"),
        "semantic_argument_model_sha256": semantic.get("semantic_argument_model_sha256"),
        "consumed_user_decisions": [
            {
                "decision_id": communication.get("user_decision_id"),
                "effect": "Use the selected audience concerns to organize chapter order and page selection.",
            }
        ] if _text(communication.get("user_decision_id")) else [],
        "prepared_at": _utc_now(),
    }


def _audit_issues(
    payload: dict[str, Any],
    source_hash: str,
    communication_hash: str,
    semantic_hash: str = "",
    semantic_source_hash: str = "",
    semantic_source_map_hash: str = "",
    semantic_argument_model_hash: str = "",
    semantic_argument_node_ids: set[str] | None = None,
    semantic_argument_node_roles: dict[str, str] | None = None,
    semantic_argument_node_weights: dict[str, str] | None = None,
    audience_concerns: list[dict[str, Any]] | None = None,
    source_sections: set[str] | None = None,
    communication_posture_contract: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    schema = _text(payload.get("schema"))
    if schema not in {"cyberppt.storyline_director.v1", "cyberppt.storyline_director.v2"}:
        issues.append({"code": "DIRECTOR_SCHEMA_INVALID", "message": "schema must be cyberppt.storyline_director.v1 or v2"})
    for field, expected in (("source_truth_sha256", source_hash), ("communication_strategy_sha256", communication_hash)):
        if _text(payload.get(field)).casefold() != expected.casefold():
            issues.append({"code": "DIRECTOR_BINDING_STALE", "message": f"{field} must match the current upstream artifact"})
    for field, expected in (
        ("semantic_understanding_sha256", semantic_hash),
        ("semantic_source_bundle_sha256", semantic_source_hash),
        ("semantic_source_map_bundle_sha256", semantic_source_map_hash),
        ("semantic_argument_model_sha256", semantic_argument_model_hash),
    ):
        if expected and _text(payload.get(field)).casefold() != expected.casefold():
            issues.append({"code": "DIRECTOR_SEMANTIC_BINDING_STALE", "message": f"{field} must match the approved semantic understanding gate"})
    if audience_concerns is not None:
        actual_concerns = _audience_concerns(payload.get("audience_concerns"))
        expected_ids = {
            _text(item.get("id"))
            for item in audience_concerns
            if isinstance(item, dict) and _text(item.get("id"))
        }
        actual_ids = {_text(item.get("id")) for item in actual_concerns}
        if actual_ids != expected_ids:
            issues.append({"code": "DIRECTOR_AUDIENCE_CONCERNS_NOT_BOUND", "message": "Director must copy the approved audience concern contract exactly"})
    if schema == "cyberppt.storyline_director.v2":
        expected_posture = communication_posture(communication_posture_contract)
        actual_posture = communication_posture(payload)
        if actual_posture != expected_posture:
            issues.append({
                "code": "DIRECTOR_COMMUNICATION_POSTURE_DRIFTED",
                "message": "Director must copy the approved frontstage/backstage communication posture exactly",
            })
        frontstage_values = [
            payload.get("theme"),
            payload.get("decision_destination"),
            payload.get("story_arc"),
            [
                {
                    field: mission.get(field)
                    for field in ("title", "question", "contribution", "transition_to_next")
                }
                for mission in (payload.get("chapter_missions") or [])
                if isinstance(mission, dict)
            ],
        ]
        hits = forbidden_frontstage_hits(
            frontstage_values,
            effective_forbidden_frontstage_frames(expected_posture),
        )
        for phrase in hits:
            issues.append({
                "code": "DIRECTOR_BACKSTAGE_INTENT_SURFACED",
                "message": f"Director surfaces forbidden frontstage frame {phrase!r}; restore the approved visible communication posture",
            })
    for field in ("theme", "decision_destination"):
        if not _text(payload.get(field)):
            issues.append({"code": "DIRECTOR_CENTER_MISSING", "message": f"{field} must be concrete and non-empty"})
    for field, minimum, maximum in (
        ("story_arc", 3, 6),
        ("selection_rules", 3, 8),
        ("exclusion_rules", 3, 8),
        ("page_rules", 4, 10),
    ):
        values = payload.get(field)
        valid = [item for item in values if _text(item)] if isinstance(values, list) else []
        if not minimum <= len(valid) <= maximum or len(set(map(_text, valid))) != len(valid):
            issues.append({"code": "DIRECTOR_RULESET_INVALID", "message": f"{field} must contain {minimum}-{maximum} unique non-empty items"})
    missions = payload.get("chapter_missions")
    valid_missions = missions if isinstance(missions, list) else []
    if not 2 <= len(valid_missions) <= 6 or any(not isinstance(item, dict) for item in valid_missions):
        issues.append({"code": "DIRECTOR_CHAPTER_MISSIONS_INVALID", "message": "chapter_missions must contain 2-6 objects"})
    else:
        ids = []
        for mission in valid_missions:
            ids.append(_text(mission.get("chapter_id")))
            if any(not _text(mission.get(field)) for field in ("chapter_id", "title", "question", "contribution", "transition_to_next")):
                issues.append({"code": "DIRECTOR_CHAPTER_MISSION_INCOMPLETE", "message": "each chapter mission requires id, title, question, contribution, and transition_to_next"})
            if semantic_hash:
                if not _text(mission.get("source_mission")) or not _text(mission.get("source_question")):
                    issues.append({"code": "DIRECTOR_SOURCE_MISSION_MISSING", "message": "each chapter mission must preserve a source-grounded mission and question"})
                section_refs = mission.get("source_section_refs")
                if not isinstance(section_refs, list) or not section_refs or any(not _text(item) for item in section_refs):
                    issues.append({"code": "DIRECTOR_SOURCE_SECTIONS_MISSING", "message": "each chapter mission must identify source section references"})
                elif source_sections is not None and not set(map(_text, section_refs)).issubset(source_sections):
                    issues.append({"code": "DIRECTOR_SOURCE_SECTION_UNKNOWN", "message": "chapter mission references a source section outside Source Truth"})
                operation = _text(mission.get("editorial_operation"))
                if operation not in {"select", "compress", "merge", "split", "reframe"}:
                    issues.append({"code": "DIRECTOR_EDITORIAL_OPERATION_INVALID", "message": "editorial_operation must be select, compress, merge, split, or reframe"})
                if mission.get("semantic_promotion") is True:
                    issues.append({"code": "EDITORIAL_THEME_UNSUPPORTED", "message": "A director mission may not promote an editorial framing into a source theme"})
                claim_ids = mission.get("source_claim_ids")
                if not isinstance(claim_ids, list) or not claim_ids or any(not _text(item) for item in claim_ids):
                    issues.append({"code": "DIRECTOR_SOURCE_CLAIMS_MISSING", "message": "each chapter mission must identify the semantic/source claims it organizes"})
                if semantic_argument_model_hash:
                    node_ids = mission.get("source_argument_node_ids")
                    if not isinstance(node_ids, list) or not node_ids or any(not _text(item) for item in node_ids):
                        issues.append({"code": "DIRECTOR_ARGUMENT_NODES_MISSING", "message": "each chapter mission must identify the Stage 00 source argument nodes it organizes"})
                    elif semantic_argument_node_ids is not None and not set(map(_text, node_ids)).issubset(semantic_argument_node_ids):
                        issues.append({"code": "DIRECTOR_ARGUMENT_NODE_UNKNOWN", "message": "chapter mission references a source argument node outside the approved semantic model"})
                    weights = mission.get("source_argument_node_weights")
                    if not isinstance(weights, dict):
                        issues.append({"code": "DIRECTOR_ARGUMENT_WEIGHTS_MISSING", "message": "chapter mission must copy source argument node weights from the approved semantic model"})
                    else:
                        for node_id in node_ids or []:
                            node_key = _text(node_id)
                            expected_weight = _text((semantic_argument_node_weights or {}).get(node_key))
                            actual_weight = _text(weights.get(node_key))
                            if not actual_weight:
                                issues.append({"code": "DIRECTOR_ARGUMENT_WEIGHT_MISSING", "message": "chapter mission is missing a selected source argument node weight"})
                            elif expected_weight and actual_weight != expected_weight:
                                issues.append({"code": "DIRECTOR_ARGUMENT_WEIGHT_DRIFTED", "message": "chapter mission changed the source argument weight; relation type cannot downgrade a core argument"})
                    roles = mission.get("source_argument_node_roles")
                    if not isinstance(roles, dict):
                        issues.append({"code": "DIRECTOR_ARGUMENT_ROLES_MISSING", "message": "chapter mission must copy source argument roles from the approved semantic model"})
                    else:
                        for node_id in node_ids or []:
                            node_key = _text(node_id)
                            expected_role = _text((semantic_argument_node_roles or {}).get(node_key))
                            actual_role = _text(roles.get(node_key))
                            if not actual_role:
                                issues.append({"code": "DIRECTOR_ARGUMENT_ROLE_MISSING", "message": "chapter mission is missing a selected source argument role"})
                            elif expected_role and actual_role != expected_role:
                                issues.append({"code": "DIRECTOR_ARGUMENT_ROLE_DRIFTED", "message": "chapter mission changed the approved source argument role; no core role may be replaced by a generic layer label"})
                concern_ids = mission.get("audience_concern_ids")
                if not isinstance(concern_ids, list) or not concern_ids:
                    issues.append({"code": "DIRECTOR_AUDIENCE_CONCERNS_MISSING", "message": "each chapter mission must state which audience concerns it answers"})
                elif audience_concerns is not None:
                    allowed = {
                        _text(item.get("id"))
                        for item in audience_concerns
                        if isinstance(item, dict) and _text(item.get("id"))
                    }
                    if not set(map(_text, concern_ids)).issubset(allowed):
                        issues.append({"code": "DIRECTOR_AUDIENCE_CONCERN_UNKNOWN", "message": "chapter mission references an audience concern outside the approved contract"})
            pages = mission.get("max_content_pages")
            if not isinstance(pages, int) or not 1 <= pages <= 12:
                issues.append({"code": "DIRECTOR_CHAPTER_PACING_INVALID", "message": "max_content_pages must be an integer from 1 to 12"})
        if "" in ids or len(ids) != len(set(ids)):
            issues.append({"code": "DIRECTOR_CHAPTER_IDS_INVALID", "message": "chapter ids must be non-empty and unique"})
    pacing = payload.get("pacing")
    if not isinstance(pacing, dict):
        issues.append({"code": "DIRECTOR_PACING_INVALID", "message": "pacing must be an object"})
    else:
        target, minimum, maximum = (pacing.get(name) for name in ("target_total_pages", "min_total_pages", "max_total_pages"))
        if not all(isinstance(item, int) and item > 0 for item in (target, minimum, maximum)) or not minimum <= target <= maximum:
            issues.append({"code": "DIRECTOR_PACING_INVALID", "message": "pacing must satisfy positive min <= target <= max"})
    return issues


def run_storyline_director_audit(project: Path) -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    communication = assert_communication_strategy_ready(project)
    if communication is None:
        raise ValueError("storyline director requires the communication-strategy gate")
    semantic = assert_semantic_understanding_ready(project)
    truth_path = project / SOURCE_TRUTH
    artifact = project / DIRECTOR_ARTIFACT
    if not truth_path.is_file() or not artifact.is_file():
        raise FileNotFoundError("storyline director input or artifact is missing; run prepare-storyline-director")
    payload = _load(artifact)
    issues = _audit_issues(
        payload,
        _sha256(truth_path),
        communication["communication_strategy_sha256"],
        semantic_hash=semantic["semantic_understanding_sha256"] if semantic else "",
        semantic_source_hash=semantic["source_bundle_sha256"] if semantic else "",
        semantic_source_map_hash=semantic.get("source_map_bundle_sha256", "") if semantic else "",
        semantic_argument_model_hash=semantic.get("semantic_argument_model_sha256", "") if semantic else "",
        semantic_argument_node_ids=(
            {
                _text(item.get("id"))
                for field in ("section_nodes", "subsection_nodes")
                for item in (load_model(project / SEMANTIC_ARGUMENT_MODEL).get(field) or [])
                if isinstance(item, dict) and _text(item.get("id"))
            }
            if semantic and semantic.get("semantic_argument_model_sha256")
            else None
        ),
        semantic_argument_node_weights=(
            {
                _text(item.get("id")): _text(item.get("argument_weight"))
                for field in ("section_nodes", "subsection_nodes")
                for item in (load_model(project / SEMANTIC_ARGUMENT_MODEL).get(field) or [])
                if isinstance(item, dict) and _text(item.get("id"))
            }
            if semantic and semantic.get("semantic_argument_model_sha256")
            else None
        ),
        semantic_argument_node_roles=(
            {
                _text(item.get("id")): _text(item.get("argument_role"))
                for field in ("section_nodes", "subsection_nodes")
                for item in (load_model(project / SEMANTIC_ARGUMENT_MODEL).get(field) or [])
                if isinstance(item, dict) and _text(item.get("id"))
            }
            if semantic and semantic.get("semantic_argument_model_sha256")
            else None
        ),
        audience_concerns=_audience_concerns(communication.get("audience_concerns")),
        communication_posture_contract=communication,
        source_sections=(
            {
                _text(record.get("source_locator", {}).get("section"))
                for record in _load(truth_path).get("records", [])
                if isinstance(record, dict) and isinstance(record.get("source_locator"), dict) and _text(record.get("source_locator", {}).get("section"))
            }
            or None
        ),
    )
    decisions = load_user_decisions(project)
    if decisions:
        issues.extend(
            decision_consumption_issues(
                decisions=decisions,
                consumed=payload.get("consumed_user_decisions"),
            )
        )
    report = {
        "schema": "cyberppt.storyline_director_audit.v1",
        "status": "rewrite_required" if issues else "passed",
        "artifact": str(artifact),
        "storyline_director_sha256": _sha256(artifact),
        "source_truth_sha256": _sha256(truth_path),
        "communication_strategy_sha256": communication["communication_strategy_sha256"],
        "semantic_understanding_sha256": semantic["semantic_understanding_sha256"] if semantic else None,
        "semantic_source_bundle_sha256": semantic["source_bundle_sha256"] if semantic else None,
        "semantic_source_map_bundle_sha256": semantic.get("source_map_bundle_sha256") if semantic else None,
        "semantic_argument_model_sha256": semantic.get("semantic_argument_model_sha256") if semantic else None,
        "issues": issues,
        "audited_at": _utc_now(),
    }
    (project / DIRECTOR_AUDIT).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return (4 if issues else 0), report


def assert_storyline_director_ready(project: Path) -> dict[str, Any] | None:
    project = project.expanduser().resolve()
    if not storyline_director_required(project):
        return None
    communication = assert_communication_strategy_ready(project)
    semantic = assert_semantic_understanding_ready(project)
    artifact = project / DIRECTOR_ARTIFACT
    audit_path = project / DIRECTOR_AUDIT
    truth_path = project / SOURCE_TRUTH
    if not artifact.is_file() or not audit_path.is_file():
        raise FileNotFoundError("required storyline-director gate is missing; run prepare-storyline-director and storyline-director-check")
    payload = _load(artifact)
    audit = _load(audit_path)
    expected = (
        audit.get("status") == "passed"
        and audit.get("storyline_director_sha256") == _sha256(artifact)
        and audit.get("source_truth_sha256") == _sha256(truth_path)
        and audit.get("communication_strategy_sha256") == communication["communication_strategy_sha256"]
        and audit.get("semantic_understanding_sha256") == (semantic["semantic_understanding_sha256"] if semantic else None)
        and audit.get("semantic_source_bundle_sha256") == (semantic["source_bundle_sha256"] if semantic else None)
        and audit.get("semantic_source_map_bundle_sha256") == (semantic.get("source_map_bundle_sha256") if semantic else None)
        and audit.get("semantic_argument_model_sha256") == (semantic.get("semantic_argument_model_sha256") if semantic else None)
    )
    if not expected:
        raise ValueError("storyline-director gate is stale or not passed; rerun storyline-director-check")
    payload["storyline_director_sha256"] = _sha256(artifact)
    payload["outline_contract"] = _outline_contract(payload)
    payload["storyline_director_path"] = str(artifact)
    return payload


def storyline_director_binding_issues(outline: dict[str, Any], gate: dict[str, Any] | None) -> list[dict[str, str]]:
    if gate is None:
        return []
    issues: list[dict[str, str]] = []
    if _text(outline.get("storyline_director_sha256")) != _text(gate.get("storyline_director_sha256")):
        issues.append({"code": "STORYLINE_DIRECTOR_NOT_BOUND", "message": "Outline storyline_director_sha256 must match the current director artifact.", "retry_strategy": "rebuild_from_storyline_director"})
    if outline.get("storyline") != gate.get("outline_contract"):
        issues.append({"code": "STORYLINE_CONTRACT_DRIFTED", "message": "Outline storyline must copy the current director contract exactly.", "retry_strategy": "rebuild_from_storyline_director"})
    return issues

"""Story-first directing gate between communication strategy and Outline authoring."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.communication_strategy import assert_communication_strategy_ready


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
    return {
        "theme": payload.get("theme"),
        "decision_destination": payload.get("decision_destination"),
        "story_arc": payload.get("story_arc"),
        "chapter_missions": payload.get("chapter_missions"),
        "selection_rules": payload.get("selection_rules"),
        "exclusion_rules": payload.get("exclusion_rules"),
        "page_rules": payload.get("page_rules"),
        "pacing": payload.get("pacing"),
    }


def prepare_storyline_director(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    communication = assert_communication_strategy_ready(project)
    if communication is None:
        raise ValueError("storyline director requires the communication-strategy gate")
    truth_path = project / SOURCE_TRUTH
    truth_audit_path = project / SOURCE_TRUTH_AUDIT
    if not truth_path.is_file() or not truth_audit_path.is_file():
        raise FileNotFoundError("storyline director requires a passed Source Truth audit")
    truth_audit = _load(truth_audit_path)
    if truth_audit.get("status") != "passed":
        raise ValueError("storyline director requires source-truth-audit status passed")
    truth = _load(truth_path)
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
        }
        for record in truth.get("records", [])
        if isinstance(record, dict) and record.get("priority") in {"P0", "P1"}
    ]
    lines = [
        "# Storyline director authoring input",
        "",
        "You are the Outline Director. Do not create pages. First define the directed story that the Outline author must follow.",
        "The source is evidence, not a page inventory. Select and organize evidence around the approved theme and decision destination; preserve all traceability but never give every source item equal narrative or visual weight.",
        "Every chapter must answer one question and hand a necessary unresolved question to the next chapter. Every future page must have one storyline role, one self-contained core meaning, and explicit transitions from the preceding page and to the following page.",
        "Do not promote generic value, constraints, boundaries, background, or technical inventories into the main line unless they are the actual subject of the approved communication strategy.",
        "",
        "Write `storyline-director.json` with schema `cyberppt.storyline_director.v1` and copy all binding hashes exactly.",
        "Required fields: theme, decision_destination, story_arc (3-6 steps), chapter_missions (2-6 entries), selection_rules (3-8), exclusion_rules (3-8), page_rules (4-10), and pacing.",
        "Each chapter mission requires chapter_id, title, question, contribution, transition_to_next, and max_content_pages.",
        "Pacing requires target_total_pages, min_total_pages, and max_total_pages.",
        "",
        "## Binding",
        "",
        f"- source_truth_sha256: {_sha256(truth_path)}",
        f"- communication_strategy_approval_sha256: {communication['communication_strategy_approval_sha256']}",
        "",
        "## Approved communication strategy",
        "",
        f"- audience: {communication.get('audience')}",
        f"- communication_purpose: {communication.get('communication_purpose')}",
        f"- decision_task: {communication.get('decision_task')}",
        f"- structure_principle: {selected.get('structure_principle')}",
        "",
        "## Document semantics",
        "",
        json.dumps(truth.get("document_semantics", {}), ensure_ascii=False),
        "",
        "## P0/P1 evidence available for directed selection",
        "",
        json.dumps(weighted_records, ensure_ascii=False, indent=2),
        "",
    ]
    input_path.write_text("\n".join(lines), encoding="utf-8")
    artifact = project / DIRECTOR_ARTIFACT
    if not artifact.exists():
        template = {
            "schema": "cyberppt.storyline_director.v1",
            "source_truth_sha256": _sha256(truth_path),
            "communication_strategy_approval_sha256": communication["communication_strategy_approval_sha256"],
            "theme": "",
            "decision_destination": "",
            "story_arc": [],
            "chapter_missions": [],
            "selection_rules": [],
            "exclusion_rules": [],
            "page_rules": [],
            "pacing": {"target_total_pages": 0, "min_total_pages": 0, "max_total_pages": 0},
        }
        artifact.write_text(json.dumps(template, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "schema": "cyberppt.storyline_director_input.v1",
        "model_input": str(input_path),
        "model_input_sha256": _sha256(input_path),
        "output": str(artifact),
        "source_truth_sha256": _sha256(truth_path),
        "communication_strategy_approval_sha256": communication["communication_strategy_approval_sha256"],
        "prepared_at": _utc_now(),
    }


def _audit_issues(payload: dict[str, Any], source_hash: str, approval_hash: str) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    if payload.get("schema") != "cyberppt.storyline_director.v1":
        issues.append({"code": "DIRECTOR_SCHEMA_INVALID", "message": "schema must be cyberppt.storyline_director.v1"})
    for field, expected in (("source_truth_sha256", source_hash), ("communication_strategy_approval_sha256", approval_hash)):
        if _text(payload.get(field)).casefold() != expected.casefold():
            issues.append({"code": "DIRECTOR_BINDING_STALE", "message": f"{field} must match the current upstream artifact"})
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
    truth_path = project / SOURCE_TRUTH
    artifact = project / DIRECTOR_ARTIFACT
    if not truth_path.is_file() or not artifact.is_file():
        raise FileNotFoundError("storyline director input or artifact is missing; run prepare-storyline-director")
    payload = _load(artifact)
    issues = _audit_issues(payload, _sha256(truth_path), communication["communication_strategy_approval_sha256"])
    report = {
        "schema": "cyberppt.storyline_director_audit.v1",
        "status": "rewrite_required" if issues else "passed",
        "artifact": str(artifact),
        "storyline_director_sha256": _sha256(artifact),
        "source_truth_sha256": _sha256(truth_path),
        "communication_strategy_approval_sha256": communication["communication_strategy_approval_sha256"],
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
        and audit.get("communication_strategy_approval_sha256") == communication["communication_strategy_approval_sha256"]
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

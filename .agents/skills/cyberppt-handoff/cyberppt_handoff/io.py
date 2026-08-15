from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def json_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_inputs(foundation_dir: Path, semantic_dir: Path, outline_dir: Path) -> dict[str, dict[str, Any]]:
    required = {
        "structure": foundation_dir / "structure.json",
        "fact_base": foundation_dir / "fact-base.json",
        "normalized": semantic_dir / "normalized-facts.json",
        "concepts": semantic_dir / "concept-base.json",
        "relations": semantic_dir / "relation-graph.json",
        "argument": semantic_dir / "argument-chain.json",
        "semantic_report": semantic_dir / "semantic-report.json",
        "deck": outline_dir / "deck-brief.json",
        "page_plan": outline_dir / "page-plan.json",
        "outline_report": outline_dir / "outline-report.json",
    }
    payloads: dict[str, dict[str, Any]] = {}
    for name, path in required.items():
        if not path.is_file():
            raise FileNotFoundError(f"Required handoff input is missing: {path}")
        payloads[name] = read_json(path)
    planning_skill = Path(__file__).resolve().parents[2] / "ppt-outline-planning"
    if str(planning_skill) not in sys.path:
        sys.path.insert(0, str(planning_skill))
    from ppt_outline_planning.validate import validate_fact_coverage

    current_coverage = validate_fact_coverage(
        Path(semantic_dir), Path(outline_dir)
    )
    if current_coverage.get("status") != "ok":
        codes = ", ".join(
            str(item.get("code") or "OUTLINE_VALIDATION_FAILED")
            for item in current_coverage.get("errors") or []
        )
        raise ValueError(f"Current PPT outline fact coverage failed before handoff: {codes}")
    workpack = outline_dir / "outline-workpack.json"
    payloads["workpack"] = read_json(workpack) if workpack.is_file() else {}
    if payloads["semantic_report"].get("status") != "ok":
        raise ValueError("semantic-report.json must report status: ok")
    if payloads["outline_report"].get("status") != "ok":
        raise ValueError("outline-report.json must report status: ok")
    deck_status = payloads["deck"].get("editorial_authoring_status")
    plan_status = payloads["page_plan"].get("editorial_authoring_status")
    deck_mode = payloads["deck"].get("editorial_authoring_mode")
    plan_mode = payloads["page_plan"].get("editorial_authoring_mode")
    if "author_driven" in {deck_mode, plan_mode} or deck_status is not None or plan_status is not None:
        if deck_mode != "author_driven" or plan_mode != "author_driven" or deck_status != "author_edited" or plan_status != "author_edited":
            raise ValueError("OUTLINE_AUTHORING_INCOMPLETE: cyberppt-handoff requires an author_edited Outline")
    return payloads

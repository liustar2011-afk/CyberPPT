"""Durable ledger for human answers that affect downstream authoring."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DECISIONS_DIR = Path("workbench/decisions")
DECISIONS_ARTIFACT = DECISIONS_DIR / "user-decisions.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": "cyberppt.user_decisions.v1", "decisions": []}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"user decision ledger root must be an object: {path}")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        raise ValueError("user decision ledger decisions must be an array")
    return payload


def record_user_decision(
    project: Path,
    *,
    decision_id: str,
    question: str,
    answer: str,
    applies_to: list[str],
    source: str = "user",
    supersedes: list[str] | None = None,
) -> dict[str, Any]:
    """Upsert a decision and return the durable record.

    A decision is not considered consumed merely because its text is copied;
    downstream stages must list the decision id and its concrete effect.
    """

    project = project.expanduser().resolve()
    if not decision_id.strip() or not question.strip() or not answer.strip():
        raise ValueError("decision_id, question, and answer are required")
    if not applies_to or any(not str(item).strip() for item in applies_to):
        raise ValueError("applies_to must contain at least one non-empty field")
    path = project / DECISIONS_ARTIFACT
    payload = _load(path)
    payload.setdefault("schema", "cyberppt.user_decisions.v1")
    superseded_ids = {
        str(item).strip()
        for item in (supersedes or [])
        if str(item).strip() and str(item).strip() != decision_id
    }
    decisions = []
    for item in payload.get("decisions", []):
        if not isinstance(item, dict) or str(item.get("id") or "") == decision_id:
            continue
        if str(item.get("id") or "") in superseded_ids:
            item = {
                **item,
                "status": "superseded",
                "superseded_by": decision_id.strip(),
                "superseded_at": _utc_now(),
            }
        decisions.append(item)
    record = {
        "id": decision_id.strip(),
        "question": question.strip(),
        "answer": answer.strip(),
        "applies_to": [str(item).strip() for item in applies_to],
        "source": source.strip() or "user",
        "status": "approved",
        "recorded_at": _utc_now(),
    }
    decisions.append(record)
    payload["decisions"] = decisions
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return record


def load_user_decisions(project: Path) -> list[dict[str, Any]]:
    payload = _load(project.expanduser().resolve() / DECISIONS_ARTIFACT)
    return [item for item in payload.get("decisions", []) if isinstance(item, dict)]


def decision_consumption_issues(
    *,
    decisions: list[dict[str, Any]],
    consumed: list[dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Check that a downstream artifact records effect, not just a hash."""

    consumed_items = consumed if isinstance(consumed, list) else []
    by_id = {
        str(item.get("decision_id") or ""): item
        for item in consumed_items
        if isinstance(item, dict) and str(item.get("decision_id") or "")
    }
    issues: list[dict[str, str]] = []
    for decision in decisions:
        decision_id = str(decision.get("id") or "")
        if not decision_id or decision.get("status") != "approved":
            continue
        applies_to = {
            str(item).strip()
            for item in decision.get("applies_to", [])
            if str(item).strip()
        }
        if applies_to and not ({"storyline", "chapter_emphasis", "page_selection", "audience_concerns"} & applies_to):
            continue
        item = by_id.get(decision_id)
        if not item or not str(item.get("effect") or "").strip():
            issues.append({
                "code": "USER_DECISION_NOT_CONSUMED",
                "message": f"Approved user decision {decision_id} is not linked to a concrete downstream effect.",
                "retry_strategy": "record_decision_consumption",
            })
    return issues

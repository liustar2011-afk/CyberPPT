"""Strict model-output schemas for the Stage 1 source-analysis gate."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


_FENCED_JSON_RE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _strings(value: Any, field: str, *, required: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    result = tuple(_text(item, field) for item in value)
    if required and not result:
        raise ValueError(f"{field} must not be empty")
    return result


@dataclass(frozen=True)
class EvidenceCandidate:
    claim: str
    verbatim_support: str
    source_unit_ids: tuple[str, ...]
    numbers: tuple[str, ...]
    confidence: str
    caveat: str
    meaning: str
    visual: str

    @classmethod
    def from_payload(cls, payload: Any) -> "EvidenceCandidate":
        if not isinstance(payload, dict):
            raise ValueError("each evidence item must be an object")
        return cls(
            claim=_text(payload.get("claim"), "evidence.claim"),
            verbatim_support=_text(payload.get("verbatim_support"), "evidence.verbatim_support"),
            source_unit_ids=_strings(payload.get("source_unit_ids"), "evidence.source_unit_ids"),
            numbers=_strings(payload.get("numbers"), "evidence.numbers", required=False),
            confidence=_text(payload.get("confidence"), "evidence.confidence"),
            caveat=_text(payload.get("caveat"), "evidence.caveat"),
            meaning=_text(payload.get("meaning"), "evidence.meaning"),
            visual=_text(payload.get("visual"), "evidence.visual"),
        )


@dataclass(frozen=True)
class SourceAnalysisDraft:
    material_type: str
    reporting_task: str
    audience: str
    evidence: tuple[EvidenceCandidate, ...]
    storylines: tuple[dict[str, Any], ...]
    material_pool: tuple[dict[str, Any], ...]
    confirmation_questions: tuple[str, ...]


def _json_payload(text: str) -> dict[str, Any]:
    value = text.strip()
    match = _FENCED_JSON_RE.match(value)
    if match:
        value = match.group(1).strip()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"model output is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("model output must be a JSON object")
    return payload


def parse_source_analysis_output(text: str) -> SourceAnalysisDraft:
    payload = _json_payload(text)
    required = {
        "material_type",
        "reporting_task",
        "audience",
        "evidence",
        "storylines",
        "material_pool",
        "confirmation_questions",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise ValueError("model output is missing required fields: " + ", ".join(missing))
    unknown = sorted(set(payload) - required - {"schema"})
    if unknown:
        raise ValueError("model output contains unknown fields: " + ", ".join(unknown))

    evidence_payload = payload["evidence"]
    if not isinstance(evidence_payload, list):
        raise ValueError("evidence must be an array")
    storylines = payload["storylines"]
    material_pool = payload["material_pool"]
    if not isinstance(storylines, list) or any(not isinstance(item, dict) for item in storylines):
        raise ValueError("storylines must be an array of objects")
    if not isinstance(material_pool, list) or any(not isinstance(item, dict) for item in material_pool):
        raise ValueError("material_pool must be an array of objects")

    return SourceAnalysisDraft(
        material_type=_text(payload["material_type"], "material_type"),
        reporting_task=_text(payload["reporting_task"], "reporting_task"),
        audience=_text(payload["audience"], "audience"),
        evidence=tuple(EvidenceCandidate.from_payload(item) for item in evidence_payload),
        storylines=tuple(storylines),
        material_pool=tuple(material_pool),
        confirmation_questions=_strings(payload["confirmation_questions"], "confirmation_questions", required=False),
    )

"""Deterministic, reversible OCR text correction.

Only candidates emitted by the OCR evidence stage are considered.  This module
does not call a language model or a network service.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"configuration must be an object: {path}")
    return value


def _protected_spans(text: str, terms: list[str]) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    for term in terms:
        if not term:
            continue
        start = text.find(term)
        while start >= 0:
            spans.append((start, start + len(term), term))
            start = text.find(term, start + 1)
    return spans


def _agreement(candidate: dict[str, Any]) -> int:
    for key in ("agreement_count", "multi_scale_agreement", "scale_agreement"):
        if key in candidate:
            value = candidate[key]
            if isinstance(value, (list, tuple, set)):
                return len(value)
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
    scales = candidate.get("scales")
    if isinstance(scales, (list, tuple, set)):
        return len(scales)
    return 1


def correct_lines(
    lines: list[dict[str, Any]],
    *,
    policy_path: Path,
    protected_terms_path: Path,
) -> list[dict[str, Any]]:
    """Apply only high-confidence, policy-approved character candidates.

    The input records are copied.  Every record gets ``final_text`` and a
    correction decision; rejected decisions retain the exact observed string.
    """
    policy = _load(policy_path)
    protected_data = _load(protected_terms_path)
    terms = protected_data.get("terms", protected_data.get("protected_terms", []))
    if not isinstance(terms, list) or not all(isinstance(term, str) for term in terms):
        raise ValueError("protected terms must be a list of strings")
    threshold = float(policy.get("min_confidence", policy.get("confidence_threshold", 0.995)))
    min_agreement = int(policy.get("min_agreement", policy.get("minimum_scale_agreement", 1)))
    output: list[dict[str, Any]] = []
    for source in lines:
        line = dict(source)
        observed = str(source.get("observed_text", ""))
        text = observed
        changes: list[dict[str, Any]] = []
        blocked = _protected_spans(observed, terms)
        candidates = source.get("char_candidates", [])
        if not isinstance(candidates, list):
            candidates = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            old, new = str(candidate.get("from", "")), str(candidate.get("to", ""))
            if len(old) != 1 or len(new) != 1:
                continue
            try:
                confidence = float(candidate.get("confidence", 0.0))
            except (TypeError, ValueError):
                confidence = 0.0
            pos = candidate.get("index", candidate.get("position"))
            if pos is None:
                positions = [i for i, char in enumerate(text) if char == old]
                pos = positions[0] if len(positions) == 1 else -1
            try:
                pos = int(pos)
            except (TypeError, ValueError):
                pos = -1
            if confidence < threshold or _agreement(candidate) < min_agreement:
                continue
            if pos < 0 or pos >= len(text) or text[pos] != old:
                continue
            if any(start <= pos < end for start, end, _ in blocked):
                continue
            text = text[:pos] + new + text[pos + 1:]
            changes.append({"index": pos, "from": old, "to": new, "confidence": confidence})
        applied = bool(changes)
        line["final_text"] = text
        line["correction"] = {
            "applied": applied,
            "changes": changes,
            "reason": "accepted_policy_candidates" if applied else ("protected_term" if blocked else "threshold_not_met"),
            "confidence": min((item["confidence"] for item in changes), default=0.0),
            "reversible": True,
        }
        line["review_required"] = bool(candidates) and not applied
        output.append(line)
    return output

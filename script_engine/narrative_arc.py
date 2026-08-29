"""Source-constrained narrative-candidate divergence checks.

Adapted from addsumtech/slides_maker at commit
0b38732543f62920f094a18c1621992068a18f57, MIT License, Copyright (c) 2026
Leo-Lyu.  CyberPPT reads candidates directly from ``deck-plan.json`` and keeps
source argument focus separate from evidence investment.
"""
from __future__ import annotations

import itertools
import re
from typing import Any


OVERLAP_THRESHOLD = 0.60
EFFORT_THRESHOLD = 0.50
_CJK_CLASS = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af"
_CJK_RUN = re.compile("[" + _CJK_CLASS + "]+")
_STRUCTURAL_ROLES = frozenset(
    {"cover", "agenda", "contents", "divider", "chapter", "transition", "ending", "closing"}
)


def _norm_role(value: object) -> str:
    return re.sub(r"[\s/_]+", "-", str(value or "").strip().lower())


def cjk_aware_tokens(value: object) -> set[str]:
    """Tokenize Latin words and each contiguous CJK run into bigrams."""

    text = str(value or "").strip().lower()
    tokens = {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9\-']*", text)
        if len(token) > 1
    }
    for run in _CJK_RUN.findall(text):
        if len(run) == 1:
            tokens.add(run)
        tokens.update(run[index : index + 2] for index in range(len(run) - 1))
    return tokens


def text_overlap(left: object, right: object) -> float:
    left_tokens = cjk_aware_tokens(left)
    right_tokens = cjk_aware_tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / float(len(left_tokens | right_tokens))


def _required_text(candidate: dict[str, Any], key: str) -> str:
    value = str(candidate.get(key) or "").strip()
    if not value:
        raise ValueError(f"narrative candidate {candidate.get('id') or '?'} requires {key}")
    return value


def _features(candidate: dict[str, Any]) -> dict[str, Any]:
    roles = [
        role
        for raw in candidate.get("opening_roles") or []
        if (role := _norm_role(raw)) and role not in _STRUCTURAL_ROLES
    ]
    if not roles:
        raise ValueError(
            f"narrative candidate {candidate.get('id') or '?'} requires non-structural opening_roles"
        )
    return {
        "id": _required_text(candidate, "id"),
        "shape": _required_text(candidate, "shape"),
        "opening": tuple(roles[:3]),
        "ask": _required_text(candidate, "closing_ask"),
        "question": _required_text(candidate, "audience_question"),
        "objection": _required_text(candidate, "objection"),
        "argument_focus": {
            str(value).strip()
            for value in candidate.get("argument_focus_node_ids") or []
            if str(value).strip()
        },
        "evidence": {
            str(value).strip()
            for value in candidate.get("evidence_refs") or []
            if str(value).strip()
        },
    }


def _compare_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    opening_length = min(len(left["opening"]), len(right["opening"]))
    ask_overlap = text_overlap(left["ask"], right["ask"])
    question_overlap = text_overlap(left["question"], right["question"])
    objection_overlap = text_overlap(left["objection"], right["objection"])
    axes = {
        "shape": left["shape"] == right["shape"],
        "order": bool(opening_length) and left["opening"][:opening_length] == right["opening"][:opening_length],
        "ask": ask_overlap >= OVERLAP_THRESHOLD,
        "stance": question_overlap >= OVERLAP_THRESHOLD and objection_overlap >= OVERLAP_THRESHOLD,
    }
    matched = [name for name, matched in axes.items() if matched]
    return {
        "a": left["id"],
        "b": right["id"],
        "matched_axes": matched,
        "too_similar": len(matched) >= 3,
        "ask_overlap": round(ask_overlap, 3),
        "question_overlap": round(question_overlap, 3),
        "objection_overlap": round(objection_overlap, 3),
    }


def review_narrative_design(design: object) -> dict[str, Any]:
    """Review direct/competitive narrative design without writing another artifact."""

    if not isinstance(design, dict):
        return {"issues": ["NARRATIVE_DESIGN_MISSING"], "warnings": [], "pairs": []}
    mode = str(design.get("mode") or "").strip()
    candidates = [item for item in design.get("candidates") or [] if isinstance(item, dict)]
    if mode == "direct":
        return {"issues": [], "warnings": [], "pairs": [], "mode": mode}
    if mode != "competitive":
        return {"issues": ["NARRATIVE_DESIGN_MODE_INVALID"], "warnings": [], "pairs": []}
    issues: list[str] = []
    if not 2 <= len(candidates) <= 3:
        issues.append("NARRATIVE_CANDIDATE_COUNT: competitive mode requires 2-3 candidates")
    try:
        features = [_features(candidate) for candidate in candidates]
    except ValueError as exc:
        return {"issues": [f"NARRATIVE_CANDIDATE_INVALID: {exc}"], "warnings": [], "pairs": []}
    ids = [feature["id"] for feature in features]
    if len(ids) != len(set(ids)):
        issues.append("NARRATIVE_CANDIDATE_ID_DUPLICATE")
    pairs = [_compare_pair(left, right) for left, right in itertools.combinations(features, 2)]
    for pair in pairs:
        if pair["too_similar"]:
            issues.append(
                "NARRATIVE_CANDIDATES_TOO_SIMILAR: "
                f"{pair['a']} and {pair['b']} match {pair['matched_axes']}"
            )
    top_evidence = max((len(feature["evidence"]) for feature in features), default=0)
    if features and top_evidence == 0:
        issues.append("NARRATIVE_CANDIDATES_NO_EVIDENCE: every candidate has empty evidence_refs")
    for feature in features:
        if top_evidence and len(feature["evidence"]) < EFFORT_THRESHOLD * top_evidence:
            issues.append(
                "NARRATIVE_STRAWMAN_CANDIDATE: "
                f"{feature['id']} carries {len(feature['evidence'])} evidence refs versus {top_evidence}"
            )
        if not feature["argument_focus"]:
            issues.append(f"NARRATIVE_ARGUMENT_FOCUS_MISSING: {feature['id']}")
    chosen_id = str(design.get("chosen_id") or "").strip()
    if chosen_id not in ids:
        issues.append("NARRATIVE_CHOSEN_ID_UNKNOWN")
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "").strip()
        if candidate_id != chosen_id and not str(candidate.get("loss_reason") or "").strip():
            issues.append(f"NARRATIVE_LOSS_REASON_MISSING: {candidate_id or '?'}")
    return {"issues": issues, "warnings": [], "pairs": pairs, "mode": mode}


__all__ = ["cjk_aware_tokens", "review_narrative_design", "text_overlap"]

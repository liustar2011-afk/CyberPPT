"""Onscreen-Critic context and measurements; never generates presentation copy."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any


_VISIBLE_RE = re.compile(r"[一-鿿A-Za-z0-9]")
_DIMENSIONS = (
    "main_judgment_visibility",
    "ten_second_comprehension",
    "density",
    "repetition",
    "relation_visibility",
    "semantic_completeness",
)


def visible_character_count(onscreen: object) -> int:
    return len(_VISIBLE_RE.findall(_onscreen_text(onscreen)))


def _onscreen_text(onscreen: object) -> str:
    if not isinstance(onscreen, list):
        return ""
    parts: list[str] = []
    for module in onscreen:
        if not isinstance(module, dict):
            continue
        parts.extend(str(module.get(key) or "") for key in ("heading", "text"))
        parts.extend(str(item) for item in module.get("items") or [])
    return "\n".join(parts)


def repeated_visible_lines(onscreen: object) -> list[str]:
    lines = [line.strip() for line in _onscreen_text(onscreen).splitlines() if line.strip()]
    counts = Counter(lines)
    return sorted(line for line, count in counts.items() if count > 1)


def build_onscreen_critic_context(
    *,
    page: dict[str, Any],
    full_copy: str,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a page-level qualitative comparison input for the author agent."""

    return {
        "page_id": page.get("id"),
        "question": page.get("question"),
        "approved_message": page.get("message"),
        "page_role": page.get("page_role"),
        "beat": page.get("beat"),
        "full_copy": full_copy,
        "candidates": [
            {
                **candidate,
                "visible_characters": visible_character_count(candidate.get("onscreen")),
                "repeated_lines": repeated_visible_lines(candidate.get("onscreen")),
            }
            for candidate in candidates
        ],
        "review_dimensions": [
            "主判断可见性", "十秒理解", "文字密度", "信息重复", "关系可见性", "语义完整性",
        ],
        "rewrite_rule": "任一关键维度失败时重写整页信息组织，保留批准命题和来源边界",
    }


def record_candidate_score(
    candidate_id: str,
    scores: dict[str, int],
    *,
    rationale: str,
) -> dict[str, Any]:
    """Validate one transient qualitative score record without persisting it."""

    missing = [dimension for dimension in _DIMENSIONS if dimension not in scores]
    invalid = {
        dimension: value
        for dimension, value in scores.items()
        if dimension not in _DIMENSIONS or not isinstance(value, int) or not 1 <= value <= 5
    }
    if missing or invalid or not rationale.strip():
        raise ValueError(
            f"invalid onscreen score: missing={missing}, invalid={invalid}, rationale_required={not rationale.strip()}"
        )
    return {
        "candidate_id": candidate_id,
        "scores": dict(scores),
        "median": sorted(scores.values())[len(scores) // 2],
        "rationale": rationale.strip(),
    }


__all__ = [
    "build_onscreen_critic_context",
    "record_candidate_score",
    "repeated_visible_lines",
    "visible_character_count",
]

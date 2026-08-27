"""Deterministic Stage 02 capacity gate for locked body text."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class TextCapacityAssessment:
    item_count: int
    character_count: int
    root_count: int
    max_hierarchy_level: int
    canvas_area: int
    pressure_score: float
    status: str
    reasons: tuple[str, ...]


def assess_text_capacity(
    texts: Sequence[str],
    *,
    root_count: int,
    hierarchy_levels: Sequence[int],
    canvas: tuple[int, int],
) -> TextCapacityAssessment:
    """Assess capacity using several structural factors, never one threshold."""

    item_count = len(texts)
    character_count = sum(len(str(text)) for text in texts)
    max_level = max((int(level) for level in hierarchy_levels), default=1)
    width, height = canvas
    canvas_area = max(1, int(width) * int(height))
    area_factor = (2048 * 1024) / canvas_area
    score = area_factor * (
        item_count / 18.0
        + character_count / 420.0
        + max(1, root_count) / 8.0
        + max(0, max_level - 1) / 4.0
    )
    reasons: list[str] = []
    if item_count >= 24:
        reasons.append(f"locked_text_items={item_count}")
    if character_count >= 520:
        reasons.append(f"locked_text_characters={character_count}")
    if root_count >= 10:
        reasons.append(f"content_roots={root_count}")
    if max_level >= 5:
        reasons.append(f"hierarchy_depth={max_level}")
    # Hard-block only when combined pressure is high and at least two concrete
    # dimensions are independently elevated. This avoids a single long line
    # or a single deep hierarchy from becoming an arbitrary hard threshold.
    blocked = score >= 3.35 and len(reasons) >= 2
    return TextCapacityAssessment(
        item_count=item_count,
        character_count=character_count,
        root_count=root_count,
        max_hierarchy_level=max_level,
        canvas_area=canvas_area,
        pressure_score=round(score, 3),
        status="blocked" if blocked else "passed",
        reasons=tuple(reasons),
    )


def assert_text_capacity(
    texts: Sequence[str],
    *,
    root_count: int,
    hierarchy_levels: Sequence[int],
    canvas: tuple[int, int],
) -> TextCapacityAssessment:
    assessment = assess_text_capacity(
        texts,
        root_count=root_count,
        hierarchy_levels=hierarchy_levels,
        canvas=canvas,
    )
    if assessment.status == "blocked":
        raise ValueError(
            "STAGE02_TEXT_CAPACITY_EXCEEDED: locked body text exceeds the current canvas capacity; "
            "return to Stage 01 to revise approved onscreen text instead of allowing ImageGen to omit or rewrite it. "
            f"score={assessment.pressure_score}; " + ", ".join(assessment.reasons)
        )
    return assessment


__all__ = ["TextCapacityAssessment", "assess_text_capacity", "assert_text_capacity"]

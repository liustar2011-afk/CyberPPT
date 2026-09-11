"""Structured relationship-shape checks for Final Script."""

from __future__ import annotations

from typing import Any


def validate_relationship_shape(final_script: dict[str, Any]) -> list[str]:
    """Require every explicit relationship edge to declare both endpoints and action.

    This validator checks only the shape of author-declared relationship objects.
    Whether relationship wording is sufficiently visible in prose remains a
    Critic/advisory concern until it can be proven through structured provenance.
    """

    issues: list[str] = []
    for slide_index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{slide_index}"
        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                continue
            missing = [
                key
                for key in ("from", "to", "relation")
                if not str(relation.get(key) or "").strip()
            ]
            if missing:
                issues.append(
                    f"slides.{slide_index} ({slide_id}): "
                    "AUTHOR_RELATIONSHIP_NOT_MATERIALIZED: relationships[{}] is missing {}".format(
                        relation_index,
                        missing,
                    )
                )
    return issues

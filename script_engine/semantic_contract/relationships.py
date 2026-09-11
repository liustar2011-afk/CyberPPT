"""Structured relationship checks for Final Script.

This module owns deterministic relationship structure only:

- every AUTHOR-declared edge has ``from`` / ``to`` / ``relation``;
- when PLAN explicitly declares a topology contract, AUTHOR edges stay inside it.

Lexical relationship wording, visibility in prose and semantic similarity remain
Critic/advisory concerns and are deliberately excluded from this validator.
"""

from __future__ import annotations

from typing import Any


_HARD_SCOPED_RELATION_TYPES = frozenset({"sequence", "hierarchy", "matrix", "mixed"})


def _plan_pages(plan: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    payload = plan if isinstance(plan, dict) else {}
    return {
        str(page.get("id")): page
        for page in payload.get("pages") or []
        if isinstance(page, dict) and str(page.get("id") or "").strip()
    }


def _explicit_secondary_pairs(page: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for relation in page.get("secondary_relations") or []:
        if not isinstance(relation, dict):
            continue
        source = str(relation.get("from") or "").strip()
        target = str(relation.get("to") or "").strip()
        if source and target:
            pairs.add((source, target))
    return pairs


def _primary_pair(primary: dict[str, Any]) -> tuple[str, str] | None:
    source = str(primary.get("from") or "").strip()
    target = str(primary.get("to") or "").strip()
    return (source, target) if source and target else None


def _edge_authorized_by_plan(
    page: dict[str, Any],
    source: str,
    target: str,
) -> bool | None:
    """Return True/False for an explicit topology contract, else None.

    ``None`` means PLAN declared no relationship topology and therefore this
    validator has no structural authorization fact to enforce.
    """

    primary = page.get("primary_relation")
    primary = primary if isinstance(primary, dict) else None
    secondary_pairs = _explicit_secondary_pairs(page)
    if primary is None and not secondary_pairs:
        return None

    pair = (source, target)
    if pair in secondary_pairs:
        return True

    if primary is None:
        return False

    explicit_primary_pair = _primary_pair(primary)
    if explicit_primary_pair is not None and pair == explicit_primary_pair:
        return True

    relation_type = str(primary.get("type") or "").strip().lower()
    scope = {
        str(value).strip()
        for value in primary.get("scope") or []
        if str(value).strip()
    }
    if (
        relation_type in _HARD_SCOPED_RELATION_TYPES
        and source in scope
        and target in scope
    ):
        return True

    return False


def validate_relationship_shape(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None = None,
) -> list[str]:
    """Validate explicit relationship shape and PLAN topology authorization.

    The topology branch is opt-in: it runs only when the matching PLAN page
    explicitly supplies ``primary_relation`` or ``secondary_relations``. This
    preserves PLAN v2 lean's normal freedom while keeping historical structured
    topology contracts deterministic when they are present.
    """

    pages = _plan_pages(plan)
    issues: list[str] = []
    for slide_index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = str(slide.get("id") or f"#{slide_index}")
        page = pages.get(slide_id)
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
                continue

            if not isinstance(page, dict):
                continue
            source = str(relation.get("from") or "").strip()
            target = str(relation.get("to") or "").strip()
            authorized = _edge_authorized_by_plan(page, source, target)
            if authorized is False:
                issues.append(
                    f"slides.{slide_index} ({slide_id}): AUTHOR_RELATIONSHIP_OUTSIDE_PLAN_TOPOLOGY: "
                    f"relationships[{relation_index}] ({source} → {target}) is not declared by "
                    "the page's primary_relation/secondary_relations topology"
                )
    return issues

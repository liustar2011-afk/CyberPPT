"""Evidence vocabulary and shared source/page helper functions."""

from __future__ import annotations

import re

EVIDENCE_TYPE_TO_CLAIM_ROLE = {
    "F": "fact",
    "J": "judgment",
    "R": "recommendation",
    "B": "boundary",
    "U": "unresolved",
}
PRIMARY_PROOF_DIRECTION_LIMIT = 3
BOUNDARY_PRIMARY_ARGUMENT_ROLES = frozenset(
    {"positioning", "scope", "assurance", "decision"}
)


def dict_items(payload: dict[str, object], field: str) -> list[dict[str, object]]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def string_list(item: dict[str, object], field: str) -> list[str]:
    raw = item.get(field)
    if not isinstance(raw, list):
        return []
    return [str(value) for value in raw if str(value)]


def normalized_similarity(left: object, right: object) -> float:
    def tokens(value: object) -> set[str]:
        compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value or "")).lower()
        if len(compact) < 3:
            return {compact} if compact else set()
        return {compact[index : index + 3] for index in range(len(compact) - 2)}

    left_tokens = tokens(left)
    right_tokens = tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def text_value(value: object) -> str:
    return str(value or "").strip()


def topic_similarity(left: object, right: object) -> float:
    def bigrams(value: object) -> set[str]:
        compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value or "")).lower()
        if len(compact) < 2:
            return {compact} if compact else set()
        return {compact[index : index + 2] for index in range(len(compact) - 1)}

    left_tokens = bigrams(left)
    right_tokens = bigrams(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def theme_similarity(page: dict[str, object], claim: object) -> float:
    theme_fields = (
        page.get("page_job"),
        page.get("business_question"),
        page.get("main_message"),
    )
    return max(
        (topic_similarity(claim, field) for field in theme_fields if text_value(field)),
        default=0.0,
    )


def dependency_cycle(
    dependencies: dict[str, list[str]],
) -> tuple[tuple[str, str], ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(page_id: str) -> tuple[tuple[str, str], ...]:
        if page_id in visited:
            return ()
        if page_id in visiting:
            start = path.index(page_id)
            cycle = path[start:] + [page_id]
            return tuple(zip(cycle, cycle[1:]))
        visiting.add(page_id)
        path.append(page_id)
        for prerequisite in dependencies.get(page_id, []):
            cycle = visit(prerequisite)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(page_id)
        visited.add(page_id)
        return ()

    for candidate in sorted(dependencies):
        cycle = visit(candidate)
        if cycle:
            return cycle
    return ()


__all__ = [
    "BOUNDARY_PRIMARY_ARGUMENT_ROLES",
    "EVIDENCE_TYPE_TO_CLAIM_ROLE",
    "PRIMARY_PROOF_DIRECTION_LIMIT",
    "dependency_cycle",
    "dict_items",
    "normalized_similarity",
    "string_list",
    "text_value",
    "theme_similarity",
    "topic_similarity",
]

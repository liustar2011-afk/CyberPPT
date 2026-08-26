"""Low-level text helpers shared by script-quality rule modules."""

from __future__ import annotations

import re
import unicodedata


def _compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def normalized_tokens(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"S\d{3}", " ", normalized)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    compact = "".join(normalized.split())
    if len(compact) < 3:
        return tuple(compact)
    return tuple(
        compact[index : index + 3]
        for index in range(len(compact) - 2)
    )


def text_similarity(left: str, right: str) -> float:
    left_set = set(normalized_tokens(left))
    right_set = set(normalized_tokens(right))
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _source_statement_overlap(statement: str, authored: str, size: int = 4) -> float:
    """Measure factual phrase survival without requiring verbatim prose.

    Asymmetric containment, not a symmetric similarity: it answers "how much
    of `statement`'s own content survives inside `authored`", so it stays
    meaningful even when `authored` is much longer than `statement` (unlike
    ``text_similarity``, which dilutes toward zero in that case). Lives here
    rather than in source_coverage.py so both source_coverage and onscreen
    can import it without an onscreen -> source_coverage -> text_rules ->
    onscreen cycle.
    """

    def shingles(value: str) -> set[str]:
        compact = re.sub(r"[^0-9A-Za-z一-鿿]", "", value or "")
        return {
            compact[index : index + size]
            for index in range(max(0, len(compact) - size + 1))
            if compact[index : index + size]
        }

    source = shingles(statement)
    if not source:
        return 1.0
    return len(source & shingles(authored)) / len(source)

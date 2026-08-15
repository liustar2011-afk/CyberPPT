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

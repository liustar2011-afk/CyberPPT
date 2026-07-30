from __future__ import annotations

import re
from collections.abc import Sequence

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import ScriptSlide, SemanticCoverageItem, SourceItem


def _normalize(text: str) -> str:
    value = re.sub(r"[\s，。；：、,.!?！？（）()《》〈〉\[\]【】]", "", text).lower()
    for old, new in {"不得": "不", "不可": "不", "只能": "", "开展": "", "进行": ""}.items():
        value = value.replace(old, new)
    return value


def _shingles(text: str, size: int = 2) -> set[str]:
    normalized = _normalize(text)
    if len(normalized) < size:
        return {normalized} if normalized else set()
    return {normalized[index : index + size] for index in range(len(normalized) - size + 1)}


def _source_recall(source: str, candidate: str) -> float:
    source_set = _shingles(source)
    candidate_set = _shingles(candidate)
    return len(source_set & candidate_set) / len(source_set) if source_set else 0.0


def _dice(left: str, right: str) -> float:
    left_set = _shingles(left)
    right_set = _shingles(right)
    if not left_set or not right_set:
        return 0.0
    return 2 * len(left_set & right_set) / (len(left_set) + len(right_set))


def _similarity_matrix(left: Sequence[str], right: Sequence[str]):
    if not left or not right:
        return None
    matrix = TfidfVectorizer(analyzer="char", ngram_range=(2, 4), min_df=1, sublinear_tf=True).fit_transform(
        list(left) + list(right)
    )
    return cosine_similarity(matrix[: len(left)], matrix[len(left) :])


def semantic_coverage(
    source_items: Sequence[SourceItem],
    slides: Sequence[ScriptSlide],
    covered_threshold: float,
    weak_threshold: float,
) -> list[SemanticCoverageItem]:
    if not source_items:
        return []
    if not slides:
        return [
            SemanticCoverageItem(item.source_id, item.importance, item.content, "missing", None, 0.0)
            for item in source_items
        ]
    source_texts = [item.content for item in source_items]
    slide_texts = [slide.content for slide in slides]
    matrix = _similarity_matrix(source_texts, slide_texts)
    results: list[SemanticCoverageItem] = []
    for index, item in enumerate(source_items):
        row = matrix[index]
        scores = [max(float(row[j]), 0.8 * _source_recall(item.content, slide_texts[j])) for j in range(len(slides))]
        best_index = max(range(len(scores)), key=scores.__getitem__)
        score = scores[best_index]
        status = "covered" if score >= covered_threshold else "weak" if score >= weak_threshold else "missing"
        results.append(
            SemanticCoverageItem(item.source_id, item.importance, item.content, status, slides[best_index].number, round(score, 4))
        )
    return results


def slide_similarity(slides: Sequence[ScriptSlide]) -> list[tuple[int, int, float]]:
    results: list[tuple[int, int, float]] = []
    for left_index, left in enumerate(slides):
        for right in slides[left_index + 1 :]:
            results.append((left.number, right.number, _dice(left.content, right.content)))
    return results

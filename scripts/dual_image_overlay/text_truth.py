from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


_IGNORED_TEXT_RE = re.compile(r"[\s,，。:：;；、（）()【】\[\]\"'“”‘’]+")
_AMBIGUITY_MARGIN = 0.03
_MIN_CONTAINMENT_LENGTH = 4
_SHORT_TOKEN_MAX_LENGTH = 2
_SUBSTRING_MATCH_THRESHOLD = 0.82


def normalize_text(text: str) -> str:
    return _IGNORED_TEXT_RE.sub("", str(text)).lower()


def _line_lengths(lines: list[str]) -> list[int]:
    return [len(normalize_text(line)) for line in lines]


def _is_line_structure_punctuation(char: str) -> bool:
    return not normalize_text(char)


def _split_script_text_to_ocr_lines(script_text: str, ocr_lines: list[str]) -> str:
    original = str(script_text)
    if len(ocr_lines) <= 1:
        return original

    script_lines = [line for line in original.splitlines() if line.strip()]
    if len(script_lines) == len(ocr_lines):
        return original

    lengths = _line_lengths(ocr_lines)
    lines: list[str] = []
    cursor = 0

    for index, length in enumerate(lengths):
        if index == len(lengths) - 1:
            line = original[cursor:]
        else:
            consumed = 0
            line_start = cursor
            while cursor < len(original) and consumed < length:
                char = original[cursor]
                cursor += 1
                if not _is_line_structure_punctuation(char):
                    consumed += 1

            while cursor < len(original) and _is_line_structure_punctuation(original[cursor]):
                cursor += 1

            line = original[line_start:cursor]
        line = line.replace("\r\n", "").replace("\n", "").replace("\r", "")
        if line:
            lines.append(line)
    return "\n".join(lines)


def _similarity(ocr_text: str, script_text: str) -> float:
    ocr_key = normalize_text(ocr_text)
    script_key = normalize_text(script_text)
    if not ocr_key or not script_key:
        return 0.0

    score = SequenceMatcher(None, ocr_key, script_key).ratio()
    if ocr_key in script_key or script_key in ocr_key:
        containment = min(len(ocr_key), len(script_key)) / max(len(ocr_key), len(script_key))
        score = max(score, containment)
    return score


def _normalized_chars_with_spans(text: str) -> tuple[str, list[tuple[int, int]]]:
    normalized_chars: list[str] = []
    spans: list[tuple[int, int]] = []
    for index, char in enumerate(str(text)):
        normalized = normalize_text(char)
        if not normalized:
            continue
        for normalized_char in normalized:
            normalized_chars.append(normalized_char)
            spans.append((index, index + 1))
    return "".join(normalized_chars), spans


def _substring_candidates(
    ocr_text: str,
    script_truth_lines: list[str],
) -> list[tuple[str, str, float, int, int, bool]]:
    ocr_key = normalize_text(ocr_text)
    if not ocr_key:
        return []

    candidates: list[tuple[str, str, float, int, int, bool]] = []
    for line in script_truth_lines:
        script_key, spans = _normalized_chars_with_spans(line)
        if not script_key:
            continue

        start = script_key.find(ocr_key)
        while start >= 0:
            end = start + len(ocr_key)
            original_start = spans[start][0]
            original_end = spans[end - 1][1]
            candidates.append((line, line[original_start:original_end], 1.0, start, end, True))
            start = script_key.find(ocr_key, start + 1)

        if candidates and len(ocr_key) < _MIN_CONTAINMENT_LENGTH:
            continue

        if len(ocr_key) >= _MIN_CONTAINMENT_LENGTH and ocr_key not in script_key:
            best: tuple[str, str, float, int, int, bool] | None = None
            for window_length in range(max(1, len(ocr_key) - 1), len(ocr_key) + 2):
                if window_length > len(script_key):
                    continue
                for start_index in range(0, len(script_key) - window_length + 1):
                    end_index = start_index + window_length
                    candidate_key = script_key[start_index:end_index]
                    score = SequenceMatcher(None, ocr_key, candidate_key).ratio()
                    if score < _SUBSTRING_MATCH_THRESHOLD:
                        continue
                    original_start = spans[start_index][0]
                    original_end = spans[end_index - 1][1]
                    candidate = (
                        line,
                        line[original_start:original_end],
                        score,
                        start_index,
                        end_index,
                        False,
                    )
                    if best is None or score > best[2]:
                        best = candidate
            if best is not None:
                candidates.append(best)

    return sorted(candidates, key=lambda item: item[2], reverse=True)


def _best_script_substring_match(
    ocr_text: str,
    script_truth_lines: list[str],
) -> tuple[str, str, float, str | None] | None:
    ocr_key = normalize_text(ocr_text)
    if len(ocr_key) < _MIN_CONTAINMENT_LENGTH and len(ocr_key) > _SHORT_TOKEN_MAX_LENGTH:
        return None

    candidates = _substring_candidates(ocr_text, script_truth_lines)
    if not candidates:
        return None

    best_line, best_span, best_score, _, _, best_exact = candidates[0]
    same_score_candidates = [
        candidate
        for candidate in candidates
        if abs(candidate[2] - best_score) <= _AMBIGUITY_MARGIN
    ]
    unique_best_span = {
        (candidate[0], candidate[1], candidate[3], candidate[4])
        for candidate in same_score_candidates
    }
    if len(unique_best_span) > 1:
        if len(ocr_key) < _MIN_CONTAINMENT_LENGTH:
            return best_line, best_span, best_score, "script_truth_containment_ambiguous"
        return best_line, best_span, best_score, "script_truth_match_ambiguous"
    if not best_exact and len(same_score_candidates) > 1:
        return best_line, best_span, best_score, "script_truth_containment_ambiguous"
    return best_line, best_span, best_score, None


def _rank_script_matches(ocr_text: str, script_truth_lines: list[str]) -> list[tuple[str, float]]:
    ranked: list[tuple[str, float]] = []
    for line in script_truth_lines:
        if not normalize_text(line):
            continue
        ranked.append((line, _similarity(ocr_text, line)))
    return sorted(ranked, key=lambda item: item[1], reverse=True)


def _truth_payload(
    *,
    status: str,
    source: str,
    matched_text: str,
    similarity: float,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "source": source,
        "matched_text": matched_text,
        "similarity": round(similarity, 3),
    }
    if reason:
        payload["reason"] = reason
    return payload


def verify_text_blocks_against_script(
    text_blocks: list[dict[str, Any]],
    script_truth_lines: list[str],
    *,
    match_threshold: float = 0.62,
) -> list[dict[str, Any]]:
    verified: list[dict[str, Any]] = []
    for block in text_blocks:
        current = dict(block)
        ocr_text = str(block.get("ocr_text") or block.get("text") or "")
        ocr_lines = [line for line in ocr_text.splitlines() if line.strip()]
        substring_match = _best_script_substring_match(ocr_text, script_truth_lines)
        if substring_match is not None:
            matched_line, matched_span, span_score, ambiguity_reason = substring_match
            if ambiguity_reason:
                current["final_text"] = ocr_text
                current["truth"] = _truth_payload(
                    status="review_required",
                    source="ocr_candidate",
                    matched_text=matched_line,
                    similarity=span_score,
                    reason=ambiguity_reason,
                )
            else:
                current["final_text"] = _split_script_text_to_ocr_lines(matched_span, ocr_lines)
                current["truth"] = _truth_payload(
                    status="script_verified",
                    source="script_truth",
                    matched_text=matched_line,
                    similarity=span_score,
                )
            verified.append(current)
            continue

        ranked = _rank_script_matches(ocr_text, script_truth_lines)
        best_text, best_score = ranked[0] if ranked else ("", 0.0)
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        if not best_text:
            current["final_text"] = ocr_text
            current["truth"] = _truth_payload(
                status="review_required",
                source="ocr_candidate",
                matched_text="",
                similarity=0.0,
                reason="script_truth_missing",
            )
        elif best_score < match_threshold:
            current["final_text"] = ocr_text
            current["truth"] = _truth_payload(
                status="review_required",
                source="ocr_candidate",
                matched_text=best_text,
                similarity=best_score,
                reason="script_truth_match_below_threshold",
            )
        elif second_score >= match_threshold and best_score - second_score <= _AMBIGUITY_MARGIN:
            current["final_text"] = ocr_text
            current["truth"] = _truth_payload(
                status="review_required",
                source="ocr_candidate",
                matched_text=best_text,
                similarity=best_score,
                reason="script_truth_match_ambiguous",
            )
        else:
            current["final_text"] = _split_script_text_to_ocr_lines(best_text, ocr_lines)
            current["truth"] = _truth_payload(
                status="script_verified",
                source="script_truth",
                matched_text=best_text,
                similarity=best_score,
            )

        verified.append(current)
    return verified

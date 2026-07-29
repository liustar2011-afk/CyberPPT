"""Read-only diagnostics for compiled ImageGen prompts.

This module intentionally does not participate in prompt rendering.  It measures
the compiled result so diagnostics can be introduced without changing existing
ImageGen output.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


_EXACT_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:亿|万|千|百)?(?:千瓦时|千瓦|小时|天|月|年))"
)
_CONTENT_START = "【内容锁定】"
_CONTENT_END = "【构图指令】"
_COMPOSITION_START = "[Mandatory composition guidance]"
_CONTENT_FIRST_START = "【页面任务｜"
_CONTENT_FIRST_ENDS = (
    "【结论句要求｜",
    "【结论表达要求｜",
    "【内容与视觉要求｜",
    "【输出与风格｜",
)
_SEMANTIC_RULE_GROUPS: dict[str, tuple[str, ...]] = {
    "detached_text_zone": (
        "detached full-height text column",
        "detached left/right column",
        "text rail",
        "separate text zone plus image zone",
        "separate text zone plus photo zone",
    ),
    "equal_card_wall": (
        "equal card wall",
        "equal capability cards",
        "equal image cards",
    ),
    "generic_scene": (
        "generic industry scene",
        "one generic office",
        "one generic scene",
        "unrelated decorative scene",
        "decorative industry photo",
    ),
}


@dataclass(frozen=True)
class PromptMetrics:
    total_chars: int
    page_content_chars: int
    global_rule_chars: int
    page_specific_ratio: float
    duplicate_rules: tuple[str, ...]
    conflicts: tuple[str, ...]
    onscreen_chars: int
    exact_number_count: int
    locked_text_preserved: bool
    exact_facts_preserved: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PagePromptDiagnostics:
    page_id: str
    title: str
    metrics: PromptMetrics
    build_metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "page_id": self.page_id,
            "title": self.title,
            **self.metrics.to_dict(),
            "duplicate_rule_count": len(self.metrics.duplicate_rules),
            "conflict_count": len(self.metrics.conflicts),
        }
        if self.build_metadata is not None:
            payload["build_metadata"] = self.build_metadata
        return payload


@dataclass(frozen=True)
class GeneratedTextFidelity:
    locked_effective_chars: int
    ocr_effective_chars: int
    character_retention_ratio: float
    text_coverage_ratio: float
    required_phrase_count: int
    missing_phrases: tuple[str, ...]
    exact_number_count: int
    missing_numbers: tuple[str, ...]
    passed: bool
    issue_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _visible_text_key(text: str) -> str:
    return "".join(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text)).lower()


def _char_ngrams(text: str, size: int = 3) -> set[str]:
    key = _visible_text_key(text)
    if len(key) < size:
        return {key} if key else set()
    return {key[index : index + size] for index in range(len(key) - size + 1)}


def _locked_required_phrases(locked_text: str) -> tuple[str, ...]:
    lines = [
        re.sub(r"^\s*[-*•]\s*", "", line).strip("* ").strip()
        for line in locked_text.splitlines()
        if line.strip()
    ]
    lead = lines[0] if lines else ""
    module_titles = re.findall(r"\*\*(.+?)\*\*", locked_text)
    return tuple(dict.fromkeys(part for part in (lead, *module_titles) if part))


def analyze_generated_text_fidelity(
    locked_text: str,
    ocr_text: str,
    *,
    required_phrases: Iterable[str] = (),
    minimum_ratio: float = 0.85,
) -> GeneratedTextFidelity:
    """Compare existing OCR output with the locked ImageGen text contract."""

    locked_key = _visible_text_key(locked_text)
    ocr_key = _visible_text_key(ocr_text)
    locked_ngrams = _char_ngrams(locked_text)
    ocr_ngrams = _char_ngrams(ocr_text)
    retention = (
        min(len(ocr_key) / len(locked_key), 1.0)
        if locked_key
        else 1.0
    )
    coverage = (
        len(locked_ngrams & ocr_ngrams) / len(locked_ngrams)
        if locked_ngrams
        else 1.0
    )
    phrases = tuple(
        dict.fromkeys(
            str(item).strip()
            for item in (
                *tuple(required_phrases),
                *_locked_required_phrases(locked_text),
            )
            if str(item).strip()
        )
    )
    missing_phrases = tuple(
        phrase
        for phrase in phrases
        if _visible_text_key(phrase) not in ocr_key
    )
    numbers = tuple(dict.fromkeys(_EXACT_NUMBER_RE.findall(locked_text)))
    missing_numbers = tuple(value for value in numbers if value not in ocr_text)
    issues: list[str] = []
    if retention < minimum_ratio:
        issues.append("generated_text_character_retention_low")
    if coverage < minimum_ratio:
        issues.append("generated_text_coverage_low")
    if missing_phrases:
        issues.append("generated_text_required_phrase_missing")
    if missing_numbers:
        issues.append("generated_text_exact_number_missing")
    return GeneratedTextFidelity(
        locked_effective_chars=len(locked_key),
        ocr_effective_chars=len(ocr_key),
        character_retention_ratio=round(retention, 4),
        text_coverage_ratio=round(coverage, 4),
        required_phrase_count=len(phrases),
        missing_phrases=missing_phrases,
        exact_number_count=len(numbers),
        missing_numbers=missing_numbers,
        passed=not issues,
        issue_codes=tuple(issues),
    )


def write_generated_text_fidelity(
    path: Path,
    *,
    page_id: str,
    locked_text: str,
    ocr_text: str,
    required_phrases: Iterable[str] = (),
    minimum_ratio: float = 0.85,
) -> Path:
    result = analyze_generated_text_fidelity(
        locked_text,
        ocr_text,
        required_phrases=required_phrases,
        minimum_ratio=minimum_ratio,
    )
    payload = {
        "schema": "cyberppt.imagegen_text_fidelity.v1",
        "page_id": page_id,
        "minimum_ratio": minimum_ratio,
        "result": result.to_dict(),
        "next_action": (
            "accept"
            if result.passed
            else "retry_once_with_same_prompt_and_stronger_text_preservation_no_reference_image"
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _section(text: str, start: str, end: str | None = None) -> str:
    if start not in text:
        return ""
    value = text.split(start, 1)[1]
    if end and end in value:
        value = value.split(end, 1)[0]
    return value.strip()


def _content_first_page_section(text: str) -> str:
    """Return page-specific content from a content-first-v1 prompt."""

    if _CONTENT_FIRST_START not in text:
        return ""
    value = text.split(_CONTENT_FIRST_START, 1)[1]
    end_positions = [
        value.index(marker)
        for marker in _CONTENT_FIRST_ENDS
        if marker in value
    ]
    if end_positions:
        value = value[: min(end_positions)]
    return value.strip()


def _meaningful_chars(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _normalized_rule(line: str) -> str:
    normalized = line.strip().lower()
    normalized = re.sub(r"^[-*]\s*", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" .;；。")


def _exact_duplicate_rules(prompt: str) -> tuple[str, ...]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for line in prompt.splitlines():
        normalized = _normalized_rule(line)
        if len(normalized) < 24:
            continue
        if normalized in seen and seen[normalized] not in duplicates:
            duplicates.append(seen[normalized])
        else:
            seen[normalized] = line.strip()
    normalized_lines = [_normalized_rule(line) for line in prompt.splitlines()]
    for rule_id, markers in _SEMANTIC_RULE_GROUPS.items():
        matching_lines = {
            index
            for index, line in enumerate(normalized_lines)
            if any(marker in line for marker in markers)
        }
        if len(matching_lines) >= 2:
            duplicates.append(f"semantic:{rule_id}")
    return tuple(duplicates)


def _known_conflicts(prompt: str) -> tuple[str, ...]:
    conflicts: list[str] = []
    lower = prompt.lower()
    if "remain editable" in lower or "保持可编辑" in prompt:
        conflicts.append("editable_text_in_bitmap")

    requires_exact_text = (
        "locked wording is exact" in lower
        or "不得近义替换" in prompt
        or "do not delete, summarize, paraphrase" in lower
    )
    allows_text_compression = (
        "允许根据画面容量压缩、取舍和重组文字" in prompt
        or bool(
            re.search(
                r"\b(?:may|can)\s+(?:compress|shorten|summarize|paraphrase)\b",
                lower,
            )
        )
    )
    if requires_exact_text and allows_text_compression:
        conflicts.append("locked_text_vs_allowed_compression")

    locks_to_onscreen = (
        "only render 上屏文字" in prompt
        or "only render the locked on-screen text" in lower
        or "正文文字以“上屏文字”为准" in prompt
    )
    allows_auxiliary_text = (
        "auxiliary semantic imagery may use" in lower
        or "辅助语义图像可以使用" in prompt
        or "辅助图像可生成" in prompt
    )
    if locks_to_onscreen and allows_auxiliary_text:
        conflicts.append("extra_auxiliary_text_vs_locked_text")
    return tuple(conflicts)


def analyze_prompt(prompt: str, *, onscreen_text: str = "") -> PromptMetrics:
    """Measure a compiled prompt without modifying it."""

    content = _section(prompt, _CONTENT_START, _CONTENT_END)
    if not content:
        content = _content_first_page_section(prompt)
    composition = ""
    if _COMPOSITION_START in prompt and _CONTENT_START in prompt:
        composition = prompt.split(_COMPOSITION_START, 1)[1].split(_CONTENT_START, 1)[0]

    page_specific_chars = _meaningful_chars(content) + _meaningful_chars(composition)
    total_chars = _meaningful_chars(prompt)
    global_rule_chars = max(total_chars - page_specific_chars, 0)
    ratio = round(page_specific_chars / total_chars, 4) if total_chars else 0.0
    onscreen = onscreen_text.strip()
    normalized_prompt = re.sub(r"\s+", "", prompt)
    locked_lines = [
        re.sub(r"\s+", "", line).strip("-*•")
        for line in onscreen.splitlines()
        if re.sub(r"\s+", "", line).strip("-*•")
    ]
    exact_facts = _EXACT_NUMBER_RE.findall(onscreen)

    return PromptMetrics(
        total_chars=total_chars,
        page_content_chars=page_specific_chars,
        global_rule_chars=global_rule_chars,
        page_specific_ratio=ratio,
        duplicate_rules=_exact_duplicate_rules(prompt),
        conflicts=_known_conflicts(prompt),
        onscreen_chars=_meaningful_chars(onscreen),
        exact_number_count=len(exact_facts),
        locked_text_preserved=all(line in normalized_prompt for line in locked_lines),
        exact_facts_preserved=all(value in prompt for value in exact_facts),
    )


def write_batch_diagnostics(
    path: Path,
    pages: Iterable[PagePromptDiagnostics],
    *,
    batch_name: str,
) -> Path:
    """Write a stable, reviewable JSON diagnostics report."""

    page_list = list(pages)
    prompt_chars = [page.metrics.total_chars for page in page_list]
    ratios = [page.metrics.page_specific_ratio for page in page_list]
    payload = {
        "schema": "cyberppt.imagegen_prompt_diagnostics.v2",
        "batch_name": batch_name,
        "mode": "warning_only",
        "summary": {
            "page_count": len(page_list),
            "average_prompt_chars": (
                round(sum(prompt_chars) / len(prompt_chars), 2) if prompt_chars else 0
            ),
            "average_page_specific_ratio": (
                round(sum(ratios) / len(ratios), 4) if ratios else 0.0
            ),
            "pages_with_duplicates": sum(
                bool(page.metrics.duplicate_rules) for page in page_list
            ),
            "pages_with_conflicts": sum(bool(page.metrics.conflicts) for page in page_list),
        },
        "pages": [page.to_dict() for page in page_list],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def compare_page_diagnostics(
    baseline: PagePromptDiagnostics,
    candidate: PagePromptDiagnostics,
) -> dict[str, object]:
    """Compare two compiler results for the same page."""

    if baseline.page_id != candidate.page_id:
        raise ValueError(
            f"cannot compare different pages: {baseline.page_id} != {candidate.page_id}"
        )
    old = baseline.metrics
    new = candidate.metrics
    return {
        "page_id": baseline.page_id,
        "title": baseline.title,
        "baseline": baseline.to_dict(),
        "candidate": candidate.to_dict(),
        "delta": {
            "total_chars": new.total_chars - old.total_chars,
            "global_rule_chars": new.global_rule_chars - old.global_rule_chars,
            "page_specific_ratio": round(
                new.page_specific_ratio - old.page_specific_ratio,
                4,
            ),
            "duplicate_rule_count": (
                len(new.duplicate_rules) - len(old.duplicate_rules)
            ),
            "conflict_count": len(new.conflicts) - len(old.conflicts),
            "onscreen_chars_preserved": new.onscreen_chars == old.onscreen_chars,
            "locked_text_preserved": new.locked_text_preserved,
            "exact_facts_preserved": new.exact_facts_preserved,
        },
    }


def write_compiler_comparison(
    path: Path,
    comparisons: Iterable[
        tuple[PagePromptDiagnostics, PagePromptDiagnostics]
    ],
    *,
    batch_name: str,
) -> Path:
    rows = [compare_page_diagnostics(old, new) for old, new in comparisons]
    payload = {
        "schema": "cyberppt.imagegen_prompt_compiler_comparison.v1",
        "batch_name": batch_name,
        "mode": "warning_only",
        "summary": {
            "page_count": len(rows),
            "pages_with_fewer_duplicates": sum(
                row["delta"]["duplicate_rule_count"] < 0 for row in rows
            ),
            "pages_with_fewer_conflicts": sum(
                row["delta"]["conflict_count"] < 0 for row in rows
            ),
            "pages_preserving_locked_text": sum(
                row["delta"]["locked_text_preserved"] for row in rows
            ),
            "pages_preserving_exact_facts": sum(
                row["delta"]["exact_facts_preserved"] for row in rows
            ),
        },
        "pages": rows,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path

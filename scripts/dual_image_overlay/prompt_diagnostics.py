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
from typing import Iterable


_EXACT_NUMBER_RE = re.compile(
    r"(?<![A-Za-z])(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?(?:亿|万|千|百)?(?:千瓦时|千瓦|小时|天|月|年))"
)
_CONTENT_START = "【内容锁定】"
_CONTENT_END = "【构图指令】"
_COMPOSITION_START = "[Mandatory composition guidance]"
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

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class PagePromptDiagnostics:
    page_id: str
    title: str
    metrics: PromptMetrics

    def to_dict(self) -> dict[str, object]:
        return {
            "page_id": self.page_id,
            "title": self.title,
            **self.metrics.to_dict(),
            "duplicate_rule_count": len(self.metrics.duplicate_rules),
            "conflict_count": len(self.metrics.conflicts),
        }


def _section(text: str, start: str, end: str | None = None) -> str:
    if start not in text:
        return ""
    value = text.split(start, 1)[1]
    if end and end in value:
        value = value.split(end, 1)[0]
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
    composition = ""
    if _COMPOSITION_START in prompt and _CONTENT_START in prompt:
        composition = prompt.split(_COMPOSITION_START, 1)[1].split(_CONTENT_START, 1)[0]

    page_specific_chars = _meaningful_chars(content) + _meaningful_chars(composition)
    total_chars = _meaningful_chars(prompt)
    global_rule_chars = max(total_chars - page_specific_chars, 0)
    ratio = round(page_specific_chars / total_chars, 4) if total_chars else 0.0
    onscreen = onscreen_text.strip()

    return PromptMetrics(
        total_chars=total_chars,
        page_content_chars=page_specific_chars,
        global_rule_chars=global_rule_chars,
        page_specific_ratio=ratio,
        duplicate_rules=_exact_duplicate_rules(prompt),
        conflicts=_known_conflicts(prompt),
        onscreen_chars=_meaningful_chars(onscreen),
        exact_number_count=len(_EXACT_NUMBER_RE.findall(onscreen)),
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
        "schema": "cyberppt.imagegen_prompt_diagnostics.v1",
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

"""Shared policy for separating page content from prompt-processing metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


FORBIDDEN_TEXT_PATTERNS: dict[str, tuple[str, ...]] = {
    "process_instruction": (
        r"本页说明",
        r"生成要求",
        r"布局说明",
        r"构图说明",
        r"请将",
        r"请生成",
    ),
    "review_note": (
        r"待核对",
        r"仅供参考",
        r"核对内容",
        r"审阅意见",
        r"^\s*注[:：]",
        r"来源说明",
        r"来源位置",
    ),
    "placeholder": (
        r"占位",
        r"placeholder",
        r"示意图",
        r"待补充",
        r"\bTBD\b",
        r"\bTODO\b",
    ),
    "metadata": (
        r"target_language",
        r"language_source",
        r"effective_language",
        r"allowed_foreign_terms",
        r"source_unit(?:_ids)?",
        r"\bE\d+\b",
        r"证据(?:编号|ID)",
        r"来源编号",
    ),
    "debug": (
        r"debug",
        r"调试",
        r"trace_id",
        r"generation_id",
        r"制作注释",
        r"caveat",
        r"小字\s*caveat",
    ),
}


@dataclass(frozen=True)
class PromptPolicy:
    schema: str = "cyberppt.prompt_policy.v1"
    visible_text_source: str = "content_lock"
    forbidden_classes: tuple[str, ...] = tuple(FORBIDDEN_TEXT_PATTERNS)
    required_sections: tuple[str, ...] = (
        "【页面类型】",
        "【内容锁定】",
        "【构图指令】",
        "【结构密度】",
    )


DEFAULT_PROMPT_POLICY = PromptPolicy()


def classify_forbidden_text(text: str) -> tuple[str, ...]:
    """Return policy classes found in a candidate page-visible line."""

    matches: list[str] = []
    for category, patterns in FORBIDDEN_TEXT_PATTERNS.items():
        if any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns):
            matches.append(category)
    return tuple(matches)


def validate_visible_text(lines: Iterable[str]) -> list[dict[str, str]]:
    """Return one violation record for each line containing forbidden text."""

    violations: list[dict[str, str]] = []
    for line in lines:
        text = str(line).strip()
        classes = classify_forbidden_text(text)
        if classes:
            violations.append(
                {
                    "class": classes[0],
                    "classes": ",".join(classes),
                    "text": text,
                }
            )
    return violations

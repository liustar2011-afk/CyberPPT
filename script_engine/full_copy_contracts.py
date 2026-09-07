"""Deterministic full-copy structure and semantic checks."""
from __future__ import annotations

import re
from typing import Any

from .semantic_text_primitives import (
    GENERIC_TRANSFORMATION_CLAIM_RE,
    has_complete_semantic_predicate,
    normalize_item_text,
)


_FULL_COPY_STRUCTURE_MIN_CHARS = 180
_FULL_COPY_PARAGRAPH_MIN_CHARS = 24
_ABSTRACT_TOPIC_SENTENCE_RE = re.compile(
    r"(?:任务|要求|工作|建设|内容).{0,8}(?:具体化|更加明确|进一步明确|更为清晰|具有重要意义|意义重大)"
)
_SOURCE_STRENGTH_ABSTRACTION_RE = re.compile(
    r"(?:形成|建立).{0,40}(?:建设内容|阶段进度|技术规则).{0,40}(?:安排|框架)"
)
_FULL_COPY_ORDINAL_RE = re.compile(r"(?:^|[：:，,。；;])\s*([一二三四五六七八九十]+)是")


def _authoring_mode(final_script: dict[str, Any]) -> str:
    deck = final_script.get("deck") if isinstance(final_script.get("deck"), dict) else {}
    return "analytical" if deck.get("authoring_mode") == "analytical" else "faithful"


def check_full_copy_structure(final_script: dict[str, Any]) -> list[str]:
    """Require an explicitly authored long multi-step chain to retain paragraph structure."""

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        full_copy = slide.get("full_copy")
        if not isinstance(full_copy, str):
            continue
        chain = (slide.get("argument") or {}).get("chain") or []
        if len(chain) < 3 or len(normalize_item_text(full_copy)) < _FULL_COPY_STRUCTURE_MIN_CHARS:
            continue
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", full_copy)
            if len(normalize_item_text(paragraph)) >= _FULL_COPY_PARAGRAPH_MIN_CHARS
        ]
        if len(paragraphs) < 2:
            slide_id = slide.get("id") or f"#{index}"
            issues.append(
                f"FULL_COPY_STRUCTURE_FLAT: slides.{index} ({slide_id}).full_copy: "
                "a long multi-step chain is collapsed into one paragraph; preserve at least "
                "two substantive paragraphs so the authored structure remains readable"
            )
    return issues


def check_full_copy_topic_semantics(final_script: dict[str, Any]) -> list[str]:
    """Protect source specificity without forcing faithful paragraphs into judgments."""

    issues: list[str] = []
    mode = _authoring_mode(final_script)
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", str(slide.get("full_copy") or ""))
            if paragraph.strip()
        ]
        for paragraph_index, paragraph in enumerate(paragraphs):
            topic = re.split(r"(?<=[。！？])", paragraph, maxsplit=1)[0].strip()
            compact = normalize_item_text(topic)
            colon_tail = re.split(r"[：:]", topic, maxsplit=1)
            has_substantive_colon_tail = (
                len(colon_tail) == 2 and len(normalize_item_text(colon_tail[1])) >= 8
            )
            if _SOURCE_STRENGTH_ABSTRACTION_RE.search(topic):
                issues.append(
                    f"FULL_COPY_TOPIC_SOURCE_STRENGTH_ABSTRACTED: slides.{index} ({slide_id}).full_copy paragraph "
                    f"{paragraph_index + 1}: opening '{topic}' replaces concrete source actions, status, milestones or "
                    "formal outputs with an author-created summary dimension; restore the concrete source matter"
                )
                continue
            if mode == "analytical" and (
                _ABSTRACT_TOPIC_SENTENCE_RE.search(topic) or (
                    len(compact) < 16
                    and not has_substantive_colon_tail
                    and not has_complete_semantic_predicate(topic)
                )
            ):
                issues.append(
                    f"FULL_COPY_TOPIC_INCOMPLETE: slides.{index} ({slide_id}).full_copy paragraph "
                    f"{paragraph_index + 1}: opening '{topic}' is a label or abstract evaluation, not a "
                    "complete analytical audience-facing point"
                )
    return issues


def check_full_copy_parallel_subconclusions(final_script: dict[str, Any]) -> list[str]:
    """Require judgment-led numbered branches only in analytical mode.

    Faithful mode may preserve source-native numbered tasks, facts, stages and
    taxonomy labels without upgrading each branch into a business conclusion.
    """

    if _authoring_mode(final_script) != "analytical":
        return []

    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict) or slide.get("page_type") != "content":
            continue
        slide_id = slide.get("id") or f"#{index}"
        paragraphs = [
            paragraph.strip()
            for paragraph in re.split(r"\n\s*\n", str(slide.get("full_copy") or ""))
            if paragraph.strip()
        ]
        for paragraph_index, paragraph in enumerate(paragraphs):
            matches = list(_FULL_COPY_ORDINAL_RE.finditer(paragraph))
            if len(matches) < 2:
                continue
            for branch_index, match in enumerate(matches):
                branch_end = (
                    matches[branch_index + 1].start()
                    if branch_index + 1 < len(matches)
                    else len(paragraph)
                )
                branch = paragraph[match.end():branch_end].lstrip("，,：: ")
                opening = re.split(r"[。；;]", branch, maxsplit=1)[0].strip()
                compact = normalize_item_text(opening)
                if GENERIC_TRANSFORMATION_CLAIM_RE.search(compact):
                    issues.append(
                        f"FULL_COPY_PARALLEL_SUBCONCLUSION_ABSTRACT: slides.{index} ({slide_id}).full_copy "
                        f"paragraph {paragraph_index + 1}, branch {match.group(1)}: opening '{opening}' names an "
                        "abstract construction-to-capability transformation without stating the concrete business "
                        "mechanism or observable operating result"
                    )
                elif len(compact) < 12 or not has_complete_semantic_predicate(opening):
                    issues.append(
                        f"FULL_COPY_PARALLEL_SUBCONCLUSION_INCOMPLETE: slides.{index} ({slide_id}).full_copy "
                        f"paragraph {paragraph_index + 1}, branch {match.group(1)}: opening '{opening}' is a label "
                        "or incomplete clause; analytical mode requires an independently intelligible "
                        "sub-conclusion before its supporting detail"
                    )
    return issues


__all__ = [
    "check_full_copy_parallel_subconclusions",
    "check_full_copy_structure",
    "check_full_copy_topic_semantics",
]

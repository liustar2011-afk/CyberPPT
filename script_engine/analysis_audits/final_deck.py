"""Focused deck-level helpers for Final Script semantic audits."""
from __future__ import annotations

from .common import *


def _source_text_for_refs(source_refs: list[Any], foundation: dict[str, Any]) -> str:
    refs = {x for x in source_refs if isinstance(x, str)}
    parts: list[str] = []
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            if refs.intersection(x for x in (item.get("source_refs") or []) if isinstance(x, str)):
                parts.append(_item_text(item))
    return " ".join(parts)


def _normalize_source_chapter_title(title: str) -> str:
    return CHAPTER_PREFIX_RE.sub("", title).strip(" 　")


_RELATIONSHIP_CLAIM_RE = re.compile(
    r"(映射|协同|闭环|衔接|转化|贯通|联动|传导|反馈|对应|支撑.+(?:形成|实现|落地))"
)


def _whole_deck_authoring_warnings(final_script: dict[str, Any]) -> list[str]:
    """Flag deck-wide authoring regressions that page-local checks cannot see."""
    content_slides = [
        slide
        for slide in final_script.get("slides") or []
        if isinstance(slide, dict) and slide.get("page_type") == "content"
    ]
    if len(content_slides) < 6:
        return []

    warnings: list[str] = []
    shapes: list[tuple[int, int]] = []
    for slide in content_slides:
        modules = [
            module for module in slide.get("onscreen") or [] if isinstance(module, dict)
        ]
        shapes.append(
            (
                len(modules),
                sum(len(module.get("items") or []) for module in modules),
            )
        )
    if len(set(shapes)) == 1:
        module_count, item_count = shapes[0]
        warnings.append(
            "AUTHOR_STRUCTURE_FLATLINE: all "
            f"{len(content_slides)} content pages use the same {module_count}-module/"
            f"{item_count}-item shape; run whole-deck Critic to verify that page missions, "
            "evidence depth and relationship grammars were authored independently"
        )

    relationship_count = sum(
        len([item for item in slide.get("relationships") or [] if isinstance(item, dict)])
        for slide in content_slides
    )
    relation_claim_pages = [
        str(slide.get("id") or "?")
        for slide in content_slides
        if _RELATIONSHIP_CLAIM_RE.search(
            " ".join(
                str(slide.get(key) or "")
                for key in ("core_message", "visual_thesis")
            )
        )
    ]
    if relationship_count == 0 and len(relation_claim_pages) >= 2:
        warnings.append(
            "AUTHOR_RELATIONSHIP_LAYER_ABSENT: the deck makes relationship claims on "
            f"{relation_claim_pages} but no content page declares relationships; verify "
            "both endpoints and the connecting action in Final Script"
        )
    return warnings


__all__ = [
    "_source_text_for_refs",
    "_normalize_source_chapter_title",
    "_whole_deck_authoring_warnings",
]

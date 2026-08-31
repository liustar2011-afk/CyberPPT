"""Reading-load estimation and strategy selection for source-index v2."""
from __future__ import annotations

import math
from typing import Any


def estimate_reading_load(
    units: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Estimate model reading load without changing the source inventory."""

    texts = [str(item.get("text") or "") for item in units]
    text_chars = sum(len(text) for text in texts)
    cjk_chars = sum(1 for text in texts for char in text if "\u3400" <= char <= "\u9fff")
    latin_chars = max(0, text_chars - cjk_chars)
    token_estimate = int(math.ceil(cjk_chars * 1.1 + latin_chars / 4))
    explicit_pages = 0
    slides_by_source: dict[str, set[int]] = {}
    sheets_by_source: dict[str, set[str]] = {}
    for item in units:
        locator = item.get("locator") if isinstance(item.get("locator"), dict) else {}
        source_id = str(item.get("source_id") or "")
        slide = locator.get("slide")
        if isinstance(slide, int):
            slides_by_source.setdefault(source_id, set()).add(slide)
        sheet = locator.get("sheet")
        if isinstance(sheet, str) and sheet:
            sheets_by_source.setdefault(source_id, set()).add(sheet)
    explicit_pages += sum(len(values) for values in slides_by_source.values())
    explicit_pages += sum(len(values) for values in sheets_by_source.values())
    text_pages = int(math.ceil(text_chars / 1000)) if text_chars else 0
    return {
        "source_count": len(sources),
        "unit_count": len(units),
        "text_chars": text_chars,
        "token_estimate": token_estimate,
        "page_equivalent": max(explicit_pages, text_pages, 1 if units else 0),
    }


def recommend_reading_mode(
    reading_load: dict[str, Any],
    *,
    max_pages: int = 45,
    max_tokens: int = 60_000,
) -> dict[str, Any]:
    """Choose direct or long reading from transparent size thresholds."""

    pages = int(reading_load.get("page_equivalent") or 0)
    tokens = int(reading_load.get("token_estimate") or 0)
    reasons: list[str] = []
    if pages > max_pages:
        reasons.append(f"page_equivalent {pages} exceeds {max_pages}")
    if tokens > max_tokens:
        reasons.append(f"token_estimate {tokens} exceeds {max_tokens}")
    return {
        "mode": "long" if reasons else "direct",
        "max_pages": max_pages,
        "max_tokens": max_tokens,
        "reasons": reasons,
    }


def _critical_deep_read_unit_ids(units: list[dict[str, Any]]) -> list[str]:
    critical_markers = (
        "必须", "不得", "应当", "责任", "条件", "范围", "边界", "计划", "已完成",
        "风险", "目标", "截止", "%", "亿元", "万元", "年", "月", "日",
    )
    result: list[str] = []
    for item in units:
        text = str(item.get("text") or "")
        if item.get("kind") == "heading" or any(marker in text for marker in critical_markers):
            unit_id = str(item.get("unit_id") or "")
            if unit_id:
                result.append(unit_id)
    return result


def default_reading_strategy(
    recommendation: dict[str, Any],
    headings: list[dict[str, Any]],
    units: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a reviewable selection without deleting any indexed unit."""

    mode = str(recommendation.get("mode") or "direct")
    all_unit_ids = [str(item.get("unit_id")) for item in units if item.get("unit_id")]
    deep_read = all_unit_ids if mode == "direct" else _critical_deep_read_unit_ids(units)
    return {
        "mode": mode,
        "section_dispositions": [
            {
                "heading_id": str(item.get("heading_id")),
                "disposition": "deep_read" if mode == "direct" else "mapped",
                "reason": (
                    "direct profile reads the complete indexed section"
                    if mode == "direct"
                    else "retain the complete argument skeleton; expand critical units first"
                ),
            }
            for item in headings
            if item.get("heading_id")
        ],
        "deep_read_unit_ids": deep_read,
        "excluded_unit_ids": [],
    }


__all__ = [
    "default_reading_strategy",
    "estimate_reading_load",
    "recommend_reading_mode",
]

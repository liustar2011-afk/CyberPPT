"""Deterministic enforcement of explicit PLAN content-route signals."""

from __future__ import annotations

import re
from typing import Any

from .models import SemanticDiagnostic


def _text(value: object) -> str:
    return str(value or "").strip()


def _page_id(page: dict[str, Any]) -> str:
    return _text(page.get("id") or page.get("page_id"))


def _slide_text(slide: dict[str, Any]) -> str:
    """Return all authored Final Script text without semantic classification."""

    parts: list[str] = []
    for key in (
        "title",
        "subtitle",
        "mission",
        "core_message",
        "full_copy",
        "visual_thesis",
        "speaker_notes",
    ):
        value = slide.get(key)
        if isinstance(value, str):
            parts.append(value)

    argument = slide.get("argument")
    if isinstance(argument, dict):
        pattern = argument.get("pattern")
        if isinstance(pattern, str):
            parts.append(pattern)
        parts.extend(
            value for value in argument.get("chain") or [] if isinstance(value, str)
        )

    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str):
                parts.append(value)
        for item in module.get("items") or []:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                value = item.get("text")
                if isinstance(value, str):
                    parts.append(value)

    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "to", "relation"):
            value = relation.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)


def collect_content_route_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Require PLAN-declared meaning signals to remain in Final Script copy."""

    if not isinstance(plan, dict):
        return []
    pages = {
        _page_id(page): page
        for page in plan.get("pages") or []
        if isinstance(page, dict) and _page_id(page)
    }
    diagnostics: list[SemanticDiagnostic] = []

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict):
            continue
        slide_id = _text(slide.get("id"))
        page = pages.get(slide_id)
        if not isinstance(page, dict):
            continue
        route = page.get("content_route")
        if not isinstance(route, dict):
            continue
        visible = re.sub(r"\s+", "", _slide_text(slide))
        for signal_index, signal in enumerate(route.get("meaning_signals") or []):
            if not isinstance(signal, str) or not signal.strip():
                continue
            normalized_signal = re.sub(r"\s+", "", signal)
            if normalized_signal in visible:
                continue
            diagnostics.append(
                SemanticDiagnostic(
                    code="CONTENT_ROUTE_MEANING_SIGNAL_MISSING",
                    message=f"PLAN-declared meaning signal {signal!r} is absent from Final Script copy",
                    slide_id=slide_id,
                    target=f"content_route.meaning_signals[{signal_index}]",
                    severity="blocking",
                    relation="conforms_to_plan",
                )
            )
    return diagnostics


__all__ = ["collect_content_route_diagnostics"]

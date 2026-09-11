"""Deterministic delivery-readiness checks for Final Script output."""

from __future__ import annotations

from typing import Any

from .models import SemanticDiagnostic


def _text(value: object) -> str:
    return str(value or "").strip()


def _page_id(page: dict[str, Any]) -> str:
    return _text(page.get("id") or page.get("page_id"))


def collect_delivery_readiness_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Require non-light self-read content pages to expose reader-facing modules.

    This check is structural. It does not score density, infer completeness from
    wording, or decide how much payload is enough once at least one module exists.
    Those editorial judgments remain review-only during Phase 4.
    """

    plan_payload = plan if isinstance(plan, dict) else {}
    pages = {
        _page_id(page): page
        for page in plan_payload.get("pages") or []
        if isinstance(page, dict) and _page_id(page)
    }
    deck = final_script.get("deck")
    delivery_mode = (
        _text(deck.get("delivery_mode")) if isinstance(deck, dict) else ""
    ) or _text(plan_payload.get("delivery_mode")) or "self_read"
    if delivery_mode != "self_read":
        return []

    diagnostics: list[SemanticDiagnostic] = []
    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict):
            continue
        slide_id = _text(slide.get("id"))
        page = pages.get(slide_id)
        page_type = _text(slide.get("page_type")) or (
            _text(page.get("page_role")) if isinstance(page, dict) else ""
        )
        if page_type != "content":
            continue
        load = _text(slide.get("content_load")) or (
            _text(page.get("content_load")) if isinstance(page, dict) else "standard"
        ) or "standard"
        if load == "light":
            continue
        modules = [
            module
            for module in slide.get("onscreen") or []
            if isinstance(module, dict)
        ]
        if modules:
            continue
        diagnostics.append(
            SemanticDiagnostic(
                code="ONSCREEN_SELF_READ_PAYLOAD_MISSING",
                message="self-read content page has no reader-facing modules",
                slide_id=slide_id,
                target="onscreen",
                severity="blocking",
                relation="delivery_policy",
            )
        )
    return diagnostics


__all__ = ["collect_delivery_readiness_diagnostics"]

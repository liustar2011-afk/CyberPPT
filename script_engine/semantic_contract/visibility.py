"""Explicit external/internal visibility checks for Final Script.

Only typed Foundation ``visibility`` values are authoritative here. Historical
text markers such as “内部测算” are deliberately excluded from this structured
validator and remain compatibility review signals.
"""

from __future__ import annotations

from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic
from .protected_payload import (
    _as_literals,
    _contains,
    _module_refs,
    _module_text,
    _number_literals,
    _refs,
    _text,
)


_INTERNAL_VISIBILITY = "internal_only"


def _used_refs(final_script: dict[str, Any], slide: dict[str, Any]) -> tuple[str, ...]:
    """Return the strongest available declaration of records actually used."""

    if _text(final_script.get("version")) == "1.1":
        ordered: list[str] = []
        seen: set[str] = set()
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            for ref in _module_refs(module):
                if ref not in seen:
                    seen.add(ref)
                    ordered.append(ref)
        return tuple(ordered)
    return tuple(dict.fromkeys(_refs(slide.get("source_refs"))))


def _slide_delivery_surface(slide: dict[str, Any]) -> str:
    """Collect Final Script text that can enter an external delivery artifact."""

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
        value = _text(slide.get(key))
        if value:
            parts.append(value)

    argument = slide.get("argument")
    if isinstance(argument, dict):
        pattern = _text(argument.get("pattern"))
        if pattern:
            parts.append(pattern)
        parts.extend(_refs(argument.get("chain")))

    for module in slide.get("onscreen") or []:
        if isinstance(module, dict):
            value = _module_text(module)
            if value:
                parts.append(value)

    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "relation", "to"):
            value = _text(relation.get(key))
            if value:
                parts.append(value)

    return "\n".join(parts)


def _explicit_internal_literals(
    index: FoundationIndex,
    ref: str,
) -> tuple[str, ...]:
    """Return only explicitly modeled values whose exposure can be proven."""

    record = index.record(ref)
    if record is None:
        return ()
    payload = record.payload
    literals: list[str] = []

    literals.extend(_as_literals(payload.get("protected_literals")))
    for key in ("formal_document_name", "document_name", "instrument_name"):
        literals.extend(_as_literals(payload.get(key)))

    if record.kind == "numbers":
        literals.extend(_number_literals(index, ref))
    else:
        literals.extend(_as_literals(payload.get("value")))
        for number_ref in _refs(payload.get("number_refs")):
            literals.extend(_number_literals(index, number_ref))

    return tuple(dict.fromkeys(literal for literal in literals if literal))


def collect_visibility_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Audit explicit ``internal_only`` evidence for external delivery.

    Referencing internal evidence is reviewable because an external conclusion may
    legitimately be derived from non-exported internal analysis. Blocking is
    reserved for exact protected values that are demonstrably present in the
    Final Script delivery surface.
    """

    if not isinstance(plan, dict) or plan.get("audience_scope") != "external":
        return []
    if not isinstance(foundation, dict):
        return []

    index = FoundationIndex(foundation)
    diagnostics: list[SemanticDiagnostic] = []

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict) or _text(slide.get("page_type")) != "content":
            continue
        slide_id = _text(slide.get("id"))
        surface = _slide_delivery_surface(slide)

        for ref in _used_refs(final_script, slide):
            record = index.record(ref)
            if record is None:
                continue
            if _text(record.payload.get("visibility")) != _INTERNAL_VISIBILITY:
                continue

            literals = _explicit_internal_literals(index, ref)
            exposed = tuple(literal for literal in literals if _contains(surface, literal))
            if exposed:
                diagnostics.append(
                    SemanticDiagnostic(
                        code="INTERNAL_PROTECTED_VALUE_EXPOSED",
                        message=(
                            "external Final Script exposes exact protected value(s) from "
                            f"internal-only evidence: {list(exposed)}"
                        ),
                        slide_id=slide_id,
                        target="delivery_surface",
                        severity="blocking",
                        evidence_refs=(ref,),
                        relation="visibility",
                    )
                )
                continue

            diagnostics.append(
                SemanticDiagnostic(
                    code="INTERNAL_EVIDENCE_EXTERNAL_REVIEW_REQUIRED",
                    message=(
                        "external Final Script references internal-only evidence without "
                        "an exact protected-value exposure; confirm that only a permitted "
                        "derived conclusion is delivered"
                    ),
                    slide_id=slide_id,
                    target="delivery_surface",
                    severity="review_required",
                    evidence_refs=(ref,),
                    relation="visibility",
                )
            )

    return diagnostics

"""Deterministic preservation checks for explicitly typed protected payload.

The checker uses only Foundation fields and exact/normalized values. It never
classifies visible prose by business keywords. Values that can be paraphrased
legitimately are routed to review instead of becoming blocking lexical rules.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic


def _text(value: object) -> str:
    return str(value or "").strip()


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(_text(item) for item in value if _text(item))


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKC", _text(value)).casefold()
    return re.sub(r"\s+", "", text)


def _contains(container: str, literal: str) -> bool:
    needle = _normalize(literal)
    return bool(needle) and needle in _normalize(container)


def _module_text(module: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("heading", "text"):
        value = _text(module.get(key))
        if value:
            parts.append(value)
    for item in module.get("items") or []:
        if isinstance(item, dict):
            value = _text(item.get("text"))
        else:
            value = _text(item)
        if value:
            parts.append(value)
    return "\n".join(parts)


def _module_refs(module: dict[str, Any]) -> tuple[str, ...]:
    provenance = module.get("provenance")
    if not isinstance(provenance, dict):
        return ()
    ordered: list[str] = []
    seen: set[str] = set()
    for ref in _refs(provenance.get("claim_refs")):
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    for binding in provenance.get("bindings") or []:
        if not isinstance(binding, dict):
            continue
        for ref in _refs(binding.get("source_refs")):
            if ref not in seen:
                seen.add(ref)
                ordered.append(ref)
    return tuple(ordered)


def _as_literals(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(_text(item) for item in value if _text(item))
    text = _text(value)
    return (text,) if text else ()


def _number_literal(index: FoundationIndex, ref: str) -> str:
    record = index.record(ref)
    if record is None:
        return ""
    value = record.payload.get("value")
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        number = str(int(value))
    else:
        number = str(value).strip()
    unit = _text(record.payload.get("unit"))
    return f"{number}{unit}" if number else ""


def collect_protected_payload_diagnostics(
    final_script: dict[str, Any],
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Check exact protected values against each module's aggregate visible copy."""

    if _text(final_script.get("version")) != "1.1" or not isinstance(foundation, dict):
        return []

    diagnostics: list[SemanticDiagnostic] = []
    index = FoundationIndex(foundation)

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict) or _text(slide.get("page_type")) != "content":
            continue
        slide_id = _text(slide.get("id"))
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            module_id = _text(module.get("id"))
            visible = _module_text(module)
            for ref in _module_refs(module):
                record = index.record(ref)
                if record is None:
                    continue
                payload = record.payload

                exact_literals: list[tuple[str, str]] = []
                for literal in _as_literals(payload.get("protected_literals")):
                    exact_literals.append(("literal", literal))
                for key in (
                    "formal_document_name",
                    "document_name",
                    "instrument_name",
                ):
                    for literal in _as_literals(payload.get(key)):
                        exact_literals.append(("formal_name", literal))
                for number_ref in _refs(payload.get("number_refs")):
                    literal = _number_literal(index, number_ref)
                    if literal:
                        exact_literals.append(("number", literal))

                for kind, literal in exact_literals:
                    if _contains(visible, literal):
                        continue
                    code = (
                        "PROTECTED_NUMBER_MISSING"
                        if kind == "number"
                        else "PROTECTED_LITERAL_MISSING"
                    )
                    diagnostics.append(
                        SemanticDiagnostic(
                            code=code,
                            message=f"module visible copy does not preserve exact {kind} {literal!r}",
                            slide_id=slide_id,
                            module_id=module_id,
                            severity="blocking",
                            evidence_refs=(ref,),
                            relation="preserves",
                        )
                    )

                for condition in index.conditions(ref):
                    if _contains(visible, condition):
                        continue
                    diagnostics.append(
                        SemanticDiagnostic(
                            code="PROTECTED_CONDITION_REVIEW_REQUIRED",
                            message=f"condition {condition!r} is not present verbatim; semantic preservation requires review",
                            slide_id=slide_id,
                            module_id=module_id,
                            severity="review_required",
                            evidence_refs=(ref,),
                            relation="preserves",
                        )
                    )

                for actor in index.actors(ref):
                    if _contains(visible, actor):
                        continue
                    diagnostics.append(
                        SemanticDiagnostic(
                            code="PROTECTED_ACTOR_REVIEW_REQUIRED",
                            message=f"actor {actor!r} is not present verbatim; alias or inherited-subject preservation requires review",
                            slide_id=slide_id,
                            module_id=module_id,
                            severity="review_required",
                            evidence_refs=(ref,),
                            relation="preserves",
                        )
                    )

    return diagnostics

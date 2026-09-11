"""Deterministic preservation checks for explicitly typed protected payload.

The checker uses only Foundation fields and exact/normalized values. It never
classifies visible prose by business keywords. Values that can be paraphrased
legitimately are routed to review instead of becoming blocking lexical rules.

Final Script 1.1 is checked at module/item provenance scope. Final Script 1.0
has no module provenance, so its compatibility projection is limited to the
slide-level source refs already declared by AUTHOR and the PLAN source boundary.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic
from .source_scope import _requires_source_consumption


_TIME_LIKE_UNITS = frozenset({"时间", "年份", "生效日期"})


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


def _scalar_text(value: object) -> str:
    if value is None or isinstance(value, bool):
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _number_literals(index: FoundationIndex, ref: str) -> tuple[str, ...]:
    """Return exact display literals from one typed Foundation number record.

    Semantic unit labels such as ``时间`` describe the value and are not literal
    suffixes. Physical/business units such as ``年``、``%``、``万元`` remain part
    of the protected visible value. List-valued records preserve each explicit
    member without inventing a combined representation.
    """

    record = index.record(ref)
    if record is None:
        return ()
    raw_value = record.payload.get("value")
    values = raw_value if isinstance(raw_value, list) else [raw_value]
    unit = _text(record.payload.get("unit"))
    literals: list[str] = []
    for raw in values:
        number = _scalar_text(raw)
        if not number:
            continue
        literals.append(number)
        if (
            not isinstance(raw_value, list)
            and unit
            and unit not in _TIME_LIKE_UNITS
            and not number.endswith(unit)
        ):
            literals.append(f"{number}{unit}")
    return tuple(dict.fromkeys(literals))


def _legacy_slide_protected_payload_diagnostics(
    final_script: dict[str, Any],
    plan: dict[str, Any] | None,
    foundation: dict[str, Any],
) -> list[SemanticDiagnostic]:
    """Project typed payload checks onto a provenance-less Final Script 1.0.

    The projection deliberately uses only explicit slide/page refs and typed
    Foundation fields. Exact number/date loss is deterministic. Conditions and
    actors can be paraphrased or inherited, so absence of the literal is a review
    finding rather than a blocker.
    """

    plan = plan if isinstance(plan, dict) else {}
    pages = {
        page.get("id"): page
        for page in plan.get("pages") or []
        if isinstance(page, dict) and isinstance(page.get("id"), str)
    }
    index = FoundationIndex(foundation)
    diagnostics: list[SemanticDiagnostic] = []

    for slide in final_script.get("slides") or []:
        if not isinstance(slide, dict) or _text(slide.get("page_type")) != "content":
            continue
        slide_id = _text(slide.get("id"))
        page = pages.get(slide_id)
        if not isinstance(page, dict) or not _requires_source_consumption(page, foundation):
            continue

        page_refs = set(_refs(page.get("source_refs")))
        usable_refs = tuple(
            dict.fromkeys(
                ref
                for ref in _refs(slide.get("source_refs"))
                if ref in page_refs and index.contains(ref)
            )
        )
        full_copy = _text(slide.get("full_copy"))

        for ref in usable_refs:
            record = index.record(ref)
            if record is None:
                continue
            payload = record.payload

            for number_ref in _refs(payload.get("number_refs")):
                for literal in _number_literals(index, number_ref):
                    if _contains(full_copy, literal):
                        continue
                    diagnostics.append(
                        SemanticDiagnostic(
                            code="PROTECTED_NUMBER_MISSING",
                            message=(
                                f"legacy slide full_copy does not preserve exact number/date "
                                f"{literal!r}"
                            ),
                            slide_id=slide_id,
                            target="full_copy",
                            severity="blocking",
                            evidence_refs=(ref,),
                            relation="preserves",
                        )
                    )

            for condition in index.conditions(ref):
                if _contains(full_copy, condition):
                    continue
                diagnostics.append(
                    SemanticDiagnostic(
                        code="PROTECTED_CONDITION_REVIEW_REQUIRED",
                        message=(
                            f"condition {condition!r} is not present verbatim in legacy "
                            "full_copy; semantic preservation requires review"
                        ),
                        slide_id=slide_id,
                        target="full_copy",
                        severity="review_required",
                        evidence_refs=(ref,),
                        relation="preserves",
                    )
                )

            for actor in index.actors(ref):
                if _contains(full_copy, actor):
                    continue
                diagnostics.append(
                    SemanticDiagnostic(
                        code="PROTECTED_ACTOR_REVIEW_REQUIRED",
                        message=(
                            f"actor {actor!r} is not present verbatim in legacy full_copy; "
                            "alias or inherited-subject preservation requires review"
                        ),
                        slide_id=slide_id,
                        target="full_copy",
                        severity="review_required",
                        evidence_refs=(ref,),
                        relation="preserves",
                    )
                )

    return diagnostics


def collect_protected_payload_diagnostics(
    final_script: dict[str, Any],
    foundation: dict[str, Any] | None,
    plan: dict[str, Any] | None = None,
) -> list[SemanticDiagnostic]:
    """Check typed protected values at the strongest available semantic scope."""

    if not isinstance(foundation, dict):
        return []

    if _text(final_script.get("version")) != "1.1":
        return _legacy_slide_protected_payload_diagnostics(
            final_script,
            plan,
            foundation,
        )

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
                    for literal in _number_literals(index, number_ref):
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

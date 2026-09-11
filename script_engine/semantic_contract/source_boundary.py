"""Deterministic Final Script source-boundary checks.

This module owns objective audience-facing numeric and formal-instrument drift for
the formal semantic contract. It deliberately does not reuse the legacy
composed-trace classifier: CJK n-gram novelty and identifier shape remain
compatibility/review signals, while exact numeric tokens and explicit formal
instrument names can be checked against Foundation and explicitly bound evidence
without business-word inference.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .foundation_index import FoundationIndex
from .models import SemanticDiagnostic


_SOURCE_TEXT_KEYS = frozenset(
    {
        "title",
        "statement",
        "claim",
        "definition",
        "context",
        "strength",
        "term",
        "relation",
        "value",
        "unit",
        "name",
        "role",
        "from",
        "to",
        "primary_thesis",
        "author_purpose",
        "decision_boundary",
        "scope",
        "decision_intent",
        "source_heading",
        "meaning",
        "label",
        "text",
        # Explicit typed payload that can legitimately carry exact source-bound
        # numbers, dates, actors or formal instrument names. These are Foundation
        # contract fields, not business vocabulary.
        "conditions",
        "condition",
        "actors",
        "actor",
        "protected_literals",
        "formal_document_name",
        "document_name",
        "instrument_name",
    }
)
_FINAL_SCALAR_FIELDS = (
    "title",
    "subtitle",
    "core_message",
    "full_copy",
    "visual_thesis",
    "speaker_notes",
)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?%?")
_FORMAL_INSTRUMENT_RE = re.compile(r"《[^》\n]{2,80}》")


def _numeric_tokens(value: object) -> set[str]:
    return set(_NUMBER_RE.findall(str(value or "")))


def _formal_instruments(value: object) -> set[str]:
    return set(_FORMAL_INSTRUMENT_RE.findall(str(value or "")))


def _selected_source_strings(value: object) -> Iterable[str]:
    """Yield scalar values nested below an explicitly selected source field."""

    if isinstance(value, (str, int, float)):
        if str(value).strip():
            yield str(value)
        return
    if isinstance(value, list):
        for child in value:
            yield from _selected_source_strings(child)
        return
    if isinstance(value, dict):
        for child in value.values():
            yield from _selected_source_strings(child)


def _source_strings(value: object) -> Iterable[str]:
    """Yield explicit Foundation source fields without business-word inference.

    Field names are structural contract keys, not business vocabulary. Compared
    with legacy composed tracing, this projection also preserves scalar values
    nested inside an explicit ``value``/text/typed-protection field (for example
    a numeric value list or source condition), so typed Foundation payload cannot
    be rejected merely because it is represented outside the main statement.
    """

    if isinstance(value, dict):
        for key, child in value.items():
            if key in _SOURCE_TEXT_KEYS:
                yield from _selected_source_strings(child)
            elif isinstance(child, (list, dict)):
                yield from _source_strings(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (list, dict)):
                yield from _source_strings(child)


def _foundation_surface_tokens(
    foundation: dict[str, Any],
) -> tuple[set[str], set[str]]:
    numbers: set[str] = set()
    instruments: set[str] = set()
    for value in _source_strings(foundation):
        numbers.update(_numeric_tokens(value))
        instruments.update(_formal_instruments(value))
    return numbers, instruments


def _record_source_strings(
    index: FoundationIndex,
    refs: tuple[str, ...],
) -> Iterable[str]:
    """Yield source surface reachable from explicit evidence refs.

    The scoped boundary follows only direct Foundation records plus their explicit
    ``number_refs`` and ``entity_refs``. It does not infer a support chain from
    prose, relation vocabulary, or nearby records.
    """

    seen: set[str] = set()
    queue = list(refs)
    while queue:
        ref = str(queue.pop(0) or "").strip()
        if not ref or ref in seen:
            continue
        seen.add(ref)
        record = index.record(ref)
        if record is None:
            continue
        yield from _source_strings(record.payload)
        for key in ("number_refs", "entity_refs"):
            value = record.payload.get(key)
            if isinstance(value, list):
                queue.extend(str(item).strip() for item in value if str(item).strip())


def _evidence_surface_tokens(
    index: FoundationIndex,
    refs: tuple[str, ...],
) -> tuple[set[str], set[str]]:
    numbers: set[str] = set()
    instruments: set[str] = set()
    for value in _record_source_strings(index, refs):
        numbers.update(_numeric_tokens(value))
        instruments.update(_formal_instruments(value))
    return numbers, instruments


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(
        dict.fromkeys(
            str(item).strip()
            for item in value
            if isinstance(item, str) and item.strip()
        )
    )


def _binding_refs(
    module: dict[str, Any],
    target: str,
    fallback: tuple[str, ...],
    *,
    use_provenance: bool,
) -> tuple[str, ...]:
    """Return the explicit v1.1 evidence binding for one visible target.

    Missing/invalid provenance is validated separately. Falling back to slide
    refs here prevents duplicate noise when provenance itself is already blocking.
    """

    if not use_provenance:
        return fallback
    provenance = module.get("provenance")
    if not isinstance(provenance, dict):
        return fallback
    for binding in provenance.get("bindings") or []:
        if not isinstance(binding, dict):
            continue
        if str(binding.get("target") or "").strip() != target:
            continue
        refs = _refs(binding.get("source_refs"))
        return refs or fallback
    return fallback


def _final_text_fields(
    final_script: dict[str, Any],
) -> Iterable[tuple[str, str, str, tuple[str, ...]]]:
    """Yield ``(slide_id, target, text, evidence_refs)`` for audited script text.

    Final Script 1.0 has only slide-level evidence, so it retains the historical
    page-scoped boundary. Final Script 1.1 narrows each visible module target to
    its explicit provenance binding; slide-level prose and relationship metadata
    continue to use slide.source_refs.
    """

    use_provenance = str(final_script.get("version") or "").strip() == "1.1"
    for slide_index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("id") or f"#{slide_index}")
        source_refs = _refs(slide.get("source_refs"))
        prefix = f"slides.{slide_index}"
        for field in _FINAL_SCALAR_FIELDS:
            value = slide.get(field)
            if isinstance(value, str) and value.strip():
                yield slide_id, f"{prefix}.{field}", value, source_refs

        argument = slide.get("argument")
        if isinstance(argument, dict):
            for item_index, value in enumerate(argument.get("chain") or []):
                if isinstance(value, str) and value.strip():
                    yield (
                        slide_id,
                        f"{prefix}.argument.chain[{item_index}]",
                        value,
                        source_refs,
                    )

        for module_index, module in enumerate(slide.get("onscreen") or []):
            if not isinstance(module, dict):
                continue
            module_prefix = f"{prefix}.onscreen[{module_index}]"
            for field in ("heading", "text"):
                value = module.get(field)
                if isinstance(value, str) and value.strip():
                    yield (
                        slide_id,
                        f"{module_prefix}.{field}",
                        value,
                        _binding_refs(
                            module,
                            field,
                            source_refs,
                            use_provenance=use_provenance,
                        ),
                    )
            for item_index, item in enumerate(module.get("items") or []):
                target = f"{module_prefix}.items[{item_index}]"
                if isinstance(item, str) and item.strip():
                    yield slide_id, target, item, source_refs
                elif isinstance(item, dict):
                    value = item.get("text")
                    item_id = str(item.get("id") or "").strip()
                    if isinstance(value, str) and value.strip():
                        yield (
                            slide_id,
                            f"{target}.text",
                            value,
                            _binding_refs(
                                module,
                                item_id,
                                source_refs,
                                use_provenance=use_provenance,
                            ),
                        )

        for relation_index, relation in enumerate(slide.get("relationships") or []):
            if not isinstance(relation, dict):
                continue
            relation_prefix = f"{prefix}.relationships[{relation_index}]"
            for field in ("from", "to", "relation"):
                value = relation.get(field)
                if isinstance(value, str) and value.strip():
                    yield slide_id, f"{relation_prefix}.{field}", value, source_refs


def collect_source_boundary_diagnostics(
    final_script: dict[str, Any],
    foundation: dict[str, Any] | None,
) -> list[SemanticDiagnostic]:
    """Block objective additions outside Foundation or declared evidence.

    Global Foundation checks reject exact numeric tokens and explicit formal
    instrument names that do not exist anywhere in source truth. Each text target
    is then checked against its strongest available declared evidence scope:
    slide.source_refs for legacy/slide-level copy, or the exact v1.1 provenance
    binding for visible module targets. Missing source/provenance contracts are
    owned by their dedicated validators.

    Identifier novelty, prose novelty and semantic similarity remain excluded.
    """

    if not isinstance(foundation, dict):
        return []

    allowed_numbers, allowed_instruments = _foundation_surface_tokens(foundation)
    index = FoundationIndex(foundation)
    evidence_surface_cache: dict[tuple[str, ...], tuple[set[str], set[str]]] = {}
    diagnostics: list[SemanticDiagnostic] = []

    for slide_id, target, text, evidence_refs in _final_text_fields(final_script):
        text_numbers = _numeric_tokens(text)
        text_instruments = _formal_instruments(text)

        outside_foundation_numbers = sorted(text_numbers - allowed_numbers)
        if outside_foundation_numbers:
            diagnostics.append(
                SemanticDiagnostic(
                    code="FINAL_NUMBER_OUTSIDE_FOUNDATION",
                    message=(
                        f"Final Script introduces numeric token(s) {outside_foundation_numbers} "
                        "that are absent from the Foundation source surface"
                    ),
                    slide_id=slide_id,
                    target=target,
                    severity="blocking",
                    relation="bounded_by_foundation",
                )
            )

        outside_foundation_instruments = sorted(
            text_instruments - allowed_instruments
        )
        if outside_foundation_instruments:
            diagnostics.append(
                SemanticDiagnostic(
                    code="FINAL_FORMAL_INSTRUMENT_OUTSIDE_FOUNDATION",
                    message=(
                        "Final Script introduces formal instrument name(s) "
                        f"{outside_foundation_instruments} that are absent from the "
                        "Foundation source surface"
                    ),
                    slide_id=slide_id,
                    target=target,
                    severity="blocking",
                    relation="bounded_by_foundation",
                )
            )

        if not evidence_refs:
            continue
        scoped_numbers, scoped_instruments = evidence_surface_cache.setdefault(
            evidence_refs,
            _evidence_surface_tokens(index, evidence_refs),
        )

        outside_scoped_numbers = sorted(
            (text_numbers & allowed_numbers) - scoped_numbers
        )
        if outside_scoped_numbers:
            diagnostics.append(
                SemanticDiagnostic(
                    code="FINAL_NUMBER_OUTSIDE_SLIDE_EVIDENCE",
                    message=(
                        f"Final Script uses numeric token(s) {outside_scoped_numbers} that "
                        "exist in Foundation but not in the target's declared evidence surface"
                    ),
                    slide_id=slide_id,
                    target=target,
                    severity="blocking",
                    evidence_refs=evidence_refs,
                    relation="bounded_by_declared_evidence",
                )
            )

        outside_scoped_instruments = sorted(
            (text_instruments & allowed_instruments) - scoped_instruments
        )
        if outside_scoped_instruments:
            diagnostics.append(
                SemanticDiagnostic(
                    code="FINAL_FORMAL_INSTRUMENT_OUTSIDE_SLIDE_EVIDENCE",
                    message=(
                        "Final Script uses formal instrument name(s) "
                        f"{outside_scoped_instruments} that exist in Foundation but not in "
                        "the target's declared evidence surface"
                    ),
                    slide_id=slide_id,
                    target=target,
                    severity="blocking",
                    evidence_refs=evidence_refs,
                    relation="bounded_by_declared_evidence",
                )
            )

    return diagnostics


__all__ = ["collect_source_boundary_diagnostics"]

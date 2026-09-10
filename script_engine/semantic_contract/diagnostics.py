"""Shared partitioning and serialization for semantic-contract diagnostics."""

from __future__ import annotations

from collections.abc import Iterable

from .models import SemanticDiagnostic


def dedupe_diagnostics(
    diagnostics: Iterable[SemanticDiagnostic],
) -> list[SemanticDiagnostic]:
    result: list[SemanticDiagnostic] = []
    seen: set[tuple[object, ...]] = set()
    for diagnostic in diagnostics:
        key = (
            diagnostic.code,
            diagnostic.severity,
            diagnostic.slide_id,
            diagnostic.module_id,
            diagnostic.target,
            diagnostic.claim_refs,
            diagnostic.evidence_refs,
            diagnostic.relation,
            diagnostic.message,
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(diagnostic)
    return result


def partition_diagnostics(
    diagnostics: Iterable[SemanticDiagnostic],
) -> tuple[list[str], list[str], list[dict[str, object]]]:
    normalized = dedupe_diagnostics(diagnostics)
    blockers = [
        diagnostic.render()
        for diagnostic in normalized
        if diagnostic.severity == "blocking"
    ]
    review_required = [
        diagnostic.render()
        for diagnostic in normalized
        if diagnostic.severity != "blocking"
    ]
    structured = [diagnostic.to_dict() for diagnostic in normalized]
    return blockers, review_required, structured

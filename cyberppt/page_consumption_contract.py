"""Shared runtime predicates for page-scoped evidence consumption."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ONSCREEN_VISIBILITIES = {"primary_onscreen", "supporting_onscreen"}


@dataclass(frozen=True)
class ArgumentChainVisibilityGap:
    """One fact-governed argument step with no visible main-chain carrier."""

    step_index: int
    source_refs: tuple[str, ...]


def _refs(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item))


def _fact_refs(step: dict[str, Any]) -> tuple[str, ...]:
    """Read fact references from either authority or projected chain shape.

    Layer-four page plans keep normalized facts under ``evidence``.  The
    CyberPPT projection maps those facts to direct ``source_refs``.  A nested
    evidence object with only relation or argument-node IDs deliberately
    returns no fact references.
    """

    evidence = step.get("evidence")
    if isinstance(evidence, dict):
        return _refs(evidence.get("normalized_fact_ids"))
    return _refs(step.get("source_refs"))


def argument_chain_visibility_gaps(
    records: list[dict[str, Any]],
    argument_chain: object,
) -> tuple[ArgumentChainVisibilityGap, ...]:
    """Find fact-governed chain steps missing a visible main-chain fact.

    One qualifying fact per step is sufficient.  Other facts in the same
    step, and evidence outside the governing chain, may remain off screen.
    Relationship-only and argument-node-only steps have no fact refs and are
    left unchanged.
    """

    if not isinstance(argument_chain, list):
        return ()
    consumption_by_ref: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for ref in _refs(record.get("source_refs")):
            consumption_by_ref.setdefault(ref, []).append(record)

    gaps: list[ArgumentChainVisibilityGap] = []
    for step_index, step in enumerate(argument_chain, start=1):
        if not isinstance(step, dict):
            continue
        fact_refs = _fact_refs(step)
        if not fact_refs:
            continue
        if any(
            str(record.get("visibility") or "") in ONSCREEN_VISIBILITIES
            and str(record.get("topology_role") or "") == "main_chain"
            for ref in fact_refs
            for record in consumption_by_ref.get(ref, [])
        ):
            continue
        gaps.append(ArgumentChainVisibilityGap(step_index, fact_refs))
    return tuple(gaps)


__all__ = [
    "ArgumentChainVisibilityGap",
    "ONSCREEN_VISIBILITIES",
    "argument_chain_visibility_gaps",
]

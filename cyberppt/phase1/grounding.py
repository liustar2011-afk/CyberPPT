"""Deterministic evidence grounding for Stage 1 model output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from cyberppt.phase1.schemas import EvidenceCandidate, SourceAnalysisDraft
from cyberppt.phase1.source_bundle import SourceBundle


_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_.])\d+(?:\.\d+)?")


@dataclass(frozen=True)
class GroundingIssue:
    code: str
    message: str
    evidence_index: int | None = None


@dataclass(frozen=True)
class GroundingReport:
    blocking: bool
    issues: tuple[GroundingIssue, ...]
    accepted_evidence: tuple[EvidenceCandidate, ...]
    evidence_ids: tuple[str, ...]
    source_locations: tuple[tuple[str, tuple[str, ...]], ...]


def _claim_numbers(candidate: EvidenceCandidate) -> set[str]:
    return set(candidate.numbers) | set(_NUMBER_RE.findall(candidate.claim))


def ground_source_analysis(draft: SourceAnalysisDraft, bundle: SourceBundle) -> GroundingReport:
    unit_by_id = {unit.unit_id: unit for unit in bundle.units}
    unit_order = {unit.unit_id: index for index, unit in enumerate(bundle.units)}
    issues: list[GroundingIssue] = []
    accepted: list[EvidenceCandidate] = []

    if not draft.evidence:
        issues.append(GroundingIssue("no_evidence", "source analysis must contain at least one evidence item"))

    for index, candidate in enumerate(draft.evidence):
        candidate_issues: list[GroundingIssue] = []
        cited = [unit_by_id[unit_id] for unit_id in candidate.source_unit_ids if unit_id in unit_by_id]
        for unit_id in candidate.source_unit_ids:
            if unit_id not in unit_by_id:
                candidate_issues.append(
                    GroundingIssue("unknown_source_unit", f"unknown source unit: {unit_id}", index)
                )
        if not cited or candidate.verbatim_support not in "\n".join(unit.text for unit in cited):
            candidate_issues.append(
                GroundingIssue("verbatim_support_missing", "verbatim support is not present in cited source units", index)
            )
        source_numbers = {number for unit in cited for number in unit.numbers}
        for number in sorted(_claim_numbers(candidate)):
            if number not in source_numbers:
                candidate_issues.append(
                    GroundingIssue("number_not_in_source", f"number is not present in cited source units: {number}", index)
                )
        if candidate_issues:
            issues.extend(candidate_issues)
        else:
            accepted.append(candidate)

    accepted.sort(key=lambda item: min(unit_order[unit_id] for unit_id in item.source_unit_ids))
    evidence_ids = tuple(f"E{index:02d}" for index in range(1, len(accepted) + 1))
    source_locations = tuple(
        (
            evidence_ids[index],
            tuple(dict.fromkeys(unit_by_id[unit_id].locator for unit_id in candidate.source_unit_ids)),
        )
        for index, candidate in enumerate(accepted)
    )
    return GroundingReport(
        blocking=bool(issues),
        issues=tuple(issues),
        accepted_evidence=tuple(accepted),
        evidence_ids=evidence_ids,
        source_locations=source_locations,
    )

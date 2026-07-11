"""Deterministic evidence grounding for Stage 1 model output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

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


@dataclass(frozen=True)
class GateGroundingIssue:
    code: str
    message: str
    page: int | None = None


@dataclass(frozen=True)
class GateGroundingReport:
    blocking: bool
    issues: tuple[GateGroundingIssue, ...]


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


def _evidence_refs(gate: str, payload: dict[str, Any]) -> list[tuple[int | None, str]]:
    if gate == "reporting_direction":
        return [(None, str(value)) for value in payload.get("evidence", [])]
    key = "modules" if gate == "report_structure" else "pages"
    refs: list[tuple[int | None, str]] = []
    for item in payload.get(key, []):
        page = item.get("page") if gate != "report_structure" else None
        for value in item.get("evidence_ids", []):
            refs.append((int(page) if isinstance(page, int) else page, str(value)))
    return refs


def ground_gate_output(
    gate: str,
    draft: Any,
    evidence_ids: set[str],
    *,
    evidence_numbers: dict[str, set[str]] | None = None,
) -> GateGroundingReport:
    payload = draft.payload
    issues: list[GateGroundingIssue] = []
    refs = _evidence_refs(gate, payload)
    for page, evidence_id in refs:
        if evidence_id not in evidence_ids:
            issues.append(GateGroundingIssue("unknown_evidence_id", f"unknown evidence ID: {evidence_id}", page))

    if gate == "reporting_direction":
        options = payload.get("options", [])
        option_values = {str(item.get("id")) for item in options} | {str(item.get("label")) for item in options}
        if len(options) < 2:
            issues.append(GateGroundingIssue("insufficient_direction_options", "reporting_direction requires at least two options"))
        if str(payload.get("recommendation")) not in option_values:
            issues.append(GateGroundingIssue("invalid_recommendation", "recommendation does not match a direction option"))
    elif gate == "report_structure":
        modules = payload.get("modules", [])
        if not 2 <= len(modules) <= 8:
            issues.append(GateGroundingIssue("invalid_module_count", "report_structure module count must be between 2 and 8"))
        for item in modules:
            for field in ("title", "focus", "evidence_ids"):
                if not item.get(field):
                    issues.append(GateGroundingIssue("missing_module_field", f"module is missing {field}"))
    else:
        pages = payload.get("pages", [])
        if not pages:
            issues.append(GateGroundingIssue("no_content_pages", f"{gate} must contain at least one page"))
        required = (
            ("page", "title", "role", "detail", "evidence_ids", "caveat", "visual", "chart_plan", "meaning", "transition", "density", "components")
            if gate == "page_design"
            else ("page", "title", "visible_content", "evidence_ids", "source_locations", "completeness", "density", "meaning", "transition")
        )
        for item in pages:
            page = item.get("page") if isinstance(item.get("page"), int) else None
            for field in required:
                if not item.get(field):
                    issues.append(GateGroundingIssue("missing_page_field", f"page is missing {field}", page))
            if gate == "business_script" and isinstance(item.get("completeness"), dict):
                for category in ("事实", "数字", "分类", "边界", "请求事项"):
                    if not item["completeness"].get(category):
                        issues.append(GateGroundingIssue("missing_completeness_category", f"page is missing completeness category: {category}", page))
            if gate == "business_script" and evidence_numbers:
                cited_numbers = {
                    number
                    for evidence_id in item.get("evidence_ids", [])
                    for number in evidence_numbers.get(str(evidence_id), set())
                }
                visible_numbers = set(_NUMBER_RE.findall(" ".join(str(value) for value in item.get("visible_content", []))))
                for number in sorted(visible_numbers - cited_numbers):
                    issues.append(GateGroundingIssue("visible_number_not_grounded", f"visible number is not grounded: {number}", page))
    return GateGroundingReport(blocking=bool(issues), issues=tuple(issues))

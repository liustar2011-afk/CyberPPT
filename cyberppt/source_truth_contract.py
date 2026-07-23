"""Structured Source Truth contracts and deterministic completeness audits."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


SCHEMA = "cyberppt.source_truth.v1"
EVIDENCE_TYPES = frozenset({"F", "J", "R", "B", "U"})
PRIORITIES = frozenset({"P0", "P1", "P2"})
REQUIRED_FIELDS = ("sources", "coverage_targets", "records", "conclusions", "pages", "retry")
PRECISE_LOCATOR_FIELDS = ("paragraph", "table", "table_row", "cell")
NUMERIC_FIELDS = ("raw_value", "raw_unit", "period", "scope")
BOUNDARY_STATUSES = ("待核", "待确认", "待摸底", "拟建议", "阶段判断", "暂缓", "条件成熟后")


@dataclass(frozen=True)
class SourceTruthIssue:
    code: str
    message: str
    source_ids: tuple[str, ...] = ()
    retry_strategy: str = "section_sweep"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_source_truth(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid source truth JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("source truth root must be an object")
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")
    for field in ("sources", "coverage_targets", "records", "conclusions", "pages"):
        if not isinstance(payload.get(field), list):
            raise ValueError(f"{field} must be an array")
    if not isinstance(payload.get("retry"), dict):
        raise ValueError("retry must be an object")
    return payload


def _items(payload: dict[str, object], field: str) -> list[dict[str, object]]:
    raw = payload.get(field)
    if not isinstance(raw, list):
        return []
    return [item for item in raw if isinstance(item, dict)]


def _refs(item: dict[str, object], field: str) -> list[str]:
    raw = item.get(field)
    if not isinstance(raw, list):
        return []
    return [str(value) for value in raw if str(value)]


def _record_issues(records: list[dict[str, object]]) -> list[SourceTruthIssue]:
    issues: list[SourceTruthIssue] = []
    seen: set[str] = set()
    for record in records:
        source_id = str(record.get("id") or "")
        ids = (source_id,) if source_id else ()
        evidence_type = record.get("type")
        if (
            not source_id
            or source_id in seen
            or not isinstance(evidence_type, str)
            or evidence_type not in EVIDENCE_TYPES
        ):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_RECORD_COMPOSITE",
                    "Each record must have one unique ID and exactly one evidence type.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        seen.add(source_id)
        if record.get("priority") not in PRIORITIES:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_PRIORITY_INVALID",
                    "Evidence priority must be P0, P1, or P2.",
                    ids,
                )
            )
        locator = record.get("source_locator")
        if (
            not isinstance(locator, dict)
            or not locator.get("source_id")
            or not locator.get("file")
            or not locator.get("section")
            or not any(locator.get(field) not in (None, "") for field in PRECISE_LOCATOR_FIELDS)
        ):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_LOCATOR_IMPRECISE",
                    "Source location must resolve to a paragraph, table, table row, or cell.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        if not str(record.get("quote") or "").strip():
            issues.append(
                SourceTruthIssue(
                    "SOURCE_QUOTE_MISSING",
                    "Evidence needs a verifiable source quote.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        numeric = record.get("numeric")
        if isinstance(numeric, dict) and any(numeric.get(field) in (None, "") for field in NUMERIC_FIELDS):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_NUMERIC_FIELDS_MISSING",
                    "Numeric evidence must retain value, unit, period, and scope.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        status = str(record.get("status") or "")
        if evidence_type == "F" and status in BOUNDARY_STATUSES:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_TYPE_STATUS_CONFLICT",
                    "Fact records cannot use proposed, conditional, or unknown status.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        if evidence_type == "U" and status not in BOUNDARY_STATUSES:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_TYPE_STATUS_CONFLICT",
                    "Unknown records must retain an unknown or pending status.",
                    ids,
                    "structured_fact_sweep",
                )
            )
    return issues


def _coverage_issues(
    targets: list[dict[str, object]],
    record_ids: set[str],
) -> list[SourceTruthIssue]:
    issues: list[SourceTruthIssue] = []
    for target in targets:
        if target.get("required") is not True:
            continue
        refs = _refs(target, "record_refs")
        covered = bool(refs) and all(ref in record_ids for ref in refs)
        if covered:
            continue
        target_id = str(target.get("id") or "")
        ids = (target_id,) if target_id else ()
        kind = str(target.get("kind") or "")
        if kind == "table":
            issues.append(
                SourceTruthIssue(
                    "SOURCE_TABLE_COVERAGE_MISSING",
                    "A required source table is not mapped to atomic evidence records.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        if kind == "boundary":
            issues.append(
                SourceTruthIssue(
                    "SOURCE_BOUNDARY_COVERAGE_MISSING",
                    "A required condition, exclusion, or pending item is not mapped.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        if target.get("priority") in {"P0", "P1"}:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_PRIORITY_COVERAGE_MISSING",
                    "A required P0/P1 coverage target is unresolved.",
                    ids,
                    "structured_fact_sweep",
                )
            )
    return issues


def _traceability_issues(
    records: list[dict[str, object]],
    conclusions: list[dict[str, object]],
    pages: list[dict[str, object]],
) -> list[SourceTruthIssue]:
    record_ids = {str(item.get("id") or "") for item in records}
    conclusion_ids = {str(item.get("id") or "") for item in conclusions}
    page_ids = {str(item.get("id") or "") for item in pages}
    broken: set[str] = set()
    for record in records:
        source_id = str(record.get("id") or "")
        if any(ref not in conclusion_ids for ref in _refs(record, "supports")):
            broken.add(source_id)
        if any(ref not in page_ids for ref in _refs(record, "page_refs")):
            broken.add(source_id)
    for item in conclusions + pages:
        item_id = str(item.get("id") or "")
        refs = _refs(item, "source_refs")
        if any(ref not in record_ids for ref in refs):
            broken.add(item_id)
    if not broken:
        return []
    return [
        SourceTruthIssue(
            "SOURCE_TRACEABILITY_BROKEN",
            "Evidence, conclusions, and pages must resolve in both directions.",
            tuple(sorted(broken)),
            "traceability_rebuild",
        )
    ]


def audit_source_truth(payload: dict[str, object]) -> list[SourceTruthIssue]:
    records = _items(payload, "records")
    conclusions = _items(payload, "conclusions")
    pages = _items(payload, "pages")
    record_ids = {str(item.get("id") or "") for item in records}
    issues = _record_issues(records)
    issues.extend(_coverage_issues(_items(payload, "coverage_targets"), record_ids))
    issues.extend(_traceability_issues(records, conclusions, pages))
    return sorted(issues, key=lambda item: (item.code, item.source_ids[:1]))


def source_truth_retry_directive(
    issues: list[SourceTruthIssue],
    previous_strategy: str = "",
) -> dict[str, object]:
    preferred = [issue.retry_strategy for issue in issues]
    if "traceability_rebuild" in preferred:
        strategy = "traceability_rebuild"
    elif "structured_fact_sweep" in preferred:
        strategy = "structured_fact_sweep"
    else:
        strategy = "section_sweep"
    progression = ("section_sweep", "structured_fact_sweep", "traceability_rebuild")
    if strategy == previous_strategy:
        index = progression.index(strategy) if strategy in progression else -1
        strategy = progression[min(index + 1, len(progression) - 1)]
    return {
        "required": bool(issues),
        "issue_codes": list(dict.fromkeys(issue.code for issue in issues)),
        "strategy": strategy,
        "instruction": "Change extraction direction, preserve current evidence, and submit the next numbered attempt.",
    }

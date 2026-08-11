"""Structured Source Truth contracts and deterministic completeness audits."""

from __future__ import annotations

import json
import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from cyberppt.argument_flow_contract import CLAIM_ROLES, PAGE_ARGUMENT_ROLES


SCHEMA = "cyberppt.source_truth.v1"
EVIDENCE_TYPES = frozenset({"F", "J", "R", "B", "U"})
PRIORITIES = frozenset({"P0", "P1", "P2"})
REQUIRED_FIELDS = ("sources", "coverage_targets", "records", "conclusions", "pages", "retry")
DOCUMENT_SEMANTIC_FIELDS = (
    "document_role",
    "subject_of_report",
    "primary_thesis",
    "decision_boundary",
    "source_refs",
)
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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def collect_source_receipts(
    payload: dict[str, object],
    roots: tuple[Path, ...] = (),
) -> list[dict[str, object]]:
    """Create lightweight, reproducible receipts for declared source files."""

    receipts: list[dict[str, object]] = []
    for source in _items(payload, "sources"):
        source_id = str(source.get("id") or "")
        declared = str(source.get("file") or "")
        candidates = [Path(declared).expanduser()] if Path(declared).is_absolute() else [
            root.expanduser().resolve() / declared for root in roots
        ]
        resolved = next((candidate for candidate in candidates if candidate.is_file()), None)
        receipt: dict[str, object] = {
            "source_id": source_id,
            "declared_file": declared,
            "present": resolved is not None,
        }
        if resolved is None:
            receipt["status"] = "missing"
        else:
            raw = resolved.read_bytes()
            receipt.update(
                {
                    "status": "verified",
                    "path": str(resolved),
                    "bytes": len(raw),
                    "sha256": _sha256_file(resolved),
                }
            )
        receipts.append(receipt)
    return receipts


def audit_source_receipts(
    receipts: list[dict[str, object]],
    *,
    required: bool = False,
    expected: object = None,
) -> list[SourceTruthIssue]:
    """Validate receipt shape and optionally fail when a declared file is absent."""

    issues: list[SourceTruthIssue] = []
    expected_by_id = {
        str(item.get("source_id")): str(item.get("sha256") or "")
        for item in expected
        if isinstance(item, dict) and item.get("source_id")
    } if isinstance(expected, list) else {}
    for receipt in receipts:
        source_id = str(receipt.get("source_id") or "")
        ids = (source_id,) if source_id else ()
        present = receipt.get("present") is True
        digest = str(receipt.get("sha256") or "")
        if required and not present:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_MATERIAL_RECEIPT_MISSING",
                    "Declared source material is unavailable; record a verified file receipt before relying on it.",
                    ids,
                    "request_missing_inputs",
                )
            )
        if present and (
            len(digest) != 64
            or digest != digest.lower()
            or any(char not in "0123456789abcdef" for char in digest)
            ):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_MATERIAL_RECEIPT_INVALID",
                    "A present source receipt must contain a lowercase SHA-256 digest.",
                    ids,
                    "structured_fact_sweep",
                )
            )
        expected_digest = expected_by_id.get(source_id)
        if present and expected_digest and expected_digest != digest:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_MATERIAL_RECEIPT_CHANGED",
                    "Source material hash differs from the previously recorded receipt; refresh Source Truth before proceeding.",
                    ids,
                    "section_sweep",
                )
            )
    return issues


def load_source_truth(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid source truth JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("source truth root must be an object")
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"schema must be {SCHEMA}")
    required_fields = (
        tuple(field for field in REQUIRED_FIELDS if field != "retry")
        if payload.get("projection_mode") == "semantic_atomic_items"
        else REQUIRED_FIELDS
    )
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")
    for field in ("sources", "coverage_targets", "records", "conclusions", "pages"):
        if not isinstance(payload.get(field), list):
            raise ValueError(f"{field} must be an array")
    if "retry" in payload and not isinstance(payload.get("retry"), dict):
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


def _semantic_record_issues(
    records: list[dict[str, object]],
    *,
    strict: bool,
) -> list[SourceTruthIssue]:
    if not strict:
        return []
    issues: list[SourceTruthIssue] = []
    record_ids = {str(record.get("id") or "") for record in records}
    for record in records:
        source_id = str(record.get("id") or "")
        ids = (source_id,) if source_id else ()
        claim_role = str(record.get("claim_role") or "")
        raw_units = record.get("semantic_units")
        units = (
            [unit for unit in raw_units if isinstance(unit, dict)]
            if isinstance(raw_units, list)
            else []
        )
        if len(units) == 1:
            statement = str(record.get("statement") or "")
            source_unit_refs = _refs(record, "source_unit_refs")
            independent_markers = sum(
                statement.count(mark) for mark in ("；", ";", "。")
            )
            if len(source_unit_refs) >= 3 or independent_markers >= 3:
                issues.append(
                    SourceTruthIssue(
                        "SOURCE_RECORD_ATOMICITY_REQUIRED",
                        "Strict Source Truth records spanning several source units or independent clauses must split semantic_units; one summary unit cannot prove atomic retention.",
                        ids,
                        "split_semantic_units",
                    )
                )
        unit_roles = {str(unit.get("claim_role") or "") for unit in units}
        if claim_role not in CLAIM_ROLES or not units or "" in unit_roles:
            issues.append(
                SourceTruthIssue(
                    "SOURCE_SEMANTIC_FIELDS_MISSING",
                    "Strict evidence records need a valid claim role and semantic units.",
                    ids,
                    "split_semantic_units",
                )
            )
        if len(unit_roles) > 1 or (unit_roles and claim_role not in unit_roles):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_RECORD_MIXED_CLAIMS",
                    "Each evidence record must contain semantic units with one claim role.",
                    ids,
                    "split_semantic_units",
                )
            )
        if record.get("type") == "F" and any(role != "fact" for role in unit_roles):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_FACT_CONTAINS_RECOMMENDATION",
                    "Fact records cannot carry judgments, recommendations, or boundaries.",
                    ids,
                    "split_semantic_units",
                )
            )
        dependencies = _refs(record, "depends_on")
        if any(dependency not in record_ids for dependency in dependencies):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_DEPENDENCY_MISSING",
                    "Claim dependencies must resolve to another evidence record.",
                    ids,
                    "rebuild_claim_dependencies",
                )
            )
        allowed = set(_refs(record, "allowed_page_roles"))
        forbidden = set(_refs(record, "forbidden_page_roles"))
        if (
            any(role not in PAGE_ARGUMENT_ROLES for role in allowed | forbidden)
            or bool(allowed & forbidden)
        ):
            issues.append(
                SourceTruthIssue(
                    "SOURCE_PAGE_ROLE_INCOMPATIBLE",
                    "Evidence page-role permissions must be valid and non-overlapping.",
                    ids,
                    "reassign_claim_page_role",
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


def _priority_hierarchy_issues(
    records: list[dict[str, object]],
    *,
    strict: bool,
) -> list[SourceTruthIssue]:
    """Reject long evidence inventories that preserve coverage but flatten importance."""

    if not strict or len(records) < 40:
        return []
    counts = {
        priority: sum(1 for record in records if record.get("priority") == priority)
        for priority in PRIORITIES
    }
    minimum_detail = 1 if len(records) < 80 else max(5, math.ceil(len(records) * 0.10))
    if counts["P0"] > 0 and counts["P2"] >= minimum_detail:
        return []
    return [
        SourceTruthIssue(
            "SOURCE_PRIORITY_HIERARCHY_FLAT",
            "Long strict Source Truth inventories must distinguish page-forming P0, "
            "module-supporting P1, and retained-detail P2 evidence. Complete retention "
            "does not make every source item equally prominent.",
            retry_strategy="rebalance_source_priority",
        )
    ]


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


def _document_semantic_issues(payload: dict[str, object]) -> list[SourceTruthIssue]:
    """Require a source-grounded whole-document identity before page planning."""

    if payload.get("document_semantics_mode") != "required":
        return []
    semantics = payload.get("document_semantics")
    if not isinstance(semantics, dict):
        return [
            SourceTruthIssue(
                "DOCUMENT_SEMANTICS_MISSING",
                "Source Truth must distinguish the document role, subject of report, primary thesis, and decision boundary before outlining.",
                retry_strategy="rebuild_from_semantic_understanding",
            )
        ]
    missing = [field for field in DOCUMENT_SEMANTIC_FIELDS if not semantics.get(field)]
    refs = _refs(semantics, "source_refs")
    record_ids = {str(item.get("id") or "") for item in _items(payload, "records")}
    if missing or not refs or not set(refs).issubset(record_ids):
        return [
            SourceTruthIssue(
                "DOCUMENT_SEMANTICS_INVALID",
                "Document semantics fields must be non-empty and cite existing Source Truth records.",
                tuple(sorted(set(refs) - record_ids)),
                "rebuild_from_semantic_understanding",
            )
        ]
    if not _items(payload, "conclusions"):
        return [
            SourceTruthIssue(
                "DOCUMENT_CONCLUSIONS_MISSING",
                "A required document-semantic contract needs at least one source-grounded whole-document conclusion.",
                retry_strategy="rebuild_from_semantic_understanding",
            )
        ]
    return []


def audit_source_truth(payload: dict[str, object]) -> list[SourceTruthIssue]:
    records = _items(payload, "records")
    conclusions = _items(payload, "conclusions")
    pages = _items(payload, "pages")
    record_ids = {str(item.get("id") or "") for item in records}
    issues = _record_issues(records)
    issues.extend(
        _semantic_record_issues(
            records,
            strict=payload.get("argument_contract_mode", "legacy") == "strict",
        )
    )
    issues.extend(_coverage_issues(_items(payload, "coverage_targets"), record_ids))
    issues.extend(
        _priority_hierarchy_issues(
            records,
            strict=payload.get("argument_contract_mode", "legacy") == "strict",
        )
    )
    issues.extend(_document_semantic_issues(payload))
    issues.extend(_traceability_issues(records, conclusions, pages))
    return sorted(issues, key=lambda item: (item.code, item.source_ids[:1]))


def source_truth_atomicity_warnings(
    payload: dict[str, object],
) -> list[SourceTruthIssue]:
    """Flag likely compound evidence records without blocking Stage 01."""

    warnings: list[SourceTruthIssue] = []
    for record in _items(payload, "records"):
        statement = str(record.get("statement") or record.get("quote") or "").strip()
        semantic_units = _refs(record, "semantic_units")
        clause_count = sum(statement.count(mark) for mark in ("；", ";", "。"))
        if len(statement) >= 100 and clause_count >= 3 and len(semantic_units) <= 1:
            source_id = str(record.get("id") or "")
            warnings.append(
                SourceTruthIssue(
                    "SOURCE_RECORD_ATOMICITY_WARNING",
                    "This evidence record may contain multiple independent claims; "
                    "split it when those claims support different page jobs.",
                    (source_id,) if source_id else (),
                    "split_semantic_units",
                )
            )
    return warnings


def source_truth_retry_directive(
    issues: list[SourceTruthIssue],
    previous_strategy: str = "",
) -> dict[str, object]:
    preferred = [issue.retry_strategy for issue in issues]
    semantic_progression = (
        "split_semantic_units",
        "rebuild_claim_dependencies",
        "reassign_claim_page_role",
    )
    if "split_semantic_units" in preferred:
        strategy = "split_semantic_units"
    elif "rebuild_claim_dependencies" in preferred:
        strategy = "rebuild_claim_dependencies"
    elif "reassign_claim_page_role" in preferred:
        strategy = "reassign_claim_page_role"
    elif "traceability_rebuild" in preferred:
        strategy = "traceability_rebuild"
    elif "structured_fact_sweep" in preferred:
        strategy = "structured_fact_sweep"
    else:
        strategy = "section_sweep"
    progression = (
        "section_sweep",
        "structured_fact_sweep",
        "traceability_rebuild",
        *semantic_progression,
    )
    if strategy == previous_strategy:
        index = progression.index(strategy) if strategy in progression else -1
        strategy = progression[min(index + 1, len(progression) - 1)]
    return {
        "required": bool(issues),
        "issue_codes": list(dict.fromkeys(issue.code for issue in issues)),
        "strategy": strategy,
        "instruction": "Change extraction direction, preserve current evidence, and submit the next numbered attempt.",
    }

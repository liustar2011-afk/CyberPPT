"""Focused report builders for Script Engine validation, audit and trace commands."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .analysis_audit import (
    audit_deck_plan,
    audit_final_script,
    audit_foundation_analysis,
    validate_source_index_coverage,
)
from .analysis_audits.composed_trace import critic_priorities, trace_composed
from .contracts import (
    load_json,
    validate_deck_plan,
    validate_final_script,
    validate_foundation,
    validate_source_refs_coverage,
)
from .plan_review import render_plan_review
from .source_index import (
    build_source_index_file,
    validate_script_foundation_against_index,
)


VALIDATORS = {
    "foundation": validate_foundation,
    "plan": validate_deck_plan,
    "final": validate_final_script,
}
ProfileResolver = Callable[[Path], str]


def validate_artifact_report(kind: str, path: Path) -> tuple[dict, int]:
    payload = load_json(path)
    issues = VALIDATORS[kind](payload)
    return (
        {
            "kind": kind,
            "path": str(path.resolve()),
            "status": "passed" if not issues else "failed",
            "issues": issues,
        },
        0 if not issues else 1,
    )


def foundation_audit_report(
    path: Path,
    *,
    profile_resolver: ProfileResolver,
) -> tuple[dict, int]:
    payload = load_json(path)
    issues = validate_foundation(payload)
    audit_issues, warnings = audit_foundation_analysis(payload)
    issues += audit_issues
    source_index_path = path.parent / ".cache" / "source-index.json"
    if profile_resolver(path) not in {"strict", "legacy"} and source_index_path.is_file():
        source_index = load_json(source_index_path)
        if source_index.get("schema") == "cyberppt.source_index.v2":
            issues += validate_script_foundation_against_index(payload, source_index)
    issues = list(dict.fromkeys(issues))
    return (
        {
            "kind": "foundation-analysis",
            "path": str(path.resolve()),
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "warnings": warnings,
        },
        0 if not issues else 1,
    )


def plan_audit_report(plan_path: Path, foundation_path: Path) -> tuple[dict, int]:
    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    issues = validate_deck_plan(plan) + validate_foundation(foundation)
    audit_issues, warnings = audit_deck_plan(plan, foundation)
    issues += audit_issues
    return (
        {
            "kind": "source-faithful-plan",
            "plan": str(plan_path.resolve()),
            "foundation": str(foundation_path.resolve()),
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "warnings": warnings,
        },
        0 if not issues else 1,
    )


def plan_review_text(plan_path: Path, foundation_path: Path) -> tuple[str, int]:
    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    issues = validate_deck_plan(plan) + validate_foundation(foundation)
    audit_issues, warnings = audit_deck_plan(plan, foundation)
    issues += audit_issues
    return (
        render_plan_review(plan, foundation, issues=issues, warnings=warnings),
        0 if not issues else 1,
    )


def final_audit_report(
    final_path: Path,
    plan_path: Path,
    foundation_path: Path,
) -> tuple[dict, int]:
    final_payload = load_json(final_path)
    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    issues = (
        validate_final_script(final_payload)
        + validate_deck_plan(plan)
        + validate_foundation(foundation)
    )
    audit_issues, warnings = audit_final_script(final_payload, plan, foundation)
    issues += audit_issues
    trace = trace_composed(final_payload, foundation)
    return (
        {
            "kind": "final-semantic-inheritance",
            "final": str(final_path.resolve()),
            "plan": str(plan_path.resolve()),
            "foundation": str(foundation_path.resolve()),
            "status": "passed" if not issues else "failed",
            "issues": issues,
            "warnings": warnings,
            "critic_priorities": critic_priorities(
                final_payload,
                plan,
                foundation,
                trace=trace,
            ),
        },
        0 if not issues else 1,
    )


def composed_trace_report(
    final_path: Path,
    foundation_path: Path,
    *,
    n: int = 3,
) -> tuple[dict, int]:
    final_payload = load_json(final_path)
    foundation = load_json(foundation_path)
    report = trace_composed(final_payload, foundation, n=n)
    report.update(
        {
            "final": str(final_path.resolve()),
            "foundation": str(foundation_path.resolve()),
            "critic_priorities": critic_priorities(
                final_payload,
                {},
                foundation,
                trace=report,
            ),
        }
    )
    return report, 0 if report["status"] == "passed" else 1


def source_refs_report(
    final_path: Path,
    foundation_path: Path,
    source_index_path: Path | None = None,
) -> tuple[dict, int]:
    final_payload = load_json(final_path)
    foundation_payload = load_json(foundation_path)
    issues = validate_source_refs_coverage(final_payload, foundation_payload)
    if source_index_path is not None:
        issues += validate_source_index_coverage(final_payload, load_json(source_index_path))
    return (
        {
            "kind": "source-refs-coverage",
            "final": str(final_path.resolve()),
            "foundation": str(foundation_path.resolve()),
            "source_index": str(source_index_path.resolve()) if source_index_path else None,
            "status": "passed" if not issues else "failed",
            "issues": issues,
        },
        0 if not issues else 1,
    )


def build_source_index_report(
    source_extract: Path,
    output: Path,
    source_file: str | None,
) -> tuple[dict, int]:
    index = build_source_index_file(source_extract, output, source_file=source_file)
    return (
        {
            "kind": "source-index",
            "status": "created",
            "source_extract": str(source_extract.resolve()),
            "output": str(output.resolve()),
            "mapped_refs": len(index.get("refs") or {}),
            "structure_nodes": len(index.get("source_structure") or []),
        },
        0,
    )


__all__ = [
    "VALIDATORS",
    "build_source_index_report",
    "composed_trace_report",
    "final_audit_report",
    "foundation_audit_report",
    "plan_audit_report",
    "plan_review_text",
    "source_refs_report",
    "validate_artifact_report",
]

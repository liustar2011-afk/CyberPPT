"""Run the lightweight Source Truth audit."""

from __future__ import annotations

from pathlib import Path

from cyberppt.source_truth_contract import (
    SourceTruthIssue,
    audit_source_truth,
    source_truth_diagnostic_warnings,
    load_source_truth,
    source_truth_retry_directive,
)
from cyberppt.semantic_understanding import SEMANTIC_ARGUMENT_MODEL
from cyberppt.source_argument_model import load_model
from cyberppt.semantic_cross_audit import (
    semantic_evidence_cross_issues,
    source_chapter_placement_suggestions,
)
from cyberppt.source_document_map import load_source_units
from cyberppt.outline_contract import load_outline


def _coverage_summary(payload: dict[str, object]) -> dict[str, int]:
    targets = payload.get("coverage_targets")
    records = payload.get("records")
    target_items = [item for item in targets if isinstance(item, dict)] if isinstance(targets, list) else []
    record_items = [item for item in records if isinstance(item, dict)] if isinstance(records, list) else []
    required = [item for item in target_items if item.get("required") is True]
    covered = [
        item
        for item in required
        if isinstance(item.get("record_refs"), list) and bool(item.get("record_refs"))
    ]
    return {
        "source_count": len(payload.get("sources", [])) if isinstance(payload.get("sources"), list) else 0,
        "record_count": len(record_items),
        "required_targets": len(required),
        "covered_targets": len(covered),
    }


def run_source_truth_audit(
    project: Path,
    input_path: Path,
) -> tuple[int, dict[str, object]]:
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    payload = load_source_truth(input_path.expanduser().resolve())
    argument_model_path = project / SEMANTIC_ARGUMENT_MODEL
    if not argument_model_path.is_file():
        raise FileNotFoundError(
            "lightweight Source Truth audit requires semantic-argument-model.json; "
            "complete semantic understanding and run semantic-check first"
        )
    argument_model = load_model(argument_model_path)
    issues = audit_source_truth(payload)
    semantic_cross_audit = None
    if argument_model is not None:
        source_semantics = payload.get("document_semantics")
        model_thesis = argument_model.get("document_thesis")
        model_semantics = argument_model.get("document_semantics")
        if isinstance(source_semantics, dict) and isinstance(model_thesis, dict):
            if str(source_semantics.get("primary_thesis") or "").strip() != str(model_thesis.get("statement") or "").strip():
                issues.append(
                    SourceTruthIssue(
                        "SOURCE_TRUTH_THESIS_DRIFTED",
                        "Source Truth 的 primary_thesis 必须复制语义阶段 document_thesis.statement，不能在证据整理阶段重新归纳主论点。",
                        retry_strategy="rebuild_from_semantic_understanding",
                    )
                )
        if isinstance(source_semantics, dict) and isinstance(model_semantics, dict):
            fields = ("document_role", "subject_of_report", "primary_thesis", "decision_boundary")
            # New semantic intent fields are authored in Stage 00 and must be
            # copied verbatim; Source Truth may add source_refs but may not
            # replace the author's purpose or argument method with a shorter
            # evidence-derived summary.
            fields += tuple(
                field
                for field in ("author_purpose", "argument_method", "supporting_basis")
                if field in model_semantics
            )
            for field in fields:
                expected = str(model_semantics.get(field) or "").strip()
                actual = str(source_semantics.get(field) or "").strip()
                if expected and actual != expected:
                    issues.append(
                        SourceTruthIssue(
                            "SOURCE_TRUTH_DOCUMENT_SEMANTICS_DRIFTED",
                            f"Source Truth 的 document_semantics.{field} 必须复制语义阶段 document_semantics，不能在证据整理阶段重新归纳。",
                            retry_strategy="rebuild_from_semantic_understanding",
                        )
                    )
        source_unit_ids = {
            str(item.get("unit_id") or "")
            for item in load_source_units(project)
            if str(item.get("unit_id") or "")
        }
        cross_issues = semantic_evidence_cross_issues(
            argument_model,
            payload,
            source_unit_ids=source_unit_ids,
        )
        semantic_cross_audit = {
            "schema": "cyberppt.semantic_evidence_cross_audit.v1",
            "status": "passed" if not cross_issues else "rewrite_required",
            "source_unit_count": len(source_unit_ids),
            "issues": cross_issues,
            "mode": "lightweight",
        }
        issues.extend(
            SourceTruthIssue(
                str(item.get("code") or "SEMANTIC_EVIDENCE_CROSS_AUDIT_FAILED"),
                str(item.get("message") or "Semantic/evidence cross-audit failed."),
                tuple(str(value) for value in item.get("source_ids", []) if str(value)),
                str(item.get("retry_strategy") or "rebuild_semantic_evidence_binding"),
            )
            for item in semantic_cross_audit.get("issues", [])
            if isinstance(item, dict)
        )
    warnings = source_truth_diagnostic_warnings(payload)
    source_units = load_source_units(project)
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    try:
        outline = load_outline(outline_path, lightweight=True) if outline_path.is_file() else None
    except ValueError:
        outline = None
    placement_diagnostics = source_chapter_placement_suggestions(
        argument_model,
        payload,
        source_units=source_units,
        outline=outline,
    )
    cross_issue_items = (
        semantic_cross_audit.get("issues", [])
        if isinstance(semantic_cross_audit, dict)
        else []
    )
    uncovered_source_units = {
        str(source_id)
        for item in cross_issue_items
        if isinstance(item, dict)
        and item.get("code") == "SOURCE_TRUTH_PROTECTED_EVIDENCE_GAP"
        for source_id in item.get("source_ids", [])
        if str(source_id).startswith("SU-")
    }
    directive = source_truth_retry_directive(issues, "")
    report: dict[str, object] = {
        "schema": "cyberppt.source_truth_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "coverage": _coverage_summary(payload),
        "issues": [issue.to_dict() for issue in issues],
        "warnings": [warning.to_dict() for warning in warnings],
        "warning_count": len(warnings),
        "repair_summary": {
            "uncovered_source_units": len(uncovered_source_units),
            "unresolved_core_claims": sum(
                item.get("code") == "SEMANTIC_CORE_CLAIM_UNRESOLVED"
                for item in cross_issue_items
                if isinstance(item, dict)
            ),
            "atomic_split_suggestions": sum(
                warning.retry_strategy == "split_semantic_units"
                for warning in warnings
            ),
            "priority_review_suggestions": sum(
                warning.code == "SOURCE_PRIORITY_NARRATIVE_WARNING"
                for warning in warnings
            ),
            "chapter_placement_suggestions": len(placement_diagnostics),
        },
        "retry_directive": directive,
        "semantic_argument_model": str(project / SEMANTIC_ARGUMENT_MODEL) if argument_model is not None else None,
        "semantic_evidence_cross_audit": semantic_cross_audit,
        "source_chapter_placement_diagnostics": placement_diagnostics,
        "mode": "lightweight",
    }
    return (0 if not issues else 4), report

"""Run the lightweight outline content/structure audit."""

from __future__ import annotations

from pathlib import Path

from cyberppt.argument_flow_contract import (
    argument_graph_summary,
    audit_argument_flow,
)
from cyberppt.outline_contract import audit_outline, load_outline, retry_directive
from cyberppt.semantic_understanding import SEMANTIC_ARGUMENT_MODEL
from cyberppt.source_argument_model import audit_outline_consumption, load_model
from cyberppt.source_truth_contract import load_source_truth


def run_outline_audit(
    project: Path,
    input_path: Path,
    source_truth_path: Path | None = None,
) -> tuple[int, dict[str, object]]:
    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    payload = load_outline(input_path.expanduser().resolve(), lightweight=True)
    resolved_source_truth = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "source-truth.json"
    )
    source_truth = (
        load_source_truth(resolved_source_truth)
        if resolved_source_truth.exists()
        else None
    )
    if source_truth_path is not None and source_truth is None:
        raise FileNotFoundError(f"source truth does not exist: {resolved_source_truth}")
    argument_model_path = project / SEMANTIC_ARGUMENT_MODEL
    argument_model = load_model(argument_model_path) if argument_model_path.is_file() else None
    argument_issues = (
        audit_argument_flow(payload, source_truth)
        if source_truth is not None
        else []
    )
    argument_model_issues = (
        audit_outline_consumption(payload, argument_model)
        if payload.get("semantic_argument_model_mode") == "required" or argument_model is not None
        else []
    )
    issues = audit_outline(
        payload,
        source_truth,
        argument_model,
        argument_flow_issues=argument_issues,
        argument_model_issues=argument_model_issues,
    )
    # audit_outline() already includes audit_outline_consumption().  Keep the
    # raw result for the report, but do not append it a second time.
    directive = retry_directive(issues, "")
    report: dict[str, object] = {
        "schema": "cyberppt.outline_audit.v1",
        "status": "rewrite_required" if issues else "passed",
        "issues": [issue.to_dict() for issue in issues],
        "retry_directive": directive,
        "argument_contract_mode": str(
            payload.get("argument_contract_mode") or "legacy"
        ),
        "semantic_contract_mode": (
            "source_relations"
            if payload.get("schema") == "cyberppt.outline.v2"
            else "legacy_argument_roles"
        ),
        "checked_source_truth": (
            str(resolved_source_truth) if source_truth is not None else None
        ),
        "semantic_argument_model": (
            str(project / SEMANTIC_ARGUMENT_MODEL) if argument_model is not None else None
        ),
        "argument_graph": argument_graph_summary(payload, source_truth),
        "argument_model_issues": argument_model_issues,
        "failed_edges": [
            list(edge)
            for issue in argument_issues
            for edge in issue.failed_edges
        ],
        "retry_scope": sorted(
            {
                page
                for issue in argument_issues
                for page in issue.pages
                if page
            }
        ),
        "mode": "lightweight",
    }
    return (0 if not issues else 4), report

"""Run the lightweight script quality audit."""

from __future__ import annotations

from pathlib import Path

from cyberppt.outline_contract import load_outline
from cyberppt.script_quality_contract import (
    audit_final_manuscript_form,
    audit_script_quality,
    build_communication_review,
    is_final_script_path,
    parse_script_markdown,
)
from cyberppt.source_truth_contract import load_source_truth


def run_script_audit(
    project: Path,
    input_path: Path,
    outline_path: Path | None = None,
    source_truth_path: Path | None = None,
) -> tuple[int, dict[str, object]]:
    project = project.expanduser().resolve()
    input_path = input_path.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    if not input_path.exists():
        raise FileNotFoundError(f"script does not exist: {input_path}")
    outline_path = (
        outline_path.expanduser().resolve()
        if outline_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "outline.json"
    )
    source_truth_path = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project
        / "workbench"
        / "stages"
        / "01-analysis"
        / "source-truth.json"
    )
    if not outline_path.exists():
        raise FileNotFoundError(f"outline does not exist: {outline_path}")
    outline = load_outline(outline_path, lightweight=True)
    if (
        not source_truth_path.exists()
        and outline.get("argument_contract_mode") == "strict"
    ):
        raise FileNotFoundError(
            f"strict script audit requires Source Truth: {source_truth_path}"
        )
    if not source_truth_path.exists():
        raise FileNotFoundError(
            f"source truth does not exist: {source_truth_path}"
        )
    source_truth = load_source_truth(source_truth_path)
    script_text = input_path.read_text(encoding="utf-8-sig")
    document = parse_script_markdown(script_text)
    issues = audit_script_quality(document, outline, source_truth)
    if is_final_script_path(input_path):
        issues.extend(audit_final_manuscript_form(script_text))
    communication_review = build_communication_review(document, outline)
    errors = [issue for issue in issues if issue.severity == "error"]
    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    failed_pages = sorted(
        {page for issue in errors for page in issue.pages}
    )
    report = {
        "schema": "cyberppt.script_check.v1",
        "status": "rewrite_required" if errors else "passed",
        "quality_status": (
            "failed"
            if errors
            else "passed_with_warnings"
            if warning_count
            else "passed"
        ),
        "warning_count": warning_count,
        "input": str(input_path),
        "outline": str(outline_path),
        "source_truth": str(source_truth_path),
        "coverage": {
            "page_count": len(document.pages),
            "first_page": document.pages[0].page_id,
            "last_page": document.pages[-1].page_id,
        },
        "issues": [issue.to_dict() for issue in issues],
        "communication_review": communication_review,
        "failed_pages": failed_pages,
        "retry_scope": failed_pages,
        "persisted": False,
        "mode": "lightweight",
    }
    return (4 if errors else 0), report

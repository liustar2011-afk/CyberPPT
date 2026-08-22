"""Run same-rule, page-scoped script linting before final assembly."""

from __future__ import annotations

from pathlib import Path

from cyberppt.outline_contract import load_outline
from cyberppt.script_quality_contract import audit_script_quality, parse_script_path
from cyberppt.source_truth_contract import load_source_truth


def run_page_lint(
    project: Path,
    input_path: Path,
    page_id: str,
    outline_path: Path | None = None,
    source_truth_path: Path | None = None,
) -> tuple[int, dict[str, object]]:
    """Lint one authored page using the same page-level rules as script-audit.

    Cross-page continuity and final-manuscript rules intentionally stay in the
    full-script audit. This gives authors immediate local feedback without
    duplicating or weakening the production validator.
    """

    project = project.expanduser().resolve()
    input_path = input_path.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    if not input_path.exists():
        raise FileNotFoundError(f"script does not exist: {input_path}")
    if not page_id:
        raise ValueError("--page is required")
    resolved_outline = (
        outline_path.expanduser().resolve()
        if outline_path is not None
        else project / "workbench" / "stages" / "01-analysis" / "outline.json"
    )
    resolved_truth = (
        source_truth_path.expanduser().resolve()
        if source_truth_path is not None
        else project / "workbench" / "stages" / "01-analysis" / "source-truth.json"
    )
    outline = load_outline(resolved_outline, lightweight=True)
    source_truth = load_source_truth(resolved_truth)
    document = parse_script_path(input_path)
    if page_id not in {page.page_id for page in document.pages}:
        raise ValueError(f"page not found in script: {page_id}")
    issues = [
        issue
        for issue in audit_script_quality(document, outline, source_truth)
        if issue.pages == (page_id,)
    ]
    errors = [issue for issue in issues if issue.severity == "error"]
    return (
        4 if errors else 0,
        {
            "schema": "cyberppt.page_lint.v1",
            "status": "rewrite_required" if errors else "passed",
            "page_id": page_id,
            "input": str(input_path),
            "outline": str(resolved_outline),
            "source_truth": str(resolved_truth),
            "cross_page_checks_deferred": True,
            "issues": [issue.to_dict() for issue in issues],
        },
    )

"""Command line utilities for the standalone Script Engine boundary."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .audit_reports import (
    VALIDATORS,
    build_source_index_report,
    composed_trace_report,
    final_audit_report,
    foundation_audit_report,
    plan_audit_report,
    plan_review_text,
    source_refs_report,
    validate_artifact_report,
)
from .cli_parser import build_parser as _build_parser
from .delivery_commands import (
    delivery_sync_report,
    lint_report,
    outline_report,
    render_stage02_delivery,
)
from .final_quality import collect_final_lint_issues, partition_final_lint_findings
from .project_scaffold import create_project
from .project_status import build_project_status, project_profile_for_foundation

_project_profile_for_foundation = project_profile_for_foundation


def _print_report(report: dict, *, stderr: bool = False) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr if stderr else sys.stdout)


def _validate(kind: str, path: Path) -> int:
    report, exit_code = validate_artifact_report(kind, path)
    _print_report(report)
    return exit_code


def _audit_foundation(path: Path) -> int:
    report, exit_code = foundation_audit_report(
        path,
        profile_resolver=_project_profile_for_foundation,
    )
    _print_report(report)
    return exit_code


def _audit_plan(plan_path: Path, foundation_path: Path) -> int:
    report, exit_code = plan_audit_report(plan_path, foundation_path)
    _print_report(report)
    return exit_code


def _review_plan(plan_path: Path, foundation_path: Path) -> int:
    review, exit_code = plan_review_text(plan_path, foundation_path)
    print(review)
    return exit_code


def _audit_final(final_path: Path, plan_path: Path, foundation_path: Path) -> int:
    report, exit_code = final_audit_report(final_path, plan_path, foundation_path)
    _print_report(report)
    return exit_code


def _trace_composed(final_path: Path, foundation_path: Path, n: int = 3) -> int:
    report, exit_code = composed_trace_report(final_path, foundation_path, n=n)
    _print_report(report)
    return exit_code


def _check_refs(final_path: Path, foundation_path: Path, source_index_path: Path | None = None) -> int:
    report, exit_code = source_refs_report(final_path, foundation_path, source_index_path)
    _print_report(report)
    return exit_code


def _build_source_index(source_extract: Path, output: Path, source_file: str | None) -> int:
    report, exit_code = build_source_index_report(source_extract, output, source_file)
    _print_report(report)
    return exit_code


_final_lint_issues = collect_final_lint_issues


def _final_lint_findings(payload: dict, markdown: str) -> tuple[list[str], list[str]]:
    """Compatibility seam over the focused Final Script quality evaluator."""

    return partition_final_lint_findings(
        payload,
        markdown,
        issue_collector=_final_lint_issues,
    )


def _lint(final_path: Path) -> int:
    report, exit_code = lint_report(
        final_path,
        final_lint_findings=_final_lint_findings,
    )
    _print_report(report)
    return exit_code


def _outline(final_path: Path) -> int:
    report, exit_code = outline_report(final_path)
    _print_report(report)
    return exit_code


def _new_project(slug: str, base_dir: Path) -> int:
    try:
        project_dir = create_project(slug, base_dir)
    except (ValueError, FileExistsError) as error:
        _print_report({"status": "failed", "issues": [str(error)]}, stderr=True)
        return 1
    _print_report({"status": "created", "path": str(project_dir.resolve())})
    return 0


def _status(project_dir: Path) -> int:
    _print_report(
        build_project_status(
            project_dir,
            final_lint_findings=_final_lint_findings,
        )
    )
    return 0


def _render(input_path: Path, output_path: Path) -> int:
    rendered_path, error_report, exit_code = render_stage02_delivery(
        input_path,
        output_path,
        final_lint_findings=_final_lint_findings,
    )
    if error_report is not None:
        _print_report(error_report, stderr=True)
    elif rendered_path is not None:
        print(rendered_path)
    return exit_code


def _check_sync(final_path: Path, markdown_path: Path) -> int:
    report, exit_code = delivery_sync_report(
        final_path,
        markdown_path,
        final_lint_findings=_final_lint_findings,
    )
    _print_report(report)
    return exit_code


def build_parser():
    """Compatibility entry point for callers that import the parser builder from ``cli``."""

    return _build_parser(VALIDATORS)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "validate": return _validate(args.kind, Path(args.path))
    if args.command == "audit-foundation": return _audit_foundation(Path(args.foundation))
    if args.command == "audit-plan": return _audit_plan(Path(args.plan), Path(args.foundation))
    if args.command == "review-plan": return _review_plan(Path(args.plan), Path(args.foundation))
    if args.command == "audit-final": return _audit_final(Path(args.final), Path(args.plan), Path(args.foundation))
    if args.command == "trace-composed": return _trace_composed(Path(args.final), Path(args.foundation), args.n)
    if args.command == "build-source-index": return _build_source_index(Path(args.source_extract), Path(args.output), args.source_file)
    if args.command == "render-stage02": return _render(Path(args.input), Path(args.output))
    if args.command == "check-refs": return _check_refs(Path(args.final), Path(args.foundation), Path(args.source_index) if args.source_index else None)
    if args.command == "lint": return _lint(Path(args.final))
    if args.command == "outline": return _outline(Path(args.final))
    if args.command == "check-sync": return _check_sync(Path(args.final), Path(args.markdown))
    if args.command == "new-project": return _new_project(args.slug, Path(args.base_dir))
    if args.command == "status": return _status(Path(args.project_dir))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

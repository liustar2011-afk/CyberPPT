"""Command line utilities for the standalone Script Engine boundary."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis_audit import (
    audit_deck_plan,
    audit_final_script,
    audit_foundation_analysis,
    validate_source_index_coverage,
)
from .analysis_audits.composed_trace import critic_priorities, trace_composed
from .contracts import (
    check_declared_count,
    load_json,
    outline_final_script,
    validate_deck_plan,
    validate_final_script,
    validate_foundation,
    validate_source_refs_coverage,
)
from .final_quality import collect_final_lint_issues, partition_final_lint_findings
from .plan_review import render_plan_review
from .project_scaffold import create_project
from .project_status import build_project_status, project_profile_for_foundation
from .render import render_stage02_markdown
from .source_index import (
    build_source_index_file,
    validate_script_foundation_against_index,
)
from .text_io import write_text_lf

VALIDATORS = {"foundation": validate_foundation, "plan": validate_deck_plan, "final": validate_final_script}
_project_profile_for_foundation = project_profile_for_foundation


def _print_report(report: dict, *, stderr: bool = False) -> None:
    print(json.dumps(report, ensure_ascii=False, indent=2), file=sys.stderr if stderr else sys.stdout)


def _validate(kind: str, path: Path) -> int:
    payload = load_json(path)
    issues = VALIDATORS[kind](payload)
    _print_report({"kind": kind, "path": str(path.resolve()), "status": "passed" if not issues else "failed", "issues": issues})
    return 0 if not issues else 1


def _audit_foundation(path: Path) -> int:
    payload = load_json(path)
    issues = validate_foundation(payload)
    audit_issues, warnings = audit_foundation_analysis(payload)
    issues += audit_issues
    source_index_path = path.parent / ".cache" / "source-index.json"
    # ``source-index.json`` and ``reading_strategy`` belong to the script
    # profile. Strict and legacy Foundations are mechanical Source Truth
    # projections, so a stale script-profile cache must not select that audit.
    # Keep the historical sibling-index behavior for standalone Foundations
    # whose project profile cannot be discovered.
    if (
        _project_profile_for_foundation(path) not in {"strict", "legacy"}
        and source_index_path.is_file()
    ):
        source_index = load_json(source_index_path)
        if source_index.get("schema") == "cyberppt.source_index.v2":
            issues += validate_script_foundation_against_index(payload, source_index)
    issues = list(dict.fromkeys(issues))
    _print_report({"kind": "foundation-analysis", "path": str(path.resolve()), "status": "passed" if not issues else "failed", "issues": issues, "warnings": warnings})
    return 0 if not issues else 1


def _audit_plan(plan_path: Path, foundation_path: Path) -> int:
    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    issues = validate_deck_plan(plan) + validate_foundation(foundation)
    audit_issues, warnings = audit_deck_plan(plan, foundation)
    issues += audit_issues
    _print_report({"kind": "source-faithful-plan", "plan": str(plan_path.resolve()), "foundation": str(foundation_path.resolve()), "status": "passed" if not issues else "failed", "issues": issues, "warnings": warnings})
    return 0 if not issues else 1


def _review_plan(plan_path: Path, foundation_path: Path) -> int:
    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    issues = validate_deck_plan(plan) + validate_foundation(foundation)
    audit_issues, warnings = audit_deck_plan(plan, foundation)
    issues += audit_issues
    print(render_plan_review(plan, foundation, issues=issues, warnings=warnings))
    return 0 if not issues else 1


def _audit_final(final_path: Path, plan_path: Path, foundation_path: Path) -> int:
    final_payload = load_json(final_path)
    plan = load_json(plan_path)
    foundation = load_json(foundation_path)
    issues = validate_final_script(final_payload) + validate_deck_plan(plan) + validate_foundation(foundation)
    audit_issues, warnings = audit_final_script(final_payload, plan, foundation)
    issues += audit_issues
    trace = trace_composed(final_payload, foundation)
    _print_report({
        "kind": "final-semantic-inheritance",
        "final": str(final_path.resolve()),
        "plan": str(plan_path.resolve()),
        "foundation": str(foundation_path.resolve()),
        "status": "passed" if not issues else "failed",
        "issues": issues,
        "warnings": warnings,
        "critic_priorities": critic_priorities(
            final_payload, plan, foundation, trace=trace
        ),
    })
    return 0 if not issues else 1


def _trace_composed(final_path: Path, foundation_path: Path, n: int = 3) -> int:
    final_payload = load_json(final_path)
    foundation = load_json(foundation_path)
    report = trace_composed(final_payload, foundation, n=n)
    report.update(
        {
            "final": str(final_path.resolve()),
            "foundation": str(foundation_path.resolve()),
            "critic_priorities": critic_priorities(
                final_payload, {}, foundation, trace=report
            ),
        }
    )
    _print_report(report)
    return 0 if report["status"] == "passed" else 1


def _check_refs(final_path: Path, foundation_path: Path, source_index_path: Path | None = None) -> int:
    final_payload = load_json(final_path)
    foundation_payload = load_json(foundation_path)
    issues = validate_source_refs_coverage(final_payload, foundation_payload)
    if source_index_path is not None:
        issues += validate_source_index_coverage(final_payload, load_json(source_index_path))
    _print_report({"kind": "source-refs-coverage", "final": str(final_path.resolve()), "foundation": str(foundation_path.resolve()), "source_index": str(source_index_path.resolve()) if source_index_path else None, "status": "passed" if not issues else "failed", "issues": issues})
    return 0 if not issues else 1


def _build_source_index(source_extract: Path, output: Path, source_file: str | None) -> int:
    index = build_source_index_file(source_extract, output, source_file=source_file)
    _print_report({"kind": "source-index", "status": "created", "source_extract": str(source_extract.resolve()), "output": str(output.resolve()), "mapped_refs": len(index.get("refs") or {}), "structure_nodes": len(index.get("source_structure") or [])})
    return 0


_final_lint_issues = collect_final_lint_issues


def _final_lint_findings(payload: dict, markdown: str) -> tuple[list[str], list[str]]:
    """Compatibility seam over the focused Final Script quality evaluator."""

    return partition_final_lint_findings(
        payload,
        markdown,
        issue_collector=_final_lint_issues,
    )


def _lint(final_path: Path) -> int:
    payload = load_json(final_path)
    markdown = render_stage02_markdown(payload)
    blockers, advisories = _final_lint_findings(payload, markdown)
    warnings = check_declared_count(payload)
    status = "failed" if blockers else "passed_with_advisories" if advisories else "passed"
    _print_report({
        "kind": "lint",
        "path": str(final_path.resolve()),
        "status": status,
        "issues": blockers,
        "advisories": advisories,
        "warnings": warnings,
    })
    return 0 if not blockers else 1


def _outline(final_path: Path) -> int:
    payload = load_json(final_path)
    _print_report({"kind": "outline", "path": str(final_path.resolve()), "slides": outline_final_script(payload)})
    return 0


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
    payload = load_json(input_path)
    issues = validate_final_script(payload)
    if issues:
        _print_report({"status": "failed", "issues": issues}, stderr=True)
        return 1
    markdown = render_stage02_markdown(payload)
    lint_blockers, _ = _final_lint_findings(payload, markdown)
    if lint_blockers:
        _print_report({"kind": "final-delivery-lint", "status": "failed", "issues": lint_blockers}, stderr=True)
        return 1
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(output_path, markdown)
    print(str(output_path.resolve()))
    return 0


def _check_sync(final_path: Path, markdown_path: Path) -> int:
    payload = load_json(final_path)
    issues = validate_final_script(payload)
    if issues:
        _print_report({"kind": "delivery-sync", "final": str(final_path.resolve()), "markdown": str(markdown_path.resolve()), "status": "failed", "issues": issues})
        return 1
    expected = render_stage02_markdown(payload)
    lint_blockers, lint_advisories = _final_lint_findings(payload, expected)
    if lint_blockers:
        _print_report({"kind": "delivery-sync", "final": str(final_path.resolve()), "markdown": str(markdown_path.resolve()), "status": "failed", "issues": lint_blockers, "advisories": lint_advisories})
        return 1
    if not markdown_path.exists():
        issues = [f"{markdown_path} does not exist; run render-stage02 to produce it"]
    else:
        actual = markdown_path.read_text(encoding="utf-8")
        if actual != expected:
            issues = [f"{markdown_path} does not match a fresh render of {final_path} — re-run render-stage02 rather than hand-editing the Markdown"]
        else:
            issues = []
    status = "failed" if issues else "passed_with_advisories" if lint_advisories else "passed"
    _print_report({"kind": "delivery-sync", "final": str(final_path.resolve()), "markdown": str(markdown_path.resolve()), "status": status, "issues": issues, "advisories": lint_advisories})
    return 0 if not issues else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cyberppt-script")
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate", help="Validate a Script Engine JSON artifact"); validate.add_argument("kind", choices=sorted(VALIDATORS)); validate.add_argument("path")
    audit_foundation = sub.add_parser("audit-foundation", help="Audit inferred relations, visibility and group-strength preservation in foundation.json"); audit_foundation.add_argument("foundation")
    audit_plan = sub.add_parser("audit-plan", help="Audit source-structure fidelity, inference support, optionality and audience visibility in deck-plan.json"); audit_plan.add_argument("plan"); audit_plan.add_argument("foundation")
    review_plan = sub.add_parser("review-plan", help="Render a human-readable, non-authoritative Markdown review of deck-plan.json"); review_plan.add_argument("plan"); review_plan.add_argument("foundation")
    audit_final = sub.add_parser("audit-final", help="Audit PLAN-to-AUTHOR semantic inheritance and high-risk source-boundary rules"); audit_final.add_argument("final"); audit_final.add_argument("plan"); audit_final.add_argument("foundation")
    trace = sub.add_parser("trace-composed", help="Triage near-source vs composed Final Script lines and block source-absent numbers or identifiers"); trace.add_argument("final"); trace.add_argument("foundation"); trace.add_argument("--n", type=int, default=3)
    build_index = sub.add_parser("build-source-index", help="Build non-authoritative .cache/source-index.json from source_extract.txt"); build_index.add_argument("source_extract"); build_index.add_argument("--output", required=True); build_index.add_argument("--source-file")
    render = sub.add_parser("render-stage02", help="Render a lint-passing, Stage 02-compatible Markdown boundary"); render.add_argument("input"); render.add_argument("--output", default="dist/final-script.md")
    check_refs = sub.add_parser("check-refs", help="Verify final-script source_refs trace to foundation and optional source index"); check_refs.add_argument("final"); check_refs.add_argument("foundation"); check_refs.add_argument("--source-index")
    lint = sub.add_parser("lint", help="Scan final-script JSON and rendered Markdown for phrasing, structure and delivery-cleanliness issues"); lint.add_argument("final")
    outline = sub.add_parser("outline", help="Print per-slide id/title/onscreen module headings"); outline.add_argument("final")
    check_sync = sub.add_parser("check-sync", help="Verify a committed final-script.md matches a fresh render of final-script.json"); check_sync.add_argument("final"); check_sync.add_argument("markdown")
    new_project = sub.add_parser("new-project", help="Scaffold a new project directory under projects/"); new_project.add_argument("slug"); new_project.add_argument("--base-dir", default="projects")
    status = sub.add_parser("status", help="Report a project's progress and semantic audit state"); status.add_argument("project_dir")
    return parser


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

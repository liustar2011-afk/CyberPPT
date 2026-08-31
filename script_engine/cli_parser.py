"""Argument parser schema for the standalone Script Engine CLI."""
from __future__ import annotations

import argparse
from collections.abc import Iterable


def build_parser(validation_kinds: Iterable[str]) -> argparse.ArgumentParser:
    """Build the stable ``cyberppt-script`` command and argument surface."""

    parser = argparse.ArgumentParser(prog="cyberppt-script")
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="Validate a Script Engine JSON artifact")
    validate.add_argument("kind", choices=sorted(validation_kinds))
    validate.add_argument("path")

    audit_foundation = sub.add_parser(
        "audit-foundation",
        help="Audit inferred relations, visibility and group-strength preservation in foundation.json",
    )
    audit_foundation.add_argument("foundation")

    audit_plan = sub.add_parser(
        "audit-plan",
        help="Audit source-structure fidelity, inference support, optionality and audience visibility in deck-plan.json",
    )
    audit_plan.add_argument("plan")
    audit_plan.add_argument("foundation")

    review_plan = sub.add_parser(
        "review-plan",
        help="Render a human-readable, non-authoritative Markdown review of deck-plan.json",
    )
    review_plan.add_argument("plan")
    review_plan.add_argument("foundation")

    audit_final = sub.add_parser(
        "audit-final",
        help="Audit PLAN-to-AUTHOR semantic inheritance and high-risk source-boundary rules",
    )
    audit_final.add_argument("final")
    audit_final.add_argument("plan")
    audit_final.add_argument("foundation")

    trace = sub.add_parser(
        "trace-composed",
        help="Triage near-source vs composed Final Script lines and block source-absent numbers or identifiers",
    )
    trace.add_argument("final")
    trace.add_argument("foundation")
    trace.add_argument("--n", type=int, default=3)

    build_index = sub.add_parser(
        "build-source-index",
        help="Build non-authoritative .cache/source-index.json from source_extract.txt",
    )
    build_index.add_argument("source_extract")
    build_index.add_argument("--output", required=True)
    build_index.add_argument("--source-file")

    render = sub.add_parser(
        "render-stage02",
        help="Render a lint-passing, Stage 02-compatible Markdown boundary",
    )
    render.add_argument("input")
    render.add_argument("--output", default="dist/final-script.md")

    check_refs = sub.add_parser(
        "check-refs",
        help="Verify final-script source_refs trace to foundation and optional source index",
    )
    check_refs.add_argument("final")
    check_refs.add_argument("foundation")
    check_refs.add_argument("--source-index")

    lint = sub.add_parser(
        "lint",
        help="Scan final-script JSON and rendered Markdown for phrasing, structure and delivery-cleanliness issues",
    )
    lint.add_argument("final")

    outline = sub.add_parser("outline", help="Print per-slide id/title/onscreen module headings")
    outline.add_argument("final")

    check_sync = sub.add_parser(
        "check-sync",
        help="Verify a committed final-script.md matches a fresh render of final-script.json",
    )
    check_sync.add_argument("final")
    check_sync.add_argument("markdown")

    new_project = sub.add_parser(
        "new-project",
        help="Scaffold a new project directory under projects/",
    )
    new_project.add_argument("slug")
    new_project.add_argument("--base-dir", default="projects")

    status = sub.add_parser("status", help="Report a project's progress and semantic audit state")
    status.add_argument("project_dir")
    return parser


__all__ = ["build_parser"]

"""Focused Final Script delivery operations used by CLI adapters."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .contracts import (
    check_declared_count,
    load_json,
    outline_final_script,
    validate_final_script,
)
from .render import render_stage02_markdown
from .text_io import write_text_lf


FinalLintFindings = Callable[[dict, str], tuple[list[str], list[str]]]


def lint_report(
    final_path: Path,
    *,
    final_lint_findings: FinalLintFindings,
) -> tuple[dict, int]:
    payload = load_json(final_path)
    markdown = render_stage02_markdown(payload)
    blockers, advisories = final_lint_findings(payload, markdown)
    warnings = check_declared_count(payload)
    status = "failed" if blockers else "passed_with_advisories" if advisories else "passed"
    return (
        {
            "kind": "lint",
            "path": str(final_path.resolve()),
            "status": status,
            "issues": blockers,
            "advisories": advisories,
            "warnings": warnings,
        },
        0 if not blockers else 1,
    )


def outline_report(final_path: Path) -> tuple[dict, int]:
    payload = load_json(final_path)
    return (
        {
            "kind": "outline",
            "path": str(final_path.resolve()),
            "slides": outline_final_script(payload),
        },
        0,
    )


def render_stage02_delivery(
    input_path: Path,
    output_path: Path,
    *,
    final_lint_findings: FinalLintFindings,
) -> tuple[str | None, dict | None, int]:
    """Validate, lint and write the Stage 02 Markdown boundary.

    Returns ``(output_path, error_report, exit_code)`` so presentation policy stays
    in the CLI while delivery behavior stays here.
    """

    payload = load_json(input_path)
    issues = validate_final_script(payload)
    if issues:
        return None, {"status": "failed", "issues": issues}, 1

    markdown = render_stage02_markdown(payload)
    lint_blockers, _ = final_lint_findings(payload, markdown)
    if lint_blockers:
        return (
            None,
            {
                "kind": "final-delivery-lint",
                "status": "failed",
                "issues": lint_blockers,
            },
            1,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(output_path, markdown)
    return str(output_path.resolve()), None, 0


def delivery_sync_report(
    final_path: Path,
    markdown_path: Path,
    *,
    final_lint_findings: FinalLintFindings,
) -> tuple[dict, int]:
    payload = load_json(final_path)
    issues = validate_final_script(payload)
    if issues:
        return (
            {
                "kind": "delivery-sync",
                "final": str(final_path.resolve()),
                "markdown": str(markdown_path.resolve()),
                "status": "failed",
                "issues": issues,
            },
            1,
        )

    expected = render_stage02_markdown(payload)
    lint_blockers, lint_advisories = final_lint_findings(payload, expected)
    if lint_blockers:
        return (
            {
                "kind": "delivery-sync",
                "final": str(final_path.resolve()),
                "markdown": str(markdown_path.resolve()),
                "status": "failed",
                "issues": lint_blockers,
                "advisories": lint_advisories,
            },
            1,
        )

    if not markdown_path.exists():
        issues = [f"{markdown_path} does not exist; run render-stage02 to produce it"]
    else:
        actual = markdown_path.read_text(encoding="utf-8")
        if actual != expected:
            issues = [
                f"{markdown_path} does not match a fresh render of {final_path} — "
                "re-run render-stage02 rather than hand-editing the Markdown"
            ]
        else:
            issues = []

    status = "failed" if issues else "passed_with_advisories" if lint_advisories else "passed"
    return (
        {
            "kind": "delivery-sync",
            "final": str(final_path.resolve()),
            "markdown": str(markdown_path.resolve()),
            "status": status,
            "issues": issues,
            "advisories": lint_advisories,
        },
        0 if not issues else 1,
    )


__all__ = [
    "delivery_sync_report",
    "lint_report",
    "outline_report",
    "render_stage02_delivery",
]

"""Stable, machine-readable facts for the CyberPPT production workflow.

This module deliberately contains only repository-level routing facts that must stay
consistent across AGENTS.md, docs/CYBERPPT_WORKFLOW.md and stage Skills.  It does not
create another project artifact or runtime state file.
"""
from __future__ import annotations

STAGE01_ROUTE: tuple[str, ...] = (
    "cyberppt-source-foundation",
    "business-semantic-understanding",
    "project-foundation",
    "cyberppt-script-workflow",
)

SCRIPT_PHASES: tuple[str, ...] = (
    "UNDERSTAND",
    "PLAN",
    "AUTHOR",
    "CRITIQUE",
    "REWRITE",
    "DELIVER",
)

AUTHORITATIVE_STAGE01_CONTENT_ARTIFACTS: tuple[str, ...] = (
    "foundation.json",
    "deck-plan.json",
    "dist/final-script.md",
)

STAGE02_ENTRY = "final-script-pages"


def workflow_contract() -> dict[str, object]:
    """Return a serialization-friendly snapshot for diagnostics and tests."""

    return {
        "stage01_route": list(STAGE01_ROUTE),
        "script_phases": list(SCRIPT_PHASES),
        "authoritative_stage01_content_artifacts": list(
            AUTHORITATIVE_STAGE01_CONTENT_ARTIFACTS
        ),
        "stage02_entry": STAGE02_ENTRY,
    }

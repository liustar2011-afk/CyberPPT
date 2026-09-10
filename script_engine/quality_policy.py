"""Severity policy for deterministic Script Engine quality findings.

This layer separates structural/source-safety failures from expression-quality
heuristics. Unknown findings remain blocking by default so introducing the
policy cannot silently weaken an existing gate.

Phase 3 rule governance has two advisory sources:

1. governed phrasing rules whose registry entry declares ``severity=warning``;
2. known lexical/similarity/length semantic checks whose code cannot prove a
   source-fidelity violation without structured Foundation evidence.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .contracts import lint_final_script, load_json, validate_final_script
from .lint_contracts import load_banned_phrasing


BLOCKER = "blocker"
ADVISORY = "advisory"

# Text-shape and semantic-word checks are editorial review signals. They remain
# visible to AUTHOR/Critic but no longer act as semantic truth gates.
_SEMANTIC_HEURISTIC_CODES = frozenset(
    {
        "AUTHOR_MISSION_GENERIC",
        "AUTHOR_VISUAL_THESIS_NONRELATIONAL",
        "AUTHOR_VISUAL_TOPOLOGY_CONFLICT",
        "AUTHOR_VISUAL_THESIS_RESTATEMENT",
        "AUTHOR_RELATION_HIDDEN_INTERMEDIATE",
        "AUTHOR_RELATION_ABSTRACT_TRANSFORMATION",
        "AUTHOR_SPEAKER_NOTES_RESTATEMENT",
        "FULL_COPY_STRUCTURE_FLAT",
        "FULL_COPY_TOPIC_SOURCE_STRENGTH_ABSTRACTED",
        "FULL_COPY_TOPIC_INCOMPLETE",
        "FULL_COPY_PARALLEL_SUBCONCLUSION_ABSTRACT",
        "FULL_COPY_PARALLEL_SUBCONCLUSION_INCOMPLETE",
        "ONSCREEN_HEADING_OBJECT_OMITTED",
        "ONSCREEN_HEADING_ABSTRACT_TRANSFORMATION",
        "ONSCREEN_HEADING_INCOMPLETE",
        "ONSCREEN_DANGLING_MODIFIER",
        "ONSCREEN_DETAIL_GENERIC",
        "ONSCREEN_FULL_COPY_MISALIGNED",
        "ONSCREEN_CORE_MISALIGNED",
    }
)


def _configured_warning_rule_ids() -> frozenset[str]:
    return frozenset(
        str(rule.get("id") or "").strip()
        for rule in load_banned_phrasing()
        if rule.get("severity") == "warning" and str(rule.get("id") or "").strip()
    )


ADVISORY_CODES = _SEMANTIC_HEURISTIC_CODES | _configured_warning_rule_ids()

_CODE_RE = re.compile(r"^(?P<code>[A-Z][A-Z0-9_]+):")
_BRACKET_CODE_RE = re.compile(r"\[(?P<code>[A-Za-z0-9_.-]+)\]")


def issue_code(issue: str) -> str:
    match = _CODE_RE.search(issue)
    if match:
        return match.group("code")
    bracket = _BRACKET_CODE_RE.search(issue)
    return bracket.group("code") if bracket else "UNKNOWN"


def classify_issue(issue: str) -> dict[str, str]:
    code = issue_code(issue)
    severity = ADVISORY if code in ADVISORY_CODES else BLOCKER
    return {"code": code, "severity": severity, "message": issue}


def partition_issues(issues: Iterable[str]) -> tuple[list[str], list[str]]:
    """Split deterministic findings into blocking and advisory messages.

    Unknown/unstructured findings remain blockers because ``classify_issue`` is
    fail-closed. This function is intentionally generic so every CLI boundary
    can consume one severity policy after collecting its existing checks.
    """

    blockers: list[str] = []
    advisories: list[str] = []
    for issue in issues:
        finding = classify_issue(str(issue))
        target = advisories if finding["severity"] == ADVISORY else blockers
        target.append(finding["message"])
    return blockers, advisories


def build_quality_report(payload: dict[str, Any]) -> dict[str, Any]:
    schema_findings = [
        {"code": "SCHEMA_INVALID", "severity": BLOCKER, "message": issue}
        for issue in validate_final_script(payload)
    ]
    lint_findings = [classify_issue(issue) for issue in lint_final_script(payload)]
    findings = [*schema_findings, *lint_findings]
    blockers = [item for item in findings if item["severity"] == BLOCKER]
    advisories = [item for item in findings if item["severity"] == ADVISORY]
    return {
        "schema": "cyberppt.script_quality_report.v1",
        "status": "blocked" if blockers else "passed_with_advisories" if advisories else "passed",
        "blockers": blockers,
        "advisories": advisories,
        "policy": {
            "unknown_findings": BLOCKER,
            "advisory_codes": sorted(ADVISORY_CODES),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify deterministic final-script findings by severity.")
    parser.add_argument("final_script", type=Path)
    args = parser.parse_args(argv)
    report = build_quality_report(load_json(args.final_script.expanduser().resolve()))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if report["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

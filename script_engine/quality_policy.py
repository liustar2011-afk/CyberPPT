"""Severity policy for deterministic Script Engine quality findings.

This layer separates structural/source-safety failures from expression-quality
heuristics. Unknown findings remain blocking by default so introducing the
policy cannot silently weaken an existing gate.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .contracts import lint_final_script, load_json, validate_final_script


BLOCKER = "blocker"
ADVISORY = "advisory"

# These checks are useful editorial signals but are not reliable enough to be
# semantic truth gates. They depend on wording/grammar patterns and should be
# reviewed by AUTHOR/Critic rather than forcing content to satisfy regexes.
ADVISORY_CODES = frozenset(
    {
        "AUTHOR_MISSION_GENERIC",
        "AUTHOR_VISUAL_THESIS_NONRELATIONAL",
        "AUTHOR_VISUAL_TOPOLOGY_CONFLICT",
    }
)

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

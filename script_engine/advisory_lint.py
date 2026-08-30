"""Non-blocking final-script phrasing heuristics for the AUTHOR/Critic loop."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from .contracts import iter_final_script_text_fields, load_json


ROOT = Path(__file__).resolve().parents[1]
ADVISORY_RULES = ROOT / "contracts" / "advisory-phrasing.json"


def load_advisory_rules(path: Path = ADVISORY_RULES) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"advisory rule root must be an object: {path}")
    rules = payload.get("rules")
    if not isinstance(rules, list):
        raise ValueError(f"advisory rules must be a list: {path}")
    return [item for item in rules if isinstance(item, dict)]


def advisory_findings(
    final_script: dict[str, Any],
    *,
    rules_path: Path = ADVISORY_RULES,
) -> list[dict[str, Any]]:
    """Return warning-only findings; never determine delivery readiness."""

    compiled: list[tuple[dict[str, Any], re.Pattern[str], set[str], set[str] | None]] = []
    for rule in load_advisory_rules(rules_path):
        rule_id = str(rule.get("id") or "").strip()
        pattern = str(rule.get("pattern") or "")
        if not rule_id or not pattern:
            continue
        compiled.append(
            (
                rule,
                re.compile(pattern),
                set(rule.get("exclude_fields") or []),
                set(rule["include_fields"]) if rule.get("include_fields") else None,
            )
        )

    findings: list[dict[str, Any]] = []
    for field_path, field_key, text in iter_final_script_text_fields(final_script):
        for rule, regex, exclude_fields, include_fields in compiled:
            if field_key in exclude_fields:
                continue
            if include_fields is not None and field_key not in include_fields:
                continue
            match = regex.search(text)
            if match is None:
                continue
            findings.append(
                {
                    "severity": "warning",
                    "rule_id": str(rule["id"]),
                    "field": field_path,
                    "field_role": field_key,
                    "matched": match.group(0),
                    "description": str(rule.get("description") or ""),
                }
            )
    return findings


def build_advisory_report(final_path: Path) -> dict[str, Any]:
    payload = load_json(final_path)
    findings = advisory_findings(payload)
    return {
        "schema": "cyberppt.script_advisory_lint.v1",
        "path": str(final_path.resolve()),
        "status": "warnings" if findings else "passed",
        "blocking": False,
        "warnings": findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run non-blocking CyberPPT AUTHOR/Critic phrasing heuristics."
    )
    parser.add_argument("final_script", type=Path)
    args = parser.parse_args(argv)
    report = build_advisory_report(args.final_script)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    # Advisory findings intentionally never block the pipeline. Parse/schema
    # errors still raise normally because an unreadable input is not a warning.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

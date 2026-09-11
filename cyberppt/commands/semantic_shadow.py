"""Observational semantic-shadow command for legacy Stage 01 projects.

The command compares the active legacy Script Quality gate with the structured
semantic contract without changing delivery authority. Exit status is derived
only from the legacy gate; semantic-only blockers and review findings remain
observational during Phase 4.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cyberppt.script_quality.parsing import parse_script_path
from cyberppt.script_quality.semantic_shadow import build_semantic_shadow_report


def _load_json_object(path: Path, *, label: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def _load_source_units(path: Path | None) -> tuple[dict[str, object], ...]:
    """Load optional source units from JSON, wrapped JSON, or JSONL."""

    if path is None:
        return ()

    text = path.read_text(encoding="utf-8-sig")
    try:
        payload: object = json.loads(text)
    except json.JSONDecodeError:
        rows: list[dict[str, object]] = []
        for line_number, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"source units JSONL has invalid JSON at line {line_number}: {path}"
                ) from exc
            if not isinstance(item, dict):
                raise ValueError(
                    f"source units JSONL line {line_number} must be an object: {path}"
                )
            rows.append(item)
        return tuple(rows)

    if isinstance(payload, dict):
        payload = payload.get("source_units")
    if not isinstance(payload, list) or not all(isinstance(item, dict) for item in payload):
        raise ValueError(
            "source units must be a JSON array of objects, a JSON object with "
            f"source_units, or JSONL objects: {path}"
        )
    return tuple(payload)


def run_semantic_shadow(
    *,
    script_path: Path,
    outline_path: Path,
    source_truth_path: Path,
    source_units_path: Path | None = None,
) -> dict[str, Any]:
    """Build one observational legacy-vs-semantic comparison report."""

    script = parse_script_path(script_path)
    outline = _load_json_object(outline_path, label="outline")
    source_truth = _load_json_object(source_truth_path, label="source truth")
    source_units = _load_source_units(source_units_path)
    report = build_semantic_shadow_report(
        script,
        outline,
        source_truth,
        source_units=source_units,
    )
    if report.get("effective_gate") != "legacy":
        raise ValueError(
            "semantic shadow report changed effective_gate; Phase 4 requires legacy authority"
        )
    return report


def semantic_shadow_exit_code(report: dict[str, Any]) -> int:
    """Return the active legacy gate status, ignoring semantic-only findings."""

    if report.get("effective_gate") != "legacy":
        raise ValueError(
            "semantic shadow exit status is defined only for effective_gate='legacy'"
        )
    legacy = report.get("legacy")
    if not isinstance(legacy, dict):
        raise ValueError("semantic shadow report is missing the legacy result")
    blockers = legacy.get("blockers")
    if not isinstance(blockers, list):
        raise ValueError("semantic shadow report legacy.blockers must be a list")
    return 1 if blockers else 0


def _codes(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "none"
    return ", ".join(str(item) for item in value)


def _parity_label(value: object) -> str:
    if value is True:
        return "match"
    if value is False:
        return "diverged"
    return "unknown"


def render_semantic_shadow_summary(report: dict[str, Any]) -> str:
    """Render a compact operator-facing comparison while retaining JSON output."""

    legacy = report.get("legacy") if isinstance(report.get("legacy"), dict) else {}
    semantic = (
        report.get("semantic_shadow")
        if isinstance(report.get("semantic_shadow"), dict)
        else {}
    )
    diff = report.get("diff") if isinstance(report.get("diff"), dict) else {}
    return "\n".join(
        [
            "semantic shadow: {} (effective gate: {})".format(
                report.get("status", "unknown"),
                report.get("effective_gate", "unknown"),
            ),
            "legacy: {} blocker(s), {} warning(s)".format(
                len(legacy.get("blockers") or []),
                len(legacy.get("warnings") or []),
            ),
            "semantic shadow: {} blocker(s), {} review finding(s)".format(
                len(semantic.get("blockers") or []),
                len(semantic.get("reviews") or []),
            ),
            "blocking outcome: {} (legacy={}, semantic={})".format(
                _parity_label(diff.get("blocking_outcome_matches")),
                legacy.get("status", "unknown"),
                semantic.get("status", "unknown"),
            ),
            f"blockers only in legacy: {_codes(diff.get('blocker_codes_only_legacy'))}",
            f"blockers only in semantic: {_codes(diff.get('blocker_codes_only_semantic'))}",
            f"common blockers: {_codes(diff.get('common_blocker_codes'))}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Compare the active legacy Script Quality gate with the structured semantic "
            "contract. This Phase 4 command is observational: only legacy blockers affect "
            "the exit code."
        )
    )
    parser.add_argument("--script", required=True, help="Final Script Markdown path.")
    parser.add_argument("--outline", required=True, help="Legacy Outline JSON path.")
    parser.add_argument("--source-truth", required=True, help="Source Truth JSON path.")
    parser.add_argument(
        "--source-units",
        help="Optional source units JSON/JSONL path used by the legacy gate.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete machine-readable shadow report instead of the summary.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to persist the complete JSON report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run_semantic_shadow(
            script_path=Path(args.script),
            outline_path=Path(args.outline),
            source_truth_path=Path(args.source_truth),
            source_units_path=Path(args.source_units) if args.source_units else None,
        )
        code = semantic_shadow_exit_code(report)
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
                newline="\n",
            )
    except (FileNotFoundError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_semantic_shadow_summary(report))
    return code


__all__ = [
    "build_parser",
    "main",
    "render_semantic_shadow_summary",
    "run_semantic_shadow",
    "semantic_shadow_exit_code",
]

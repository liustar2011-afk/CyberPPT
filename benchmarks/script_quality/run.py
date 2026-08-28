"""Run the committed Script Quality benchmark without mutating the repository."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from script_engine.analysis_audit import audit_deck_plan


FIXTURE_PATH = Path(__file__).with_name("fixtures.json")


def _code(value: str) -> str:
    return value.split(":", 1)[0].strip()


def run_benchmark(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    fixtures = json.loads(path.read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []
    true_positive = false_positive = false_negative = 0
    for fixture in fixtures:
        expected = fixture.get("expected") or {}
        expected_issues = set(expected.get("issues") or [])
        expected_warnings = set(expected.get("warnings") or [])
        issues, warnings = audit_deck_plan(fixture["plan"], fixture["foundation"])
        actual_issues = {_code(value) for value in issues}
        actual_warnings = {_code(value) for value in warnings}
        expected_codes = expected_issues | expected_warnings
        actual_codes = actual_issues | actual_warnings
        true_positive += len(expected_codes & actual_codes)
        false_positive += len(actual_codes - expected_codes)
        false_negative += len(expected_codes - actual_codes)
        results.append({
            "id": fixture["id"],
            "status": "passed" if actual_codes == expected_codes else "failed",
            "expected": {"issues": sorted(expected_issues), "warnings": sorted(expected_warnings)},
            "actual": {"issues": sorted(actual_issues), "warnings": sorted(actual_warnings)},
        })
    precision = true_positive / (true_positive + false_positive) if true_positive + false_positive else 1.0
    recall = true_positive / (true_positive + false_negative) if true_positive + false_negative else 1.0
    return {
        "fixture_count": len(fixtures),
        "passed": sum(item["status"] == "passed" for item in results),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixtures", type=Path, default=FIXTURE_PATH)
    args = parser.parse_args()
    report = run_benchmark(args.fixtures)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] == report["fixture_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

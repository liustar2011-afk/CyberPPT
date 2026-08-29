from __future__ import annotations

from pathlib import Path

from benchmarks.script_quality.run import run_benchmark


ROOT = Path(__file__).resolve().parents[2]


def test_committed_script_quality_benchmark_is_repeatable_and_clean() -> None:
    report = run_benchmark(ROOT / "benchmarks" / "script_quality" / "fixtures.json")

    assert report["fixture_count"] == 12
    assert report["passed"] == report["fixture_count"]
    assert report["false_positive"] == 0
    assert report["false_negative"] == 0
    assert report["precision"] >= 0.85

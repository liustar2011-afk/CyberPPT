from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_large_semantic_modules_stay_within_reviewed_growth_budgets() -> None:
    config = json.loads(
        (ROOT / "config" / "architecture_module_budgets.json").read_text(encoding="utf-8")
    )
    failures: list[str] = []
    for relative, limit in config["files"].items():
        path = ROOT / relative
        size = path.stat().st_size
        if size > int(limit):
            failures.append(f"{relative}: {size} > {limit}")

    assert failures == [], "large-module growth requires decomposition review: " + "; ".join(failures)


def test_decomposition_plan_keeps_authority_and_behavior_constraints() -> None:
    text = (ROOT / "docs" / "STAGE01_DECOMPOSITION_PLAN.md").read_text(encoding="utf-8")

    assert "行为保持型" in text
    assert "不新增平行 authority" in text
    assert "advisory lint" in text
    assert "Stage 01 Authority Map" in text

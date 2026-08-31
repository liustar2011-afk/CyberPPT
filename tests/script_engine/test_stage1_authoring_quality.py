from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.contracts import lint_final_script


ROOT = Path(__file__).resolve().parents[2]


def _example() -> dict:
    return json.loads(
        (ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8")
    )


def test_lint_final_script_flags_unlabeled_bare_numbers_in_onscreen_details() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"][0]["items"] = ["80%", "30家", "3项"]

    issues = lint_final_script(payload)

    assert sum("ONSCREEN_NUMBER_WITHOUT_OBJECT" in issue for issue in issues) == 3


def test_lint_final_script_allows_labeled_numbers_dates_and_numbers_in_prose() -> None:
    payload = copy.deepcopy(_example())
    payload["slides"][0]["onscreen"][0]["items"] = [
        "覆盖率：80%",
        "2026年",
        "首批覆盖30家重点单位",
        "形成3项可验收成果",
    ]

    issues = lint_final_script(payload)

    assert not any("ONSCREEN_NUMBER_WITHOUT_OBJECT" in issue for issue in issues)

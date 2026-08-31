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


def test_lint_final_script_flags_roadmap_stages_without_trigger_or_new_state() -> None:
    payload = copy.deepcopy(_example())
    slide = payload["slides"][0]
    slide["argument"] = {
        "pattern": "roadmap",
        "chain": ["数据准备", "联合分析", "常态运行"],
    }
    slide["onscreen"] = [
        {"heading": "阶段一推进数据治理", "items": ["统一目录和口径"]},
        {"heading": "阶段二推进联合分析", "items": ["开展月季年联合分析"]},
    ]

    issues = lint_final_script(payload)

    assert sum("ROADMAP_TRIGGER_MISSING" in issue for issue in issues) == 2
    assert sum("ROADMAP_NEW_STATE_MISSING" in issue for issue in issues) == 2


def test_lint_final_script_accepts_roadmap_trigger_and_new_state_per_stage() -> None:
    payload = copy.deepcopy(_example())
    slide = payload["slides"][0]
    slide["argument"] = {
        "pattern": "roadmap",
        "chain": ["数据规则贯通", "跨周期试运行"],
    }
    slide["onscreen"] = [
        {
            "heading": "数据规则贯通后形成可复用共同输入",
            "items": ["进入条件：完成核心目录和版本规则统一"],
        },
        {
            "heading": "2027年形成可比较的跨周期结论",
            "items": ["月度滚动、季度校核和年度展望在同一框架联合运行"],
        },
    ]

    issues = lint_final_script(payload)

    assert not any(issue.startswith("ROADMAP_") for issue in issues)


def test_lint_final_script_does_not_force_roadmap_floor_on_generic_progression() -> None:
    payload = copy.deepcopy(_example())
    slide = payload["slides"][0]
    slide["argument"] = {"pattern": "progression", "chain": ["输入", "处理", "输出"]}
    slide["onscreen"] = [
        {"heading": "数据治理建立统一资源口径", "items": ["统一目录和口径"]},
        {"heading": "可信流通机制保障受控使用", "items": ["授权控制和审计留痕"]},
    ]

    issues = lint_final_script(payload)

    assert not any(issue.startswith("ROADMAP_") for issue in issues)

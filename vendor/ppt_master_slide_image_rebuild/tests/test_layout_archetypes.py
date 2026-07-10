from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from layout_family_lib import build_detected_layout_family, classify_layout_archetype
from layout_reference_to_svg_plan import build_markdown, build_plan


def test_three_stage_goal_timeline_archetype_detected() -> None:
    result = classify_layout_archetype(
        layout_type="three_stage_goal_timeline",
        family="dense_cards_with_icons",
        signals={"estimated_column_count": 3},
        zones=[
            {"id": "short_goal", "role": "card"},
            {"id": "mid_goal", "role": "card"},
            {"id": "long_goal", "role": "card"},
        ],
        main_chain={"connectors": [{"from": "short_goal", "to": "mid_goal"}, {"from": "mid_goal", "to": "long_goal"}]},
    )

    assert result["name"] == "three_stage_goal_timeline"
    assert result["confidence"] >= 0.8
    assert "stage_cards" in result["required_objects"]


def test_weak_archetype_signals_stay_custom() -> None:
    result = classify_layout_archetype(
        layout_type="to_be_completed_by_agent",
        family="custom",
        zones=[{"id": "decorative_bg", "role": "decorative"}],
    )

    assert result["name"] == "custom"
    assert result["confidence"] < 0.65


def test_build_detected_layout_family_includes_archetype() -> None:
    block = build_detected_layout_family({
        "layout_type": "three_stage_goal_timeline",
        "zones": [
            {"id": "short_goal", "role": "card"},
            {"id": "mid_goal", "role": "card"},
            {"id": "long_goal", "role": "card"},
        ],
        "main_chain": {
            "connectors": [
                {"from": "short_goal", "to": "mid_goal"},
                {"from": "mid_goal", "to": "long_goal"},
            ]
        },
    })

    assert block["archetype"]["name"] == "three_stage_goal_timeline"


def test_svg_build_plan_carries_layout_archetype_to_markdown() -> None:
    layout = {
        "canvas": {"width_px": 1600, "height_px": 900},
        "layout_type": "three_stage_goal_timeline",
        "detected_layout_family": {
            "archetype": {
                "name": "three_stage_goal_timeline",
                "label": "三阶段目标 / 路线图",
                "confidence": 0.84,
                "required_objects": ["title", "stage_cards", "chain_connectors"],
                "signals": ["three stage/card signals"],
            }
        },
        "zones": [{"id": "short_goal", "role": "card", "x_ratio": 0.1, "y_ratio": 0.2, "w_ratio": 0.2, "h_ratio": 0.3}],
    }
    mapping = {"renderable_content": {"modules": [{"zone_id": "short_goal", "title": "短期目标"}]}}

    plan = build_plan(layout, mapping)
    markdown = build_markdown(plan)

    assert plan["layout_archetype"]["name"] == "three_stage_goal_timeline"
    assert "## Layout Archetype" in markdown
    assert "three_stage_goal_timeline" in markdown

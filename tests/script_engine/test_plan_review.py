from __future__ import annotations

import copy
import json
from pathlib import Path

from script_engine.analysis_audit import audit_deck_plan
from script_engine.plan_review import render_plan_review


ROOT = Path(__file__).resolve().parents[2]


def _load(name: str) -> dict:
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


def test_plan_review_renders_only_plan_boundary_fields() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")
    issues, warnings = audit_deck_plan(plan, foundation)

    text = render_plan_review(plan, foundation, issues=issues, warnings=warnings)

    assert "# 脚本规划待确认" in text
    assert "页面问题" in text
    assert "页面使命" in text
    assert "来源范围" in text
    assert "来源锚点" in text
    assert "论证链" not in text
    assert "上屏模块" not in text
    assert "证据角色" not in text
    assert "视觉关系" not in text
    assert "讲述备注" not in text


def test_plan_review_surfaces_analytical_mode_without_author_prose() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")
    plan["authoring_mode"] = "analytical"
    plan["pages"][0]["question"] = "资源治理与可信使用如何共同支撑服务输出？"
    plan["pages"][0]["logic"] = "分析两项基础与服务输出之间的支撑关系"
    issues, warnings = audit_deck_plan(plan, foundation)

    text = render_plan_review(plan, foundation, issues=issues, warnings=warnings)

    assert "写作模式：分析性深化" in text
    assert "资源治理与可信使用如何共同支撑服务输出？" in text
    assert "分析两项基础与服务输出之间的支撑关系" in text
    assert "论证链" not in text
    assert "上屏模块" not in text


def test_plan_review_marks_cross_chapter_user_authorization() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")
    foundation["source_structure"].append(
        {
            "id": "CH02",
            "title": "第二章 应用验证",
            "order": 3,
            "level": "chapter",
            "source_refs": ["ST004"],
        }
    )
    plan["source_structure_mode"] = "user_authorized_restructure"
    plan["chapters"][0]["source_chapter_ids"] = ["CH01", "CH02"]
    plan["chapters"][0]["structural_operation"] = "user_authorized_cross_chapter"

    issues, warnings = audit_deck_plan(plan, foundation)
    text = render_plan_review(plan, foundation, issues=issues, warnings=warnings)

    assert "按用户授权重组" in text
    assert "用户授权跨章重组" in text


def test_plan_review_exposes_blocking_audit_findings() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")
    plan["pages"][0]["source_refs"] = ["UNKNOWN"]
    issues, warnings = audit_deck_plan(plan, foundation)

    text = render_plan_review(plan, foundation, issues=issues, warnings=warnings)

    assert issues
    assert "## 审计结论" in text
    assert "LEAN_SOURCE_REF_UNKNOWN" in text


def test_plan_review_does_not_mutate_inputs() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")
    before = copy.deepcopy(plan)
    before_foundation = copy.deepcopy(foundation)

    render_plan_review(plan, foundation)

    assert plan == before
    assert foundation == before_foundation


def test_plan_review_renders_compact_source_anchor_for_each_known_page_ref() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")

    text = render_plan_review(plan, foundation)

    assert "F1 数据资源首先需要完成可识别和可管理的治理。" in text
    assert "F2 可信使用机制控制授权、安全和审计。" in text
    assert "F3 治理和可信使用共同支撑服务输出。" in text
    assert "F4 具体技术能力清单留到后续页面说明。" in text
    assert "来源锚点仅用于核对，不新增页面结论" in text


def test_plan_review_truncates_long_source_anchor_without_changing_foundation() -> None:
    foundation = _load("foundation.example.json")
    plan = _load("deck-plan.example.json")
    long_text = "甲" * 100
    foundation["facts"][0]["statement"] = long_text
    before = copy.deepcopy(foundation)

    text = render_plan_review(plan, foundation)

    assert f"F1 {'甲' * 71}…" in text
    assert long_text not in text
    assert foundation == before

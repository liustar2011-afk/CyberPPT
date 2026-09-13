from copy import deepcopy
import json
from pathlib import Path

import pytest

from script_engine.analysis_audit import audit_deck_plan
from script_engine.cli import main
from script_engine.plan_quality import build_plan_critic_context, validate_delivery_mode_alignment
from script_engine.plan_review import render_plan_review
from script_engine.schema_contracts import validate_deck_plan


ROOT = Path(__file__).resolve().parents[2]


def example():
    return tuple(json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
                 for name in ("deck-plan.example.json", "foundation.example.json"))


@pytest.mark.parametrize("mode", ["presented", "self_read"])
def test_selected_purpose_is_valid_and_visible_in_review(mode):
    plan, foundation = example()
    plan["delivery_mode"] = mode
    assert validate_deck_plan(plan) == []
    assert audit_deck_plan(plan, foundation)[0] == []
    review = render_plan_review(plan, foundation)
    assert ("演讲辅助" if mode == "presented" else "独立阅读") in review
    assert plan["pagination_rationale"] in review


@pytest.mark.parametrize("field,value", [
    ("delivery_mode", None), ("delivery_mode", "mixed"),
    ("pagination_rationale", None), ("pagination_rationale", "  "),
])
def test_unresolved_purpose_blocks_actual_review_cli(field, value, tmp_path, capsys):
    plan, foundation = example()
    if value is None:
        plan.pop(field)
    else:
        plan[field] = value
    assert validate_deck_plan(plan)
    assert audit_deck_plan(plan, foundation)[0]
    for name, payload in (("plan", plan), ("foundation", foundation)):
        (tmp_path / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
    assert main(["review-plan", str(tmp_path / "plan.json"), str(tmp_path / "foundation.json")]) == 1
    output = capsys.readouterr().out
    assert "PLAN_DELIVERY_MODE_REQUIRED" in output or "PLAN_PAGINATION_RATIONALE_REQUIRED" in output


def test_same_page_scopes_receive_mode_specific_pagination_review_without_mutation():
    plan, _ = example()
    first = plan["pages"][0]
    first["logic"] = "包括资源治理、可信使用，包括服务输出"
    second = deepcopy(first)
    second.update(id="P02", logic="说明服务输出的适用条件")
    plan["pages"].append(second)
    snapshots = []
    for mode in ("presented", "self_read"):
        plan["delivery_mode"] = mode
        before = deepcopy(plan)
        snapshots.append(build_plan_critic_context(plan))
        assert plan == before
    presented, reading = snapshots
    assert presented["pages"] == reading["pages"]
    assert presented["pagination_guidance"] != reading["pagination_guidance"]
    assert presented["single_core_guidance"] == reading["single_core_guidance"]
    assert any(item["code"] == "PLAN_SINGLE_CORE_REVIEW" for item in presented["priorities"])
    assert not any(item["code"] == "PLAN_SELF_READ_CONTINUITY_REVIEW" for item in presented["priorities"])
    assert any(item["code"] == "PLAN_SELF_READ_CONTINUITY_REVIEW" for item in reading["priorities"])
    assert any(item["code"] == "PLAN_SINGLE_CORE_REVIEW" for item in reading["priorities"])


@pytest.mark.parametrize("mode", ["presented", "self_read"])
def test_independent_questions_surface_in_actual_plan_review(mode, tmp_path, capsys):
    plan, foundation = example()
    plan["delivery_mode"] = mode
    plan["pages"][0].update(question="资源治理如何开展？年度预算如何分配？", logic="说明相关工作")
    for name, payload in (("plan", plan), ("foundation", foundation)):
        (tmp_path / f"{name}.json").write_text(json.dumps(payload), encoding="utf-8")
    main(["review-plan", str(tmp_path / "plan.json"), str(tmp_path / "foundation.json")])
    output = capsys.readouterr().out
    assert "PLAN_SINGLE_CORE_REVIEW" in output
    assert "一页只表达一项核心内容" in output


@pytest.mark.parametrize("mode", ["presented", "self_read"])
@pytest.mark.parametrize("logic,question", [
    ("呈现数据服务从申请、审核到开通的完整流程", "数据服务如何开通？"),
    ("说明服务覆盖的企业、个人与机构三类对象", "服务覆盖哪些对象？"),
])
def test_multiple_supports_for_one_topic_do_not_force_split(mode, logic, question):
    plan, _ = example()
    plan["delivery_mode"] = mode
    plan["pages"][0].update(logic=logic, question=question)
    context = build_plan_critic_context(plan)
    assert not any(item["code"] == "PLAN_SINGLE_CORE_REVIEW" for item in context["priorities"])
    assert len(context["pages"]) == 1


@pytest.mark.parametrize("actual", [None, "self_read"])
def test_final_cannot_default_or_switch_away_from_presented_plan(actual):
    plan, _ = example()
    plan["delivery_mode"] = "presented"
    assert validate_delivery_mode_alignment({"deck": {"delivery_mode": actual}}, plan)
    assert not validate_delivery_mode_alignment({"deck": {"delivery_mode": "presented"}}, plan)


def test_historical_unversioned_plan_retains_compatibility():
    assert validate_delivery_mode_alignment({"deck": {}}, {}) == []

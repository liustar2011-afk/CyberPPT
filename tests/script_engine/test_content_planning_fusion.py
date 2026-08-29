from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from script_engine.analysis_audits.deck_plan import audit_deck_plan
from script_engine.analysis_audits.final_script import audit_final_script
from script_engine.contracts import validate_deck_plan
from script_engine.narrative_arc import cjk_aware_tokens, review_narrative_design, text_overlap
from script_engine.onscreen_quality import build_onscreen_critic_context, record_candidate_score, visible_character_count
from script_engine.plan_quality import plan_critic_priorities
from script_engine.plan_review import render_plan_review
from cyberppt.stage02_handoff import _lean_stage02_plan_projection


ROOT = Path(__file__).resolve().parents[2]


def _foundation() -> dict:
    return {
        "document_thesis": {"statement": "统一规则把国家部署转化为电力行业可验证的建设行动"},
        "document_semantics": {"argument_method": ["A1", "A2"]},
        "argument_nodes": [
            {"id": "A1", "source_refs": ["F1"]},
            {"id": "A2", "source_refs": ["F2"]},
        ],
        "facts": [
            {"id": "F1", "statement": "国家部署给出总体任务"},
            {"id": "F2", "statement": "先行先试要求开展标准验证"},
        ],
    }


def _candidate(candidate_id: str, *, shape: str, roles: list[str], evidence: list[str]) -> dict:
    return {
        "id": candidate_id,
        "name": f"候选{candidate_id}",
        "shape": shape,
        "opening_roles": roles,
        "audience_question": "标准体系为何必须进入先行先试建设主线",
        "objection": "标准研究会不会与项目建设脱节",
        "closing_ask": "确认标准验证作为建设阶段的共同验收线索",
        "argument_focus_node_ids": ["A1", "A2"],
        "evidence_refs": evidence,
    }


def _lean_plan() -> dict:
    first = _candidate("ARC-A", shape="evidence-build", roles=["problem", "evidence", "decision"], evidence=["F1", "F2"])
    second = _candidate("ARC-B", shape="recommendation-first", roles=["decision", "evidence", "roadmap"], evidence=["F1", "F2"])
    second.update(
        {
            "audience_question": "先行先试应按什么共同标准验收",
            "objection": "现有项目成果能否直接替代统一标准",
            "closing_ask": "以标准验证串联能力建设和阶段成果",
            "loss_reason": "行动结论前置会削弱国家部署到行业任务的证据递进",
        }
    )
    return {
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "delivery_mode": "presented",
        "communication_goal": "说明标准体系研究在先行先试中的不可替代职责",
        "audience": "项目决策与实施团队",
        "audience_scope": "internal",
        "source_structure_mode": "preserve",
        "source_thesis": "统一规则把国家部署转化为电力行业可验证的建设行动",
        "source_argument_method": ["A1", "A2"],
        "thesis": "标准验证是把政策约束、节点能力和阶段成果接成一条建设主线的共同尺度",
        "narrative_arc": "部署依据 → 项目任务 → 验证尺度",
        "storyline": ["国家部署给出边界", "项目任务形成载体", "标准验证形成尺度"],
        "narrative_design": {
            "mode": "competitive",
            "chosen_id": "ARC-A",
            "selection_reason": "先建立约束来源，再落到项目验收职责",
            "emotional_curve": "依据 → 张力 → 任务 → 决策",
            "peak_page_id": "P02",
            "candidates": [first, second],
        },
        "chapters": [
            {
                "id": "C1",
                "title": "建设依据与验证职责",
                "purpose": "建立标准验证的项目职责",
                "question": "标准验证为何必须进入建设主线",
                "message": "政策约束与项目任务共同要求统一验证尺度",
                "relationship_to_previous": "承接封面交流目标",
                "source_argument_node_ids": ["A1", "A2"],
            }
        ],
        "pages": [
            {
                "id": "P01",
                "chapter_id": "C1",
                "title": "建设部署形成统一约束",
                "question": "国家部署提供了哪些建设边界",
                "message": "国家部署用总体任务和统一规则限定行业建设边界",
                "logic": "依据",
                "page_role": "context",
                "beat": "建立约束来源",
                "content": ["总体任务"],
                "source_argument_node_ids": ["A1"],
                "source_refs": ["F1"],
                "receives": "交流目标",
                "next": "项目如何承接统一约束",
                "spoken_thread": "先说明统一规则的来源和约束对象",
            },
            {
                "id": "P02",
                "chapter_id": "C1",
                "title": "标准验证贯通建设与验收",
                "question": "项目如何把统一约束转成可验证成果",
                "message": "标准验证把节点能力、重点任务和阶段成果纳入同一验收尺度",
                "logic": "结论",
                "page_role": "conclusion",
                "beat": "把政策依据转化为项目决策",
                "content": ["节点能力", "阶段成果"],
                "primary_relation": {"type": "parallel", "scope": ["节点能力", "阶段成果"], "authority": "hard"},
                "source_argument_node_ids": ["A2"],
                "source_refs": ["F2"],
                "receives": "项目承接统一约束",
                "next": "形成实施安排",
                "spoken_thread": "再说明统一尺度如何进入项目建设和验收",
            },
        ],
    }


def test_cjk_tokenization_does_not_bridge_latin_islands() -> None:
    tokens = cjk_aware_tokens("接受INR骨干")
    assert "受骨" not in tokens
    assert {"接受", "骨干", "inr"}.issubset(tokens)
    assert 0 < text_overlap("让评审接受这个方法", "让评审委员会接受该方法") < 1


def test_competitive_narrative_rejects_collapsed_and_strawman_candidates() -> None:
    first = _candidate("A", shape="evidence-build", roles=["problem", "evidence"], evidence=["F1", "F2"])
    second = deepcopy(first)
    second.update({"id": "B", "name": "候选B", "evidence_refs": []})
    second["loss_reason"] = "证据投入不足"
    result = review_narrative_design({"mode": "competitive", "chosen_id": "A", "candidates": [first, second]})
    joined = "\n".join(result["issues"])
    assert "NARRATIVE_CANDIDATES_TOO_SIMILAR" in joined
    assert "NARRATIVE_STRAWMAN_CANDIDATE" in joined


def test_direct_mode_has_no_multi_candidate_tax() -> None:
    assert review_narrative_design({"mode": "direct"})["issues"] == []


def test_v2_lean_schema_and_audit_keep_argument_bindings_without_v1_contracts() -> None:
    plan = _lean_plan()
    assert validate_deck_plan(plan) == []
    issues, _ = audit_deck_plan(plan, _foundation())
    assert issues == []

    drifted = deepcopy(plan)
    drifted["source_argument_method"] = ["A2", "A1"]
    issues, _ = audit_deck_plan(drifted, _foundation())
    assert any("SOURCE_ARGUMENT_METHOD_DRIFT" in issue for issue in issues)


def test_presented_lean_plan_requires_spoken_thread() -> None:
    plan = _lean_plan()
    plan["pages"][0].pop("spoken_thread")
    issues, _ = audit_deck_plan(plan, _foundation())
    assert any("LEAN_SPOKEN_THREAD_MISSING" in issue for issue in issues)


def test_lean_plan_source_asset_requires_carrier_binding_and_peak_misreading_boundary() -> None:
    foundation = _foundation()
    foundation["argument_nodes"][1]["source_refs"] = ["SU-ASSET"]
    foundation["source_assets"] = [
        {
            "id": "ASSET-0123456789ABCDEF",
            "kind": "chart",
            "source_unit_refs": ["SU-ASSET"],
            "locator": {"slide": 2, "shape": 7},
            "argument_node_ids": ["A2"],
        }
    ]
    plan = _lean_plan()
    plan["pages"][1]["visual_evidence"] = {
        "kind": "asset",
        "ref": "ASSET-0123456789ABCDEF",
        "answers": "why",
    }

    issues, _ = audit_deck_plan(plan, foundation)
    assert any("SOURCE_ASSET_CARRYING_ELEMENT_MISSING" in issue for issue in issues)
    assert any("SOURCE_ASSET_WRONG_READING_MISSING" in issue for issue in issues)

    plan["pages"][1]["visual_evidence"]["carrying_element"] = "主图：建设与验收的贯通关系图"
    foundation["source_assets"][0]["wrong_reading"] = "图中连接线代表已完成实施"
    foundation["source_assets"][0]["meaning"] = "统一尺度连接节点能力和阶段验收"
    issues, warnings = audit_deck_plan(plan, foundation)
    assert not any("SOURCE_ASSET" in item for item in issues + warnings)
    review = render_plan_review(plan, foundation)
    assert "来源图表传播说明" in review
    assert "主图：建设与验收的贯通关系图" in review
    assert "图中连接线代表已完成实施" in review


def test_v2_final_script_preserves_approved_message_without_unit_dispositions() -> None:
    plan = _lean_plan()
    slides = []
    for page in plan["pages"]:
        slides.append(
            {
                "id": page["id"],
                "page_type": "content",
                "core_message": page["message"],
                "full_copy": "国家部署给出总体任务，先行先试要求开展标准验证。",
                "onscreen": [],
                "relationships": [],
                "speaker_notes": "建设任务需要统一验证尺度。",
            }
        )
    issues, _ = audit_final_script({"slides": slides}, plan, _foundation())
    assert not any("PLAN evidence-fit gate" in issue for issue in issues)
    assert not any("source_consumption" in issue for issue in issues)

    slides[0]["core_message"] = "漂移后的判断"
    issues, _ = audit_final_script({"slides": slides}, plan, _foundation())
    assert any("AUTHOR_PAGE_PROPOSITION_DRIFTED" in issue for issue in issues)


def test_plan_review_shows_candidates_peak_and_qualitative_priorities() -> None:
    plan = _lean_plan()
    plan["pages"][0]["message"] = "总体部署明确建设任务，统一规则提供落地支撑，行业政策构成直接依据"
    review = render_plan_review(plan, _foundation())
    assert "## 叙事选择" in review
    assert "ARC-A" in review and "ARC-B" in review
    assert "高潮页：P02" in review
    assert "PLAN_MESSAGE_COVERAGE_SUMMARY" in review
    assert plan_critic_priorities(plan)


def test_onscreen_quality_measures_candidates_without_generating_copy() -> None:
    page = _lean_plan()["pages"][1]
    candidates = [
        {"strategy": "judgment_led", "onscreen": [{"heading": "判断", "text": "标准验证贯通建设与验收", "items": []}]},
        {"strategy": "evidence_led", "onscreen": [{"heading": "证据", "items": ["节点能力", "阶段成果"]}]},
    ]
    context = build_onscreen_critic_context(page=page, full_copy="完整页面论证", candidates=candidates)
    assert context["review_dimensions"] == ["主判断可见性", "十秒理解", "文字密度", "信息重复", "关系可见性", "语义完整性"]
    assert context["candidates"][0]["visible_characters"] == visible_character_count(candidates[0]["onscreen"])
    assert "winner" not in context
    score = record_candidate_score(
        "judgment_led",
        {
            "main_judgment_visibility": 4,
            "ten_second_comprehension": 4,
            "density": 3,
            "repetition": 4,
            "relation_visibility": 4,
            "semantic_completeness": 5,
        },
        rationale="判断清楚，关键证据保留，密度仍可继续压缩",
    )
    assert score["median"] == 4


def test_stage02_projection_derives_from_final_script_and_ignores_v1_authoring_fields() -> None:
    page = _lean_plan()["pages"][1]
    page["stage02_readiness"] = {"continuous_sentence_signals": ["不应进入 lean 投影"]}
    page["source_consumption"] = {"mode": "strict", "unit_dispositions": []}
    projected = _lean_stage02_plan_projection(page)
    assert projected["title"] == page["title"]
    assert projected["message"] == page["message"]
    assert "stage02_readiness" not in projected
    assert "source_consumption" not in projected


def test_real_power_sample_reduces_visible_density_without_losing_key_boundaries() -> None:
    case = json.loads(
        (ROOT / "benchmarks/stage01_content_quality/cases/power-p03-p04.json").read_text(
            encoding="utf-8"
        )
    )
    by_id = {page["id"]: page for page in case["pages"]}
    field_inventory = case["authoring_field_inventory"]
    assert len(field_inventory["after_v2_presented"]) <= 0.60 * len(field_inventory["before_v1_p03"])
    assert visible_character_count(by_id["P03"]["before"]["onscreen"]) == 402
    assert visible_character_count(by_id["P03"]["after"]["onscreen"]) == 185
    assert visible_character_count(by_id["P04"]["before"]["onscreen"]) == 326
    assert visible_character_count(by_id["P04"]["after"]["onscreen"]) == 132

    p03_after = json.dumps(by_id["P03"]["after"], ensure_ascii=False)
    for required in ("2026", "2028", "2029", "六项", "一般、重要、核心", "安全责任"):
        assert required in p03_after
    p04_after = json.dumps(by_id["P04"]["after"], ensure_ascii=False)
    for required in ("三统一", "八类", "标准体系框架", "可交付", "可验证", "可运营", "中电联"):
        assert required in p04_after

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from script_engine.analysis_audits.deck_plan import audit_deck_plan
from script_engine.analysis_audits.final_script import audit_final_script
from script_engine.contracts import validate_deck_plan
from script_engine.narrative_arc import cjk_aware_tokens, review_narrative_design, text_overlap
from script_engine.onscreen_quality import build_onscreen_critic_context, record_candidate_score, visible_character_count
from script_engine.plan_review import render_plan_review


ROOT = Path(__file__).resolve().parents[2]


def _foundation() -> dict:
    return {
        "source_structure": [{"id": "S1", "level": "chapter", "order": 1}],
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
    return {
        "plan_contract_version": 2,
        "planning_profile": "lean",
        "communication_goal": "说明标准体系研究在先行先试中的不可替代职责",
        "audience": "项目决策与实施团队",
        "audience_scope": "internal",
        "source_structure_mode": "preserve",
        "chapters": [
            {
                "id": "C1",
                "title": "建设依据与验证职责",
                "purpose": "建立标准验证的项目职责",
                "source_chapter_ids": ["S1"],
            }
        ],
        "pages": [
            {
                "id": "P01",
                "chapter_id": "C1",
                "title": "建设部署形成统一约束",
                "question": "国家部署提供了哪些建设边界",
                "logic": "说明国家部署形成的建设边界",
                "page_role": "content",
                "source_refs": ["F1"],
            },
            {
                "id": "P02",
                "chapter_id": "C1",
                "title": "标准验证贯通建设与验收",
                "question": "项目如何把统一约束转成可验证成果",
                "logic": "说明标准验证如何进入建设和验收",
                "page_role": "content",
                "source_refs": ["F2"],
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


def test_v2_lean_schema_and_audit_keep_only_outline_and_source_boundaries() -> None:
    plan = _lean_plan()
    assert validate_deck_plan(plan) == []
    issues, _ = audit_deck_plan(plan, _foundation())
    assert issues == []

    drifted = deepcopy(plan)
    drifted["pages"][0]["source_refs"] = ["UNKNOWN"]
    issues, _ = audit_deck_plan(drifted, _foundation())
    assert any("LEAN_SOURCE_REF_UNKNOWN" in issue for issue in issues)


def test_v2_lean_plan_accepts_promoted_source_asset_boundary() -> None:
    plan = _lean_plan()
    foundation = _foundation()
    foundation["source_assets"] = [{"id": "ASSET-0123456789ABCDEF"}]
    plan["pages"][0]["source_refs"] = ["ASSET-0123456789ABCDEF"]

    issues, _ = audit_deck_plan(plan, foundation)

    assert not any("LEAN_SOURCE_REF_UNKNOWN" in issue for issue in issues)


def test_v2_lean_plan_rejects_author_and_visual_fields() -> None:
    plan = _lean_plan()
    plan["narrative_design"] = {"mode": "direct"}
    plan["pages"][0]["content"] = ["提前编写的内容"]
    plan["pages"][0]["onscreen_contract"] = {"relation": "parallel", "detail_axis": "对象", "modules": []}
    issues, _ = audit_deck_plan(plan, _foundation())
    assert any("PLAN_AUTHOR_FIELDS_FORBIDDEN" in issue for issue in issues)
    assert any("PLAN_PAGE_AUTHOR_FIELDS_FORBIDDEN" in issue for issue in issues)


def test_v2_final_script_owns_authored_message() -> None:
    plan = _lean_plan()
    slides = []
    for page in plan["pages"]:
        slides.append(
            {
                "id": page["id"],
                "page_type": "content",
                "title": page["title"],
                "core_message": "AUTHOR根据完整来源形成的页面判断",
                "full_copy": "国家部署给出总体任务，先行先试要求开展标准验证。",
                "onscreen": [{"heading": "依据", "items": ["国家部署给出总体任务", "先行先试要求开展标准验证"]}],
                "relationships": [],
                "speaker_notes": "建设任务需要统一验证尺度。",
                "source_refs": page["source_refs"],
            }
        )
    issues, _ = audit_final_script({"slides": slides}, plan, _foundation())
    assert not any("PLAN evidence-fit gate" in issue for issue in issues)
    assert not any("source_consumption" in issue for issue in issues)
    assert not any("AUTHOR_PAGE_PROPOSITION_DRIFTED" in issue for issue in issues)


def test_v2_lean_source_refs_are_evidence_boundary_not_full_copy_checklist() -> None:
    plan = _lean_plan()
    plan["pages"] = [plan["pages"][0]]
    foundation = _foundation()
    foundation["facts"][0]["semantic_units"] = [
        {"id": "F1-U1", "text": "国家部署给出总体任务"},
        {"id": "F1-U2", "text": "配套材料还列出若干非核心技术细节"},
    ]
    final = {
        "slides": [
            {
                "id": "P01",
                "page_type": "content",
                "title": "建设部署形成统一约束",
                "core_message": "国家部署已经形成统一建设约束。",
                "full_copy": "国家部署明确总体建设任务，由此形成项目必须遵循的统一约束。",
                "onscreen": [{"heading": "统一建设约束", "text": "国家部署明确总体建设任务"}],
                "source_refs": ["F1"],
            }
        ]
    }

    issues, _ = audit_final_script(final, plan, foundation)

    assert not any("F1-U2" in issue or "source_consumption" in issue for issue in issues)


def test_strict_foundation_requires_its_source_consumption_contract_before_authoring() -> None:
    plan = _lean_plan()
    foundation = _foundation()
    foundation.update(
        {
            "source_consumption_policy": "required",
            "source_consumption_contract_version": 2,
        }
    )

    issues, warnings = audit_deck_plan(plan, foundation)

    assert any("SOURCE_CONSUMPTION_CONTRACT_MISSING" in issue for issue in issues)
    assert not warnings


def test_legacy_plan_contract_is_rejected_by_schema() -> None:
    plan = _lean_plan()
    plan["plan_contract_version"] = 1
    plan["planning_profile"] = "strict"
    plan["evidence_fit_review_mode"] = "strict"
    foundation = _foundation()
    foundation["source_consumption_contract_version"] = 2

    assert validate_deck_plan(plan)


def test_whole_deck_audit_warns_on_uniform_author_shape_and_missing_relationships() -> None:
    plan = _lean_plan()
    plan["pages"] = []
    slides = []
    for index in range(6):
        page_id = f"P{index + 1:02d}"
        plan["pages"].append(
            {
                "id": page_id,
                "chapter_id": "C1",
                "title": f"主题{index + 1}",
                "question": f"问题{index + 1}",
                "logic": f"说明关系{index + 1}",
                "page_role": "content",
                "source_refs": ["F1"],
            }
        )
        slides.append(
            {
                "id": page_id,
                "page_type": "content",
                "title": f"主题{index + 1}",
                "core_message": "统一规则推动来源事实转化为建设行动",
                "full_copy": "国家部署给出总体任务。",
                "onscreen": [
                    {"heading": "国家部署明确总体任务", "items": ["总体任务形成建设依据"]},
                    {"heading": "统一规则推动任务落地", "items": ["建设行动承接总体要求"]},
                ],
                "relationships": [],
                "speaker_notes": "总体任务需要落实为具体行动。",
                "source_refs": ["F1"],
            }
        )

    _, warnings = audit_final_script({"slides": slides}, plan, _foundation())

    assert any("AUTHOR_STRUCTURE_FLATLINE" in warning for warning in warnings)
    assert any("AUTHOR_RELATIONSHIP_LAYER_ABSENT" in warning for warning in warnings)


def test_plan_review_shows_compact_outline_without_authoring_details() -> None:
    plan = _lean_plan()
    review = render_plan_review(plan, _foundation())
    assert "规划合同：v2 lean" in review
    assert "建设依据与验证职责" in review
    assert "说明国家部署形成的建设边界" in review
    assert "## 叙事选择" not in review


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

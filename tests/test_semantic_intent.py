from __future__ import annotations

from dataclasses import replace

from cyberppt.script_quality_contract import parse_script_markdown
from cyberppt.semantic_intent import (
    CANONICAL_INTENTS,
    SemanticIntentDecision,
    canonicalize_intent,
    legacy_intent_for,
    resolve_semantic_intent,
    validate_semantic_structure,
)
from scripts.imagegen_pipeline.imagegen_handoff import audit_page_semantic_intent


SCRIPT = """## 第1页：运行闭环

- 页面类型：内容页
- 页面标题：运行闭环
- 主判断：验证结果回流模型，形成持续校正。
- 视觉结构：闭环回流；结果返回处理节点
- 上屏文字：

  **输入｜数据**
  - 数据进入处理环节。
  **验证｜反馈**
  - 验证结果回流模型，形成持续校正。
"""


def test_registry_has_eighteen_unique_canonical_intents() -> None:
    assert len(CANONICAL_INTENTS) == 18
    assert len(set(CANONICAL_INTENTS)) == 18


def test_legacy_aliases_round_trip_to_supported_production_types() -> None:
    assert canonicalize_intent("closed_loop") == "closed_loop_operation"
    assert legacy_intent_for("closed_loop_operation") == "closed_loop"
    assert legacy_intent_for("network_ecosystem") == "capability_relationship"


def test_explicit_canonical_intent_has_highest_authority() -> None:
    decision = resolve_semantic_intent(
        explicit_intent="role_responsibility_map",
        legacy_intent="closed_loop",
        content_relations=({"relation": "feedback_to"},),
        corpus="反馈回流",
    )
    assert decision.primary_intent == "role_responsibility_map"
    assert decision.source == "explicit"
    assert decision.confidence == 1.0


def test_contract_relation_and_corpus_split_legacy_capability_bucket() -> None:
    decision = resolve_semantic_intent(
        legacy_intent="capability_relationship",
        content_relations=(
            {"relation": "responsible_for"},
            {"relation": "hands_off_to"},
        ),
        corpus="各主体明确职责分工与交付接口。",
    )
    assert decision.primary_intent == "role_responsibility_map"
    assert decision.source == "contract_relation"
    assert "responsible_for" in decision.supporting_relations
    assert decision.legacy_intent == "capability_relationship"


def test_parallel_application_engines_route_to_capability_outcomes() -> None:
    decision = resolve_semantic_intent(
        legacy_intent="capability_relationship",
        corpus=(
            "检索增强、画像推荐、教学诊断与分层预测分别支撑三类应用，"
            "三类引擎分别采用适合学习、教学和规划分析的模型与工作流。"
        ),
    )
    assert decision.primary_intent == "capability_to_outcomes"
    assert decision.legacy_intent == "capability_relationship"


def test_negated_loop_phrase_does_not_create_loop_intent() -> None:
    decision = resolve_semantic_intent(corpus="当前尚未形成闭环，只有阶段性输出。")
    assert decision.primary_intent != "closed_loop_operation"


def test_legacy_only_decision_is_low_confidence_and_non_authoritative() -> None:
    decision = resolve_semantic_intent(legacy_intent="hierarchy_support")
    assert decision.primary_intent == "layered_architecture"
    assert decision.source == "legacy_hint"
    assert decision.confidence == 0.5


def test_closed_loop_gate_requires_feedback_evidence() -> None:
    decision = SemanticIntentDecision(
        "closed_loop_operation", (), "explicit", 1.0, (), (), (), "closed_loop"
    )
    assert validate_semantic_structure(decision, corpus="三个并列模块") == (
        "SEMANTIC_LOOP_MISSING_FEEDBACK",
    )
    assert validate_semantic_structure(
        decision,
        corpus="结果反馈到模型进行下一轮修订",
    ) == ()


def test_shadow_audit_preserves_legacy_production_selector() -> None:
    page = parse_script_markdown(SCRIPT).pages[0]
    page = replace(
        page,
        contract_receipt={
            "content_relations": [
                {"from": "验证结果", "relation": "feedback_to", "to": "模型"}
            ]
        },
    )
    record = audit_page_semantic_intent(page)
    assert record["legacy_intent"] == "closed_loop"
    assert record["primary_intent"] == "closed_loop_operation"
    assert record["legacy_matches"] is True
    assert record["blocking_issues"] == []
    assert record["composition"]["reading_path"][-1] == "feedback"
    assert len(record["visual_carrier"]["candidates"]) == 3
    assert "Reading path:" in record["composition_guidance"]

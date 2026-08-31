"""Executable Stage1 authoring fixtures shared by cross-layer regressions.

These cases model business semantics only.  They intentionally do not add a
new Stage1 schema or persisted IR.  ``verified_relationships`` represents the
layout-neutral semantic graph; ``visual_structure`` is the authored Final
Script surface that Stage2 is expected to interpret without rewriting copy.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthoringRelationCase:
    name: str
    authoring_topology: str
    expected_semantic_topology: str
    expected_expression_form: str
    verified_relationships: tuple[dict[str, object], ...]
    visual_structure: str
    module_titles: tuple[str, ...]
    page_text: str = ""

    @property
    def module_count(self) -> int:
        return len(self.module_titles)


def _relation(subject: str, relation: str, *objects: str) -> dict[str, object]:
    return {
        "subject": subject,
        "relation": relation,
        "objects": list(objects),
        "confidence": 1.0,
        "constraint_authority": "hard",
    }


def correct_relationship_cases() -> tuple[AuthoringRelationCase, ...]:
    """Return the eight golden relation families as fresh executable cases."""

    return (
        AuthoringRelationCase(
            name="parallel_mece",
            authoring_topology="parallel grouping",
            expected_semantic_topology="peer_set",
            expected_expression_form="parallel_classification_3_6",
            verified_relationships=(
                _relation(
                    "统一预测体系",
                    "peer_classification",
                    "研判范围",
                    "周期规则",
                    "运行闭环",
                ),
            ),
            visual_structure=(
                "主体采用并列分类，研判范围、周期规则和运行闭环三项处于同一层级，"
                "相互独立并共同支撑统一预测体系。"
            ),
            module_titles=("研判范围", "周期规则", "运行闭环"),
        ),
        AuthoringRelationCase(
            name="flow_feedback",
            authoring_topology="directed chain + feedback",
            expected_semantic_topology="feedback_loop",
            expected_expression_form="operation_loop",
            verified_relationships=(
                _relation("数据与规则", "sequence_before", "预测研判"),
                _relation("预测研判", "sequence_before", "审校发布"),
                _relation("审校发布", "sequence_before", "误差复盘"),
                _relation("误差复盘", "feeds_back_to", "数据与规则"),
            ),
            visual_structure=(
                "数据与规则 → 预测研判：顺序衔接\n"
                "预测研判 → 审校发布：顺序衔接\n"
                "审校发布 → 误差复盘：顺序衔接\n"
                "误差复盘 → 数据与规则：反馈回流"
            ),
            module_titles=("数据与规则", "预测研判", "审校发布", "误差复盘"),
        ),
        AuthoringRelationCase(
            name="causal_chain",
            authoring_topology="directed chain",
            expected_semantic_topology="causal_chain",
            expected_expression_form="causal_chain",
            verified_relationships=(
                _relation("数据口径不一致", "causes", "跨周期结论不可比"),
                _relation("跨周期结论不可比", "causes", "风险判断难以持续复盘"),
            ),
            visual_structure=(
                "数据口径不一致 → 跨周期结论不可比：因果导致\n"
                "跨周期结论不可比 → 风险判断难以持续复盘：因果导致"
            ),
            module_titles=("数据口径不一致", "跨周期结论不可比", "风险判断难以持续复盘"),
        ),
        AuthoringRelationCase(
            name="support_convergence",
            authoring_topology="convergence",
            expected_semantic_topology="support_convergence",
            expected_expression_form="support_convergence_3_6",
            verified_relationships=(
                _relation("统一数据口径", "supports", "持续风险预警"),
                _relation("跨周期分析框架", "supports", "持续风险预警"),
                _relation("误差复盘机制", "supports", "持续风险预警"),
            ),
            visual_structure=(
                "统一数据口径 → 持续风险预警：共同支撑\n"
                "跨周期分析框架 → 持续风险预警：共同支撑\n"
                "误差复盘机制 → 持续风险预警：共同支撑"
            ),
            module_titles=("统一数据口径", "跨周期分析框架", "误差复盘机制"),
        ),
        AuthoringRelationCase(
            name="mapping",
            authoring_topology="mapping",
            expected_semantic_topology="mapping",
            expected_expression_form="mapping_2_6",
            verified_relationships=(
                _relation("口径不统一", "problem_response", "统一指标与版本规则"),
                _relation("结果不可追溯", "problem_response", "审校与复盘留痕"),
            ),
            visual_structure=(
                "口径不统一 → 统一指标与版本规则：问题回应\n"
                "结果不可追溯 → 审校与复盘留痕：问题回应"
            ),
            module_titles=("口径不统一", "统一指标与版本规则", "结果不可追溯", "审校与复盘留痕"),
        ),
        AuthoringRelationCase(
            name="comparison",
            authoring_topology="comparison",
            expected_semantic_topology="comparison",
            expected_expression_form="comparison_2col",
            verified_relationships=(
                _relation("分散预测模式", "comparison", "统一预测体系"),
            ),
            visual_structure="分散预测模式 → 统一预测体系：对照比较",
            module_titles=("分散预测模式", "统一预测体系"),
        ),
        AuthoringRelationCase(
            name="roadmap",
            authoring_topology="roadmap",
            expected_semantic_topology="sequence",
            expected_expression_form="flow_3_5",
            verified_relationships=(
                _relation("规则贯通", "sequence_before", "跨周期试运行"),
                _relation("跨周期试运行", "sequence_before", "常态化运行"),
            ),
            visual_structure=(
                "规则贯通 → 跨周期试运行：顺序衔接\n"
                "跨周期试运行 → 常态化运行：顺序衔接"
            ),
            module_titles=("规则贯通", "跨周期试运行", "常态化运行"),
            page_text="进入条件满足后逐步推进，阶段完成时形成可验证的新运行状态。",
        ),
        AuthoringRelationCase(
            name="governance_boundary",
            authoring_topology="governance chain",
            expected_semantic_topology="dependency_chain",
            expected_expression_form="directed_dependency_2_6",
            verified_relationships=(
                _relation("使用申请", "directed_dependency", "授权决策"),
                _relation("授权决策", "directed_dependency", "受控调用"),
                _relation("受控调用", "directed_dependency", "审计记录"),
            ),
            visual_structure=(
                "使用申请 → 授权决策：提供基础\n"
                "授权决策 → 受控调用：前提\n"
                "受控调用 → 审计记录：提供基础"
            ),
            module_titles=("使用申请", "授权决策", "受控调用", "审计记录"),
        ),
    )


__all__ = ["AuthoringRelationCase", "correct_relationship_cases"]

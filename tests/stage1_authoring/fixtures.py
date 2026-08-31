"""Executable Stage1 authoring fixtures shared by cross-layer regressions.

These cases model business semantics only. They intentionally do not add a new
Stage1 schema or persisted IR. ``verified_relationships`` represents the
layout-neutral semantic graph; ``visual_structure`` mirrors the current golden
page relation surface that Stage2 is expected to interpret without rewriting
copy.
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
    """Return the eight current golden relation families as executable cases."""

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
                    "运行机制",
                ),
            ),
            visual_structure=(
                "主体采用并列分类，研判范围、周期规则和运行机制三项处于同一层级，"
                "相互独立并共同支撑统一预测体系；兄弟单元之间无方向。"
            ),
            module_titles=("研判范围", "周期规则", "运行机制"),
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
                "数据与规则 → 预测研判：顺序衔接｜交接物：统一数据目录、指标口径、版本标识、周期范围\n"
                "预测研判 → 审校发布：顺序衔接｜交接物：研判结论、情景结果、关键假设\n"
                "审校发布 → 误差复盘：顺序衔接｜交接物：正式发布版本、结论清单、误差记录\n"
                "误差复盘 → 数据与规则：反馈回流｜回写物：偏差原因、口径调整、版本修订、参数修正"
            ),
            module_titles=("数据与规则", "预测研判", "审校发布", "误差复盘"),
        ),
        AuthoringRelationCase(
            name="causal_chain",
            authoring_topology="directed chain",
            expected_semantic_topology="causal_chain",
            expected_expression_form="causal_chain",
            verified_relationships=(
                _relation("数据口径和版本分散", "causes", "同一指标计算基准不一致"),
                _relation("同一指标计算基准不一致", "causes", "跨周期结论难以校核"),
                _relation("跨周期结论难以校核", "causes", "预测偏差难以追溯"),
                _relation("预测偏差难以追溯", "causes", "风险预警难以持续更新"),
            ),
            visual_structure=(
                "数据口径和版本分散 → 同一指标计算基准不一致：因果导致\n"
                "同一指标计算基准不一致 → 跨周期结论难以校核：因果导致\n"
                "跨周期结论难以校核 → 预测偏差难以追溯：因果导致\n"
                "预测偏差难以追溯 → 风险预警难以持续更新：因果导致"
            ),
            module_titles=(
                "数据口径和版本分散",
                "同一指标计算基准不一致",
                "跨周期结论难以校核",
                "预测偏差难以追溯",
                "风险预警难以持续更新",
            ),
        ),
        AuthoringRelationCase(
            name="support_convergence",
            authoring_topology="convergence",
            expected_semantic_topology="support_convergence",
            expected_expression_form="support_convergence_3_6",
            verified_relationships=(
                _relation("供给边界输入", "supports", "综合供需风险判断"),
                _relation("需求压力输入", "supports", "综合供需风险判断"),
                _relation("互济缓释输入", "supports", "综合供需风险判断"),
                _relation("波动扰动输入", "supports", "综合供需风险判断"),
            ),
            visual_structure=(
                "供给边界输入 → 综合供需风险判断：共同支撑\n"
                "需求压力输入 → 综合供需风险判断：共同支撑\n"
                "互济缓释输入 → 综合供需风险判断：共同支撑\n"
                "波动扰动输入 → 综合供需风险判断：共同支撑"
            ),
            module_titles=("供给边界输入", "需求压力输入", "互济缓释输入", "波动扰动输入"),
        ),
        AuthoringRelationCase(
            name="mapping",
            authoring_topology="mapping",
            expected_semantic_topology="mapping",
            expected_expression_form="mapping_2_6",
            verified_relationships=(
                _relation("供给波动", "problem_response", "可用能力与检修受限分析"),
                _relation("需求峰值", "problem_response", "负荷情景与峰谷爬坡分析"),
                _relation("市场互济", "problem_response", "跨区跨省交易与可调用空间分析"),
                _relation("新能源偏差", "problem_response", "概率区间与多情景分析"),
            ),
            visual_structure=(
                "供给波动 → 可用能力与检修受限分析：问题回应\n"
                "需求峰值 → 负荷情景与峰谷爬坡分析：问题回应\n"
                "市场互济 → 跨区跨省交易与可调用空间分析：问题回应\n"
                "新能源偏差 → 概率区间与多情景分析：问题回应"
            ),
            module_titles=(
                "供给波动",
                "可用能力与检修受限分析",
                "需求峰值",
                "负荷情景与峰谷爬坡分析",
                "市场互济",
                "跨区跨省交易与可调用空间分析",
                "新能源偏差",
                "概率区间与多情景分析",
            ),
        ),
        AuthoringRelationCase(
            name="comparison",
            authoring_topology="comparison",
            expected_semantic_topology="comparison",
            expected_expression_form="comparison_2col",
            verified_relationships=(
                _relation("分散预测方式", "comparison", "统一预测体系"),
            ),
            visual_structure="比较对象｜分散预测方式 vs 统一预测体系：对照比较",
            module_titles=("分散预测方式", "统一预测体系"),
        ),
        AuthoringRelationCase(
            name="roadmap",
            authoring_topology="roadmap",
            expected_semantic_topology="sequence",
            expected_expression_form="flow_3_5",
            verified_relationships=(
                _relation("S0 当前分散基础", "sequence_before", "S1 共同输入可复用"),
                _relation("S1 共同输入可复用", "sequence_before", "S2 跨周期结论可比较"),
                _relation("S2 跨周期结论可比较", "sequence_before", "S3 复盘回写常态化"),
            ),
            visual_structure=(
                "S0 当前分散基础 → S1 共同输入可复用：顺序演进｜进入条件：首批数据、指标、周期范围和责任边界明确\n"
                "S1 共同输入可复用 → S2 跨周期结论可比较：顺序演进｜进入条件：共同输入稳定并可连续支持月季年分析\n"
                "S2 跨周期结论可比较 → S3 复盘回写常态化：顺序演进｜进入条件：关键结论稳定复核且主要偏差可追溯"
            ),
            module_titles=(
                "S0 当前分散基础",
                "S1 共同输入可复用",
                "S2 跨周期结论可比较",
                "S3 复盘回写常态化",
            ),
            page_text=(
                "Roadmap 以前状态、进入条件和新状态构成可验证状态跃迁；"
                "S1、S2 分别成为后一阶段的实际前置基础。"
            ),
        ),
        AuthoringRelationCase(
            name="governance_boundary",
            authoring_topology="governance chain",
            expected_semantic_topology="dependency_chain",
            expected_expression_form="directed_dependency_2_6",
            verified_relationships=(
                _relation("业务牵头方", "directed_dependency", "业务口径与结论边界"),
                _relation("数据责任方", "directed_dependency", "数据来源与版本记录"),
                _relation("分析执行方", "directed_dependency", "模型方法与计算过程"),
                _relation("业务口径与结论边界", "directed_dependency", "共同控制机制"),
                _relation("数据来源与版本记录", "directed_dependency", "共同控制机制"),
                _relation("模型方法与计算过程", "directed_dependency", "共同控制机制"),
                _relation("共同控制机制", "directed_dependency", "受保护结果"),
            ),
            visual_structure=(
                "业务牵头方 → 业务口径与结论边界：责任绑定\n"
                "数据责任方 → 数据来源与版本记录：责任绑定\n"
                "分析执行方 → 模型方法与计算过程：责任绑定\n"
                "业务口径与结论边界 → 共同控制机制：治理汇入\n"
                "数据来源与版本记录 → 共同控制机制：治理汇入\n"
                "模型方法与计算过程 → 共同控制机制：治理汇入\n"
                "共同控制机制 → 受保护结果：保护结果"
            ),
            module_titles=("业务牵头方", "数据责任方", "分析执行方", "共同控制机制"),
        ),
    )


__all__ = ["AuthoringRelationCase", "correct_relationship_cases"]

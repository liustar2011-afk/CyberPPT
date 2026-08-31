"""Negative authoring fixtures for Stage1 quality regressions.

The fixture metadata deliberately distinguishes deterministic checks from
semantic Critic checks.  A negative example being present here is not a reason
to add a regex rule; only cases marked ``lint`` are expected to map to a stable
machine-readable lint code.
"""
from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AuthoringFailureCase:
    name: str
    failure_class: str
    detection_mode: str
    source_semantics: str
    incorrect_surface: str
    expected_lint_codes: tuple[str, ...] = ()
    rationale: str = ""


def failure_cases() -> tuple[AuthoringFailureCase, ...]:
    return (
        AuthoringFailureCase(
            name="direction_flattened",
            failure_class="directional_relation_flattened",
            detection_mode="cross_layer_regression",
            source_semantics="数据准备 → 预测研判 → 审校发布，存在真实顺序关系。",
            incorrect_surface="数据准备、预测研判、审校发布被改写成三个无方向的并列模块。",
            rationale="关系端点仍在，但顺序语义丢失；应通过 source/Final Script 关系保持回归发现。",
        ),
        AuthoringFailureCase(
            name="fake_mece",
            failure_class="false_parallel_mece",
            detection_mode="critic",
            source_semantics="三个单元分别表达原因、处置动作和结果，不处于同一语义维度。",
            incorrect_surface="将原因、动作、结果包装成三个同级并列分类。",
            rationale="是否同维度需要语义判断，不新增关键词式 MECE lint。",
        ),
        AuthoringFailureCase(
            name="orphan_evidence",
            failure_class="evidence_binding_lost",
            detection_mode="critic_existing_contracts",
            source_semantics="证据应直接证明或限定其父级论点，并保留对象、作用或边界。",
            incorrect_surface="只留下一个来源名称或孤立事实，无法判断它证明哪个论点。",
            rationale="优先复用既有 Evidence layer / source-detail contracts，不创建同义 EVIDENCE_ORPHAN 规则。",
        ),
        AuthoringFailureCase(
            name="parent_child_repetition",
            failure_class="parent_child_semantic_repetition",
            detection_mode="critic_existing_contracts",
            source_semantics="明细应补充父级标题的新事实、动作、机制、条件或结果。",
            incorrect_surface="模块标题与唯一明细逐字或近义重复，没有新增信息。",
            rationale="复用既有 hierarchy / role repetition 检查，不另造重复 lint。",
        ),
        AuthoringFailureCase(
            name="mapping_endpoint_missing",
            failure_class="mapping_endpoint_missing",
            detection_mode="cross_layer_regression",
            source_semantics="口径不统一 → 统一指标与版本规则；结果不可追溯 → 审校与复盘留痕。",
            incorrect_surface="上屏只保留两个解决动作，问题端点被删除，映射关系不可恢复。",
            rationale="通过 Final Script → Stage2 relationship adapter 的端点保持测试发现。",
        ),
        AuthoringFailureCase(
            name="roadmap_stage_names_only",
            failure_class="roadmap_incomplete",
            detection_mode="lint",
            source_semantics="每个阶段都应有时间/触发条件，并说明阶段完成后的新状态。",
            incorrect_surface="阶段一：数据治理；阶段二：联合分析。",
            expected_lint_codes=("ROADMAP_TRIGGER_MISSING", "ROADMAP_NEW_STATE_MISSING"),
            rationale="属于可机械判定的 Roadmap completeness 底线。",
        ),
        AuthoringFailureCase(
            name="governance_actor_misalignment",
            failure_class="governance_actor_responsibility_misaligned",
            detection_mode="critic",
            source_semantics="授权主体作出授权决策，使用方在授权边界内调用，平台记录审计证据。",
            incorrect_surface="将使用方写成授权决策主体，或把平台审计职责写成业务使用责任。",
            rationale="主体职责需要理解业务语义和来源约束，保留给 AUTHOR/CRITIQUE 判断。",
        ),
        AuthoringFailureCase(
            name="bare_number_without_object",
            failure_class="number_without_business_object",
            detection_mode="lint",
            source_semantics="数字必须与覆盖对象、成果对象、指标名称或业务动作绑定。",
            incorrect_surface="80% / 30家 / 3项",
            expected_lint_codes=("ONSCREEN_NUMBER_WITHOUT_OBJECT",),
            rationale="属于已落地的确定性上屏文字底线。",
        ),
    )


def _example() -> dict:
    return json.loads(
        (ROOT / "examples" / "final-script.example.json").read_text(encoding="utf-8")
    )


def build_lint_failure_payload(name: str) -> dict:
    """Build only negative cases with stable deterministic lint expectations."""

    payload = copy.deepcopy(_example())
    slide = payload["slides"][0]

    if name == "bare_number_without_object":
        slide["onscreen"][0]["items"] = ["80%", "30家", "3项"]
        return payload

    if name == "roadmap_stage_names_only":
        slide["argument"] = {
            "pattern": "roadmap",
            "chain": ["数据治理", "联合分析"],
        }
        slide["onscreen"] = [
            {"heading": "阶段一推进数据治理", "items": ["统一目录和口径"]},
            {"heading": "阶段二开展联合分析", "items": ["开展联合分析"]},
        ]
        return payload

    raise KeyError(f"failure fixture is not a deterministic lint case: {name}")


__all__ = [
    "AuthoringFailureCase",
    "build_lint_failure_payload",
    "failure_cases",
]

"""Canonical semantic-intent decisions for page visual structure.

This module deliberately separates source-supported business relations from
legacy ImageGen layout labels.  It is dependency-free so Stage 01, audits, and
the ImageGen handoff can share the same deterministic contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence


CANONICAL_INTENTS = (
    "single_judgment_anchor",
    "multi_semantic_foundation",
    "evidence_to_judgment",
    "scene_embedded_flow",
    "transformation_pipeline",
    "convergence_to_capability",
    "capability_to_outcomes",
    "layered_architecture",
    "dual_engine_synergy",
    "closed_loop_operation",
    "comparison_tension",
    "phased_roadmap",
    "network_ecosystem",
    "policy_to_action",
    "risk_control_boundary",
    "data_flow_value_chain",
    "role_responsibility_map",
    "problem_cause_resolution",
)

LEGACY_TO_CANONICAL = {
    "boundary_guardrail": "risk_control_boundary",
    "crosscutting_chain": "layered_architecture",
    "hierarchy_support": "layered_architecture",
    "multi_semantic_foundation": "multi_semantic_foundation",
    "comparison": "comparison_tension",
    "closed_loop": "closed_loop_operation",
    "path_chain": "transformation_pipeline",
    "phase": "phased_roadmap",
    "capability_relationship": "convergence_to_capability",
    "decision_admission": "risk_control_boundary",
    "scenario_application": "scene_embedded_flow",
    "causal": "problem_cause_resolution",
    "judgment_evidence": "evidence_to_judgment",
}

# Weak-signal candidates used only for legacy-hint *scoring*.  Unlike
# LEGACY_TO_CANONICAL (which picks one deterministic representative for
# explicit/legacy comparisons), this table lets a single legacy label boost
# every canonical intent it could plausibly mean, mirroring RELATION_CANDIDATES.
LEGACY_HINT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "boundary_guardrail": ("risk_control_boundary",),
    "crosscutting_chain": ("layered_architecture",),
    "hierarchy_support": ("layered_architecture",),
    "multi_semantic_foundation": ("multi_semantic_foundation",),
    "comparison": ("comparison_tension",),
    "closed_loop": ("closed_loop_operation",),
    "path_chain": ("transformation_pipeline", "data_flow_value_chain", "policy_to_action"),
    "phase": ("phased_roadmap", "transformation_pipeline"),
    "capability_relationship": (
        "convergence_to_capability",
        "capability_to_outcomes",
        "dual_engine_synergy",
        "network_ecosystem",
        "role_responsibility_map",
    ),
    "decision_admission": ("risk_control_boundary",),
    "scenario_application": ("scene_embedded_flow",),
    "causal": ("problem_cause_resolution",),
    "judgment_evidence": ("evidence_to_judgment", "single_judgment_anchor"),
}

CANONICAL_TO_LEGACY = {
    "single_judgment_anchor": "judgment_evidence",
    "multi_semantic_foundation": "multi_semantic_foundation",
    "evidence_to_judgment": "judgment_evidence",
    "scene_embedded_flow": "scenario_application",
    "transformation_pipeline": "path_chain",
    "convergence_to_capability": "capability_relationship",
    "capability_to_outcomes": "capability_relationship",
    "layered_architecture": "hierarchy_support",
    "dual_engine_synergy": "capability_relationship",
    "closed_loop_operation": "closed_loop",
    "comparison_tension": "comparison",
    "phased_roadmap": "phase",
    "network_ecosystem": "capability_relationship",
    "policy_to_action": "path_chain",
    "risk_control_boundary": "boundary_guardrail",
    "data_flow_value_chain": "path_chain",
    "role_responsibility_map": "capability_relationship",
    "problem_cause_resolution": "causal",
}

# Relation routing is intentionally many-to-many.  The first candidate is the
# conservative default; evidence in the page corpus may promote a narrower one.
RELATION_CANDIDATES: dict[str, tuple[str, ...]] = {
    "composed_of": ("layered_architecture",),
    "contains": ("layered_architecture",),
    "part_of": ("layered_architecture",),
    "classified_as": ("layered_architecture",),
    "layered_as": ("layered_architecture",),
    "depends_on": ("layered_architecture",),
    "sequence_before": ("phased_roadmap", "transformation_pipeline"),
    "sequence_after": ("phased_roadmap", "transformation_pipeline"),
    "transforms_into": ("transformation_pipeline",),
    "input_to": ("transformation_pipeline", "data_flow_value_chain"),
    "output_of": ("transformation_pipeline", "capability_to_outcomes"),
    "feedback_to": ("closed_loop_operation",),
    "iterates_with": ("closed_loop_operation",),
    "supports": ("convergence_to_capability", "layered_architecture"),
    "provides_to": ("capability_to_outcomes", "role_responsibility_map"),
    "produces": ("capability_to_outcomes",),
    "converges_into": ("convergence_to_capability",),
    "expands_to": ("capability_to_outcomes",),
    "corresponds_to": ("role_responsibility_map", "dual_engine_synergy"),
    "applies_to": ("scene_embedded_flow", "policy_to_action"),
    "covers": ("scene_embedded_flow",),
    "owned_by": ("role_responsibility_map",),
    "responsible_for": ("role_responsibility_map",),
    "collaborates_with": ("dual_engine_synergy", "network_ecosystem"),
    "hands_off_to": ("role_responsibility_map", "scene_embedded_flow"),
    "bounded_by": ("risk_control_boundary",),
    "authorized_by": ("risk_control_boundary", "policy_to_action"),
    "filtered_by": ("risk_control_boundary",),
    "admitted_by": ("risk_control_boundary",),
    "prohibited_from": ("risk_control_boundary",),
    "audited_by": ("risk_control_boundary", "closed_loop_operation"),
    "causes": ("problem_cause_resolution",),
    "contributes_to": ("problem_cause_resolution",),
    "constrained_by": ("problem_cause_resolution", "risk_control_boundary"),
    "resolved_by": ("problem_cause_resolution",),
    "mitigated_by": ("problem_cause_resolution", "risk_control_boundary"),
    "requires": ("policy_to_action",),
    "implemented_as": ("policy_to_action",),
}

INTENT_SIGNALS: dict[str, tuple[str, ...]] = {
    "single_judgment_anchor": ("核心结论", "唯一结论", "总体判断", "一句话结论", "关键判断"),
    "closed_loop_operation": ("反馈", "回流", "复盘", "迭代", "回到"),
    "transformation_pipeline": ("输入", "处理", "输出", "转化", "加工"),
    "convergence_to_capability": ("汇聚", "汇集", "形成能力", "统一中枢"),
    "capability_to_outcomes": (
        "产生结果",
        "形成成果",
        "服务于",
        "输出到",
        "分别支撑",
        "三类应用",
        "分别采用",
    ),
    "dual_engine_synergy": ("双侧", "双方", "双轮", "两个主体", "协同"),
    "network_ecosystem": ("多主体", "生态", "交换", "多方协同"),
    "role_responsibility_map": ("职责", "分工", "责任", "交付接口"),
    "policy_to_action": ("政策要求", "落实为", "建设任务", "工作要求"),
    "data_flow_value_chain": ("数据流", "流转", "受控调用", "价值形成"),
    "scene_embedded_flow": ("业务场景", "现场", "作业", "应用场景"),
    "layered_architecture": ("分层", "底座", "平台层", "应用层", "上下依赖"),
    "phased_roadmap": ("阶段", "近期", "中期", "远期", "里程碑"),
    "comparison_tension": ("对比", "差异", "相较", "前后变化"),
    "risk_control_boundary": ("边界", "授权", "准入", "不得", "受控"),
    "problem_cause_resolution": ("原因", "导致", "问题", "解决", "缓解"),
}

NEGATED_MARKERS = ("尚未", "未形成", "不构成", "并非", "不是")


@dataclass(frozen=True)
class SemanticIntentDecision:
    primary_intent: str
    secondary_intents: tuple[str, ...]
    source: str
    confidence: float
    supporting_relations: tuple[str, ...]
    evidence: tuple[str, ...]
    rejected_candidates: tuple[dict[str, str], ...] = ()
    legacy_intent: str = ""

    def __post_init__(self) -> None:
        if self.primary_intent not in CANONICAL_INTENTS:
            raise ValueError(f"unsupported semantic intent: {self.primary_intent}")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def canonicalize_intent(value: str) -> str:
    value = value.strip()
    if value in CANONICAL_INTENTS:
        return value
    return LEGACY_TO_CANONICAL.get(value, "")


def legacy_intent_for(value: str) -> str:
    canonical = canonicalize_intent(value)
    return CANONICAL_TO_LEGACY.get(canonical, "judgment_evidence")


def _relation_names(relations: Iterable[Mapping[str, object]]) -> tuple[str, ...]:
    ordered: list[str] = []
    for item in relations:
        name = str(item.get("relation") or "").strip()
        if name and name not in ordered:
            ordered.append(name)
    return tuple(ordered)


def _signal_hits(intent: str, corpus: str) -> tuple[str, ...]:
    hits: list[str] = []
    for phrase in INTENT_SIGNALS.get(intent, ()):
        if phrase not in corpus:
            continue
        positions = [index for index in range(len(corpus)) if corpus.startswith(phrase, index)]
        if all(any(marker in corpus[max(0, pos - 8):pos] for marker in NEGATED_MARKERS) for pos in positions):
            continue
        hits.append(phrase)
    return tuple(hits)


def resolve_semantic_intent(
    *,
    explicit_intent: str = "",
    legacy_intent: str = "",
    content_relations: Sequence[Mapping[str, object]] = (),
    corpus: str = "",
) -> SemanticIntentDecision:
    """Resolve a canonical intent without inventing unsupported relations."""

    explicit = canonicalize_intent(explicit_intent)
    if explicit:
        return SemanticIntentDecision(
            explicit, (), "explicit", 1.0, (), (explicit_intent.strip(),), (), legacy_intent_for(explicit)
        )

    relation_names = _relation_names(content_relations)
    scores: dict[str, float] = {}
    evidence: dict[str, list[str]] = {}
    for relation in relation_names:
        for rank, intent in enumerate(RELATION_CANDIDATES.get(relation, ())):
            scores[intent] = scores.get(intent, 0.0) + (4.0 if rank == 0 else 2.0)
            evidence.setdefault(intent, []).append(f"relation:{relation}")
    for intent in CANONICAL_INTENTS:
        hits = _signal_hits(intent, corpus)
        if hits:
            scores[intent] = scores.get(intent, 0.0) + min(3.0, float(len(hits)))
            evidence.setdefault(intent, []).extend(f"signal:{hit}" for hit in hits)
    if "分别支撑" in corpus and "三类应用" in corpus:
        scores["capability_to_outcomes"] = scores.get("capability_to_outcomes", 0.0) + 2.0
        evidence.setdefault("capability_to_outcomes", []).append(
            "compound:分别支撑三类应用"
        )

    legacy_key = legacy_intent.strip()
    legacy_candidates = LEGACY_HINT_CANDIDATES.get(legacy_key, ())
    if not legacy_candidates:
        legacy_single = canonicalize_intent(legacy_intent)
        legacy_candidates = (legacy_single,) if legacy_single else ()
    for rank, intent in enumerate(legacy_candidates):
        scores[intent] = scores.get(intent, 0.0) + (1.5 if rank == 0 else 0.7)
        evidence.setdefault(intent, []).append(f"legacy:{legacy_intent}")

    if not scores:
        return SemanticIntentDecision(
            "evidence_to_judgment", (), "fallback", 0.35, (), (), (), "judgment_evidence"
        )

    ranked = sorted(scores.items(), key=lambda item: (-item[1], CANONICAL_INTENTS.index(item[0])))
    primary, top_score = ranked[0]
    secondary = tuple(intent for intent, score in ranked[1:] if score >= max(3.0, top_score - 2.0))[:2]
    has_semantic_evidence = any(
        item.startswith("signal:") for item in evidence.get(primary, ())
    )
    source = (
        "contract_relation"
        if relation_names
        else "semantic_scored"
        if has_semantic_evidence
        else "legacy_hint"
    )
    confidence = (
        0.5 if source == "legacy_hint" else min(0.95, 0.55 + 0.06 * top_score)
    )
    rejected = tuple(
        {"intent": intent, "reason": f"score {score:g} below selected {top_score:g}"}
        for intent, score in ranked[1:4]
        if intent not in secondary
    )
    return SemanticIntentDecision(
        primary,
        secondary,
        source,
        round(confidence, 2),
        relation_names,
        tuple(evidence.get(primary, ())),
        rejected,
        legacy_intent_for(primary),
    )


def validate_semantic_structure(
    decision: SemanticIntentDecision,
    *,
    corpus: str,
    content_relations: Sequence[Mapping[str, object]] = (),
) -> tuple[str, ...]:
    """Return deterministic blocking issue codes for high-risk structures."""

    relations = set(_relation_names(content_relations))
    issues: list[str] = []
    if decision.primary_intent == "closed_loop_operation":
        has_feedback = bool(relations & {"feedback_to", "iterates_with"}) or bool(
            _signal_hits("closed_loop_operation", corpus)
        )
        if not has_feedback:
            issues.append("SEMANTIC_LOOP_MISSING_FEEDBACK")
    elif decision.primary_intent == "layered_architecture":
        has_layer = bool(relations & {"layered_as", "depends_on", "part_of"}) or bool(
            _signal_hits("layered_architecture", corpus)
        )
        if not has_layer:
            issues.append("SEMANTIC_LAYER_MISSING_DEPENDENCY")
    elif decision.primary_intent == "risk_control_boundary":
        has_boundary = bool(relations & {"bounded_by", "authorized_by", "filtered_by", "admitted_by", "prohibited_from"}) or bool(
            _signal_hits("risk_control_boundary", corpus)
        )
        if not has_boundary:
            issues.append("SEMANTIC_BOUNDARY_MISSING_CONTROL")
    elif decision.primary_intent in {"transformation_pipeline", "phased_roadmap"}:
        has_direction = bool(relations & {"sequence_before", "sequence_after", "transforms_into", "input_to", "output_of"}) or bool(
            _signal_hits(decision.primary_intent, corpus)
        )
        if not has_direction:
            issues.append("SEMANTIC_PATH_MISSING_DIRECTION")
    return tuple(issues)

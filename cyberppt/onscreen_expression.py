"""Classify professional on-screen expression forms without choosing a layout.

Stage 02 now prefers a verified semantic topology.  Raw relationship names are
retained only as a compatibility fallback for legacy callers; they are no
longer the primary authority in the official handoff path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from cyberppt.relation_semantics import resolve_relation_expression


@dataclass(frozen=True)
class ExpressionSpec:
    key: str
    label: str
    module_range: tuple[int, int]
    heading_grammar: str
    heading_policy: str = "parallel_proposition"
    require_return_relation: bool = False
    relation_pattern: str = ""
    reading_requirement: str = ""
    balance_requirement: str = ""
    required_features: tuple[str, ...] = ()
    anti_patterns: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExpressionDecision:
    form: str
    source: str
    confidence: float
    evidence: tuple[str, ...]
    candidates: tuple[tuple[str, float], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "form": self.form,
            "source": self.source,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "candidates": [[form, score] for form, score in self.candidates],
        }


@dataclass(frozen=True)
class ExpressionAuditFinding:
    code: str
    message: str
    action: str
    evidence: tuple[str, ...]
    severity: str = "error"


EXPRESSION_SPECS: dict[str, ExpressionSpec] = {
    "framework_4": ExpressionSpec(
        "framework_4", "四模块框架", (4, 4), "parallel_noun", "parallel_fact",
        relation_pattern="peer_modules", reading_requirement="parallel",
        balance_requirement="four peers have comparable reading weight",
        required_features=("four_peer_nodes", "peer_balance"),
        anti_patterns=("forced_sequence", "dominant_center"),
    ),
    "key_points_3": ExpressionSpec(
        "key_points_3", "三要素结构", (3, 3), "parallel_phrase", "parallel_proposition",
        relation_pattern="peer_key_points", reading_requirement="parallel",
        balance_requirement="three points jointly support one page judgment",
        required_features=("three_peer_points", "shared_judgment"),
        anti_patterns=("invented_causality", "invented_time_order"),
    ),
    "parallel_classification_3_6": ExpressionSpec(
        "parallel_classification_3_6", "三至六项并列分类", (3, 6), "parallel_noun", "classification_segment",
        relation_pattern="peer_taxonomy", reading_requirement="parallel",
        balance_requirement="peer categories remain peers; no sequence or hierarchy is implied",
        required_features=("peer_categories", "taxonomy_preserved"),
        anti_patterns=("forced_sequence", "invented_hierarchy", "dominant_center"),
    ),
    "support_convergence_3_6": ExpressionSpec(
        "support_convergence_3_6", "多项支撑汇聚", (3, 6), "supporting_proposition", "supporting_proposition",
        relation_pattern="supporting_convergence", reading_requirement="convergent",
        balance_requirement="multiple supports remain distinct and converge on one bounded judgment",
        required_features=("multiple_supports", "single_conclusion"),
        anti_patterns=("parallel_conclusions", "forced_sequence", "invented_causality"),
    ),
    "mapping_2_6": ExpressionSpec(
        "mapping_2_6", "二至六组对应关系", (2, 6), "paired_dimension", "parallel_proposition",
        relation_pattern="mapped_pairs", reading_requirement="mapped",
        balance_requirement="preserve each source-supported pair without turning mapping into comparison",
        required_features=("source_target_pairs", "pair_integrity"),
        anti_patterns=("forced_comparison", "invented_ranking", "forced_sequence"),
    ),
    "directed_dependency_2_6": ExpressionSpec(
        "directed_dependency_2_6", "二至六节点有向承接", (2, 6), "relation_node", "relation_node",
        relation_pattern="directed_dependency", reading_requirement="directed_dependency",
        balance_requirement="preserve explicit direction and dependency without inventing chronology, hierarchy, or peer equivalence",
        required_features=("directed_dependency_edge",),
        anti_patterns=("unordered_peer_groups", "invented_time_order", "invented_hierarchy"),
    ),
    "neutral_structure_1_7": ExpressionSpec(
        "neutral_structure_1_7", "一至七节点中性结构", (1, 7), "mixed", "neutral",
        relation_pattern="unresolved_relation", reading_requirement="neutral",
        balance_requirement="preserve authored grouping and explicit edges while leaving unresolved relation type open for visual review",
        required_features=("relation_review_required",),
        anti_patterns=("invented_peer_equivalence", "invented_sequence", "invented_hierarchy"),
    ),
    "flow_3_5": ExpressionSpec(
        "flow_3_5", "三至六步链路", (3, 6), "verb_object", heading_policy="action",
        relation_pattern="directed_sequence", reading_requirement="directed",
        balance_requirement="each action has a legible place in the progression",
        required_features=("ordered_progression",), anti_patterns=("unordered_peer_groups",),
    ),
    "operation_loop": ExpressionSpec(
        "operation_loop", "运营闭环", (3, 6), "verb_object", heading_policy="action",
        require_return_relation=True, relation_pattern="directed_cycle", reading_requirement="cyclic",
        balance_requirement="each action participates in a closed operating relation",
        required_features=("ordered_progression", "feedback_edge_required"),
        anti_patterns=("linear_only_flow", "missing_feedback_edge"),
    ),
    "architecture_layers": ExpressionSpec(
        "architecture_layers", "分层架构", (3, 6), "parallel_noun", "layer_component",
        relation_pattern="layered_dependency", reading_requirement="layered",
        balance_requirement="layers state their carrying, interface, or dependency relation",
        required_features=("layer_dependency",), anti_patterns=("stacked_text_only",),
    ),
    "pyramid_argument": ExpressionSpec(
        "pyramid_argument", "金字塔归纳", (3, 3), "supporting_proposition", "supporting_proposition",
        relation_pattern="supporting_convergence", reading_requirement="convergent",
        balance_requirement="three supports converge on one judgment",
        required_features=("three_supports", "convergence_required"),
        anti_patterns=("parallel_conclusions", "missing_convergence"),
    ),
    "comparison_2col": ExpressionSpec(
        "comparison_2col", "双列对照", (2, 2), "paired_dimension", "paired_dimension",
        relation_pattern="paired_comparison", reading_requirement="paired",
        balance_requirement="both objects use matched comparison dimensions",
        required_features=("two_objects", "matched_dimensions"), anti_patterns=("unmatched_columns",),
    ),
    "grouped_2": ExpressionSpec(
        "grouped_2", "双组信息结构", (2, 2), "grouped_proposition", "grouped_proposition",
        relation_pattern="grouped_elaboration", reading_requirement="grouped",
        balance_requirement="one group establishes the subject and the other advances its directly supported mechanism or boundary",
        required_features=("two_distinct_groups", "explicit_group_relation"),
        anti_patterns=("forced_comparison", "invented_sequence"),
    ),
    "matrix_2x2": ExpressionSpec(
        "matrix_2x2", "四象限分群", (4, 4), "parallel_segment", "classification_segment",
        relation_pattern="two_axis_classification", reading_requirement="two_axis",
        balance_requirement="each group states why it belongs under both dimensions",
        required_features=("two_classification_dimensions", "four_classified_positions"),
        anti_patterns=("unclassified_four_cards",),
    ),
    "causal_chain": ExpressionSpec(
        "causal_chain", "因果链", (3, 4), "causal_predicate", "causal_predicate",
        relation_pattern="directed_cause_to_effect", reading_requirement="directed",
        balance_requirement="each cause is attached to its consequence",
        required_features=("directed_causal_chain",), anti_patterns=("unordered_peer_groups", "self_loop"),
    ),
    "actions_3": ExpressionSpec(
        "actions_3", "三项举措", (3, 3), "verb_object", heading_policy="action",
        relation_pattern="coordinated_actions", reading_requirement="action_oriented",
        balance_requirement="three actions jointly point to one outcome",
        required_features=("three_verb_object_actions", "shared_outcome"), anti_patterns=("noun_only_list",),
    ),
}
VALID_EXPRESSION_FORMS = frozenset(EXPRESSION_SPECS)
ACTION_HEADING_POLICY = "action"
_ACTION_RE = re.compile(
    r"推进|建设|完善|强化|提升|形成|构建|汇聚|组织|治理|授权|流通|运营|反馈|迭代|驱动|支撑|带动|促进|实现"
    r"|执行|下发|记录|计量|确认|对账|结算|汇总|开展"
)
_LAYER_RE = re.compile(r"层|底座|体系架构")
_FRAMEWORK_RE = re.compile(r"框架|四模块|四方面|四项|构成|组成")
_PARALLEL_RE = re.compile(r"并列|分类|同类|类别|类型|三类|四类|五类|六类")
_COMPARISON_RE = re.compile(r"现状|目标|当前|未来|方案|对照|比较")
_MATRIX_RE = re.compile(r"象限|维度|优先级|分群|高低|二维")
_CAUSAL_RE = re.compile(r"驱动|制约|影响|导致|结果|原因|因果")
_LOOP_RE = re.compile(r"闭环|反馈|回流|迭代|循环")
_ACTION_TOPIC_RE = re.compile(r"举措|任务|行动|重点|安排|保障")
_FLOW_RE = re.compile(r"流程|链路|路径|阶段|环节|依次|先后|逐步|进入|转入|输出|流转")
_DEPENDENCY_RE = re.compile(r"依托|承接|提供基础|形成基础|作为基础|支撑后续|前提")


def validate_expression_form(value: str) -> str:
    form = str(value or "").strip()
    if form and form not in VALID_EXPRESSION_FORMS:
        raise ValueError(f"invalid onscreen expression form: {form}")
    return form


def expression_constraints(form: str) -> dict[str, object]:
    key = validate_expression_form(form)
    if not key:
        raise ValueError("expression form is required")
    spec = EXPRESSION_SPECS[key]
    return {
        "form": spec.key,
        "heading_policy": spec.heading_policy,
        "node_range": list(spec.module_range),
        "relation_pattern": spec.relation_pattern,
        "reading_requirement": spec.reading_requirement,
        "balance_requirement": spec.balance_requirement,
        "required_features": list(spec.required_features),
        "anti_patterns": list(spec.anti_patterns),
    }


def expression_requires_action_headings(form: str) -> bool:
    key = validate_expression_form(form)
    return bool(key and EXPRESSION_SPECS[key].heading_policy == ACTION_HEADING_POLICY)


def expression_constraints_sha256(constraints: Mapping[str, object]) -> str:
    stable = json.dumps(constraints, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(stable.encode("utf-8")).hexdigest()


def _relationship_confidence(
    relationships: Sequence[Mapping[str, object]],
) -> float:
    values: list[float] = []
    names: set[str] = set()
    for item in relationships:
        if not isinstance(item, Mapping):
            continue
        relation = str(item.get("relation") or "").strip()
        if relation:
            names.add(relation)
        raw = item.get("confidence")
        if isinstance(raw, (int, float)):
            values.append(max(0.0, min(float(raw), 1.0)))
            continue
        label = str(raw or "").strip().lower()
        values.append({"high": 0.90, "medium": 0.75, "low": 0.60}.get(label, 0.84))
    confidence = min(values) if values else 0.84
    if "directed_dependency" in names:
        confidence = min(confidence, 0.82)
    if names & {"directed_relation", "semantic_association"}:
        confidence = min(confidence, 0.68)
    return round(confidence, 2)


def _topology_expression(
    topology: Mapping[str, object],
    *,
    module_count: int,
    surface_text: str,
) -> tuple[str, tuple[str, ...]] | None:
    primary = str(topology.get("primary_topology") or "unknown")
    evidence = (f"semantic_topology:{primary}",)
    if primary == "feedback_loop" and 3 <= module_count <= 6:
        return "operation_loop", evidence
    if primary == "causal_chain" and 3 <= module_count <= 4:
        return "causal_chain", evidence
    if primary == "sequence" and 3 <= module_count <= 6:
        return "flow_3_5", evidence
    if primary == "layered_structure" and 3 <= module_count <= 6:
        return "architecture_layers", evidence
    if primary == "support_convergence" and 3 <= module_count <= 6:
        return "support_convergence_3_6", evidence
    if primary == "dependency_chain" and 2 <= module_count <= 6:
        return "directed_dependency_2_6", evidence
    if primary == "mapping" and 2 <= module_count <= 6:
        return "mapping_2_6", evidence
    if primary == "comparison":
        if module_count == 2:
            return "comparison_2col", evidence
        if 2 <= module_count <= 6:
            return "mapping_2_6", evidence
    if primary == "matrix" and module_count == 4:
        return "matrix_2x2", evidence
    if primary == "containment":
        if module_count == 4:
            return "framework_4", evidence
        if module_count == 2:
            return "grouped_2", evidence
        if 1 <= module_count <= 7:
            return "neutral_structure_1_7", evidence
    if primary == "peer_set":
        if module_count == 4 and _FRAMEWORK_RE.search(surface_text):
            return "framework_4", evidence
        if module_count == 3 and re.search(r"三要素|三项重点|原则|价值", surface_text):
            return "key_points_3", evidence
        if 3 <= module_count <= 6:
            return "parallel_classification_3_6", evidence
    if primary == "unknown" and 1 <= module_count <= 7:
        return "neutral_structure_1_7", evidence
    return None


def resolve_onscreen_expression(
    page: Any,
    *,
    page_mission: str = "",
    business_relationships: Sequence[Mapping[str, object]] = (),
    actions: Sequence[str] = (),
    topic_category: str = "",
    semantic_topology: Mapping[str, object] | None = None,
) -> ExpressionDecision:
    """Resolve a layout-neutral reading contract from verified page semantics."""

    explicit = validate_expression_form(str(getattr(page, "onscreen_expression_form", "") or ""))
    candidates = _score_candidates(page, page_mission, actions, topic_category)
    if explicit:
        return ExpressionDecision(explicit, "explicit", 1.0, ("author_override",), candidates)

    modules = tuple(str(item).strip() for item in getattr(page, "top_level_module_titles", ()) if str(item).strip())
    surface_text = "\n".join((page_mission, topic_category, "\n".join(modules), "\n".join(actions)))

    if isinstance(semantic_topology, Mapping):
        resolved = _topology_expression(
            semantic_topology,
            module_count=len(modules),
            surface_text=surface_text,
        )
        if resolved is not None:
            form, evidence = resolved
            return ExpressionDecision(
                form,
                "verified_topology",
                round(float(semantic_topology.get("confidence") or 0.0), 2),
                evidence,
                candidates,
            )

    # Compatibility path for legacy direct callers that do not yet supply a
    # verified topology.  The official Stage 02 handoff uses the branch above.
    semantic = resolve_relation_expression(relationships=business_relationships, module_count=len(modules))
    if semantic is not None:
        form, evidence = semantic
        spec = EXPRESSION_SPECS.get(form)
        if spec is not None and spec.module_range[0] <= len(modules) <= spec.module_range[1]:
            return ExpressionDecision(
                form,
                "relation",
                _relationship_confidence(business_relationships),
                evidence,
                candidates,
            )

    form, score = candidates[0]
    if score < 0.60:
        if getattr(page, "page_type", "content") == "content" and 1 <= len(modules) <= 7:
            return ExpressionDecision(
                "neutral_structure_1_7",
                "fallback",
                round(score, 2),
                ("relation_unresolved", "insufficient_surface_signals"),
                candidates,
            )
        return ExpressionDecision(
            "key_points_3",
            "fallback",
            round(score, 2),
            ("no_authoritative_relation", "insufficient_surface_signals"),
            candidates,
        )
    return ExpressionDecision(form, "scored", round(score, 2), ("surface_signals",), candidates)


def _score_candidates(
    page: Any, page_mission: str, actions: Sequence[str], topic_category: str
) -> tuple[tuple[str, float], ...]:
    modules = tuple(str(item).strip() for item in getattr(page, "top_level_module_titles", ()) if str(item).strip())
    text = "\n".join((page_mission, topic_category, "\n".join(modules), "\n".join(actions)))
    module_count = len(modules)
    action_count = sum(bool(_ACTION_RE.search(value)) for value in (*modules, *actions))
    scores = {form: 0.0 for form in VALID_EXPRESSION_FORMS}

    # Cardinality establishes eligibility only; it cannot prove peer semantics.
    if module_count == 4:
        scores["framework_4"] += 0.12
        scores["matrix_2x2"] += 0.08
    if module_count == 3:
        scores["key_points_3"] += 0.12
        scores["pyramid_argument"] += 0.08
        scores["actions_3"] += 0.08

    if module_count == 4 and _FRAMEWORK_RE.search(text):
        scores["framework_4"] += 0.68
    if 3 <= module_count <= 6 and _PARALLEL_RE.search(text):
        scores["parallel_classification_3_6"] += 0.78
    # Action-bearing labels alone do not prove a process.  A flow also needs a
    # progression/path signal; this prevents words such as "形成" in a four-
    # module framework from stealing the page into flow_3_5.
    if 3 <= module_count <= 6 and action_count >= 2 and _FLOW_RE.search(text):
        scores["flow_3_5"] += 0.78
    if 2 <= module_count <= 6 and _DEPENDENCY_RE.search(text):
        scores["directed_dependency_2_6"] += 0.64
    if _LOOP_RE.search(text) and 3 <= module_count <= 6:
        scores["operation_loop"] += 0.76
    if _LAYER_RE.search(text) and 3 <= module_count <= 6:
        scores["architecture_layers"] += 0.74
    if _COMPARISON_RE.search(text) and module_count == 2:
        scores["comparison_2col"] += 0.74
    if _MATRIX_RE.search(text) and module_count == 4:
        scores["matrix_2x2"] += 0.76
    if _CAUSAL_RE.search(text) and 3 <= module_count <= 4:
        scores["causal_chain"] += 0.76
    if _ACTION_TOPIC_RE.search(text) and module_count == 3 and action_count >= 2:
        scores["actions_3"] += 0.72
    if getattr(page, "onscreen_judgment", "") and module_count == 3:
        scores["pyramid_argument"] += 0.22
    if module_count == 3 and re.search(r"总分|论证|归纳", text):
        scores["pyramid_argument"] += 0.58
    if module_count == 3 and re.search(r"原则|价值|重点", text):
        scores["key_points_3"] += 0.52
    if module_count:
        for form, spec in EXPRESSION_SPECS.items():
            if not spec.module_range[0] <= module_count <= spec.module_range[1]:
                scores[form] = 0.0
    return tuple(sorted(((form, min(round(score, 2), 0.89)) for form, score in scores.items()), key=lambda item: (-item[1], item[0])))


def audit_expression_balance(page: Any, decision: ExpressionDecision) -> list[ExpressionAuditFinding]:
    modules = tuple(str(item).strip() for item in getattr(page, "top_level_module_titles", ()) if str(item).strip())
    spec = EXPRESSION_SPECS[decision.form]
    findings: list[ExpressionAuditFinding] = []
    if not spec.module_range[0] <= len(modules) <= spec.module_range[1]:
        fitting = sorted(other.key for other in EXPRESSION_SPECS.values() if other.module_range[0] <= len(modules) <= other.module_range[1])
        action = "Revise the visible structure so its peer-module count matches the selected expression form."
        if fitting:
            action += f" Forms that already fit {len(modules)} module(s): {', '.join(fitting)}."
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_MODULE_COUNT_MISMATCH",
            f"{spec.label} requires {spec.module_range[0]}–{spec.module_range[1]} top-level modules.",
            action, (f"actual={len(modules)}", *(f"fits:{form}" for form in fitting)),
        ))
    lengths = [len(re.sub(r"\s+", "", item)) for item in modules]
    if len(lengths) >= 2 and max(lengths) - min(lengths) > 8:
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_HEADING_LENGTH_IMBALANCED",
            "Peer headings have visibly uneven lengths.",
            "Keep the long business proposition in a child detail and make peer headings comparable in reading weight.",
            modules, "warning",
        ))
    if expression_requires_action_headings(decision.form):
        inactive = tuple(item for item in modules if not _ACTION_RE.search(item))
        if inactive:
            findings.append(ExpressionAuditFinding(
                "ONSCREEN_FLOW_ACTION_MISSING",
                "This expression form requires action-bearing peer headings.",
                "Rewrite peer headings with concise business actions and retain evidence in child details.",
                inactive,
            ))
    if decision.form == "operation_loop" and not any(_LOOP_RE.search(item) for item in modules):
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_LOOP_RETURN_MISSING",
            "An operation loop requires one visible feedback or return node.",
            "Add a concise feedback, return, or iteration node that closes the operating relation.",
            modules,
        ))
    if decision.form == "comparison_2col" and len(modules) == 2 and abs(lengths[0] - lengths[1]) > 4:
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_COMPARISON_DIMENSION_MISMATCH",
            "The two comparison dimensions have uneven reading weight.",
            "Use matched dimension labels on both sides of the comparison.",
            modules,
        ))
    return findings

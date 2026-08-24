"""Classify professional on-screen expression forms without choosing a layout."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence

from cyberppt.semantic_relation_contract import expression_form_hint, relation_names


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
    "parallel_classification": ExpressionSpec(
        "parallel_classification", "并列分类", (2, 6), "parallel_noun", "classification_segment",
        relation_pattern="peer_classification", reading_requirement="parallel",
        balance_requirement="peer categories remain comparable and no order or hierarchy is implied",
        required_features=("peer_categories",),
        anti_patterns=("forced_sequence", "invented_hierarchy", "dominant_center"),
    ),
    "mapping_2_6": ExpressionSpec(
        "mapping_2_6", "对应映射", (2, 6), "mapped_proposition", "parallel_proposition",
        relation_pattern="paired_mapping", reading_requirement="mapped",
        balance_requirement="each response remains attached to its source problem or counterpart",
        required_features=("mapped_pairs",),
        anti_patterns=("forced_comparison", "forced_sequence", "invented_causality"),
    ),
    # Keep the historical key for compatibility; the production contract now
    # supports the real six-step Stage 02 flow used by current decks.
    "flow_3_5": ExpressionSpec(
        "flow_3_5", "三至六步链路", (3, 6), "verb_object", heading_policy="action",
        relation_pattern="directed_sequence", reading_requirement="directed",
        balance_requirement="each action has a legible place in the progression",
        required_features=("ordered_progression",), anti_patterns=("unordered_peer_groups",),
    ),
    "operation_loop": ExpressionSpec(
        "operation_loop", "运营闭环", (3, 5), "verb_object", heading_policy="action",
        require_return_relation=True, relation_pattern="directed_cycle", reading_requirement="cyclic",
        balance_requirement="each action participates in a closed operating relation",
        required_features=("ordered_progression", "feedback_edge_required"),
        anti_patterns=("linear_only_flow", "missing_feedback_edge"),
    ),
    "architecture_layers": ExpressionSpec(
        "architecture_layers", "分层架构", (3, 4), "parallel_noun", "layer_component",
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
        relation_pattern="paired_correspondence", reading_requirement="paired",
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
_COMPARISON_RE = re.compile(r"现状|目标|当前|未来|主体|方案|对照|比较|差异")
_CLASSIFICATION_RE = re.compile(r"分类|并列|类型|类别|分为|分成")
_MAPPING_RE = re.compile(r"对应|回应|响应|映射|匹配|适配")
_MATRIX_RE = re.compile(r"象限|维度|优先级|分群|高低|二维")
_CAUSAL_RE = re.compile(r"驱动|制约|影响|导致|结果|原因")
_LOOP_RE = re.compile(r"闭环|反馈|回流|迭代|循环")
_ACTION_TOPIC_RE = re.compile(r"举措|任务|行动|重点|安排|保障")


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


def resolve_onscreen_expression(
    page: Any,
    *,
    page_mission: str = "",
    business_relationships: Sequence[Mapping[str, object]] = (),
    actions: Sequence[str] = (),
    topic_category: str = "",
) -> ExpressionDecision:
    """Return a reading-structure decision while keeping visual topology separate."""

    explicit = validate_expression_form(str(getattr(page, "onscreen_expression_form", "") or ""))
    candidates = _score_candidates(page, page_mission, actions, topic_category)
    if explicit:
        return ExpressionDecision(explicit, "explicit", 1.0, ("author_override",), candidates)

    modules = tuple(str(item).strip() for item in getattr(page, "top_level_module_titles", ()) if str(item).strip())
    relation_context = "\n".join((
        page_mission,
        topic_category,
        "\n".join(modules),
        str(getattr(page, "onscreen_text", "") or ""),
    ))
    hint = expression_form_hint(
        business_relationships,
        module_count=len(modules),
        comparison_requested=bool(_COMPARISON_RE.search(relation_context)),
    )
    names = set(relation_names(business_relationships))
    if hint:
        return _relation_decision(hint, names, candidates)

    form, score = candidates[0]
    if score < 0.60:
        return ExpressionDecision(
            "key_points_3",
            "fallback",
            round(score, 2),
            ("no_expression_form_implied_by_semantic_relation", "insufficient_surface_signals"),
            candidates,
        )
    return ExpressionDecision(form, "scored", round(score, 2), ("surface_signals",), candidates)


def _relation_decision(
    form: str, relations: set[str], candidates: tuple[tuple[str, float], ...]
) -> ExpressionDecision:
    return ExpressionDecision(
        form,
        "relation",
        0.92,
        tuple(f"relation:{value}" for value in sorted(relations)),
        candidates,
    )


def _score_candidates(
    page: Any, page_mission: str, actions: Sequence[str], topic_category: str
) -> tuple[tuple[str, float], ...]:
    modules = tuple(str(item).strip() for item in getattr(page, "top_level_module_titles", ()) if str(item).strip())
    text = "\n".join((page_mission, topic_category, "\n".join(modules), "\n".join(actions)))
    module_count = len(modules)
    action_count = sum(bool(_ACTION_RE.search(value)) for value in (*modules, *actions))
    scores = {form: 0.0 for form in VALID_EXPRESSION_FORMS}
    if module_count == 4:
        scores["framework_4"] += 0.82
        scores["matrix_2x2"] += 0.35
    if module_count == 3:
        scores["key_points_3"] += 0.58
        scores["pyramid_argument"] += 0.34
        scores["actions_3"] += 0.26
    if 2 <= module_count <= 6 and _CLASSIFICATION_RE.search(text):
        scores["parallel_classification"] += 0.78
    if 2 <= module_count <= 6 and _MAPPING_RE.search(text):
        scores["mapping_2_6"] += 0.68
    if 3 <= module_count <= 6 and action_count >= 2:
        scores["flow_3_5"] += 0.75
    if 3 <= module_count <= 4 and action_count >= 2:
        scores["causal_chain"] += 0.30
    if _LOOP_RE.search(text):
        scores["operation_loop"] += 0.70
    if _LAYER_RE.search(text):
        scores["architecture_layers"] += 0.70
    if _COMPARISON_RE.search(text):
        scores["comparison_2col"] += 0.70
    if _MATRIX_RE.search(text):
        scores["matrix_2x2"] += 0.70
    if _CAUSAL_RE.search(text):
        scores["causal_chain"] += 0.70
    if _ACTION_TOPIC_RE.search(text) and module_count == 3 and action_count >= 2:
        scores["actions_3"] += 0.70
    if getattr(page, "onscreen_judgment", "") and module_count == 3:
        scores["pyramid_argument"] += 0.35
    if module_count == 3 and re.search(r"总分|论证|归纳", text):
        scores["pyramid_argument"] += 0.55
    if module_count == 3 and re.search(r"原则|价值|重点", text):
        scores["key_points_3"] += 0.48
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
        fitting = sorted(
            other.key
            for other in EXPRESSION_SPECS.values()
            if other.module_range[0] <= len(modules) <= other.module_range[1]
        )
        action = "Revise the visible structure so its peer-module count matches the selected expression form."
        if fitting:
            action += f" Forms that already fit {len(modules)} module(s): {', '.join(fitting)}."
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_MODULE_COUNT_MISMATCH",
            f"{spec.label} requires {spec.module_range[0]}–{spec.module_range[1]} top-level modules.",
            action,
            (f"actual={len(modules)}", *(f"fits:{form}" for form in fitting)),
        ))
    lengths = [len(re.sub(r"\s+", "", item)) for item in modules]
    if len(lengths) >= 2 and max(lengths) - min(lengths) > 8:
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_HEADING_LENGTH_IMBALANCED",
            "Peer headings have visibly uneven lengths.",
            "Keep the long business proposition in a child detail and make peer headings comparable in reading weight.",
            modules,
            "warning",
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

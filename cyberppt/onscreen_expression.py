"""Classify professional on-screen expression forms without choosing a layout."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ExpressionSpec:
    key: str
    label: str
    module_range: tuple[int, int]
    heading_grammar: str
    require_action: bool = False
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
        "framework_4", "四模块框架", (4, 4), "parallel_noun",
        relation_pattern="peer_modules", reading_requirement="parallel",
        balance_requirement="four peers have comparable reading weight",
        required_features=("four_peer_nodes", "peer_balance"),
        anti_patterns=("forced_sequence", "dominant_center"),
    ),
    "key_points_3": ExpressionSpec(
        "key_points_3", "三要素结构", (3, 3), "parallel_phrase",
        relation_pattern="peer_key_points", reading_requirement="parallel",
        balance_requirement="three points jointly support one page judgment",
        required_features=("three_peer_points", "shared_judgment"),
        anti_patterns=("invented_causality", "invented_time_order"),
    ),
    "flow_3_5": ExpressionSpec(
        "flow_3_5", "三至五步链路", (3, 5), "verb_object", require_action=True,
        relation_pattern="directed_sequence", reading_requirement="directed",
        balance_requirement="each action has a legible place in the progression",
        required_features=("ordered_progression",),
        anti_patterns=("unordered_peer_groups",),
    ),
    "operation_loop": ExpressionSpec(
        "operation_loop", "运营闭环", (3, 5), "verb_object", require_action=True,
        require_return_relation=True, relation_pattern="directed_cycle", reading_requirement="cyclic",
        balance_requirement="each action participates in a closed operating relation",
        required_features=("ordered_progression", "feedback_edge_required"),
        anti_patterns=("linear_only_flow", "missing_feedback_edge"),
    ),
    "architecture_layers": ExpressionSpec(
        "architecture_layers", "分层架构", (3, 4), "parallel_noun",
        relation_pattern="layered_dependency", reading_requirement="layered",
        balance_requirement="layers state their carrying, interface, or dependency relation",
        required_features=("layer_dependency",),
        anti_patterns=("stacked_text_only",),
    ),
    "pyramid_argument": ExpressionSpec(
        "pyramid_argument", "金字塔归纳", (3, 3), "supporting_proposition",
        relation_pattern="supporting_convergence", reading_requirement="convergent",
        balance_requirement="three supports converge on one judgment",
        required_features=("three_supports", "convergence_required"),
        anti_patterns=("parallel_conclusions", "missing_convergence"),
    ),
    "comparison_2col": ExpressionSpec(
        "comparison_2col", "双列对照", (2, 2), "paired_dimension",
        relation_pattern="paired_correspondence", reading_requirement="paired",
        balance_requirement="both objects use matched comparison dimensions",
        required_features=("two_objects", "matched_dimensions"),
        anti_patterns=("unmatched_columns",),
    ),
    "matrix_2x2": ExpressionSpec(
        "matrix_2x2", "四象限分群", (4, 4), "parallel_segment",
        relation_pattern="two_axis_classification", reading_requirement="two_axis",
        balance_requirement="each group states why it belongs under both dimensions",
        required_features=("two_classification_dimensions", "four_classified_positions"),
        anti_patterns=("unclassified_four_cards",),
    ),
    "causal_chain": ExpressionSpec(
        "causal_chain", "因果链", (3, 4), "causal_predicate", require_action=True,
        relation_pattern="directed_cause_to_effect", reading_requirement="directed",
        balance_requirement="each cause is attached to its consequence",
        required_features=("directed_causal_chain",),
        anti_patterns=("unordered_peer_groups", "self_loop"),
    ),
    "actions_3": ExpressionSpec(
        "actions_3", "三项举措", (3, 3), "verb_object", require_action=True,
        relation_pattern="coordinated_actions", reading_requirement="action_oriented",
        balance_requirement="three actions jointly point to one outcome",
        required_features=("three_verb_object_actions", "shared_outcome"),
        anti_patterns=("noun_only_list",),
    ),
}
VALID_EXPRESSION_FORMS = frozenset(EXPRESSION_SPECS)

_RELATION_FORMS = {
    "composed_of": "framework_4",
    "contains": "framework_4",
    "supports": "framework_4",
    "sequence_before": "flow_3_5",
    "sequence_after": "flow_3_5",
    "layered_as": "architecture_layers",
    "part_of": "architecture_layers",
    "causes": "causal_chain",
    "corresponds_to": "comparison_2col",
}
_RETURN_RELATIONS = {"feedback", "feeds_back", "returns_to", "iterates", "loops_to"}
_ACTION_RE = re.compile(r"推进|建设|完善|强化|提升|形成|构建|汇聚|治理|授权|流通|运营|反馈|迭代|驱动|支撑|带动|促进|实现")
_LAYER_RE = re.compile(r"层|底座|体系架构")
_COMPARISON_RE = re.compile(r"现状|目标|当前|未来|主体|方案|对照|比较")
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
    """Return a fresh, layout-neutral default profile for an expression form."""

    key = validate_expression_form(form)
    if not key:
        raise ValueError("expression form is required")
    spec = EXPRESSION_SPECS[key]
    return {
        "form": spec.key,
        "node_range": list(spec.module_range),
        "relation_pattern": spec.relation_pattern,
        "reading_requirement": spec.reading_requirement,
        "balance_requirement": spec.balance_requirement,
        "required_features": list(spec.required_features),
        "anti_patterns": list(spec.anti_patterns),
    }


def expression_constraints_sha256(constraints: Mapping[str, object]) -> str:
    """Hash a normalized expression profile for cross-artifact traceability."""

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
    """Return a reviewable semantic expression decision for a content page."""

    explicit = validate_expression_form(str(getattr(page, "onscreen_expression_form", "") or ""))
    candidates = _score_candidates(page, page_mission, actions, topic_category)
    if explicit:
        return ExpressionDecision(explicit, "explicit", 1.0, ("author_override",), candidates)

    relation_names = {
        str(item.get("relation") or "").strip()
        for item in business_relationships
        if isinstance(item, Mapping)
    }
    if relation_names & _RETURN_RELATIONS:
        return _relation_decision("operation_loop", relation_names, candidates)
    for relation, form in _RELATION_FORMS.items():
        if relation in relation_names:
            return _relation_decision(form, relation_names, candidates)

    form, score = candidates[0]
    if score < 0.60:
        return ExpressionDecision(
            "key_points_3",
            "fallback",
            round(score, 2),
            ("no_authoritative_relation", "insufficient_surface_signals"),
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
    if 3 <= module_count <= 5 and action_count >= 2:
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
    return tuple(sorted(((form, min(round(score, 2), 0.89)) for form, score in scores.items()), key=lambda item: (-item[1], item[0])))


def audit_expression_balance(page: Any, decision: ExpressionDecision) -> list[ExpressionAuditFinding]:
    """Return form-specific text-balance diagnostics without choosing a layout."""

    modules = tuple(str(item).strip() for item in getattr(page, "top_level_module_titles", ()) if str(item).strip())
    spec = EXPRESSION_SPECS[decision.form]
    findings: list[ExpressionAuditFinding] = []
    if not spec.module_range[0] <= len(modules) <= spec.module_range[1]:
        findings.append(ExpressionAuditFinding(
            "ONSCREEN_MODULE_COUNT_MISMATCH",
            f"{spec.label} requires {spec.module_range[0]}–{spec.module_range[1]} top-level modules.",
            "Revise the visible structure so its peer-module count matches the selected expression form.",
            (f"actual={len(modules)}",),
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
    if spec.require_action:
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

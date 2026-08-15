"""Source-native argument model produced by semantic understanding.

The semantic stage is responsible for understanding the source.  Later stages
may select, compress, and order this model for an audience, but they may not
invent a new thesis or silently flatten a source heading into a page label.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


SCHEMA = "cyberppt.semantic_argument_model.v1"
MODEL_JSON = "semantic-argument-model.json"
MODEL_BLOCK_MARKER = "semantic-argument-model"
ROOT_NODE_IDS = frozenset({"document", "document_thesis"})

RELATIONS = frozenset(
    {
        "supports",
        "depends_on",
        "transforms_to",
        "realized_by",
        "implemented_by",
        "maps_to",
        "operationalizes",
        "precedes",
        "constrains",
        "contains",
        "composed_of",
        "contrasts_with",
        "requires_confirmation_of",
    }
)
RELATION_WEIGHT_EFFECTS = frozenset({"none"})
ARGUMENT_WEIGHTS = frozenset({"core", "supporting", "detail", "constraint"})
ARGUMENT_DUTIES = frozenset(
    {"premise", "driver", "consequence", "gap", "response", "support", "detail", "boundary", "metadata"}
)
ARGUMENT_ROLES = frozenset(
    {
        "thesis",
        "foundation",
        "definition",
        "positioning",
        "construction",
        "capability",
        "advantage",
        "architecture",
        "operation",
        "cooperation",
        "implementation",
        "recommendation",
        "boundary",
        "gap",
        "evidence",
    }
)
STATUS_VALUES = frozenset(
    {
        "existing",
        "in_progress",
        "planned",
        "proposal",
        "to_confirm",
        "recommendation",
        "mixed",
        "unknown",
    }
)
INTERPRETATION_CONTRACT_MODES = frozenset({"legacy", "strict"})
CLAIM_ORIGINS = frozenset(
    {"source_explicit", "source_implied", "editorial_hypothesis"}
)
SOURCE_TRUTH_CLAIM_ROLES = frozenset(
    {"fact", "change", "problem", "judgment", "recommendation", "boundary", "unresolved"}
)
ARGUMENT_DUTIES = frozenset(
    {"premise", "driver", "consequence", "gap", "response", "support", "detail", "boundary", "metadata"}
)
INFERENCE_ORIGINS = frozenset({"source_implied", "editorial_hypothesis"})
CONCEPT_RESOLUTIONS = frozenset(
    {"same_meaning", "different_dimension", "homonym", "requires_review"}
)
_LEGACY_EVIDENCE_RE = re.compile(r"S\d+")
_SOURCE_UNIT_RE = re.compile(r"SU-[A-Z0-9-]+")


def _looks_corrupted_text(value: object) -> bool:
    """Detect text lost during a non-UTF-8 model handoff.

    A semantic model is source text, not an opaque token payload.  When a
    model is copied through a lossy console or file writer, Chinese strings
    often become runs of ``?`` (or the Unicode replacement character).  Such
    a model must fail in Stage 00; otherwise later stages can see valid JSON
    and silently consume an empty/meaningless thesis.
    """

    if not isinstance(value, str):
        return False
    text = value.strip()
    if not text:
        return False
    if "\ufffd" in text:
        return True
    meaningful = re.sub(r"[?\s]", "", text)
    if not meaningful and "?" in text:
        return True
    question_count = text.count("?")
    return len(text) >= 8 and question_count / max(len(text), 1) >= 0.6


def _walk_corrupted_text(value: object, path: str = "model") -> list[str]:
    paths: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            paths.extend(_walk_corrupted_text(item, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            paths.extend(_walk_corrupted_text(item, f"{path}[{index}]"))
    elif _looks_corrupted_text(value):
        paths.append(path)
    return paths


def _evidence_refs(value: object) -> tuple[list[str], bool]:
    """Return normalized evidence IDs and whether the field is well formed."""

    if not isinstance(value, list) or not value:
        return [], False
    refs = [_text(item) for item in value]
    valid = all(
        ref
        and (
            _LEGACY_EVIDENCE_RE.fullmatch(ref)
            or _SOURCE_UNIT_RE.fullmatch(ref)
        )
        for ref in refs
    )
    return refs, valid


def empty_model() -> dict[str, Any]:
    """Return the required shape used in the semantic authoring template."""

    return {
        "schema": SCHEMA,
        "version": 1,
        "interpretation_contract_mode": "strict",
        "source_truth_projection_mode": "required",
        "document_semantics": {
            "document_role": "",
            "subject_of_report": "",
            "primary_thesis": "",
            "decision_boundary": "",
            "author_purpose": "",
            "argument_method": [],
            "supporting_basis": [],
            "business_objects": [],
            "scope": "",
            "decision_intent": "",
        },
        "document_thesis": {
            "statement": "",
            "argument_role": "thesis",
            "argument_weight": "core",
            "status": "mixed",
            "evidence_refs": [],
            "actor_refs": [],
            "claim_origin": "source_explicit",
        },
        "section_nodes": [],
        "subsection_nodes": [],
        "argument_relations": [],
        "mece_rules": {
            "partition_basis": "",
            "exhaustive_scope": "",
            "overlap_policy": "",
            "groups": [],
            "review_notes": [],
        },
        "inference_register": [],
        "concept_occurrence_graph": {
            "concepts": [],
            "relations": [],
            "review_notes": [],
        },
        "semantic_content_unit_coverage_mode": "required",
        "source_coverage": {
            "assignments": [],
            "intentional_omissions": [],
            "review_notes": [],
        },
        "source_gaps": [],
    }


def render_model_block(model: dict[str, Any] | None = None) -> str:
    value = model if model is not None else empty_model()
    return (
        f"<!-- {MODEL_BLOCK_MARKER} -->\n"
        "```json\n"
        + json.dumps(value, ensure_ascii=False, indent=2)
        + "\n```"
    )


def render_review_markdown(model: dict[str, Any]) -> str:
    """Render the human semantic review from the canonical machine model.

    Lightweight Stage 01 authors the semantic model once.  This renderer keeps
    the required review document available without asking a model to restate
    the same interpretation in a second independently-authored artifact.
    """

    semantics = model.get("document_semantics")
    semantics = semantics if isinstance(semantics, dict) else {}
    thesis = model.get("document_thesis")
    thesis = thesis if isinstance(thesis, dict) else {}
    sections = [item for item in _list(model.get("section_nodes")) if isinstance(item, dict)]
    nodes = sections + [
        item for item in _list(model.get("subsection_nodes")) if isinstance(item, dict)
    ]

    def value(field: str, fallback: str) -> str:
        return _text(semantics.get(field)) or fallback

    def node_thesis(node: dict[str, Any]) -> str:
        return _text(node.get("section_thesis") or node.get("thesis"))

    def bullet_lines(items: list[str], fallback: str) -> list[str]:
        cleaned = [item for item in items if item]
        return [f"- {item}" for item in cleaned] or [f"- {fallback}"]

    business_objects = [
        _text(item) for item in _list(semantics.get("business_objects")) if _text(item)
    ]
    structure_lines = [
        f"{index}. {_text(node.get('source_heading'))}：{node_thesis(node)}"
        for index, node in enumerate(sections, start=1)
        if _text(node.get("source_heading")) and node_thesis(node)
    ]
    foundation_gap = [
        f"{_text(node.get('source_heading'))}：{node_thesis(node)}"
        for node in nodes
        if _text(node.get("argument_role")) in {"foundation", "gap"}
        and node_thesis(node)
    ]
    goal_support = [
        f"{_text(node.get('source_heading'))}：{node_thesis(node)}"
        for node in nodes
        if _text(node.get("argument_weight")) in {"core", "supporting"}
        and node_thesis(node)
    ]
    relations = [
        f"{_text(item.get('from'))} --{_text(item.get('relation'))}--> "
        f"{_text(item.get('to'))}：{_text(item.get('explanation'))}"
        for item in _list(model.get("argument_relations"))
        if isinstance(item, dict)
    ]
    state_rows = [
        "| {heading} | {actors} | {status} | {weight} |".format(
            heading=_text(node.get("source_heading")) or _text(node.get("id")),
            actors="、".join(_text(item) for item in _list(node.get("actor_refs")) if _text(item)) or "未单列主体",
            status=_text(node.get("status")) or "unknown",
            weight=_text(node.get("argument_weight")) or "detail",
        )
        for node in nodes
    ]
    concept_rows = []
    graph = model.get("concept_occurrence_graph")
    if isinstance(graph, dict):
        for item in _list(graph.get("concepts")):
            if not isinstance(item, dict):
                continue
            concept_rows.append(
                "| {term} | {resolution} | {refs} |".format(
                    term=_text(item.get("concept") or item.get("term") or item.get("name")),
                    resolution=_text(item.get("resolution")) or "按源材料语境区分",
                    refs="、".join(
                        _text(ref)
                        for ref in _list(item.get("occurrence_source_unit_ids") or item.get("source_unit_refs"))
                        if _text(ref)
                    ) or "见语义节点证据",
                )
            )
    if not concept_rows:
        concept_rows = [
            f"| {item} | 按源材料中的业务对象含义使用 | 见相关语义节点 evidence_refs |"
            for item in business_objects
        ]
    gaps = [
        _text(item.get("statement") if isinstance(item, dict) else item)
        for item in _list(model.get("source_gaps"))
    ]
    forbidden = [
        _text(item.get("handling") or item.get("statement"))
        for item in _list(model.get("inference_register"))
        if isinstance(item, dict)
    ]

    primary_thesis = _text(thesis.get("statement")) or value(
        "primary_thesis", "全文主论点见机器可读语义模型。"
    )
    author_purpose = value("author_purpose", "保持源材料意图并供后续阶段直接消费。")
    decision_intent = value("decision_intent", "由受众理解材料并确认后续动作。")
    decision_boundary = value("decision_boundary", "不得将未确认事项写成既成事实。")

    lines = [
        "# 全文语义理解",
        "",
        "> 本文由 semantic-argument-model.json 确定性渲染；机器模型是唯一语义作者产物。",
        "",
        "## 全文业务主语",
        "",
        value("subject_of_report", primary_thesis) + "；全文主论点为：" + primary_thesis,
        "",
        "## 核心业务对象",
        "",
        "以下对象必须保持各自业务含义、主体责任和来源边界：",
        *bullet_lines(business_objects, "业务对象及其边界以语义节点和来源证据为准。"),
        "",
        "## 空间、时间与服务范围",
        "",
        value("scope", "范围以来源单元、状态和边界字段的共同约束为准。")
        + "；不得超出来源声明的空间、时间、服务及成熟度范围。",
        "",
        "## 材料意图与决策动作",
        "",
        f"- 作者目的：{author_purpose}",
        f"- 受众动作：{decision_intent}",
        f"- 成熟度边界：{decision_boundary}",
        "",
        "## 原文结构与论证顺序",
        "",
        *bullet_lines(structure_lines, "按原文一级章节和语义节点顺序组织论证。"),
        "",
        "## 现有基础与能力缺口",
        "",
        *bullet_lines(foundation_gap, "基础与缺口分别由对应语义节点及其证据界定。"),
        "",
        "## 业务目标与支撑手段",
        "",
        *bullet_lines(goal_support, primary_thesis),
        "",
        "## 核心概念语义表",
        "",
        "| 原文简称 | 语义处理 | 来源锚点 |",
        "| --- | --- | --- |",
        *concept_rows,
        "",
        "## 跨章节证据链",
        "",
        *bullet_lines(relations, "全文主论点及章节判断均绑定稳定 SU-* 来源单元。"),
        "",
        "## 状态、主体与边界",
        "",
        "| 语义节点 | 主体 | 状态 | 权重 |",
        "| --- | --- | --- | --- |",
        *state_rows,
        "",
        "## 待核事项与禁止推断",
        "",
        *bullet_lines(
            gaps + forbidden,
            decision_boundary + "；不得据此推导未经来源确认的承诺、因果、结果或责任。",
        ),
        "",
        "## 源材料论点模型（机器可读）",
        "",
        render_model_block(model),
        "",
    ]
    return "\n".join(lines)


def extract_model(text: str) -> dict[str, Any] | None:
    """Extract the marked JSON block from semantic-understanding.md."""

    marker = re.search(
        rf"(?ms)<!--\s*{re.escape(MODEL_BLOCK_MARKER)}\s*-->\s*```(?:json)?\s*(?P<body>.*?)\s*```",
        text,
    )
    candidates = [marker.group("body")] if marker else []
    if not candidates:
        candidates = re.findall(r"(?ms)^```json\s*(?P<body>.*?)\s*```", text)
    for body in candidates:
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("schema") == SCHEMA:
            return payload
    return None


def load_model(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("semantic argument model root must be an object")
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"semantic argument model schema must be {SCHEMA}")
    return payload


def _text(value: object) -> str:
    return str(value or "").strip()


def _heading_key(value: object) -> str:
    return re.sub(r"\s+", "", _text(value))


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _ids(items: object) -> set[str]:
    return {_text(item.get("id")) for item in _list(items) if isinstance(item, dict) and _text(item.get("id"))}


def _issue(code: str, message: str, *, node_id: str = "") -> dict[str, str]:
    result = {"code": code, "message": message}
    if node_id:
        result["node_id"] = node_id
    return result


def _strict_contract_issues(
    model: dict[str, Any],
    *,
    thesis: dict[str, Any] | None,
    sections: list[Any],
    subsections: list[Any],
    relations: list[Any],
    required_heading_records: list[dict[str, Any]] | None,
    source_unit_ids: set[str] | None,
) -> list[dict[str, str]]:
    """Validate the source-native interpretation layer used by new projects."""

    issues: list[dict[str, str]] = []
    known_source_units = source_unit_ids

    def source_unit_ref_issues(
        refs_value: object,
        *,
        owner: str,
        node_id: str = "",
        required: bool = True,
    ) -> list[str]:
        refs, well_formed = _evidence_refs(refs_value)
        if required and not well_formed:
            issues.append(
                _issue(
                    "SEMANTIC_STABLE_EVIDENCE_INVALID",
                    f"{owner} 必须声明非空且格式正确的 evidence/source refs。",
                    node_id=node_id,
                )
            )
            return refs
        legacy = sorted({ref for ref in refs if _LEGACY_EVIDENCE_RE.fullmatch(ref)})
        if legacy:
            issues.append(
                _issue(
                    "SEMANTIC_STABLE_EVIDENCE_REQUIRED",
                    f"严格语义合同必须使用稳定 source_unit_id，不得继续使用临时 Sxxxx：{'、'.join(legacy)}",
                    node_id=node_id,
                )
            )
        unit_refs = [ref for ref in refs if _SOURCE_UNIT_RE.fullmatch(ref)]
        if known_source_units is not None:
            unknown = sorted(set(unit_refs) - known_source_units)
            if unknown:
                issues.append(
                    _issue(
                        "SEMANTIC_SOURCE_UNIT_UNKNOWN",
                        "语义模型引用了源材料地图中不存在的 source_unit_id：" + "、".join(unknown),
                        node_id=node_id,
                    )
                )
        return refs

    inference_items = model.get("inference_register")
    if not isinstance(inference_items, list):
        issues.append(
            _issue(
                "SEMANTIC_INFERENCE_REGISTER_INVALID",
                "严格语义合同必须声明 inference_register 数组；没有推断时使用空数组。",
            )
        )
        inference_items = []
    inference_ids: set[str] = set()
    known_argument_ids = {
        _text(item.get("id"))
        for item in sections + subsections
        if isinstance(item, dict) and _text(item.get("id"))
    }
    for item in inference_items:
        if not isinstance(item, dict):
            issues.append(_issue("SEMANTIC_INFERENCE_INVALID", "inference_register 的每项必须是对象。"))
            continue
        inference_id = _text(item.get("id"))
        if not inference_id or inference_id in inference_ids:
            issues.append(_issue("SEMANTIC_INFERENCE_ID_INVALID", "推断记录 id 必须非空且唯一。", node_id=inference_id))
        if inference_id:
            inference_ids.add(inference_id)
        for field in ("statement", "handling"):
            if not _text(item.get(field)):
                issues.append(_issue("SEMANTIC_INFERENCE_INCOMPLETE", f"推断记录缺少 {field}。", node_id=inference_id))
        origin = _text(item.get("claim_origin"))
        if origin not in INFERENCE_ORIGINS:
            issues.append(
                _issue(
                    "SEMANTIC_INFERENCE_ORIGIN_INVALID",
                    "推断记录 claim_origin 必须是 source_implied 或 editorial_hypothesis。",
                    node_id=inference_id,
                )
            )
        source_unit_ref_issues(
            item.get("basis_refs"), owner="推断记录 basis_refs", node_id=inference_id
        )
        affected = [_text(value) for value in _list(item.get("affected_node_ids")) if _text(value)]
        if not affected:
            issues.append(_issue("SEMANTIC_INFERENCE_TARGET_MISSING", "推断记录必须声明 affected_node_ids。", node_id=inference_id))
        unknown_targets = sorted(set(affected) - known_argument_ids - {"document_thesis"})
        if unknown_targets:
            issues.append(
                _issue(
                    "SEMANTIC_INFERENCE_TARGET_UNKNOWN",
                    "推断记录引用了未知论点节点：" + "、".join(unknown_targets),
                    node_id=inference_id,
                )
            )

    # Every heading in the original tree must be interpreted directly by a
    # section/subsection node (matched on exact title + level).  This replaces
    # a separate heading_semantic_cards mirror: that structure required every
    # node to restate the same title/level/role/weight/claim_origin a second
    # time and then be checked for drift against the node itself, which added
    # a large amount of authoring and validation surface without covering any
    # heading a section/subsection node check does not already cover.
    found_headings = {
        (_heading_key(node.get("source_heading")), node.get("level"))
        for node in sections + subsections
        if isinstance(node, dict) and _text(node.get("source_heading"))
    }
    missing_headings = sorted(
        {
            _text(item.get("title"))
            for item in (required_heading_records or [])
            if isinstance(item, dict)
            and (_heading_key(item.get("title")), item.get("level")) not in found_headings
        }
    )
    if missing_headings:
        issues.append(
            _issue(
                "SEMANTIC_SOURCE_HEADINGS_UNINTERPRETED",
                "原始标题树中仍有标题未被任何语义节点解读：" + "、".join(missing_headings),
            )
        )

    claim_items: list[tuple[str, dict[str, Any]]] = []
    if isinstance(thesis, dict):
        claim_items.append(("document_thesis", thesis))
    claim_items.extend(
        (_text(item.get("id")), item)
        for item in sections + subsections
        if isinstance(item, dict)
    )
    for node_id, item in claim_items:
        origin = _text(item.get("claim_origin"))
        if origin not in CLAIM_ORIGINS:
            issues.append(
                _issue(
                    "SEMANTIC_CLAIM_ORIGIN_INVALID",
                    "严格语义合同中的每项主张必须标注 source_explicit、source_implied 或 editorial_hypothesis。",
                    node_id=node_id,
                )
            )
        if origin in INFERENCE_ORIGINS:
            inference_id = _text(item.get("inference_id"))
            if not inference_id or inference_id not in inference_ids:
                issues.append(_issue("SEMANTIC_CLAIM_INFERENCE_UNREGISTERED", "非显式主张必须绑定 inference_register 中的记录。", node_id=node_id))
        if origin == "editorial_hypothesis":
            issues.append(
                _issue(
                    "SEMANTIC_EDITORIAL_HYPOTHESIS_PROMOTED",
                    "编辑性假设只能登记为 Director 候选，不得进入源材料主论点、章节论点或标题语义卡。",
                    node_id=node_id,
                )
            )
        source_unit_ref_issues(item.get("evidence_refs"), owner="语义主张 evidence_refs", node_id=node_id)

    for relation in relations:
        if not isinstance(relation, dict):
            continue
        relation_id = _text(relation.get("id"))
        origin = _text(relation.get("claim_origin"))
        if origin not in CLAIM_ORIGINS:
            issues.append(_issue("SEMANTIC_CLAIM_ORIGIN_INVALID", "严格合同中的论证关系必须声明 claim_origin。", node_id=relation_id))
        if origin in INFERENCE_ORIGINS:
            inference_id = _text(relation.get("inference_id"))
            if not inference_id or inference_id not in inference_ids:
                issues.append(_issue("SEMANTIC_CLAIM_INFERENCE_UNREGISTERED", "非显式论证关系必须绑定 inference_register。", node_id=relation_id))
        if origin == "editorial_hypothesis":
            issues.append(_issue("SEMANTIC_EDITORIAL_HYPOTHESIS_PROMOTED", "编辑性关系不得写入源材料 argument_relations。", node_id=relation_id))
        source_unit_ref_issues(relation.get("evidence_refs"), owner="论证关系 evidence_refs", node_id=relation_id)

    context = model.get("document_semantics")
    if isinstance(context, dict):
        for field in ("argument_method", "supporting_basis"):
            value = context.get(field)
            if not isinstance(value, list) or not value:
                issues.append(_issue("SEMANTIC_DOCUMENT_ARGUMENT_TRACE_MISSING", f"严格语义合同必须声明非空 {field} 数组。"))
                continue
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    issues.append(_issue("SEMANTIC_DOCUMENT_ARGUMENT_TRACE_INVALID", f"{field}[{index}] 必须是对象。"))
                    continue
                if not _text(item.get("statement")):
                    issues.append(_issue("SEMANTIC_DOCUMENT_ARGUMENT_TRACE_INVALID", f"{field}[{index}] 缺少 statement。"))
                source_unit_ref_issues(
                    item.get("source_refs"),
                    owner=f"{field}[{index}].source_refs",
                )

    # concept_occurrence_graph is an optional, advisory aid for catching
    # repeated terms with different meanings. It is validated for internal
    # consistency when the author chooses to fill it in, but its absence is
    # not a blocking issue: unlike evidence/status/claim_origin, a missed
    # homonym does not put a fabricated or mis-stated claim into the model.
    graph = model.get("concept_occurrence_graph")
    if isinstance(graph, dict) and (graph.get("concepts") or graph.get("relations")):
        concepts = graph.get("concepts")
        graph_relations = graph.get("relations")
        if not isinstance(concepts, list) or not isinstance(graph_relations, list):
            issues.append(_issue("SEMANTIC_CONCEPT_GRAPH_INVALID", "概念出现图声明时必须包含 concepts 和 relations 数组。"))
            concepts = concepts if isinstance(concepts, list) else []
            graph_relations = graph_relations if isinstance(graph_relations, list) else []
        concept_ids: set[str] = set()
        for concept in concepts:
            if not isinstance(concept, dict):
                issues.append(_issue("SEMANTIC_CONCEPT_INVALID", "concepts 的每项必须是对象。"))
                continue
            concept_id = _text(concept.get("concept_id"))
            if not concept_id or concept_id in concept_ids:
                issues.append(_issue("SEMANTIC_CONCEPT_ID_INVALID", "concept_id 必须非空且唯一。", node_id=concept_id))
            if concept_id:
                concept_ids.add(concept_id)
            for field in ("canonical_label", "rationale"):
                if not _text(concept.get(field)):
                    issues.append(_issue("SEMANTIC_CONCEPT_INCOMPLETE", f"重复概念记录缺少 {field}。", node_id=concept_id))
            if _text(concept.get("resolution")) not in CONCEPT_RESOLUTIONS:
                issues.append(_issue("SEMANTIC_CONCEPT_RESOLUTION_INVALID", "resolution 必须说明同义、不同维度、同名异义或待复核。", node_id=concept_id))
            occurrences = [_text(value) for value in _list(concept.get("occurrence_unit_ids")) if _text(value)]
            if len(occurrences) < 2 or len(occurrences) != len(set(occurrences)):
                issues.append(_issue("SEMANTIC_CONCEPT_OCCURRENCES_INVALID", "重复概念必须绑定至少两个不重复的 source_unit_id。", node_id=concept_id))
            source_unit_ref_issues(occurrences, owner="重复概念 occurrence_unit_ids", node_id=concept_id)
        for relation in graph_relations:
            if not isinstance(relation, dict):
                issues.append(_issue("SEMANTIC_CONCEPT_RELATION_INVALID", "概念关系必须是对象。"))
                continue
            relation_id = _text(relation.get("id"))
            left = _text(relation.get("from_concept_id"))
            right = _text(relation.get("to_concept_id"))
            if not relation_id or not _text(relation.get("relation")):
                issues.append(_issue("SEMANTIC_CONCEPT_RELATION_INCOMPLETE", "概念关系缺少 id 或 relation。", node_id=relation_id))
            if left not in concept_ids or right not in concept_ids or left == right:
                issues.append(_issue("SEMANTIC_CONCEPT_RELATION_TARGET_INVALID", "概念关系必须连接两个不同且已声明的概念。", node_id=relation_id))
            source_unit_ref_issues(relation.get("evidence_refs"), owner="概念关系 evidence_refs", node_id=relation_id)
    return issues


def validate_model(
    model: dict[str, Any] | None,
    *,
    required_headings: list[str] | None = None,
    required_heading_records: list[dict[str, Any]] | None = None,
    source_record_ids: set[str] | None = None,
    source_unit_ids: set[str] | None = None,
    required_content_unit_ids: set[str] | None = None,
    require_document_context: bool = False,
) -> list[dict[str, str]]:
    """Validate semantic structure without deciding page count or page layout."""

    issues: list[dict[str, str]] = []
    if not isinstance(model, dict):
        return [_issue("SEMANTIC_ARGUMENT_MODEL_MISSING", "语义理解必须产出机器可读的源材料论点模型。")]
    corrupted_paths = _walk_corrupted_text(model)
    if corrupted_paths:
        preview = "、".join(corrupted_paths[:8])
        if len(corrupted_paths) > 8:
            preview += "……"
        issues.append(
            _issue(
                "SEMANTIC_ARGUMENT_MODEL_TEXT_CORRUPTED",
                "源材料论点模型包含疑似编码损坏的文本（问号/替换字符），必须在语义理解阶段以 UTF-8 重新生成；问题路径：" + preview,
            )
        )
    if model.get("schema") != SCHEMA:
        issues.append(_issue("SEMANTIC_ARGUMENT_MODEL_SCHEMA_INVALID", f"论点模型 schema 必须是 {SCHEMA}。"))
    interpretation_mode = _text(model.get("interpretation_contract_mode")) or "legacy"
    if interpretation_mode not in INTERPRETATION_CONTRACT_MODES:
        issues.append(
            _issue(
                "SEMANTIC_INTERPRETATION_MODE_INVALID",
                "interpretation_contract_mode 必须是 legacy 或 strict。",
            )
        )
    context = model.get("document_semantics")
    if require_document_context:
        if not isinstance(context, dict):
            issues.append(_issue("SEMANTIC_DOCUMENT_CONTEXT_MISSING", "正式语义理解必须固化 document_semantics，后续阶段只能复制消费。"))
        else:
            for field in ("document_role", "subject_of_report", "primary_thesis", "decision_boundary", "scope", "decision_intent"):
                if not _text(context.get(field)):
                    issues.append(_issue("SEMANTIC_DOCUMENT_CONTEXT_INCOMPLETE", f"document_semantics 缺少 {field}。"))
            if not isinstance(context.get("business_objects"), list) or not context.get("business_objects"):
                issues.append(_issue("SEMANTIC_DOCUMENT_CONTEXT_OBJECTS_MISSING", "document_semantics.business_objects 必须是非空业务对象数组。"))
    thesis = model.get("document_thesis")
    if not isinstance(thesis, dict):
        issues.append(_issue("SEMANTIC_DOCUMENT_THESIS_MISSING", "论点模型必须声明 document_thesis。"))
    else:
        for field in ("statement", "argument_role", "argument_weight", "status"):
            if not _text(thesis.get(field)):
                issues.append(_issue("SEMANTIC_DOCUMENT_THESIS_INCOMPLETE", f"document_thesis 缺少 {field}。"))
        if _text(thesis.get("argument_role")) != "thesis":
            issues.append(_issue("SEMANTIC_DOCUMENT_THESIS_ROLE_INVALID", "document_thesis.argument_role 必须为 thesis。"))
        if _text(thesis.get("argument_weight")) != "core":
            issues.append(_issue("SEMANTIC_DOCUMENT_THESIS_WEIGHT_INVALID", "document_thesis.argument_weight 必须为 core。"))
        _, evidence_ok = _evidence_refs(thesis.get("evidence_refs"))
        if not evidence_ok:
            issues.append(_issue("SEMANTIC_DOCUMENT_THESIS_EVIDENCE_MISSING", "全文主论点必须有可回查的 evidence_refs。"))
        if not isinstance(thesis.get("actor_refs"), list) or any(not _text(item) for item in thesis.get("actor_refs", [])):
            issues.append(_issue("SEMANTIC_DOCUMENT_THESIS_ACTORS_INVALID", "document_thesis.actor_refs 必须是非空主体 ID/名称数组。"))
        if isinstance(context, dict) and _text(context.get("primary_thesis")) and _text(context.get("primary_thesis")) != _text(thesis.get("statement")):
            issues.append(_issue("SEMANTIC_DOCUMENT_CONTEXT_THESIS_DRIFTED", "document_semantics.primary_thesis 必须与 document_thesis.statement 完全一致。"))

    sections = _list(model.get("section_nodes"))
    subsections = _list(model.get("subsection_nodes"))
    if not sections:
        issues.append(_issue("SEMANTIC_SECTION_NODES_MISSING", "论点模型必须保留源材料一级章节节点。"))
    section_ids = _ids(sections)
    subsection_ids = _ids(subsections)
    if len(section_ids) != len([item for item in sections if isinstance(item, dict)]):
        issues.append(_issue("SEMANTIC_SECTION_NODE_IDS_INVALID", "一级章节节点 id 必须非空且唯一。"))
    if len(subsection_ids) != len([item for item in subsections if isinstance(item, dict)]):
        issues.append(_issue("SEMANTIC_SUBSECTION_NODE_IDS_INVALID", "二级章节节点 id 必须非空且唯一。"))

    expected_heading_set = {_heading_key(item) for item in (required_headings or []) if _heading_key(item)}
    found_heading_set: set[str] = set()
    for node in sections:
        if not isinstance(node, dict):
            issues.append(_issue("SEMANTIC_SECTION_NODE_INVALID", "section_nodes 的每一项必须是对象。"))
            continue
        node_id = _text(node.get("id"))
        for field in ("id", "source_heading", "section_thesis", "argument_role", "argument_weight", "status", "primary_consumer"):
            if not _text(node.get(field)):
                issues.append(_issue("SEMANTIC_SECTION_NODE_INCOMPLETE", f"一级节点缺少 {field}。", node_id=node_id))
        if _text(node.get("argument_role")) not in ARGUMENT_ROLES:
            issues.append(_issue("SEMANTIC_ARGUMENT_ROLE_INVALID", "一级节点 argument_role 不在受控词表中。", node_id=node_id))
        if _text(node.get("argument_weight")) not in ARGUMENT_WEIGHTS:
            issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHT_INVALID", "一级节点 argument_weight 必须是 core、supporting、detail 或 constraint。", node_id=node_id))
        if _text(node.get("status")) not in STATUS_VALUES:
            issues.append(_issue("SEMANTIC_STATUS_INVALID", "一级节点 status 不在受控词表中。", node_id=node_id))
        _, evidence_ok = _evidence_refs(node.get("evidence_refs"))
        if not evidence_ok:
            issues.append(_issue("SEMANTIC_SECTION_EVIDENCE_MISSING", "每个一级节点必须声明 evidence_refs。", node_id=node_id))
        if not isinstance(node.get("actor_refs"), list) or any(not _text(item) for item in node.get("actor_refs", [])):
            issues.append(_issue("SEMANTIC_SECTION_ACTORS_INVALID", "一级节点 actor_refs 必须是非空主体 ID/名称数组。", node_id=node_id))
        heading = _text(node.get("source_heading"))
        if heading:
            found_heading_set.add(_heading_key(heading))
        children = _list(node.get("subsection_ids"))
        if any(_text(item) not in subsection_ids for item in children):
            issues.append(_issue("SEMANTIC_SUBSECTION_REFERENCE_UNKNOWN", "一级节点引用了不存在的 subsection id。", node_id=node_id))

    if expected_heading_set:
        missing = sorted(expected_heading_set - found_heading_set)
        if missing:
            issues.append(_issue("SEMANTIC_SOURCE_HEADINGS_NOT_PRESERVED", "论点模型未完整保留源材料一级标题：" + "；".join(missing)))

    known_parent_ids = section_ids | subsection_ids
    for node in subsections:
        if not isinstance(node, dict):
            issues.append(_issue("SEMANTIC_SUBSECTION_NODE_INVALID", "subsection_nodes 的每一项必须是对象。"))
            continue
        node_id = _text(node.get("id"))
        for field in ("id", "parent_id", "source_heading", "section_thesis", "argument_role", "argument_weight", "status", "primary_consumer"):
            if not _text(node.get(field)):
                issues.append(_issue("SEMANTIC_SUBSECTION_NODE_INCOMPLETE", f"二级节点缺少 {field}。", node_id=node_id))
        parent_id = _text(node.get("parent_id"))
        if parent_id not in known_parent_ids or parent_id == node_id:
            issues.append(_issue("SEMANTIC_SUBSECTION_PARENT_UNKNOWN", "二级节点 parent_id 不指向已声明的一级/上级节点。", node_id=node_id))
        if _text(node.get("argument_role")) not in ARGUMENT_ROLES:
            issues.append(_issue("SEMANTIC_ARGUMENT_ROLE_INVALID", "二级节点 argument_role 不在受控词表中。", node_id=node_id))
        if _text(node.get("argument_weight")) not in ARGUMENT_WEIGHTS:
            issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHT_INVALID", "二级节点 argument_weight 必须是 core、supporting、detail 或 constraint。", node_id=node_id))
        if _text(node.get("status")) not in STATUS_VALUES:
            issues.append(_issue("SEMANTIC_STATUS_INVALID", "二级节点 status 不在受控词表中。", node_id=node_id))
        _, evidence_ok = _evidence_refs(node.get("evidence_refs"))
        if not evidence_ok:
            issues.append(_issue("SEMANTIC_SUBSECTION_EVIDENCE_MISSING", "每个二级节点必须声明 evidence_refs。", node_id=node_id))
        if not isinstance(node.get("actor_refs"), list) or any(not _text(item) for item in node.get("actor_refs", [])):
            issues.append(_issue("SEMANTIC_SUBSECTION_ACTORS_INVALID", "二级节点 actor_refs 必须是非空主体 ID/名称数组。", node_id=node_id))

    node_ids = known_parent_ids
    levels = {
        _text(item.get("id")): item.get("level")
        for item in sections + subsections
        if isinstance(item, dict) and _text(item.get("id"))
    }
    for node in sections:
        if not isinstance(node, dict):
            continue
        node_id = _text(node.get("id"))
        if node.get("level") != 1:
            issues.append(_issue("SEMANTIC_NODE_LEVEL_INVALID", "一级章节节点 level 必须为 1。", node_id=node_id))
    for node in subsections:
        if not isinstance(node, dict):
            continue
        node_id = _text(node.get("id"))
        parent_id = _text(node.get("parent_id"))
        parent_level = levels.get(parent_id)
        if not isinstance(node.get("level"), int) or not isinstance(parent_level, int) or node.get("level") != parent_level + 1:
            issues.append(_issue("SEMANTIC_NODE_LEVEL_INVALID", "论点节点 level 必须比 parent_id 的 level 高一级；不得把三级能力/优势条目伪装成二级标题。", node_id=node_id))

    relations = _list(model.get("argument_relations"))
    if not relations:
        issues.append(_issue("SEMANTIC_ARGUMENT_RELATIONS_MISSING", "论点模型必须声明章节和论点之间的论证关系。"))
    for relation in relations:
        if not isinstance(relation, dict):
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_INVALID", "argument_relations 的每一项必须是对象。"))
            continue
        relation_id = _text(relation.get("id"))
        source = _text(relation.get("from"))
        target = _text(relation.get("to"))
        kind = _text(relation.get("relation"))
        weight_effect = _text(relation.get("weight_effect"))
        if source not in node_ids or target not in node_ids:
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_NODE_UNKNOWN", "论证关系 from/to 必须指向已声明节点。", node_id=relation_id))
        if kind not in RELATIONS:
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_TYPE_INVALID", "论证关系 relation 不在受控词表中。", node_id=relation_id))
        if weight_effect not in RELATION_WEIGHT_EFFECTS:
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_WEIGHT_EFFECT_INVALID", "论证关系必须声明 weight_effect=none；supports、maps_to 等关系只描述连接，不得改变任一节点的核心/支撑权重。", node_id=relation_id))
        _, evidence_ok = _evidence_refs(relation.get("evidence_refs"))
        if not evidence_ok:
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_EVIDENCE_MISSING", "论证关系必须有 evidence_refs，不能由提纲阶段自行补出因果。", node_id=relation_id))
        if not _text(relation.get("explanation")):
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_EXPLANATION_MISSING", "论证关系必须说明源材料支持的连接方式。", node_id=relation_id))
        if source == target:
            issues.append(_issue("SEMANTIC_ARGUMENT_RELATION_SELF_LOOP", "论证关系不得连接节点自身。", node_id=relation_id))

    mece = model.get("mece_rules")
    if not isinstance(mece, dict):
        issues.append(_issue("SEMANTIC_MECE_RULES_MISSING", "语义理解必须声明 MECE 分区规则。"))
    else:
        for field in ("partition_basis", "exhaustive_scope", "overlap_policy"):
            if not _text(mece.get(field)):
                issues.append(_issue("SEMANTIC_MECE_RULES_INCOMPLETE", f"mece_rules 缺少 {field}。"))
        groups = _list(mece.get("groups"))
        if not groups:
            issues.append(_issue("SEMANTIC_MECE_GROUPS_MISSING", "mece_rules.groups 至少要声明一个可检查的同级分区。"))
        seen_group_nodes: set[str] = set()
        for group in groups:
            if not isinstance(group, dict):
                issues.append(_issue("SEMANTIC_MECE_GROUP_INVALID", "mece_rules.groups 的每项必须是对象。"))
                continue
            parent_id = _text(group.get("parent_id"))
            group_nodes = [_text(item) for item in _list(group.get("node_ids")) if _text(item)]
            for field in ("parent_id", "partition_basis", "exhaustive_scope", "overlap_policy"):
                if not _text(group.get(field)):
                    issues.append(_issue("SEMANTIC_MECE_GROUP_INCOMPLETE", f"MECE 分区缺少 {field}。", node_id=parent_id))
            if parent_id and parent_id not in known_parent_ids and parent_id not in ROOT_NODE_IDS:
                issues.append(_issue("SEMANTIC_MECE_PARENT_UNKNOWN", "MECE 分区 parent_id 不指向已声明节点。", node_id=parent_id))
            if len(group_nodes) < 2 or len(group_nodes) != len(set(group_nodes)):
                issues.append(_issue("SEMANTIC_MECE_NODE_SET_INVALID", "MECE 分区必须包含至少两个不重复节点。", node_id=parent_id))
            unknown_group_nodes = sorted(set(group_nodes) - known_parent_ids)
            if unknown_group_nodes:
                issues.append(_issue("SEMANTIC_MECE_NODE_UNKNOWN", "MECE 分区引用了未知节点：" + "、".join(unknown_group_nodes), node_id=parent_id))
            duplicate_group_nodes = sorted(set(group_nodes) & seen_group_nodes)
            if duplicate_group_nodes:
                issues.append(_issue("SEMANTIC_MECE_NODE_REUSED", "同一节点被多个同级 MECE 分区重复归类：" + "、".join(duplicate_group_nodes), node_id=parent_id))
            seen_group_nodes.update(group_nodes)
        if not isinstance(mece.get("review_notes"), list):
            issues.append(_issue("SEMANTIC_MECE_REVIEW_NOTES_INVALID", "mece_rules.review_notes 必须是数组。"))

    gaps = _list(model.get("source_gaps"))
    gap_ids = _ids(gaps)
    for gap in gaps:
        if not isinstance(gap, dict):
            issues.append(_issue("SEMANTIC_SOURCE_GAP_INVALID", "source_gaps 的每一项必须是对象。"))
            continue
        gap_id = _text(gap.get("id"))
        for field in ("id", "description", "impact", "handling"):
            if not _text(gap.get(field)):
                issues.append(_issue("SEMANTIC_SOURCE_GAP_INCOMPLETE", f"source_gap 缺少 {field}。", node_id=gap_id))
    for node in sections + subsections:
        if not isinstance(node, dict):
            continue
        unknown_gap_ids = {
            _text(item)
            for item in _list(node.get("source_gap_ids"))
            if _text(item) not in gap_ids
        }
        if unknown_gap_ids:
            issues.append(_issue("SEMANTIC_SOURCE_GAP_REFERENCE_UNKNOWN", "论点节点引用了不存在的 source_gap：" + "、".join(sorted(unknown_gap_ids)), node_id=_text(node.get("id"))))

    if source_record_ids is not None:
        refs: list[str] = []
        if isinstance(thesis, dict):
            refs.extend(str(item) for item in _list(thesis.get("evidence_refs")))
        for node in sections + subsections:
            if isinstance(node, dict):
                refs.extend(str(item) for item in _list(node.get("evidence_refs")))
        for relation in relations:
            if isinstance(relation, dict):
                refs.extend(str(item) for item in _list(relation.get("evidence_refs")))
        unknown = sorted(
            {
                ref
                for ref in refs
                if _LEGACY_EVIDENCE_RE.fullmatch(ref)
                and ref not in source_record_ids
            }
        )
        if unknown:
            issues.append(_issue("SEMANTIC_ARGUMENT_EVIDENCE_UNKNOWN", "论点模型引用了 Source Truth 中不存在的证据：" + "、".join(unknown)))
    if interpretation_mode == "strict":
        issues.extend(
            _strict_contract_issues(
                model,
                thesis=thesis if isinstance(thesis, dict) else None,
                sections=sections,
                subsections=subsections,
                relations=relations,
                required_heading_records=required_heading_records,
                source_unit_ids=source_unit_ids,
            )
        )
        if required_content_unit_ids is not None:
            if _text(model.get("semantic_content_unit_coverage_mode")) != "required":
                issues.append(
                    _issue(
                        "SEMANTIC_CONTENT_UNIT_COVERAGE_MODE_REQUIRED",
                        "严格语义理解默认启用原子事项覆盖；semantic_content_unit_coverage_mode 必须为 required。",
                    )
                )
            coverage = model.get("source_coverage")
            if not isinstance(coverage, dict):
                issues.append(
                    _issue(
                        "SEMANTIC_SOURCE_COVERAGE_MISSING",
                        "严格语义理解必须逐一处置全部正文源单元：归入语义节点，或以具体理由声明有意忽略。",
                    )
                )
            else:
                assigned_refs: set[str] = set()
                omitted_refs: set[str] = set()
                node_lookup = node_index(model)
                protected_refs = {
                    ref
                    for node in node_lookup.values()
                    if _text(node.get("argument_weight")) in {"core", "constraint"}
                    or (
                        _text(node.get("argument_weight")) == "supporting"
                        and len({_text(item) for item in _list(node.get("evidence_refs")) if _text(item)}) >= 6
                    )
                    for ref in _list(node.get("evidence_refs"))
                    if _text(ref) in required_content_unit_ids
                }
                for assignment in _list(coverage.get("assignments")):
                    if not isinstance(assignment, dict):
                        issues.append(_issue("SEMANTIC_SOURCE_ASSIGNMENT_INVALID", "source_coverage.assignments 的每项必须是对象。"))
                        continue
                    refs = {_text(item) for item in _list(assignment.get("source_unit_refs")) if _text(item)}
                    target_ids = {_text(item) for item in _list(assignment.get("semantic_node_ids")) if _text(item)}
                    if not refs or not target_ids or not _text(assignment.get("summary")):
                        issues.append(_issue("SEMANTIC_SOURCE_ASSIGNMENT_INCOMPLETE", "每项源信息归属必须包含 source_unit_refs、semantic_node_ids 和具体 summary。"))
                        continue
                    unknown_targets = sorted(target_ids - set(node_lookup))
                    if unknown_targets:
                        issues.append(_issue("SEMANTIC_SOURCE_ASSIGNMENT_NODE_UNKNOWN", "源信息归属指向不存在的语义节点：" + "、".join(unknown_targets)))
                    for target_id in target_ids & set(node_lookup):
                        node_evidence = {_text(item) for item in _list(node_lookup[target_id].get("evidence_refs")) if _text(item)}
                        missing_evidence = sorted(refs - node_evidence)
                        if missing_evidence:
                            issues.append(_issue("SEMANTIC_SOURCE_ASSIGNMENT_EVIDENCE_DISCONNECTED", "已归属源单元必须同时进入目标语义节点 evidence_refs：" + "、".join(missing_evidence), node_id=target_id))
                    atomic_items = _list(assignment.get("atomic_items"))
                    if not atomic_items:
                        issues.append(
                            _issue(
                                "SEMANTIC_ATOMIC_ITEMS_MISSING",
                                "源单元归属不能只写 summary；必须拆出保留业务对象、动作、条件、状态和数字的 atomic_items。",
                            )
                        )
                    atomic_covered_refs: set[str] = set()
                    # Atomic items carry the source-faithful proposition and
                    # its local argument duty. A node can contain premise,
                    # demand, gap and response together, so this duty cannot
                    # be derived from the node's coarse argument role.
                    for atomic_item in atomic_items:
                        if not isinstance(atomic_item, dict):
                            issues.append(_issue("SEMANTIC_ATOMIC_ITEM_INVALID", "assignment.atomic_items 的每项必须是对象。"))
                            continue
                        item_id = _text(atomic_item.get("item_id"))
                        statement = _text(atomic_item.get("statement"))
                        item_refs = {_text(item) for item in _list(atomic_item.get("source_unit_refs")) if _text(item)}
                        anchors = [_text(item) for item in _list(atomic_item.get("coverage_anchors")) if _text(item)]
                        status = _text(atomic_item.get("status"))
                        duty = _text(atomic_item.get("argument_duty"))
                        if not item_id or not statement or not item_refs or not status:
                            issues.append(_issue("SEMANTIC_ATOMIC_ITEM_INCOMPLETE", "每个 atomic_item 必须包含 item_id、statement、source_unit_refs 和 status。", node_id=item_id))
                            continue
                        if not item_refs <= refs:
                            issues.append(_issue("SEMANTIC_ATOMIC_ITEM_SOURCE_DISCONNECTED", "atomic_item.source_unit_refs 必须属于当前 assignment。", node_id=item_id))
                        if len(set(anchors)) < 2:
                            issues.append(_issue("SEMANTIC_ATOMIC_ITEM_ANCHORS_INSUFFICIENT", "每个原子事项至少保留两个来源特征锚点，不能用通用概括代替具体业务内容。", node_id=item_id))
                        if status not in STATUS_VALUES:
                            issues.append(_issue("SEMANTIC_ATOMIC_STATUS_INVALID", "atomic_item.status 不在受控状态词表中。", node_id=item_id))
                        if interpretation_mode == "strict" and not duty:
                            issues.append(_issue("SEMANTIC_ATOMIC_ARGUMENT_DUTY_MISSING", "严格语义理解的每个 atomic_item 必须声明其在来源论证中的 argument_duty，不能由下游按位置或关键词猜测。", node_id=item_id))
                        elif duty and duty not in ARGUMENT_DUTIES:
                            issues.append(_issue("SEMANTIC_ATOMIC_ARGUMENT_DUTY_INVALID", "atomic_item.argument_duty 必须为 premise、driver、consequence、gap、response、support、detail、boundary 或 metadata。", node_id=item_id))
                        compatible_targets = [node_lookup[target_id] for target_id in target_ids if target_id in node_lookup]
                        if compatible_targets and status != "mixed" and all(_text(node.get("status")) not in {status, "mixed"} for node in compatible_targets):
                            issues.append(_issue("SEMANTIC_ATOMIC_STATUS_MISMATCH", "原子事项 status 与其目标语义节点均不相容，应保留真实状态并纠正归类。", node_id=item_id))
                        atomic_covered_refs.update(item_refs)
                    abstracted_refs = sorted(refs - atomic_covered_refs)
                    if abstracted_refs:
                        issues.append(_issue("SEMANTIC_SOURCE_UNIT_ABSTRACTED_AWAY", "以下已分配源单元没有进入任何原子事项，仍可能被 summary 抽象掉：" + "、".join(abstracted_refs)))
                    assigned_refs.update(refs)
                for omission in _list(coverage.get("intentional_omissions")):
                    if not isinstance(omission, dict):
                        issues.append(_issue("SEMANTIC_SOURCE_OMISSION_INVALID", "source_coverage.intentional_omissions 的每项必须是对象。"))
                        continue
                    refs = {_text(item) for item in _list(omission.get("source_unit_refs")) if _text(item)}
                    reason = _text(omission.get("reason"))
                    if not refs or len(reason) < 8:
                        issues.append(_issue("SEMANTIC_SOURCE_OMISSION_REASON_MISSING", "有意忽略必须列明源单元并给出具体编辑理由，不能使用空泛说明。"))
                        continue
                    protected_omissions = sorted(refs & protected_refs)
                    if protected_omissions and (
                        omission.get("user_authorized_omission") is not True
                        or not _text(omission.get("user_decision_ref"))
                    ):
                        issues.append(
                            _issue(
                                "SEMANTIC_PROTECTED_SOURCE_OMITTED",
                                "核心、约束或证据充分的独立支撑事项不得自动舍弃；必须记录 user_authorized_omission=true 和 user_decision_ref："
                                + "、".join(protected_omissions),
                            )
                        )
                    omitted_refs.update(refs)
                overlap = sorted(assigned_refs & omitted_refs)
                if overlap:
                    issues.append(_issue("SEMANTIC_SOURCE_DISPOSITION_CONFLICT", "同一源单元不得同时标记为已归属和有意忽略：" + "、".join(overlap)))
                unknown_dispositions = sorted((assigned_refs | omitted_refs) - set(required_content_unit_ids))
                if unknown_dispositions:
                    issues.append(_issue("SEMANTIC_SOURCE_DISPOSITION_UNKNOWN", "source_coverage 引用了非正文或不存在的源单元：" + "、".join(unknown_dispositions)))
                missing_dispositions = sorted(set(required_content_unit_ids) - assigned_refs - omitted_refs)
                if missing_dispositions:
                    preview = "、".join(missing_dispositions[:12])
                    if len(missing_dispositions) > 12:
                        preview += "……"
                    issues.append(_issue("SEMANTIC_SOURCE_UNIT_UNDISPOSED", "以下正文源信息既未归入语义节点，也未声明有意忽略：" + preview))
    return issues


def node_index(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for field in ("section_nodes", "subsection_nodes"):
        for item in _list(model.get(field)):
            if isinstance(item, dict) and _text(item.get("id")):
                result[_text(item.get("id"))] = item
    return result


def validate_projection_model(
    model: dict[str, Any] | None,
    *,
    source_unit_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    """Validate the narrow contract consumed from a Source Foundation projection.

    Source Foundation handoffs deliberately keep a ``projection_only`` semantic
    model instead of pretending that layer-three/four reconstruction is a
    Stage 00 authoring decision.  Source Truth can still be compiled from that
    projection, but only from the fields it actually consumes: source-bound
    atomic items, node IDs, and the source thesis.  The full ``validate_model``
    contract remains reserved for ``strict`` semantic authoring models.
    """

    issues: list[dict[str, str]] = []
    if not isinstance(model, dict):
        return [_issue("SEMANTIC_ARGUMENT_MODEL_MISSING", "语义理解必须产出机器可读的源材料论点模型。")]
    if model.get("schema") != SCHEMA:
        issues.append(_issue("SEMANTIC_ARGUMENT_MODEL_SCHEMA_INVALID", f"论点模型 schema 必须是 {SCHEMA}。"))
    if _text(model.get("interpretation_contract_mode")) != "projection":
        issues.append(_issue("SEMANTIC_PROJECTION_MODE_REQUIRED", "Source Foundation 兼容模型必须声明 interpretation_contract_mode=projection。"))
    if _text(model.get("authority_mode")) != "projection_only":
        issues.append(_issue("SEMANTIC_PROJECTION_AUTHORITY_REQUIRED", "Source Foundation 兼容模型必须声明 authority_mode=projection_only。"))

    thesis = model.get("document_thesis")
    if not isinstance(thesis, dict) or not _text(thesis.get("statement")):
        issues.append(_issue("SEMANTIC_PROJECTION_THESIS_MISSING", "projection 模型必须保留非空 document_thesis.statement。"))
    elif not _evidence_refs(thesis.get("evidence_refs"))[1]:
        issues.append(_issue("SEMANTIC_PROJECTION_THESIS_EVIDENCE_MISSING", "projection 模型的 document_thesis 必须保留 source evidence_refs。"))

    context = model.get("document_semantics")
    if not isinstance(context, dict):
        issues.append(_issue("SEMANTIC_PROJECTION_CONTEXT_MISSING", "projection 模型必须保留 document_semantics。"))
    elif not _text(context.get("document_role")) or not _text(context.get("subject_of_report")):
        issues.append(_issue("SEMANTIC_PROJECTION_CONTEXT_INCOMPLETE", "projection 模型必须保留 document_role 和 subject_of_report。"))

    nodes = node_index(model)
    if not nodes:
        issues.append(_issue("SEMANTIC_PROJECTION_NODES_MISSING", "projection 模型必须保留可供 Source Truth 绑定的语义节点。"))
    assignments = model.get("source_coverage")
    assignments = assignments.get("assignments") if isinstance(assignments, dict) else None
    if not isinstance(assignments, list) or not assignments:
        issues.append(_issue("SEMANTIC_PROJECTION_ASSIGNMENTS_MISSING", "projection 模型必须保留 source_coverage.assignments。"))
        return issues

    known_units = source_unit_ids or set()
    item_ids: set[str] = set()
    atomic_count = 0
    for assignment in assignments:
        if not isinstance(assignment, dict):
            issues.append(_issue("SEMANTIC_PROJECTION_ASSIGNMENT_INVALID", "projection source_coverage.assignments 的每项必须是对象。"))
            continue
        target_ids = [_text(value) for value in _list(assignment.get("semantic_node_ids")) if _text(value)]
        unknown_nodes = sorted(set(target_ids) - set(nodes))
        if unknown_nodes:
            issues.append(_issue("SEMANTIC_PROJECTION_NODE_UNKNOWN", "projection assignment 引用了未知语义节点：" + "、".join(unknown_nodes)))
        atomics = assignment.get("atomic_items")
        if not isinstance(atomics, list) or not atomics:
            issues.append(_issue("SEMANTIC_PROJECTION_ATOMIC_ITEMS_MISSING", "projection assignment 必须保留 atomic_items。"))
            continue
        for atomic in atomics:
            if not isinstance(atomic, dict):
                issues.append(_issue("SEMANTIC_PROJECTION_ATOMIC_ITEM_INVALID", "projection atomic_items 的每项必须是对象。"))
                continue
            atomic_count += 1
            item_id = _text(atomic.get("item_id"))
            statement = _text(atomic.get("statement"))
            refs, refs_ok = _evidence_refs(atomic.get("source_unit_refs"))
            if not item_id or item_id in item_ids or not statement or not refs_ok:
                issues.append(_issue("SEMANTIC_PROJECTION_ATOMIC_ITEM_INCOMPLETE", "projection atomic item 必须包含唯一 item_id、statement 和 source_unit_refs。", node_id=item_id))
            if item_id:
                item_ids.add(item_id)
            if known_units:
                unknown_refs = sorted(set(refs) - known_units)
                if unknown_refs:
                    issues.append(_issue("SEMANTIC_SOURCE_UNIT_UNKNOWN", "projection atomic item 引用了不存在的 source_unit_id：" + "、".join(unknown_refs), node_id=item_id))
    if not atomic_count:
        issues.append(_issue("SEMANTIC_PROJECTION_ATOMIC_ITEMS_MISSING", "projection 模型没有可编译的 atomic_items。"))
    return issues


def audit_outline_consumption(
    outline: dict[str, Any],
    model: dict[str, Any] | None,
    source_truth: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """Check that an outline consumes semantic nodes instead of source records alone."""

    if not isinstance(model, dict):
        return [_issue("OUTLINE_ARGUMENT_MODEL_MISSING", "严格提纲必须消费语义阶段产出的 source argument model。")]
    index = node_index(model)
    gap_index = {
        _text(item.get("id")): item
        for item in _list(model.get("source_gaps"))
        if isinstance(item, dict) and _text(item.get("id"))
    }
    all_pages = [item for item in _list(outline.get("pages")) if isinstance(item, dict)]
    pages = [item for item in all_pages if item.get("page_type") == "content"]
    subsection_node_ids = {
        _text(item.get("id"))
        for item in _list(model.get("subsection_nodes"))
        if isinstance(item, dict) and _text(item.get("id"))
    }
    records_by_node: dict[str, set[str]] = {}
    if isinstance(source_truth, dict):
        for record in _list(source_truth.get("records")):
            if not isinstance(record, dict):
                continue
            record_id = _text(record.get("id"))
            if not record_id or _text(record.get("argument_duty")) == "metadata":
                continue
            for node_id in _list(record.get("semantic_node_ids")):
                node_id = _text(node_id)
                if node_id:
                    records_by_node.setdefault(node_id, set()).add(record_id)
    author_edited = (
        outline.get("editorial_authoring_mode") == "author_driven"
        and outline.get("editorial_authoring_status") == "author_edited"
        and outline.get("semantic_argument_model_mode") == "required"
    )
    issues: list[dict[str, str]] = []
    primary_consumers: dict[str, list[str]] = {}
    assigned_consumers: dict[str, list[str]] = {}
    for page in pages:
        page_id = _text(page.get("page_id"))
        primary = _text(page.get("primary_argument_node_id"))
        assigned = page.get("source_argument_node_ids")
        if not primary or not isinstance(assigned, list) or not assigned:
            issues.append(_issue("OUTLINE_ARGUMENT_NODE_MAPPING_MISSING", "内容页必须声明 primary_argument_node_id 和 source_argument_node_ids。", node_id=page_id))
            continue
        if primary not in assigned:
            issues.append(_issue("OUTLINE_PRIMARY_ARGUMENT_NOT_ASSIGNED", "页面 primary_argument_node_id 必须包含在 source_argument_node_ids 中。", node_id=page_id))
        assigned_ids = [_text(item) for item in assigned]
        for node_id in assigned_ids:
            if node_id:
                assigned_consumers.setdefault(node_id, []).append(page_id)
        evidence_ids = [
            _text(item)
            for item in _list(page.get("source_evidence_node_ids"))
            if _text(item)
        ]
        for node_id in evidence_ids:
            assigned_consumers.setdefault(node_id, []).append(page_id)
        if len(assigned_ids) != len(set(assigned_ids)):
            issues.append(_issue("OUTLINE_ARGUMENT_NODE_DUPLICATED", "页面 source_argument_node_ids 不得重复声明同一语义节点。", node_id=page_id))
        for node_id in assigned_ids:
            node_id = _text(node_id)
            if node_id not in index:
                issues.append(_issue("OUTLINE_ARGUMENT_NODE_UNKNOWN", "页面引用了语义模型中不存在的论点节点。", node_id=page_id))
        if primary in index:
            # Only the explicit primary node is a primary consumer.  Supporting
            # nodes may be cited by several pages without pretending that the
            # source thesis has multiple owners.
            primary_consumers.setdefault(primary, []).append(page_id)
        page_source_refs = {_text(record_id) for record_id in _list(page.get("source_refs")) if _text(record_id)}
        page_records = [
            record for record in _list(source_truth.get("records"))
            if isinstance(record, dict)
            and _text(record.get("id")) in page_source_refs
        ] if isinstance(source_truth, dict) else []
        if page_records:
            shared_nodes = set.intersection(
                *[{_text(node_id) for node_id in _list(record.get("semantic_node_ids")) if _text(node_id)} for record in page_records]
            )
            scoped_nodes = shared_nodes & subsection_node_ids
            if scoped_nodes and primary not in scoped_nodes:
                narrowest = max(scoped_nodes, key=lambda node_id: int(index.get(node_id, {}).get("level") or 0))
                issues.append(_issue(
                    "PAGE_SOURCE_SCOPE_NODE_TOO_BROAD",
                    "内容页主语义节点必须采用其来源记录共同关联的最窄原文标题范围，不能以章节级节点替代来源范围：" + narrowest,
                    node_id=page_id,
                ))
        # A subsection heading defines a bounded source topic.  Its primary
        # page must consume the complete non-metadata record closure.
        if primary in subsection_node_ids and records_by_node:
            expected_records = records_by_node.get(primary, set())
            actual_records = {
                _text(record_id) for record_id in _list(page.get("source_refs"))
                if _text(record_id)
            }
            missing_records = sorted(expected_records - actual_records)
            if missing_records:
                issues.append(_issue(
                    "PAGE_SOURCE_SECTION_COVERAGE_INCOMPLETE",
                    "内容页主承载原文二级论点时，必须覆盖该论点全部非元数据 Source Truth 记录；代表性首段不能替代完整论证链：" + "、".join(missing_records),
                    node_id=page_id,
                ))
        statuses = page.get("source_argument_node_statuses")
        if not isinstance(statuses, dict):
            issues.append(_issue("OUTLINE_ARGUMENT_STATUSES_MISSING", "页面必须复制所消费语义节点的状态，避免把规划/建议写成已建成事实。", node_id=page_id))
        else:
            for node_id in assigned_ids:
                expected_status = _text(index.get(_text(node_id), {}).get("status"))
                actual_status = _text(statuses.get(_text(node_id)))
                if not actual_status:
                    issues.append(_issue("OUTLINE_ARGUMENT_STATUS_MISSING", "页面未声明某个语义节点的状态。", node_id=page_id))
                elif expected_status and actual_status != expected_status:
                    issues.append(_issue("OUTLINE_ARGUMENT_STATUS_DRIFTED", "页面复制的语义节点状态与 Stage 00 不一致。", node_id=page_id))
        weights = page.get("source_argument_node_weights")
        if not isinstance(weights, dict):
            issues.append(_issue("OUTLINE_ARGUMENT_WEIGHTS_MISSING", "页面必须复制所消费语义节点的 argument_weight，不能根据 supports/maps_to 关系自行降格核心论点。", node_id=page_id))
        else:
            for node_id in assigned_ids:
                expected_weight = _text(index.get(_text(node_id), {}).get("argument_weight"))
                actual_weight = _text(weights.get(_text(node_id)))
                if not actual_weight:
                    issues.append(_issue("OUTLINE_ARGUMENT_WEIGHT_MISSING", "页面未声明某个语义节点的 argument_weight。", node_id=page_id))
                elif expected_weight and actual_weight != expected_weight:
                    issues.append(_issue("OUTLINE_ARGUMENT_WEIGHT_DRIFTED", "页面复制的语义节点 argument_weight 与 Stage 00 不一致；核心论点不得被改写为支撑层。", node_id=page_id))
        roles = page.get("source_argument_node_roles")
        if not isinstance(roles, dict):
            issues.append(_issue("OUTLINE_ARGUMENT_ROLES_MISSING", "页面必须复制所消费语义节点的 argument_role，避免用通用层级标签覆盖源论点角色。", node_id=page_id))
        else:
            for node_id in assigned_ids:
                expected_role = _text(index.get(_text(node_id), {}).get("argument_role"))
                actual_role = _text(roles.get(_text(node_id)))
                if not actual_role:
                    issues.append(_issue("OUTLINE_ARGUMENT_ROLE_MISSING", "页面未声明某个语义节点的 argument_role。", node_id=page_id))
                elif expected_role and actual_role != expected_role:
                    issues.append(_issue("OUTLINE_ARGUMENT_ROLE_DRIFTED", "页面复制的语义节点 argument_role 与 Stage 00 不一致；任何核心源论点都不得被改写为通用支撑层。", node_id=page_id))
        referenced_gaps = {
            _text(gap_id)
            for node_id in assigned
            for gap_id in _list(index.get(_text(node_id), {}).get("source_gap_ids"))
            if _text(gap_id)
        }
        if referenced_gaps:
            page_gap_ids = {_text(item) for item in _list(page.get("source_gap_ids"))}
            unknown_page_gaps = page_gap_ids - set(gap_index)
            if unknown_page_gaps:
                issues.append(_issue("OUTLINE_SOURCE_GAP_UNKNOWN", "页面引用了语义模型中不存在的 source_gap。", node_id=page_id))
            if not referenced_gaps.issubset(page_gap_ids):
                issues.append(_issue("OUTLINE_SOURCE_GAP_HANDLING_MISSING", "页面消费了含源材料缺口的节点，必须声明 source_gap_ids 和 gap_handling。", node_id=page_id))
            elif not _text(page.get("gap_handling")):
                issues.append(_issue("OUTLINE_SOURCE_GAP_HANDLING_MISSING", "页面声明了源材料缺口，但没有说明待确认/条件性表达的处理方式。", node_id=page_id))
        derivation = page.get("core_message_derivation")
        if not isinstance(derivation, dict):
            issues.append(_issue("OUTLINE_DERIVATION_NODE_MISSING", "页面必须声明 core_message_derivation.argument_node_ids。", node_id=page_id))
        else:
            derivation_nodes = {_text(item) for item in _list(derivation.get("argument_node_ids"))}
            if not set(assigned_ids).issubset(derivation_nodes):
                issues.append(_issue("OUTLINE_DERIVATION_NODE_MISSING", "core_message_derivation.argument_node_ids 必须包含页面全部 source_argument_node_ids。", node_id=page_id))

    section_node_ids = {
        _text(item.get("id"))
        for item in _list(model.get("section_nodes"))
        if isinstance(item, dict) and _text(item.get("id"))
    }
    if author_edited:
        core_sections = [
            item for item in _list(model.get("section_nodes"))
            if isinstance(item, dict)
            and _text(item.get("id"))
            and _text(item.get("argument_weight")) == "core"
        ]
        expected_section_ids = [_text(item.get("id")) for item in core_sections]
        chapter_pages = [item for item in all_pages if item.get("page_type") == "chapter"]
        actual_section_ids: list[str] = []
        for chapter in chapter_pages:
            page_id = _text(chapter.get("page_id"))
            section_id = _text(chapter.get("source_section_node_id"))
            expected = next((item for item in core_sections if _text(item.get("id")) == section_id), None)
            if expected is None:
                issues.append(_issue(
                    "SOURCE_SECTION_MAPPING_MISSING",
                    "作者编辑后的章节页必须映射到语义模型中的一级核心章节节点。",
                    node_id=page_id,
                ))
                continue
            actual_section_ids.append(section_id)
            source_title = _text(chapter.get("source_section_title"))
            expected_title = _text(expected.get("source_heading"))
            if source_title != expected_title or _text(chapter.get("title")) != expected_title:
                issues.append(_issue(
                    "SOURCE_SECTION_TITLE_DRIFTED",
                    "章节页 title 和 source_section_title 必须等于映射的原文一级章节标题；编辑标签应放在 editorial_chapter_label。",
                    node_id=page_id,
                ))
        if actual_section_ids != expected_section_ids:
            issues.append(_issue(
                "SOURCE_SECTION_ORDER_DRIFTED",
                "章节页必须按语义模型中的一级核心章节顺序逐一呈现，不得重排、漏映射或替换为编辑标题。",
            ))
    required_nodes = list(_list(model.get("section_nodes"))) + list(_list(model.get("subsection_nodes")))
    for node in required_nodes:
        if not isinstance(node, dict):
            continue
        node_id = _text(node.get("id"))
        primary_requirement = node.get("required_for_primary_consumer")
        chapter_mapped = any(
            _text(page.get("source_section_node_id")) == node_id
            for page in all_pages
            if page.get("page_type") == "chapter"
        )
        required_for_primary = primary_requirement is True or (
            node_id in section_node_ids
            and primary_requirement is not False
            and _text(node.get("argument_weight")) == "core"
            and not chapter_mapped
        )
        if not required_for_primary:
            continue
        if not node_id or not _text(node.get("primary_consumer")):
            continue
        consumers = primary_consumers.get(node_id, [])
        if not consumers:
            issues.append(_issue("ARGUMENT_NODE_WITHOUT_PRIMARY_CONSUMER", "语义模型中的源论点没有页面 primary consumer；必须明确承载页或声明合并。", node_id=node_id))
        elif len(consumers) > 1:
            allowed = {_text(item) for item in _list(node.get("allowed_merges"))}
            if not allowed or not set(consumers).issubset(allowed):
                issues.append(_issue("ARGUMENT_NODE_PRIMARY_CONSUMER_DUPLICATED", "同一源论点被多个页面作为主论点消费，但没有声明 allowed_merges。", node_id=node_id))

    disposition_required = (
        outline.get("semantic_argument_model_mode") == "required"
        or outline.get("argument_node_disposition_mode") == "required"
    )
    if disposition_required and outline.get("argument_node_disposition_mode") != "required":
        issues.append(_issue(
            "OUTLINE_ARGUMENT_DISPOSITION_MODE_REQUIRED",
            "正式语义论点提纲默认必须启用 argument_node_disposition_mode=required，逐项说明章节内容如何形成页面。",
        ))
    if disposition_required:
        raw_dispositions = outline.get("argument_node_dispositions")
        dispositions = [
            item for item in _list(raw_dispositions) if isinstance(item, dict)
        ]
        disposition_index: dict[str, dict[str, Any]] = {}
        for item in dispositions:
            node_id = _text(item.get("node_id"))
            if not node_id:
                issues.append(_issue(
                    "OUTLINE_ARGUMENT_DISPOSITION_NODE_MISSING",
                    "论点节点处置项必须声明 node_id。",
                ))
                continue
            if node_id in disposition_index:
                issues.append(_issue(
                    "OUTLINE_ARGUMENT_DISPOSITION_DUPLICATED",
                    "同一论点节点只能声明一次页面处置。",
                    node_id=node_id,
                ))
            disposition_index[node_id] = item

        # Subsection nodes are the smallest source-authored argument units that
        # can become pages.  Every one must be deliberately carried, merged, or
        # omitted; a detail/evidence citation alone must not hide page loss.
        candidate_ids = {
            _text(item.get("id"))
            for item in _list(model.get("subsection_nodes"))
            if isinstance(item, dict) and _text(item.get("id"))
        }
        for node_id in sorted(candidate_ids):
            item = disposition_index.get(node_id)
            node = index.get(node_id, {})
            weight = _text(node.get("argument_weight"))
            evidence_count = len(_list(node.get("evidence_refs")))
            protected = (
                weight in {"core", "constraint"}
                or (
                    bool(_text(node.get("source_heading")))
                    and evidence_count >= 6
                    and weight == "supporting"
                )
            )
            if item is None:
                issues.append(_issue(
                    "OUTLINE_ARGUMENT_DISPOSITION_MISSING",
                    "源材料小节论点未声明独立成页、合并承载或有意舍弃；detail_refs 和证据引用不能替代章节选材决定。",
                    node_id=node_id,
                ))
                continue
            disposition = _text(item.get("disposition"))
            page_id = _text(item.get("page_id"))
            rationale = _text(item.get("rationale"))
            if disposition not in {"standalone_page", "merged_page", "intentional_omission"}:
                issues.append(_issue(
                    "OUTLINE_ARGUMENT_DISPOSITION_INVALID",
                    "论点节点处置必须是 standalone_page、merged_page 或 intentional_omission。",
                    node_id=node_id,
                ))
                continue
            if not rationale:
                issues.append(_issue(
                    "OUTLINE_ARGUMENT_DISPOSITION_RATIONALE_MISSING",
                    "每个论点节点的页面处置都必须说明选择、合并或舍弃理由。",
                    node_id=node_id,
                ))
            if disposition == "standalone_page":
                if not page_id or page_id not in primary_consumers.get(node_id, []):
                    issues.append(_issue(
                        "OUTLINE_STANDALONE_ARGUMENT_NOT_PRIMARY",
                        "声明独立成页的论点节点必须是对应页面的 primary_argument_node_id。",
                        node_id=node_id,
                    ))
            elif disposition == "merged_page":
                if not page_id or page_id not in assigned_consumers.get(node_id, []):
                    issues.append(_issue(
                        "OUTLINE_MERGED_ARGUMENT_NOT_CONSUMED",
                        "声明合并承载的论点节点必须由指定页面正式消费，不能只放入 detail_refs 或 evidence 字段。",
                        node_id=node_id,
                    ))
                if not _text(item.get("merge_reason")):
                    issues.append(_issue(
                        "OUTLINE_ARGUMENT_MERGE_REASON_MISSING",
                        "合并承载必须说明两个论点为何属于同一页面主题和同一主业务关系。",
                        node_id=node_id,
                    ))
                shared_topic = _text(item.get("shared_page_topic"))
                target_page = next(
                    (page for page in pages if _text(page.get("page_id")) == page_id),
                    None,
                )
                if not shared_topic:
                    issues.append(_issue(
                        "OUTLINE_ARGUMENT_MERGE_TOPIC_MISSING",
                        "合并承载必须声明 shared_page_topic，证明被合并论点服务于同一页面主题。",
                        node_id=node_id,
                    ))
                elif isinstance(target_page, dict) and shared_topic != _text(target_page.get("topic_category")):
                    issues.append(_issue(
                        "OUTLINE_ARGUMENT_MERGE_TOPIC_MISMATCH",
                        "合并处置的 shared_page_topic 必须与承载页 topic_category 完全一致。",
                        node_id=node_id,
                    ))
                source_parent = _text(node.get("parent_id"))
                target_primary = _text(target_page.get("primary_argument_node_id")) if isinstance(target_page, dict) else ""
                target_parent = _text(index.get(target_primary, {}).get("parent_id"))
                if (
                    source_parent
                    and target_primary
                    and target_primary != source_parent
                    and target_parent != source_parent
                    and not _text(item.get("cross_chapter_reason"))
                ):
                    issues.append(_issue(
                        "OUTLINE_ARGUMENT_CROSS_CHAPTER_REASON_MISSING",
                        "论点跨出原章节承载时必须声明 cross_chapter_reason，说明新的章节位置为何更符合故事线。",
                        node_id=node_id,
                    ))
            elif disposition == "intentional_omission":
                if not _text(item.get("omission_reason")):
                    issues.append(_issue(
                        "OUTLINE_ARGUMENT_OMISSION_REASON_MISSING",
                        "有意舍弃必须说明其与所选交流目标或故事线的关系，不能以篇幅有限笼统代替。",
                        node_id=node_id,
                    ))
                if author_edited:
                    retained_for = {
                        _text(value) for value in _list(item.get("retained_for"))
                        if _text(value)
                    }
                    allowed_retention = {
                        "page_script", "implementation_plan",
                        "single_item_confirmation", "traceability_only",
                    }
                    if not retained_for or not retained_for.issubset(allowed_retention):
                        issues.append(_issue(
                            "OUTLINE_OMISSION_RETAINED_FOR_MISSING",
                            "作者编辑后的有意舍弃必须以 retained_for 说明细节保留在页面脚本、实施方案、单项确认或追溯层。",
                            node_id=node_id,
                        ))
                    known_page_ids = {_text(page.get("page_id")) for page in all_pages}
                    related_page_ids = {
                        _text(value) for value in _list(item.get("related_page_ids"))
                        if _text(value)
                    }
                    if not related_page_ids.issubset(known_page_ids):
                        issues.append(_issue(
                            "OUTLINE_OMISSION_RELATED_PAGE_UNKNOWN",
                            "有意舍弃项的 related_page_ids 必须引用当前提纲中存在的页面。",
                            node_id=node_id,
                        ))
                if protected and not (
                    item.get("user_authorized_omission") is True
                    and _text(item.get("user_decision_ref"))
                ):
                    issues.append(_issue(
                        "OUTLINE_PROTECTED_ARGUMENT_OMITTED",
                        "核心、关键约束或证据充分的独立小节论点不得由生成器自行舍弃；如用户明确要求删除，必须记录 user_authorized_omission=true 和 user_decision_ref。",
                        node_id=node_id,
                    ))

    # The semantic model marks relationships between semantic layers.  A page
    # cannot claim that two nodes are interchangeable merely because they cite
    # overlapping evidence.
    relation_pairs = {
        (_text(item.get("from")), _text(item.get("to")))
        for item in _list(model.get("argument_relations"))
        if isinstance(item, dict)
    }
    for page in pages:
        assigned = [_text(item) for item in _list(page.get("source_argument_node_ids"))]
        for left in assigned:
            for right in assigned:
                if left >= right or left not in index or right not in index:
                    continue
                if (left, right) not in relation_pairs and (right, left) not in relation_pairs and left != right:
                    issues.append(_issue("OUTLINE_ARGUMENT_NODES_MERGED_WITHOUT_RELATION", "页面合并了没有源材料关系说明的不同论点节点；请拆分或在语义阶段声明关系。", node_id=_text(page.get("page_id"))))
    return issues

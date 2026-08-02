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
ARGUMENT_WEIGHT_BUCKETS = ("core", "supporting", "detail", "constraint")
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
    valid = all(ref and re.fullmatch(r"S\d+", ref) for ref in refs)
    return refs, valid


def empty_model() -> dict[str, Any]:
    """Return the required shape used in the semantic authoring template."""

    return {
        "schema": SCHEMA,
        "version": 1,
        "document_semantics": {
            "document_role": "",
            "subject_of_report": "",
            "primary_thesis": "",
            "decision_boundary": "",
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
        },
        "section_nodes": [],
        "subsection_nodes": [],
        "argument_relations": [],
        "argument_weighting": {
            "definition": "论点权重描述源材料自身的论证重要性；core 是独立核心主张，supporting 是证明或展开模块，detail 是保留细节，constraint 是约束条件。论证关系不改变节点权重。",
            "core_node_ids": [],
            "supporting_node_ids": [],
            "detail_node_ids": [],
            "constraint_node_ids": [],
            "review_notes": [],
        },
        "mece_rules": {
            "partition_basis": "",
            "exhaustive_scope": "",
            "overlap_policy": "",
            "groups": [],
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


def validate_model(
    model: dict[str, Any] | None,
    *,
    required_headings: list[str] | None = None,
    source_record_ids: set[str] | None = None,
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

    weighting = model.get("argument_weighting")
    if not isinstance(weighting, dict):
        issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_MISSING", "语义理解必须声明 argument_weighting，明确哪些节点是核心论点、支撑模块、细节或约束。"))
    else:
        if not _text(weighting.get("definition")):
            issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_INCOMPLETE", "argument_weighting.definition 必须解释论点权重与论证关系的区别。"))
        bucket_ids: dict[str, list[str]] = {}
        for bucket in ARGUMENT_WEIGHT_BUCKETS:
            values = weighting.get(f"{bucket}_node_ids")
            if not isinstance(values, list):
                issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_BUCKET_INVALID", f"argument_weighting.{bucket}_node_ids 必须是数组。"))
                values = []
            bucket_ids[bucket] = [_text(item) for item in values if _text(item)]
        assigned: dict[str, str] = {}
        for bucket, values in bucket_ids.items():
            if len(values) != len(set(values)):
                issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_DUPLICATED", f"argument_weighting.{bucket}_node_ids 不得重复。"))
            for node_id in values:
                if node_id not in node_ids:
                    issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_NODE_UNKNOWN", "argument_weighting 引用了不存在的论点节点。", node_id=node_id))
                if node_id in assigned:
                    issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_NODE_REUSED", "同一论点节点不得同时被归入多个权重桶。", node_id=node_id))
                assigned[node_id] = bucket
        missing_weights = sorted(node_ids - set(assigned))
        if missing_weights:
            issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHTING_NODE_MISSING", "每个章节/子章节节点都必须进入一个明确的论点权重桶：" + "、".join(missing_weights)))
        for node_id, expected_weight in assigned.items():
            actual_weight = _text((node_index(model).get(node_id) or {}).get("argument_weight"))
            if actual_weight and actual_weight != expected_weight:
                issues.append(_issue("SEMANTIC_ARGUMENT_WEIGHT_DRIFTED", "节点 argument_weight 必须与 argument_weighting 的权重桶一致；关系类型不能覆盖该字段。", node_id=node_id))

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
        unknown = sorted({ref for ref in refs if ref.startswith("S") and ref not in source_record_ids})
        if unknown:
            issues.append(_issue("SEMANTIC_ARGUMENT_EVIDENCE_UNKNOWN", "论点模型引用了 Source Truth 中不存在的证据：" + "、".join(unknown)))
    return issues


def node_index(model: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for field in ("section_nodes", "subsection_nodes"):
        for item in _list(model.get(field)):
            if isinstance(item, dict) and _text(item.get("id")):
                result[_text(item.get("id"))] = item
    return result


def audit_outline_consumption(
    outline: dict[str, Any],
    model: dict[str, Any] | None,
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
    pages = [item for item in _list(outline.get("pages")) if isinstance(item, dict) and item.get("page_type") == "content"]
    issues: list[dict[str, str]] = []
    primary_consumers: dict[str, list[str]] = {}
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
            issues.append(_issue("OUTLINE_ARGUMENT_ROLES_MISSING", "页面必须复制所消费语义节点的 argument_role，避免把 advantage/capability 等核心论点改写成 foundation。", node_id=page_id))
        else:
            for node_id in assigned_ids:
                expected_role = _text(index.get(_text(node_id), {}).get("argument_role"))
                actual_role = _text(roles.get(_text(node_id)))
                if not actual_role:
                    issues.append(_issue("OUTLINE_ARGUMENT_ROLE_MISSING", "页面未声明某个语义节点的 argument_role。", node_id=page_id))
                elif expected_role and actual_role != expected_role:
                    issues.append(_issue("OUTLINE_ARGUMENT_ROLE_DRIFTED", "页面复制的语义节点 argument_role 与 Stage 00 不一致；不能把行业优势/核心能力节点改写成 foundation。", node_id=page_id))
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
    required_nodes = list(_list(model.get("section_nodes"))) + list(_list(model.get("subsection_nodes")))
    for node in required_nodes:
        if not isinstance(node, dict):
            continue
        node_id = _text(node.get("id"))
        required_for_primary = node.get("required_for_primary_consumer") is True or (
            node_id in section_node_ids and node.get("required_for_primary_consumer") is not False
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

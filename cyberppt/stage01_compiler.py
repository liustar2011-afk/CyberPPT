"""Deterministic lightweight Stage 01 projections.

The canonical semantic model is authored once.  Source Truth and the first
Outline draft are projections of that model, source units, and the selected
communication goal.  They remain normal CyberPPT artifacts and are checked by
the existing lightweight audits.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from cyberppt.semantic_understanding import SEMANTIC_ARGUMENT_MODEL
from cyberppt.source_argument_model import load_model, node_index, validate_model
from cyberppt.source_document_map import SOURCE_REGISTRY, SOURCE_UNITS


SOURCE_TRUTH = Path("workbench/stages/01-analysis/source-truth.json")
OUTLINE = Path("workbench/stages/01-analysis/outline.json")

EVIDENCE_TYPE = {
    "fact": "F",
    "change": "F",
    "problem": "J",
    "judgment": "J",
    "recommendation": "R",
    "boundary": "B",
    "unresolved": "U",
}
PRIORITY = {"core": "P0", "supporting": "P2", "constraint": "P1", "detail": "P2"}
STATUS = {
    "existing": "现状",
    "in_progress": "进行中",
    "planned": "规划",
    "proposal": "拟建议",
    "to_confirm": "待确认",
    "recommendation": "建议",
    "mixed": "阶段判断",
    "unknown": "待确认",
}
PAGE_ROLE = {
    "foundation": "foundation",
    "definition": "positioning",
    "positioning": "positioning",
    "construction": "solution",
    "capability": "solution",
    "advantage": "solution",
    "architecture": "solution",
    "operation": "solution",
    "cooperation": "scope",
    "implementation": "implementation",
    "recommendation": "implementation",
    "boundary": "assurance",
    "gap": "gap",
    "evidence": "foundation",
}
VISUAL_INTENT = {
    "foundation": "evidence_support",
    "definition": "concept_definition",
    "positioning": "positioning_relation",
    "construction": "architecture",
    "capability": "capability_map",
    "advantage": "judgment_evidence",
    "architecture": "architecture",
    "operation": "closed_loop_operation",
    "cooperation": "actor_relation",
    "implementation": "phase",
    "recommendation": "phase",
    "boundary": "boundary_guardrail",
    "gap": "gap_evidence",
    "evidence": "evidence_support",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at {path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _source_units(project: Path) -> dict[str, dict[str, Any]]:
    path = project / SOURCE_UNITS
    if not path.is_file():
        raise FileNotFoundError(
            f"source units do not exist: {path}; run prepare-source-map first"
        )
    result: dict[str, dict[str, Any]] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            item = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid source unit JSON at {path}:{line_number}: {exc.msg}") from exc
        if not isinstance(item, dict) or not str(item.get("unit_id") or "").strip():
            raise ValueError(f"invalid source unit at {path}:{line_number}")
        result[str(item["unit_id"])] = item
    return result


def _source_locator(unit: dict[str, Any]) -> dict[str, Any]:
    locator = unit.get("locator") if isinstance(unit.get("locator"), dict) else {}
    result: dict[str, Any] = {
        "source_id": str(unit.get("source_id") or ""),
        "file": str(unit.get("source_path") or ""),
        "section": " / ".join(_strings(unit.get("heading_path"))) or "全文",
    }
    for field in ("paragraph", "table", "table_row", "cell", "line"):
        if locator.get(field) not in (None, ""):
            result["paragraph" if field == "line" else field] = locator[field]
    if not any(result.get(field) not in (None, "") for field in ("paragraph", "table", "table_row", "cell")):
        result["paragraph"] = int(unit.get("source_order") or 1)
    return result


def _record_id(index: int) -> str:
    return f"ST{index:04d}"


def compile_source_truth(project: Path, output: Path | None = None) -> Path:
    """Project semantic atomic items into the canonical Source Truth artifact."""

    project = project.expanduser().resolve()
    model_path = project / SEMANTIC_ARGUMENT_MODEL
    if not model_path.is_file():
        raise FileNotFoundError(f"semantic argument model does not exist: {model_path}")
    model = load_model(model_path)
    units = _source_units(project)
    required_content_unit_ids = {
        unit_id
        for unit_id, unit in units.items()
        if str(unit.get("kind") or "") != "heading"
    }
    model_issues = validate_model(
        model,
        source_unit_ids=set(units),
        required_content_unit_ids=required_content_unit_ids,
        require_document_context=True,
    )
    if model_issues:
        codes = ", ".join(
            dict.fromkeys(str(item.get("code") or "SEMANTIC_MODEL_INVALID") for item in model_issues)
        )
        raise ValueError(
            "cannot compile Source Truth: semantic argument model has blocking contract issues: "
            + codes
        )
    nodes = node_index(model)
    assignments = _items((model.get("source_coverage") or {}).get("assignments")) if isinstance(model.get("source_coverage"), dict) else []
    records: list[dict[str, Any]] = []
    item_to_record: dict[str, str] = {}

    for assignment in assignments:
        semantic_node_ids = _strings(assignment.get("semantic_node_ids"))
        for atomic in _items(assignment.get("atomic_items")):
            item_id = str(atomic.get("item_id") or "").strip()
            statement = str(atomic.get("statement") or "").strip()
            refs = _strings(atomic.get("source_unit_refs"))
            if not item_id or not statement or not refs:
                raise ValueError(
                    "cannot compile Source Truth: every atomic item needs item_id, statement, and source_unit_refs"
                )
            if item_id in item_to_record:
                raise ValueError(f"cannot compile Source Truth: duplicate atomic item id: {item_id}")
            missing = [ref for ref in refs if ref not in units]
            if missing:
                raise ValueError(f"atomic item {item_id} references unknown source units: {missing}")
            record_id = _record_id(len(records) + 1)
            item_to_record[item_id] = record_id
            evidence_role = str(atomic["evidence_role"])
            first = units[refs[0]]
            quote = "\n".join(str(units[ref].get("text") or "").strip() for ref in refs).strip()
            origins = {
                str(nodes.get(node_id, {}).get("claim_origin") or "").strip()
                for node_id in semantic_node_ids
                if node_id in nodes
            }
            claim_origin = str(atomic.get("claim_origin") or "").strip()
            if not claim_origin:
                claim_origin = next((value for value in origins if value), "source_explicit")
            anchors = _strings(atomic.get("coverage_anchors"))
            importance = str(atomic.get("importance") or "detail").strip()
            status = str(atomic.get("status") or "unknown").strip()
            clauses = [
                clause.strip()
                for clause in re.split(r"(?<=[。；;])", statement)
                if clause.strip()
            ]
            if len(clauses) > 1:
                semantic_units = [
                    {"text": clause, "claim_role": evidence_role, "source_unit_refs": refs}
                    for clause in clauses
                ]
            else:
                semantic_units = [
                    {
                        "text": str(units[ref].get("text") or statement).strip(),
                        "claim_role": evidence_role,
                        "source_unit_ref": ref,
                    }
                    for ref in refs
                ]
            fingerprint_source = json.dumps(
                {"statement": statement, "source_unit_refs": refs},
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
            records.append(
                {
                    "id": record_id,
                    "atomic_item_id": item_id,
                    "type": EVIDENCE_TYPE[evidence_role],
                    "priority": (
                        str(atomic.get("evidence_priority"))
                        if str(atomic.get("evidence_priority")) in {"P0", "P1", "P2"}
                        else PRIORITY.get(importance, "P2")
                    ),
                    "statement": statement,
                    "source_locator": _source_locator(first),
                    "source_unit_refs": refs,
                    "semantic_node_ids": semantic_node_ids,
                    "claim_origin": claim_origin,
                    "status": STATUS.get(status, status or "待确认"),
                    "semantic_status": status,
                    "claim_role": evidence_role,
                    "semantic_argument_role": str(atomic.get("claim_role") or ""),
                    "semantic_units": semantic_units,
                    "coverage_anchors": anchors,
                    "actors": _strings(atomic.get("actors")),
                    "conditions": _strings(atomic.get("conditions")),
                    "numeric_facts": atomic.get("numeric_facts") if isinstance(atomic.get("numeric_facts"), list) else [],
                    "allowed_page_roles": [],
                    "forbidden_page_roles": [],
                    "depends_on": [],
                    "supports": [],
                    "page_refs": [],
                    "quote": quote or statement,
                    "fingerprint": "sha256:" + hashlib.sha256(fingerprint_source).hexdigest(),
                }
            )

    if not records:
        raise ValueError("semantic model has no atomic items to compile into Source Truth")

    for assignment in assignments:
        for atomic in _items(assignment.get("atomic_items")):
            record_id = item_to_record.get(str(atomic.get("item_id") or ""))
            if not record_id:
                continue
            record = next(item for item in records if item["id"] == record_id)
            record["depends_on"] = [
                item_to_record[item_id]
                for item_id in _strings(atomic.get("depends_on_item_ids"))
                if item_id in item_to_record
            ]

    thesis = model.get("document_thesis") if isinstance(model.get("document_thesis"), dict) else {}
    thesis_units = set(_strings(thesis.get("evidence_refs")))
    conclusion_refs = [
        record["id"]
        for record in records
        if thesis_units.intersection(_strings(record.get("source_unit_refs")))
    ] or [record["id"] for record in records if record["priority"] == "P0"] or [records[0]["id"]]
    conclusion = {
        "id": "C001",
        "statement": str(thesis.get("statement") or "").strip(),
        "source_refs": conclusion_refs,
    }
    for record in records:
        if record["id"] in conclusion_refs:
            record["supports"] = ["C001"]

    registry_path = project / SOURCE_REGISTRY
    registry = _read_json(registry_path) if registry_path.is_file() else {"sources": []}
    registry_sources = _items(registry.get("sources"))
    source_summaries = []
    for source in registry_sources:
        source_id = str(source.get("source_id") or "")
        source_units = [item for item in units.values() if str(item.get("source_id") or "") == source_id]
        source_summaries.append(
            {
                "id": source_id,
                "file": str(source.get("path") or source.get("file_name") or ""),
                "role": str(source.get("role") or "primary"),
                "non_empty_paragraphs": sum(1 for item in source_units if item.get("kind") != "heading"),
                "headings": sum(1 for item in source_units if item.get("kind") == "heading"),
                "tables": sum(1 for item in source_units if item.get("kind") in {"table", "table_row", "table_cell"}),
            }
        )

    coverage_targets = []
    for node_id, node in nodes.items():
        record_refs = [
            record["id"]
            for record in records
            if node_id in _strings(record.get("semantic_node_ids"))
        ]
        if not record_refs:
            continue
        coverage_targets.append(
            {
                "id": f"T{len(coverage_targets) + 1:03d}",
                "kind": "semantic_node",
                "label": str(node.get("source_heading") or node_id),
                "semantic_node_id": node_id,
                "priority": PRIORITY.get(str(node.get("argument_weight") or "detail"), "P2"),
                "required": True,
                "record_refs": record_refs,
            }
        )

    semantics = dict(model.get("document_semantics") or {})
    semantics["primary_thesis"] = str(thesis.get("statement") or semantics.get("primary_thesis") or "")
    semantics["source_refs"] = conclusion_refs
    coverage = model.get("source_coverage") if isinstance(model.get("source_coverage"), dict) else {}
    payload = {
        "schema": "cyberppt.source_truth.v1",
        "argument_contract_mode": "strict",
        "document_semantics_mode": "required",
        "projection_mode": "semantic_atomic_items",
        "project": {
            "title": project.name,
            "material_type": str(semantics.get("document_role") or "正式材料"),
            "audience": "由后续交流目标确定",
        },
        "document_semantics": semantics,
        "sources": source_summaries,
        "coverage_targets": coverage_targets,
        "records": records,
        "conclusions": [conclusion],
        "pages": [],
        "intentional_source_unit_omissions": _items(coverage.get("intentional_omissions")),
    }
    return _write_json(output.expanduser().resolve() if output else project / SOURCE_TRUTH, payload)


def _clean_title(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^第[一二三四五六七八九十百\d]+章[、：:\s　]*", "", text)
    text = re.sub(r"^[一二三四五六七八九十百\d]+[、.．]\s*", "", text)
    return text or "业务事项"


def _page_content_units(page_id: str, records: list[dict[str, Any]], topic: str) -> tuple[list[dict[str, Any]], list[str]]:
    structural = [record for record in records if str(record.get("priority")) != "P2"]
    details = [str(record.get("id")) for record in records if str(record.get("priority")) == "P2"]
    if not structural and records:
        structural = [records[0]]
        details = [str(record.get("id")) for record in records[1:]]

    boundaries = [
        record
        for record in structural
        if str(record.get("claim_role") or "") in {"boundary", "unresolved"}
    ]
    ordinary = [record for record in structural if record not in boundaries]
    primary = [record for record in ordinary if str(record.get("priority")) == "P0"]
    supporting = [record for record in ordinary if record not in primary]
    if not primary and supporting:
        primary, supporting = supporting[:1], supporting[1:]

    groups: list[tuple[str, list[dict[str, Any]]]] = []
    if primary:
        groups.append(("primary", primary))
    by_role: dict[str, list[dict[str, Any]]] = {}
    for record in supporting:
        by_role.setdefault(str(record.get("claim_role") or "fact"), []).append(record)
    for role_records in list(by_role.values())[:3]:
        groups.append(("supporting", role_records))
    ungrouped_supporting = [
        record
        for role_records in list(by_role.values())[3:]
        for record in role_records
    ]
    details.extend(str(record.get("id")) for record in ungrouped_supporting)
    if boundaries:
        groups.append(("boundary", boundaries))

    result: list[dict[str, Any]] = []
    for index, (role, grouped) in enumerate(groups, start=1):
        anchors = list(
            dict.fromkeys(
                anchor
                for record in grouped
                for anchor in _strings(record.get("coverage_anchors")) + _strings(record.get("actors"))
            )
        )
        if len(anchors) < 2:
            anchors = (anchors + [_clean_title(grouped[0].get("statement")), topic])[:2]
        statements = [
            str(record.get("statement") or "").strip()
            for record in grouped
            if str(record.get("statement") or "").strip()
        ]
        result.append(
            {
                "unit_id": f"{page_id}-U{index:02d}",
                "statement": "；".join(statements),
                "source_refs": [str(record.get("id")) for record in grouped],
                "role": role,
                "importance": role,
                "full_prose_required": True,
                "coverage_anchors": anchors[:4],
                "onscreen_required": role in {"primary", "boundary"},
                "onscreen_anchors": anchors[:1],
                "topic_category": topic,
            }
        )
    if result and not any(item["onscreen_required"] for item in result):
        result[0]["onscreen_required"] = True
        result[0]["onscreen_anchors"] = result[0]["coverage_anchors"][:1]
    return result, list(dict.fromkeys(details))


def compile_outline_draft(
    project: Path,
    *,
    communication_goal: str,
    output: Path | None = None,
    source_truth: Path | None = None,
) -> Path:
    """Compile a complete editable Outline draft from semantic nodes and truth."""

    project = project.expanduser().resolve()
    if not communication_goal.strip():
        raise ValueError("communication_goal is required")
    model = load_model(project / SEMANTIC_ARGUMENT_MODEL)
    semantic_nodes = node_index(model)
    truth_path = source_truth.expanduser().resolve() if source_truth else project / SOURCE_TRUTH
    truth = _read_json(truth_path)
    records = _items(truth.get("records"))
    record_by_node: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for node_id in _strings(record.get("semantic_node_ids")):
            record_by_node.setdefault(node_id, []).append(record)
    sections = _items(model.get("section_nodes"))
    subsections = _items(model.get("subsection_nodes"))
    subsections_by_parent: dict[str, list[dict[str, Any]]] = {}
    for node in subsections:
        subsections_by_parent.setdefault(str(node.get("parent_id") or ""), []).append(node)

    pages: list[dict[str, Any]] = []
    pages.append({"page_id": "p01", "sequence": 1, "page_type": "cover", "title": _clean_title((model.get("document_semantics") or {}).get("subject_of_report"))})
    pages.append({"page_id": "p02", "sequence": 2, "page_type": "agenda", "title": "目录"})
    dispositions: list[dict[str, Any]] = []
    chapter_missions: list[dict[str, Any]] = []
    chapter_orders: list[dict[str, Any]] = []
    content_pages: list[dict[str, Any]] = []

    for section_index, section in enumerate(sections, start=1):
        chapter_id = f"C{section_index}"
        chapter_title = _clean_title(section.get("source_heading"))
        pages.append(
            {
                "page_id": f"p{len(pages) + 1:02d}",
                "sequence": len(pages) + 1,
                "page_type": "chapter",
                "chapter_id": chapter_id,
                "title": chapter_title,
            }
        )
        nodes = subsections_by_parent.get(str(section.get("id") or ""), [])
        if not nodes:
            nodes = [section]
        chapter_content: list[dict[str, Any]] = []
        for node in nodes:
            node_id = str(node.get("id") or "")
            merge_with_section = node in subsections and not chapter_content
            section_id = str(section.get("id") or "")
            primary_node_id = section_id if merge_with_section else node_id
            consumed_node_ids = list(dict.fromkeys([primary_node_id, node_id]))
            page_id = f"p{len(pages) + 1:02d}"
            topic = _clean_title(node.get("source_heading"))
            node_records = []
            seen_record_ids: set[str] = set()
            for consumed_node_id in consumed_node_ids:
                for record in record_by_node.get(consumed_node_id, []):
                    record_id = str(record.get("id") or "")
                    if record_id and record_id not in seen_record_ids:
                        seen_record_ids.add(record_id)
                        node_records.append(record)
            if not node_records and node is section:
                node_records = record_by_node.get(str(section.get("id") or ""), [])
            if not node_records:
                continue
            content_units, detail_refs = _page_content_units(page_id, node_records, topic)
            source_refs = [str(record.get("id")) for record in node_records]
            core_message = str(node.get("section_thesis") or node.get("thesis") or "").strip()
            if not core_message:
                core_message = str(node_records[0].get("statement") or "").strip()
            semantic_role = str(node.get("argument_role") or "evidence")
            page_role = PAGE_ROLE.get(semantic_role, "solution")
            boundary_refs = [
                str(record.get("id"))
                for record in node_records
                if str(record.get("claim_role") or "") in {"boundary", "unresolved"}
            ]
            structural_refs = [ref for unit in content_units for ref in _strings(unit.get("source_refs"))]
            relation_objects = [
                str(unit.get("statement") or "").strip()
                for unit in content_units[:4]
                if str(unit.get("statement") or "").strip()
            ]
            page = {
                "page_id": page_id,
                "sequence": len(pages) + 1,
                "page_type": "content",
                "chapter_id": chapter_id,
                "title": topic,
                "page_mission": f"说明{topic}在全文论证中的业务含义、状态和证据边界。",
                "page_job": f"说明{topic}在全文论证中的业务含义、状态和证据边界。",
                "core_message": core_message,
                "audience_question": f"{topic}具体包含什么，当前处于什么状态？",
                "business_question": f"{topic}的业务含义和状态是什么？",
                "topic_category": topic,
                "must_not_include": ["未经来源确认的承诺、结果或责任"],
                "split_risk": "low",
                "new_value_vs_previous": f"建立对{topic}的独立、可回查认识。",
                "reserved_for_later": "相邻主题、实施细节和未确认事项由其责任页面继续展开。",
                "storyline_role": f"回答本章关于{topic}的独立问题。",
                "transition_from_previous": "由前一主题的已知条件进入本主题的业务判断。",
                "transition_to_next": "以本主题形成的判断作为下一主题的理解前提。",
                "page_order_reason": f"保持来源章节顺序，并在本章第{len(chapter_content) + 1}个位置处理{topic}。",
                "argument_role": page_role,
                "allowed_claim_roles": sorted({str(record.get("claim_role") or "fact") for record in node_records}),
                "forbidden_claim_roles": [],
                "prerequisite_pages": [chapter_content[-1]["page_id"]] if chapter_content else [],
                "main_claim_status": "proposed" if boundary_refs else "confirmed",
                "primary_argument_node_id": primary_node_id,
                "source_argument_node_ids": consumed_node_ids,
                "source_evidence_node_ids": [],
                "source_argument_node_roles": {
                    consumed_node_id: str(semantic_nodes.get(consumed_node_id, {}).get("argument_role") or "evidence")
                    for consumed_node_id in consumed_node_ids
                },
                "source_argument_node_weights": {
                    consumed_node_id: str(semantic_nodes.get(consumed_node_id, {}).get("argument_weight") or "detail")
                    for consumed_node_id in consumed_node_ids
                },
                "source_argument_node_statuses": {
                    consumed_node_id: str(semantic_nodes.get(consumed_node_id, {}).get("status") or "unknown")
                    for consumed_node_id in consumed_node_ids
                },
                "source_gap_ids": [],
                "gap_handling": "保留 Source Truth 中的状态、边界和未决事项，不提升成熟度。",
                "core_message_derivation": {
                    "source_refs": structural_refs,
                    "supporting_statements": [str(unit.get("statement") or "") for unit in content_units],
                    "derivation": "等强度归纳语义节点对应的原子 Source Truth 记录。",
                    "introduced_relations": [],
                    "introduced_modalities": [],
                    "argument_node_ids": consumed_node_ids,
                },
                "source_refs": source_refs,
                "detail_refs": detail_refs,
                "boundary_refs": boundary_refs,
                "content_units": content_units,
                "content_relations": [
                    {
                        "subject": topic,
                        "objects": relation_objects or [core_message],
                        "relation": "contains",
                        "source_refs": structural_refs or source_refs[:1],
                    }
                ],
                "visual_intent_type": VISUAL_INTENT.get(semantic_role, "judgment_evidence"),
                "page_necessity": f"{topic}对应独立来源标题和语义命题，需要明确承载其业务判断与状态边界。",
            }
            if semantic_role == "boundary" or (boundary_refs and len(boundary_refs) == len(source_refs)):
                page["boundary_focus"] = True
                page["boundary_focus_reason"] = "本页来源全部属于边界或未决事项，边界本身就是页面主题。"
            pages.append(page)
            content_pages.append(page)
            chapter_content.append(page)
            if node in subsections:
                if merge_with_section:
                    dispositions.append(
                        {
                            "node_id": node_id,
                            "disposition": "merged_page",
                            "page_id": page_id,
                            "rationale": f"{topic}与父章节主张共同建立本章起始判断。",
                            "merge_reason": "父章节主张与首个子节点构成同一来源主题和同一支撑关系。",
                            "shared_page_topic": topic,
                        }
                    )
                else:
                    dispositions.append(
                        {
                            "node_id": node_id,
                            "disposition": "standalone_page",
                            "page_id": page_id,
                            "rationale": f"{topic}具有独立来源标题、语义命题和证据责任，先编译为独立候选页；仅在后续规划判断确认共享主题与主关系后才可合并。",
                        }
                    )
        topics = [str(page["topic_category"]) for page in chapter_content]
        page_ids = [str(page["page_id"]) for page in chapter_content]
        if chapter_content:
            chapter_missions.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_question": f"{chapter_title}需要回答哪些来源支持的业务问题？",
                    "mission": str(section.get("section_thesis") or f"说明{chapter_title}。"),
                    "topic_categories": topics,
                    "max_content_pages": len(chapter_content),
                }
            )
            chapter_orders.append(
                {
                    "chapter_id": chapter_id,
                    "ordering_principles": ["source_argument_sequence", "audience_question_progression"],
                    "ordered_topic_categories": topics,
                    "ordered_page_ids": page_ids,
                    "rationale": "按来源章节顺序承接语义节点；后续只对有共同主题和主关系的相邻候选页执行合并。",
                }
            )

    pages.append(
        {
            "page_id": f"p{len(pages) + 1:02d}",
            "sequence": len(pages) + 1,
            "page_type": "ending",
            "title": "交流与后续事项",
        }
    )
    for index, page in enumerate(content_pages):
        previous = content_pages[index - 1] if index > 0 else None
        following = content_pages[index + 1] if index + 1 < len(content_pages) else None
        page["transition_from_previous"] = (
            f"承接《{previous['title']}》形成的判断，进一步说明《{page['title']}》。"
            if previous
            else f"从本章问题进入《{page['title']}》的来源判断。"
        )
        page["transition_to_next"] = (
            f"本页判断完成后，下一页继续回答《{following['title']}》的业务问题。"
            if following
            else "本页完成正文论证，并将后续动作交给正式封底。"
        )

    semantics = dict(truth.get("document_semantics") or model.get("document_semantics") or {})
    thesis = str((model.get("document_thesis") or {}).get("statement") or semantics.get("primary_thesis") or "")
    payload = {
        "schema": "cyberppt.outline.v2",
        "material_type": str(semantics.get("document_role") or "正式材料"),
        "audience": "交流目标所述受众",
        "communication_goal": communication_goal.strip(),
        "communication_purpose": communication_goal.strip(),
        "decision_task": str(semantics.get("decision_intent") or communication_goal).strip(),
        "architecture_mode": "solution",
        "architecture_reason": "正式方案材料默认使用方案型结构；候选页按来源论证顺序编译，再执行一次合并与节奏判断。",
        "structure_principle": "source_logic_focused：保留来源论证顺序并局部压缩可合并候选页。",
        "title_style_mode": "formal_plain",
        "argument_contract_mode": "strict",
        "core_message_derivation_mode": "required",
        "topic_partition_mode": "required",
        "page_sequence_mode": "required",
        "argument_node_disposition_mode": "required",
        "page_content_unit_coverage_mode": "required",
        "editorial_control_mode": "required",
        "storyline_contract_mode": "required",
        "semantic_argument_model_mode": "required",
        "source_truth_mapping_mode": "consumption_manifest",
        "source_section_weights": {},
        "document_semantics": semantics,
        "narrative_thesis": thesis,
        "storyline": {
            "theme": thesis,
            "decision_destination": communication_goal.strip(),
            "story_arc": [str(item.get("section_thesis") or item.get("source_heading") or "") for item in sections],
            "chapter_missions": chapter_missions,
            "selection_rules": [
                "全部受保护语义节点进入候选页或明确合并处置",
                "P0/P1进入页面结构，P2保留为detail_refs",
                "只在共享页面主题和主关系成立时合并",
            ],
            "exclusion_rules": [
                "不把规划、建议或待确认事项提升为既成事实",
                "不为压缩页数而自动舍弃受保护来源事项",
            ],
            "page_rules": [
                "每页一个主题、一个核心判断和一个主关系",
                "来源状态、主体和业务特征必须保留",
            ],
            "pacing": {
                "min_total_pages": len(pages),
                "max_total_pages": len(pages),
                "content_pages": len(content_pages),
                "chapter_pages": sum(1 for page in pages if page.get("page_type") == "chapter"),
                "template_pages": sum(1 for page in pages if page.get("page_type") not in {"chapter", "content"}),
            },
        },
        "chapter_page_orders": chapter_orders,
        "argument_node_dispositions": dispositions,
        "pages": pages,
    }
    return _write_json(output.expanduser().resolve() if output else project / OUTLINE, payload)

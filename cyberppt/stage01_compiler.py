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
from cyberppt.source_argument_model import (
    load_model,
    node_index,
    validate_model,
    validate_projection_model,
)
from cyberppt.source_document_map import SOURCE_HEADING_TREE, SOURCE_REGISTRY, SOURCE_UNITS
from cyberppt.subtitle_policy import resolve_subtitle_policy


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
# Atomic items no longer redeclare evidence_role/claim_role independently of
# their target semantic node (Stage 00 authors it once, on the node); this
# derives the Source Truth evidence_role from the node's own argument_role.
ARGUMENT_ROLE_TO_EVIDENCE_ROLE = {
    "thesis": "judgment",
    "recommendation": "recommendation",
    "boundary": "boundary",
    "gap": "unresolved",
}
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
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return path


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _top_level_section_nodes(project: Path, model: dict[str, Any]) -> list[dict[str, Any]]:
    """Return section nodes whose source heading has no represented ancestor.

    ``section_nodes`` is a semantic collection, not a promise that every item
    is a chapter.  Some semantic models contain a lower source heading in that
    collection while retaining its ancestor as another section node.  The
    source heading tree is the authority for that parent/child relationship;
    do not infer hierarchy from the section node's declared level alone.
    """

    sections = _items(model.get("section_nodes"))
    heading_path = project / SOURCE_HEADING_TREE
    if not heading_path.is_file():
        return sections
    headings = _items(_read_json(heading_path).get("headings"))
    by_source_heading_id: dict[str, dict[str, Any]] = {}
    for heading in headings:
        for field in ("unit_id", "heading_id"):
            source_heading_id = str(heading.get(field) or "")
            if source_heading_id:
                by_source_heading_id[source_heading_id] = heading
    represented_ids = {
        str(section.get("source_heading_id") or "")
        for section in sections
        if str(section.get("source_heading_id") or "")
    }
    result: list[dict[str, Any]] = []
    for section in sections:
        source_heading_id = str(section.get("source_heading_id") or "")
        heading = by_source_heading_id.get(source_heading_id)
        path = _strings(heading.get("heading_path")) if heading else []
        represented_ancestor = False
        if path:
            for ancestor in headings:
                ancestor_ids = {
                    str(ancestor.get(field) or "")
                    for field in ("unit_id", "heading_id")
                }
                ancestor_path = _strings(ancestor.get("heading_path"))
                if (
                    represented_ids.intersection(ancestor_ids)
                    and len(ancestor_path) < len(path)
                    and path[: len(ancestor_path)] == ancestor_path
                ):
                    represented_ancestor = True
                    break
        if not represented_ancestor:
            result.append(section)
    return result


def _candidate_page_groups(
    project: Path,
    model: dict[str, Any],
    truth: dict[str, Any],
) -> list[dict[str, Any]]:
    """Project Source Truth coverage targets into source-ordered page groups.

    The semantic model contains two different hierarchies: source-section
    nodes and later page-consumer nodes.  The latter are the only nodes that
    may become candidate content pages.  In particular, a page-consumer node
    can be parented by a synthetic semantic root rather than by the section
    node that happens to carry the same source heading.  Walking only
    ``subsection_nodes`` below the selected section nodes therefore silently
    drops valid pages.  Source units provide the authoritative chapter path;
    Source Truth coverage targets provide the authoritative page inventory.
    """

    semantic_nodes = node_index(model)
    subsection_ids = {
        str(node.get("id") or "")
        for node in _items(model.get("subsection_nodes"))
        if str(node.get("id") or "")
    }
    records_by_node: dict[str, list[dict[str, Any]]] = {}
    records_by_id = {
        str(record.get("id") or ""): record
        for record in _items(truth.get("records"))
        if str(record.get("id") or "")
    }
    for record in records_by_id.values():
        if str(record.get("argument_duty") or "") == "metadata":
            continue
        for node_id in _strings(record.get("semantic_node_ids")):
            records_by_node.setdefault(node_id, []).append(record)

    target_order: list[str] = []
    for target in _items(truth.get("coverage_targets")):
        node_id = str(target.get("semantic_node_id") or "")
        if node_id and node_id not in target_order:
            target_order.append(node_id)
    # Keep the projection usable for hand-authored/minimal fixtures that do
    # not carry coverage_targets yet, while still requiring a real page
    # consumer and source records.
    if not target_order:
        target_order = [
            str(node.get("id") or "")
            for node in _items(model.get("subsection_nodes"))
            if str(node.get("id") or "")
        ]

    source_units = _source_units(project)
    groups: dict[str, dict[str, Any]] = {}
    ordered_groups: list[dict[str, Any]] = []
    for node_id in target_order:
        if node_id not in subsection_ids:
            continue
        node = semantic_nodes.get(node_id)
        if not isinstance(node, dict) or not str(node.get("primary_consumer") or "").strip():
            continue
        node_records = records_by_node.get(node_id, [])
        if not node_records:
            continue

        evidence_refs = _strings(node.get("evidence_refs"))
        record_refs = [
            ref
            for record in node_records
            for ref in _strings(record.get("source_unit_refs"))
        ]
        source_candidates = [
            source_units[ref]
            for ref in evidence_refs + record_refs
            if ref in source_units and isinstance(source_units[ref], dict)
        ]
        source_candidates.sort(key=lambda item: int(item.get("source_order") or 0))
        heading_path = _strings(source_candidates[0].get("heading_path")) if source_candidates else []
        chapter_title = heading_path[0] if heading_path else ""
        if not chapter_title:
            chapter_title = str(node.get("source_heading") or "").strip()
        if not chapter_title:
            chapter_title = "未命名章节"

        group = groups.get(chapter_title)
        if group is None:
            group = {
                "chapter_title": chapter_title,
                "nodes": [],
                "first_source_order": int(source_candidates[0].get("source_order") or 0)
                if source_candidates
                else len(ordered_groups),
                "source_group_order": len(ordered_groups),
            }
            groups[chapter_title] = group
            ordered_groups.append(group)
        group["nodes"].append(node)

    ordered_groups.sort(
        key=lambda item: (int(item["first_source_order"]), int(item["source_group_order"]))
    )
    return ordered_groups


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
    if locator.get("section_paragraph") not in (None, ""):
        result["section_paragraph"] = locator["section_paragraph"]
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
    projection_model = str(model.get("interpretation_contract_mode") or "").strip() == "projection"
    units = _source_units(project)
    required_content_unit_ids = {
        unit_id
        for unit_id, unit in units.items()
        if str(unit.get("kind") or "") != "heading"
    }
    if projection_model:
        model_issues = validate_projection_model(model, source_unit_ids=set(units))
    else:
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
            target_nodes = [nodes[node_id] for node_id in semantic_node_ids if node_id in nodes]
            primary_node = target_nodes[0] if target_nodes else {}
            node_argument_role = str(primary_node.get("argument_role") or "evidence").strip()
            evidence_role = str(
                atomic.get("evidence_role")
                or atomic.get("claim_role")
                or ("judgment" if projection_model else ARGUMENT_ROLE_TO_EVIDENCE_ROLE.get(node_argument_role, "fact"))
            ).strip()
            if evidence_role not in EVIDENCE_TYPE:
                evidence_role = "fact"
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
            importance = str(
                atomic.get("importance") or primary_node.get("argument_weight") or "detail"
            ).strip()
            semantic_status = str(atomic.get("status") or "unknown").strip()
            status = (
                "来源陈述"
                if projection_model and semantic_status in {"mixed", "unknown"}
                else STATUS.get(semantic_status, semantic_status or "待确认")
            )
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
                        # The atomic statement is already the authored,
                        # source-faithful proposition.  Re-expanding it to the
                        # whole source paragraph silently recombines sibling
                        # facts, recommendations, and boundaries that Stage 00
                        # deliberately split.
                        "text": statement,
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
                    "status": status,
                    "semantic_status": semantic_status,
                    "claim_role": evidence_role,
                    "semantic_argument_role": str(atomic.get("claim_role") or node_argument_role),
                    "argument_duty": str(atomic.get("argument_duty") or "detail"),
                    "argument_function": str(atomic.get("argument_function") or ""),
                    "decision_scope": str(atomic.get("decision_scope") or ""),
                    "decision_effect": str(atomic.get("decision_effect") or ""),
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
    if projection_model:
        # Keep the authority boundary visible in the derived artifact: strict
        # here describes the Source Truth record contract, not a promotion of
        # the upstream compatibility projection into Stage 00 authorship.
        payload["authority_mode"] = "projection_only"
    return _write_json(output.expanduser().resolve() if output else project / SOURCE_TRUTH, payload)


def _clean_title(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"^第[一二三四五六七八九十百\d]+章[、：:\s　]*", "", text)
    text = re.sub(r"^[一二三四五六七八九十百\d]+[、.．]\s*", "", text)
    return text or "业务事项"


def _content_unit_anchors(record: dict[str, Any], topic: str) -> list[str]:
    """Return short source-specific anchors that a human author can preserve.

    Stage 00 may retain long source slices as coverage anchors.  Those slices
    are appropriate for source traceability but make a Stage 01 prose contract
    impossible to satisfy: a faithful rewrite need not repeat an arbitrary
    100-character substring verbatim.  Prefer business clauses from semantic
    units and retain only short existing anchors as a fallback.
    """

    candidates: list[str] = []
    for unit in _items(record.get("semantic_units")):
        for clause in re.split(r"[，；。]", str(unit.get("text") or "")):
            # ``、`` normally separates members of one source-native business
            # enumeration; keep that clause intact.  A decision condition
            # introduced by “选择” is the narrow exception: its individual
            # conditions are useful short anchors, and are not claims created
            # by the compiler.
            fragments = (
                clause.split("、")
                if "选择" in clause
                else [clause]
            )
            for fragment in fragments:
                fragment = _audience_anchor_fragment(fragment)
                if (
                    4 <= len(fragment) <= 36
                    and not _is_nonvisible_anchor_fragment(fragment)
                    and fragment not in candidates
                ):
                    candidates.append(fragment)
    for anchor in _strings(record.get("coverage_anchors")):
        if (
            4 <= len(anchor) <= 36
            and not _is_nonvisible_anchor_fragment(anchor)
            and anchor not in candidates
        ):
            candidates.append(anchor)
    # A source sentence may introduce several background factors and then list
    # the actual decision conditions.  Preserve source order within each class,
    # but make complete, audience-actionable conditions available before their
    # lead-in so a short onscreen contract does not stop at a dangling premise.
    candidates.sort(key=lambda value: 0 if _is_decision_condition_anchor(value) else 1)
    if not candidates:
        candidates = [_clean_title(record.get("statement")), topic]
    return candidates[:2]


def _audience_anchor_fragment(value: str) -> str:
    """Keep the source-native condition when a list item has a lead-in verb.

    ``优先选择真实需求明确`` is a natural source clause, but its reusable
    visible fact is ``真实需求明确``.  Removing this small decision lead-in
    does not paraphrase or add a claim; it prevents a dangling instruction from
    becoming an onscreen label while retaining the original condition.
    """

    value = str(value or "").strip()
    return re.sub(r"^(?:.{0,12}?)?(?:优先)?选择", "", value).strip()


def _is_nonvisible_anchor_fragment(value: str) -> bool:
    """Exclude source-only scaffolding and classification boundaries.

    Phrases such as ``本节从……角度`` locate the author in the document; they
    do not name a business object, action, condition, or conclusion.  They may
    remain in full prose for traceability, but forcing them on screen produces
    truncated labels instead of audience-facing information.  The same applies
    to negative chapter-boundary clauses (for example, ``不构成……新服务类型``):
    these govern how to read a section, rather than what an audience needs to
    decide or do on the page.
    """

    return bool(
        re.match(r"^本(?:节|章|部分).{0,16}(?:从.+角度|主要从.+|以下)", value)
        or re.match(r"^对(?:前述|上述|本(?:节|章|部分)).{0,32}(?:排序|说明|阐释|界定)$", value)
        or re.match(r"^(?:不构成(?:与|为)|不|并非|非).{0,32}(?:类型|事项|内容|范围)?$", value)
        or re.match(r"^.{0,28}并列的新服务类型$", value)
    )


def _is_decision_condition_anchor(value: str) -> bool:
    """Recognize a complete, source-native condition in a decision list."""

    return bool(re.search(r"(?:明确|清晰|可验证|可执行|具备条件)", value))


def _page_content_units(
    page_id: str,
    records: list[dict[str, Any]],
    topic: str,
    *,
    visual_intent_type: str = "",
    argument_chain: object = None,
    expression_model_selection: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    structural_duties = {"premise", "driver", "consequence", "gap", "response", "boundary"}
    visible_argument_duties = structural_duties - {"boundary"}
    eligible = [
        record for record in records
        if str(record.get("argument_duty") or "") != "metadata"
    ]
    structural = [
        record for record in eligible
        if str(record.get("priority")) != "P2"
        or str(record.get("argument_duty") or "") in structural_duties
    ]
    details = [str(record.get("id")) for record in eligible if record not in structural]
    if not structural and eligible:
        structural = [eligible[0]]
        details = [str(record.get("id")) for record in eligible[1:]]

    selected_mapping = (
        expression_model_selection.get("source_mapping")
        if isinstance(expression_model_selection, dict)
        and expression_model_selection.get("fit") == "selected"
        and isinstance(expression_model_selection.get("source_mapping"), list)
        else []
    )
    record_by_id = {str(record.get("id") or ""): record for record in structural}
    model_groups: list[tuple[str, str, list[dict[str, Any]]]] = []
    model_record_ids: set[str] = set()
    for mapping in selected_mapping:
        if not isinstance(mapping, dict) or mapping.get("implicit") is True:
            continue
        slot = str(mapping.get("slot") or "").strip()
        grouped = [
            record_by_id[record_id]
            for record_id in _strings(mapping.get("source_refs"))
            if record_id in record_by_id
        ]
        if slot and grouped:
            model_groups.append((slot, "primary" if slot == "answer" else "supporting", grouped))
            model_record_ids.update(str(record.get("id") or "") for record in grouped)

    boundaries = [
        record
        for record in structural
        if str(record.get("claim_role") or "") in {"boundary", "unresolved"}
    ]
    ordinary = [record for record in structural if record not in boundaries]
    primary = [record for record in ordinary if str(record.get("priority")) == "P0"]
    supporting = [record for record in ordinary if record not in primary]
    if not primary and supporting:
        duty_rank = {"gap": 0, "driver": 1, "response": 2, "consequence": 3, "premise": 4}
        selected = min(
            supporting,
            key=lambda record: duty_rank.get(
                str(record.get("argument_duty") or ""), 9
            ),
        )
        primary = [selected]
        supporting = [record for record in supporting if record is not selected]

    groups: list[tuple[str, list[dict[str, Any]], str]] = []
    for slot, role, grouped in model_groups:
        groups.append((role, grouped, slot))
    # A semantic atomic item's argument duty is authored upstream from the
    # source's meaning.  Preserve consecutive records that carry the same
    # duty as one source-native content unit; do not pair unrelated P0 records
    # merely because they are adjacent in the source list.
    structural_runs: list[tuple[str, list[dict[str, Any]]]] = []
    for record in ordinary:
        if str(record.get("id") or "") in model_record_ids:
            continue
        duty = str(record.get("argument_duty") or "")
        if duty not in visible_argument_duties:
            continue
        if structural_runs and structural_runs[-1][0] == duty:
            structural_runs[-1][1].append(record)
        else:
            structural_runs.append((duty, [record]))
    structural_ids = {
        str(record.get("id") or "")
        for _duty, run in structural_runs
        for record in run
    }
    structural_primary_assigned = False
    for duty, run in structural_runs:
        role = "supporting"
        if duty in {"gap", "response"} and not structural_primary_assigned:
            role = "primary"
            structural_primary_assigned = True
        groups.append((role, run, ""))
    if structural_runs and not structural_primary_assigned:
        duty_rank = {"gap": 0, "driver": 1, "response": 2, "consequence": 3, "premise": 4}
        primary_index = min(
            range(len(groups)),
            key=lambda index: duty_rank.get(structural_runs[index][0], 9),
        )
        _role, run, slot = groups[primary_index + len(model_groups)]
        groups[primary_index + len(model_groups)] = ("primary", run, slot)
    consumed_ids = structural_ids | model_record_ids
    primary = [record for record in primary if str(record.get("id") or "") not in consumed_ids]
    supporting = [record for record in supporting if str(record.get("id") or "") not in consumed_ids]
    if primary:
        # Do not collapse an entire subsection into one giant "primary"
        # unit.  Two-record evidence packs retain a meaningful local chain
        # while avoiding the flat one-record-per-unit anti-pattern.
        if len(primary) <= 4:
            for index in range(0, len(primary), 2):
                groups.append(("primary" if index == 0 else "supporting", primary[index:index + 2], ""))
        else:
            groups.append(("primary", primary, ""))
    by_role: dict[str, list[dict[str, Any]]] = {}
    for record in supporting:
        by_role.setdefault(str(record.get("claim_role") or "fact"), []).append(record)
    for role_records in list(by_role.values())[:3]:
        groups.append(("supporting", role_records, ""))
    ungrouped_supporting = [
        record
        for role_records in list(by_role.values())[3:]
        for record in role_records
    ]
    details.extend(str(record.get("id")) for record in ungrouped_supporting)
    if boundaries:
        groups.append(("boundary", boundaries, ""))

    result: list[dict[str, Any]] = []
    for index, (role, grouped, model_slot) in enumerate(groups, start=1):
        anchors = list(dict.fromkeys(
            anchor
            for record in grouped
            for anchor in _content_unit_anchors(record, topic)
        ))
        if len(anchors) < 2:
            anchors = (anchors + [_clean_title(grouped[0].get("statement")), topic])[:2]
        statements = [
            str(record.get("statement") or "").strip()
            for record in grouped
            if str(record.get("statement") or "").strip()
        ]
        unit = {
                "unit_id": f"{page_id}-U{index:02d}",
                "statement": "；".join(statements),
                "source_refs": [str(record.get("id")) for record in grouped],
                "role": role,
                "importance": role,
                "full_prose_required": True,
                "coverage_anchors": anchors[:4],
                "argument_duties": list(dict.fromkeys(
                    str(record.get("argument_duty") or "detail") for record in grouped
                )),
                "onscreen_required": bool(model_slot) or role == "primary" or any(
                    str(record.get("argument_duty") or "") in visible_argument_duties
                    for record in grouped
                ),
                "onscreen_anchors": anchors[:2] if model_slot or any(
                    str(record.get("argument_duty") or "") in structural_duties
                    for record in grouped
                ) else anchors[:1],
                "topic_category": topic,
            }
        if model_slot:
            unit["model_slot"] = model_slot
        result.append(unit)
    if result and not any(item["onscreen_required"] for item in result):
        result[0]["onscreen_required"] = True
        result[0]["onscreen_anchors"] = result[0]["coverage_anchors"][:1]
    return result, list(dict.fromkeys(details))


def _onscreen_modules(
    page_id: str,
    records: list[dict[str, Any]],
    expression_model_selection: dict[str, Any] | None = None,
    *,
    visual_intent_type: str = "",
) -> list[dict[str, Any]]:
    """Derive source-bounded presentation candidates without merging facts.

    A direct visual module has one Source Truth record as its fact boundary.
    Expression-model mappings may put several records in one slot, but that
    does not authorize combining their objects, states, or results.

    The first overview record of a source-native architecture is a page
    judgment, not a peer body module: its component records carry the visual
    structure that expands it.  This keeps source traceability separate from
    visual hierarchy and prevents an overview from being repeated as a card.
    """

    slots_by_ref: dict[str, list[str]] = {}
    selected = (
        expression_model_selection.get("source_mapping")
        if isinstance(expression_model_selection, dict)
        and expression_model_selection.get("fit") == "selected"
        else []
    )
    for mapping in selected if isinstance(selected, list) else []:
        if not isinstance(mapping, dict) or mapping.get("implicit") is True:
            continue
        slot = str(mapping.get("slot") or "").strip()
        if not slot:
            continue
        for ref in _strings(mapping.get("source_refs")):
            slots_by_ref.setdefault(ref, []).append(slot)

    model_id = str((expression_model_selection or {}).get("model_id") or "")
    architecture_overview = (
        model_id == "source_native"
        and str(visual_intent_type or "") == "architecture"
    )
    modules: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        record_id = str(record.get("id") or "").strip()
        statement = str(record.get("statement") or "").strip()
        if not record_id or not statement:
            continue
        characteristics = _content_unit_anchors(record, "")
        is_overview = (
            architecture_overview
            and index == 1
            and any(marker in statement for marker in ("总体架构", "总体框架"))
        )
        is_deployment_detail = (
            architecture_overview
            and any(marker in statement for marker in ("平台部署", "部署根据服务对象"))
        )
        modules.append({
            "module_id": f"{page_id}-M{index:02d}",
            "display_title": characteristics[0] if characteristics else _clean_title(statement),
            "source_refs": [record_id],
            "model_slots": list(dict.fromkeys(slots_by_ref.get(record_id, []))),
            "derivation_mode": "direct",
            "presentation_role": (
                "lead" if is_overview else "boundary" if is_deployment_detail else "structure"
            ),
            "visible_layer": (
                "semantic" if is_overview else "notes" if is_deployment_detail else "body"
            ),
            "allowed_visible_claim": statement,
            "required_characteristics": characteristics,
        })
    return modules


def _preserve_authored_module_decisions(
    candidates: list[dict[str, Any]],
    authored: object,
) -> list[dict[str, Any]]:
    """Keep author-edited display hierarchy when refreshing derived evidence."""

    authored_by_ref = {
        tuple(_strings(item.get("source_refs"))): item
        for item in _items(authored)
        if len(_strings(item.get("source_refs"))) == 1
    }
    for candidate in candidates:
        prior = authored_by_ref.get(tuple(_strings(candidate.get("source_refs"))))
        if not prior:
            continue
        prior_title = str(prior.get("display_title") or "").strip()
        candidate_title = str(candidate.get("display_title") or "").strip()
        if prior_title and prior_title != candidate_title:
            candidate["display_title"] = prior_title
            # A changed title is evidence of an author-made presentation
            # decision, so retain its declared visual role as well.
            for field in ("presentation_role", "visible_layer"):
                if candidate.get("presentation_role") == "lead":
                    # Lead facts are semantic thesis by default.  A short
                    # audience subtitle remains an independent author field.
                    continue
                value = prior.get(field)
                if isinstance(value, str) and value.strip():
                    candidate[field] = value.strip()
            continue
        for field in ("display_title",):
            value = prior.get(field)
            if isinstance(value, str) and value.strip():
                candidate[field] = value.strip()
    return candidates


def refresh_outline_content_units(
    project: Path,
    outline_path: Path | None = None,
    source_truth_path: Path | None = None,
    page_id: str | None = None,
) -> Path:
    """Refresh derived content units without changing professional Outline decisions."""

    project = project.expanduser().resolve()
    target = (outline_path or project / "workbench/stages/01-analysis/outline.json").expanduser().resolve()
    truth_target = (source_truth_path or project / SOURCE_TRUTH).expanduser().resolve()
    outline = _read_json(target)
    truth = _read_json(truth_target)
    records = {
        str(record.get("id") or ""): record
        for record in _items(truth.get("records"))
        if str(record.get("id") or "")
    }
    for page in _items(outline.get("pages")):
        if str(page.get("page_type") or "") != "content":
            continue
        if page_id and str(page.get("page_id") or "") != page_id:
            continue
        page_records = [
            records[record_id]
            for record_id in _strings(page.get("source_refs"))
            if record_id in records
        ]
        if not page_records:
            continue
        units, details = _page_content_units(
            str(page.get("page_id") or ""), page_records,
            str(page.get("topic_category") or page.get("title") or ""),
            visual_intent_type=str(page.get("visual_intent_type") or ""),
            argument_chain=page.get("argument_chain"),
            expression_model_selection=page.get("expression_model_selection"),
        )
        page["content_units"] = units
        page["detail_refs"] = details
        candidates = _onscreen_modules(
            str(page.get("page_id") or ""),
            page_records,
            page.get("expression_model_selection")
            if isinstance(page.get("expression_model_selection"), dict)
            else None,
            visual_intent_type=str(page.get("visual_intent_type") or ""),
        )
        page["onscreen_modules"] = _preserve_authored_module_decisions(
            candidates, page.get("onscreen_modules"),
        )
        existing_policy = page.get("subtitle_policy")
        existing_subtitle = str(page.get("subtitle") or "").strip()
        if not (
            isinstance(existing_policy, dict)
            and str(existing_policy.get("mode") or "") == "authored"
        ):
            policy = (
                {
                    "mode": "authored",
                    "subtitle": existing_subtitle,
                    "rationale": "保留刷新前已有的作者层副标题。",
                    "source_refs": _strings(page.get("source_refs")),
                    "derived_from": ["author"],
                }
                if existing_subtitle else resolve_subtitle_policy(
                    core_message=str(page.get("core_message") or ""),
                    visual_intent_type=str(page.get("visual_intent_type") or ""),
                    onscreen_expression_form=str(page.get("onscreen_expression_form") or ""),
                    onscreen_modules=page["onscreen_modules"],
                    content_units=units,
                )
            )
            page["subtitle_policy"] = policy
            if policy["mode"] in {"generated", "authored"}:
                page["subtitle"] = str(policy["subtitle"])
            else:
                page.pop("subtitle", None)
        page["source_grounding_mode"] = "required"
    target.write_text(json.dumps(outline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return target


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
    chapter_groups = _candidate_page_groups(project, model, truth)
    page_nodes = [
        node
        for group in chapter_groups
        for node in group["nodes"]
    ]
    page_node_ids = {str(node.get("id") or "") for node in page_nodes}
    support_nodes_by_page: dict[str, list[dict[str, Any]]] = {}
    page_node_order = {
        str(node.get("id") or ""): index
        for index, node in enumerate(page_nodes)
    }
    page_node_record_ids = {
        str(node.get("id") or ""): {
            str(record.get("id") or "")
            for record in record_by_node.get(str(node.get("id") or ""), [])
            if str(record.get("id") or "")
        }
        for node in page_nodes
    }
    for support_node in _items(model.get("subsection_nodes")):
        support_id = str(support_node.get("id") or "")
        if not support_id or support_id in page_node_ids:
            continue
        support_records = {
            str(record.get("id") or "")
            for record in record_by_node.get(support_id, [])
            if str(record.get("id") or "")
        }
        if not support_records:
            continue
        support_title = _clean_title(support_node.get("source_heading"))
        candidates = []
        for page_node in page_nodes:
            page_id = str(page_node.get("id") or "")
            overlap = len(support_records & page_node_record_ids.get(page_id, set()))
            if overlap:
                candidates.append(
                    (
                        support_title == _clean_title(page_node.get("source_heading")),
                        overlap,
                        -page_node_order[page_id],
                        page_id,
                    )
                )
        if not candidates:
            continue
        target_page_node_id = max(candidates)[-1]
        support_nodes_by_page.setdefault(target_page_node_id, []).append(support_node)

    pages: list[dict[str, Any]] = []
    pages.append({"page_id": "p01", "sequence": 1, "page_type": "cover", "title": _clean_title((model.get("document_semantics") or {}).get("subject_of_report"))})
    pages.append({"page_id": "p02", "sequence": 2, "page_type": "agenda", "title": "目录"})
    dispositions: list[dict[str, Any]] = []
    chapter_missions: list[dict[str, Any]] = []
    chapter_orders: list[dict[str, Any]] = []
    content_pages: list[dict[str, Any]] = []

    for section_index, chapter_group in enumerate(chapter_groups, start=1):
        chapter_id = f"C{section_index}"
        chapter_title = str(chapter_group["chapter_title"])
        pages.append(
            {
                "page_id": f"p{len(pages) + 1:02d}",
                "sequence": len(pages) + 1,
                "page_type": "chapter",
                "chapter_id": chapter_id,
                "title": chapter_title,
            }
        )
        nodes = list(chapter_group["nodes"])
        chapter_content: list[dict[str, Any]] = []
        for node in nodes:
            node_id = str(node.get("id") or "")
            primary_node_id = node_id
            consumed_node_ids = [node_id]
            evidence_node_ids = [
                str(support.get("id") or "")
                for support in support_nodes_by_page.get(node_id, [])
                if str(support.get("id") or "")
            ]
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
            if not node_records:
                continue
            content_units, detail_refs = _page_content_units(page_id, node_records, topic)
            source_refs = [
                str(record.get("id"))
                for record in node_records
                if str(record.get("argument_duty") or "") != "metadata"
            ]
            # A candidate page message is a source projection, not an author
            # judgment. Project every bound content unit so an incomplete
            # semantic thesis cannot hide source records already assigned to
            # this page.
            source_projected_statements = [
                str(unit.get("statement") or "").strip()
                for unit in content_units
                if str(unit.get("statement") or "").strip()
            ]
            core_message = "；".join(source_projected_statements)
            if not core_message:
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
            core_derivation_refs = [
                ref for ref in structural_refs if ref not in set(boundary_refs)
            ]
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
                "page_mission": "",
                "page_job": "",
                "core_message": core_message,
                "audience_question": "",
                "business_question": "",
                "topic_category": topic,
                "must_not_include": [],
                "split_risk": "",
                "split_risk_reason": "",
                "new_value_vs_previous": "",
                "reserved_for_later": "",
                "storyline_role": "",
                "transition_from_previous": "",
                "transition_to_next": "",
                "page_order_reason": "",
                "argument_role": page_role,
                "allowed_claim_roles": sorted({str(record.get("claim_role") or "fact") for record in node_records}),
                "forbidden_claim_roles": [],
                "prerequisite_pages": [chapter_content[-1]["page_id"]] if chapter_content else [],
                "main_claim_status": "proposed" if boundary_refs else "confirmed",
                "primary_argument_node_id": primary_node_id,
                "source_argument_node_ids": consumed_node_ids,
                "source_evidence_node_ids": evidence_node_ids,
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
                    "source_refs": core_derivation_refs,
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
                "page_necessity": "",
                # These fields deliberately remain empty in the deterministic
                # candidate draft.  They are editorial decisions and must be
                # authored from the communication goal, adjacent pages, and
                # evidence duties before the Outline can pass its formal gate.
                "non_substitutable_value": "",
                "argument_chain": [],
                "evidence_roles": [],
                "excluded_from_onscreen": [],
            }
            candidate_modules = _onscreen_modules(
                page_id,
                node_records,
                visual_intent_type=str(page["visual_intent_type"]),
            )
            page["onscreen_modules"] = candidate_modules
            subtitle_policy = resolve_subtitle_policy(
                core_message=core_message,
                visual_intent_type=str(page["visual_intent_type"]),
                onscreen_expression_form="",
                onscreen_modules=candidate_modules,
                content_units=content_units,
            )
            page["subtitle_policy"] = subtitle_policy
            if subtitle_policy["mode"] == "generated":
                page["subtitle"] = str(subtitle_policy["subtitle"])
            if semantic_role == "boundary" or (boundary_refs and len(boundary_refs) == len(source_refs)):
                page["boundary_focus"] = True
                page["boundary_focus_reason"] = "本页来源全部属于边界或未决事项，边界本身就是页面主题。"
                page["core_message_derivation"]["source_refs"] = structural_refs
            pages.append(page)
            content_pages.append(page)
            chapter_content.append(page)
            dispositions.append(
                {
                    "node_id": node_id,
                    "disposition": "standalone_page",
                    "page_id": page_id,
                    "rationale": f"{topic}具有独立来源标题、语义命题和证据责任，先编译为独立候选页；仅在后续规划判断确认共享主题与主关系后才可合并。",
                }
            )
            for support_node in support_nodes_by_page.get(node_id, []):
                support_id = str(support_node.get("id") or "")
                dispositions.append(
                    {
                        "node_id": support_id,
                        "disposition": "merged_page",
                        "page_id": page_id,
                        "rationale": f"{support_node.get('source_heading') or support_id}与{topic}共享来源标题和证据范围，作为支撑语义节点合并承载；页面主论点仍由 {node_id} 承担。",
                        "merge_reason": "同一来源事项已由更具体的页面承载节点拆分表达，保留本节点作为支撑语义而不重复成页。",
                        "shared_page_topic": topic,
                        "cross_chapter_reason": "该节点是同一来源事项的支撑语义投影，保留在对应页面的证据节点字段中，不另造页面或改变其来源章节。",
                    }
                )
        if not chapter_content:
            pages.pop()
            continue
        topics = [str(page["topic_category"]) for page in chapter_content]
        page_ids = [str(page["page_id"]) for page in chapter_content]
        if chapter_content:
            chapter_missions.append(
                {
                    "chapter_id": chapter_id,
                    "chapter_question": "",
                    "mission": "",
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
    semantics = dict(truth.get("document_semantics") or model.get("document_semantics") or {})
    thesis = str((model.get("document_thesis") or {}).get("statement") or semantics.get("primary_thesis") or "")
    payload = {
        "schema": "cyberppt.outline.v2",
        "material_type": str(semantics.get("document_role") or "正式材料"),
        "audience": "",
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
        "editorial_authoring_mode": "author_driven",
        "editorial_authoring_status": "mechanical_draft",
        "storyline_contract_mode": "required",
        "semantic_argument_model_mode": "required",
        # This compiler never backfills page_refs into Source Truth records
        # (page-to-evidence mapping lives only in each page's content_units);
        # "frozen" tells the argument-flow audit to enforce that invariant.
        "source_truth_mapping_mode": "frozen",
        "source_section_weights": {},
        "document_semantics": semantics,
        "narrative_thesis": thesis,
        "storyline": {
            "theme": thesis,
            "decision_destination": communication_goal.strip(),
            "story_arc": [str(item["chapter_title"]) for item in chapter_groups],
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

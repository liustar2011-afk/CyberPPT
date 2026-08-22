from __future__ import annotations

import re
from typing import Any

from .ids import stable_id
from .mappings import FACT_TYPE_TO_EVIDENCE_TYPE, FACT_TYPE_TO_CLAIM_ROLE, IMPORTANCE_TO_PRIORITY, normalize_importance

def _flatten_sections(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    def visit(node: dict[str, Any], path: list[str]) -> None:
        current_path = [*path, str(node.get("title") or "").strip()]
        item = dict(node)
        item["heading_path"] = current_path
        result.append(item)
        for child in node.get("children") or []:
            if isinstance(child, dict):
                visit(child, current_path)
    for node in nodes:
        if isinstance(node, dict):
            visit(node, [])
    return result

def _anchors(statement: str, heading_path: list[str]) -> list[str]:
    """Extract readable anchors, including Markdown table cells.

    Tables arrive from source conversion as Markdown.  Treating a row as one
    pipe-delimited sentence creates punctuation artefacts and loses the cell
    boundary that tells an author what must survive on screen.
    """

    raw = str(statement)
    table_cells: list[str] = []
    prose_lines: list[str] = []
    for line in raw.splitlines() or [raw]:
        stripped = line.strip()
        if "|" in stripped:
            cells = [re.sub(r"\*+", "", cell).strip() for cell in stripped.strip("|").split("|")]
            # Markdown alignment rows have no audience-facing business text.
            if cells and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells if cell):
                continue
            table_cells.extend(cell for cell in cells if cell)
        else:
            prose_lines.append(stripped)
    statement = " ".join(prose_lines).strip()
    statement = re.sub(r"\*+", "", statement)
    statement = re.sub(r"^[\s•·-]+", "", statement)
    statement = " ".join(statement.split()).strip()
    anchors: list[str] = []
    for cell in table_cells:
        cell = re.sub(r"^[\s•·-]+", "", cell).strip(" ，。；;：:")
        if cell and cell not in anchors:
            anchors.append(cell)
        if len(anchors) >= 2:
            return anchors[:2]
    if statement:
        chunks = [part.strip(" ，。；;：:") for part in statement.replace("；", "，").replace("。", "，").split("，") if part.strip()]
        for chunk in chunks:
            if chunk and chunk not in anchors:
                anchors.append(chunk)
            if len(anchors) >= 2:
                break
    if len(anchors) < 2 and heading_path:
        heading = str(heading_path[-1]).strip()
        if heading and heading not in anchors:
            anchors.append(heading)
    if len(anchors) < 2 and statement and statement not in anchors:
        anchors.append(statement)
    if len(anchors) < 2 and statement:
        # Short source labels such as a table heading may have no punctuation.
        # Keep two non-overlapping source-derived fragments so downstream
        # coverage can verify the label without injecting a generic fallback.
        compact = re.sub(r"[，。；;：:\s]", "", statement)
        if len(compact) >= 6:
            for fragment in (compact[:4], compact[-4:]):
                if fragment and fragment not in anchors:
                    anchors.append(fragment)
                if len(anchors) >= 2:
                    break
    return anchors[:2] or ["source-projection", "source-projection"]

def _fact_refs_from_evidence(evidence: dict[str, Any], relation_by_id: dict[str, dict[str, Any]], arg_by_id: dict[str, dict[str, Any]]) -> set[str]:
    result = {str(item) for item in evidence.get("normalized_fact_ids") or []}
    for rel_id in evidence.get("relation_ids") or []:
        relation = relation_by_id.get(str(rel_id), {})
        result.update(str(item) for item in relation.get("normalized_fact_ids") or [])
    for arg_id in evidence.get("argument_node_ids") or []:
        node = arg_by_id.get(str(arg_id), {})
        result.update(str(item) for item in node.get("normalized_fact_ids") or [])
    return result

def _project_source_units(structure: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str], str]:
    source = structure.get("source") or {}
    original_source_file = str(source.get("source_file") or "")
    source_path = str(structure.get("input_markdown") or original_source_file or "source.md")
    source_key = str(structure.get("markdown_sha256") or source_path)
    source_id = stable_id("SRC", source_key, source_path, length=12)
    units: list[dict[str, Any]] = []
    block_map: dict[str, str] = {}
    section_map: dict[str, str] = {}

    flat_sections = _flatten_sections(structure.get("outline") or [])
    section_by_id = {str(item.get("section_id")): item for item in flat_sections if item.get("section_id")}
    for section in flat_sections:
        section_id = str(section.get("section_id"))
        unit_id = stable_id("SU", source_key, "heading", section_id)
        section_map[section_id] = unit_id
        units.append({
            "schema": "cyberppt.source_unit.v1",
            "unit_id": unit_id,
            "source_id": source_id,
            "source_path": source_path,
            "kind": "heading",
            "source_order": int(section.get("line") or len(units) + 1),
            "heading_id": stable_id("H", source_key, section_id, length=12),
            "heading_path": section.get("heading_path") or [section.get("title")],
            "outline_level": int(section.get("level") or 1),
            "locator": {"line_start": int(section.get("line") or 1), "line_end": int(section.get("line") or 1)},
            "text_anchor": str(section.get("title") or "")[:48],
            "text": str(section.get("title") or ""),
            "metadata": {"projection_only": True, "authority_type": "section", "original_source_file": original_source_file, "conversion_engine": source.get("conversion_engine")},
            "authority_ref": section_id,
        })

    for block in structure.get("blocks") or []:
        if not isinstance(block, dict) or not block.get("block_id"):
            continue
        block_id = str(block["block_id"])
        unit_id = stable_id("SU", source_key, "block", block_id)
        block_map[block_id] = unit_id
        section = section_by_id.get(str(block.get("section_id") or ""), {})
        kind = str(block.get("type") or "paragraph")
        if kind == "list_item":
            kind = "paragraph"
        units.append({
            "schema": "cyberppt.source_unit.v1",
            "unit_id": unit_id,
            "source_id": source_id,
            "source_path": source_path,
            "kind": kind,
            "source_order": int(block.get("line_start") or len(units) + 1),
            "heading_id": stable_id("H", source_key, str(block.get("section_id")), length=12) if block.get("section_id") else None,
            "heading_path": list(block.get("heading_path") or section.get("heading_path") or []),
            "locator": {"line_start": int(block.get("line_start") or 1), "line_end": int(block.get("line_end") or block.get("line_start") or 1)},
            "text_anchor": str(block.get("text") or "").replace("\n", " ")[:48],
            "text": str(block.get("text") or ""),
            "metadata": {"projection_only": True, "authority_type": "block", "original_block_type": block.get("type"), "original_source_file": original_source_file, "conversion_engine": source.get("conversion_engine")},
            "authority_ref": block_id,
        })
    units.sort(key=lambda item: (int(item.get("source_order") or 0), 0 if item.get("kind") == "heading" else 1, str(item.get("unit_id"))))
    return units, block_map, section_map, source_id

def _page_fact_usage(page_plan: dict[str, Any], relation_by_id: dict[str, dict[str, Any]], arg_by_id: dict[str, dict[str, Any]]) -> dict[str, str]:
    rank = {"low": 0, "medium": 1, "high": 2}
    usage: dict[str, str] = {}
    for page in page_plan.get("pages") or []:
        if not isinstance(page, dict) or page.get("page_type") != "content":
            continue
        importance = normalize_importance(page.get("importance"))
        evidence = page.get("evidence") if isinstance(page.get("evidence"), dict) else {}
        for fact_id in evidence.get("normalized_fact_ids") or []:
            fact_id = str(fact_id)
            prior = usage.get(fact_id)
            if prior is None or rank.get(importance, 0) > rank.get(prior, 0):
                usage[fact_id] = importance
    return usage

def _project_source_truth(payloads: dict[str, dict[str, Any]], units: list[dict[str, Any]], block_map: dict[str, str], source_id: str) -> tuple[dict[str, Any], dict[str, str]]:
    normalized = payloads["normalized"]
    relation_by_id = {str(item.get("relation_id")): item for item in payloads["relations"].get("relations") or [] if isinstance(item, dict)}
    arg_by_id = {str(item.get("node_id")): item for group in (payloads["argument"].get("source_chain") or [], payloads["argument"].get("reconstructed_chain") or []) for item in group if isinstance(item, dict)}
    usage = _page_fact_usage(payloads["page_plan"], relation_by_id, arg_by_id)
    unit_by_id = {str(item.get("unit_id")): item for item in units}
    factbase = {str(item.get("fact_id")): item for item in payloads["fact_base"].get("entries") or [] if isinstance(item, dict)}
    records: list[dict[str, Any]] = []
    nf_to_st: dict[str, str] = {}
    for index, fact in enumerate(payloads["normalized"].get("facts") or [], start=1):
        if not isinstance(fact, dict):
            continue
        nf_id = str(fact.get("normalized_fact_id") or "")
        st_id = f"ST{index:04d}"
        nf_to_st[nf_id] = st_id
        evidence = fact.get("evidence") if isinstance(fact.get("evidence"), list) else []
        source_unit_refs: list[str] = []
        source_lines: list[tuple[int, int]] = []
        heading_path: list[str] = []
        for item in evidence:
            if not isinstance(item, dict):
                continue
            block_id = str(item.get("block_id") or "")
            unit_id = block_map.get(block_id)
            if unit_id and unit_id not in source_unit_refs:
                source_unit_refs.append(unit_id)
                unit = unit_by_id.get(unit_id, {})
                if not heading_path:
                    heading_path = list(unit.get("heading_path") or [])
            if item.get("line_start") is not None:
                source_lines.append((int(item.get("line_start")), int(item.get("line_end") or item.get("line_start"))))
        if not source_unit_refs:
            for source_assertion_id in fact.get("source_assertion_ids") or []:
                base = factbase.get(str(source_assertion_id), {})
                ref = base.get("source_ref") if isinstance(base.get("source_ref"), dict) else {}
                block_id = str(ref.get("block_id") or "")
                if block_id in block_map:
                    source_unit_refs.append(block_map[block_id])
                    heading_path = list(base.get("heading_path") or [])
                    if ref.get("line_start") is not None:
                        source_lines.append((int(ref["line_start"]), int(ref.get("line_end") or ref["line_start"])))
        line_start = min((value[0] for value in source_lines), default=1)
        line_end = max((value[1] for value in source_lines), default=line_start)
        fact_type = str(fact.get("fact_type") or "fact")
        evidence_type = FACT_TYPE_TO_EVIDENCE_TYPE.get(fact_type, "J")
        claim_role = FACT_TYPE_TO_CLAIM_ROLE.get(fact_type, "judgment")
        statement = str(fact.get("statement") or "").strip()
        importance = usage.get(nf_id, "low")
        record = {
            "id": st_id,
            "authority_ref": nf_id,
            "type": evidence_type,
            "priority": IMPORTANCE_TO_PRIORITY.get(importance, "P2"),
            "statement": statement,
            "source_locator": {
                "source_id": source_id,
                "file": str(payloads["structure"].get("input_markdown") or (payloads["structure"].get("source") or {}).get("source_file") or "source.md"),
                "original_source_file": str((payloads["structure"].get("source") or {}).get("source_file") or ""),
                "section": " / ".join(heading_path) or "全文",
                "paragraph": line_start,
                "line_start": line_start,
                "line_end": line_end,
                "projection_locator_mode": "markdown_line",
            },
            "source_unit_refs": source_unit_refs,
            "semantic_node_ids": [],
            "claim_origin": "source_explicit" if str(fact.get("normalization")) == "verbatim" else "source_implied",
            "status": "来源陈述",
            "semantic_status": "unverified",
            "verification_status": str(fact.get("verification_status") or "unverified"),
            "claim_role": claim_role,
            "semantic_argument_role": claim_role,
            "argument_duty": "detail",
            "semantic_units": [{"text": statement, "claim_role": claim_role, "source_unit_refs": source_unit_refs}],
            "coverage_anchors": _anchors(statement, heading_path),
            "actors": [], "conditions": [], "numeric_facts": [],
            "allowed_page_roles": [], "forbidden_page_roles": [],
            "depends_on": [], "supports": [], "page_refs": [],
            "quote": statement,
            "projection_only": True,
        }
        records.append(record)
    source = payloads["structure"].get("source") or {}
    truth = {
        "schema": "cyberppt.source_truth.v1",
        "argument_contract_mode": "projection",
        "document_semantics_mode": "projection",
        "projection_mode": "source_material_foundation_v0.5",
        "authority_mode": "projection_only",
        "project": {"title": str(payloads["deck"].get("deck_strategy", {}).get("working_title") or "PPT"), "material_type": str(payloads["deck"].get("deck_strategy", {}).get("deck_type") or "formal"), "audience": str(payloads["deck"].get("task_understanding", {}).get("audience") or "")},
        "document_semantics": {},
        "sources": [{"id": source_id, "file": str(payloads["structure"].get("input_markdown") or source.get("source_file") or "source.md"), "original_source_file": str(source.get("source_file") or ""), "role": "primary", "projection_only": True}],
        "coverage_targets": [],
        "records": records,
        "conclusions": [{"id": "C001", "statement": str(payloads["deck"].get("deck_strategy", {}).get("deck_thesis") or ""), "source_refs": [item["id"] for item in records if item["priority"] == "P0"] or [item["id"] for item in records[:1]]}],
        "pages": [],
        "retry": {"attempt": 1, "max_attempts": 3, "strategy": "projection_only"},
        "intentional_source_unit_omissions": [],
    }
    return truth, nf_to_st

def _source_registry(structure: dict[str, Any], source_id: str) -> dict[str, Any]:
    source = structure.get("source") or {}
    return {"schema": "cyberppt.source_registry.v1", "authority_mode": "projection_only", "sources": [{"source_id": source_id, "path": str(structure.get("input_markdown") or source.get("source_file") or "source.md"), "sha256": str(structure.get("markdown_sha256") or ""), "role": "primary", "original_source_file": str(source.get("source_file") or ""), "source_format": source.get("source_format"), "conversion_engine": source.get("conversion_engine"), "locator_basis": "derived_markdown", "projection_only": True}]}

def _heading_tree(structure: dict[str, Any], source_id: str, section_map: dict[str, str]) -> dict[str, Any]:
    headings = []
    for section in _flatten_sections(structure.get("outline") or []):
        sec_id = str(section.get("section_id") or "")
        headings.append({"heading_id": stable_id("H", str(structure.get("markdown_sha256") or ""), sec_id, length=12), "source_id": source_id, "source_path": str(structure.get("input_markdown") or (structure.get("source") or {}).get("source_file") or "source.md"), "original_source_file": str((structure.get("source") or {}).get("source_file") or ""), "title": str(section.get("title") or ""), "level": int(section.get("level") or 1), "source_order": int(section.get("line") or 1), "unit_id": section_map.get(sec_id), "heading_path": list(section.get("heading_path") or [section.get("title")]), "authority_ref": sec_id, "projection_only": True})
    return {"schema": "cyberppt.source_heading_tree.v1", "authority_mode": "projection_only", "headings": headings}

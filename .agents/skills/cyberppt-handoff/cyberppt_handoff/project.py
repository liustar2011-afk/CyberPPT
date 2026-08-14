from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .io import json_sha256, load_inputs
from .mappings import ARGUMENT_DUTY
from .source_projection import _project_source_units, _project_source_truth, _source_registry, _heading_tree
from .semantic_projection import _project_semantic_model
from .outline_projection import _project_outline
from .render_projection import _semantic_review_markdown, _outline_review_markdown

def build_projection(foundation_dir: Path | str, semantic_dir: Path | str, outline_dir: Path | str) -> dict[str, Any]:
    payloads = load_inputs(Path(foundation_dir), Path(semantic_dir), Path(outline_dir))
    units, block_map, section_map, source_id = _project_source_units(payloads["structure"])
    source_truth, nf_to_st = _project_source_truth(payloads, units, block_map, source_id)
    semantic_model = _project_semantic_model(payloads, nf_to_st, block_map, section_map)
    # add semantic-node IDs to Source Truth records mechanically from argument fact coverage
    arg_by_fact: dict[str, list[str]] = defaultdict(list)
    for node in payloads["argument"].get("reconstructed_chain") or []:
        if isinstance(node, dict):
            for nf in node.get("normalized_fact_ids") or []:
                arg_by_fact[str(nf)].append(str(node.get("node_id")))
    for record in source_truth["records"]:
        record["semantic_node_ids"] = arg_by_fact.get(str(record.get("authority_ref")), [])
        node_roles = [str(next((node.get("role") for node in payloads["argument"].get("reconstructed_chain") or [] if isinstance(node, dict) and str(node.get("node_id")) == node_id), "other")) for node_id in record["semantic_node_ids"]]
        if node_roles:
            record["argument_duty"] = ARGUMENT_DUTY.get(node_roles[0], "detail")
    source_truth["document_semantics"] = semantic_model["document_semantics"]
    source_truth["coverage_targets"] = [{"id": f"T{index:03d}", "kind": "semantic_node", "label": str(node.get("source_heading") or node.get("id")), "semantic_node_id": str(node.get("id")), "priority": {"core":"P0","supporting":"P1","detail":"P2","constraint":"P1"}.get(str(node.get("argument_weight")), "P2"), "required": True, "record_refs": [record["id"] for record in source_truth["records"] if str(node.get("id")) in record.get("semantic_node_ids", [])]} for index, node in enumerate(semantic_model.get("subsection_nodes") or [], start=1)]
    outline, page_map = _project_outline(payloads, source_truth, semantic_model, nf_to_st)
    authority_map = {
        "schema": "source-material-foundation.cyberppt_authority_map.v1", "authority_mode": "projection_only",
        "authoritative_inputs": {name: json_sha256(payloads[name]) for name in ("structure", "fact_base", "normalized", "concepts", "relations", "argument", "deck", "page_plan")},
        "block_to_source_unit": block_map, "section_to_heading_unit": section_map, "normalized_fact_to_source_truth": nf_to_st,
        "page_to_cyberppt_page": page_map,
        "page_direct_normalized_facts": {str(page.get("page_id")): [str(value) for value in ((page.get("evidence") or {}).get("normalized_fact_ids") or [])] for page in payloads["page_plan"].get("pages") or [] if isinstance(page, dict) and page.get("page_type") == "content"},
        "page_direct_source_truth": {str(page.get("page_id")): [nf_to_st[str(value)] for value in ((page.get("evidence") or {}).get("normalized_fact_ids") or []) if str(value) in nf_to_st] for page in payloads["page_plan"].get("pages") or [] if isinstance(page, dict) and page.get("page_type") == "content"},
        "relation_to_projected_relation": {str(item.get("relation_id")): str(item.get("relation_id")) for item in payloads["relations"].get("relations") or [] if isinstance(item, dict)},
        "argument_node_to_semantic_node": {str(item.get("node_id")): str(item.get("node_id")) for item in payloads["argument"].get("reconstructed_chain") or [] if isinstance(item, dict)},
    }
    report = {
        "schema": "source-material-foundation.cyberppt_handoff_report.v1", "status": "prepared", "authority_mode": "projection_only",
        "counts": {"source_units": len(units), "source_truth_records": len(source_truth["records"]), "semantic_nodes": len(semantic_model.get("section_nodes") or []) + len(semantic_model.get("subsection_nodes") or []), "semantic_relations": len(semantic_model.get("argument_relations") or []), "pages": len(outline.get("pages") or [])},
        "runtime_validation": {"status": "not_run", "reason": "CyberPPT runtime was not supplied to this adapter run."},
        "warnings": ["CyberPPT artifacts are compatibility projections; authoritative reasoning remains in Source Material Foundation layers 2–4."],
    }
    return {
        "source_registry": _source_registry(payloads["structure"], source_id), "source_units": units, "source_heading_tree": _heading_tree(payloads["structure"], source_id, section_map),
        "semantic_argument_model": semantic_model, "semantic_understanding_markdown": _semantic_review_markdown(semantic_model),
        "source_truth": source_truth, "outline": outline, "outline_review_markdown": _outline_review_markdown(outline),
        "authority_map": authority_map, "report": report,
    }

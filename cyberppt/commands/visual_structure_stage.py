"""Register and gate the visual-structure-designer stage."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cyberppt.artifact_ledger import append_artifacts, write_json_atomic
from cyberppt.page_artifact_spec import is_text_dense
from cyberppt.onscreen_expression import expression_constraints, expression_constraints_sha256
from cyberppt.semantic_digest import script_semantic_digest
from cyberppt.visual_structure_contract import (
    audit_visual_design_package,
    audit_visual_deck_rhythm,
    prompt_contract_hashes,
    read_json as _read_json,
    sha256 as _sha256,
    skill_bundle_sha256,
)


SKILL_RELATIVE = Path("vendor/skills/ppt-visual-structure-designer")
VISUAL_FILES = {
    "design_input": Path("visual/visual-design-input.json"),
    "skill_request": Path("visual/skill-request.json"),
    "skill_invocation": Path("visual/skill-invocation.md"),
    "decisions": Path("visual/visual-design-decisions.json"),
    "execution_receipt": Path("visual/execution-receipt.json"),
    "spec_json": Path("visual/deck-visual-spec.json"),
    "spec_markdown": Path("visual/script-visual-structure.md"),
    "generation_prompts": Path("visual/generation-prompts.md"),
    "validation": Path("visual/validation-report.json"),
    "review_summary": Path("visual/visual-review-summary.md"),
}


def _spec_content_sha256(path: Path) -> str:
    """Hash deck-visual-spec.json excluding the audit's own status stamps.

    `run_visual_structure_audit` writes its pass/fail verdict back onto every
    page's `qa` block and `quality_contract.status`/`focus_competition.status`
    (see the `write_json_atomic(spec_json, audited_spec)` call below). Binding
    the execution receipt to the raw file hash made that self-annotation
    invalidate the very receipt the same audit run had just verified: a
    second, unchanged audit run would report EXECUTION_ARTIFACT_STALE purely
    because the first run stamped the file. Hashing the compiler-owned
    content only (with the audit-owned status fields normalized out) keeps
    the binding sensitive to real spec changes without being sensitive to the
    audit re-stamping its own prior verdict.
    """

    payload = _read_json(path)
    payload.pop("qa_summary", None)
    for page in payload.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page.pop("qa", None)
        contract = page.get("quality_contract")
        if isinstance(contract, dict):
            contract["status"] = None
            focus = contract.get("focus_competition")
            if isinstance(focus, dict):
                focus["status"] = None
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


_DIRECTION_MAP = {
    "left_to_right": "left_to_right",
    "right_to_left": "right_to_left",
    "top_to_bottom": "top_to_bottom",
    "bottom_to_top": "bottom_to_top",
    "outside_to_anchor": "outside_to_center",
    "two_sides_to_interface": "outside_to_center",
    "validation_to_decision_branches": "left_to_right",
}

# The skill decision (the actual visual-structure designer) must name the
# page's business topology explicitly -- this compiler does not infer it
# from spatial_grammar/relation, because that inference is exactly the kind
# of business classification the designer, not the compiler, is responsible
# for (see _build_executable_page's "no intent routing" contract).
ALLOWED_TOPOLOGY = {
    "parallel_set",
    "causal_convergence",
    "layered_architecture",
    "directed_flow",
    "lifecycle_loop",
    "governance_boundary",
    "ecosystem_map",
    "allocation_flow",
    "conclusion_anchor",
}

# Generic anti-patterns every topology forbids, plus topology-specific ones.
# This is repo policy, not a per-page business decision, so it is a static
# table rather than something the skill decision has to author per page.
#
# "invented_center_hub" belongs on every topology, not just the ones that
# were originally judged most at risk: a real generation of P04
# (causal_convergence, two evidence groups converging on a judgment) came
# back as a generic "center circle with radiating cards" SmartArt diagram
# -- exactly what this token exists to forbid -- even though convergence
# was not in the original topology-specific list below. Convergent and
# cyclic topologies are if anything the *most* tempted toward a literal
# hub/orbit rendering, so the gap was real, not theoretical.
_UNIVERSAL_FORBIDDEN_STRUCTURES = ["equal_peer_cards", "invented_center_hub"]
_FORBIDDEN_STRUCTURES_BY_TOPOLOGY = {
    "parallel_set": ["forced_sequential_edge"],
    "causal_convergence": ["missing_result_node"],
    "layered_architecture": ["missing_dependency_edge"],
    "directed_flow": [],
    "lifecycle_loop": ["missing_feedback_edge"],
    "governance_boundary": ["missing_boundary_edge"],
    "ecosystem_map": ["forced_sequential_edge"],
    "allocation_flow": ["missing_value_destination"],
    "conclusion_anchor": ["multiple_equal_conclusions"],
}
_DEFAULT_FORBIDDEN_STRUCTURES = list(_UNIVERSAL_FORBIDDEN_STRUCTURES)


def _fail(message: str) -> None:
    raise ValueError(message)


def _page_id(value: object) -> str:
    raw = str(value or "").strip()
    if raw.lower().startswith("p") and raw[1:].isdigit():
        return f"P{int(raw[1:]):02d}"
    _fail(f"invalid visual page id: {raw!r}")


def _render_business_relationships(value: object) -> str:
    """Render Stage 01 relation records as plain business sentences."""

    sentences: list[str] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        relation = str(item.get("relation") or "").strip()
        objects = item.get("objects")
        if not isinstance(objects, list):
            objects = [item.get("object")]
        for raw_object in objects:
            object_ = str(raw_object or "").strip()
            sentence = " ".join(part for part in (subject, relation, object_) if part)
            if sentence and sentence not in sentences:
                sentences.append(sentence)
    return "；".join(sentences) or "业务关系"


def _decision_execution_design(
    source: dict[str, Any], decision: dict[str, Any], selected: dict[str, Any], page_id: str
) -> dict[str, object]:
    design = decision.get("execution_design")
    if not isinstance(design, dict):
        design = {}
    required = (
        "business_object",
        "visual_focus",
        "text_integration_method",
        "spatial_organization",
        "relationship_encoding",
    )
    normalized = {key: str(design.get(key) or "").strip() for key in required}
    missing = [key for key, value in normalized.items() if not value]
    corrupted = [key for key, value in normalized.items() if "?" in value]
    if not missing and not corrupted:
        return {
            **normalized,
            "semantic_role": str(design.get("semantic_role") or normalized["relationship_encoding"]).strip(),
            "use_scene": design.get("use_scene") if isinstance(design.get("use_scene"), bool) else False,
            "scene_type": str(
                design.get("scene_type")
                or "不使用实景，由选定业务关系场承载"
            ).strip(),
        }
    # Older receipts may contain a non-authoritative experimental field that
    # was damaged by a console encoding round-trip.  The selected candidate,
    # authoritative relationships, and exact copy are still sound.  Compile
    # a concrete relation-bearing design from those inputs instead of sending
    # the damaged text downstream or pretending that it is a valid design.
    relationships = source.get("business_relationships") or []
    subject = next((str(relation.get("subject") or "").strip() for relation in relationships if isinstance(relation, dict) and str(relation.get("subject") or "").strip()), "本页业务关系")
    focus_key = str((selected.get("semantic_focus") or {}).get("evidence_key") or "")
    evidence = {str(item.get("key") or ""): str(item.get("summary") or "") for item in decision.get("evidence_units") or [] if isinstance(item, dict)}
    focus = evidence.get(focus_key) or str(source.get("core_judgment") or "")
    # Decision receipts retain evidence summaries for audit, which can be very
    # long.  They are not prompt copy.  Use the concise group label as the
    # selected drawable focus, never concatenate the evidence payload.
    focus_label = focus.split("/")[0].split("｜")[0].split("：")[0].strip(" 。；")
    focus_label = re.sub(r"^\s*\d+\s*(?:→|—|-)\s*", "", focus_label).strip()
    focus_label = focus_label or subject
    if len(focus_label) > 28:
        focus_label = focus_label[:28].rstrip("，。；：")
    fallback: dict[str, object] = {
        "business_object": f"{subject}中围绕“{focus_label}”形成的业务关系场",
        "visual_focus": f"“{focus_label}”所承接的业务对象、动作与结果",
        "text_integration_method": f"将“{focus_label}”对应正文贴附在主业务对象及其承接动作上；其余正文贴附到输入、条件、接口或结果，不独立成文字栏",
        "spatial_organization": f"以“{focus_label}”为唯一视觉焦点，围绕{subject}把输入、承接动作与结果组织为连续关系场；辅助信息仅贴附于对应对象",
        "relationship_encoding": f"通过{subject}中对象、动作、条件与结果的承接关系表达本页判断；不以逐条文字或装饰对象代替业务关系",
        "semantic_role": f"以{subject}的对象、动作和结果关系证明本页判断",
        "use_scene": False,
        "scene_type": "不使用实景，由选定业务关系场承载",
    }
    return fallback


def _expression_contract(source: dict[str, Any], selected: dict[str, Any]) -> dict[str, object]:
    constraints = source.get("expression_constraints")
    fit = selected.get("expression_fit")
    if not isinstance(constraints, dict) or not isinstance(fit, dict):
        _fail("selected visual candidate must retain expression constraints and expression_fit")
    return {
        "form": str(constraints.get("form") or ""),
        "constraints_sha256": expression_constraints_sha256(constraints),
        "selected_candidate_id": str(selected.get("id") or ""),
        "fit_status": str(fit.get("constraint_status") or ""),
        "reading_relation": str(fit.get("reading_relation") or ""),
        "balance_strategy": str(fit.get("balance_strategy") or ""),
        "deviation_reason": str(fit.get("deviation_reason") or ""),
    }


def _quality_contract(decision: dict[str, Any], selected: dict[str, Any], focus_ref: str) -> dict[str, object]:
    rationale = selected.get("selection_rationale") if isinstance(selected.get("selection_rationale"), dict) else {}
    feasibility = rationale.get("generation_feasibility") if isinstance(rationale.get("generation_feasibility"), dict) else {}
    budget = selected.get("text_capacity_budget") if isinstance(selected.get("text_capacity_budget"), dict) else {}
    coverage = decision.get("relationship_coverage") if isinstance(decision.get("relationship_coverage"), list) else []
    return {
        "status": "pending_audit",
        "mission_fit": str(rationale.get("mission_fit") or ""),
        "generation_feasibility": {"score": feasibility.get("score"), "risks": feasibility.get("risks") or []},
        "relationship_coverage": {key: sum(1 for item in coverage if isinstance(item, dict) and item.get("visual_status") == key) for key in ("primary", "secondary", "not_rendered")} | {"total": len(coverage)},
        "text_capacity": {"risk_level": budget.get("risk_level"), "locked_text_count": budget.get("locked_text_count"), "risks": budget.get("risks") or []},
        "focus_competition": {"status": "pending_audit", "primary_ref": focus_ref},
    }


def _build_executable_page(source: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    """Compile a Skill decision receipt into one schema-1.1 visual spec.

    This deliberately does no intent routing: the selected candidate and the
    concrete execution design are supplied by the actual visual-structure
    designer.  The compiler only preserves their decision and binds exact copy.
    """

    page_id = _page_id(source.get("page_id"))
    if _page_id(decision.get("page_id")) != page_id:
        _fail(f"{page_id}: decision receipt page id does not match visual input")
    evidence = decision.get("evidence_units")
    candidates = decision.get("candidates")
    if not isinstance(evidence, list) or not evidence or not isinstance(candidates, list) or len(candidates) < 1:
        _fail(f"{page_id}: decision receipt must contain evidence_units and at least one candidate")
    evidence_keys = [str(item.get("key") or "").strip() for item in evidence if isinstance(item, dict)]
    if len(evidence_keys) != len(evidence) or not all(evidence_keys) or len(set(evidence_keys)) != len(evidence_keys):
        _fail(f"{page_id}: evidence keys must be non-empty and unique")
    # The registered visual-spec schema permits at most seven evidence nodes.
    # Decisions may bind several contiguous locked strings to a single node,
    # but must not turn every line of on-screen copy into a graph node.
    if len(evidence_keys) > 7:
        _fail(
            f"{page_id}: visual decision has {len(evidence_keys)} evidence units; "
            "group contiguous locked copy into at most 7 business evidence units"
        )
    selected_id = str(decision.get("selected_candidate") or "")
    selected = next((item for item in candidates if isinstance(item, dict) and item.get("id") == selected_id), None)
    if selected is None:
        _fail(f"{page_id}: selected candidate is missing")
    expression_contract = _expression_contract(source, selected)
    design = _decision_execution_design(source, decision, selected, page_id)
    focus = selected.get("semantic_focus") if isinstance(selected.get("semantic_focus"), dict) else {}
    focus_key = str(focus.get("evidence_key") or "")
    if focus_key not in evidence_keys:
        _fail(f"{page_id}: selected candidate has an unknown semantic focus")
    topology = str(selected.get("topology") or "")
    if topology not in ALLOWED_TOPOLOGY:
        _fail(f"{page_id}: selected candidate must declare a topology from {sorted(ALLOWED_TOPOLOGY)}")
    locked = source.get("locked_text_items")
    if not isinstance(locked, list) or not locked:
        _fail(f"{page_id}: visual input has no locked body text")
    expected_ids = [str(item.get("text_id") or "") for item in locked]
    expected_text = [str(item.get("text") or "") for item in locked]
    if not all(expected_ids) or not all(expected_text) or len(set(expected_ids)) != len(expected_ids):
        _fail(f"{page_id}: locked body text is invalid")
    evidence_by_key = {str(item["key"]): item for item in evidence}
    text_ids_by_evidence = {
        key: [str(value) for value in evidence_by_key[key].get("text_ids") or []]
        for key in evidence_keys
    }
    actual_ids = [item for key in evidence_keys for item in text_ids_by_evidence[key]]
    if actual_ids != expected_ids:
        _fail(f"{page_id}: evidence text_ids must cover every locked text id once and in order")
    eid = {key: f"E{index}" for index, key in enumerate(evidence_keys, start=1)}
    reading_keys = [str(value) for value in selected.get("reading_sequence") or []]
    if len(reading_keys) != len(set(reading_keys)) or set(reading_keys) != set(evidence_keys):
        _fail(f"{page_id}: selected reading sequence must cover every evidence key once")
    grammar = [str(value) for value in selected.get("spatial_grammar") or []]
    # "peer" (coordinate_peer_set, see visual-intent-router.md) marks items with
    # no source-supported order, priority, or causal relation between them.
    # It must not fall through to the "anchor" default below, and it must not
    # get a "flow" chain of directed, main_chain connectors labeled 业务承接
    # ("business handoff") -- that label and a main-chain flag are exactly the
    # sequential/causal relationship the source explicitly does not support.
    allowed_grammar = {"anchor", "path", "convergence", "divergence", "layer", "boundary", "interface", "network", "tension", "feedback", "control", "peer"}
    grammar = [item for item in grammar if item in allowed_grammar] or ["anchor"]
    if "peer" in grammar:
        relation = "peer"
    else:
        relation = "transform" if "transform" in str(selected.get("visual_intent_type")) else "flow"
        if "convergence" in grammar:
            relation = "converge"
        elif "divergence" in grammar:
            relation = "diverge"
        elif "boundary" in grammar:
            relation = "boundary"
        elif "feedback" in grammar:
            relation = "loop"
        elif "control" in grammar:
            relation = "control"
    direction = _DIRECTION_MAP.get(str(selected.get("direction") or ""), "spatial")
    graph_edges = []
    connectors = []
    if relation == "converge":
        # A converging relation means every other node feeds the focus node
        # directly -- not a linear left-to-right chain. A chain would only
        # ever put one edge into the focus regardless of how many evidence
        # nodes exist, so MISSING_RESULT_NODE (which requires at least two
        # edges converging on the focus) could never be satisfied by a real
        # multi-evidence convergence page.
        for key in reading_keys:
            if key == focus_key:
                continue
            graph_edges.append({"from": eid[key], "to": eid[focus_key], "relation": "converge", "label": "汇聚支撑", "direction": "forward"})
            connectors.append({"from": eid[key], "to": eid[focus_key], "type": "converge", "direction": direction, "label": "汇聚支撑", "main_chain": True})
    else:
        for left, right in zip(reading_keys, reading_keys[1:]):
            if relation == "peer":
                # A directed "业务承接" (business handoff) edge with main_chain=True
                # is itself a sequential/causal claim -- exactly what "peer" means
                # the source does not support. Record the pair as siblings under
                # the same shared judgment instead, with no direction or chain flag.
                graph_edges.append({"from": eid[left], "to": eid[right], "relation": "peer", "label": "共同支撑同一判断", "direction": "none"})
                connectors.append({"from": eid[left], "to": eid[right], "type": "peer", "direction": "none", "label": "共同支撑同一判断", "main_chain": False})
            else:
                graph_edges.append({"from": eid[left], "to": eid[right], "relation": relation, "label": "业务承接", "direction": "forward"})
                connectors.append({"from": eid[left], "to": eid[right], "type": relation, "direction": direction, "label": "业务承接", "main_chain": True})
        if relation == "loop" and len(reading_keys) > 1:
            # A forward chain alone is not a loop: without a real edge
            # returning to the start, "loop" was only ever a label, not an
            # actual cycle, and MISSING_FEEDBACK_EDGE (which requires a
            # backward-direction edge) could never pass for a real
            # lifecycle_loop page. The feedback closes from the last node
            # (the cycle's outcome) back to the first (where it re-enters).
            last_key, first_key = reading_keys[-1], reading_keys[0]
            graph_edges.append({"from": eid[last_key], "to": eid[first_key], "relation": "loop", "label": "反馈回流", "direction": "backward"})
            connectors.append({"from": eid[last_key], "to": eid[first_key], "type": "loop", "direction": "spatial", "label": "反馈回流", "main_chain": False})
    trace_refs = [str(value).strip() for value in source.get("trace_refs") or [] if str(value).strip()]
    source_ref = "、".join(trace_refs) or page_id
    evidence_units = [
        {
            "id": eid[key], "text": str(evidence_by_key[key].get("summary") or expected_text[0]),
            "kind": "result" if key == focus_key else "process", "priority": "P0",
            "source_ref": source_ref, "status": "locked",
        }
        for key in evidence_keys
    ]
    focus_id = eid[focus_key]
    graph_nodes = [
        {
            "id": eid[key],
            "role": "judgment" if key == focus_key else "evidence",
            "source_refs": text_ids_by_evidence[key],
        }
        for key in evidence_keys
    ]
    grouping_decisions = []
    for key in evidence_keys:
        source_refs = text_ids_by_evidence[key]
        if len(source_refs) < 2:
            continue
        reason = str(evidence_by_key[key].get("grouping_reason") or "").strip()
        loss_risk = str(evidence_by_key[key].get("loss_risk") or "").strip()
        if not reason or loss_risk not in {"low", "medium", "high"}:
            _fail(
                f"{page_id}: evidence unit {key!r} merges {len(source_refs)} locked text ids "
                "and must declare grouping_reason and loss_risk (low/medium/high)"
            )
        grouping_decisions.append({
            "source_nodes": source_refs,
            "target_node": eid[key],
            "reason": reason,
            "loss_risk": loss_risk,
        })
    no_arrows = any(
        "不绘制箭头" in str(design.get(field) or "")
        or "不使用箭头" in str(design.get(field) or "")
        for field in ("text_integration_method", "spatial_organization", "relationship_encoding")
    )
    forbidden_structures = list(dict.fromkeys((
        *_UNIVERSAL_FORBIDDEN_STRUCTURES,
        *_FORBIDDEN_STRUCTURES_BY_TOPOLOGY.get(topology, []),
        *(("no_arrows",) if no_arrows else ()),
    )))
    quality_contract = _quality_contract(decision, selected, focus_id)
    final_text = [
        {"id": item_id, "role": "body", "text": text, "region_id": "R_RELATION"}
        for item_id, text in zip(expected_ids, expected_text)
    ]
    locked_items = [{"id": f"{page_id}-TITLE", "type": "title", "text": str(source.get("page_title") or page_id), "source_ref": source_ref}]
    locked_items.extend({"id": item_id, "type": "body", "text": text, "source_ref": source_ref} for item_id, text in zip(expected_ids, expected_text))
    dense_text_page = is_text_dense(expected_text)
    visual_budget = (
        {
            "mode": "relationship_field_only" if dense_text_page else "shared_field",
            "max_auxiliary_fragments": 0 if dense_text_page else 1,
            "scope": "page",
            "region_local_visuals": False,
        }
        if topology == "parallel_set" or not bool(design["use_scene"])
        else {
            "mode": "integrated_scene",
            "max_auxiliary_fragments": 4,
            "scope": "region",
            "region_local_visuals": True,
        }
    )
    return {
        "schema_version": "1.1", "page_id": page_id, "page_number": int(source["page_number"]),
        "page_title": str(source["page_title"]), "page_role": str(source.get("argument_role") or "content"),
        "page_mission": str(source["page_mission"]), "core_judgment": str(source["core_judgment"]),
        "content_lock": {"mode": "strict", "locked_items": locked_items, "allowed_transformations": ["line_break", "grouping", "position_change"], "forbidden_transformations": ["Do not change facts, numbers, dates or units.", "Do not change actors, responsibilities or status.", "Do not add presentation copy that is not part of the approved locked text.", "For a \"label: sentence\" locked text item, render it once as that single label-plus-sentence unit; do not additionally repeat the label alone as a separate heading, card title, or tag.", "Do not invent a heading, label, or tag for a locked text item that has no label in the required text (for example a bare boundary sentence); render it as plain text with no invented label."]},
        "evidence_units": evidence_units,
        "semantic_graph": {"primary_relation": relation, "direction": direction, "topology": topology, "focus_node": focus_id, "nodes": graph_nodes, "edges": graph_edges, "decision_relationship": _render_business_relationships(source.get("business_relationships")), "business_relationships": deepcopy(source.get("business_relationships") or []), "grouping_decisions": grouping_decisions, "forbidden_structures": forbidden_structures},
        "structural_decision": {"semantic_focus": {"kind": str(focus.get("kind") or "relationship"), "ref": focus_id}, "spatial_grammar": grammar, "semantic_tags": [str(selected.get("visual_intent_type") or "relationship")], "primary_refs": [focus_id], "secondary_refs": [eid[key] for key in evidence_keys if key != focus_key], "reading_sequence": [eid[key] for key in reading_keys], "text_bindings": [{"evidence_id": eid[key], "target_ref": eid[key], "binding": "result" if key == focus_key else "embedded", "text_ids": text_ids_by_evidence[key]} for key in evidence_keys], "representation_freedom": {"carrier": "free", "medium": "free", "reason": "上游仅锁定业务关系和正文，Stage02已选定具体业务关系场与文字贴附方式"}},
        "visual_decision": {"visual_intent_type": str(selected.get("visual_intent_type") or "relationship_field"), "visual_thesis": str(selected.get("visual_thesis") or source["core_judgment"]), "spatial_organization": design["spatial_organization"], "reading_path": [str(evidence_by_key[key].get("summary") or "") for key in reading_keys], "text_integration_method": design["text_integration_method"], "relationship_encoding": design["relationship_encoding"], "visual_center_count": 1, "visual_hierarchy": {"primary": design["visual_focus"], "secondary": [str(evidence_by_key[key].get("summary") or "") for key in evidence_keys if key != focus_key], "tertiary": []}},
        "text_integration": {"title_render_mode": str(source.get("title_render_mode") or "external_text_layer"), "subtitle_render_mode": str(source.get("subtitle_render_mode") or "external_text_layer"), "body_render_mode": "in_image", "placement_strategy": design["text_integration_method"]},
        "geometry": {"canvas": source.get("body_image_canvas") or {"width": 2048, "height": 1024, "ratio": "2:1"}, "title_exclusion_zone": {"x": 0, "y": 0, "w": 2048, "h": 0}, "regions": [{"id": "R_RELATION", "role": "relation-bearing business field", "x": 80, "y": 120, "w": 1888, "h": 800, "priority": "primary"}]},
        "image_plan": {"use_scene": bool(design["use_scene"]), "scene_type": str(design["scene_type"]), "business_object": design["business_object"], "semantic_role": str(design["semantic_role"]), "placement": design["spatial_organization"], "front_facing_people": False, "identifiable_location": False, "factual_event_implication": False},
        "visual_budget": visual_budget,
        "expression_contract": expression_contract,
        "quality_contract": quality_contract,
        "connectors": connectors, "final_text": final_text,
        "generation_handoff": {"structural_guidance": {"source": "structural_decision", "additional_constraints": ["Use the selected business relationship field and its text attachment design; do not render instructions or internal text ids.", "Keep one visual focus and do not create an independent text wall or second summary structure.", "Respect visual_budget: semantic evidence units may share one page-level visual carrier; do not create region-local imagery when region_local_visuals is false."]}, "required_text_ids": expected_ids, "required_text": expected_text, "style_source_ref": "external style lock selected at final-script-pages", "title_exclusion_instruction": "Reserve page title and subtitle for the external PowerPoint text layer; do not render them in the body image."},
        "avoid": ["Do not map each body item to an isolated icon or decorative image.", "Do not create an independent text wall or second result chain."],
        "qa": {"status": "pending_audit", "score": None, "blocking_issues": [], "warnings": []},
    }


def _render_visual_structure_markdown(spec: dict[str, Any]) -> str:
    """Render the human-reviewable contract from the same executable JSON."""
    lines = [f"# {spec['deck_title']}视觉结构设计脚本", "", "## 整套视觉设计总则", "", "- 以每页唯一业务关系场承载正文；具体视觉风格仅由最终 Style lock 提供。", ""]
    for page in spec["pages"]:
        vd, sg, structural = page["visual_decision"], page["semantic_graph"], page["structural_decision"]
        visual_budget = page.get("visual_budget") if isinstance(page.get("visual_budget"), dict) else {}
        contract = page.get("expression_contract") if isinstance(page.get("expression_contract"), dict) else {}
        form = str(contract.get("form") or "")
        constraints = expression_constraints(form) if form else {}
        expression_lines = ["### 上屏表达结构与候选取舍"]
        if constraints:
            expression_lines.extend([
                f"- 表达结构：{form}（{constraints['relation_pattern']}）",
                f"- 核心约束：{constraints['reading_requirement']}；{constraints['balance_requirement']}",
                f"- 已选候选：{contract.get('selected_candidate_id', '')}；适配状态：{contract.get('fit_status', '')}",
                f"- 阅读关系：{contract.get('reading_relation', '')}",
                f"- 均衡策略：{contract.get('balance_strategy', '')}",
            ])
            if str(contract.get("deviation_reason") or "").strip():
                expression_lines.append(f"- 偏离理由：{contract['deviation_reason']}")
        node_summary = ", ".join(f"{node['id']}({node['role']})" for node in sg["nodes"])
        edge_summary = "; ".join(f"{edge['from']} -> {edge['to']}（{edge['relation']}，{edge['direction']}）" for edge in sg["edges"]) or "无"
        forbidden_summary = ", ".join(sg["forbidden_structures"]) or "无"
        lines += [f"## 第{page['page_number']}页｜{page['page_title']}", "", "### 页面角色", page["page_role"], "", "### 页面使命", page["page_mission"], "", "### 核心结论", page["core_judgment"], "", "### 内容锁定", "- 严格保留 generation_handoff.required_text 所列正文", "", "### 证据单元与语义关系", f"- 主关系：{sg['decision_relationship']}", f"- 拓扑：{sg['topology']}", f"- 焦点节点：{sg['focus_node']}", f"- 节点：{node_summary}", f"- 关系边：{edge_summary}", f"- 禁止结构：{forbidden_summary}", "", *expression_lines, "", "### 视觉意图", f"- 视觉意图类型：{vd['visual_intent_type']}", f"- 语义焦点：{structural['semantic_focus']['kind']} / {structural['semantic_focus']['ref']}", f"- 空间语法：{', '.join(structural['spatial_grammar'])}", f"- 主结构：{', '.join(structural['primary_refs'])}", f"- 文字归属：{vd['text_integration_method']}", "", "### 页面草图", f"- 唯一业务关系场：{page['image_plan']['business_object']}", f"- 配图预算：{visual_budget.get('mode', 'integrated_scene')}；最多辅助片段 {visual_budget.get('max_auxiliary_fragments', 4)} 个；作用域 {visual_budget.get('scope', 'region')}；区域局部配图 {visual_budget.get('region_local_visuals', True)}", "", "### 页面构图", vd['spatial_organization'], "", "### 实景锚点与图文融合", vd['relationship_encoding'], "", "### 元素与空间关系", page['image_plan']['placement'], "", "### 箭头与连接关系", *[f"- {item['from']} -> {item['to']}：{item['label']}" for item in page['connectors']], "", "### 标题与文字渲染", "- 标题与副标题由外部PPT文字层渲染；正文贴附在业务对象、动作、接口、边界或结果上", "", "### 终稿文字", *[f"- {item['text']}" for item in page['final_text']], "", "### 生图执行摘要", f"- {vd['text_integration_method']}", "", "### 禁止事项", *[f"- {item}" for item in page['avoid']], ""]
    return "\n".join(lines)


def _render_visual_review_summary(spec: dict[str, Any], decisions: dict[str, Any], validation: dict[str, Any]) -> str:
    """Render the audit-only P3 reviewer minimum package; never a prompt input."""

    by_id = {_page_id(item.get("page_id")): item for item in decisions.get("pages") or [] if isinstance(item, dict)}
    lines = [f"# {spec.get('deck_title', '')}视觉质量人工复核摘要", ""]
    for page in spec.get("pages") or []:
        if not isinstance(page, dict):
            continue
        decision = by_id.get(_page_id(page.get("page_id")), {})
        selected = str(decision.get("selected_candidate") or "")
        candidates = [item for item in decision.get("candidates") or [] if isinstance(item, dict)]
        contract = page.get("quality_contract") if isinstance(page.get("quality_contract"), dict) else {}
        graph = page.get("semantic_graph") if isinstance(page.get("semantic_graph"), dict) else {}
        structural = page.get("structural_decision") if isinstance(page.get("structural_decision"), dict) else {}
        lines += [f"## 第{page.get('page_number', '')}页｜{page.get('page_title', '')}", "", f"- 页面使命：{page.get('page_mission', '')}", f"- 选中候选：{selected}", "- 候选取舍："]
        for candidate in candidates:
            if str(candidate.get("id") or "") != selected:
                lines.append(f"  - {candidate.get('id', '')}：{candidate.get('rejection_rationale', '')}")
        lines += ["- 关系草图："]
        for edge in graph.get("edges") or []:
            if isinstance(edge, dict):
                lines.append(f"  - {edge.get('from', '')} → {edge.get('to', '')}（{edge.get('relation', '')}）")
        capacity = contract.get("text_capacity") if isinstance(contract.get("text_capacity"), dict) else {}
        feasibility = contract.get("generation_feasibility") if isinstance(contract.get("generation_feasibility"), dict) else {}
        coverage = contract.get("relationship_coverage") if isinstance(contract.get("relationship_coverage"), dict) else {}
        focus = contract.get("focus_competition") if isinstance(contract.get("focus_competition"), dict) else {}
        lines += [
            f"- 锁定文字容量：{capacity.get('locked_text_count')}项；风险={capacity.get('risk_level')}；{', '.join(str(item) for item in capacity.get('risks') or []) or '无'}",
            f"- 可生成性：{feasibility.get('score')}；风险={', '.join(str(item) for item in feasibility.get('risks') or []) or '无'}",
            f"- 关系/焦点风险：覆盖={coverage}；焦点={focus}；主焦点={structural.get('semantic_focus', {})}",
            "",
        ]
    rhythm = validation.get("deck_rhythm") if isinstance(validation.get("deck_rhythm"), dict) else {}
    lines += ["## 整套节奏结论", "", f"- 状态：{rhythm.get('status', 'pending_audit')}"]
    for issue in rhythm.get("blocking_issues") or []:
        lines.append(f"- 阻断：{issue.get('code', '')}｜{issue.get('message', '')}")
    for warning in rhythm.get("warnings") or []:
        lines.append(f"- 警告：{warning.get('code', '')}｜{warning.get('message', '')}")
    return "\n".join(lines) + "\n"


def execute_visual_structure_stage(project: Path, script: Path) -> dict[str, Path]:
    """Create official Stage02 visual-spec outputs from an executed decision receipt."""
    project, script = project.expanduser().resolve(), script.expanduser().resolve()
    design_input_path, decisions_path = project / VISUAL_FILES["design_input"], project / VISUAL_FILES["decisions"]
    if not script.is_file() or not design_input_path.is_file() or not decisions_path.is_file():
        raise FileNotFoundError("visual structure execution requires script, visual-design-input.json and visual-design-decisions.json")
    design_input, decisions = _read_json(design_input_path), _read_json(decisions_path)
    if decisions.get("source_sha256") != _sha256(design_input_path):
        _fail("visual design decisions are stale for visual-design-input.json")
    sources = design_input.get("pages")
    received = decisions.get("pages")
    if not isinstance(sources, list) or not isinstance(received, list):
        _fail("visual design input and decisions must both contain pages arrays")
    by_id = {_page_id(item.get("page_id")): item for item in received if isinstance(item, dict)}
    if len(by_id) != len(sources) or {_page_id(item.get("page_id")) for item in sources} != set(by_id):
        _fail("visual design decisions do not cover the current input page set")
    pages = [_build_executable_page(source, by_id[_page_id(source.get("page_id"))]) for source in sources]
    spec = {"schema_version": "1.1", "deck_id": project.name, "deck_title": str(project.name), "deck_context": {"audience": "项目既定受众", "purpose": "承接已确认业务脚本形成可执行页面视觉设计", "usage_scene": "正式汇报", "narrative": "每页以唯一业务关系场承载已锁定正文", "source_files": [str(design_input_path)]}, "global_profile": "ppt-visual-structure-designer", "content_lock": {"default_mode": "strict", "global_locked_terms": [], "global_forbidden_changes": ["不得改变锁定正文、事实、主体关系或边界"]}, "pages": pages, "deck_rhythm": {"density_pattern": "随页面业务关系复杂度变化", "visual_intent_sequence": [item['visual_decision']['visual_intent_type'] for item in pages], "repetition_control": "连续页面避免复用同一视觉意图和空间语法"}, "capacity_suggestions": [], "qa_summary": {"status": "pending_audit", "average_score": None, "blocking_issues": [], "warnings": []}}
    json_path, markdown_path = project / VISUAL_FILES["spec_json"], project / VISUAL_FILES["spec_markdown"]
    write_json_atomic(json_path, spec)
    markdown_path.write_text(_render_visual_structure_markdown(spec) + "\n", encoding="utf-8")
    return {"spec_json": json_path, "spec_markdown": markdown_path}


def _write_visual_design_input(project: Path, handoff: Path) -> Path:
    payload = _read_json(handoff)
    source_pages = payload.get("pages") or []
    content_pages = [page for page in source_pages if page.get("render_role") == "content"]
    pages: list[dict[str, Any]] = []
    for index, page in enumerate(content_pages):
        visual = page.get("stage02_visual_input") or {}
        expression = visual.get("onscreen_expression") or page.get("onscreen_expression") or {}
        constraints = visual.get("expression_constraints") or page.get("expression_constraints")
        if constraints is None:
            constraints = expression_constraints(str(expression.get("form") or ""))
        previous_page = content_pages[index - 1] if index else None
        next_page = content_pages[index + 1] if index + 1 < len(content_pages) else None
        pages.append(
            {
                "page_id": page.get("page_id"),
                "page_number": page.get("page_number"),
                "page_title": page.get("title"),
                "argument_role": page.get("argument_role"),
                "page_mission": page.get("page_mission"),
                "core_judgment": page.get("core_message"),
                "semantic_context": page.get("full_prose"),
                "locked_on_screen_text": page.get("onscreen_text"),
                "locked_on_screen_items": page.get("onscreen_items") or [],
                "locked_text_items": visual.get("locked_text_items") or [],
                "trace_refs": list(dict.fromkeys([
                    *[str(value) for value in page.get("source_refs") or [] if str(value)],
                    *[str(value) for value in page.get("boundary_source_refs") or [] if str(value)],
                ])),
                "onscreen_expression": expression,
                "expression_constraints": constraints,
                "business_relationships": visual.get("business_relationships") or [],
                "stage01_relationship_features": visual.get("stage01_relationship_features") or {},
                "relationship_authority": "business_relationships",
                "author_visual_notes": visual.get("author_visual_notes") or "",
                "author_visual_notes_authority": "advisory_only",
                "must_not_include": page.get("must_not_include") or [],
                "body_image_canvas": visual.get("body_image_canvas"),
                "title_render_mode": visual.get("title_render_mode"),
                "subtitle_render_mode": visual.get("subtitle_render_mode"),
                "previous_content_page": (
                    {"page_id": previous_page.get("page_id"), "title": previous_page.get("title")}
                    if previous_page
                    else None
                ),
                "next_content_page": (
                    {"page_id": next_page.get("page_id"), "title": next_page.get("title")}
                    if next_page
                    else None
                ),
            }
        )
    output = project / VISUAL_FILES["design_input"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_design_input.v2",
            "source": str(handoff),
            "source_sha256": _sha256(handoff),
            "content_lock": "strict",
            "style_policy": "visual structure must not select or embed a visual style",
            "relationship_policy": (
                "business_relationships is authoritative; author_visual_notes is advisory only "
                "and must never be copied into decision_relationship"
            ),
            "decision_policy": (
                "ppt-visual-structure-designer writes one candidate when the page's business "
                "relationship type is unambiguous from expression_constraints.reading_requirement "
                "and content alone; when the relationship type is genuinely contested (for example "
                "parallel vs. hierarchical), it must compare 2-3 materially different candidates "
                "and justify the selection; deterministic keyword routing is never authoritative"
            ),
            "pages": pages,
        },
    )
    return output


def visual_structure_required(project: Path) -> bool:
    manifest = project / "manifest.yml"
    if manifest.is_file():
        text = manifest.read_text(encoding="utf-8-sig")
        if "visual_structure_designer: required" in text:
            return True
    # Older lightweight projects were created before the manifest gate was
    # registered.  Once any Stage 02 visual-structure artifact exists, that
    # project has entered the same governed workflow and cannot bypass a
    # failed audit merely because its historical manifest lacks the flag.
    visual = project / "visual"
    return any((visual / name).is_file() for name in (
        "skill-request.json", "visual-design-input.json", "deck-visual-spec.json",
        "visual-design-decisions.json", "validation-report.json",
    ))


def _skill_root() -> Path:
    return (Path(__file__).resolve().parents[2] / SKILL_RELATIVE).resolve()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _write_skill_request(project: Path, script: Path, design_input: Path) -> Path:
    skill_root = _skill_root()
    contracts = prompt_contract_hashes(skill_root)
    output = project / VISUAL_FILES["skill_request"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_structure_skill_request.v1",
            "skill": "ppt-visual-structure-designer",
            "skill_root": str(skill_root),
            "skill_bundle_sha256": contracts["skill_bundle"],
            "skill_contract_sha256": contracts,
            "approved_script": str(script),
            "approved_script_sha256": _sha256(script),
            "approved_script_semantic_sha256": script_semantic_digest(script),
            "visual_design_input": str(design_input),
            "visual_design_input_sha256": _sha256(design_input),
            "content_lock": "strict",
            "relationship_authority": "business_relationships",
            "author_visual_notes_authority": "advisory_only",
            "required_outputs": [VISUAL_FILES["decisions"].as_posix()],
            "compiler_outputs": [
                VISUAL_FILES["spec_json"].as_posix(),
                VISUAL_FILES["spec_markdown"].as_posix(),
            ],
            "forbidden_outputs": ["image", "svg", "html", "pptx"],
            "prepared_at": _utc_now(),
        },
    )
    return output


def prepare_visual_structure_stage(
    project: Path,
    script: Path,
    *,
    lightweight_stage01_confirmed: bool = False,
    reuse_current_handoff: bool = False,
) -> Path:
    # Kept for direct-call compatibility; handoff preparation is governed by
    # the current full-script audit, not an interactive-confirmation flag.
    _ = lightweight_stage01_confirmed
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    from cyberppt.stage02_handoff import HANDOFF_JSON, prepare_stage02_handoff

    handoff = project / HANDOFF_JSON
    if reuse_current_handoff:
        if not handoff.is_file():
            raise FileNotFoundError(
                "reuse_current_handoff requires an existing Stage 02 handoff"
            )
        from cyberppt.stage02_handoff import audit_stage02_handoff

        report = audit_stage02_handoff(project)
        if report.get("status") != "passed":
            codes = ", ".join(
                item.get("code", "HANDOFF_INVALID")
                for item in report.get("blocking_issues", [])
            )
            raise ValueError(
                f"reuse_current_handoff requires a current Stage 02 handoff: {codes}"
            )
    else:
        report = prepare_stage02_handoff(
            project,
            script=script,
        )
        if report.get("status") != "passed":
            raise ValueError("Stage 01 to Stage 02 handoff is not passed")
    design_input = _write_visual_design_input(project, handoff)
    skill_root = _skill_root()
    skill = skill_root / "SKILL.md"
    if not skill.is_file():
        raise FileNotFoundError(f"registered visual structure skill is missing: {skill}")
    skill_request = _write_skill_request(project, script, design_input)
    output = project / VISUAL_FILES["skill_invocation"]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            [
                "# PPT Visual Structure Designer Invocation",
                "",
                "- skill: ppt-visual-structure-designer",
                f"- skill_path: {skill}",
                f"- skill_sha256: {_sha256(skill)}",
                f"- skill_bundle_sha256: {skill_bundle_sha256(skill_root)}",
                f"- approved_script: {script}",
                f"- approved_script_sha256: {_sha256(script)}",
                f"- approved_script_semantic_sha256: {script_semantic_digest(script)}",
                f"- stage02_handoff: {handoff}",
                f"- visual_design_input: {design_input}",
                f"- skill_request: {skill_request}",
                "- mode: workbench-handoff",
                "- content_lock: strict",
                "",
                "## Required action",
                "",
                "Invoke the registered skill in the current execution surface. Use visual-design-input.json, derived only from stage02_handoff.json, as the visual-design interface. Write cyberppt.visual_design_decisions.v3. Treat business_relationships as authoritative, use stage01_relationship_features to preserve actors, actions, directions, conditions, branches and feedback, and treat author_visual_notes as advisory only. trace_refs are audit-only provenance: use them to justify decisions but never copy them into visual copy or ImageGen prompt material. Treat expression_constraints as the required reading-relation and balance profile: it governs peer hierarchy, progression, correspondence, feedback or causal direction; it must never be converted directly into a fixed card, column, arrow, loop, pyramid or matrix template. Every candidate must provide its own visual_thesis and expression_fit with the received form, satisfied constraints, reading relation, balance strategy, and either an empty default-profile deviation or an adapted-profile changed-constraint list plus business reason that preserves the expression core. Each selected page decision must provide execution_design.business_object, visual_focus, semantic_role, use_scene (boolean), scene_type, text_integration_method, spatial_organization and relationship_encoding; these selected scene/carrier fields are authoritative and must survive unchanged into deck-visual-spec.json. For every page, also provide visual_budget with mode (relationship_field_only, shared_field or integrated_scene), max_auxiliary_fragments, scope (page or region) and region_local_visuals. A parallel_set page must use shared_field or relationship_field_only, with at most one page-level auxiliary fragment and region_local_visuals=false. For every page, record stage01_visual_note_disposition with the received form, chosen reading relation and balance strategy, plus inherited, adjusted and rejected upstream visual features and reasons. Do not read or reuse any existing Stage 02 visual/ or workbench/prompts/imagegen outputs as authority. Write one candidate when the page's business relationship type is unambiguous from expression_constraints.reading_requirement and content alone; when it is genuinely contested (for example parallel vs. hierarchical), generate and compare 2-3 materially different candidates and justify the selection. Deterministic keyword matching must not choose the final visual intent or carrier. Preserve the approved page set, locked text ids and locked text, and write only:",
                "",
                "- `visual/visual-design-decisions.json`",
                "",
                "After the Skill has actually produced that decision receipt, run `python -m cyberppt execute-visual-structure <project> --script <script>` to compile `deck-visual-spec.json` and `script-visual-structure.md`; then record the execution with `python -m cyberppt record-visual-structure-execution <project> --script <script> --executor <surface> --model <model>`, and run `visual-structure-audit`. The audit, not the Skill, rebuilds generation-prompts.md as a legacy structural preview. Formal ImageGen handoff uses the repository artifact-spec-v2 compiler over the audited Stage 02 handoff, deck visual spec and style lock.",
                "",
                "Do not select a visual style, generate images, SVG, HTML, or PPTX in this stage.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return output


def record_visual_structure_execution(
    project: Path,
    script: Path,
    *,
    executor: str,
    model: str,
    note: str = "",
) -> Path:
    """Record a completed, externally executed Skill run with current hashes."""

    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    if not executor.strip() or not model.strip():
        raise ValueError("executor and model are required for the visual structure execution receipt")
    skill_root = _skill_root()
    design_input = project / VISUAL_FILES["design_input"]
    request_path = project / VISUAL_FILES["skill_request"]
    artifact_paths = {
        key: project / VISUAL_FILES[key]
        for key in ("decisions", "spec_json", "spec_markdown")
    }
    for path in (script, design_input, request_path, *artifact_paths.values()):
        if not path.is_file():
            raise FileNotFoundError(f"visual structure execution artifact is missing: {path}")
    request = _read_json(request_path)
    contracts = prompt_contract_hashes(skill_root)
    if request.get("visual_design_input_sha256") != _sha256(design_input):
        raise ValueError("visual structure skill request is stale for visual-design-input.json")
    if request.get("skill_bundle_sha256") != contracts["skill_bundle"]:
        raise ValueError("visual structure skill request is stale for the current registered Skill")
    design_payload = _read_json(design_input)
    page_ids = [str(item.get("page_id") or "") for item in design_payload.get("pages") or [] if isinstance(item, dict)]
    output = project / VISUAL_FILES["execution_receipt"]
    write_json_atomic(
        output,
        {
            "schema": "cyberppt.visual_structure_execution_receipt.v1",
            "skill": "ppt-visual-structure-designer",
            "executor": executor.strip(),
            "model": model.strip(),
            "skill_request": str(request_path),
            "skill_request_sha256": _sha256(request_path),
            "skill_bundle_sha256": contracts["skill_bundle"],
            "skill_contract_sha256": contracts,
            "approved_script": str(script),
            "approved_script_semantic_sha256": script_semantic_digest(script),
            "visual_design_input": str(design_input),
            "visual_design_input_sha256": _sha256(design_input),
            "page_ids": page_ids,
            "skill_outputs": ["decisions"],
            "compiler_outputs": ["spec_json", "spec_markdown"],
            "artifact_sha256": {
                key: (_spec_content_sha256(path) if key == "spec_json" else _sha256(path))
                for key, path in artifact_paths.items()
            },
            "executed_at": _utc_now(),
            "note": note.strip(),
        },
    )
    return output


def _audit_execution_receipt(
    project: Path,
    script: Path,
    skill_root: Path,
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []

    def issue(code: str, message: str) -> None:
        issues.append({"code": code, "message": message})

    receipt_path = project / VISUAL_FILES["execution_receipt"]
    if not receipt_path.is_file():
        return {
            "schema": "cyberppt.visual_structure_execution_audit.v1",
            "status": "failed",
            "blocking_issues": [{"code": "EXECUTION_RECEIPT_MISSING", "message": f"Missing execution receipt: {receipt_path}"}],
        }
    receipt = _read_json(receipt_path)
    request_path = project / VISUAL_FILES["skill_request"]
    design_input = project / VISUAL_FILES["design_input"]
    contracts = prompt_contract_hashes(skill_root)
    expected = {
        "skill_request_sha256": _sha256(request_path),
        "skill_bundle_sha256": contracts["skill_bundle"],
        "approved_script_semantic_sha256": script_semantic_digest(script),
        "visual_design_input_sha256": _sha256(design_input),
    }
    # Where each expected hash comes from, so a stale-receipt error can point
    # at the exact file that changed instead of just naming the field.
    expected_hash_source = {
        "skill_request_sha256": str(request_path),
        "skill_bundle_sha256": f"{skill_root} (vendor Skill bundle)",
        "approved_script_semantic_sha256": str(script),
        "visual_design_input_sha256": str(design_input),
    }
    rerun_command = (
        f"python -m cyberppt record-visual-structure-execution {project} --script {script} "
        "--executor <executor> --model <model>"
    )
    if receipt.get("schema") != "cyberppt.visual_structure_execution_receipt.v1":
        issue("EXECUTION_RECEIPT_SCHEMA_INVALID", "Visual structure execution receipt schema is invalid.")
    for field in ("executor", "model", "executed_at"):
        if not str(receipt.get(field) or "").strip():
            issue("EXECUTION_RECEIPT_FIELD_MISSING", f"Execution receipt is missing {field}.")
    for field, value in expected.items():
        if receipt.get(field) != value:
            issue(
                "EXECUTION_RECEIPT_STALE",
                f"Execution receipt field {field!r} is stale; current expected hash comes from "
                f"{expected_hash_source[field]!r}. Re-run: {rerun_command}",
            )
    if receipt.get("skill_outputs") != ["decisions"]:
        issue(
            "EXECUTION_RECEIPT_OUTPUT_OWNERSHIP_INVALID",
            "Execution receipt must record visual-design-decisions.json as the only Skill output.",
        )
    if receipt.get("compiler_outputs") != ["spec_json", "spec_markdown"]:
        issue(
            "EXECUTION_RECEIPT_OUTPUT_OWNERSHIP_INVALID",
            "Execution receipt must record the visual spec JSON and Markdown as compiler outputs.",
        )
    receipt_contracts = receipt.get("skill_contract_sha256")
    if receipt_contracts != contracts:
        stale_contract_fields = sorted(
            key for key, value in contracts.items() if receipt_contracts is None or receipt_contracts.get(key) != value
        )
        issue(
            "EXECUTION_RECEIPT_CONTRACT_STALE",
            f"Execution receipt is not bound to the current Skill contract files: {stale_contract_fields}; "
            f"current expected hashes come from {skill_root} (SKILL.md, prompt builder, validator, schemas). "
            f"Re-run: {rerun_command}",
        )
    receipt_artifacts = receipt.get("artifact_sha256") if isinstance(receipt.get("artifact_sha256"), dict) else {}
    for key in ("decisions", "spec_json", "spec_markdown"):
        path = project / VISUAL_FILES[key]
        current = _spec_content_sha256(path) if key == "spec_json" else _sha256(path)
        if not path.is_file() or receipt_artifacts.get(key) != current:
            issue(
                "EXECUTION_ARTIFACT_STALE",
                f"Execution receipt does not match {path}; current expected hash comes from that file's "
                f"present content. Re-run: {rerun_command}",
            )
    input_pages = [
        str(item.get("page_id") or "")
        for item in _read_json(design_input).get("pages") or []
        if isinstance(item, dict)
    ]
    if receipt.get("page_ids") != input_pages:
        issue("EXECUTION_PAGE_SET_STALE", "Execution receipt page_ids differ from visual-design-input.json.")
    return {
        "schema": "cyberppt.visual_structure_execution_audit.v1",
        "status": "passed" if not issues else "failed",
        "blocking_issues": issues,
    }


def _prompt_inputs_sha256(project: Path, script: Path, skill_root: Path) -> dict[str, str]:
    contracts = prompt_contract_hashes(skill_root)
    try:
        script_digest = script_semantic_digest(script)
    except ValueError:
        # Legacy external-script fixtures may not expose structured semantic
        # fields.  Bind those byte-for-byte instead of dropping script
        # freshness from the prompt contract.
        script_digest = _sha256(script)
    values = {
        "script_semantic": script_digest,
        "design_input": _sha256(project / VISUAL_FILES["design_input"]),
        "decisions": _sha256(project / VISUAL_FILES["decisions"]),
        "execution_receipt": _sha256(project / VISUAL_FILES["execution_receipt"]),
        "spec_json": _sha256(project / VISUAL_FILES["spec_json"]),
        "spec_markdown": _sha256(project / VISUAL_FILES["spec_markdown"]),
    }
    values.update({f"contract_{key}": value for key, value in contracts.items()})
    return values


def run_visual_structure_audit(project: Path, script: Path) -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    skill_root = _skill_root()
    validator = skill_root / "scripts" / "validate_visual_spec.py"
    prompt_builder = skill_root / "scripts" / "build_generation_prompt.py"
    design_input = project / VISUAL_FILES["design_input"]
    request_path = project / VISUAL_FILES["skill_request"]
    decisions = project / VISUAL_FILES["decisions"]
    execution_receipt = project / VISUAL_FILES["execution_receipt"]
    spec_json = project / VISUAL_FILES["spec_json"]
    spec_md = project / VISUAL_FILES["spec_markdown"]
    prompts = project / VISUAL_FILES["generation_prompts"]
    report_path = project / VISUAL_FILES["validation"]
    previous_report = _read_json(report_path) if report_path.is_file() else {}
    from cyberppt.stage02_handoff import HANDOFF_JSON, load_stage02_handoff

    handoff = load_stage02_handoff(project, required=True)
    handoff_path = project / HANDOFF_JSON
    for path in (
        validator,
        prompt_builder,
        script,
        design_input,
        request_path,
        decisions,
        execution_receipt,
        spec_json,
        spec_md,
    ):
        if not path.is_file():
            raise FileNotFoundError(f"visual structure stage artifact is missing: {path}")
    design_payload = _read_json(design_input)
    if design_payload.get("source_sha256") != _sha256(handoff_path):
        raise ValueError("visual-design-input.json is stale for the current Stage 02 handoff")

    results: dict[str, Any] = {}
    for label, path in (("markdown", spec_md), ("json", spec_json)):
        completed = subprocess.run(
            [sys.executable, str(validator), str(path), "--strict", "--json-report"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        results[label] = json.loads(completed.stdout)
        # The visual validator uses a non-zero exit code for warnings under
        # --strict.  Stage 02 must preserve those warnings without promoting
        # them to a blocking failure; `valid` is the contract-level result.
        results[label]["status"] = "passed" if results[label].get("valid") is True else "failed"

    results["decision_package"] = audit_visual_design_package(
        design_input,
        decisions,
        spec_json,
    )
    results["execution_receipt"] = _audit_execution_receipt(project, script, skill_root)
    results["deck_rhythm"] = audit_visual_deck_rhythm(_read_json(spec_json), _read_json(decisions))
    pre_prompt_passed = all(result.get("status") == "passed" for result in results.values())
    audited_spec = _read_json(spec_json)
    page_score = 100 if pre_prompt_passed else None
    qa_status = "passed" if pre_prompt_passed else "failed"
    page_issues = [] if pre_prompt_passed else [str(issue.get("code") or "") for result in results.values() for issue in result.get("blocking_issues", []) if isinstance(issue, dict)]
    rhythm_warnings = [str(issue.get("code") or "") for issue in results["deck_rhythm"].get("warnings", []) if isinstance(issue, dict)]
    for page in audited_spec.get("pages") or []:
        if isinstance(page, dict):
            page["qa"] = {"status": qa_status, "score": page_score, "blocking_issues": page_issues, "warnings": rhythm_warnings}
            contract = page.get("quality_contract")
            if isinstance(contract, dict):
                contract["status"] = qa_status
                contract["focus_competition"]["status"] = qa_status
    audited_spec["qa_summary"] = {"status": qa_status, "average_score": page_score, "blocking_issues": page_issues, "warnings": rhythm_warnings}
    write_json_atomic(spec_json, audited_spec)
    review_summary = project / VISUAL_FILES["review_summary"]
    review_summary.write_text(_render_visual_review_summary(audited_spec, _read_json(decisions), {"deck_rhythm": results["deck_rhythm"]}), encoding="utf-8")
    prompt_inputs = _prompt_inputs_sha256(project, script, skill_root)
    previous_inputs = previous_report.get("prompt_inputs_sha256")
    previous_inputs = previous_inputs if isinstance(previous_inputs, dict) else {}
    rebuild_reasons = [
        key
        for key, value in prompt_inputs.items()
        if previous_inputs.get(key) != value
    ]
    if not prompts.is_file():
        rebuild_reasons.append("generation_prompts_missing")
    elif previous_report.get("artifact_sha256", {}).get("generation_prompts") != _sha256(prompts):
        rebuild_reasons.append("generation_prompts_hash")
    rebuild_reasons = list(dict.fromkeys(rebuild_reasons))
    prompt_rebuilt = False
    if pre_prompt_passed and rebuild_reasons:
        subprocess.run(
            [sys.executable, str(prompt_builder), str(spec_json), "--output", str(prompts)],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        prompt_rebuilt = True
    if pre_prompt_passed and prompts.is_file():
        results["prompt_freshness"] = {
            "status": "passed",
            "rebuilt": prompt_rebuilt,
            "rebuild_reasons": rebuild_reasons,
            "generation_prompts_sha256": _sha256(prompts),
        }
    else:
        results["prompt_freshness"] = {
            "status": "failed",
            "rebuilt": False,
            "rebuild_reasons": rebuild_reasons,
            "blocking_issues": [
                {
                    "code": "PROMPT_REBUILD_BLOCKED",
                    "message": "Prompt rebuild is blocked until the visual decision package and execution receipt pass.",
                }
            ],
        }
    passed = all(result.get("status") == "passed" for result in results.values())
    contracts = prompt_contract_hashes(skill_root)
    report = {
        "schema": "cyberppt.visual_structure_stage.v2",
        "build_id": f"visual-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{_sha256(script)[:10]}",
        "status": "passed" if passed else "failed",
        "validated_at": _utc_now(),
        "skill": "ppt-visual-structure-designer",
        "skill_sha256": _sha256(skill_root / "SKILL.md"),
        "skill_bundle_sha256": contracts["skill_bundle"],
        "skill_contract_sha256": contracts,
        "script": str(script),
        "script_sha256": _sha256(script),
        "script_semantic_sha256": script_semantic_digest(script),
        "stage02_handoff": str(handoff_path) if handoff is not None else None,
        "stage02_handoff_sha256": _sha256(handoff_path),
        "artifacts": {key: str(project / value) for key, value in VISUAL_FILES.items() if key != "validation"},
        "artifact_sha256": {
            key: _sha256(project / relative)
            for key, relative in VISUAL_FILES.items()
            if key != "validation" and (project / relative).is_file()
        },
        "prompt_inputs_sha256": prompt_inputs,
        "prompt_rebuilt": prompt_rebuilt,
        "prompt_rebuild_reasons": rebuild_reasons,
        "results": results,
    }
    if isinstance(previous_report.get("semantic_review"), dict):
        report["semantic_review"] = previous_report["semantic_review"]
    write_json_atomic(report_path, report)
    _register_visual_artifacts(project, script, report_path, build_id=str(report["build_id"]))
    return (0 if passed else 1), report


def _register_visual_artifacts(
    project: Path,
    script: Path,
    report_path: Path,
    *,
    build_id: str,
) -> None:
    ledger_path = project / "workbench" / "artifact-ledger.json"
    registered_paths = [
        VISUAL_FILES["design_input"],
        VISUAL_FILES["skill_request"],
        VISUAL_FILES["skill_invocation"],
        VISUAL_FILES["decisions"],
        VISUAL_FILES["execution_receipt"],
        VISUAL_FILES["spec_json"],
        VISUAL_FILES["spec_markdown"],
        VISUAL_FILES["review_summary"],
        VISUAL_FILES["generation_prompts"],
        VISUAL_FILES["validation"],
    ]
    try:
        script_dependency = script.relative_to(project).as_posix()
    except ValueError:
        script_dependency = str(script)
    resume = f"python -m cyberppt visual-structure-audit {project} --script {script}"
    records: list[dict[str, Any]] = []
    status = "passed" if _read_json(report_path).get("status") == "passed" else "failed"
    for relative in registered_paths:
        path = project / relative
        if not path.is_file():
            continue
        records.append(
            {
                "stage": "02-visual-structure",
                "page": None,
                "path": relative.as_posix(),
                "status": status,
                "depends_on": [script_dependency],
                "resume_command": resume,
                "sha256": _sha256(path),
            }
        )
    append_artifacts(ledger_path, records, build_id=build_id)


def assert_visual_structure_ready(project: Path, script: Path) -> Path | None:
    project = project.expanduser().resolve()
    script = script.expanduser().resolve()
    if not visual_structure_required(project):
        return None
    report_path = project / VISUAL_FILES["validation"]
    if not report_path.is_file():
        raise FileNotFoundError(
            "required visual structure stage is missing; prepare the Skill request, execute "
            "ppt-visual-structure-designer, record its execution, and run visual-structure-audit before Stage 02"
        )
    report = _read_json(report_path)
    from cyberppt.stage02_handoff import load_stage02_handoff

    handoff = load_stage02_handoff(project, required=True)
    script_binding = (handoff.get("source_bindings") or {}).get("script")
    if not isinstance(script_binding, dict) or not script_binding.get("path"):
        raise ValueError("Stage 02 handoff is missing its script binding")
    bound_script = Path(str(script_binding["path"])).expanduser().resolve()
    if (
        bound_script != script
        or script_binding.get("sha256") != _sha256(script)
    ):
        raise ValueError(
            "Stage 02 handoff is bound to a different script; prepare the handoff and visual structure again."
        )
    for key in (
        "design_input",
        "skill_request",
        "decisions",
        "execution_receipt",
        "spec_json",
        "spec_markdown",
        "review_summary",
        "generation_prompts",
    ):
        path = project / VISUAL_FILES[key]
        if not path.is_file() or report.get("artifact_sha256", {}).get(key) != _sha256(path):
            raise ValueError(f"visual structure artifact is missing or changed: {path}")

    handoff_path = project / Path("workbench/stages/02-handoff/stage02-handoff.json")
    design_input = _read_json(project / VISUAL_FILES["design_input"])
    if design_input.get("source_sha256") != _sha256(handoff_path):
        raise ValueError(
            "visual structure design input is stale: it was compiled from a different Stage 02 handoff"
        )

    handoff_pages = {
        str(page.get("page_id")): page
        for page in handoff.get("pages") or []
        if isinstance(page, dict) and page.get("page_id")
    }
    spec = _read_json(project / VISUAL_FILES["spec_json"])
    for page in spec.get("pages") or []:
        if not isinstance(page, dict):
            continue
        page_id = str(page.get("page_id") or "")
        source_page = handoff_pages.get(page_id.lower()) or handoff_pages.get(page_id.upper())
        if source_page is None or source_page.get("render_role") != "content":
            continue
        generation_handoff = page.get("generation_handoff")
        if not isinstance(generation_handoff, dict):
            raise ValueError(f"visual structure page {page_id} is missing generation_handoff")
        expected_text = [str(value) for value in source_page.get("onscreen_items") or []]
        actual_text = [str(value) for value in generation_handoff.get("required_text") or []]
        if actual_text != expected_text:
            raise ValueError(
                f"visual structure required_text drifted from final-script onscreen_text: {page_id}"
            )
    return report_path

"""Deterministic audit for Stage 02 Region Graph structure and bindings."""

from __future__ import annotations

from typing import Any, Mapping

from cyberppt.region_graph import validate_region_graph


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _validation_code(message: str) -> str:
    lowered = message.lower()
    if "weight" in lowered:
        return "REGION_WEIGHT_INVALID"
    if "relation" in lowered or "unknown region" in lowered:
        return "REGION_RELATION_INVALID"
    if "role" in lowered:
        return "REGION_ROLE_INVALID"
    return "REGION_GRAPH_INVALID"


def audit_region_graph(page_spec: Mapping[str, object]) -> list[dict[str, str]]:
    """Audit Region Graph without inventing a replacement visual structure.

    Legacy specs with no Region Graph and no RG-prefixed final-text binding stay
    readable. Current compiler output binds final text to RGxx; removing its
    Region Graph therefore becomes a deterministic blocking error.
    """

    issues: list[dict[str, str]] = []
    raw_graph = page_spec.get("region_graph")
    final_text = [item for item in page_spec.get("final_text") or [] if isinstance(item, Mapping)]
    rg_bound_text = any(str(item.get("region_id") or "").startswith("RG") for item in final_text)
    if not isinstance(raw_graph, Mapping):
        if rg_bound_text:
            issues.append(_issue(
                "REGION_GRAPH_MISSING",
                "Current Region Graph text bindings exist but region_graph is missing.",
            ))
        return issues

    try:
        graph = validate_region_graph(raw_graph).to_dict()
    except ValueError as exc:
        message = str(exc)
        issues.append(_issue(_validation_code(message), message))
        return issues

    regions = graph["regions"]
    relations = graph["relations"]
    region_ids = {item["id"] for item in regions}
    evidence_items = [item for item in page_spec.get("evidence_units") or [] if isinstance(item, Mapping)]
    p0_ids = {
        str(item.get("id") or "")
        for item in evidence_items
        if item.get("priority") == "P0" and str(item.get("id") or "")
    }
    evidence_owners: dict[str, list[str]] = {}
    text_owners: dict[str, list[str]] = {}
    for region in regions:
        region_id = region["id"]
        for evidence_id in region["semantic_refs"]:
            evidence_owners.setdefault(evidence_id, []).append(region_id)
        for text_id in region.get("text_ids") or []:
            text_owners.setdefault(str(text_id), []).append(region_id)

    missing_p0 = sorted(evidence_id for evidence_id in p0_ids if len(evidence_owners.get(evidence_id, [])) != 1)
    if missing_p0:
        issues.append(_issue(
            "REGION_BINDING_MISSING",
            f"P0 evidence must belong to exactly one Region Graph region: {missing_p0}",
        ))

    handoff = page_spec.get("generation_handoff")
    handoff = handoff if isinstance(handoff, Mapping) else {}
    required_text_ids = [str(value) for value in handoff.get("required_text_ids") or []]
    bad_text = [text_id for text_id in required_text_ids if len(text_owners.get(text_id, [])) != 1]
    extras = sorted(set(text_owners) - set(required_text_ids))
    if bad_text or extras:
        issues.append(_issue(
            "REGION_BINDING_MISSING",
            f"Locked text must have exact Region Graph ownership: missing_or_duplicate={bad_text}, extra={extras}",
        ))

    final_region_by_text = {
        str(item.get("id") or ""): str(item.get("region_id") or "")
        for item in final_text
        if str(item.get("id") or "")
    }
    drifted = [
        text_id
        for text_id in required_text_ids
        if text_owners.get(text_id)
        and final_region_by_text.get(text_id) != text_owners[text_id][0]
    ]
    if drifted:
        issues.append(_issue(
            "REGION_BINDING_MISSING",
            f"final_text.region_id must match Region Graph text ownership: {drifted}",
        ))

    semantic_graph = page_spec.get("semantic_graph")
    semantic_graph = semantic_graph if isinstance(semantic_graph, Mapping) else {}
    topology = str(semantic_graph.get("topology") or "")
    focus_id = str(semantic_graph.get("focus_node") or "")
    focus_regions = [item for item in regions if focus_id in item["semantic_refs"]]
    focus_region = focus_regions[0] if len(focus_regions) == 1 else None
    visual_decision = page_spec.get("visual_decision")
    visual_decision = visual_decision if isinstance(visual_decision, Mapping) else {}
    focus_policy = str(visual_decision.get("focus_policy") or "")

    expected_roles: dict[str, set[str]] = {
        "parallel_set": {"peer"},
        "causal_convergence": {"source", "result"},
        "layered_architecture": {"layer"},
        "directed_flow": {"stage", "result"},
        "lifecycle_loop": {"lifecycle_stage"},
        "governance_boundary": {"boundary_anchor", "boundary_participant"},
        "ecosystem_map": {"actor"},
        "allocation_flow": {"source", "destination"},
        "conclusion_anchor": {"evidence", "conclusion"},
    }
    allowed_roles = expected_roles.get(topology)
    if allowed_roles is None:
        issues.append(_issue("REGION_TOPOLOGY_MISMATCH", f"Unsupported Region Graph topology: {topology!r}"))
        return issues
    invalid_roles = [item["id"] for item in regions if item["role"] not in allowed_roles]
    if invalid_roles:
        issues.append(_issue(
            "REGION_ROLE_INVALID",
            f"Region roles do not match topology {topology}: {invalid_roles}",
        ))

    relation_types = [item["type"] for item in relations]
    incoming_to_focus = []
    if focus_region:
        incoming_to_focus = [item for item in relations if item["to"] == focus_region["id"]]

    mismatch = ""
    if topology == "parallel_set":
        weights = [float(item["weight"]) for item in regions]
        if focus_policy != "peer_field" or any(item["priority"] != "primary" for item in regions):
            mismatch = "parallel_set must retain peer_field with all peer regions primary"
        elif weights and max(weights) - min(weights) > 0.02:
            issues.append(_issue("REGION_WEIGHT_INVALID", "parallel_set peer regions must have comparable weights"))
        elif any(item["type"] != "peer" for item in relations):
            mismatch = "parallel_set relations must remain peer relations"
    elif topology == "causal_convergence":
        if not focus_region or focus_region["role"] != "result" or len([item for item in incoming_to_focus if item["type"] == "converge"]) < 2:
            mismatch = "causal_convergence requires at least two convergence relations into the result region"
    elif topology == "layered_architecture":
        if len([item for item in relations if item["type"] == "dependency"]) < max(0, len(regions) - 1):
            mismatch = "layered_architecture requires a continuous dependency region chain"
    elif topology == "directed_flow":
        if len([item for item in relations if item["type"] == "flow"]) < max(0, len(regions) - 1):
            mismatch = "directed_flow requires a continuous flow region chain"
    elif topology == "lifecycle_loop":
        if "feedback" not in relation_types:
            mismatch = "lifecycle_loop requires a feedback region relation"
    elif topology == "governance_boundary":
        if not focus_region or focus_region["role"] != "boundary_anchor" or "boundary" not in relation_types:
            mismatch = "governance_boundary requires a boundary anchor and boundary relation"
    elif topology == "ecosystem_map":
        if any(item["anchor"] == "center" for item in regions):
            mismatch = "ecosystem_map must not invent a center region without source authority"
    elif topology == "allocation_flow":
        source_regions = [item for item in regions if item["role"] == "source"]
        if len(source_regions) != 1 or not any(item["from"] == source_regions[0]["id"] and item["type"] == "allocation" for item in relations):
            mismatch = "allocation_flow requires one source region with allocation relations to destinations"
    elif topology == "conclusion_anchor":
        if not focus_region or focus_region["role"] != "conclusion" or not incoming_to_focus:
            mismatch = "conclusion_anchor requires evidence relations into one conclusion region"

    if mismatch:
        issues.append(_issue("REGION_TOPOLOGY_MISMATCH", mismatch))

    invalid_endpoints = [
        item for item in relations
        if item["from"] not in region_ids or item["to"] not in region_ids
    ]
    if invalid_endpoints:
        issues.append(_issue("REGION_RELATION_INVALID", "Region Graph relation references an unknown region"))
    return issues


__all__ = ["audit_region_graph"]

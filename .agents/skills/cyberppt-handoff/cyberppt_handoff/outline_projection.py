from __future__ import annotations

from typing import Any, Iterable

from .mappings import CHAIN_ROLE_TO_DUTY, PAGE_ROLE, VISUAL_INTENT
from .source_projection import _anchors
from .semantic_projection import layer_four_page_node_id

POLICY_FIELDS = (
    "writing_style_mode",
    "source_structure_mode",
    "source_title_mode",
    "source_order_mode",
    "source_content_mode",
    "capacity_split_allowed",
    "duplicate_content_merge_allowed",
    "reframing_requires_explicit_user_request",
    "agenda_mode",
)


def _project_planning_policy(
    payloads: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    workpack_policy = (payloads.get("workpack") or {}).get("planning_policy") or {}
    task = payloads["deck"].get("task_understanding") or {}
    return {
        field: workpack_policy[field] if field in workpack_policy else task[field]
        for field in POLICY_FIELDS
        if field in workpack_policy or field in task
    }


def _project_page_relationships(
    page: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    nf_to_st: dict[str, str],
) -> list[dict[str, Any]]:
    evidence = page.get("evidence") if isinstance(page.get("evidence"), dict) else {}
    relation_ids = [str(value) for value in evidence.get("relation_ids") or []]
    if not relation_ids:
        return []
    allowed_fact_ids = {
        str(value) for value in evidence.get("normalized_fact_ids") or []
    }
    relation_by_id = {
        str(item.get("relation_id")): item
        for item in payloads["relations"].get("relations") or []
        if isinstance(item, dict) and item.get("relation_id")
    }
    concept_by_id = {
        str(item.get("concept_id")): item
        for item in payloads["concepts"].get("concepts") or []
        if isinstance(item, dict) and item.get("concept_id")
    }
    relationships: list[dict[str, Any]] = []
    for relation_id in relation_ids:
        relation = relation_by_id.get(relation_id)
        if relation is None:
            raise ValueError(f"page references unknown relation: {relation_id}")
        from_id = str(relation.get("from_concept_id") or "")
        to_id = str(relation.get("to_concept_id") or "")
        from_concept = concept_by_id.get(from_id)
        to_concept = concept_by_id.get(to_id)
        if from_concept is None or not str(from_concept.get("canonical_name") or "").strip():
            raise ValueError(
                f"relation references unknown or unnamed concept: {from_id}"
            )
        if to_concept is None or not str(to_concept.get("canonical_name") or "").strip():
            raise ValueError(
                f"relation references unknown or unnamed concept: {to_id}"
            )
        relation_fact_ids = [
            str(value)
            for value in relation.get("normalized_fact_ids") or []
            if str(value) in allowed_fact_ids
        ]
        relationships.append(
            {
                "subject": str(from_concept["canonical_name"]).strip(),
                "relation": str(relation.get("relation_type") or "").strip(),
                "objects": [str(to_concept["canonical_name"]).strip()],
                "direction": str(
                    relation.get("direction") or "subject_to_objects"
                ).strip(),
                "condition": str(relation.get("condition") or "").strip(),
                "modality": str(relation.get("modality") or "").strip(),
                "basis": str(relation.get("basis") or "").strip(),
                "confidence": str(relation.get("confidence") or "").strip(),
                "source_refs": [
                    nf_to_st[nf_id]
                    for nf_id in relation_fact_ids
                    if nf_id in nf_to_st
                ],
                "authority_ref": relation_id,
            }
        )
    return relationships


def _expand_evidence_ids(
    ids: Iterable[str],
    payloads: dict[str, dict[str, Any]],
    nf_to_st: dict[str, str],
    *,
    allowed_fact_ids: set[str] | None = None,
) -> list[str]:
    relation_by_id = {str(item.get("relation_id")): item for item in payloads["relations"].get("relations") or [] if isinstance(item, dict)}
    arg_by_id = {str(item.get("node_id")): item for group in (payloads["argument"].get("source_chain") or [], payloads["argument"].get("reconstructed_chain") or []) for item in group if isinstance(item, dict)}
    nfs: set[str] = set()
    for raw in ids:
        value = str(raw)
        if value in nf_to_st:
            nfs.add(value)
        elif value in relation_by_id:
            nfs.update(str(x) for x in relation_by_id[value].get("normalized_fact_ids") or [])
        elif value in arg_by_id:
            nfs.update(str(x) for x in arg_by_id[value].get("normalized_fact_ids") or [])
    if allowed_fact_ids is not None:
        nfs.intersection_update(allowed_fact_ids)
    return [nf_to_st[nf] for nf in sorted(nfs) if nf in nf_to_st]

def _project_evidence_roles(
    roles: dict[str, Any],
    payloads: dict[str, dict[str, Any]],
    nf_to_st: dict[str, str],
    direct_fact_ids: list[str],
) -> list[dict[str, Any]]:
    role_order = ("claim", "reason", "instance", "boundary", "trace_only")
    semantic_role: dict[str, str] = {}
    for role_name in role_order:
        for value in roles.get(role_name) or []:
            semantic_role[str(value)] = role_name
    relation_by_id = {str(item.get("relation_id")): item for item in payloads["relations"].get("relations") or [] if isinstance(item, dict)}
    arg_by_id = {str(item.get("node_id")): item for group in (payloads["argument"].get("source_chain") or [], payloads["argument"].get("reconstructed_chain") or []) for item in group if isinstance(item, dict)}
    grouped: dict[str, list[str]] = {name: [] for name in role_order}
    for nf_id in direct_fact_ids:
        nf_id = str(nf_id)
        role_name = semantic_role.get(nf_id)
        if role_name is None:
            for candidate_role in role_order:
                candidate_ids = [str(value) for value in roles.get(candidate_role) or []]
                if any(nf_id in [str(x) for x in relation_by_id.get(value, {}).get("normalized_fact_ids") or []] for value in candidate_ids):
                    role_name = candidate_role
                    break
                if any(nf_id in [str(x) for x in arg_by_id.get(value, {}).get("normalized_fact_ids") or []] for value in candidate_ids):
                    role_name = candidate_role
                    break
        role_name = role_name or "reason"
        st_id = nf_to_st.get(nf_id)
        if st_id and st_id not in grouped[role_name]:
            grouped[role_name].append(st_id)
    return [{"role": name, "source_refs": grouped[name]} for name in role_order if grouped[name]]


def _normalize_evidence_roles(value: Any) -> dict[str, list[str]]:
    """Normalize explicit role records without deriving roles from chain order."""

    role_order = ("claim", "reason", "instance", "boundary", "trace_only")
    if isinstance(value, dict):
        return {
            role: [str(item) for item in value.get(role) or [] if str(item)]
            for role in role_order
        }
    normalized = {role: [] for role in role_order}
    if isinstance(value, list):
        for item in value:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "")
            if role not in normalized:
                continue
            normalized[role].extend(
                str(ref) for ref in item.get("source_refs") or [] if str(ref)
            )
    return normalized

def _cyber_page_id(page: dict[str, Any]) -> str:
    return f"p{int(page.get('order') or 0):02d}"

def _project_outline(payloads: dict[str, dict[str, Any]], source_truth: dict[str, Any], semantic_model: dict[str, Any], nf_to_st: dict[str, str]) -> tuple[dict[str, Any], dict[str, str]]:
    deck = payloads["deck"]
    page_plan = payloads["page_plan"]
    strategy = deck.get("deck_strategy") or {}
    task = deck.get("task_understanding") or {}
    page_map = {str(page.get("page_id")): _cyber_page_id(page) for page in page_plan.get("pages") or [] if isinstance(page, dict)}
    chapter_map: dict[str, str] = {}
    divider_section_ids = {
        str(page.get("section_id"))
        for page in page_plan.get("pages") or []
        if isinstance(page, dict)
        and page.get("page_type") == "template"
        and str(page.get("template_kind") or page.get("template_role") or "")
        == "section_divider"
        and page.get("section_id")
    }
    for index, section in enumerate(deck.get("sections") or [], start=1):
        if isinstance(section, dict) and section.get("section_id"):
            section_id = str(section["section_id"])
            if section_id in divider_section_ids:
                chapter_map[section_id] = f"C{index}"
    st_by_id = {str(item.get("id")): item for item in source_truth.get("records") or [] if isinstance(item, dict)}
    semantic_nodes = {str(item.get("id")): item for group in (semantic_model.get("section_nodes") or [], semantic_model.get("subsection_nodes") or []) for item in group if isinstance(item, dict)}
    argument_by_id = {str(item.get("node_id")): item for item in payloads["argument"].get("reconstructed_chain") or [] if isinstance(item, dict)}
    pages_out: list[dict[str, Any]] = []
    for page in page_plan.get("pages") or []:
        if not isinstance(page, dict):
            continue
        cyber_id = _cyber_page_id(page)
        if page.get("page_type") == "template":
            kind_map = {"cover": "cover", "agenda": "agenda", "section_divider": "chapter", "closing": "ending"}
            template_kind = str(page.get("template_kind") or page.get("template_role") or "cover")
            item = {"page_id": cyber_id, "sequence": int(page.get("order") or 0), "page_type": kind_map.get(template_kind, template_kind), "title": str(page.get("title_intent") or ""), "page_mission": str(page.get("page_mission") or ""), "projection_only": True, "authority_ref": str(page.get("page_id") or "")}
            if page.get("section_id") in chapter_map:
                item["chapter_id"] = chapter_map[str(page.get("section_id"))]
            pages_out.append(item)
            continue
        page_evidence = page.get("evidence") if isinstance(page.get("evidence"), dict) else {}
        direct_fact_ids = [str(value) for value in page_evidence.get("normalized_fact_ids") or []]
        allowed_fact_ids = set(direct_fact_ids)
        source_refs = [nf_to_st[nf_id] for nf_id in direct_fact_ids if nf_id in nf_to_st]
        roles = _normalize_evidence_roles(page.get("evidence_roles"))
        evidence_roles_out = _project_evidence_roles(roles, payloads, nf_to_st, direct_fact_ids)
        evidence_roles_dict = {
            item["role"]: item["source_refs"] for item in evidence_roles_out
        }
        chain_out: list[dict[str, Any]] = []
        content_units: list[dict[str, Any]] = []
        for index, node in enumerate(page.get("argument_chain") or [], start=1):
            if not isinstance(node, dict):
                continue
            evidence = node.get("evidence") if isinstance(node.get("evidence"), dict) else {}
            node_ids = [*(evidence.get("normalized_fact_ids") or []), *(evidence.get("relation_ids") or []), *(evidence.get("argument_node_ids") or [])]
            node_refs = _expand_evidence_ids(node_ids, payloads, nf_to_st, allowed_fact_ids=allowed_fact_ids)
            role = str(node.get("role") or "support")
            chain_out.append({"role": role, "statement": str(node.get("statement") or ""), "source_refs": node_refs})
            role_membership = [name for name in ("claim", "reason", "instance", "boundary", "trace_only") if set(node_ids).intersection(set(roles.get(name) or []))]
            primary_role = next(iter(role_membership), "reason") if len(role_membership) == 1 else "reason"
            unit_role = "primary" if primary_role == "claim" else "boundary" if primary_role == "boundary" else "supporting"
            onscreen = primary_role in {"claim", "reason", "instance"}
            # Split each cited statement into its natural clauses (on Chinese
            # punctuation) instead of blindly slicing the first N characters.
            # A raw character cut mid-clause forces a full-length source
            # sentence onto the slide to satisfy anchor coverage; a PPT page
            # is not a Word paragraph and must stay phrase/structured.
            anchors = []
            for st_id in node_refs:
                statement = str(st_by_id.get(st_id, {}).get("statement") or "")
                if not statement:
                    continue
                for chunk in _anchors(statement, []):
                    # A clause without an early comma can still run long; cap it
                    # so the anchor stays achievable inside a short on-screen
                    # phrase instead of forcing a full source clause onto the
                    # slide.
                    chunk = chunk[:20]
                    if chunk and chunk not in anchors:
                        anchors.append(chunk)
            if len(anchors) < 2:
                anchors.extend(chunk[:20] for chunk in _anchors(str(node.get("statement") or ""), []))
            anchors = list(dict.fromkeys(anchors))[:2]
            content_units.append({
                "unit_id": f"{cyber_id}-U{index:02d}", "statement": str(node.get("statement") or ""), "source_refs": node_refs,
                "role": unit_role, "importance": unit_role, "full_prose_required": primary_role != "trace_only", "coverage_anchors": anchors,
                "argument_duties": [CHAIN_ROLE_TO_DUTY.get(role, "detail")], "onscreen_required": onscreen, "onscreen_anchors": anchors if onscreen else [], "authority_refs": [str(x) for x in node_ids],
            })
        role_map = {item["role"]: item["source_refs"] for item in evidence_roles_out}
        detail_refs = list(role_map.get("trace_only", []))
        boundary_refs = list(role_map.get("boundary", []))
        requested_arg_ids = [str(x) for x in page_evidence.get("argument_node_ids") or []]
        page_node_id = layer_four_page_node_id(page)
        arg_ids = [page_node_id] if page_node_id in semantic_nodes else []
        for arg_id in requested_arg_ids:
            node_fact_ids = {str(value) for value in argument_by_id.get(arg_id, {}).get("normalized_fact_ids") or []}
            if node_fact_ids and node_fact_ids.issubset(allowed_fact_ids):
                arg_ids.append(arg_id)
        primary_arg = page_node_id if page_node_id in arg_ids else (arg_ids[0] if arg_ids else "")
        reserved_items = page.get("reserved_for_later") if isinstance(page.get("reserved_for_later"), list) else []
        reserved_text = "；".join(f"{item.get('topic')} → {page_map.get(str(item.get('target_page')), str(item.get('target_page')))}" for item in reserved_items if isinstance(item, dict)) or "无"
        allowed_claim_roles = sorted({str(st_by_id.get(ref, {}).get("claim_role") or "fact") for ref in source_refs})
        receipt = page.get("judgment_derivation") or page.get("core_message_derivation")
        if not isinstance(receipt, dict):
            receipt = {
                "source_refs": source_refs,
                "supporting_statements": [
                    str(node.get("statement") or "")
                    for node in page.get("argument_chain") or []
                    if isinstance(node, dict)
                ],
                "derivation": f"Projection of layer-four judgment_basis={page.get('judgment_basis')}",
                "introduced_relations": list(page_evidence.get("relation_ids") or []) if page.get("judgment_basis") == "planning_inference" else [],
                "introduced_modalities": [],
            }
        receipt_refs = _expand_evidence_ids(
            [str(value) for value in receipt.get("source_refs") or []],
            payloads,
            nf_to_st,
            allowed_fact_ids=allowed_fact_ids,
        )
        item = {
            "page_id": cyber_id, "sequence": int(page.get("order") or 0), "page_type": "content",
            "title": str(page.get("title_intent") or ""), "page_mission": str(page.get("page_mission") or ""), "page_job": str(page.get("page_mission") or ""),
            "audience_question": str(page.get("audience_question") or ""), "business_question": str(page.get("audience_question") or ""),
            "core_message": str(page.get("key_judgment") or ""), "non_substitutable_value": str(page.get("non_substitutable_value") or ""),
            "topic_category": str(page.get("title_intent") or ""), "must_not_include": list(page.get("must_not_include") or []),
            "split_risk": str(page.get("split_risk") or "low"), "new_value_vs_previous": str(page.get("non_substitutable_value") or ""),
            "reserved_for_later": reserved_text, "reserved_for_later_items": reserved_items,
            "storyline_role": str(page.get("argument_role") or ""), "transition_from_previous": str(page.get("transition_from_previous") or ""), "transition_to_next": str(page.get("transition_to_next") or ""),
            "page_order_reason": "Preserve validated layer-four page order; no re-planning in adapter.",
            "argument_role": PAGE_ROLE.get(str(page.get("argument_role") or "other"), "solution"), "allowed_claim_roles": allowed_claim_roles, "forbidden_claim_roles": [],
            "prerequisite_pages": [page_map.get(str((page_plan.get("pages") or [])[int(page.get("order") or 1)-2].get("page_id")))] if int(page.get("order") or 1) > 1 and isinstance((page_plan.get("pages") or [])[int(page.get("order") or 1)-2], dict) else [],
            "main_claim_status": "proposed" if page.get("judgment_basis") == "planning_inference" else "confirmed", "confirmation_scope": "source_supported_only",
            "primary_argument_node_id": primary_arg, "source_argument_node_ids": arg_ids, "context_argument_node_ids": [arg_id for arg_id in requested_arg_ids if arg_id not in arg_ids], "source_evidence_node_ids": [],
            "source_argument_node_roles": {arg_id: str(semantic_nodes.get(arg_id, {}).get("argument_role") or "other") for arg_id in arg_ids},
            "source_argument_node_weights": {arg_id: str(semantic_nodes.get(arg_id, {}).get("argument_weight") or "detail") for arg_id in arg_ids},
            "source_argument_node_statuses": {arg_id: str(semantic_nodes.get(arg_id, {}).get("status") or "mixed") for arg_id in arg_ids},
            "source_gap_ids": [], "gap_handling": "Preserve upstream diagnostics and epistemic boundaries; adapter adds no gap inference.",
            "core_message_derivation": {"source_refs": receipt_refs, "supporting_statements": [str(value) for value in receipt.get("supporting_statements") or []], "derivation": str(receipt.get("derivation") or ""), "introduced_relations": list(receipt.get("introduced_relations") or []), "introduced_modalities": list(receipt.get("introduced_modalities") or []), "argument_node_ids": arg_ids},
            "source_refs": source_refs, "detail_refs": detail_refs, "boundary_refs": boundary_refs, "content_units": content_units,
            "content_relations": _project_page_relationships(
                page, payloads, nf_to_st
            ),
            "visual_intent_type": VISUAL_INTENT.get(str(page.get("content_strategy") or "other"), "judgment_evidence"),
            "page_necessity": str(page.get("non_substitutable_value") or ""), "argument_chain": chain_out, "evidence_roles": evidence_roles_dict,
            "excluded_from_onscreen": detail_refs, "projection_only": True, "authority_ref": str(page.get("page_id") or ""),
        }
        if page.get("split_risk_reason"):
            item["split_risk_reason"] = str(page["split_risk_reason"])
        if page.get("inference_rationale"):
            item["planning_inference_rationale"] = str(page["inference_rationale"])
        for field in (
            "source_heading_ids",
            "primary_source_heading_id",
            "subtitle_policy",
            "judgment_role",
        ):
            if field in page:
                value = page[field]
                item[field] = list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value
        if str(page.get("section_id") or "") in chapter_map:
            item["chapter_id"] = chapter_map[str(page.get("section_id"))]
        pages_out.append(item)
    section_by_id = {str(item.get("section_id")): item for item in deck.get("sections") or [] if isinstance(item, dict)}
    chapter_missions = []
    chapter_orders = []
    for sec_id, chapter_id in chapter_map.items():
        section = section_by_id.get(sec_id, {})
        page_ids = [page_map.get(str(pid), str(pid)) for pid in section.get("page_ids") or []]
        chapter_missions.append({"chapter_id": chapter_id, "chapter_question": str(section.get("section_mission") or ""), "mission": str(section.get("section_thesis") or ""), "topic_categories": [str(next((page.get("title_intent") for page in page_plan.get("pages") or [] if isinstance(page, dict) and str(page.get("page_id")) == str(pid)), "")) for pid in section.get("page_ids") or []], "max_content_pages": len(page_ids)})
        chapter_orders.append({"chapter_id": chapter_id, "ordering_principles": ["validated_layer_four_order"], "ordered_page_ids": page_ids, "rationale": "Projected exactly from validated deck section page_ids."})
    dispositions = []
    for node in semantic_model.get("subsection_nodes") or []:
        if not isinstance(node, dict):
            continue
        consumer = str(node.get("primary_consumer") or "")
        if consumer:
            dispositions.append({"node_id": str(node.get("id")), "disposition": "merged_page", "page_id": consumer, "rationale": "Projected from layer-four evidence assignment; no new page decision made.", "merge_reason": "Compatibility projection only.", "shared_page_topic": str(next((page.get("title") for page in pages_out if page.get("page_id") == consumer), ""))})
    outline = {
        "schema": "cyberppt.outline.v2", "authority_mode": "projection_only", "material_type": str(strategy.get("deck_type") or "formal"), "audience": str(task.get("audience") or ""),
        "communication_goal": str(task.get("purpose") or ""), "communication_purpose": str(task.get("purpose") or ""), "decision_task": str(strategy.get("core_question") or ""),
        "architecture_mode": "solution", "architecture_reason": "Compatibility projection of an already validated layer-four deck; no CyberPPT re-planning is performed.",
        "structure_principle": str(strategy.get("narrative_mode") or "custom"), "title_style_mode": "formal_plain", "argument_contract_mode": "projection",
        "core_message_derivation_mode": "required", "topic_partition_mode": "required", "page_sequence_mode": "required", "argument_node_disposition_mode": "projection",
        "page_content_unit_coverage_mode": "required", "editorial_control_mode": "projection", "editorial_authoring_mode": "projection", "editorial_authoring_status": "validated_upstream",
        "storyline_contract_mode": "projection", "semantic_argument_model_mode": "projection", "source_truth_mapping_mode": "frozen", "source_section_weights": {},
        "document_semantics": semantic_model.get("document_semantics") or {}, "narrative_thesis": str(strategy.get("deck_thesis") or ""),
        "storyline": {"theme": str(strategy.get("deck_thesis") or ""), "decision_destination": str(task.get("purpose") or ""), "story_arc": [str(item.get("section_thesis") or "") for item in deck.get("sections") or [] if isinstance(item, dict)], "chapter_missions": chapter_missions, "selection_rules": ["Consume validated layer-four page architecture without re-planning."], "exclusion_rules": ["Do not upgrade inferred or unverified upstream claims."], "page_rules": ["One audience question, one core message, one governing argument chain per content page."]},
        "chapter_page_orders": chapter_orders, "argument_node_dispositions": dispositions, "pages": pages_out,
    }
    planning_policy = _project_planning_policy(payloads)
    if planning_policy:
        outline["planning_policy"] = planning_policy
    return outline, page_map

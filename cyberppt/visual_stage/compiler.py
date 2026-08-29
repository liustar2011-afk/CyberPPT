from __future__ import annotations

from copy import deepcopy
import re
from pathlib import Path
from typing import Any

from cyberppt.page_artifact_spec import is_text_dense
from cyberppt.region_graph import build_region_graph
from cyberppt.region_binding import bind_region_graph_text, region_text_owner_map
from cyberppt.visual_medium_policy import resolve_visual_medium_policy
from cyberppt.onscreen_expression import expression_constraints, expression_constraints_sha256
from cyberppt.topology_resolver import CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY

from .persistence import VISUAL_FILES, _read_json, _sha256, write_json


_DIRECTION_MAP = {
    "left_to_right": "left_to_right",
    "right_to_left": "right_to_left",
    "top_to_bottom": "top_to_bottom",
    "bottom_to_top": "bottom_to_top",
    "outside_to_anchor": "outside_to_center",
    "two_sides_to_interface": "outside_to_center",
    "validation_to_decision_branches": "left_to_right",
}

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
_UNIVERSAL_FORBIDDEN_STRUCTURES = ["invented_center_hub"]
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

ALLOWED_FOCUS_POLICIES = {
    "single_anchor",
    "paired_focus",
    "peer_field",
    "distributed_focus",
    "sequence_focus",
}

ALLOWED_SCENE_POLICIES = {
    "required",
    "allowed",
    "forbidden",
    "auto",
}

_FOCUS_POLICY_BY_TOPOLOGY = {
    "parallel_set": "peer_field",
    "causal_convergence": "single_anchor",
    "layered_architecture": "sequence_focus",
    "directed_flow": "sequence_focus",
    "lifecycle_loop": "sequence_focus",
    "governance_boundary": "paired_focus",
    "ecosystem_map": "distributed_focus",
    "allocation_flow": "sequence_focus",
    "conclusion_anchor": "single_anchor",
}

_CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY = CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY


def _connector_relation(topology: str, grammar: list[str], visual_intent: str) -> str:
    """Map the selected carrier to its connector semantics.

    ``reading_sequence`` is a placement order.  It becomes a business edge
    only for a topology whose contract explicitly describes progression.
    """
    if topology == "parallel_set":
        return "peer"
    if topology in {"causal_convergence", "conclusion_anchor"}:
        return "converge"
    if topology == "lifecycle_loop":
        return "loop"
    if topology == "layered_architecture":
        return "layer"
    if topology == "governance_boundary":
        return "boundary"
    if topology == "ecosystem_map":
        return "interface"
    if topology == "allocation_flow":
        return "allocation"
    if "peer" in grammar:
        return "peer"
    if "convergence" in grammar:
        return "converge"
    if "feedback" in grammar:
        return "loop"
    if "boundary" in grammar:
        return "boundary"
    if "control" in grammar:
        return "control"
    return "transform" if "transform" in visual_intent else "flow"


def _has_explicit_relationship_chain(value: object) -> bool:
    """Return whether verified relationships contain an actual dependency chain."""
    edges: list[tuple[str, str]] = []
    for item in value if isinstance(value, list) else []:
        if not isinstance(item, dict):
            continue
        subject = str(item.get("subject") or "").strip()
        objects = item.get("objects")
        if not isinstance(objects, list):
            objects = [item.get("object")]
        edges.extend(
            (subject, str(object_).strip())
            for object_ in objects
            if subject and str(object_ or "").strip() and subject != str(object_).strip()
        )
    subjects = {subject for subject, _ in edges}
    return any(object_ in subjects for _, object_ in edges)


def _coverage_business_edges(
    decision: dict[str, Any],
    evidence_ids: dict[str, str],
) -> list[dict[str, Any]]:
    """Project only explicitly authored evidence endpoints into graph edges."""
    edges: list[dict[str, Any]] = []
    for item in decision.get("relationship_coverage") or []:
        if not isinstance(item, dict) or item.get("visual_status") == "not_rendered":
            continue
        raw_from = item.get("from_evidence_refs") or item.get("source_evidence_refs")
        raw_to = item.get("to_evidence_refs") or item.get("target_evidence_refs")
        if not isinstance(raw_from, list) or not isinstance(raw_to, list):
            continue
        relation_name = str(item.get("relation") or "").strip()
        relation = {
            "supports": "support",
            "evidence_supports": "support",
            "causes": "cause",
            "transforms_to": "transform",
            "sequence_before": "flow",
            "sequence_after": "flow",
            "directed_dependency": "flow",
            "directed_relation": "mapping",
            "semantic_mapping": "mapping",
            "corresponds_to": "mapping",
            "feedback": "loop",
            "feeds_back": "loop",
            "returns_to": "loop",
        }.get(relation_name, "mapping")
        label = {
            "support": "支撑关系",
            "cause": "因果关系",
            "transform": "转化关系",
            "flow": "业务先后",
            "mapping": "对应关系",
            "loop": "反馈回流",
        }[relation]
        direction = "backward" if relation == "loop" else ("none" if relation == "mapping" else "forward")
        for source in raw_from:
            for target in raw_to:
                source_id = evidence_ids.get(str(source).strip())
                target_id = evidence_ids.get(str(target).strip())
                if not source_id or not target_id or source_id == target_id:
                    continue
                edges.append({
                    "from": source_id,
                    "to": target_id,
                    "relation": relation,
                    "label": label,
                    "direction": direction,
                })
    return edges


def _fail(message: str) -> None:
    raise ValueError(message)


def _page_id(value: object) -> str:
    raw = str(value or "").strip()
    if raw.lower().startswith("p") and raw[1:].isdigit():
        return f"P{int(raw[1:]):02d}"
    _fail(f"invalid visual page id: {raw!r}")


def _resolve_focus_policy(selected: dict[str, Any], topology: str, page_id: str) -> str:
    requested = str(selected.get("focus_policy") or "").strip()
    if requested:
        if requested not in ALLOWED_FOCUS_POLICIES:
            _fail(f"{page_id}: unsupported focus_policy {requested!r}")
        return requested
    return _FOCUS_POLICY_BY_TOPOLOGY[topology]


def _resolve_scene_policy(design: dict[str, Any], prompt_mode: str, page_id: str) -> str:
    requested = str(design.get("scene_policy") or "").strip()
    if requested:
        if requested not in ALLOWED_SCENE_POLICIES:
            _fail(f"{page_id}: unsupported scene_policy {requested!r}")
        return requested
    legacy = design.get("use_scene")
    if isinstance(legacy, bool):
        return "allowed" if legacy else "forbidden"
    return "auto" if prompt_mode == "semantic_brief" else "forbidden"


def _legacy_use_scene(scene_policy: str) -> bool:
    # Deprecated projection only; auto does not mean a scene was selected.
    return scene_policy in {"required", "allowed"}


def _visual_budget(dense_text_page: bool, medium_policy: dict[str, object] | str) -> dict[str, object]:
    if isinstance(medium_policy, str):
        medium_policy = resolve_visual_medium_policy(None, scene_policy=medium_policy).to_dict()
    if dense_text_page:
        return {
            "mode": "relationship_field_only",
            "max_auxiliary_fragments": 0,
            "scope": "page",
            "region_local_visuals": False,
        }
    preferred = str(medium_policy.get("preferred") or "")
    scene_policy = str(medium_policy.get("scene_policy") or "")
    if scene_policy == "forbidden" and preferred in {"relationship_diagram", "data_visualization"}:
        return {
            "mode": "shared_field",
            "max_auxiliary_fragments": 1,
            "scope": "page",
            "region_local_visuals": False,
        }
    return {
        "mode": "integrated_scene",
        "max_auxiliary_fragments": 4,
        "scope": "region",
        "region_local_visuals": True,
    }


def _fallback_spatial_organization(focus_policy: str, focus_label: str, subject: str) -> str:
    if focus_policy == "peer_field":
        return f"以{subject}形成一个完整共享关系场，各同权证据保持相近视觉权重并共同支撑页面判断；不得人为放大某一项为结果中心"
    if focus_policy == "paired_focus":
        return f"围绕{subject}保持两个主对象或两侧关系的成对重心，明确接口、边界或相互作用；不得将任一侧降为装饰性附属"
    if focus_policy == "distributed_focus":
        return f"围绕{subject}形成分布式关系场，各业务主体按真实关系连接；只有来源明确存在枢纽时才允许中心对象"
    if focus_policy == "sequence_focus":
        return f"围绕{subject}沿已声明阅读路径组织连续业务承接，视觉重心随阶段推进；不得额外制造第二条叙事链"
    return f"以“{focus_label}”为主视觉锚点，围绕{subject}把输入、承接动作与结果组织为连续关系场；辅助信息仅贴附于对应对象"


def _render_business_relationships(value: object) -> str:
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
    source: dict[str, Any],
    decision: dict[str, Any],
    selected: dict[str, Any],
    page_id: str,
    focus_policy: str = "single_anchor",
) -> dict[str, object]:
    prompt_mode = str(source.get("prompt_mode") or "directed_composition").strip()
    if prompt_mode == "semantic_brief":
        relationships = _render_business_relationships(source.get("business_relationships"))
        focus = str(source.get("core_judgment") or "本页核心判断").strip()
        scene_policy = "auto"
        medium_policy = resolve_visual_medium_policy(
            selected.get("visual_medium_policy"),
            scene_policy=scene_policy,
        )
        return {
            "business_object": relationships,
            "visual_focus": focus,
            "text_integration_method": "精确上屏文字与其对应业务对象保持语义邻近",
            "spatial_organization": _fallback_spatial_organization(focus_policy, focus, relationships),
            "relationship_encoding": "仅表达已声明的业务关系，不新增顺序、层级或因果",
            "semantic_role": "承载已声明业务对象、动作、条件与结果",
            "scene_policy": scene_policy,
            "visual_medium_policy": medium_policy.to_dict(),
            "use_scene": _legacy_use_scene(scene_policy),
            "scene_type": "依据页面语义、视觉媒介策略和Style lock选择业务场景、对象插图或结构表达",
        }
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
        scene_policy = _resolve_scene_policy(design, prompt_mode, page_id)
        medium_policy = resolve_visual_medium_policy(
            design.get("visual_medium_policy") or selected.get("visual_medium_policy"),
            scene_policy=scene_policy,
        )
        return {
            **normalized,
            "semantic_role": str(design.get("semantic_role") or normalized["relationship_encoding"]).strip(),
            "scene_policy": scene_policy,
            "visual_medium_policy": medium_policy.to_dict(),
            "use_scene": _legacy_use_scene(scene_policy),
            "scene_type": str(
                design.get("scene_type")
                or (
                    "依据页面语义和Style lock选择适当业务场景或对象表达"
                    if scene_policy != "forbidden"
                    else "不使用实景，由选定业务关系场承载"
                )
            ).strip(),
        }
    relationships = source.get("business_relationships") or []
    subject = next(
        (
            str(relation.get("subject") or "").strip()
            for relation in relationships
            if isinstance(relation, dict) and str(relation.get("subject") or "").strip()
        ),
        "本页业务关系",
    )
    focus_key = str((selected.get("semantic_focus") or {}).get("evidence_key") or "")
    evidence = {
        str(item.get("key") or ""): str(item.get("summary") or "")
        for item in decision.get("evidence_units") or []
        if isinstance(item, dict)
    }
    focus = evidence.get(focus_key) or str(source.get("core_judgment") or "")
    focus_label = focus.split("/")[0].split("｜")[0].split("：")[0].strip(" 。；")
    focus_label = re.sub(r"^\s*\d+\s*(?:→|—|-)\s*", "", focus_label).strip()
    focus_label = focus_label or subject
    if len(focus_label) > 28:
        focus_label = focus_label[:28].rstrip("，。；：")
    scene_policy = "forbidden"
    medium_policy = resolve_visual_medium_policy(
        selected.get("visual_medium_policy"),
        scene_policy=scene_policy,
    )
    return {
        "business_object": f"{subject}中围绕“{focus_label}”形成的业务关系场",
        "visual_focus": f"“{focus_label}”所承接的业务对象、动作与结果",
        "text_integration_method": f"将“{focus_label}”对应正文贴附在主业务对象及其承接动作上；其余正文贴附到输入、条件、接口或结果，不独立成文字栏",
        "spatial_organization": _fallback_spatial_organization(focus_policy, focus_label, subject),
        "relationship_encoding": f"通过{subject}中对象、动作、条件与结果的承接关系表达本页判断；不以逐条文字或装饰对象代替业务关系",
        "semantic_role": f"以{subject}的对象、动作和结果关系证明本页判断",
        "scene_policy": scene_policy,
        "visual_medium_policy": medium_policy.to_dict(),
        "use_scene": _legacy_use_scene(scene_policy),
        "scene_type": "不使用实景，由选定业务关系场承载",
    }


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
        "relationship_coverage": {
            key: sum(
                1
                for item in coverage
                if isinstance(item, dict) and item.get("visual_status") == key
            )
            for key in ("primary", "secondary", "not_rendered")
        }
        | {"total": len(coverage)},
        "text_capacity": {
            "risk_level": budget.get("risk_level"),
            "locked_text_count": budget.get("locked_text_count"),
            "risks": budget.get("risks") or [],
        },
        "focus_competition": {"status": "pending_audit", "primary_ref": focus_ref},
    }


def _build_executable_page(source: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    page_id = _page_id(source.get("page_id"))
    prompt_mode = str(source.get("prompt_mode") or "directed_composition").strip()
    if prompt_mode not in {"semantic_brief", "directed_composition"}:
        _fail(f"{page_id}: unsupported prompt_mode {prompt_mode!r}")
    if _page_id(decision.get("page_id")) != page_id:
        _fail(f"{page_id}: decision receipt page id does not match visual input")
    evidence = decision.get("evidence_units")
    candidates = decision.get("candidates")
    if not isinstance(evidence, list) or not evidence or not isinstance(candidates, list) or len(candidates) < 1:
        _fail(f"{page_id}: decision receipt must contain evidence_units and at least one candidate")
    evidence_keys = [str(item.get("key") or "").strip() for item in evidence if isinstance(item, dict)]
    if len(evidence_keys) != len(evidence) or not all(evidence_keys) or len(set(evidence_keys)) != len(evidence_keys):
        _fail(f"{page_id}: evidence keys must be non-empty and unique")
    if len(evidence_keys) > 7:
        _fail(
            f"{page_id}: visual decision has {len(evidence_keys)} evidence units; "
            "group contiguous locked copy into at most 7 business evidence units"
        )
    selected_id = str(decision.get("selected_candidate") or "")
    selected = next(
        (item for item in candidates if isinstance(item, dict) and item.get("id") == selected_id),
        None,
    )
    if selected is None:
        _fail(f"{page_id}: selected candidate is missing")
    expression_contract = _expression_contract(source, selected)
    focus = selected.get("semantic_focus") if isinstance(selected.get("semantic_focus"), dict) else {}
    focus_key = str(focus.get("evidence_key") or "")
    if focus_key not in evidence_keys:
        _fail(f"{page_id}: selected candidate has an unknown semantic focus")
    topology = str(selected.get("topology") or "")
    if topology not in ALLOWED_TOPOLOGY:
        _fail(f"{page_id}: selected candidate must declare a topology from {sorted(ALLOWED_TOPOLOGY)}")
    focus_policy = _resolve_focus_policy(selected, topology, page_id)
    design = _decision_execution_design(source, decision, selected, page_id, focus_policy)
    stage01_features = source.get("stage01_relationship_features")
    stage01_features = stage01_features if isinstance(stage01_features, dict) else {}
    # ``render_topology`` is the canonical Stage 02 handoff field.  Keep the
    # nested alias for older inputs, but never let its absence disable the
    # candidate/topology compatibility guard.
    semantic_topology = source.get("render_topology")
    if not isinstance(semantic_topology, dict):
        semantic_topology = stage01_features.get("semantic_topology")
    semantic_topology = semantic_topology if isinstance(semantic_topology, dict) else {}
    verified_topology = str(semantic_topology.get("primary_topology") or "").strip()
    compatible_topologies = _CANDIDATE_TOPOLOGIES_BY_SEMANTIC_TOPOLOGY.get(verified_topology)
    if compatible_topologies and topology not in compatible_topologies:
        _fail(
            f"{page_id}: selected candidate topology {topology!r} is incompatible with "
            f"verified semantic topology {verified_topology!r}"
        )
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
    content_nodes = {
        str(node.get("text_id")): node
        for node in (source.get("content_integrity") or {}).get("nodes") or []
        if isinstance(node, dict)
    }
    if content_nodes:
        for key in evidence_keys:
            ids = text_ids_by_evidence[key]
            if len(ids) < 2:
                continue
            root_ids = {
                str(content_nodes[tid].get("root_id"))
                for tid in ids
                if tid in content_nodes
            }
            if len(root_ids) > 1:
                _fail(
                    f"{page_id}: evidence unit {key!r} merges text ids from different root "
                    f"modules ({sorted(root_ids)}); cross-root grouping is forbidden"
                )
        focus_ids = text_ids_by_evidence.get(focus_key, [])
        if focus_ids and not any(
            content_nodes[tid].get("content_role") == "root_module"
            for tid in focus_ids
            if tid in content_nodes
        ):
            _fail(
                f"{page_id}: semantic focus {focus_key!r} has no root-module text id; "
                "a detail-only evidence unit cannot become the page result/judgment"
            )
    eid = {key: f"E{index}" for index, key in enumerate(evidence_keys, start=1)}
    reading_keys = [str(value) for value in selected.get("reading_sequence") or []]
    if len(reading_keys) != len(set(reading_keys)) or set(reading_keys) != set(evidence_keys):
        _fail(f"{page_id}: selected reading sequence must cover every evidence key once")
    grammar = [str(value) for value in selected.get("spatial_grammar") or []]
    allowed_grammar = {
        "anchor", "path", "convergence", "divergence", "layer", "boundary",
        "interface", "network", "tension", "feedback", "control", "peer",
    }
    grammar = [item for item in grammar if item in allowed_grammar] or ["anchor"]
    relation = _connector_relation(
        topology,
        grammar,
        str(selected.get("visual_intent_type") or ""),
    )
    direction = _DIRECTION_MAP.get(str(selected.get("direction") or ""), "spatial")
    explicit_chain = _has_explicit_relationship_chain(source.get("business_relationships"))
    authored_edges = _coverage_business_edges(decision, eid)
    relationship_items = source.get("business_relationships")
    if (
        topology == "directed_flow"
        and not explicit_chain
        and isinstance(relationship_items, list)
        and len(relationship_items) > 1
    ):
        _fail(
            f"{page_id}: directed_flow requires an explicit relationship chain; "
            "reading_sequence cannot create flow edges"
        )
    graph_edges: list[dict[str, Any]] = []
    connectors: list[dict[str, Any]] = []
    if relation == "converge":
        if authored_edges:
            graph_edges.extend(authored_edges)
            connectors.extend(
                {"from": edge["from"], "to": edge["to"], "type": edge["relation"], "direction": direction, "label": edge["label"], "main_chain": True}
                for edge in authored_edges
            )
        else:
            for key in reading_keys:
                if key == focus_key:
                    continue
                graph_edges.append({"from": eid[key], "to": eid[focus_key], "relation": "converge", "label": "汇聚支撑", "direction": "forward"})
                connectors.append({"from": eid[key], "to": eid[focus_key], "type": "converge", "direction": direction, "label": "汇聚支撑", "main_chain": True})
    elif authored_edges and relation != "peer":
        graph_edges.extend(authored_edges)
        connectors.extend(
            {"from": edge["from"], "to": edge["to"], "type": edge["relation"], "direction": direction, "label": edge["label"], "main_chain": edge["relation"] != "loop"}
            for edge in authored_edges
        )
    else:
        for left, right in zip(reading_keys, reading_keys[1:]):
            if relation == "peer":
                graph_edges.append({"from": eid[left], "to": eid[right], "relation": "peer", "label": "共同支撑同一判断", "direction": "none"})
            elif relation in {"flow", "transform"} and not explicit_chain:
                continue
            else:
                label = {
                    "layer": "层级支撑",
                    "boundary": "边界约束",
                    "control": "控制约束",
                    "interface": "接口关系",
                    "allocation": "分配关系",
                    "transform": "转化关系",
                }.get(relation, "业务承接")
                graph_edges.append({"from": eid[left], "to": eid[right], "relation": relation, "label": label, "direction": "forward"})
                connectors.append({"from": eid[left], "to": eid[right], "type": relation, "direction": direction, "label": label, "main_chain": True})
        if relation == "loop" and len(reading_keys) > 1:
            last_key, first_key = reading_keys[-1], reading_keys[0]
            graph_edges.append({"from": eid[last_key], "to": eid[first_key], "relation": "loop", "label": "反馈回流", "direction": "backward"})
            connectors.append({"from": eid[last_key], "to": eid[first_key], "type": "loop", "direction": "spatial", "label": "反馈回流", "main_chain": False})
    trace_refs = [str(value).strip() for value in source.get("trace_refs") or [] if str(value).strip()]
    source_ref = "、".join(trace_refs) or page_id
    evidence_units = [
        {
            "id": eid[key],
            "text": str(evidence_by_key[key].get("summary") or expected_text[0]),
            "kind": "fact" if focus_policy == "peer_field" else ("result" if key == focus_key else "process"),
            "priority": "P0",
            "source_ref": source_ref,
            "status": "locked",
        }
        for key in evidence_keys
    ]
    focus_id = eid[focus_key]
    graph_nodes = [
        {"id": eid[key], "role": "evidence" if focus_policy == "peer_field" else ("judgment" if key == focus_key else "evidence"), "source_refs": text_ids_by_evidence[key]}
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
        grouping_decisions.append({"source_nodes": source_refs, "target_node": eid[key], "reason": reason, "loss_risk": loss_risk})
    no_arrows = any(
        "不绘制箭头" in str(design.get(field) or "") or "不使用箭头" in str(design.get(field) or "")
        for field in ("text_integration_method", "spatial_organization", "relationship_encoding")
    )
    forbidden_structures = list(dict.fromkeys((
        *_UNIVERSAL_FORBIDDEN_STRUCTURES,
        *(("equal_peer_cards",) if topology != "parallel_set" else ()),
        *_FORBIDDEN_STRUCTURES_BY_TOPOLOGY.get(topology, []),
        *(("no_arrows",) if no_arrows else ()),
    )))
    normalized_business_relationships = []
    for item in source.get("business_relationships") or []:
        if not isinstance(item, dict):
            continue
        relationship = {
            key: deepcopy(item[key])
            for key in (
                "subject", "relation", "objects", "direction", "condition", "modality",
                "basis", "confidence", "source_refs", "authority_ref",
            )
            if key in item
        }
        if "confidence" in relationship:
            relationship["confidence"] = str(relationship["confidence"])
        normalized_business_relationships.append(relationship)
    semantic_focus_kind = str(focus.get("kind") or "relationship")
    if semantic_focus_kind not in {"entity", "action", "state", "relationship", "outcome"}:
        semantic_focus_kind = "relationship"
    region_graph = bind_region_graph_text(
        build_region_graph(
            topology=topology,
            evidence_ids=[eid[key] for key in evidence_keys],
            focus_id=focus_id,
            reading_sequence=[eid[key] for key in reading_keys],
            semantic_edges=graph_edges,
            focus_policy=focus_policy,
        ),
        evidence_text_ids={eid[key]: text_ids_by_evidence[key] for key in evidence_keys},
        required_text_ids=expected_ids,
    )
    text_region_ids = region_text_owner_map(region_graph)
    quality_contract = _quality_contract(decision, selected, focus_id)
    final_text = [
        {"id": item_id, "role": "body", "text": text, "region_id": text_region_ids[item_id]}
        for item_id, text in zip(expected_ids, expected_text)
    ]
    locked_items = [
        {"id": f"{page_id}-TITLE", "type": "title", "text": str(source.get("page_title") or page_id), "source_ref": source_ref}
    ]
    locked_items.extend(
        {"id": item_id, "type": "body", "text": text, "source_ref": source_ref}
        for item_id, text in zip(expected_ids, expected_text)
    )
    dense_text_page = is_text_dense(expected_text)
    scene_policy = str(design["scene_policy"])
    medium_policy = dict(design["visual_medium_policy"])
    visual_budget = _visual_budget(dense_text_page, medium_policy)
    return {
        "schema_version": "1.1",
        "page_id": page_id,
        "page_number": int(source["page_number"]),
        "prompt_mode": prompt_mode,
        "content_integrity": source.get("content_integrity") or {},
        "page_title": str(source["page_title"]),
        "page_role": str(source.get("argument_role") or "content"),
        "page_mission": str(source["page_mission"]),
        "core_judgment": str(source["core_judgment"]),
        "content_lock": {
            "mode": "strict",
            "locked_items": locked_items,
            "allowed_transformations": ["line_break", "grouping", "position_change"],
            "forbidden_transformations": [
                "Do not change facts, numbers, dates or units.",
                "Do not change actors, responsibilities or status.",
                "Do not add presentation copy that is not part of the approved locked text.",
                "For a \"label: sentence\" locked text item, preserve every character and render it once in one semantic region. The label before the colon may use stronger typography or a line break, but must not be duplicated elsewhere as a heading, card title, or tag.",
                "Do not invent a heading, label, or tag for a locked text item that has no label in the required text (for example a bare boundary sentence); render it as plain text with no invented label.",
            ],
        },
        "evidence_units": evidence_units,
        "semantic_graph": {
            "primary_relation": relation,
            "direction": direction,
            "topology": topology,
            "focus_node": focus_id,
            "nodes": graph_nodes,
            "edges": graph_edges,
            "edge_source": "relationship_coverage" if authored_edges else ("reading_sequence_legacy" if graph_edges else "none"),
            "decision_relationship": _render_business_relationships(source.get("business_relationships")),
            "business_relationships": normalized_business_relationships,
            "grouping_decisions": grouping_decisions,
            "forbidden_structures": forbidden_structures,
        },
        "region_graph": region_graph,
        "visual_medium_policy": medium_policy,
        "structural_decision": {
            "semantic_focus": {"kind": semantic_focus_kind, "ref": focus_id},
            "spatial_grammar": grammar,
            "semantic_tags": [str(selected.get("visual_intent_type") or "relationship")],
            "primary_refs": [eid[key] for key in evidence_keys] if focus_policy == "peer_field" else [focus_id],
            "secondary_refs": [] if focus_policy == "peer_field" else [eid[key] for key in evidence_keys if key != focus_key],
            "reading_sequence": [eid[key] for key in reading_keys],
            "text_bindings": [
                {
                    "evidence_id": eid[key],
                    "target_ref": eid[key],
                    "binding": "embedded" if focus_policy == "peer_field" else ("result" if key == focus_key else "embedded"),
                    "text_ids": text_ids_by_evidence[key],
                }
                for key in evidence_keys
            ],
            "representation_freedom": {
                "carrier": "constrained",
                "medium": "free",
                "reason": "视觉媒介须服从scene policy与已声明业务关系；区域内部具体实现由ImageGen完成" if prompt_mode == "semantic_brief" else "定向构图模式锁定来源支持的业务关系场与文字贴附方式",
            },
        },
        "visual_decision": {
            "visual_intent_type": str(selected.get("visual_intent_type") or "relationship_field"),
            "visual_thesis": str(selected.get("visual_thesis") or source["core_judgment"]),
            "spatial_organization": design["spatial_organization"],
            "reading_path": [str(evidence_by_key[key].get("summary") or "") for key in reading_keys],
            "text_integration_method": design["text_integration_method"],
            "relationship_encoding": design["relationship_encoding"],
            "focus_policy": focus_policy,
            # Deprecated compatibility field. New structure logic must consume focus_policy.
            "visual_center_count": len(evidence_keys) if focus_policy == "peer_field" else 1,
            "visual_hierarchy": {
                "primary": design["visual_focus"],
                "secondary": [str(evidence_by_key[key].get("summary") or "") for key in evidence_keys if focus_policy == "peer_field" or key != focus_key],
                "tertiary": [],
            },
        },
        "text_integration": {
            "title_render_mode": str(source.get("title_render_mode") or "external_text_layer"),
            "subtitle_render_mode": str(source.get("subtitle_render_mode") or "external_text_layer"),
            "body_render_mode": "in_image",
            "placement_strategy": design["text_integration_method"],
        },
        "geometry": {
            "canvas": source.get("body_image_canvas") or {"width": 2048, "height": 1024, "ratio": "2:1"},
            "title_exclusion_zone": {"x": 0, "y": 0, "w": 2048, "h": 0},
            "regions": [{"id": "R_RELATION", "role": "relation-bearing business field", "x": 80, "y": 120, "w": 1888, "h": 800, "priority": "primary"}],
        },
        "image_plan": {
            "scene_policy": scene_policy,
            # Deprecated compatibility field; new logic consumes scene_policy.
            "use_scene": _legacy_use_scene(scene_policy),
            "scene_type": str(design["scene_type"]),
            "business_object": design["business_object"],
            "semantic_role": str(design["semantic_role"]),
            "placement": design["spatial_organization"],
            "front_facing_people": False,
            "identifiable_location": False,
            "factual_event_implication": False,
        },
        "visual_budget": visual_budget,
        "expression_contract": expression_contract,
        "quality_contract": quality_contract,
        "connectors": connectors,
        "final_text": final_text,
        "generation_handoff": {
            "structural_guidance": {
                "source": "semantic_graph" if prompt_mode == "semantic_brief" else "structural_decision",
                "additional_constraints": (
                    [
                        f"Respect scene_policy={scene_policy}; scene, business illustration or structural carrier may be selected only within that policy.",
                        f"Respect focus_policy={focus_policy}; preserve the declared macro focus relationship and do not manufacture a dominant peer or extra result center.",
                        "Preserve only source-supported relationship direction and keep exact visible text near its corresponding business meaning.",
                    ]
                    if prompt_mode == "semantic_brief"
                    else [
                        "Use the selected business relationship field and its text attachment design; do not render instructions or internal text ids.",
                        f"Respect focus_policy={focus_policy}; do not create an independent text wall or second summary structure.",
                        "Respect visual_budget: semantic evidence units may share one page-level visual carrier; region-local imagery is allowed only when region_local_visuals is true.",
                    ]
                ),
            },
            "required_text_ids": expected_ids,
            "required_text": expected_text,
            "style_source_ref": "external style lock selected at final-script-pages",
            "title_exclusion_instruction": "Reserve page title and subtitle for the external PowerPoint text layer; do not render them in the body image.",
        },
        "avoid": [
            "Do not map each body item to an isolated icon or decorative image.",
            "Do not create an independent text wall or second result chain.",
        ],
        "qa": {"status": "pending_audit", "score": None, "blocking_issues": [], "warnings": []},
    }


def _render_visual_structure_markdown(spec: dict[str, Any]) -> str:
    lines = [
        f"# {spec['deck_title']}视觉结构设计脚本", "", "## 整套视觉设计总则", "",
        "- 每页以一个完整业务关系场承载正文；具体视觉风格仅由最终 Style lock 提供。", "",
    ]
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
        scene_policy = str(page.get("image_plan", {}).get("scene_policy") or "legacy")
        lines += [
            f"## 第{page['page_number']}页｜{page['page_title']}", "", "### 页面角色", page["page_role"], "",
            "### 页面使命", page["page_mission"], "", "### 核心结论", page["core_judgment"], "",
            "### 内容锁定", "- 严格保留 generation_handoff.required_text 所列正文", "",
            "### 证据单元与语义关系", f"- 主关系：{sg['decision_relationship']}", f"- 拓扑：{sg['topology']}",
            f"- 焦点节点：{sg['focus_node']}", f"- 节点：{node_summary}", f"- 关系边：{edge_summary}",
            f"- 禁止结构：{forbidden_summary}", "", *expression_lines, "", "### 视觉意图",
            f"- 视觉意图类型：{vd['visual_intent_type']}",
            f"- 语义焦点：{structural['semantic_focus']['kind']} / {structural['semantic_focus']['ref']}",
            f"- 焦点策略：{vd['focus_policy']}",
            f"- 空间语法：{', '.join(structural['spatial_grammar'])}",
            f"- 主结构：{', '.join(structural['primary_refs'])}", f"- 文字归属：{vd['text_integration_method']}", "",
            "### 页面草图", f"- 页面业务关系场：{page['image_plan']['business_object']}",
            f"- 场景策略：{scene_policy}；配图预算：{visual_budget.get('mode', 'integrated_scene')}；最多辅助片段 {visual_budget.get('max_auxiliary_fragments', 4)} 个；作用域 {visual_budget.get('scope', 'region')}；区域局部配图 {visual_budget.get('region_local_visuals', True)}", "",
            "### 页面构图", vd['spatial_organization'], "", "### 实景锚点与图文融合", vd['relationship_encoding'], "",
            "### 元素与空间关系", page['image_plan']['placement'], "", "### 箭头与连接关系",
            *[f"- {item['from']} -> {item['to']}：{item['label']}" for item in page['connectors']], "",
            "### 标题与文字渲染", "- 标题与副标题由外部PPT文字层渲染；正文贴附在业务对象、动作、接口、边界或结果上", "",
            "### 终稿文字", *[f"- {item['text']}" for item in page['final_text']], "", "### 生图执行摘要",
            f"- {vd['text_integration_method']}", "", "### 禁止事项", *[f"- {item}" for item in page['avoid']], "",
        ]
    return "\n".join(lines)


def compile_visual_spec(project: Path, design_input_path: Path, decisions_path: Path) -> dict[str, Any]:
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
    return {
        "schema_version": "1.1",
        "deck_id": project.name,
        "deck_title": str(project.name),
        "deck_context": {
            "audience": "项目既定受众",
            "purpose": "承接已确认业务脚本形成可执行页面视觉设计",
            "usage_scene": "正式汇报",
            "narrative": "每页以一个完整业务关系场承载已锁定正文",
            "source_files": [str(design_input_path)],
        },
        "global_profile": "ppt-visual-structure-designer",
        "content_lock": {
            "default_mode": "strict",
            "global_locked_terms": [],
            "global_forbidden_changes": ["不得改变锁定正文、事实、主体关系或边界"],
        },
        "pages": pages,
        "deck_rhythm": {
            "density_pattern": "随页面业务关系复杂度变化",
            "visual_intent_sequence": [item["visual_decision"]["visual_intent_type"] for item in pages],
            "repetition_control": "连续页面避免复用同一视觉意图和空间语法",
        },
        "capacity_suggestions": [],
        "qa_summary": {"status": "pending_audit", "average_score": None, "blocking_issues": [], "warnings": []},
    }

"""Page-level argument contracts for source-grounded Stage 01 authoring.

The contract deliberately separates a *candidate workpack* from an authored
logic decision.  A deterministic compiler may expose facts, source order and
declared relations, but it must never promote adjacency into causality.
"""

from __future__ import annotations

import re
from typing import Any

from cyberppt.content_route import render_content_route


REQUIRED_MODE = "required"
_VALID_NODE_ROLES = {"context", "driver", "need", "constraint", "requirement", "consequence", "claim", "boundary", "support"}
_VALID_BASES = {"explicit", "inferred"}
_VALID_CONFIDENCE = {"high", "medium", "low"}
_VALID_CARRIERS = {
    "connector",
    "ordered_chain",
    "integrated_proposition",
    "integrated_landing",
}
_VALID_NODE_ONSCREEN_REQUIREMENTS = {"required", "prose_only"}
_STRONG_CAUSAL_RELATIONS = {"causes", "drives", "determines", "leads_to", "results_in"}
ONSCREEN_EXPRESSION_IR_SCHEMA = "cyberppt.onscreen_expression_ir.v1"
_VALID_EXPRESSION_PATTERNS = {"parallel_states_to_foundation"}
_VALID_EXPRESSION_NODE_ROLES = {
    "context", "claim", "current_state", "requirement_target", "conclusion",
}
_VALID_EXPRESSION_RENDERS = {"statement_stack", "focus_label", "chip_set", "landing"}


def _refs(value: object) -> list[str]:
    if not isinstance(value, (list, tuple, set)):
        return []
    return list(dict.fromkeys(str(item) for item in value if str(item).strip()))


def _compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip("-•：:；;。")


def _signals(value: object) -> tuple[str, ...]:
    """Return distinct, author-declared wording that must survive a projection."""

    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(
        str(item).strip() for item in value if _compact(item)
    ))


def _missing_signals(text: str, signals: tuple[str, ...]) -> tuple[str, ...]:
    compact_text = _compact(text)
    return tuple(signal for signal in signals if _compact(signal) not in compact_text)


def _page_message(page: dict[str, object]) -> str:
    return str(
        page.get("core_message")
        or page.get("key_judgment")
        or page.get("main_message")
        or ""
    ).strip()


def page_logic_mode(page: dict[str, object]) -> str:
    return str(page.get("page_logic_contract_mode") or "legacy").strip() or "legacy"


def _candidate_nodes(page: dict[str, object]) -> list[dict[str, object]]:
    units = [item for item in page.get("content_units") or [] if isinstance(item, dict)]
    ordered = sorted(
        units,
        key=lambda item: (
            item.get("sequence_index") if isinstance(item.get("sequence_index"), int) else 10**6,
            str(item.get("unit_id") or ""),
        ),
    )
    nodes: list[dict[str, object]] = []
    for index, unit in enumerate(ordered, start=1):
        role = str(unit.get("topology_role") or unit.get("argument_function") or "support")
        if role not in _VALID_NODE_ROLES:
            role = "support"
        nodes.append({
            "id": str(unit.get("unit_id") or f"candidate-{index}"),
            "role": role,
            "statement": str(unit.get("statement") or "").strip(),
            "source_refs": _refs(unit.get("source_refs")),
            "candidate_only": True,
        })
    return nodes


def build_candidate_page_logic(page: dict[str, object]) -> dict[str, object]:
    """Expose available evidence without inventing missing logical edges."""

    nodes = _candidate_nodes(page)
    relations = [item for item in page.get("content_relations") or [] if isinstance(item, dict)]
    main_chain = [
        node for node in nodes
        if any(
            str(unit.get("unit_id") or "") == node["id"]
            and unit.get("topology_role") == "main_chain"
            for unit in page.get("content_units") or []
            if isinstance(unit, dict)
        )
    ]
    return {
        "nodes": nodes,
        "declared_relations": relations,
        "main_chain_candidate": [node["id"] for node in main_chain],
        "note": "候选工作包只呈现已声明事实、顺序和关系；缺失的论证边必须由作者依据来源补充。",
    }


def _contract(page: dict[str, object]) -> dict[str, object]:
    value = page.get("page_logic_contract")
    return value if isinstance(value, dict) else {}


def _expression_ir(contract: dict[str, object]) -> dict[str, object] | None:
    value = contract.get("onscreen_expression")
    return value if isinstance(value, dict) else None


def _expression_texts(node: dict[str, object]) -> tuple[str, ...]:
    text = str(node.get("text") or "").strip()
    items = _signals(node.get("items"))
    return (text,) if text else items


def _expression_surface_texts(node: dict[str, object]) -> tuple[str, ...]:
    """Return every author-approved visible wording unit for one node."""

    label = str(node.get("surface_label") or "").strip()
    return tuple(value for value in (label, *_expression_texts(node)) if _compact(value))


def _logic_nodes_reaching_proposition(
    nodes: dict[str, dict[str, object]],
    edges: list[dict[str, object]],
    proposition_node_ids: set[str],
) -> set[str]:
    """Find logic nodes that can advance the declared page proposition.

    A source fact may be relevant to the document yet still be irrelevant to a
    particular page.  The page's declared edges, rather than lexical
    similarity, are the authority for deciding whether it belongs on screen.
    """

    reverse: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for edge in edges:
        source = str(edge.get("from") or "").strip()
        target = str(edge.get("to") or "").strip()
        if source in reverse and target in reverse:
            reverse[target].add(source)
    reachable = set(proposition_node_ids).intersection(nodes)
    pending = list(reachable)
    while pending:
        target = pending.pop()
        for source in reverse.get(target, ()):
            if source not in reachable:
                reachable.add(source)
                pending.append(source)
    return reachable


def _unmapped_onscreen_lines(onscreen: str, expression: dict[str, object]) -> tuple[str, ...]:
    """Return visible lines containing copy outside the declared expression.

    This is intentionally a closed authoring check, not an NLP relevance
    classifier.  A natural sentence may combine declared labels, statements,
    object items and relation labels with punctuation or lightweight Chinese
    connectors; any remaining substantive wording has no approved argument
    role and must be declared or removed.
    """

    approved: set[str] = set()
    for node in expression.get("nodes") or []:
        if isinstance(node, dict):
            approved.update(_compact(value) for value in _expression_surface_texts(node))
    for edge in expression.get("edges") or []:
        if isinstance(edge, dict):
            label = _compact(edge.get("visible_label"))
            if label:
                approved.add(label)
    ordered = sorted((value for value in approved if value), key=len, reverse=True)
    leftovers: list[str] = []
    for raw_line in str(onscreen or "").splitlines():
        visible_line = re.sub(r"^\s*(?:[-*+]\s+|\d+[.、]\s+)", "", raw_line)
        compact_line = _compact(visible_line.replace("*", ""))
        if not compact_line:
            continue
        residual = compact_line
        for wording in ordered:
            residual = residual.replace(wording, "")
        residual = re.sub(r"(?:以及|和|及|与|或|从|由|至|到|等|的)+", "", residual)
        residual = re.sub(r"[、，,；;：:。→—\-－|｜（）()【】\[\]“”\"'·]+", "", residual)
        if residual:
            leftovers.append(visible_line.strip())
    return tuple(leftovers)


def _validate_onscreen_expression_ir(
    contract: dict[str, object],
    *,
    page_refs: set[str],
    logic_nodes: dict[str, dict[str, object]],
    required_nodes: set[str],
) -> list[dict[str, object]]:
    """Validate the author-declared screen expression graph when supplied.

    This is deliberately an optional extension to the existing page logic
    contract.  Legacy required contracts remain readable; once an author opts
    in, every visible node and relation must be traceable to the already
    declared page logic and direct source evidence.
    """

    expression = _expression_ir(contract)
    if expression is None:
        return []
    issues: list[dict[str, object]] = []
    if (
        str(expression.get("schema") or "") != ONSCREEN_EXPRESSION_IR_SCHEMA
        or str(expression.get("pattern") or "") not in _VALID_EXPRESSION_PATTERNS
    ):
        issues.append({"code": "ONSCREEN_EXPRESSION_IR_INVALID", "message": "On-screen expression IR needs a supported schema and pattern.", "action": "Use the current expression IR schema and an author-supported pattern."})
        return issues
    nodes = [item for item in expression.get("nodes") or [] if isinstance(item, dict)]
    edges = [item for item in expression.get("edges") or [] if isinstance(item, dict)]
    reading_order = [str(item) for item in expression.get("reading_order") or [] if str(item)]
    expression_nodes: dict[str, dict[str, object]] = {}
    carried_logic_nodes: set[str] = set()
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        refs = _refs(node.get("source_refs"))
        logic_node_ids = [str(item) for item in node.get("logic_node_ids") or [] if str(item)]
        render = str(node.get("render") or "").strip()
        texts = _expression_texts(node)
        has_text = bool(str(node.get("text") or "").strip())
        has_items = bool(_signals(node.get("items")))
        if (
            not node_id or node_id in expression_nodes
            or str(node.get("role") or "") not in _VALID_EXPRESSION_NODE_ROLES
            or render not in _VALID_EXPRESSION_RENDERS
            or not refs or not set(refs).issubset(page_refs)
            or not logic_node_ids or not set(logic_node_ids).issubset(logic_nodes)
            or not texts or has_text == has_items
        ):
            issues.append({"code": "ONSCREEN_EXPRESSION_NODE_INVALID", "message": "Each expression node needs a unique id, supported role/render, one visible text form, in-scope source refs, and known logic node bindings.", "action": "Declare whether the node renders one statement or an item set, then bind it to page logic and source evidence."})
            continue
        allowed_refs = set().union(*(
            set(_refs(logic_nodes[logic_node_id].get("source_refs")))
            for logic_node_id in logic_node_ids
        ))
        if not set(refs).issubset(allowed_refs):
            issues.append({"code": "ONSCREEN_EXPRESSION_NODE_SOURCE_UNGROUNDED", "message": "An expression node cites source facts outside its bound logic nodes.", "source_refs": tuple(refs), "action": "Bind the visible text to the logic node that owns its source evidence."})
        expression_nodes[node_id] = node
        carried_logic_nodes.update(logic_node_ids)
    if set(reading_order) != set(expression_nodes) or len(reading_order) != len(expression_nodes):
        issues.append({"code": "ONSCREEN_EXPRESSION_READING_ORDER_INVALID", "message": "Reading order must list every expression node exactly once.", "action": "Declare the intended audience reading sequence without relying on spatial adjacency."})
    missing_logic_nodes = tuple(sorted(required_nodes - carried_logic_nodes))
    if missing_logic_nodes:
        issues.append({"code": "ONSCREEN_EXPRESSION_LOGIC_NODE_MISSING", "message": "A required logic node is absent from the on-screen expression graph.", "evidence": missing_logic_nodes, "action": "Bind every required business state or conclusion to at least one visible expression node."})
    proposition = contract.get("page_proposition")
    proposition_node_ids = proposition.get("node_ids") if isinstance(proposition, dict) else ()
    proposition_nodes = {
        str(node_id) for node_id in proposition_node_ids or []
        if str(node_id) in logic_nodes
    }
    if proposition_nodes:
        topic_nodes = _logic_nodes_reaching_proposition(
            logic_nodes,
            [item for item in contract.get("edges") or [] if isinstance(item, dict)],
            proposition_nodes,
        )
        for expression_node in expression_nodes.values():
            bound_nodes = {
                str(node_id) for node_id in expression_node.get("logic_node_ids") or []
            }
            disconnected = tuple(sorted(bound_nodes - topic_nodes))
            if disconnected:
                issues.append({"code": "ONSCREEN_EXPRESSION_TOPIC_DISCONNECTED", "message": "An on-screen expression node cannot advance the declared page proposition through the authored argument graph.", "source_refs": tuple(_refs(expression_node.get("source_refs"))), "evidence": disconnected, "action": "Remove this on-screen copy, or declare the source-grounded logic edge by which it supports the page proposition."})
    edge_ids: set[str] = set()
    for edge in edges:
        edge_id = str(edge.get("id") or "").strip()
        source_basis = str(edge.get("source_basis") or "").strip()
        relation = str(edge.get("relation") or "").strip()
        refs = _refs(edge.get("source_refs"))
        endpoints = (str(edge.get("from") or ""), str(edge.get("to") or ""))
        if (
            not edge_id or edge_id in edge_ids or endpoints[0] not in expression_nodes
            or endpoints[1] not in expression_nodes or endpoints[0] == endpoints[1]
            or not relation or source_basis not in _VALID_BASES
            or not str(edge.get("visible_label") or "").strip()
            or not refs or not set(refs).issubset(page_refs)
        ):
            issues.append({"code": "ONSCREEN_EXPRESSION_EDGE_INVALID", "message": "Each expression edge needs known endpoints, relation, source basis, visible label, and in-scope source refs.", "action": "Declare the readable relationship label and its source basis; do not infer it from text order."})
            continue
        edge_ids.add(edge_id)
        if source_basis == "inferred" and relation in _STRONG_CAUSAL_RELATIONS:
            issues.append({"code": "ONSCREEN_EXPRESSION_UNSUPPORTED_CAUSAL_LANGUAGE", "message": "An inferred screen relationship uses strong causal language.", "action": "Use a weaker source-grounded relation or retain explicit causal evidence."})
    return issues


def validate_page_logic_contract(page: dict[str, object]) -> list[dict[str, object]]:
    """Validate author-declared page logic before prose or layout is written."""

    if page_logic_mode(page) != REQUIRED_MODE:
        return []
    contract = _contract(page)
    issues: list[dict[str, object]] = []
    nodes = [item for item in contract.get("nodes") or [] if isinstance(item, dict)]
    edges = [item for item in contract.get("edges") or [] if isinstance(item, dict)]
    paragraphs = [item for item in contract.get("paragraph_plan") or [] if isinstance(item, dict)]
    projections = [item for item in contract.get("onscreen_projection") or [] if isinstance(item, dict)]
    if not nodes:
        return [{"code": "PAGE_LOGIC_CONTRACT_MISSING", "message": "Required page logic contract has no nodes.", "action": "Author source-grounded logic nodes in the authoritative page plan."}]
    page_refs = set(_refs(page.get("source_refs")))
    ids: set[str] = set()
    required_nodes: set[str] = set()
    for node in nodes:
        node_id = str(node.get("id") or "").strip()
        refs = _refs(node.get("source_refs"))
        prose_signals = _signals(node.get("prose_signals"))
        onscreen_signals = _signals(node.get("onscreen_signals"))
        onscreen_requirement = str(node.get("onscreen_requirement") or "required")
        if (
            not node_id
            or node_id in ids
            or str(node.get("role") or "") not in _VALID_NODE_ROLES
            or not refs
            or not str(node.get("statement") or "").strip()
            or not prose_signals
            or (onscreen_requirement == "required" and not onscreen_signals)
        ):
            issues.append({"code": "PAGE_LOGIC_NODE_INVALID", "message": "Each logic node needs a unique id, role, source refs, canonical statement, full-prose signals, and required on-screen signals.", "action": "State the source-grounded node and the wording that must survive in the full-prose and on-screen projections."})
            continue
        ids.add(node_id)
        if onscreen_requirement not in _VALID_NODE_ONSCREEN_REQUIREMENTS:
            issues.append({"code": "PAGE_LOGIC_NODE_VISIBILITY_INVALID", "message": "A logic node has an invalid on-screen requirement.", "action": "Use required or prose_only for the node's on-screen requirement."})
        elif onscreen_requirement == "required":
            required_nodes.add(node_id)
        outside = tuple(ref for ref in refs if ref not in page_refs)
        if outside:
            issues.append({"code": "PAGE_LOGIC_NODE_SOURCE_OUT_OF_SCOPE", "message": "A logic node cites facts outside the page evidence boundary.", "source_refs": outside, "action": "Keep node evidence within the page's direct source refs."})
    proposition = contract.get("page_proposition")
    if not isinstance(proposition, dict):
        issues.append({"code": "PAGE_PROPOSITION_LOGIC_MISSING", "message": "The required page logic contract has no proposition binding.", "action": "Bind the page proposition to its supporting logic nodes and its full-prose/on-screen signals."})
    else:
        proposition_nodes = {str(item) for item in proposition.get("node_ids") or [] if str(item)}
        proposition_refs = _refs(proposition.get("source_refs"))
        proposition_prose = _signals(proposition.get("prose_signals"))
        proposition_onscreen = _signals(proposition.get("onscreen_signals"))
        page_message = _page_message(page)
        if (
            not str(proposition.get("statement") or "").strip()
            or not proposition_nodes
            or not proposition_nodes.issubset(ids)
            or not proposition_refs
            or not set(proposition_refs).issubset(page_refs)
            or not proposition_prose
            or not proposition_onscreen
            or not page_message
            or _compact(proposition.get("statement")) != _compact(page_message)
        ):
            issues.append({"code": "PAGE_PROPOSITION_LOGIC_INVALID", "message": "The page proposition must equal the authoritative core message and declare in-scope evidence, supporting nodes, and full-prose/on-screen signals.", "action": "Repair the proposition binding before writing; do not leave the page judgment as an isolated backend field."})
    if len(nodes) >= 4 and len(page.get("argument_chain") or []) <= 1:
        issues.append({"code": "ARGUMENT_CHAIN_TOO_COARSE", "message": "The governing argument chain is too coarse to explain the page logic.", "action": "Retain the authored node-and-edge contract and split the page argument chain into its actual reasoning stages."})
    edge_ids: set[str] = set()
    for edge in edges:
        edge_id = str(edge.get("id") or "").strip()
        relation = str(edge.get("relation") or "").strip()
        basis = str(edge.get("basis") or "").strip()
        if not edge_id or edge_id in edge_ids or str(edge.get("from") or "") not in ids or str(edge.get("to") or "") not in ids or str(edge.get("from") or "") == str(edge.get("to") or "") or not relation or basis not in _VALID_BASES or str(edge.get("confidence") or "") not in _VALID_CONFIDENCE:
            issues.append({"code": "PAGE_RELATION_MISSING", "message": "Each page logic edge needs valid endpoints, relation, basis, and confidence.", "action": "Declare the relationship from source evidence rather than relying on adjacent copy."})
            continue
        edge_ids.add(edge_id)
        if basis == "inferred" and not str(edge.get("inference_rationale") or "").strip():
            issues.append({"code": "PAGE_RELATION_INFERENCE_RATIONALE_MISSING", "message": "An inferred page relation has no rationale.", "action": "State why the inference is warranted, or remove the edge."})
        if basis == "inferred" and relation in _STRONG_CAUSAL_RELATIONS:
            issues.append({"code": "UNSUPPORTED_CAUSAL_LANGUAGE", "message": "An inferred relation uses strong causal language.", "action": "Use a weaker relation such as requires or supports, or retain only explicit causal wording."})
    planned_nodes = [str(node_id) for paragraph in paragraphs for node_id in paragraph.get("node_ids") or []]
    if not paragraphs or set(planned_nodes) != ids or len(planned_nodes) != len(set(planned_nodes)):
        issues.append({"code": "PROSE_PARAGRAPH_LOGIC_GAP", "message": "Paragraph plan must place every logic node once in the authored reading order.", "action": "Plan full-prose paragraphs around logic nodes before compressing on-screen text."})
    required_edges = {str(edge.get("id")) for edge in edges if str(edge.get("onscreen_requirement") or "required") == "required"}
    carried_edges: set[str] = set()
    carried_nodes: set[str] = set()
    for projection in projections:
        edge_refs = {str(item) for item in projection.get("edge_ids") or [] if str(item)}
        node_refs = {str(item) for item in projection.get("node_ids") or [] if str(item)}
        carrier = str(projection.get("carrier") or "").strip()
        mode = str(projection.get("carrier_mode") or "").strip()
        signal = str(projection.get("relation_signal") or "").strip()
        onscreen_signals = _signals(projection.get("onscreen_signals"))
        if (
            not edge_refs.issubset(edge_ids)
            or not node_refs.issubset(ids)
            or not (edge_refs or node_refs)
            or not carrier
            or mode not in _VALID_CARRIERS
            or not signal
            or not onscreen_signals
        ):
            issues.append({"code": "ONSCREEN_RELATION_CARRIER_MISSING", "message": "Every on-screen projection needs a real carrier, mode, relation signal, projection signals, and known logic node or edge ids.", "action": "Map each required node and edge to a visible connector, ordered chain, or integrated proposition."})
            continue
        carried_edges.update(edge_refs)
        carried_nodes.update(node_refs)
    missing_edges = tuple(sorted(required_edges - carried_edges))
    if missing_edges:
        issues.append({"code": "ONSCREEN_ARGUMENT_EDGE_MISSING", "message": "Required logic edges have no on-screen carrier declaration.", "evidence": missing_edges, "action": "Add an on-screen logic projection; do not flatten a directed chain into peer phrases."})
    missing_nodes = tuple(sorted(required_nodes - carried_nodes))
    if missing_nodes:
        issues.append({"code": "ONSCREEN_ARGUMENT_NODE_MISSING", "message": "A required logic node has no on-screen carrier declaration.", "evidence": missing_nodes, "action": "Keep the source-grounded current state, demand, or requirement visible; mark a node prose_only only when it does not carry the page argument."})
    logic_nodes = {
        str(node.get("id") or ""): node
        for node in nodes
        if str(node.get("id") or "") in ids
    }
    issues.extend(_validate_onscreen_expression_ir(
        contract,
        page_refs=page_refs,
        logic_nodes=logic_nodes,
        required_nodes=required_nodes,
    ))
    return issues


def build_page_logic_preflight(page: dict[str, object]) -> dict[str, object]:
    issues = validate_page_logic_contract(page)
    return {
        "mode": page_logic_mode(page),
        "contract_status": "blocked" if issues else ("ready" if page_logic_mode(page) == REQUIRED_MODE else "advisory"),
        "contract": _contract(page),
        "candidate": build_candidate_page_logic(page),
        "issues": issues,
    }


def validate_authored_page_logic(page: dict[str, object], *, prose: str, onscreen: str, module_titles: tuple[str, ...]) -> list[dict[str, object]]:
    """Check that an authored script consumes the approved logic plan."""

    issues = validate_page_logic_contract(page)
    if page_logic_mode(page) != REQUIRED_MODE:
        return issues
    contract = _contract(page)
    paragraphs = [value.strip() for value in re.split(r"\n\s*\n", prose) if value.strip()]
    plan = [item for item in contract.get("paragraph_plan") or [] if isinstance(item, dict)]
    if len(paragraphs) != len(plan):
        issues.append({"code": "PROSE_PARAGRAPH_LOGIC_GAP", "message": "Full prose paragraph count does not match the approved logic paragraph plan.", "action": "Keep one authored prose paragraph for each planned reasoning stage."})
    for index, paragraph_plan in enumerate(plan):
        if index >= len(paragraphs):
            break
        for node_id in paragraph_plan.get("node_ids") or []:
            node = next(
                (item for item in contract.get("nodes") or []
                 if isinstance(item, dict) and str(item.get("id") or "") == str(node_id)),
                {},
            )
            missing = _missing_signals(paragraphs[index], _signals(node.get("prose_signals")))
            if missing:
                issues.append({"code": "PROSE_ARGUMENT_NODE_MISSING", "message": "A planned logic node is absent from its full-prose reasoning paragraph.", "evidence": missing, "action": "Keep the node's business object, current state, or requirement in the planned paragraph before compressing it for the screen."})
    proposition = contract.get("page_proposition")
    if isinstance(proposition, dict):
        missing = _missing_signals(prose, _signals(proposition.get("prose_signals")))
        if missing:
            issues.append({"code": "PROSE_PAGE_PROPOSITION_MISSING", "message": "The full prose does not establish the approved page proposition.", "evidence": missing, "action": "Write the page proposition as the conclusion of the source-grounded reasoning, not as a separate metadata field."})
    titles = {_compact(title) for title in module_titles if _compact(title)}
    compact_onscreen = _compact(onscreen)
    for node in contract.get("nodes") or []:
        if not isinstance(node, dict) or str(node.get("onscreen_requirement") or "required") != "required":
            continue
        missing = _missing_signals(onscreen, _signals(node.get("onscreen_signals")))
        if missing:
            issues.append({"code": "ONSCREEN_ARGUMENT_NODE_MISSING", "message": "A required logic node was compressed out of the authored on-screen layer.", "source_refs": tuple(_refs(node.get("source_refs"))), "evidence": missing, "action": "Keep this source-grounded current state, demand, boundary, or requirement visible on screen; shorten wording only after its decisive meaning remains."})
    if isinstance(proposition, dict):
        missing = _missing_signals(onscreen, _signals(proposition.get("onscreen_signals")))
        if missing:
            issues.append({"code": "ONSCREEN_PAGE_PROPOSITION_MISSING", "message": "The approved page proposition is not readable in the authored on-screen layer.", "evidence": missing, "action": "Present the page judgment as a visible conclusion, integrated proposition, or relationship outcome."})
    for projection in contract.get("onscreen_projection") or []:
        if not isinstance(projection, dict):
            continue
        carrier = _compact(projection.get("carrier"))
        carrier_mode = str(projection.get("carrier_mode") or "").strip()
        signal = _compact(projection.get("relation_signal"))
        missing = _missing_signals(onscreen, _signals(projection.get("onscreen_signals")))
        carrier_visible = (
            carrier in compact_onscreen
            if carrier_mode == "integrated_landing"
            else carrier in titles
        )
        if not carrier_visible or signal not in compact_onscreen or missing:
            issues.append({"code": "ONSCREEN_RELATION_CARRIER_MISSING", "message": "The authored on-screen layer does not contain the approved relation carrier and signal.", "evidence": tuple(value for value in (carrier, signal) if value), "action": "Keep the declared relation readable on screen; short phrases may compress facts but may not remove the relationship."})
    expression = _expression_ir(contract)
    if expression is not None:
        for node in expression.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            missing = _missing_signals(onscreen, _expression_texts(node))
            if missing:
                issues.append({"code": "ONSCREEN_EXPRESSION_TEXT_MISSING", "message": "A declared expression node is not fully readable in the authored on-screen layer.", "source_refs": tuple(_refs(node.get("source_refs"))), "evidence": missing, "action": "Keep every declared statement or object-group item visible; shorten through hierarchy rather than deletion."})
        for edge in expression.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            label = str(edge.get("visible_label") or "").strip()
            if label and _compact(label) not in compact_onscreen:
                issues.append({"code": "ONSCREEN_EXPRESSION_RELATION_MISSING", "message": "A declared expression relationship label is not readable on screen.", "source_refs": tuple(_refs(edge.get("source_refs"))), "evidence": (label,), "action": "Retain the visible connector or relationship label so readers can follow the authored argument."})
        unmapped = _unmapped_onscreen_lines(onscreen, expression)
        if unmapped:
            issues.append({"code": "ONSCREEN_EXPRESSION_COPY_UNMAPPED", "message": "On-screen copy contains wording that is not carried by the declared page expression graph.", "evidence": unmapped, "action": "Remove the wording, or add it as an expression node or relation with a source-grounded path to the page proposition."})
    return issues


def render_page_logic_contract(page: dict[str, object]) -> list[str]:
    """Return a readable non-audience view for authors and human reviewers."""

    if page_logic_mode(page) != REQUIRED_MODE:
        return [
            "- 状态：advisory（尚未启用页面逻辑硬门禁）",
            render_content_route(page),
        ]
    contract = _contract(page)
    lines = ["- 状态：required", render_content_route(page)]
    proposition = contract.get("page_proposition")
    if isinstance(proposition, dict):
        lines.append(
            "- 页面命题："
            f"{proposition.get('statement')}｜节点 {'、'.join(str(item) for item in proposition.get('node_ids') or [])}"
            f"｜完整稿信号 {'、'.join(_signals(proposition.get('prose_signals')))}"
            f"｜上屏信号 {'、'.join(_signals(proposition.get('onscreen_signals')))}"
        )
    for node in contract.get("nodes") or []:
        if isinstance(node, dict):
            lines.append(
                f"- 节点 {node.get('id')}｜{node.get('role')}｜{node.get('onscreen_requirement', 'required')}"
                f"｜{'、'.join(_refs(node.get('source_refs')))}｜{node.get('statement')}"
                f"｜完整稿信号 {'、'.join(_signals(node.get('prose_signals')))}"
                f"｜上屏信号 {'、'.join(_signals(node.get('onscreen_signals')))}"
            )
    for edge in contract.get("edges") or []:
        if isinstance(edge, dict):
            lines.append(f"- 关系 {edge.get('id')}：{edge.get('from')} --{edge.get('relation')}--> {edge.get('to')}｜{edge.get('basis')}/{edge.get('confidence')}")
    for index, paragraph in enumerate(contract.get("paragraph_plan") or [], start=1):
        if isinstance(paragraph, dict):
            lines.append(f"- 段落 {index}：{'、'.join(str(item) for item in paragraph.get('node_ids') or [])}")
    for projection in contract.get("onscreen_projection") or []:
        if isinstance(projection, dict):
            item_ids = [
                *[str(item) for item in projection.get('node_ids') or []],
                *[str(item) for item in projection.get('edge_ids') or []],
            ]
            lines.append(
                f"- 上屏承载：{'、'.join(item_ids)} → {projection.get('carrier')}"
                f"（{projection.get('relation_signal')}；{'、'.join(_signals(projection.get('onscreen_signals'))) }）"
            )
    expression = _expression_ir(contract)
    if expression is not None:
        lines.append(
            f"- 上屏表达模式：{expression.get('pattern')}｜阅读顺序 {' → '.join(str(item) for item in expression.get('reading_order') or [])}"
        )
        for node in expression.get("nodes") or []:
            if isinstance(node, dict):
                visible = "、".join(_expression_surface_texts(node))
                lines.append(
                    f"- 表达节点 {node.get('id')}｜{node.get('role')}／{node.get('render')}"
                    f"｜逻辑 {'、'.join(str(item) for item in node.get('logic_node_ids') or [])}"
                    f"｜{visible}"
                )
        for edge in expression.get("edges") or []:
            if isinstance(edge, dict):
                lines.append(
                    f"- 表达关系 {edge.get('id')}：{edge.get('from')} --{edge.get('visible_label')}--> {edge.get('to')}"
                    f"｜{edge.get('source_basis')}"
                )
    return lines


def render_onscreen_expression_ir(page: dict[str, object]) -> list[str]:
    """Render the author-declared screen expression graph for review only."""

    expression = _expression_ir(_contract(page))
    if expression is None:
        return ["- 未声明上屏表达图；沿用现有页面逻辑合同。"]
    lines = [
        f"- 模式：{expression.get('pattern')}",
        f"- 阅读顺序：{' → '.join(str(item) for item in expression.get('reading_order') or [])}",
    ]
    for node in expression.get("nodes") or []:
        if isinstance(node, dict):
            visible = "、".join(_expression_surface_texts(node))
            lines.append(
                f"- 节点 {node.get('id')}｜{node.get('role')}／{node.get('render')}"
                f"｜逻辑 {'、'.join(str(item) for item in node.get('logic_node_ids') or [])}"
                f"｜{visible}"
            )
    for edge in expression.get("edges") or []:
        if isinstance(edge, dict):
            lines.append(
                f"- 关系 {edge.get('id')}：{edge.get('from')} --{edge.get('visible_label')}--> {edge.get('to')}"
                f"｜{edge.get('source_basis')}"
            )
    return lines


__all__ = [
    "REQUIRED_MODE",
    "ONSCREEN_EXPRESSION_IR_SCHEMA",
    "build_candidate_page_logic",
    "build_page_logic_preflight",
    "page_logic_mode",
    "render_page_logic_contract",
    "render_onscreen_expression_ir",
    "validate_authored_page_logic",
    "validate_page_logic_contract",
]

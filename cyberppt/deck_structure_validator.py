"""Deck-level semantic/visual structure collapse checks for Stage 02.

The validator accepts both verifier-rich handoff pages and the compiled visual
spec.  Compiled pages do not need a new schema field: when ``semantic_contract``
is absent, verified/canonical business relations preserved in
``semantic_graph.business_relationships`` are resolved back into semantic
topology for the cross-check.
"""
from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

from cyberppt.topology_resolver import resolve_semantic_topology


_DIRECTED_SEMANTIC_TOPOLOGIES = {
    "dependency_chain",
    "sequence",
    "causal_chain",
    "support_convergence",
    "feedback_loop",
    "layered_structure",
}
_PEER_LIKE_VISUAL_TOPOLOGIES = {"parallel_set"}


def _page_id(page: Mapping[str, object]) -> str:
    return str(page.get("page_id") or "")


def _semantic(page: Mapping[str, object]) -> tuple[str, str, float]:
    contract = page.get("semantic_contract")
    contract = contract if isinstance(contract, Mapping) else {}
    topology = contract.get("topology")
    topology = topology if isinstance(topology, Mapping) else {}
    explicit_topology = str(topology.get("primary_topology") or "").strip()
    if explicit_topology:
        return (
            explicit_topology,
            str(topology.get("constraint_authority") or "soft"),
            float(topology.get("confidence") or 0.0),
        )

    # The compiler already preserves the relationship authority in the graph.
    # Re-resolve it here instead of adding another semantic field to the visual
    # spec schema.  This makes the deck check usable on official compiled specs
    # and keeps semantic verification separate from visual topology selection.
    graph = page.get("semantic_graph")
    graph = graph if isinstance(graph, Mapping) else {}
    relationships = graph.get("business_relationships")
    if isinstance(relationships, list) and relationships:
        verified = [item for item in relationships if isinstance(item, Mapping)]
        resolved = resolve_semantic_topology(verified)
        return (
            str(resolved.get("primary_topology") or "unknown"),
            str(resolved.get("constraint_authority") or "soft"),
            float(resolved.get("confidence") or 0.0),
        )
    return "unknown", "soft", 0.0


def _visual(page: Mapping[str, object]) -> str:
    graph = page.get("semantic_graph")
    graph = graph if isinstance(graph, Mapping) else {}
    return str(graph.get("topology") or "")


def _form(page: Mapping[str, object]) -> str:
    contract = page.get("expression_contract")
    contract = contract if isinstance(contract, Mapping) else {}
    return str(contract.get("form") or "")


def _ratio(counter: Counter[str], total: int) -> tuple[str, float]:
    if not counter or total <= 0:
        return "", 0.0
    key, count = counter.most_common(1)[0]
    return key, count / total


def audit_deck_structure_collapse(pages: Sequence[Mapping[str, object]]) -> dict[str, object]:
    """Check semantic-vs-visual mismatch and suspicious deck-wide repetition.

    Repetition alone is never proof of an error: a deck may legitimately
    contain several peer pages. Blocking is reserved for a semantic mismatch
    or for repeated visual parallelism that contradicts at least one page's
    semantic topology.
    """

    content = [
        page
        for page in pages
        if isinstance(page, Mapping) and str(page.get("page_role") or "") != "chapter"
    ]
    blocking: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []

    semantic_values: list[str] = []
    visual_values: list[str] = []
    form_values: list[str] = []
    rows: list[tuple[str, str, str, str, float]] = []

    for page in content:
        semantic, authority, confidence = _semantic(page)
        visual = _visual(page)
        form = _form(page)
        page_id = _page_id(page)
        semantic_values.append(semantic)
        visual_values.append(visual)
        form_values.append(form)
        rows.append((page_id, semantic, visual, authority, confidence))

        if semantic in _DIRECTED_SEMANTIC_TOPOLOGIES and visual in _PEER_LIKE_VISUAL_TOPOLOGIES:
            issue = {
                "code": "DIRECTED_SEMANTICS_FLATTENED_TO_PARALLEL",
                "page_ids": [page_id],
                "message": (
                    f"{page_id} has semantic topology {semantic!r} but selected "
                    f"visual topology {visual!r}."
                ),
            }
            if authority in {"hard", "strong"} or confidence >= 0.80:
                blocking.append(issue)
            else:
                warnings.append(issue)

    total = len(content)
    semantic_counter = Counter(value for value in semantic_values if value)
    visual_counter = Counter(value for value in visual_values if value)
    form_counter = Counter(value for value in form_values if value)
    common_semantic, common_semantic_ratio = _ratio(semantic_counter, total)
    common_visual, common_visual_ratio = _ratio(visual_counter, total)
    common_form, common_form_ratio = _ratio(form_counter, total)
    peer_like_count = sum(1 for value in visual_values if value in _PEER_LIKE_VISUAL_TOPOLOGIES)
    peer_like_ratio = peer_like_count / total if total else 0.0

    if total >= 5 and common_form_ratio > 0.35:
        warnings.append({
            "code": "DECK_EXPRESSION_FORM_CONCENTRATION",
            "page_ids": [],
            "message": (
                f"Expression form {common_form!r} appears on {common_form_ratio:.0%} "
                "of content pages; review for structural overuse."
            ),
        })
    if total >= 5 and peer_like_ratio > 0.40:
        warnings.append({
            "code": "DECK_PEER_LIKE_TOPOLOGY_CONCENTRATION",
            "page_ids": [],
            "message": (
                f"Peer-like visual topology appears on {peer_like_ratio:.0%} of "
                "content pages; review whether semantics were flattened."
            ),
        })
    if total >= 5 and common_visual_ratio > 0.50:
        warnings.append({
            "code": "DECK_VISUAL_TOPOLOGY_CONCENTRATION",
            "page_ids": [],
            "message": (
                f"Visual topology {common_visual!r} appears on "
                f"{common_visual_ratio:.0%} of content pages."
            ),
        })

    for length in (3, 4):
        for index in range(0, max(0, len(rows) - length + 1)):
            group = rows[index:index + length]
            visuals = {item[2] for item in group}
            if len(visuals) != 1 or not next(iter(visuals), ""):
                continue
            page_ids = [item[0] for item in group]
            visual = group[0][2]
            semantically_consistent = all(
                (item[1] == "peer_set" if visual == "parallel_set" else True)
                for item in group
            )
            if length == 3:
                warnings.append({
                    "code": "DECK_TOPOLOGY_RUN_WARNING",
                    "page_ids": page_ids,
                    "message": f"Three consecutive content pages use visual topology {visual!r}.",
                })
            elif visual == "parallel_set" and not semantically_consistent:
                blocking.append({
                    "code": "DECK_PARALLEL_COLLAPSE_REVIEW_REQUIRED",
                    "page_ids": page_ids,
                    "message": (
                        "Four consecutive pages use parallel_set while at least "
                        "one page is not semantically peer_set."
                    ),
                })
            else:
                warnings.append({
                    "code": "DECK_TOPOLOGY_RUN_WARNING",
                    "page_ids": page_ids,
                    "message": (
                        f"Four consecutive content pages use visual topology {visual!r}; "
                        "verify this repetition is semantically justified."
                    ),
                })

    return {
        "schema": "cyberppt.deck_structure_collapse_audit.v1",
        "status": "failed" if blocking else "passed",
        "metrics": {
            "content_page_count": total,
            "same_semantic_topology": {
                "topology": common_semantic,
                "ratio": round(common_semantic_ratio, 4),
            },
            "same_visual_topology": {
                "topology": common_visual,
                "ratio": round(common_visual_ratio, 4),
            },
            "same_expression_form": {
                "form": common_form,
                "ratio": round(common_form_ratio, 4),
            },
            "peer_like_visual_ratio": round(peer_like_ratio, 4),
        },
        "blocking_issues": blocking,
        "warnings": warnings,
    }


__all__ = ["audit_deck_structure_collapse"]

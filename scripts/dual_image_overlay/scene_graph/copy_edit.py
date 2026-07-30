from __future__ import annotations

import re
from dataclasses import replace
from typing import Any, Iterable, Mapping

from .schema import PageSceneGraph, TextNode


COPY_EDIT_SCHEMA = "cyberppt.semantic_safe_copy_edit.v1"
PROTECTED_QUALIFIERS = {
    "不",
    "无",
    "未",
    "非",
    "不得",
    "禁止",
    "必须",
    "应当",
    "可能",
    "可",
    "仅",
    "至少",
    "最多",
    "之前",
    "之后",
}
FACT_PATTERN = re.compile(
    r"\d+(?:\.\d+)?(?:%|％|年|月|日|个|项|次|小时|分钟|万元|亿元|万|亿)?"
    r"|[A-Za-z][A-Za-z0-9_.+/-]*"
)


def _normalized_token(value: str) -> str:
    return re.sub(r"\s+", "", value).casefold()


def protected_facts(text: str, *, protected_terms: Iterable[str] = ()) -> list[str]:
    facts = FACT_PATTERN.findall(text)
    facts.extend(term for term in PROTECTED_QUALIFIERS if term in text)
    facts.extend(str(term) for term in protected_terms if str(term).strip())
    return sorted(set(facts), key=lambda value: (_normalized_token(value), value))


def _fact_multiset(text: str, protected: Iterable[str]) -> list[str]:
    return sorted(_normalized_token(value) for value in protected_facts(text, protected_terms=protected))


def validate_semantic_safe_revision(
    source_text: str,
    revised_text: str,
    *,
    protected_terms: Iterable[str] = (),
) -> dict[str, Any]:
    source_facts = _fact_multiset(source_text, protected_terms)
    revised_facts = _fact_multiset(revised_text, protected_terms)
    issues: list[dict[str, Any]] = []
    if not revised_text.strip():
        issues.append({"code": "revised_text_empty", "blocking": True})
    if source_facts != revised_facts:
        issues.append(
            {
                "code": "protected_fact_changed",
                "source_facts": source_facts,
                "revised_facts": revised_facts,
                "blocking": True,
            }
        )
    return {
        "schema": "cyberppt.semantic_safe_copy_edit_gate.v1",
        "valid": not issues,
        "issues": issues,
        "protected_facts": protected_facts(source_text, protected_terms=protected_terms),
    }


def conservative_screen_edit(text: str) -> tuple[str, list[str]]:
    """Apply deterministic, meaning-preserving screen-copy cleanup only."""

    revised = re.sub(r"[ \t]+", " ", str(text)).strip()
    revised = re.sub(r"\s*([，。；：、！？])\s*", r"\1", revised)
    lines = [line.strip() for line in revised.splitlines()]
    deduped: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = _normalized_token(line)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(line)
    final = "\n".join(deduped)
    operations: list[str] = []
    if final != text:
        operations.append("normalize_screen_copy")
    if len(deduped) < len([line for line in lines if line]):
        operations.append("remove_duplicate_lines")
    return final, operations


def edit_text_node(
    node: TextNode,
    *,
    proposed_text: str | None = None,
    protected_terms: Iterable[str] = (),
) -> tuple[TextNode, dict[str, Any]]:
    source = node.text
    if proposed_text is None:
        revised, operations = conservative_screen_edit(source)
        mode = "deterministic_conservative"
    else:
        revised = str(proposed_text).strip()
        operations = ["proposed_semantic_rewrite"] if revised != source else []
        mode = "proposed_revision"
    gate = validate_semantic_safe_revision(source, revised, protected_terms=protected_terms)
    accepted = bool(gate["valid"])
    final_text = revised if accepted else source
    attributes = dict(node.attributes)
    attributes["copy_edit"] = {
        "schema": COPY_EDIT_SCHEMA,
        "mode": mode,
        "source_text": source,
        "revised_text": revised,
        "final_text": final_text,
        "operations": operations,
        "accepted": accepted,
        "gate": gate,
    }
    return replace(node, text=final_text, attributes=attributes), attributes["copy_edit"]


def edit_scene_graph_copy(
    graph: PageSceneGraph,
    *,
    proposed_revisions: Mapping[str, str] | None = None,
    protected_terms: Iterable[str] = (),
) -> tuple[PageSceneGraph, dict[str, Any]]:
    proposed = dict(proposed_revisions or {})
    nodes: list[TextNode] = []
    records: list[dict[str, Any]] = []
    for node in graph.text_nodes:
        updated, record = edit_text_node(
            node,
            proposed_text=proposed.get(node.node_id),
            protected_terms=protected_terms,
        )
        nodes.append(updated)
        records.append({"node_id": node.node_id, **record})
    report = {
        "schema": COPY_EDIT_SCHEMA,
        "page": graph.page,
        "valid": all(record["accepted"] for record in records),
        "changed_count": sum(record["source_text"] != record["final_text"] for record in records),
        "rejected_count": sum(not record["accepted"] for record in records),
        "items": records,
    }
    return replace(
        graph,
        text_nodes=nodes,
        metadata={**graph.metadata, "copy_edit": report},
    ), report

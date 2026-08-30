"""Shared source-argument indexes for PLAN audits and narrative selection."""
from __future__ import annotations

from typing import Any, Iterable


def _text(value: object) -> str:
    return str(value or "").strip()


def source_argument_index(foundation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index authored source argument nodes by stable id."""

    return {
        _text(node.get("id")): node
        for node in foundation.get("argument_nodes") or []
        if isinstance(node, dict) and _text(node.get("id"))
    }


def source_argument_method(foundation: dict[str, Any]) -> list[str]:
    semantics = foundation.get("document_semantics") or {}
    if not isinstance(semantics, dict):
        return []
    method = semantics.get("argument_method") or []
    nodes = source_argument_index(foundation)
    node_by_heading = {
        _text(node.get("source_heading")): node_id
        for node_id, node in nodes.items()
        if _text(node.get("source_heading"))
    }
    heading_by_ref = {
        ref: _text(item.get("title"))
        for item in foundation.get("source_structure") or []
        if isinstance(item, dict)
        for ref in item.get("source_refs") or []
        if _text(ref) and _text(item.get("title"))
    }

    resolved: list[str] = []
    for item in method:
        if isinstance(item, str) and _text(item):
            resolved.append(_text(item))
            continue
        if not isinstance(item, dict):
            continue
        for ref in item.get("source_refs") or []:
            node_id = node_by_heading.get(heading_by_ref.get(_text(ref), ""))
            if node_id:
                resolved.append(node_id)
    return list(dict.fromkeys(resolved))


def argument_source_refs(
    node_ids: Iterable[object],
    node_index: dict[str, dict[str, Any]],
) -> set[str]:
    refs: set[str] = set()
    for node_id in node_ids:
        node = node_index.get(_text(node_id))
        if not node:
            continue
        refs.update(_text(ref) for ref in node.get("source_refs") or [] if _text(ref))
    return refs


def evidence_intersects_arguments(
    node_ids: Iterable[object],
    evidence_refs: Iterable[object],
    node_index: dict[str, dict[str, Any]],
) -> bool:
    expected = argument_source_refs(node_ids, node_index)
    actual = {_text(ref) for ref in evidence_refs if _text(ref)}
    return not expected or bool(expected & actual)


__all__ = [
    "argument_source_refs",
    "evidence_intersects_arguments",
    "source_argument_index",
    "source_argument_method",
]

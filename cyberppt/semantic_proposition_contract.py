"""Machine-readable proposition graph for source-grounded Stage 01 outlines."""

from __future__ import annotations

from typing import Any


def build_proposition_graph(outline: dict[str, object]) -> dict[str, object]:
    propositions: list[dict[str, object]] = []
    relations: list[dict[str, object]] = []
    for raw_page in outline.get("pages", []):
        if not isinstance(raw_page, dict) or raw_page.get("page_type") != "content":
            continue
        page_id = str(raw_page.get("page_id") or "")
        statement = str(
            raw_page.get("core_message") or raw_page.get("main_message") or ""
        ).strip()
        derivation = raw_page.get("core_message_derivation") or raw_page.get("judgment_derivation")
        source_refs = list(raw_page.get("source_refs") or [])
        if isinstance(derivation, dict) and derivation.get("source_refs"):
            source_refs = list(derivation["source_refs"])
        if statement:
            propositions.append(
                {
                    "id": f"PROP-{page_id.upper()}",
                    "page_id": page_id,
                    "statement": statement,
                    "source_refs": source_refs,
                    "modality": "source_preserving",
                }
            )
        for index, relation in enumerate(raw_page.get("content_relations") or [], 1):
            if isinstance(relation, dict):
                relations.append(
                    {
                        "id": f"REL-{page_id.upper()}-{index:02d}",
                        "page_id": page_id,
                        **relation,
                    }
                )
    return {
        "schema": "cyberppt.proposition_graph.v1",
        "propositions": propositions,
        "relations": relations,
    }

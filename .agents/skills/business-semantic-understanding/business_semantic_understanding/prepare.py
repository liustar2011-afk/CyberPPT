from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


def _flatten_outline(nodes: list[dict[str, Any]], parent_id: str | None = None) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for node in nodes:
        item = {
            "section_id": node["section_id"],
            "level": node.get("level"),
            "title": node.get("title", ""),
            "line": node.get("line"),
            "parent_section_id": parent_id,
        }
        flattened.append(item)
        flattened.extend(_flatten_outline(list(node.get("children", [])), node["section_id"]))
    return flattened


def _json_sha256(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_inputs(structure: dict[str, Any], fact_base: dict[str, Any]) -> None:
    if structure.get("artifact_type") != "document_structure":
        raise ValueError("structure.json is not a document_structure artifact")
    if fact_base.get("artifact_type") != "source_fact_base":
        raise ValueError("fact-base.json is not a source_fact_base artifact")
    if structure.get("markdown_sha256") and fact_base.get("markdown_sha256"):
        if structure["markdown_sha256"] != fact_base["markdown_sha256"]:
            raise ValueError("structure.json and fact-base.json refer to different Markdown content")


def build_workpack(
    structure: dict[str, Any],
    fact_base: dict[str, Any],
    *,
    chunk_size: int = 60,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be at least 1")
    _validate_inputs(structure, fact_base)

    outline = _flatten_outline(list(structure.get("outline", [])))
    section_by_id = {section["section_id"]: section for section in outline}
    block_by_id = {block["block_id"]: block for block in structure.get("blocks", [])}

    facts_by_section: dict[str, list[dict[str, Any]]] = {}
    preamble: list[dict[str, Any]] = []
    for fact in fact_base.get("entries", []):
        source_ref = fact.get("source_ref", {})
        block = block_by_id.get(source_ref.get("block_id"))
        section_id = block.get("section_id") if block else None
        if section_id:
            facts_by_section.setdefault(section_id, []).append(deepcopy(fact))
        else:
            preamble.append(deepcopy(fact))

    sections: list[dict[str, Any]] = []
    if preamble:
        sections.append({
            "section_id": "preamble",
            "level": 0,
            "title": "Preamble",
            "parent_section_id": None,
            "fact_ids": [fact["fact_id"] for fact in preamble],
            "block_ids": sorted({fact.get("source_ref", {}).get("block_id") for fact in preamble if fact.get("source_ref", {}).get("block_id")}),
        })
    for section in outline:
        facts = facts_by_section.get(section["section_id"], [])
        sections.append({
            **section,
            "fact_ids": [fact["fact_id"] for fact in facts],
            "block_ids": sorted({fact.get("source_ref", {}).get("block_id") for fact in facts if fact.get("source_ref", {}).get("block_id")}),
        })

    chunks: list[dict[str, Any]] = []

    def append_chunks(section_id: str, facts: list[dict[str, Any]]) -> None:
        if not facts:
            return
        section = section_by_id.get(section_id, {
            "section_id": "preamble",
            "level": 0,
            "title": "Preamble",
            "line": None,
            "parent_section_id": None,
        })
        for offset in range(0, len(facts), chunk_size):
            subset = facts[offset : offset + chunk_size]
            chunk_id = f"chunk-{len(chunks) + 1:04d}"
            block_ids = [fact.get("source_ref", {}).get("block_id") for fact in subset]
            blocks = [deepcopy(block_by_id[block_id]) for block_id in dict.fromkeys(block_ids) if block_id in block_by_id]
            chunks.append({
                "schema_version": "1.0",
                "artifact_type": "semantic_work_chunk",
                "chunk_id": chunk_id,
                "section": deepcopy(section),
                "document_outline": deepcopy(outline),
                "facts": deepcopy(subset),
                "source_blocks": blocks,
                "semantic_policy": {
                    "truth_status": "source_assertions_unverified",
                    "external_enrichment": "forbidden",
                    "inference_must_be_labeled": True,
                },
            })

    if preamble:
        append_chunks("preamble", preamble)
    for section in outline:
        append_chunks(section["section_id"], facts_by_section.get(section["section_id"], []))

    warnings: list[dict[str, Any]] = []
    source_fact_count = len(fact_base.get("entries", []))
    chunked_fact_count = sum(len(chunk["facts"]) for chunk in chunks)
    if source_fact_count != chunked_fact_count:
        warnings.append({
            "code": "fact_chunk_count_mismatch",
            "severity": "error",
            "message": f"Expected {source_fact_count} facts but chunked {chunked_fact_count}.",
        })

    workpack = {
        "schema_version": "1.0",
        "artifact_type": "semantic_workpack",
        "source": deepcopy(fact_base.get("source") or structure.get("source") or {}),
        "input_markdown": fact_base.get("input_markdown") or structure.get("input_markdown"),
        "markdown_sha256": fact_base.get("markdown_sha256") or structure.get("markdown_sha256"),
        "foundation": {
            "structure_sha256": _json_sha256(structure),
            "fact_base_sha256": _json_sha256(fact_base),
        },
        "document": {
            "title": structure.get("document", {}).get("title"),
            "heading_count": structure.get("document", {}).get("heading_count", 0),
            "block_count": structure.get("document", {}).get("block_count", 0),
            "source_fact_count": source_fact_count,
            "section_count": len(outline),
            "chunk_count": len(chunks),
        },
        "outline": deepcopy(outline),
        "sections": sections,
        "chunks": [
            {
                "chunk_id": chunk["chunk_id"],
                "file": f"chunks/{chunk['chunk_id']}.json",
                "section_id": chunk["section"]["section_id"],
                "fact_ids": [fact["fact_id"] for fact in chunk["facts"]],
            }
            for chunk in chunks
        ],
        "semantic_policy": {
            "source_assertions_are_verified_truth": False,
            "external_enrichment": "forbidden",
            "preserve_conflicts_and_ambiguity": True,
            "inference_must_be_labeled": True,
        },
        "warnings": warnings,
    }
    return workpack, chunks


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare_foundation(
    foundation_dir: Path | str,
    output_dir: Path | str,
    *,
    chunk_size: int = 60,
    force: bool = False,
) -> dict[str, Any]:
    foundation = Path(foundation_dir)
    output = Path(output_dir)
    structure_path = foundation / "structure.json"
    fact_base_path = foundation / "fact-base.json"
    if not structure_path.is_file():
        raise FileNotFoundError(f"Missing layer-two artifact: {structure_path}")
    if not fact_base_path.is_file():
        raise FileNotFoundError(f"Missing layer-two artifact: {fact_base_path}")

    workpack_path = output / "semantic-workpack.json"
    if workpack_path.exists() and not force:
        raise FileExistsError(f"Semantic workpack already exists: {workpack_path}")

    structure = _read_json(structure_path)
    fact_base = _read_json(fact_base_path)
    workpack, chunks = build_workpack(structure, fact_base, chunk_size=chunk_size)

    output.mkdir(parents=True, exist_ok=True)
    if force and (output / "chunks").exists():
        for old in (output / "chunks").glob("chunk-*.json"):
            old.unlink()
    _write_json(workpack_path, workpack)
    for chunk in chunks:
        _write_json(output / "chunks" / f"{chunk['chunk_id']}.json", chunk)

    return {
        "status": "prepared",
        "foundation": str(foundation),
        "output": str(output),
        "workpack": str(workpack_path),
        "chunk_count": len(chunks),
        "fact_count": workpack["document"]["source_fact_count"],
        "warnings": workpack["warnings"],
    }

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any


AUTHORED_SEMANTIC_ARTIFACTS = (
    "normalized-facts.json",
    "concept-base.json",
    "relation-graph.json",
    "argument-chain.json",
    "semantic-report.json",
)
FOUNDATION_DIGEST_VERSION = "semantic-foundation-v1"


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


def _semantic_foundation_digest(payload: dict[str, Any], artifact_type: str) -> str:
    """Hash semantic source content while excluding volatile provenance metadata."""
    if artifact_type == "document_structure":
        stable = {
            "schema_version": payload.get("schema_version"),
            "artifact_type": payload.get("artifact_type"),
            "markdown_sha256": payload.get("markdown_sha256"),
            "document": payload.get("document", {}),
            "outline": payload.get("outline", []),
            "blocks": payload.get("blocks", []),
        }
    elif artifact_type == "source_fact_base":
        stable = {
            "schema_version": payload.get("schema_version"),
            "artifact_type": payload.get("artifact_type"),
            "markdown_sha256": payload.get("markdown_sha256"),
            "semantics": payload.get("semantics", {}),
            "entries": payload.get("entries", []),
        }
    else:
        raise ValueError(f"Unsupported foundation artifact type: {artifact_type}")
    return _json_sha256(stable)


def _foundation_changed(
    previous: dict[str, Any] | None,
    current: dict[str, Any],
    current_legacy_foundation: dict[str, str],
) -> bool:
    if not isinstance(previous, dict):
        return False
    previous_foundation = previous.get("foundation", {})
    current_foundation = current.get("foundation", {})
    if previous_foundation.get("digest_version") == FOUNDATION_DIGEST_VERSION:
        return previous_foundation != current_foundation

    # Legacy workpacks hashed complete JSON artifacts. Exact equality proves the
    # digest-algorithm migration itself did not change the source foundation.
    # Any other legacy difference stays fail-closed because a parser change can
    # alter semantic assertions while leaving the Markdown hash unchanged.
    return previous_foundation != current_legacy_foundation


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

    # Chunks are filled up to chunk_size in document order. A section with fewer
    # facts than chunk_size does not get a dedicated chunk of its own; instead its
    # facts are appended to a shared buffer with the neighboring sections that
    # follow it, so a document with many short sections does not explode into one
    # near-empty chunk per section. A section is only split across chunks when it
    # alone has at least chunk_size facts.
    pending: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
    pending_count = 0

    def _default_section(section_id: str) -> dict[str, Any]:
        return {
            "section_id": section_id,
            "level": 0,
            "title": "Preamble",
            "line": None,
            "parent_section_id": None,
        }

    def _flush() -> None:
        if not pending:
            return
        sections_in_chunk = [deepcopy(section) for section, _ in pending]
        facts_in_chunk: list[dict[str, Any]] = []
        for _, section_facts in pending:
            facts_in_chunk.extend(section_facts)
        chunk_id = f"chunk-{len(chunks) + 1:04d}"
        block_ids = [fact.get("source_ref", {}).get("block_id") for fact in facts_in_chunk]
        blocks = [deepcopy(block_by_id[block_id]) for block_id in dict.fromkeys(block_ids) if block_id in block_by_id]
        chunks.append({
            "schema_version": "1.0",
            "artifact_type": "semantic_work_chunk",
            "chunk_id": chunk_id,
            "section": sections_in_chunk[0],
            "sections": sections_in_chunk,
            "section_ids": [section["section_id"] for section in sections_in_chunk],
            "document_outline": deepcopy(outline),
            "facts": deepcopy(facts_in_chunk),
            "source_blocks": blocks,
            "semantic_policy": {
                "truth_status": "source_assertions_unverified",
                "external_enrichment": "allowed_with_basis_label",
                "inference_must_be_labeled": True,
            },
        })
        pending.clear()

    def append_chunks(section_id: str, facts: list[dict[str, Any]]) -> None:
        nonlocal pending_count
        if not facts:
            return
        section = section_by_id.get(section_id, _default_section(section_id))
        remaining = list(facts)

        if pending_count and len(remaining) > chunk_size - pending_count:
            room = chunk_size - pending_count
            pending.append((section, remaining[:room]))
            remaining = remaining[room:]
            _flush()
            pending_count = 0

        while len(remaining) >= chunk_size:
            pending.append((section, remaining[:chunk_size]))
            _flush()
            pending_count = 0
            remaining = remaining[chunk_size:]

        if remaining:
            pending.append((section, remaining))
            pending_count += len(remaining)

    if preamble:
        append_chunks("preamble", preamble)
    for section in outline:
        append_chunks(section["section_id"], facts_by_section.get(section["section_id"], []))
    _flush()

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
            "digest_version": FOUNDATION_DIGEST_VERSION,
            "structure_sha256": _semantic_foundation_digest(structure, "document_structure"),
            "fact_base_sha256": _semantic_foundation_digest(fact_base, "source_fact_base"),
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
                "section_ids": chunk["section_ids"],
                "fact_ids": [fact["fact_id"] for fact in chunk["facts"]],
            }
            for chunk in chunks
        ],
        "semantic_policy": {
            "source_assertions_are_verified_truth": False,
            "external_enrichment": "allowed_with_basis_label",
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

    previous_workpack = _read_json(workpack_path) if workpack_path.is_file() else None
    structure = _read_json(structure_path)
    fact_base = _read_json(fact_base_path)
    workpack, chunks = build_workpack(structure, fact_base, chunk_size=chunk_size)

    invalidated: list[str] = []
    current_legacy_foundation = {
        "structure_sha256": _json_sha256(structure),
        "fact_base_sha256": _json_sha256(fact_base),
    }
    upstream_changed = bool(
        force
        and _foundation_changed(previous_workpack, workpack, current_legacy_foundation)
    )
    if upstream_changed:
        for name in AUTHORED_SEMANTIC_ARTIFACTS:
            path = output / name
            if path.is_file():
                path.unlink()
                invalidated.append(name)

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
        "upstream_changed": upstream_changed,
        "foundation_digest": workpack["foundation"],
        "invalidated_authored_artifacts": invalidated,
        "warnings": workpack["warnings"],
    }

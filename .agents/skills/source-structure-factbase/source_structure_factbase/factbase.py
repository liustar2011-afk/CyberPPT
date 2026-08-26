from __future__ import annotations

import re
from typing import Any


_TERMINAL_RE = re.compile(r"[。！？；!?;]+")


def _split_atomic(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts: list[str] = []
    start = 0
    for match in _TERMINAL_RE.finditer(text):
        end = match.end()
        piece = text[start:end].strip()
        if piece:
            parts.append(piece)
        start = end
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return parts


def _base_entry(fact_id: str, fact_type: str, text: str, block: dict[str, Any]) -> dict[str, Any]:
    return {
        "fact_id": fact_id,
        "fact_type": fact_type,
        "text": text,
        "heading_path": list(block.get("heading_path", [])),
        "claim_status": "source_assertion",
        "verification_status": "unverified",
        "semantic_role": "unclassified",
        "source_ref": {
            "block_id": block["block_id"],
            "line_start": block["line_start"],
            "line_end": block["line_end"],
        },
    }


def build_fact_base(structure: dict[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    base_index = 0

    def next_id() -> str:
        nonlocal base_index
        base_index += 1
        return f"fact-{base_index:04d}"

    for block in structure.get("blocks", []):
        block_type = block.get("type")
        if block_type in {"paragraph", "list_item", "blockquote"}:
            for segment_index, piece in enumerate(_split_atomic(str(block.get("text", ""))), start=1):
                entry = _base_entry(next_id(), "statement", piece, block)
                entry["segment_index"] = segment_index
                entries.append(entry)
            continue

        if block_type == "table":
            headers = list(block.get("headers", []))
            rows = list(block.get("rows", []))
            raw_rows = list(block.get("raw_rows", []))
            candidate_header = (
                block.get("candidate_header")
                if isinstance(block.get("candidate_header"), dict)
                else None
            )
            for row_index, cells in enumerate(rows):
                raw_text = raw_rows[row_index] if row_index < len(raw_rows) else ""
                parent_id = next_id()
                entry = _base_entry(parent_id, "table_record", raw_text, block)
                row_line = int(block["line_start"]) + 2 + row_index
                entry["source_ref"] = {
                    "block_id": block["block_id"],
                    "line_start": row_line,
                    "line_end": row_line,
                }
                entry["table"] = {
                    "headers": headers,
                    "header_status": str(block.get("header_status") or ""),
                    "cells": list(cells),
                    "row_index": row_index + 1,
                    "row_role": (
                        "candidate_header"
                        if candidate_header
                        and candidate_header.get("status") == "unconfirmed"
                        and candidate_header.get("row_index") == row_index + 1
                        and candidate_header.get("line_start") == row_line
                        else "data"
                    ),
                }
                if entry["table"]["row_role"] == "candidate_header":
                    entry["table"]["candidate_header"] = dict(candidate_header)
                entries.append(entry)
                row_label = str(cells[0]).strip() if cells else ""
                for cell_index, raw_cell in enumerate(cells, start=1):
                    cell_text = str(raw_cell).strip()
                    if not cell_text:
                        continue
                    header = str(headers[cell_index - 1]).strip() if cell_index <= len(headers) else ""
                    for segment_index, piece in enumerate(_split_atomic(cell_text), start=1):
                        context = []
                        if cell_index > 1 and row_label:
                            context.append(row_label)
                        if header:
                            context.append(header)
                        statement = f"{'｜'.join(context)}：{piece}" if context else piece
                        child = _base_entry(
                            f"{parent_id}-c{cell_index:02d}-s{segment_index:02d}",
                            "table_cell_statement",
                            statement,
                            block,
                        )
                        child["source_ref"] = dict(entry["source_ref"])
                        child["parent_fact_id"] = parent_id
                        child["segment_index"] = segment_index
                        child["table_cell"] = {
                            "row_index": row_index + 1,
                            "cell_index": cell_index,
                            "header": header,
                            "row_label": row_label,
                            "source_text": piece,
                            "row_role": entry["table"]["row_role"],
                        }
                        entries.append(child)

    warnings: list[dict[str, str]] = []
    if not entries:
        warnings.append({
            "code": "no_fact_entries",
            "severity": "warning",
            "message": "No source assertion entries were generated from eligible content blocks.",
        })

    return {
        "schema_version": "1.0",
        "artifact_type": "source_fact_base",
        "source": structure.get("source", {}),
        "input_markdown": structure.get("input_markdown"),
        "markdown_sha256": structure.get("markdown_sha256"),
        "semantics": {
            "entry_status": "source_assertion_candidates",
            "truth_policy": "Entries record what the source says; they are not independently verified truths.",
        },
        "entries": entries,
        "warnings": warnings,
    }

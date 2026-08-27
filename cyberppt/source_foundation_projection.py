"""Project validated Source Foundation semantics into canonical Source Truth.

This bridge is intentionally mechanical.  It binds layer-three normalized
facts to the repository's stable source units and then delegates Source Truth
record construction to :func:`cyberppt.stage01_compiler.compile_source_truth`.
It does not plan pages, rewrite facts, or create a second semantic authority.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from cyberppt.semantic_understanding import SEMANTIC_ARGUMENT_MODEL
from cyberppt.source_argument_model import SCHEMA as ARGUMENT_MODEL_SCHEMA
from cyberppt.source_document_map import (
    SOURCE_HEADING_TREE,
    load_source_units,
)
from cyberppt.stage01_compiler import SOURCE_TRUTH, compile_source_truth


_ROLE_MAP = {
    "background": "foundation",
    "context": "foundation",
    "goal": "positioning",
    "mechanism": "architecture",
    "approach": "capability",
    "constraint": "boundary",
    "implementation": "implementation",
    "evidence": "evidence",
    "other": "evidence",
}

_DUTY_MAP = {
    "metadata": "metadata",
    "problem": "gap",
    "constraint": "boundary",
    "condition": "boundary",
    "goal": "response",
    "process": "driver",
    "responsibility": "support",
    "platform": "support",
    "service": "support",
    "capability": "support",
    "dataset": "support",
    "scenario": "support",
    "technology": "support",
    "metric": "support",
}

_EVIDENCE_ROLE_MAP = {
    "problem": "problem",
    "constraint": "boundary",
    "condition": "boundary",
    "requirement": "boundary",
}

_RECOMMENDATION_MARKER_RE = re.compile(
    r"(?:^|[：。；])\s*(?:建议|应当|应|坚持|优先)"
)
_PLANNED_ACTION_MARKER_RE = re.compile(
    r"(?:^|[：。；])\s*(?:制定|完善|建立|完成|推动|形成|实现|开展|加快)"
)
_FUTURE_ACTION_MARKER_RE = re.compile(
    r"(?:^|[：。；])\s*(?:后续|下一步|未来)|将(?:在|由|继续|持续)?"
)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at {path}: {exc.msg}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path


def _text(value: object) -> str:
    return str(value or "").strip()


def _items(value: object) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _strings(value: object) -> list[str]:
    return [_text(item) for item in value if _text(item)] if isinstance(value, list) else []


def _normalized_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", _text(value))
    return re.sub(r"\s+", "", text)


def _normalized_binding_text(value: object) -> str:
    """Normalize converter-only Markdown emphasis before source binding."""

    return _normalized_text(value).replace("**", "")


def _discover_dirs(
    project: Path,
    foundation_dir: Path | None,
    semantic_dir: Path | None,
) -> tuple[Path, Path]:
    if foundation_dir is not None or semantic_dir is not None:
        if foundation_dir is None or semantic_dir is None:
            raise ValueError("--foundation-dir and --semantic-dir must be supplied together")
        return foundation_dir.expanduser().resolve(), semantic_dir.expanduser().resolve()

    manifest_path = project / "workbench/source-foundation/manifest.json"
    manifest = _read_json(manifest_path)
    candidates = [
        item
        for item in _items(manifest.get("items"))
        if item.get("status") == "ok" and item.get("foundation") and item.get("semantic")
    ]
    if len(candidates) != 1:
        raise ValueError(
            "source-foundation projection requires exactly one successful manifest item; "
            f"found {len(candidates)}"
        )
    item = candidates[0]
    return Path(str(item["foundation"])).expanduser().resolve(), Path(str(item["semantic"])).expanduser().resolve()


def _block_row_texts(block: dict[str, Any]) -> list[str]:
    """Return one comparable text per addressable row inside ``block``.

    A `paragraph`-type block (or any block without a `rows` breakdown) is a
    single addressable row: its own text. A `table`-type block bundles every
    data row of one Markdown table (plus its synthetic empty header and
    divider lines) into one block, while fact-base.json's table facts and the
    docx-native stable source map both address each row individually. `rows`/
    `raw_rows` (written by source_structure_factbase's table parser) already
    enumerate exactly those addressable rows in document order, so reuse them
    instead of re-deriving row boundaries here.
    """

    rows = block.get("rows")
    if isinstance(rows, list) and rows:
        # `rows` holds each row already split into per-cell strings (no `|`
        # table syntax); join with the same " | " separator the docx-native
        # stable source map uses for its `table_row` unit text, so the two
        # can be compared directly. `raw_rows` keeps the literal Markdown
        # line (with its outer `|` and cell-separator syntax) and is not
        # comparable to unit text without re-parsing it.
        return [" | ".join(str(cell) for cell in row) for row in rows if isinstance(row, list)]
    return [str(block.get("text", ""))]


def _block_row_lines(block: dict[str, Any], row_count: int) -> list[int]:
    line_start = int(block.get("line_start") or 0)
    if block.get("type") == "table" and isinstance(block.get("rows"), list) and block.get("rows"):
        # Matches source_structure_factbase.factbase's row_line formula
        # (line_start + 2 to skip the block's own empty-header and divider
        # lines), so fact evidence's `line_start` lines up with these keys,
        # regardless of how many rows the table has.
        return [line_start + 2 + row_index for row_index in range(row_count)]
    return [line_start]


def _matches_explicit_table_header(block: dict[str, Any], unit: dict[str, Any]) -> bool:
    """Return whether ``unit`` is the table header stored as block metadata.

    The structure parser removes an explicit Markdown table header from
    ``rows`` and records it in ``headers``. The stable DOCX source map keeps
    that same physical row as a ``table_row`` source unit. Skip it only when
    all structural and textual signals agree, so a real data row can never be
    discarded merely because it happens to be first in a table.
    """

    headers = block.get("headers")
    locator = unit.get("locator") if isinstance(unit.get("locator"), dict) else {}
    if (
        block.get("type") != "table"
        or block.get("header_status") != "explicit"
        or not isinstance(headers, list)
        or not headers
        or _text(unit.get("kind")) != "table_row"
        or int(locator.get("table_row") or 0) != 1
    ):
        return False
    header_text = " | ".join(str(cell) for cell in headers)
    return _normalized_binding_text(header_text) == _normalized_binding_text(unit.get("text"))


def _block_to_source_unit(project: Path, structure: dict[str, Any]) -> dict[tuple[str, int], str]:
    blocks = _items(structure.get("blocks"))
    # In the normal case (structure.json actually detected Markdown `#`
    # headings), heading text becomes an outline node rather than a block, so
    # the docx-native heading-kind units it corresponds to must be excluded
    # here too. But when a source used Word "Heading" styles or whole-
    # paragraph bold emphasis for its section titles instead of `#`
    # (`pseudo_headings_used`), the parser recovers an outline without
    # removing those paragraphs from `blocks` (removing them now would
    # invalidate every fact-base entry and semantic-authoring artifact
    # already keyed to today's block IDs) — so their docx-native heading-kind
    # units DO have a corresponding block and must stay in the pool, or
    # block/unit counts permanently disagree for the whole document.
    exclude_heading_units = not bool(structure.get("document", {}).get("pseudo_headings_used"))
    units = iter(
        sorted(
            (
                item
                for item in load_source_units(project)
                if not (exclude_heading_units and _text(item.get("kind")) == "heading")
            ),
            key=lambda item: int(item.get("source_order") or 0),
        )
    )

    result: dict[tuple[str, int], str] = {}
    mismatches: list[str] = []
    consumed = 0
    pending_unit: dict[str, Any] | None = None
    for block in blocks:
        block_id = _text(block.get("block_id"))
        row_texts = _block_row_texts(block)
        row_lines = _block_row_lines(block, len(row_texts))
        if block.get("type") == "table" and block.get("header_status") == "explicit":
            try:
                candidate = pending_unit or next(units)
            except StopIteration as exc:
                raise ValueError(
                    "source-foundation blocks address more rows than the stable "
                    "non-heading source map has units"
                ) from exc
            pending_unit = None
            if _matches_explicit_table_header(block, candidate):
                consumed += 1
            else:
                pending_unit = candidate
        for line, row_text in zip(row_lines, row_texts, strict=True):
            try:
                unit = pending_unit or next(units)
            except StopIteration as exc:
                raise ValueError(
                    "source-foundation blocks address more rows than the stable "
                    "non-heading source map has units"
                ) from exc
            pending_unit = None
            consumed += 1
            unit_id = _text(unit.get("unit_id"))
            if not block_id or not unit_id:
                raise ValueError("source-foundation block and source unit IDs must be non-empty")
            if _normalized_binding_text(row_text) != _normalized_binding_text(unit.get("text")):
                mismatches.append(f"{block_id}@{line}")
                continue
            result[(block_id, line)] = unit_id
    remaining = (1 if pending_unit is not None else 0) + sum(1 for _ in units)
    if remaining:
        raise ValueError(
            "source-foundation blocks address fewer rows than the stable non-heading "
            f"source map has units: {consumed} matched, {remaining} unit(s) left over"
        )
    if mismatches:
        preview = ", ".join(mismatches[:8])
        raise ValueError(
            "source-foundation block text does not match the current stable source map; "
            f"first mismatches: {preview}"
        )
    return result


def _source_structure(project: Path) -> list[dict[str, Any]]:
    payload = _read_json(project / SOURCE_HEADING_TREE)
    headings = sorted(
        _items(payload.get("headings")),
        key=lambda item: int(item.get("source_order") or 0),
    )
    result: list[dict[str, Any]] = []
    for heading in headings:
        title = _text(heading.get("title"))
        level_number = int(heading.get("level") or 1)
        if level_number == 1 and title.startswith("附件"):
            level = "appendix"
        elif level_number == 1 and title == "结束语":
            level = "closing"
        elif level_number == 1:
            level = "chapter"
        elif level_number == 2:
            level = "section"
        else:
            level = "subsection"
        item: dict[str, Any] = {
            "id": _text(heading.get("heading_id")),
            "title": title,
            "order": int(heading.get("source_order") or 0),
            "level": level,
            "source_refs": [_text(heading.get("unit_id"))],
        }
        parent_id = _text(heading.get("parent_heading_id"))
        if parent_id:
            item["parent_id"] = parent_id
        result.append(item)
    return result


def _fact_unit_refs(
    fact: dict[str, Any],
    block_map: dict[tuple[str, int], str],
    single_row_blocks: dict[str, str],
) -> list[str]:
    refs: list[str] = []
    for evidence in _items(fact.get("evidence")):
        block_id = _text(evidence.get("block_id"))
        line_start = evidence.get("line_start")
        unit_id = block_map.get((block_id, int(line_start))) if line_start else None
        if not unit_id:
            # Evidence without a row-level `line_start` (or one that does not
            # match) can still resolve unambiguously when the block addresses
            # exactly one row.
            unit_id = single_row_blocks.get(block_id)
        if not unit_id:
            raise ValueError(
                f"normalized fact {_text(fact.get('normalized_fact_id'))} references unmapped block "
                f"{block_id}" + (f"@{line_start}" if line_start else "")
            )
        if unit_id not in refs:
            refs.append(unit_id)
    if not refs:
        raise ValueError(
            f"normalized fact {_text(fact.get('normalized_fact_id'))} has no source-bound evidence"
        )
    return refs


def _fact_section_ids(
    fact: dict[str, Any],
    blocks_by_id: dict[str, dict[str, Any]],
) -> list[str]:
    section_ids: list[str] = []
    normalized_section = _text(fact.get("section_id"))
    if normalized_section:
        section_ids.append(normalized_section)
    for evidence in _items(fact.get("evidence")):
        block_id = _text(evidence.get("block_id"))
        block = blocks_by_id.get(block_id)
        if block is None:
            raise ValueError(
                f"normalized fact {_text(fact.get('normalized_fact_id'))} references unknown block {block_id}"
            )
        section_id = _text(block.get("section_id"))
        if section_id and section_id not in section_ids:
            section_ids.append(section_id)
    return section_ids


def _fact_source_roles(argument: dict[str, Any]) -> dict[str, str]:
    """Return the source-authored argument role for each normalized fact."""

    roles: dict[str, str] = {}
    for field in ("source_chain", "reconstructed_chain"):
        for node in _items(argument.get(field)):
            role = _text(node.get("role"))
            if not role:
                continue
            for fact_id in _strings(node.get("normalized_fact_ids")):
                roles.setdefault(fact_id, role)
    return roles


def _table_group_contexts(facts: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Resolve inherited first-column table groups without rewriting facts.

    Vertically merged DOCX cells become blank Markdown cells on continuation
    rows.  The literal normalized statement remains unchanged; this metadata
    makes the row's parent category explicit for downstream planning.
    """

    rows: dict[tuple[str, int], dict[str, Any]] = {}
    facts_by_row: dict[tuple[str, int], list[str]] = {}
    for fact in facts:
        fact_id = _text(fact.get("normalized_fact_id"))
        cell = fact.get("table_cell")
        evidence = _items(fact.get("evidence"))
        if not fact_id or not isinstance(cell, dict) or not evidence:
            continue
        block_id = _text(evidence[0].get("block_id"))
        row_index = cell.get("row_index")
        if not block_id or not isinstance(row_index, int):
            continue
        key = (block_id, row_index)
        facts_by_row.setdefault(key, []).append(fact_id)
        label = _text(cell.get("row_label"))
        row = rows.setdefault(key, {"cells": {}})
        if label:
            row["explicit_label"] = label
        row["cells"][fact_id] = {
            "row_index": row_index,
            "cell_index": cell.get("cell_index"),
            "header": _text(cell.get("header")),
        }

    result: dict[str, dict[str, Any]] = {}
    current_by_block: dict[str, str] = {}
    for block_id, row_index in sorted(rows, key=lambda value: (value[0], value[1])):
        row = rows[(block_id, row_index)]
        explicit = _text(row.get("explicit_label"))
        if explicit:
            current_by_block[block_id] = explicit
        group_label = explicit or current_by_block.get(block_id, "")
        if not group_label:
            continue
        basis = (
            "explicit_first_column"
            if explicit
            else "inherited_previous_nonempty_first_column"
        )
        for fact_id in facts_by_row[(block_id, row_index)]:
            result[fact_id] = {
                **row["cells"][fact_id],
                "group_label": group_label,
                "basis": basis,
            }
    return result


def _atomic_semantic_profile(
    fact: dict[str, Any],
    *,
    source_role: str,
) -> tuple[str, str, str]:
    """Return evidence role, semantic status, and argument duty."""

    fact_type = _text(fact.get("fact_type")) or "other"
    statement = _text(fact.get("statement"))
    if fact_type == "problem" or source_role == "problem":
        return "problem", "existing", "gap"
    if fact_type in {"constraint", "condition"}:
        return "boundary", "existing", "boundary"
    if fact_type == "metadata":
        return "fact", "unknown", "metadata"

    recommendation_marker = bool(_RECOMMENDATION_MARKER_RE.search(statement))
    planned_action_marker = bool(_PLANNED_ACTION_MARKER_RE.search(statement))
    future_action_marker = bool(_FUTURE_ACTION_MARKER_RE.search(statement))
    if source_role == "approach":
        return "recommendation", "recommendation", "response"
    if source_role == "implementation":
        return "recommendation", "planned", "response"
    if source_role == "recommendation":
        return "recommendation", "recommendation", "response"
    if source_role == "goal":
        return "fact", "planned", "response"
    if source_role == "conclusion":
        if recommendation_marker:
            return "recommendation", "recommendation", "response"
        if planned_action_marker or future_action_marker:
            return "recommendation", "planned", "response"
        return "fact", "existing", "response"
    if source_role == "requirement":
        if recommendation_marker:
            return "recommendation", "recommendation", "response"
        if planned_action_marker:
            return "recommendation", "planned", "response"
        return "boundary", "existing", "boundary"
    if fact_type == "requirement":
        if recommendation_marker:
            return "recommendation", "recommendation", "response"
        if planned_action_marker or future_action_marker:
            return "recommendation", "planned", "response"
        return "boundary", "existing", "boundary"
    if fact_type == "responsibility" and recommendation_marker:
        return "recommendation", "recommendation", "response"
    return (
        _EVIDENCE_ROLE_MAP.get(fact_type, "fact"),
        "existing",
        _DUTY_MAP.get(fact_type, "detail"),
    )


def _node_statement(item: dict[str, Any], fact_by_id: dict[str, dict[str, Any]]) -> str:
    statement = _text(item.get("statement"))
    if statement:
        return statement
    # The semantic-contract does not require argument-chain nodes to carry
    # their own `statement` (only normalized facts must have one); when a
    # node omits it, its first cited normalized fact's statement stands in
    # as the node's thesis instead of leaving it — and the deck's overall
    # thesis derived from it — empty.
    for fact_id in _strings(item.get("normalized_fact_ids")):
        fact = fact_by_id.get(fact_id)
        if fact is not None:
            statement = _text(fact.get("statement"))
            if statement:
                return statement
    return ""


def _node(
    item: dict[str, Any],
    *,
    node_id: str,
    source_heading: str,
    evidence_refs: list[str],
    weight: str,
    statement: str,
) -> dict[str, Any]:
    return {
        "id": node_id,
        "source_heading": source_heading or node_id,
        "section_thesis": statement,
        "argument_role": _ROLE_MAP.get(_text(item.get("role")), "evidence"),
        "argument_weight": weight,
        "status": "mixed",
        "evidence_refs": evidence_refs,
        "claim_origin": "source_implied",
        "projection_only": True,
    }


def build_projection_model(
    project: Path,
    foundation_dir: Path,
    semantic_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    structure = _read_json(foundation_dir / "structure.json")
    normalized = _read_json(semantic_dir / "normalized-facts.json")
    concepts = _read_json(semantic_dir / "concept-base.json")
    relations = _read_json(semantic_dir / "relation-graph.json")
    argument = _read_json(semantic_dir / "argument-chain.json")
    report = _read_json(semantic_dir / "semantic-report.json")
    if report.get("status") != "ok":
        raise ValueError("semantic-report.json must report status: ok before projection")

    facts = _items(normalized.get("facts"))
    fact_by_id = {
        _text(item.get("normalized_fact_id")): item
        for item in facts
        if _text(item.get("normalized_fact_id"))
    }
    block_map = _block_to_source_unit(project, structure)
    single_row_blocks: dict[str, str] = {}
    ambiguous_blocks: set[str] = set()
    for (block_id, _line), unit_id in block_map.items():
        if block_id in single_row_blocks:
            ambiguous_blocks.add(block_id)
        else:
            single_row_blocks[block_id] = unit_id
    for block_id in ambiguous_blocks:
        del single_row_blocks[block_id]
    refs_by_fact = {
        fact_id: _fact_unit_refs(fact, block_map, single_row_blocks)
        for fact_id, fact in fact_by_id.items()
    }
    blocks_by_id = {
        _text(item.get("block_id")): item
        for item in _items(structure.get("blocks"))
        if _text(item.get("block_id"))
    }
    sections_by_fact = {
        fact_id: _fact_section_ids(fact, blocks_by_id)
        for fact_id, fact in fact_by_id.items()
    }

    reconstructed = _items(argument.get("reconstructed_chain"))
    source_chain = _items(argument.get("source_chain"))
    source_roles = _fact_source_roles(argument)
    table_contexts = _table_group_contexts(facts)
    section_title = {
        _text(item.get("section_id")): _text(item.get("title"))
        for item in _items(_read_json(semantic_dir / "semantic-workpack.json").get("sections"))
    }
    fact_nodes: dict[str, list[str]] = {}
    source_node_by_section: dict[str, str] = {}
    section_nodes: list[dict[str, Any]] = []
    for index, item in enumerate(reconstructed, start=1):
        node_id = _text(item.get("node_id")) or f"RC-{index:03d}"
        fact_ids = [fact_id for fact_id in _strings(item.get("normalized_fact_ids")) if fact_id in fact_by_id]
        evidence_refs = list(dict.fromkeys(ref for fact_id in fact_ids for ref in refs_by_fact[fact_id]))
        first_section = next(iter(_strings(item.get("section_ids"))), "")
        section_nodes.append(
            _node(
                item,
                node_id=node_id,
                source_heading=section_title.get(first_section, first_section),
                evidence_refs=evidence_refs,
                weight="core" if index == 1 else "supporting",
                statement=_node_statement(item, fact_by_id),
            )
        )
        for fact_id in fact_ids:
            fact_nodes.setdefault(fact_id, []).append(node_id)

    subsection_nodes: list[dict[str, Any]] = []
    for index, item in enumerate(source_chain, start=1):
        node_id = _text(item.get("node_id")) or f"SC-{index:03d}"
        for section_id in _strings(item.get("section_ids")):
            # The semantic-understanding contract lets one section's argument
            # be reconstructed as several source_chain nodes (one per
            # argument beat) rather than a single section-level summary; a
            # section legitimately maps to more than one node here. Only the
            # *first* node registered for a section is kept as its fallback
            # representative below (for facts no chain node explicitly
            # cites) — first-in-document-order is as good a default owner as
            # any for a fact the author didn't place in the argument flow.
            source_node_by_section.setdefault(section_id, node_id)
        fact_ids = [fact_id for fact_id in _strings(item.get("normalized_fact_ids")) if fact_id in fact_by_id]
        evidence_refs = list(dict.fromkeys(ref for fact_id in fact_ids for ref in refs_by_fact[fact_id]))
        first_section = next(iter(_strings(item.get("section_ids"))), "")
        node = _node(
            item,
            node_id=node_id,
            source_heading=section_title.get(first_section, first_section),
            evidence_refs=evidence_refs,
            weight="supporting",
            statement=_node_statement(item, fact_by_id),
        )
        node["parent_id"] = next(
            (
                _text(parent.get("node_id"))
                for parent in reconstructed
                if set(_strings(parent.get("section_ids"))) & set(_strings(item.get("section_ids")))
            ),
            "document",
        )
        subsection_nodes.append(node)
        for fact_id in fact_ids:
            fact_nodes.setdefault(fact_id, []).insert(0, node_id)

    metadata_ids = [
        fact_id
        for fact_id, fact in fact_by_id.items()
        if _text(fact.get("fact_type")) == "metadata"
    ]
    if metadata_ids:
        metadata_refs = list(dict.fromkeys(ref for fact_id in metadata_ids for ref in refs_by_fact[fact_id]))
        section_nodes.append(
            {
                "id": "META-001",
                "source_heading": "题名与目录元数据",
                "section_thesis": "题名、落款、日期和目录条目保留在来源追溯层。",
                "argument_role": "evidence",
                "argument_weight": "detail",
                "status": "existing",
                "evidence_refs": metadata_refs,
                "claim_origin": "source_explicit",
                "projection_only": True,
            }
        )
        for fact_id in metadata_ids:
            fact_nodes.setdefault(fact_id, []).append("META-001")

    if not section_nodes:
        raise ValueError("argument-chain.json has no reconstructed nodes to project")

    core_fact_ids = {
        next((fact_id for fact_id in _strings(item.get("normalized_fact_ids")) if fact_id in fact_by_id), "")
        for item in reconstructed
    }
    core_fact_ids.discard("")
    assignments: list[dict[str, Any]] = []
    for fact_id, fact in fact_by_id.items():
        fact_type = _text(fact.get("fact_type")) or "other"
        source_role = source_roles.get(fact_id, "")
        evidence_role, semantic_status, argument_duty = _atomic_semantic_profile(
            fact,
            source_role=source_role,
        )
        semantic_node_ids = list(fact_nodes.get(fact_id, []))
        if not semantic_node_ids:
            section_ids = sections_by_fact[fact_id]
            is_metadata = fact_type == "metadata" or section_ids == ["preamble"]
            if is_metadata:
                if "META-001" not in {item["id"] for item in section_nodes}:
                    raise ValueError(f"metadata fact {fact_id} has no META-001 projection node")
                semantic_node_ids = ["META-001"]
            else:
                semantic_node_ids = list(
                    dict.fromkeys(
                        source_node_by_section[section_id]
                        for section_id in section_ids
                        if section_id in source_node_by_section
                    )
                )
                if not semantic_node_ids:
                    joined = ", ".join(section_ids) or "<none>"
                    raise ValueError(
                        f"substantive normalized fact {fact_id} has no source-chain node "
                        f"for section(s): {joined}"
                    )
        if fact_id in core_fact_ids:
            importance = "core"
        elif fact_type in {"constraint", "condition", "requirement"}:
            importance = "constraint"
        else:
            importance = "detail"
        assignments.append(
            {
                "semantic_node_ids": semantic_node_ids,
                "atomic_items": [
                    {
                        "item_id": fact_id,
                        "statement": _text(fact.get("statement")),
                        "source_unit_refs": refs_by_fact[fact_id],
                        "status": semantic_status,
                        "evidence_role": evidence_role,
                        "importance": importance,
                        "argument_duty": argument_duty,
                        "normalized_fact_type": fact_type,
                        "normalized_semantic_role": _text(fact.get("semantic_role")),
                        "source_argument_role": source_role,
                        "table_context": table_contexts.get(fact_id),
                        "claim_origin": (
                            "source_explicit"
                            if _text(fact.get("normalization")) == "verbatim"
                            else "source_implied"
                        ),
                        "coverage_anchors": [_text(fact.get("statement"))[:48]],
                    }
                ],
            }
        )

    # The first reconstructed-chain node is the one node already treated as
    # "core" above (`weight="core" if index == 1`); use its statement (or its
    # cited fact's, via the same fallback as `_node_statement`) as the
    # document's primary thesis. Joining every node's statement instead would
    # produce an unusably long "thesis" once a document's argument chain is
    # authored at fine (multi-node-per-section) granularity.
    thesis = next(
        (candidate for item in reconstructed[:1] if (candidate := _node_statement(item, fact_by_id))),
        "",
    )
    thesis_refs = list(dict.fromkeys(ref for fact_id in core_fact_ids for ref in refs_by_fact[fact_id]))
    source = structure.get("source") if isinstance(structure.get("source"), dict) else {}
    source_file = _text(source.get("source_file")) or _text(structure.get("input_markdown"))
    subject = Path(source_file).stem if source_file else project.name
    business_objects = [
        _text(item.get("canonical_name"))
        for item in _items(concepts.get("concepts"))
        if _text(item.get("canonical_name"))
    ]
    model = {
        "schema": ARGUMENT_MODEL_SCHEMA,
        "version": 1,
        "interpretation_contract_mode": "projection",
        "authority_mode": "projection_only",
        "document_semantics": {
            "document_role": "合作交流材料" if "合作交流" in subject else "正式材料",
            "subject_of_report": subject,
            "primary_thesis": thesis,
            "decision_boundary": "内容范围、事实强度、主体责任、条件和状态均继承已验证 Source Foundation 产物。",
            "author_purpose": "",
            "argument_method": [
                _text(item.get("statement")) for item in reconstructed if _text(item.get("statement"))
            ],
            "supporting_basis": business_objects,
            "business_objects": business_objects,
            "scope": "；".join(
                item["title"] for item in _source_structure(project) if item["level"] == "chapter"
            ),
            "decision_intent": "为后续交流目标和脚本规划提供源材料事实与论证基础。",
        },
        "document_thesis": {
            "statement": thesis,
            "argument_role": "thesis",
            "argument_weight": "core",
            "status": "mixed",
            "evidence_refs": thesis_refs,
            "actor_refs": [],
            "claim_origin": "source_implied",
            "projection_only": True,
        },
        "section_nodes": section_nodes,
        "subsection_nodes": subsection_nodes,
        "argument_relations": [],
        "source_coverage": {
            "assignments": assignments,
            "intentional_omissions": [],
            "review_notes": [
                "由已验证 normalized-facts.json 机械投影；未新增、合并或改写事实。"
            ],
        },
        "source_gaps": _items(argument.get("diagnostics")),
    }
    return model, concepts, relations


def _enrich_source_truth(
    project: Path,
    truth_path: Path,
    concepts: dict[str, Any],
    relations: dict[str, Any],
    normalized: dict[str, Any],
) -> Path:
    truth = _read_json(truth_path)
    record_by_fact = {
        _text(item.get("atomic_item_id")): item
        for item in _items(truth.get("records"))
        if _text(item.get("atomic_item_id"))
    }
    projected_concepts: list[dict[str, Any]] = []
    for item in _items(concepts.get("concepts")):
        fact_ids = _strings(item.get("normalized_fact_ids"))
        record_refs = [record_by_fact[fact_id]["id"] for fact_id in fact_ids if fact_id in record_by_fact]
        projected_concepts.append(
            {
                "id": _text(item.get("concept_id")),
                "term": _text(item.get("canonical_name")),
                "definition": _text(item.get("definition")),
                "source_refs": record_refs,
                "visibility": "external_ok",
            }
        )
    # relation-graph.json (business-semantic-understanding) uses a three-way
    # basis: source / inferred / external. Downstream Source Truth consumers
    # (e.g. cyberppt/page_logic_contract.py's _VALID_BASES) only know the
    # original two-way explicit/inferred distinction; map at the projection
    # boundary rather than propagating a third value they cannot validate.
    # `external` (depends on domain knowledge or a web check, not the source
    # itself) is not source-stated, so it maps to `inferred` for downstream
    # evidence-strength purposes.
    _RELATION_BASIS_PROJECTION = {"source": "explicit", "inferred": "inferred", "external": "inferred"}
    projected_relations: list[dict[str, Any]] = []
    for item in _items(relations.get("relations")):
        fact_ids = _strings(item.get("normalized_fact_ids"))
        support = [record_by_fact[fact_id]["id"] for fact_id in fact_ids if fact_id in record_by_fact]
        projected_relations.append(
            {
                "id": _text(item.get("relation_id")),
                "from": _text(item.get("from_concept_id")),
                "to": _text(item.get("to_concept_id")),
                "relation": _text(item.get("relation_type")) or "associated_with",
                "basis": _RELATION_BASIS_PROJECTION.get(_text(item.get("basis")), "explicit"),
                "confidence": _text(item.get("confidence")) or "medium",
                "support": support,
                "source_refs": list(
                    dict.fromkeys(
                        ref
                        for record_id in support
                        for ref in _strings(
                            next(
                                (
                                    record.get("source_unit_refs")
                                    for record in _items(truth.get("records"))
                                    if _text(record.get("id")) == record_id
                                ),
                                [],
                            )
                        )
                    )
                ),
            }
        )
    issues = _items(normalized.get("conflicts")) + _items(normalized.get("ambiguities"))
    truth["source_structure"] = _source_structure(project)
    truth["semantic_concepts"] = projected_concepts
    truth["semantic_relations"] = projected_relations
    truth["open_questions"] = [
        _text(item.get("statement") or item.get("description"))
        for item in issues
        if _text(item.get("statement") or item.get("description"))
    ]
    return _write_json(truth_path, truth)


def project_source_foundation_truth(
    project: Path,
    *,
    foundation_dir: Path | None = None,
    semantic_dir: Path | None = None,
    model_output: Path | None = None,
    truth_output: Path | None = None,
) -> tuple[Path, Path]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    foundation, semantic = _discover_dirs(project, foundation_dir, semantic_dir)
    model, concepts, relations = build_projection_model(project, foundation, semantic)
    model_path = (
        model_output.expanduser().resolve()
        if model_output is not None
        else project / SEMANTIC_ARGUMENT_MODEL
    )
    _write_json(model_path, model)
    truth_path = compile_source_truth(project, truth_output)
    normalized = _read_json(semantic / "normalized-facts.json")
    _enrich_source_truth(project, truth_path, concepts, relations, normalized)
    return model_path, truth_path

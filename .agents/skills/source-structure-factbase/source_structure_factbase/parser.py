from __future__ import annotations

import hashlib
from pathlib import Path
import re
from typing import Any

from .frontmatter import parse_front_matter


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})(.*)$")
_LIST_RE = re.compile(r"^(\s*)([-+*]|\d+[.)])\s+(.*)$")
_DIVIDER_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$")
_TABLE_DIVIDER_CELL_RE = re.compile(r"^:?-{3,}:?$")

# A whole-paragraph bold run, e.g. "**一、从紫金云专业能力出发……**" or
# "**核心结论**". Anchored end-to-end (with DOTALL so a title wrapping two
# physical lines still matches as one run) so a paragraph that merely
# *contains* bold emphasis inside a longer sentence never qualifies.
_PSEUDO_HEADING_RE = re.compile(r"^\*\*(.+)\*\*$", re.DOTALL)
_CJK_NUMERAL = "一二三四五六七八九十百千〇零"
_PSEUDO_HEADING_LEVEL1_RE = re.compile(rf"^[{_CJK_NUMERAL}]+、")
_PSEUDO_HEADING_LEVEL2_RE = re.compile(rf"^[（(][{_CJK_NUMERAL}0-9]+[）)]")
_PSEUDO_HEADING_LEVEL3_RE = re.compile(r"^\d+[.、]")
# Chinese business docs rarely run a genuine section title past this length;
# a longer fully-bold paragraph is far more likely emphasised body prose
# (a caveat, a pull-quote) than a heading, so it is left alone.
_PSEUDO_HEADING_MAX_CHARS = 40


def _warning(code: str, message: str, **extra: Any) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "severity": "warning", "message": message}
    item.update(extra)
    return item


def _heading_title(raw: str) -> str:
    title = raw.strip()
    title = re.sub(r"\s+#+\s*$", "", title)
    return title.strip()


def _split_table_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith("\\|"):
        stripped = stripped[:-1]
    parts = re.split(r"(?<!\\)\|", stripped)
    return [part.strip().replace("\\|", "|") for part in parts]


def _is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines) or "|" not in lines[index]:
        return False
    header = _split_table_row(lines[index])
    divider = _split_table_row(lines[index + 1])
    if not header or len(header) != len(divider):
        return False
    return all(_TABLE_DIVIDER_CELL_RE.match(cell) for cell in divider)


def _is_special_start(lines: list[str], index: int) -> bool:
    line = lines[index]
    if not line.strip():
        return True
    if _HEADING_RE.match(line) or _FENCE_RE.match(line) or _DIVIDER_RE.match(line):
        return True
    if _LIST_RE.match(line) or re.match(r"^\s{0,3}>", line):
        return True
    return _is_table_start(lines, index)


def _outline_node(section_id: str, level: int, title: str, line: int) -> dict[str, Any]:
    return {
        "section_id": section_id,
        "level": level,
        "title": title,
        "line": line,
        "children": [],
    }


def _pseudo_heading_title(block: dict[str, Any]) -> str | None:
    match = _PSEUDO_HEADING_RE.match(str(block.get("text", "")).strip())
    if not match:
        return None
    title = re.sub(r"\s+", "", match.group(1))
    if not title or len(title) > _PSEUDO_HEADING_MAX_CHARS:
        return None
    return title


def _pseudo_heading_level(title: str, has_open_level1: bool) -> int:
    if _PSEUDO_HEADING_LEVEL1_RE.match(title):
        return 1
    if _PSEUDO_HEADING_LEVEL2_RE.match(title) or _PSEUDO_HEADING_LEVEL3_RE.match(title):
        return 2
    # An unnumbered bold label (e.g. "核心结论", "数据与来源说明") is a peer of
    # the numbered chapters when none is open yet, otherwise a sub-label
    # nested inside whichever chapter is currently open.
    return 1 if not has_open_level1 else 2


def infer_pseudo_headings(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recover an outline from whole-paragraph bold pseudo-headings.

    Only meaningful when the document used Word "Heading" styles or bold
    emphasis for its section titles instead of Markdown `#` headings, so no
    real heading was found by the main parse. Those paragraphs already exist
    as ordinary ``blocks`` (added before this runs) and must stay that way —
    changing that would invalidate every downstream artifact (fact-base
    entries, semantic authoring) already keyed to today's block IDs. This
    only adds outline nodes and fills in ``section_id``/``heading_path`` on
    every block, mutating ``blocks`` in place.
    """

    outline: list[dict[str, Any]] = []
    section_stack: list[dict[str, Any]] = []
    pseudo_heading_count = 0

    for block in blocks:
        title: str | None = None
        if block.get("type") == "paragraph":
            title = _pseudo_heading_title(block)
        if title is not None:
            pseudo_heading_count += 1
            level = _pseudo_heading_level(title, has_open_level1=any(n["level"] == 1 for n in section_stack))
            while section_stack and section_stack[-1]["level"] >= level:
                section_stack.pop()
            node = _outline_node(f"psec-{pseudo_heading_count:04d}", level, title, int(block.get("line_start") or 0))
            if section_stack:
                section_stack[-1]["children"].append(node)
            else:
                outline.append(node)
            section_stack.append(node)
        block["section_id"] = section_stack[-1]["section_id"] if section_stack else None
        block["heading_path"] = [n["title"] for n in section_stack]

    return outline


def parse_document(markdown: str, source_name: str) -> dict[str, Any]:
    front = parse_front_matter(markdown, fallback_name=source_name)
    body_lines = front.body.splitlines()
    warnings: list[dict[str, Any]] = [dict(item) for item in front.warnings]
    if not front.body.strip():
        warnings.append(_warning("empty_body", "Markdown source body is empty."))

    outline: list[dict[str, Any]] = []
    section_stack: list[dict[str, Any]] = []
    blocks: list[dict[str, Any]] = []
    heading_count = 0
    previous_heading_level: int | None = None
    first_heading: str | None = None
    first_h1: str | None = None

    def current_heading_path() -> list[str]:
        return [node["title"] for node in section_stack]

    def current_section_id() -> str | None:
        return section_stack[-1]["section_id"] if section_stack else None

    def add_block(block_type: str, text: str, start_idx: int, end_idx: int, **extra: Any) -> None:
        block: dict[str, Any] = {
            "block_id": f"blk-{len(blocks) + 1:04d}",
            "type": block_type,
            "text": text,
            "line_start": front.body_start_line + start_idx,
            "line_end": front.body_start_line + end_idx,
            "section_id": current_section_id(),
            "heading_path": current_heading_path(),
        }
        block.update(extra)
        blocks.append(block)

    i = 0
    while i < len(body_lines):
        line = body_lines[i]
        if not line.strip():
            i += 1
            continue

        heading_match = _HEADING_RE.match(line)
        if heading_match:
            level = len(heading_match.group(1))
            title = _heading_title(heading_match.group(2))
            heading_count += 1
            absolute_line = front.body_start_line + i
            if first_heading is None:
                first_heading = title
            if level == 1 and first_h1 is None:
                first_h1 = title
            if previous_heading_level is not None and level > previous_heading_level + 1:
                warnings.append(_warning(
                    "heading_level_jump",
                    f"Heading level jumps from {previous_heading_level} to {level}; source structure was preserved without repair.",
                    line=absolute_line,
                    from_level=previous_heading_level,
                    to_level=level,
                ))
            previous_heading_level = level
            while section_stack and section_stack[-1]["level"] >= level:
                section_stack.pop()
            node = _outline_node(f"sec-{heading_count:04d}", level, title, absolute_line)
            if section_stack:
                section_stack[-1]["children"].append(node)
            else:
                outline.append(node)
            section_stack.append(node)
            i += 1
            continue

        fence_match = _FENCE_RE.match(line)
        if fence_match:
            start = i
            marker = fence_match.group(1)
            marker_char = marker[0]
            marker_len = len(marker)
            i += 1
            closed = False
            while i < len(body_lines):
                candidate = body_lines[i].lstrip()
                if re.match(rf"^{re.escape(marker_char)}{{{marker_len},}}\s*$", candidate):
                    closed = True
                    i += 1
                    break
                i += 1
            end = i - 1 if i > start else start
            text = "\n".join(body_lines[start : end + 1])
            if not closed:
                warnings.append(_warning(
                    "unclosed_fence",
                    "Fenced code/text block has no closing fence; remaining content was preserved in the fence block.",
                    line=front.body_start_line + start,
                ))
            add_block("code_fence", text, start, end, closed=closed)
            continue

        if _is_table_start(body_lines, i):
            start = i
            headers = _split_table_row(body_lines[i])
            i += 2  # header + delimiter
            rows: list[list[str]] = []
            raw_rows: list[str] = []
            while i < len(body_lines) and body_lines[i].strip() and "|" in body_lines[i]:
                raw_rows.append(body_lines[i])
                rows.append(_split_table_row(body_lines[i]))
                i += 1
            end = i - 1
            raw_text = "\n".join(body_lines[start : end + 1])
            header_status = "explicit" if any(cell.strip() for cell in headers) else "empty"
            candidate_header = None
            if header_status == "empty" and rows:
                candidate_header = {
                    "status": "unconfirmed",
                    "row_index": 1,
                    "line_start": front.body_start_line + start + 2,
                    "line_end": front.body_start_line + start + 2,
                    "cells": list(rows[0]),
                    "reason": "first_body_row_after_empty_markdown_header",
                }
            add_block(
                "table",
                raw_text,
                start,
                end,
                headers=headers,
                header_status=header_status,
                candidate_header=candidate_header,
                rows=rows,
                raw_rows=raw_rows,
            )
            continue

        list_match = _LIST_RE.match(line)
        if list_match:
            marker = list_match.group(2)
            add_block(
                "list_item",
                list_match.group(3),
                i,
                i,
                raw=line,
                list_kind="ordered" if marker[0].isdigit() else "bullet",
                list_marker=marker,
                list_level=max(0, len(list_match.group(1).replace("\t", "    ")) // 2),
            )
            i += 1
            continue

        if re.match(r"^\s{0,3}>", line):
            start = i
            while i < len(body_lines) and re.match(r"^\s{0,3}>", body_lines[i]):
                i += 1
            end = i - 1
            add_block("blockquote", "\n".join(body_lines[start : end + 1]), start, end)
            continue

        if _DIVIDER_RE.match(line):
            add_block("divider", line, i, i)
            i += 1
            continue

        start = i
        i += 1
        while i < len(body_lines) and not _is_special_start(body_lines, i):
            i += 1
        end = i - 1
        add_block("paragraph", "\n".join(body_lines[start : end + 1]), start, end)

    if heading_count == 0 and len(front.body.strip()) >= 500:
        warnings.append(_warning(
            "no_headings",
            "Substantial Markdown source has no headings; downstream structure should be reviewed.",
        ))

    pseudo_headings_used = False
    if heading_count == 0 and blocks:
        pseudo_outline = infer_pseudo_headings(blocks)
        if pseudo_outline:
            # The source used Word "Heading" styles or whole-paragraph bold
            # emphasis for its section titles instead of Markdown `#`
            # headings. Recover a real chapter/section outline from those
            # paragraphs (which already exist as ordinary blocks and stay
            # that way) instead of leaving every block section-less.
            outline.extend(pseudo_outline)
            pseudo_headings_used = True
        else:
            # No bold-pseudo-heading pattern was found either: downstream
            # layers (business-semantic-understanding's prepare.py) still
            # bucket every section-less block/fact under a synthetic
            # "preamble" section. Without a matching outline node here,
            # validate.py's section_ids check (sourced only from `outline`)
            # can never recognize "preamble", making argument-chain
            # validation unwinnable for any zero-heading document. Register
            # the same synthetic section so the two layers agree.
            outline.append(_outline_node("preamble", 0, "Preamble", 0))

    title = first_h1 or first_heading or Path(str(front.metadata.get("source_file") or source_name)).stem
    return {
        "schema_version": "1.0",
        "artifact_type": "document_structure",
        "input_markdown": source_name,
        "markdown_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "source": front.metadata,
        "document": {
            "title": title,
            "heading_count": heading_count,
            "block_count": len(blocks),
            "pseudo_headings_used": pseudo_headings_used,
        },
        "outline": outline,
        "blocks": blocks,
        "warnings": warnings,
    }

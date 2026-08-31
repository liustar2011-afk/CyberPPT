"""Legacy Word source-extract parsing and v1 source-index construction."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .text_io import write_text_lf


PARAGRAPH_RE = re.compile(r"^\[/body/p\[(?P<key>[^\]]+)\]\]\s*(?P<text>.*)$")
CHAPTER_RE = re.compile(r"^第([一二三四五六七八九十百零〇两]+)章[　\s]*(.*)$")
SECTION_RE = re.compile(r"^([一二三四五六七八九十]+)、\s*(.+)$")
SUBSECTION_RE = re.compile(r"^（([一二三四五六七八九十]+)）\s*(.+)$")
APPENDIX_RE = re.compile(r"^附件([一二三四五六七八九十]+)[　\s]*(.*)$")
TOC_ENTRY_RE = re.compile(r"\t+\d+\s*$")
DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def chinese_number(text: str) -> int:
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = DIGITS.get(left, 1) if left else 1
        ones = DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    value = 0
    for char in text:
        if char == "百":
            value = max(value, 1) * 100
        else:
            value = value * 10 + DIGITS.get(char, 0)
    return value


def _ensure(
    refs: dict[str, dict[str, Any]],
    ref: str,
    title: str,
    source_file: str | None,
) -> dict[str, Any]:
    return refs.setdefault(
        ref,
        {
            "ref": ref,
            "title": title,
            "source_file": source_file,
            "paragraph_keys": [],
            "line_numbers": [],
        },
    )


def _is_toc_entry(text: str) -> bool:
    """Return True for Word TOC rows that end in a tab-separated page number."""

    return bool(TOC_ENTRY_RE.search(text))


def build_source_index(text: str, source_file: str | None = None) -> dict[str, Any]:
    refs: dict[str, dict[str, Any]] = {}
    structure: list[dict[str, Any]] = []
    chapter_no = 1
    section_no = 0
    current_ref = "S1.0"
    current_title = "Front matter"
    order = 0
    _ensure(refs, current_ref, current_title, source_file)

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        match = PARAGRAPH_RE.match(raw_line.strip())
        if not match:
            continue
        key = match.group("key")
        para = match.group("text").strip()
        if not para:
            continue
        if _is_toc_entry(para):
            continue

        chapter = CHAPTER_RE.match(para)
        section = SECTION_RE.match(para)
        subsection = SUBSECTION_RE.match(para)
        appendix = APPENDIX_RE.match(para)

        if chapter:
            chapter_no = chinese_number(chapter.group(1))
            section_no = 0
            current_ref = f"S{chapter_no}.0"
            current_title = para
            order += 1
            structure.append(
                {
                    "id": f"CH{chapter_no:02d}",
                    "title": para,
                    "order": order,
                    "level": "chapter",
                    "source_refs": [current_ref],
                }
            )
            _ensure(refs, current_ref, current_title, source_file)
        elif appendix:
            current_ref = f"附件{appendix.group(1)}"
            current_title = para
            order += 1
            structure.append(
                {
                    "id": current_ref,
                    "title": para,
                    "order": order,
                    "level": "appendix",
                    "source_refs": [current_ref],
                }
            )
            _ensure(refs, current_ref, current_title, source_file)
        elif para == "结束语":
            current_ref = "结束语"
            current_title = para
            order += 1
            structure.append(
                {
                    "id": "CLOSING",
                    "title": para,
                    "order": order,
                    "level": "closing",
                    "source_refs": [current_ref],
                }
            )
            _ensure(refs, current_ref, current_title, source_file)
        elif section and current_ref.startswith("S"):
            section_no = chinese_number(section.group(1))
            current_ref = f"S{chapter_no}.{section_no}"
            current_title = para
            order += 1
            structure.append(
                {
                    "id": f"CH{chapter_no:02d}-S{section_no:02d}",
                    "title": para,
                    "order": order,
                    "level": "section",
                    "parent_id": f"CH{chapter_no:02d}",
                    "source_refs": [current_ref],
                }
            )
            _ensure(refs, current_ref, current_title, source_file)
        elif subsection and current_ref.startswith("S") and section_no:
            sub_no = chinese_number(subsection.group(1))
            current_ref = f"S{chapter_no}.{section_no}.{sub_no}"
            current_title = para
            order += 1
            structure.append(
                {
                    "id": f"CH{chapter_no:02d}-S{section_no:02d}-SS{sub_no:02d}",
                    "title": para,
                    "order": order,
                    "level": "subsection",
                    "parent_id": f"CH{chapter_no:02d}-S{section_no:02d}",
                    "source_refs": [current_ref],
                }
            )
            _ensure(refs, current_ref, current_title, source_file)

        record = _ensure(refs, current_ref, current_title, source_file)
        record["paragraph_keys"].append(key)
        record["line_numbers"].append(line_no)

    return {
        "version": "1.0",
        "source_file": source_file,
        "refs": refs,
        "source_structure": structure,
    }


def build_source_index_file(
    source_extract: Path,
    output: Path,
    source_file: str | None = None,
) -> dict[str, Any]:
    index = build_source_index(
        source_extract.read_text(encoding="utf-8-sig"),
        source_file=source_file,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    write_text_lf(output, json.dumps(index, ensure_ascii=False, indent=2) + "\n")
    return index


__all__ = [
    "APPENDIX_RE",
    "CHAPTER_RE",
    "DIGITS",
    "PARAGRAPH_RE",
    "SECTION_RE",
    "SUBSECTION_RE",
    "TOC_ENTRY_RE",
    "build_source_index",
    "build_source_index_file",
    "chinese_number",
]

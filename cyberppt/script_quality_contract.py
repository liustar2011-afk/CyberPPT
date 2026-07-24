"""Deterministic PPT script parsing and quality contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re


PAGE_HEADING_RE = re.compile(r"^##\s+第(\d+)页[：:](.+?)\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$")
MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
SOURCE_RE = re.compile(r"S\d{3}")


@dataclass(frozen=True)
class ScriptPage:
    page_id: str
    sequence: int
    heading: str
    page_type: str
    title: str
    main_message: str
    source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]


@dataclass(frozen=True)
class ScriptDocument:
    pages: tuple[ScriptPage, ...]


def _normalize_page_type(value: str) -> str:
    if "章节" in value:
        return "chapter"
    if "封面" in value:
        return "cover"
    if "目录" in value:
        return "contents"
    if "封底" in value:
        return "closing"
    return "content"


def _page_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(PAGE_HEADING_RE.finditer(text))
    return [
        (
            int(match.group(1)),
            match.group(2).strip(),
            text[
                match.end() : (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(text)
                )
            ],
        )
        for index, match in enumerate(matches)
    ]


def _field_blocks(body: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    active = ""
    for raw_line in body.splitlines():
        match = FIELD_RE.match(raw_line)
        if match:
            active = match.group(1).strip()
            blocks[active] = [match.group(2).strip()]
        elif active:
            blocks[active].append(raw_line.rstrip())
    return {key: "\n".join(lines).strip() for key, lines in blocks.items()}


def parse_script_markdown(text: str) -> ScriptDocument:
    pages: list[ScriptPage] = []
    for sequence, heading, body in _page_sections(text):
        fields = _field_blocks(body)
        onscreen = fields.get("上屏文字", "")
        modules = tuple(
            match.group(1).strip()
            for line in onscreen.splitlines()
            if (match := MODULE_RE.match(line))
        )
        pages.append(
            ScriptPage(
                page_id=f"p{sequence:02d}",
                sequence=sequence,
                heading=heading,
                page_type=_normalize_page_type(fields.get("页面类型", "")),
                title=fields.get("页面标题", heading).strip(),
                main_message=fields.get("主判断", "").strip(),
                source_refs=tuple(SOURCE_RE.findall(fields.get("证据", ""))),
                boundary=fields.get("边界", "").strip(),
                visual_structure=fields.get("视觉结构", "").strip(),
                onscreen_text=onscreen,
                module_titles=modules,
            )
        )
    if not pages:
        raise ValueError("script contains no page headings")
    return ScriptDocument(tuple(pages))

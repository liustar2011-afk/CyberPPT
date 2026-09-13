"""Structured external Deck Plan intake; no Stage 01 grammar or authoring."""
from __future__ import annotations

import re

from cyberppt.script_quality.models import ScriptDocument, ScriptPage
from cyberppt.script_quality.parsing import _parse_fidelity_text


SLIDE_RE = re.compile(r"^#{2,6}\s+Slide\s+(\d+)\s*[-–—:]\s*(.+?)\s*$", re.I)
PART_RE = re.compile(r"^#{2,3}\s+(Part\s+\d+\s*[:：].+?)\s*$", re.I)
FIELD_RE = re.compile(r"^[-*]\s+(?:\*\*(.+?)\*\*|([\w][\w /-]*?))\s*[:：]\s*(.*)$")
PAGE_TYPES = {
    "content": "content", "内容页": "content",
    "cover": "cover", "封面": "cover",
    "agenda": "contents", "contents": "contents", "toc": "contents", "目录": "contents", "目录页": "contents",
    "transition": "chapter", "section": "chapter", "chapter": "chapter", "过渡页": "chapter", "章节页": "chapter",
    "back-cover": "closing", "back cover": "closing", "closing": "closing", "ending": "closing", "封底": "closing",
}


def normalize_page_type(value: str) -> str:
    normalized = re.sub(r"^template\s*[:：]\s*", "", value.strip().lower())
    if normalized not in PAGE_TYPES:
        raise ValueError(f"DECK_PLAN_PAGE_TYPE: unsupported Page type {value!r}")
    return PAGE_TYPES[normalized]


def is_deck_plan(text: str) -> bool:
    fence = ""
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            fence = "" if fence == marker[1][0] else marker[1][0]
        elif not fence and re.match(r"^#{2,6}\s+Slide\b", line, re.I):
            return True
    return False


def parse_deck_plan(text: str) -> ScriptDocument:
    """Read explicit page fields without treating document instructions as actions."""
    contract: dict[str, str] = {}
    blocks: list[tuple[int, str, str, dict[str, str]]] = []
    part = ""
    fields: dict[str, str] | None = None
    active = ""
    in_contract = False
    modes: list[str] = []
    fence = ""
    for lineno, line in enumerate(text.splitlines(), 1):
        fence_match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence_match:
            marker = fence_match[1][0]
            fence = "" if fence == marker else marker
            if fields is not None and active:
                fields[active] += "\n" + line
            continue
        if fence:
            if fields is not None and active:
                fields[active] += "\n" + line
            continue
        slide = SLIDE_RE.match(line)
        if slide:
            fields = {}
            blocks.append((int(slide[1]), slide[2], part, fields))
            active = ""
            in_contract = False
            continue
        if re.match(r"^#{2,6}\s+Slide\b", line, re.I):
            raise ValueError(f"DECK_PLAN_INVALID_SLIDE at line {lineno}: {line}")
        section = PART_RE.match(line)
        if section:
            part = section[1]
            fields = None
            active = ""
            continue
        # Document sections end the last page as well as the contract table.
        if re.match(r"^#{1,2}\s+", line):
            in_contract = "communication contract" in line.lower()
            fields = None
            active = ""
            continue
        if not blocks:
            mode = re.match(r"^>\s*交流方式\s*[:：]\s*(\S+)\s*$", line)
            if mode:
                modes.append(mode[1])
            if in_contract and line.strip().startswith("|"):
                cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
                if len(cells) != 2:
                    raise ValueError(f"DECK_PLAN_INVALID_TABLE at line {lineno}")
                key, value = (cell.strip().replace(r"\|", "|") for cell in cells)
                if key.lower() == "item" or re.fullmatch(r"[: -]+", key):
                    continue
                if key in contract:
                    raise ValueError(f"DECK_PLAN_DUPLICATE_CONTRACT at line {lineno}: {key}")
                contract[key] = value
        if fields is not None:
            match = FIELD_RE.match(line)
            if match:
                active = (match[1] or match[2]).strip().lower().replace("_", " ")
                if active in fields:
                    raise ValueError(f"DECK_PLAN_DUPLICATE_FIELD at line {lineno}: {active}")
                fields[active] = match[3]
            elif active:
                fields[active] += "\n" + line
            elif line.strip():
                raise ValueError(f"DECK_PLAN_UNASSIGNED_TEXT at line {lineno}")
    numbers = [block[0] for block in blocks]
    if numbers != list(range(1, len(blocks) + 1)) or not blocks:
        raise ValueError("DECK_PLAN_PAGE_SEQUENCE: expected unique consecutive Slide numbers starting at 1")
    declared = contract.get("Page Count")
    if declared is not None and (not declared.isdigit() or int(declared) != len(blocks)):
        raise ValueError(f"DECK_PLAN_PAGE_COUNT: declared {declared}, parsed {len(blocks)}")
    if len(set(modes)) > 1:
        raise ValueError("conflicting delivery_mode declarations")
    contract_mode = contract.get("Reading Mode", "")
    if modes and contract_mode in {"presented", "self_read"} and modes[0] != contract_mode:
        raise ValueError("conflicting delivery_mode declarations")
    mode = modes[0] if modes else contract_mode
    explicit = mode in {"presented", "self_read"}
    if modes and not explicit:
        raise ValueError(f"unsupported delivery_mode: {mode}")
    pages = []
    context_keys = ("audience move", "evidence", "relationships", "composition", "rhythm", "cover impact", "closing impact")
    known = {*context_keys, "title", "content", "core message", "fidelity text", "保真文字", "page type", "页面类型"}
    for number, heading, chapter, raw in blocks:
        values = {key: value.strip() for key, value in raw.items()}
        for required in ("title", "content"):
            if not values.get(required):
                raise ValueError(f"DECK_PLAN_MISSING_FIELD: Slide {number:02d} needs {required}")
        if "fidelity text" in values and "保真文字" in values:
            raise ValueError(f"DECK_PLAN_DUPLICATE_FIELD: Slide {number:02d} fidelity_text")
        if "page type" in values and "页面类型" in values:
            raise ValueError(f"DECK_PLAN_DUPLICATE_FIELD: Slide {number:02d} page_type")
        page_type = normalize_page_type(values.get("page type", values.get("页面类型", "content")))
        pages.append(ScriptPage(
            page_id=f"p{number:02d}", sequence=number, heading=heading,
            page_type=page_type, title=values["title"], main_message=values.get("core message", ""),
            full_prose=values["content"], onscreen_text=values["content"],
            raw_onscreen_text=values["content"], onscreen_source="external_content_stage02_source",
            selection_notes="", evidence_map="", evidence_map_refs=(), source_refs=(),
            boundary_source_refs=(), boundary="", visual_structure="", module_titles=(),
            fidelity_text=_parse_fidelity_text(values.get("fidelity text", values.get("保真文字", ""))),
            delivery_mode=mode if explicit else "self_read", delivery_mode_explicit=explicit,
            external_format="deck-plan-v1",
            part=chapter, communication_contract=dict(contract),
            additional_fields={key: value for key, value in values.items() if key not in known},
            **{key.replace(" ", "_"): values.get(key, "") for key in context_keys},
        ))
    return ScriptDocument(tuple(pages))

"""Deterministic parsing for CyberPPT script-quality contracts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from .models import ScriptDocument, ScriptPage


PAGE_HEADING_RE = re.compile(
    r"^##\s+(?:(?:第(\d+)页[：:](.+?)|P(\d+)\s+(.+?)))\s*$",
    re.MULTILINE,
)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$")
HEADING_FIELD_RE = re.compile(r"^###\s+(.+?)\s*$")
NON_ONSCREEN_VISUAL_HEADING_RE = re.compile(r"^【视觉结构[，,]\s*不上屏】\s*$")

# Current project scripts also use Markdown section headings for the page
# contract fields. Keep the legacy ``- 字段：内容`` parser, but normalize these
# headings so the drawable 上屏文字 block is not silently dropped.
HEADING_FIELD_ALIASES = {
    "完整文字稿": "完整文字稿",
    "完整文字稿段落映射": "完整文字稿段落映射",
    "文字稿取舍说明": "文字稿取舍说明",
    "证据映射": "证据映射",
    "证据": "证据",
    "边界依据": "边界依据",
    "边界": "边界",
    "上屏文字": "上屏文字",
    "上屏结论": "上屏结论",
    "视觉意图类型": "视觉意图类型",
    "视觉证明": "视觉证明",
    # "逻辑骨架" and "视觉意图与生图构图" are legacy heading names some
    # generators use in place of a real 视觉结构 section; both alias onto
    # the canonical field. When a page uses the canonical "视觉结构（不上屏）"
    # heading directly (added to the page-composition contract so a genuine
    # composition field always exists — see generate_script_final.py's
    # 视觉结构 requirement), it must ALSO map onto the same key, or
    # _heading_field_name returns None for it, the heading is invisible as a
    # field boundary, and its content silently merges with whatever field
    # preceded it (observed: 逻辑骨架 + 视觉结构 + the page-contract HTML
    # comment all concatenating into one blob).
    "逻辑骨架": "视觉结构",
    "视觉结构": "视觉结构",
    "视觉意图与生图构图": "视觉结构",
    "演讲者备注": "演讲者备注",
}

# Peer-level page-contract fields.  A ``- label: value`` line inside the
# drawable 上屏文字 block is ambiguous: most such lines are visible module
# copy, while these names start a new backend/contract field.  Keep the list
# explicit so ordinary module labels remain drawable without allowing a
# backend field to be swallowed by 上屏文字.
PAGE_CONTRACT_FIELDS = {
    "页面类型",
    "页面标题",
    "副标题",
    "核心结论",
    "主判断",
    "完整文字稿",
    "完整文字稿段落映射",
    "文字稿取舍说明",
    "证据映射",
    "上屏文字",
    "上屏模块清单",
    "上屏顶层模块清单",
    "上屏结论",
    "判断角色",
    "上屏结论模式",
    "视觉意图类型",
    "视觉载体",
    "生图锁定文字",
    "版式母题",
    "场景角色",
    "视觉证明",
    "证据",
    "边界依据",
    "边界",
    "视觉结构",
    "讲解提示",
    "演讲者备注",
}


def _heading_field_name(raw: str) -> str | None:
    """Map a Markdown page-contract heading to the canonical field name."""

    name = re.sub(r"[（(].*?[）)]\s*$", "", raw.strip()).strip()
    return HEADING_FIELD_ALIASES.get(name)


MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
INLINE_MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*(?:\s*[|｜:：].*)?\s*$")
# Source Truth identifiers are historically S015/S0410 and current Stage 01
# projects may use ST003/ST0410. Match both complete forms so a valid formal
# Source Truth ID is not reported as missing merely because its namespace is
# explicit.
SOURCE_RE = re.compile(r"ST?\d{3,4}(?!\d)")
SOURCE_RANGE_RE = re.compile(
    r"(?P<prefix>ST?)?(?P<start>\d{3,4})\s*[—–-]\s*"
    r"(?P<end_prefix>ST?)(?P<end>\d{3,4})"
)
PAGE_CONTRACT_RECEIPT_RE = re.compile(
    r"<!--\s*cyberppt-page-contract\s+(?P<payload>\{.*?\})\s*-->",
    re.S,
)
SPEAKER_SECTION_RE = re.compile(
    r"【(?:演讲者备注|演讲稿|讲稿|备注)】\s*(?P<body>.*)$",
    re.S,
)


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
            int(match.group(1) or match.group(3)),
            (match.group(2) or match.group(4)).strip(),
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
        if re.match(r"^【(?:演讲者备注|演讲稿|讲稿|备注)】", raw_line.strip()):
            active = ""
            continue
        if NON_ONSCREEN_VISUAL_HEADING_RE.match(raw_line.strip()):
            active = "视觉结构"
            blocks[active] = []
            continue
        heading_match = HEADING_FIELD_RE.match(raw_line.strip())
        if heading_match:
            heading_field = _heading_field_name(heading_match.group(1))
            if heading_field:
                active = heading_field
                blocks[active] = []
                continue
            # Module headings inside 上屏文字 are content, not a new field;
            # leave ``active`` unchanged so their following bullets remain
            # drawable text, but preserve the heading itself so downstream
            # module-title extraction can retain the reading hierarchy.
            if active == "上屏文字":
                blocks[active].append(raw_line.rstrip())
            continue
        match = FIELD_RE.match(raw_line)
        if match:
            field_name = match.group(1).strip()
            if active == "上屏文字" and field_name not in PAGE_CONTRACT_FIELDS:
                # Module bullets such as ``- 政策牵引：...`` belong to the
                # drawable text layer; they are not peer-level contract fields.
                blocks[active].append(raw_line.rstrip())
                continue
            active = field_name
            blocks[active] = [match.group(2).strip()]
        elif active:
            blocks[active].append(raw_line.rstrip())
    result: dict[str, str] = {}
    for key, lines in blocks.items():
        # Drop only genuinely blank leading/trailing lines. A naive
        # ``"\n".join(lines).strip()`` also character-strips the joined
        # string, which eats the leading indentation of the first content
        # line whenever the field declaration line itself was empty (a
        # common, even recommended, layout: ``- 上屏文字：`` followed by a
        # blank line, then indented module content). That asymmetric loss
        # made the first top-level on-screen module look like it sat at
        # indent 0 while its siblings kept their real indent, corrupting the
        # module-hierarchy checks downstream.
        start = 0
        end = len(lines)
        while start < end and not lines[start].strip():
            start += 1
        while end > start and not lines[end - 1].strip():
            end -= 1
        result[key] = "\n".join(lines[start:end])
    return result


def _source_refs(text: str) -> tuple[str, ...]:
    """Extract explicit Source IDs and expand inclusive S/ST ranges.

    Authoring inputs and human-readable scripts use ranges to avoid turning the
    evidence field into an unreadable wall of IDs.  The audit contract still
    needs the atomic IDs for exact Outline coverage, so expand ranges at parse
    time while preserving first-seen order and de-duplicating references.
    """

    source_text = text or ""
    ranges = list(SOURCE_RANGE_RE.finditer(source_text))
    events: list[tuple[int, str, object]] = []
    for match in ranges:
        events.append((match.start(), "range", match))
    for match in SOURCE_RE.finditer(source_text):
        if any(item.start() <= match.start() < item.end() for item in ranges):
            continue
        events.append((match.start(), "single", match.group(0)))

    refs: list[str] = []
    for _, kind, value in sorted(events, key=lambda item: item[0]):
        if kind == "single":
            refs.append(str(value))
            continue
        match = value
        assert isinstance(match, re.Match)
        prefix = match.group("prefix") or match.group("end_prefix")
        if prefix != match.group("end_prefix"):
            continue
        start = int(match.group("start"))
        end = int(match.group("end"))
        if end < start or end - start > 1000:
            continue
        width = max(len(match.group("start")), len(match.group("end")))
        refs.extend(
            f"{prefix}{number:0{width}d}" for number in range(start, end + 1)
        )
    return tuple(dict.fromkeys(refs))


def _parse_prose_paragraph_map(text: str) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Parse one off-screen provenance entry for each full-prose paragraph."""

    result: list[tuple[tuple[str, ...], str]] = []
    for raw in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*]\s*)?", "", raw).strip()
        if not line:
            continue
        refs_text, marker, reason = line.partition("｜合并理由：")
        refs = _source_refs(refs_text)
        if refs:
            result.append((refs, reason.strip() if marker else ""))
    return tuple(result)


def _field_order(body: str) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw_line in body.splitlines():
        if NON_ONSCREEN_VISUAL_HEADING_RE.match(raw_line.strip()):
            ordered.append("视觉结构")
            continue
        heading_match = HEADING_FIELD_RE.match(raw_line.strip())
        if heading_match:
            heading_field = _heading_field_name(heading_match.group(1))
            if heading_field:
                ordered.append(heading_field)
            continue
        match = FIELD_RE.match(raw_line)
        if match:
            field_name = match.group(1).strip()
            if field_name in PAGE_CONTRACT_FIELDS:
                ordered.append(field_name)
    return tuple(ordered)


def extract_speaker_notes(body: str) -> str:
    """Prefer 【演讲者备注】 section, then `- 演讲者备注：` field."""

    section = SPEAKER_SECTION_RE.search(body)
    if section:
        return re.sub(r"\n-{3,}\s*$", "", section.group("body").strip()).strip()
    fields = _field_blocks(body)
    return fields.get("演讲者备注", "").strip()


def extract_page_contract_receipt(body: str) -> dict[str, object] | None:
    match = PAGE_CONTRACT_RECEIPT_RE.search(body)
    if not match:
        return None
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return {"_invalid": True}
    return payload if isinstance(payload, dict) else {"_invalid": True}


def _module_title(line: str) -> str | None:
    """Extract a Markdown module title from a standalone or inline heading.

    Reading-oriented scripts commonly use either ``**模块**`` followed by
    bullets or the compact ``**模块**｜正文`` form.  Both represent one
    drawable module; the inline body must remain in the visible text layer.
    """

    # Accept both a bare Markdown heading and the repository's readable
    # ``- **小标题**`` list form.
    candidate = re.sub(r"^\s*-\s+", "", line)
    match = MODULE_RE.match(candidate) or INLINE_MODULE_RE.match(candidate)
    if match:
        return match.group(1).strip()
    # Canonical v3 on-screen text is plain text, not Markdown.  A module is
    # represented as ``label：body`` or as a short standalone group label;
    # indentation carries hierarchy.  Keep legacy Markdown recognition above
    # for migration diagnostics, but do not require it for module extraction.
    plain = candidate.strip()
    if not plain:
        return None
    if "：" in plain or ":" in plain:
        label = re.split(r"[：:]", plain, maxsplit=1)[0].strip()
        return label or None
    if len(plain) <= 28 and not re.search(r"[。；;！？!?]$", plain):
        return plain
    return None


def audience_facing_group_label(label: str) -> str:
    """Remove authoring-only structural markers from a visible group label.

    Labels such as ``第1行｜...`` are layout/debug coordinates, not audience
    copy.  Strip them centrally so every script generator benefits, regardless
    of the source project.
    """

    value = str(label or "").strip()
    value = re.sub(
        r"^第\s*(?:[一二三四五六七八九十]+|\d+|[Xx])\s*行\s*[｜|:]\s*",
        "",
        value,
    )
    value = re.sub(r"(?:一|二|两|三|四|五|六|七|八|九|十|\d+)个层面$", "", value)
    value = re.sub(r"(控制链|权利对象)层面$", r"\1", value)
    if value == "四个维度分别选择":
        value = "交付维度选择"
    return value.strip(" ：:")


def strip_authoring_group_marker(line: str) -> str:
    """Remove authoring-only row markers while preserving line indentation.

    Final scripts may contain layout coordinates such as ``第1行｜...`` or
    ``第X行｜...``.  They are useful to an author but are not audience-facing
    copy and must never be sent to ImageGen as visible text.
    """

    raw = str(line or "")
    match = re.match(r"^(\s*)(.*)$", raw, flags=re.S)
    if not match:
        return raw
    indent, body = match.groups()
    cleaned = audience_facing_group_label(body)
    return indent + cleaned if cleaned != body else raw


def _line_indent(line: str) -> int:
    """Return leading-space indentation for relative module hierarchy."""

    return len(line) - len(line.lstrip(" "))


def _json_string_list(value: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, list):
        return ()
    return tuple(str(item).strip() for item in payload if str(item).strip())


def load_page_contract_sidecar(script_path: Path) -> dict[str, dict[str, object]]:
    """Load and verify the page-contract sidecar next to a final script.

    Missing sidecars are allowed for legacy scripts.  A present sidecar is a
    formal binding artifact and therefore fails closed when its script hash or
    shape is invalid.
    """

    script_path = script_path.expanduser().resolve()
    sidecar = script_path.with_name("page-contracts.json")
    if not sidecar.is_file():
        return {}
    payload = json.loads(sidecar.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("schema") != "cyberppt.page_contracts.v1":
        raise ValueError(f"invalid page-contract sidecar: {sidecar}")
    if payload.get("script") != script_path.name:
        raise ValueError(f"page-contract sidecar targets another script: {sidecar}")
    expected_script = hashlib.sha256(script_path.read_bytes()).hexdigest()
    if str(payload.get("script_sha256") or "").casefold() != expected_script.casefold():
        raise ValueError(f"page-contract sidecar is stale for script: {sidecar}")
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, dict):
        raise ValueError(f"page-contract sidecar pages must be an object: {sidecar}")
    pages: dict[str, dict[str, object]] = {}
    for page_id, receipt in raw_pages.items():
        normalized_page_id = str(page_id)
        if not re.fullmatch(r"p\d{2,}", normalized_page_id):
            raise ValueError(f"invalid page id in page-contract sidecar: {page_id}")
        if not isinstance(receipt, dict):
            raise ValueError(f"invalid receipt for {normalized_page_id}: {sidecar}")
        if receipt.get("page_id") != normalized_page_id:
            raise ValueError(
                f"page-contract receipt id mismatch for {normalized_page_id}: {sidecar}"
            )
        pages[normalized_page_id] = receipt
    return pages


def parse_script_markdown(
    text: str,
    page_contracts: dict[str, dict[str, object]] | None = None,
) -> ScriptDocument:
    pages: list[ScriptPage] = []
    for sequence, heading, body in _page_sections(text):
        fields = _field_blocks(body)
        page_type = _normalize_page_type(fields.get("页面类型", ""))
        onscreen = fields.get("上屏文字", "")
        module_lines: list[tuple[str, int]] = []
        if page_type == "content":
            for line in onscreen.splitlines():
                title = _module_title(line)
                if title is None:
                    continue
                module_lines.append((title, _line_indent(line)))
        modules = tuple(title for title, _ in module_lines)
        # Markdown nested under ``- 上屏文字：`` normally starts with two or
        # four spaces, so absolute column zero is not a valid definition of
        # top level.  The least-indented module on this page is the peer level;
        # only deeper module headings are children.
        base_module_indent = min((indent for _, indent in module_lines), default=0)
        top_level_modules = tuple(
            title for title, indent in module_lines if indent == base_module_indent
        )
        declared_modules = _json_string_list(fields.get("上屏模块清单", ""))
        declared_top_level_modules = _json_string_list(
            fields.get("上屏顶层模块清单", "")
        )
        if declared_modules:
            modules = declared_modules
        if declared_top_level_modules:
            top_level_modules = declared_top_level_modules
        pages.append(
            ScriptPage(
                page_id=f"p{sequence:02d}",
                sequence=sequence,
                heading=heading,
                page_type=page_type,
                title=fields.get("页面标题", heading).strip(),
                subtitle=fields.get("副标题", "").strip(),
                main_message=(
                    fields.get("核心结论")
                    or fields.get("主判断")
                    or fields.get("页面命题", "")
                ).strip(),
                full_prose=fields.get("完整文字稿", "").strip(),
                prose_paragraph_map=_parse_prose_paragraph_map(
                    fields.get("完整文字稿段落映射", "")
                ),
                selection_notes=fields.get("文字稿取舍说明", "").strip(),
                evidence_map=fields.get("证据映射", "").strip(),
                evidence_map_refs=_source_refs(fields.get("证据映射", "")),
                source_refs=tuple(
                    dict.fromkeys(
                        list(_source_refs(fields.get("证据", "")))
                        + list(_source_refs(fields.get("边界依据", "")))
                    )
                ),
                boundary_source_refs=_source_refs(fields.get("边界依据", "")),
                boundary=fields.get("边界", "").strip(),
                visual_structure=(
                    fields.get("视觉结构", "")
                    .split("<!--", 1)[0]
                    .strip()
                ),
                onscreen_text=onscreen,
                module_titles=modules,
                raw_onscreen_text=onscreen,
                top_level_module_titles=top_level_modules,
                visual_proof=fields.get("视觉证明", "").strip(),
                onscreen_judgment=fields.get("上屏结论", "").strip(),
                judgment_role=fields.get("判断角色", "").strip(),
                onscreen_judgment_mode=fields.get("上屏结论模式", "").strip(),
                visual_intent_type=fields.get("视觉意图类型", "").strip(),
                visual_carrier=fields.get("视觉载体", "").strip(),
                image_locked_text=fields.get("生图锁定文字", "").strip(),
                onscreen_expression_form=fields.get("上屏表达结构", "").strip(),
                layout_motif=fields.get("版式母题", "").strip(),
                scene_role=fields.get("场景角色", "").strip(),
                field_order=_field_order(body),
                coaching_tip=(
                    fields.get("讲解提示", "")
                    .split("<!--", 1)[0]
                    .split("【", 1)[0]
                    .strip()
                ),
                speaker_notes=extract_speaker_notes(body),
                contract_receipt=(page_contracts or {}).get(f"p{sequence:02d}")
                or extract_page_contract_receipt(body),
            )
        )
    if not pages:
        raise ValueError("script contains no page headings")
    return ScriptDocument(tuple(pages))


def parse_script_path(path: Path) -> ScriptDocument:
    """Parse a script with its verified sidecar, falling back to legacy comments."""

    path = path.expanduser().resolve()
    return parse_script_markdown(
        path.read_text(encoding="utf-8-sig"),
        load_page_contract_sidecar(path),
    )


__all__ = [
    "PAGE_HEADING_RE",
    "audience_facing_group_label",
    "extract_page_contract_receipt",
    "extract_speaker_notes",
    "load_page_contract_sidecar",
    "parse_script_markdown",
    "parse_script_path",
    "strip_authoring_group_marker",
]

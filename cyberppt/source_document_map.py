"""Deterministic source registry, heading tree, and stable semantic units.

This module is deliberately factual.  It records where source content lives
and how the source itself is structured; it does not decide the author's
thesis, narrative importance, or slide structure.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import posixpath
import re
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


SOURCE_MAP_STAGE = Path("workbench/stages/00-source-map")
SOURCE_REGISTRY = SOURCE_MAP_STAGE / "source-registry.json"
SOURCE_UNITS = SOURCE_MAP_STAGE / "source-units.jsonl"
SOURCE_HEADING_TREE = SOURCE_MAP_STAGE / "source-heading-tree.json"
SOURCE_MAP_MD = SOURCE_MAP_STAGE / "source-map.md"
SOURCE_MAP_AUDIT = SOURCE_MAP_STAGE / "source-map-audit.json"

REGISTRY_SCHEMA = "cyberppt.source_registry.v1"
UNIT_SCHEMA = "cyberppt.source_unit.v1"
HEADING_TREE_SCHEMA = "cyberppt.source_heading_tree.v1"
AUDIT_SCHEMA = "cyberppt.source_map_audit.v1"

_TEXT_SUFFIXES = frozenset({".txt", ".md", ".json", ".csv", ".tsv", ".yaml", ".yml"})
# Only .docx and .md can structurally carry heading markup (Word paragraph
# styles / "#" syntax); .txt and the other text suffixes never produce
# headings by design, so they are excluded from the missing-heading check.
_HEADING_CAPABLE_SUFFIXES = frozenset({".docx", ".md"})
_MIN_SUBSTANTIVE_UNITS_FOR_HEADING_CHECK = 3
# Fallback heading detection for sources with zero Word/Markdown-native
# headings. Deliberately narrow: only unambiguous numbering prefixes used by
# Chinese formal-document convention (章/节/顿号编号/括号编号/多级数字编号),
# matched against a short standalone line. This is a safety net for headings
# that were typed with the right numbering but never given a real heading
# style — not a general "looks like a heading" classifier, since a wrong
# guess here would silently inject fabricated chapter structure downstream.
_HEURISTIC_HEADING_PATTERNS: tuple[tuple[re.Pattern[str], int], ...] = (
    (re.compile(r"^第[一二三四五六七八九十百千0-9]+章[、：:\s　]*"), 1),
    (re.compile(r"^第[一二三四五六七八九十百千0-9]+节[、：:\s　]*"), 2),
    (re.compile(r"^\d+\.\d+(?:[.、．]|\s|$)"), 3),
    (re.compile(r"^[（(][一二三四五六七八九十百]+[)）]"), 3),
    (re.compile(r"^[一二三四五六七八九十百]+[、.．]"), 2),
    (re.compile(r"^\d+[、.．](?!\d)"), 2),
)
_MAX_HEURISTIC_HEADING_LENGTH = 40


def _heuristic_heading_level(text: str) -> int | None:
    stripped = text.strip()
    if not stripped or len(stripped) > _MAX_HEURISTIC_HEADING_LENGTH:
        return None
    if stripped[-1] in "。！？；":
        return None
    for pattern, level in _HEURISTIC_HEADING_PATTERNS:
        if pattern.match(stripped):
            return level
    return None
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_WP = "{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _source_id(relative_path: str) -> str:
    digest = _sha256_bytes(relative_path.casefold().encode("utf-8"))[:10].upper()
    return f"SRC-{digest}"


def _stable_id(
    source_id: str,
    kind: str,
    identity: str,
    duplicate_counts: dict[tuple[str, str], int],
) -> str:
    digest = _sha256_bytes(identity.encode("utf-8"))[:12].upper()
    # Unit and heading-tree occurrence counters share one extraction-local
    # dictionary but describe different identity domains.
    key = (f"unit:{kind}", digest)
    duplicate_counts[key] += 1
    return f"SU-{source_id.removeprefix('SRC-')}-{kind.upper()}-{digest}-{duplicate_counts[key]:02d}"


def _heading_id(
    source_id: str,
    level: int,
    title: str,
    parent_id: str,
    duplicate_counts: dict[tuple[str, str], int],
) -> str:
    identity = f"{level}\0{parent_id}\0{title.strip()}"
    digest = _sha256_bytes(identity.encode("utf-8"))[:12].upper()
    key = ("tree:heading", digest)
    duplicate_counts[key] += 1
    return f"H-{source_id.removeprefix('SRC-')}-{digest}-{duplicate_counts[key]:02d}"


def _anchor(text: str, maximum: int = 48) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    return normalized[:maximum]


def _paragraph_text(node: ElementTree.Element) -> str:
    return "".join(item.text or "" for item in node.iter(f"{_W}t")).strip()


def _style_metadata(package: zipfile.ZipFile) -> dict[str, dict[str, Any]]:
    try:
        root = ElementTree.fromstring(package.read("word/styles.xml"))
    except KeyError:
        return {}
    result: dict[str, dict[str, Any]] = {}
    for style in root.findall(f"{_W}style"):
        style_id = str(style.get(f"{_W}styleId") or "")
        if not style_id:
            continue
        name = style.find(f"{_W}name")
        outline = style.find(f"{_W}pPr/{_W}outlineLvl")
        outline_value = outline.get(f"{_W}val") if outline is not None else None
        result[style_id] = {
            "name": str(name.get(f"{_W}val") or "") if name is not None else "",
            "outline_level": int(outline_value) + 1 if str(outline_value or "").isdigit() else None,
        }
    return result


def _paragraph_style(node: ElementTree.Element) -> str:
    style = node.find(f"{_W}pPr/{_W}pStyle")
    return str(style.get(f"{_W}val") or "") if style is not None else ""


def _heading_level(
    node: ElementTree.Element,
    style_id: str,
    styles: dict[str, dict[str, Any]],
) -> int | None:
    explicit = node.find(f"{_W}pPr/{_W}outlineLvl")
    explicit_value = explicit.get(f"{_W}val") if explicit is not None else None
    if str(explicit_value or "").isdigit():
        return int(str(explicit_value)) + 1
    metadata = styles.get(style_id, {})
    if isinstance(metadata.get("outline_level"), int):
        return int(metadata["outline_level"])
    candidates = (style_id, str(metadata.get("name") or ""))
    for candidate in candidates:
        match = re.search(r"(?i)(?:heading|标题)\s*([1-9])", candidate)
        if match:
            return int(match.group(1))
    return None


def _is_caption(style_id: str, styles: dict[str, dict[str, Any]]) -> bool:
    name = str(styles.get(style_id, {}).get("name") or "")
    return any(
        re.search(pattern, value, flags=re.IGNORECASE)
        for value in (style_id, name)
        for pattern in (r"caption", r"题注")
    )


def _image_alt_text(doc_pr: ElementTree.Element | None) -> str:
    if doc_pr is None:
        return ""
    descriptive = str(doc_pr.get("descr") or doc_pr.get("title") or "").strip()
    if descriptive:
        return descriptive
    name = str(doc_pr.get("name") or "").strip()
    if re.fullmatch(r"(?i)(?:picture|image|图片|图像)\s*\d+", name):
        return ""
    return name


def _document_relationships(package: zipfile.ZipFile) -> dict[str, str]:
    try:
        root = ElementTree.fromstring(package.read("word/_rels/document.xml.rels"))
    except KeyError:
        return {}
    return {
        str(item.get("Id") or ""): str(item.get("Target") or "")
        for item in root.findall(f"{_REL}Relationship")
        if item.get("Id") and item.get("Target")
    }


def _unit(
    *,
    unit_id: str,
    source_id: str,
    source_path: str,
    kind: str,
    source_order: int,
    text: str,
    heading_id: str | None,
    heading_path: list[str],
    locator: dict[str, Any],
    style_id: str = "",
    outline_level: int | None = None,
    raw_sha256: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": UNIT_SCHEMA,
        "unit_id": unit_id,
        "source_id": source_id,
        "source_path": source_path,
        "kind": kind,
        "source_order": source_order,
        "heading_id": heading_id,
        "heading_path": list(heading_path),
        "style_id": style_id,
        "outline_level": outline_level,
        "locator": locator,
        "text_anchor": _anchor(text),
        "text": text,
        "unit_sha256": raw_sha256 or _sha256_bytes(text.encode("utf-8")),
        "metadata": metadata or {},
    }


def _extract_docx(
    path: Path,
    *,
    source_id: str,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    units: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    duplicate_counts: dict[tuple[str, str], int] = defaultdict(int)
    with zipfile.ZipFile(path) as package:
        root = ElementTree.fromstring(package.read("word/document.xml"))
        body = root.find(f"{_W}body")
        if body is None:
            raise ValueError(f"DOCX has no document body: {path}")
        styles = _style_metadata(package)
        relationships = _document_relationships(package)
        heading_stack: list[dict[str, Any]] = []
        paragraph_number = 0
        table_number = 0
        source_order = 0
        for child in body:
            source_order += 1
            if child.tag == f"{_W}p":
                paragraph_number += 1
                text = _paragraph_text(child)
                style_id = _paragraph_style(child)
                level = _heading_level(child, style_id, styles)
                if level is not None and text:
                    while heading_stack and int(heading_stack[-1]["level"]) >= level:
                        heading_stack.pop()
                    parent_id = str(heading_stack[-1]["heading_id"]) if heading_stack else ""
                    heading_id = _heading_id(source_id, level, text, parent_id, duplicate_counts)
                    heading_path = [str(item["title"]) for item in heading_stack] + [text]
                    unit_id = _stable_id(
                        source_id,
                        "heading",
                        f"{level}\0{'/'.join(heading_path)}\0{text}",
                        duplicate_counts,
                    )
                    units.append(
                        _unit(
                            unit_id=unit_id,
                            source_id=source_id,
                            source_path=source_path,
                            kind="heading",
                            source_order=source_order,
                            text=text,
                            heading_id=heading_id,
                            heading_path=heading_path,
                            locator={"paragraph": paragraph_number},
                            style_id=style_id,
                            outline_level=level,
                        )
                    )
                    heading = {
                        "heading_id": heading_id,
                        "source_id": source_id,
                        "source_path": source_path,
                        "title": text,
                        "level": level,
                        "parent_heading_id": parent_id or None,
                        "source_order": source_order,
                        "unit_id": unit_id,
                        "heading_path": heading_path,
                    }
                    headings.append(heading)
                    heading_stack.append(heading)
                elif text:
                    heading_id = str(heading_stack[-1]["heading_id"]) if heading_stack else None
                    heading_path = [str(item["title"]) for item in heading_stack]
                    kind = "caption" if _is_caption(style_id, styles) else "paragraph"
                    unit_id = _stable_id(
                        source_id,
                        kind,
                        f"{'/'.join(heading_path)}\0{style_id}\0{text}",
                        duplicate_counts,
                    )
                    units.append(
                        _unit(
                            unit_id=unit_id,
                            source_id=source_id,
                            source_path=source_path,
                            kind=kind,
                            source_order=source_order,
                            text=text,
                            heading_id=heading_id,
                            heading_path=heading_path,
                            locator={"paragraph": paragraph_number},
                            style_id=style_id,
                        )
                    )

                heading_id = str(heading_stack[-1]["heading_id"]) if heading_stack else None
                heading_path = [str(item["title"]) for item in heading_stack]
                drawing_properties = list(child.iter(f"{_WP}docPr"))
                for image_index, blip in enumerate(child.iter(f"{_A}blip"), 1):
                    rel_id = str(blip.get(f"{_R}embed") or "")
                    target = relationships.get(rel_id, "")
                    media_path = posixpath.normpath(posixpath.join("word", target)) if target else ""
                    doc_pr = (
                        drawing_properties[image_index - 1]
                        if image_index <= len(drawing_properties)
                        else None
                    )
                    alt_text = _image_alt_text(doc_pr)
                    raw = package.read(media_path) if media_path and media_path in package.namelist() else b""
                    display = alt_text or (f"[image: {Path(media_path).name}]" if media_path else "[image]")
                    unit_id = _stable_id(
                        source_id,
                        "image",
                        f"{'/'.join(heading_path)}\0{_sha256_bytes(raw) if raw else rel_id}\0{display}",
                        duplicate_counts,
                    )
                    units.append(
                        _unit(
                            unit_id=unit_id,
                            source_id=source_id,
                            source_path=source_path,
                            kind="image",
                            source_order=source_order,
                            text=display,
                            heading_id=heading_id,
                            heading_path=heading_path,
                            locator={
                                "paragraph": paragraph_number,
                                "image_index": image_index,
                                "relationship_id": rel_id,
                                "media_path": media_path,
                            },
                            raw_sha256=_sha256_bytes(raw) if raw else None,
                            metadata={
                                "alt_text": alt_text,
                                "media_path": media_path,
                                "mime_type": mimetypes.guess_type(media_path)[0] if media_path else None,
                                "requires_visual_interpretation": not bool(alt_text),
                            },
                        )
                    )
                    if not alt_text:
                        warnings.append(
                            {
                                "code": "SOURCE_IMAGE_SEMANTICS_PENDING",
                                "message": f"Image {media_path or rel_id} has no usable alt text and needs visual/OCR interpretation.",
                            }
                        )
            elif child.tag == f"{_W}tbl":
                table_number += 1
                heading_id = str(heading_stack[-1]["heading_id"]) if heading_stack else None
                heading_path = [str(item["title"]) for item in heading_stack]
                for row_number, row in enumerate(child.findall(f"{_W}tr"), 1):
                    cells = [
                        "".join(node.text or "" for node in cell.iter(f"{_W}t")).strip()
                        for cell in row.findall(f"{_W}tc")
                    ]
                    text = " | ".join(cells).strip()
                    if not text:
                        continue
                    unit_id = _stable_id(
                        source_id,
                        "table-row",
                        f"{'/'.join(heading_path)}\0{table_number}\0{text}",
                        duplicate_counts,
                    )
                    units.append(
                        _unit(
                            unit_id=unit_id,
                            source_id=source_id,
                            source_path=source_path,
                            kind="table_row",
                            source_order=source_order,
                            text=text,
                            heading_id=heading_id,
                            heading_path=heading_path,
                            locator={"table": table_number, "table_row": row_number},
                            metadata={"cells": cells},
                        )
                    )
    return units, headings, warnings


def _extract_text(
    path: Path,
    *,
    source_id: str,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig")
    units: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    duplicate_counts: dict[tuple[str, str], int] = defaultdict(int)
    heading_stack: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        value = raw_line.strip()
        if not value:
            continue
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", value) if path.suffix.casefold() == ".md" else None
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            while heading_stack and int(heading_stack[-1]["level"]) >= level:
                heading_stack.pop()
            parent_id = str(heading_stack[-1]["heading_id"]) if heading_stack else ""
            heading_id = _heading_id(source_id, level, title, parent_id, duplicate_counts)
            heading_path = [str(item["title"]) for item in heading_stack] + [title]
            unit_id = _stable_id(source_id, "heading", f"{level}\0{'/'.join(heading_path)}", duplicate_counts)
            units.append(
                _unit(
                    unit_id=unit_id,
                    source_id=source_id,
                    source_path=source_path,
                    kind="heading",
                    source_order=line_number,
                    text=title,
                    heading_id=heading_id,
                    heading_path=heading_path,
                    locator={"line": line_number},
                    outline_level=level,
                )
            )
            heading = {
                "heading_id": heading_id,
                "source_id": source_id,
                "source_path": source_path,
                "title": title,
                "level": level,
                "parent_heading_id": parent_id or None,
                "source_order": line_number,
                "unit_id": unit_id,
                "heading_path": heading_path,
            }
            headings.append(heading)
            heading_stack.append(heading)
            continue
        heading_id = str(heading_stack[-1]["heading_id"]) if heading_stack else None
        heading_path = [str(item["title"]) for item in heading_stack]
        unit_id = _stable_id(
            source_id,
            "line",
            f"{'/'.join(heading_path)}\0{value}",
            duplicate_counts,
        )
        units.append(
            _unit(
                unit_id=unit_id,
                source_id=source_id,
                source_path=source_path,
                kind="paragraph",
                source_order=line_number,
                text=value,
                heading_id=heading_id,
                heading_path=heading_path,
                locator={"line": line_number},
            )
        )
    return units, headings, []


def _extract_binary(
    path: Path,
    *,
    source_id: str,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    raw = path.read_bytes()
    duplicate_counts: dict[tuple[str, str], int] = defaultdict(int)
    unit_id = _stable_id(source_id, "binary", _sha256_bytes(raw), duplicate_counts)
    unit = _unit(
        unit_id=unit_id,
        source_id=source_id,
        source_path=source_path,
        kind="binary",
        source_order=1,
        text=f"[binary source: {path.name}; direct inspection required]",
        heading_id=None,
        heading_path=[],
        locator={"file": source_path},
        raw_sha256=_sha256_bytes(raw),
        metadata={"mime_type": mimetypes.guess_type(path.name)[0], "requires_direct_inspection": True},
    )
    return [unit], [], [
        {
            "code": "SOURCE_BINARY_DIRECT_INSPECTION_REQUIRED",
            "message": f"{source_path} is registered but not deterministically text-extracted.",
        }
    ]


def _extract_source(
    path: Path,
    *,
    source_id: str,
    source_path: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, str]]]:
    suffix = path.suffix.casefold()
    if suffix == ".docx":
        return _extract_docx(path, source_id=source_id, source_path=source_path)
    if suffix in _TEXT_SUFFIXES:
        return _extract_text(path, source_id=source_id, source_path=source_path)
    return _extract_binary(path, source_id=source_id, source_path=source_path)


def _render_source_map(
    registry: dict[str, Any],
    headings: list[dict[str, Any]],
    units: list[dict[str, Any]],
    audit: dict[str, Any],
) -> str:
    lines = [
        "# Source document map",
        "",
        f"- status: `{audit['status']}`",
        f"- sources: {len(registry['sources'])}",
        f"- headings: {len(headings)}",
        f"- semantic units: {len(units)}",
        "",
        "## Sources",
        "",
    ]
    for source in registry["sources"]:
        lines.append(
            f"- `{source['source_id']}` `{source['path']}` bytes={source['bytes']} sha256=`{source['sha256']}`"
        )
    lines += ["", "## Original heading tree", ""]
    for heading in headings:
        indent = "  " * max(0, int(heading["level"]) - 1)
        marker = " ⚠ heuristic" if heading.get("detection_method") == "heuristic_pattern" else ""
        lines.append(f"{indent}- `{heading['heading_id']}` {heading['title']}{marker}")
    if not headings:
        lines.append("- No semantic headings detected.")
    lines += ["", "## Unit inventory", ""]
    counts: dict[str, int] = defaultdict(int)
    for item in units:
        counts[str(item["kind"])] += 1
    for kind, count in sorted(counts.items()):
        lines.append(f"- {kind}: {count}")
    lines += ["", "## Warnings", ""]
    if audit["warnings"]:
        lines.extend(f"- `{item['code']}`: {item['message']}" for item in audit["warnings"])
    else:
        lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def _promote_heuristic_headings(
    source_id: str,
    source_path: str,
    units: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    """Reclassify strongly-numbered paragraphs as headings when a source has
    no Word/Markdown-native headings at all. Every promoted unit/heading is
    tagged ``detection_method: "heuristic_pattern"`` so it never looks like a
    real, author-declared heading downstream.
    """

    duplicate_counts: dict[tuple[str, str], int] = defaultdict(int)
    heading_stack: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    rewritten: list[dict[str, Any]] = []
    promoted = 0
    for unit in units:
        level = (
            _heuristic_heading_level(str(unit.get("text") or ""))
            if unit.get("kind") == "paragraph"
            else None
        )
        if level is None:
            rewritten.append(
                {
                    **unit,
                    "heading_id": str(heading_stack[-1]["heading_id"]) if heading_stack else None,
                    "heading_path": [str(item["title"]) for item in heading_stack],
                }
            )
            continue
        while heading_stack and int(heading_stack[-1]["level"]) >= level:
            heading_stack.pop()
        parent_id = str(heading_stack[-1]["heading_id"]) if heading_stack else ""
        title = str(unit.get("text") or "").strip()
        heading_id = _heading_id(source_id, level, title, parent_id, duplicate_counts)
        heading_path = [str(item["title"]) for item in heading_stack] + [title]
        heading = {
            "heading_id": heading_id,
            "source_id": source_id,
            "source_path": source_path,
            "title": title,
            "level": level,
            "parent_heading_id": parent_id or None,
            "source_order": unit.get("source_order"),
            "unit_id": unit.get("unit_id"),
            "heading_path": heading_path,
            "detection_method": "heuristic_pattern",
        }
        headings.append(heading)
        heading_stack.append(heading)
        promoted += 1
        rewritten.append(
            {
                **unit,
                "kind": "heading",
                "heading_id": heading_id,
                "heading_path": heading_path,
                "outline_level": level,
                "detection_method": "heuristic_pattern",
            }
        )
    return rewritten, headings, promoted


def prepare_source_map(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    source_dir = project / "source"
    if not source_dir.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source_dir}")
    files = sorted(path for path in source_dir.rglob("*") if path.is_file() and path.name != ".gitkeep")
    if not files:
        raise FileNotFoundError(f"no source files found: {source_dir}")
    stage = project / SOURCE_MAP_STAGE
    stage.mkdir(parents=True, exist_ok=True)
    registry_sources: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    headings: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    issues: list[dict[str, str]] = []
    for path in files:
        relative = path.relative_to(project).as_posix()
        source_id = _source_id(relative)
        registry_sources.append(
            {
                "source_id": source_id,
                "path": relative,
                "file_name": path.name,
                "suffix": path.suffix.casefold(),
                "bytes": path.stat().st_size,
                "sha256": _sha256_path(path),
                "role": "primary" if len(files) == 1 else "registered",
                "authority": "unspecified",
                "version": "unclassified",
            }
        )
        try:
            source_units, source_headings, source_warnings = _extract_source(
                path,
                source_id=source_id,
                source_path=relative,
            )
        except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            issues.append(
                {
                    "code": "SOURCE_EXTRACTION_FAILED",
                    "message": f"{relative}: {exc}",
                }
            )
            continue
        if not source_units:
            issues.append(
                {
                    "code": "SOURCE_UNITS_MISSING",
                    "message": f"{relative} produced no source units.",
                }
            )
        elif not source_headings and path.suffix.casefold() in _HEADING_CAPABLE_SUFFIXES:
            substantive_units = [
                item
                for item in source_units
                if item.get("kind") in {"paragraph", "table_row", "caption"}
                and str(item.get("text") or "").strip()
            ]
            if len(substantive_units) >= _MIN_SUBSTANTIVE_UNITS_FOR_HEADING_CHECK:
                promoted_units, promoted_headings, promoted_count = _promote_heuristic_headings(
                    source_id, relative, source_units
                )
                if promoted_count:
                    source_units = promoted_units
                    source_headings = promoted_headings
                    warnings.append(
                        {
                            "code": "SOURCE_HEADINGS_HEURISTICALLY_DETECTED",
                            "message": (
                                f"{relative} 未使用 Word/Markdown 标题样式，但按编号模式"
                                f"（第X章/一、/（一）/1.1 等）识别出 {promoted_count} 个疑似标题；"
                                "这些标题不是原文样式声明的，请核对层级是否正确。"
                            ),
                        }
                    )
                else:
                    # A silent zero-heading extraction is worse than an error:
                    # every downstream stage that is supposed to preserve
                    # source-native chapter structure treats an empty
                    # required-heading list as "nothing to check" and passes
                    # vacuously. Surface this here, at the earliest point it
                    # can be diagnosed, instead of letting it resurface as an
                    # unexplained structure problem much later.
                    issues.append(
                        {
                            "code": "SOURCE_HEADINGS_NOT_DETECTED",
                            "message": (
                                f"{relative} 有 {len(substantive_units)} 段正文内容，但未识别出任何标题层级；"
                                "请确认标题是否使用了 Word 的标题段落样式（而不是仅加粗/放大字号），"
                                "或该源文件确实不含章节结构。"
                            ),
                        }
                    )
        units.extend(source_units)
        headings.extend(source_headings)
        warnings.extend(source_warnings)
    unit_ids = [str(item["unit_id"]) for item in units]
    heading_ids = [str(item["heading_id"]) for item in headings]
    if len(unit_ids) != len(set(unit_ids)):
        issues.append({"code": "SOURCE_UNIT_IDS_DUPLICATED", "message": "Source unit IDs must be unique."})
    if len(heading_ids) != len(set(heading_ids)):
        issues.append({"code": "SOURCE_HEADING_IDS_DUPLICATED", "message": "Source heading IDs must be unique."})
    known_heading_ids = set(heading_ids)
    for heading in headings:
        parent = heading.get("parent_heading_id")
        if parent and parent not in known_heading_ids:
            issues.append(
                {
                    "code": "SOURCE_HEADING_PARENT_UNKNOWN",
                    "message": f"Heading {heading['heading_id']} references missing parent {parent}.",
                }
            )
    registry = {"schema": REGISTRY_SCHEMA, "sources": registry_sources}
    heading_tree = {"schema": HEADING_TREE_SCHEMA, "headings": headings}
    registry_path = project / SOURCE_REGISTRY
    units_path = project / SOURCE_UNITS
    heading_path = project / SOURCE_HEADING_TREE
    _write_json(registry_path, registry)
    units_path.write_text(
        "".join(json.dumps(item, ensure_ascii=False, separators=(",", ":")) + "\n" for item in units),
        encoding="utf-8",
    )
    _write_json(heading_path, heading_tree)
    bundle_material = "\n".join(
        (
            _sha256_path(registry_path),
            _sha256_path(units_path),
            _sha256_path(heading_path),
        )
    )
    audit = {
        "schema": AUDIT_SCHEMA,
        "status": "passed" if not issues else "rewrite_required",
        "source_count": len(registry_sources),
        "heading_count": len(headings),
        "unit_count": len(units),
        "unit_kind_counts": {
            kind: sum(1 for item in units if item.get("kind") == kind)
            for kind in sorted({str(item.get("kind") or "") for item in units})
        },
        "source_registry_sha256": _sha256_path(registry_path),
        "source_units_sha256": _sha256_path(units_path),
        "source_heading_tree_sha256": _sha256_path(heading_path),
        "source_map_bundle_sha256": _sha256_bytes(bundle_material.encode("utf-8")),
        "issues": issues,
        "warnings": warnings,
        "audited_at": _utc_now(),
    }
    _write_json(project / SOURCE_MAP_AUDIT, audit)
    (project / SOURCE_MAP_MD).write_text(
        _render_source_map(registry, headings, units, audit),
        encoding="utf-8",
    )
    return {
        **audit,
        "source_registry": str(registry_path),
        "source_units": str(units_path),
        "source_heading_tree": str(heading_path),
        "source_map_markdown": str(project / SOURCE_MAP_MD),
        "source_map_audit": str(project / SOURCE_MAP_AUDIT),
        "sources": registry_sources,
        "headings": headings,
        "unit_ids": unit_ids,
    }


def run_source_map_audit(project: Path) -> tuple[int, dict[str, Any]]:
    report = prepare_source_map(project)
    return (0 if report["status"] == "passed" else 4), report


def load_source_units(project: Path) -> list[dict[str, Any]]:
    path = project.expanduser().resolve() / SOURCE_UNITS
    if not path.is_file():
        prepare_source_map(project)
    result: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            result.append(payload)
    return result


def render_units_for_model(
    project: Path,
    *,
    prepared: dict[str, Any] | None = None,
) -> list[tuple[dict[str, Any], str]]:
    prepared = prepared or prepare_source_map(project)
    units = load_source_units(project)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in units:
        grouped[str(item.get("source_id") or "")].append(item)
    rendered: list[tuple[dict[str, Any], str]] = []
    for source in prepared["sources"]:
        lines: list[str] = []
        for item in grouped.get(str(source["source_id"]), []):
            qualifiers = [f"kind={item.get('kind')}"]
            if item.get("heading_id"):
                qualifiers.append(f"heading={item['heading_id']}")
            if item.get("outline_level"):
                qualifiers.append(f"level={item['outline_level']}")
            lines.append(
                f"[{item['unit_id']}][{';'.join(qualifiers)}] {item.get('text', '')}".rstrip()
            )
        rendered.append((source, "\n".join(lines).rstrip() + "\n"))
    return rendered

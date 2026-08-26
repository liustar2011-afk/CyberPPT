from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

import fitz
from docx import Document
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from pptx import Presentation

from .utils import sha256_file, stable_hash, utc_now_iso, write_json


SUPPORTED_EXTENSIONS = {".docx", ".pdf", ".md", ".markdown", ".txt", ".pptx"}


@dataclass
class ExtractionResult:
    metadata: dict[str, Any]
    blocks: list[dict[str, Any]]


def _normalise_text(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _heading_level(style_name: str | None, text: str) -> int | None:
    style = (style_name or "").strip()
    patterns = [r"^Heading\s*(\d+)$", r"^标题\s*(\d+)$", r"^Title\s*(\d+)$"]
    for pattern in patterns:
        m = re.match(pattern, style, flags=re.I)
        if m:
            return max(1, min(9, int(m.group(1))))
    if style.lower() in {"title", "标题"}:
        return 1
    stripped = text.strip()
    if 0 < len(stripped) <= 40:
        if re.match(r"^(第[一二三四五六七八九十百]+[章节篇部分]|[一二三四五六七八九十]+、|\d+(?:\.\d+){0,3}[、.\s])", stripped):
            dots = re.match(r"^(\d+(?:\.\d+)*)", stripped)
            return min(6, (dots.group(1).count(".") + 1) if dots else 2)
    return None


def _iter_docx_blocks(parent: _Document | _Cell) -> Iterator[Paragraph | Table]:
    if isinstance(parent, _Document):
        parent_elm = parent.element.body
    elif isinstance(parent, _Cell):
        parent_elm = parent._tc
    else:
        raise ValueError("Unsupported parent")
    for child in parent_elm.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def extract_docx(path: Path) -> ExtractionResult:
    doc = Document(path)
    blocks: list[dict[str, Any]] = []
    section_stack: list[str] = []
    paragraph_index = 0
    table_index = 0

    for item in _iter_docx_blocks(doc):
        if isinstance(item, Paragraph):
            paragraph_index += 1
            text = _normalise_text(item.text)
            if not text:
                continue
            style_name = item.style.name if item.style is not None else ""
            level = _heading_level(style_name, text)
            if level is not None:
                section_stack = section_stack[: level - 1]
                while len(section_stack) < level - 1:
                    section_stack.append("")
                section_stack.append(text)
                kind = "heading"
            else:
                kind = "paragraph"
            blocks.append(
                {
                    "source_id": "",
                    "kind": kind,
                    "section_path": [s for s in section_stack if s],
                    "text": text,
                    "location": {"paragraph": paragraph_index},
                    "style": style_name,
                }
            )
        else:
            table_index += 1
            for row_index, row in enumerate(item.rows, start=1):
                cells = [_normalise_text(cell.text) for cell in row.cells]
                # python-docx may repeat merged cell contents; keep order but collapse exact consecutive repeats.
                collapsed: list[str] = []
                for cell in cells:
                    if cell and (not collapsed or collapsed[-1] != cell):
                        collapsed.append(cell)
                text = " | ".join(collapsed)
                if not text:
                    continue
                blocks.append(
                    {
                        "source_id": "",
                        "kind": "table_row",
                        "section_path": [s for s in section_stack if s],
                        "text": text,
                        "location": {"table": table_index, "row": row_index},
                        "style": "table",
                    }
                )

    return _finalise(path, blocks, "docx")


def extract_pdf(path: Path) -> ExtractionResult:
    doc = fitz.open(path)
    blocks: list[dict[str, Any]] = []
    for page_index, page in enumerate(doc, start=1):
        page_dict = page.get_text("dict", sort=True)
        page_blocks: list[tuple[float, float, str, float]] = []
        for block in page_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            lines: list[str] = []
            max_size = 0.0
            for line in block.get("lines", []):
                spans_text: list[str] = []
                for span in line.get("spans", []):
                    spans_text.append(span.get("text", ""))
                    max_size = max(max_size, float(span.get("size", 0.0)))
                line_text = _normalise_text("".join(spans_text))
                if line_text:
                    lines.append(line_text)
            text = _normalise_text("\n".join(lines))
            if text:
                bbox = block.get("bbox", [0, 0, 0, 0])
                page_blocks.append((float(bbox[1]), float(bbox[0]), text, max_size))
        page_blocks.sort(key=lambda x: (x[0], x[1]))
        if page_blocks:
            median_size = sorted([b[3] for b in page_blocks if b[3] > 0])[len([b for b in page_blocks if b[3] > 0]) // 2] if any(b[3] > 0 for b in page_blocks) else 0
        else:
            median_size = 0
        section_stack: list[str] = []
        for block_index, (_, _, text, max_size) in enumerate(page_blocks, start=1):
            is_heading = len(text) <= 60 and max_size >= (median_size * 1.18 if median_size else 999)
            if is_heading:
                section_stack = [text]
            blocks.append(
                {
                    "source_id": "",
                    "kind": "heading" if is_heading else "page_text",
                    "section_path": list(section_stack),
                    "text": text,
                    "location": {"page": page_index, "block": block_index},
                    "style": f"font_size:{max_size:.1f}" if max_size else "pdf_text",
                }
            )
    metadata_note = "" if blocks else "PDF未提取到可用文本；扫描版PDF需要先做OCR。"
    result = _finalise(path, blocks, "pdf")
    if metadata_note:
        result.metadata["warning"] = metadata_note
    return result


def extract_markdown(path: Path) -> ExtractionResult:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks: list[dict[str, Any]] = []
    section_stack: list[str] = []
    paragraph_lines: list[str] = []
    paragraph_start = 1

    def flush(current_line: int) -> None:
        nonlocal paragraph_lines, paragraph_start
        content = _normalise_text("\n".join(paragraph_lines))
        if content:
            blocks.append(
                {
                    "source_id": "",
                    "kind": "paragraph",
                    "section_path": [s for s in section_stack if s],
                    "text": content,
                    "location": {"line_start": paragraph_start, "line_end": current_line - 1},
                    "style": "markdown",
                }
            )
        paragraph_lines = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            flush(line_no)
            level = len(m.group(1))
            heading = _normalise_text(m.group(2))
            section_stack = section_stack[: level - 1]
            while len(section_stack) < level - 1:
                section_stack.append("")
            section_stack.append(heading)
            blocks.append(
                {
                    "source_id": "",
                    "kind": "heading",
                    "section_path": [s for s in section_stack if s],
                    "text": heading,
                    "location": {"line": line_no},
                    "style": f"heading_{level}",
                }
            )
            paragraph_start = line_no + 1
        elif not line.strip():
            flush(line_no + 1)
            paragraph_start = line_no + 1
        else:
            if not paragraph_lines:
                paragraph_start = line_no
            paragraph_lines.append(line)
    flush(len(text.splitlines()) + 1)
    return _finalise(path, blocks, "markdown")


def extract_txt(path: Path) -> ExtractionResult:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    blocks: list[dict[str, Any]] = []
    section_stack: list[str] = []
    for index, part in enumerate(re.split(r"\n\s*\n", text), start=1):
        content = _normalise_text(part)
        if not content:
            continue
        level = _heading_level("", content)
        if level is not None and "\n" not in content:
            section_stack = section_stack[: level - 1] + [content]
            kind = "heading"
        else:
            kind = "paragraph"
        blocks.append(
            {
                "source_id": "",
                "kind": kind,
                "section_path": [s for s in section_stack if s],
                "text": content,
                "location": {"block": index},
                "style": "plain_text",
            }
        )
    return _finalise(path, blocks, "txt")


def extract_pptx(path: Path) -> ExtractionResult:
    prs = Presentation(path)
    blocks: list[dict[str, Any]] = []
    for slide_index, slide in enumerate(prs.slides, start=1):
        title = ""
        if slide.shapes.title is not None and getattr(slide.shapes.title, "text", ""):
            title = _normalise_text(slide.shapes.title.text)
            blocks.append(
                {
                    "source_id": "",
                    "kind": "heading",
                    "section_path": [title],
                    "text": title,
                    "location": {"slide": slide_index, "shape": "title"},
                    "style": "ppt_title",
                }
            )
        for shape_index, shape in enumerate(slide.shapes, start=1):
            if shape is slide.shapes.title:
                continue
            if not hasattr(shape, "text"):
                continue
            text = _normalise_text(shape.text)
            if not text:
                continue
            blocks.append(
                {
                    "source_id": "",
                    "kind": "slide_text",
                    "section_path": [title] if title else [f"第{slide_index}页"],
                    "text": text,
                    "location": {"slide": slide_index, "shape": shape_index},
                    "style": "ppt_text",
                }
            )
    return _finalise(path, blocks, "pptx")


def _finalise(path: Path, blocks: list[dict[str, Any]], file_type: str) -> ExtractionResult:
    for index, block in enumerate(blocks, start=1):
        block["source_id"] = f"S{index:05d}"
    char_count = sum(len(block.get("text", "")) for block in blocks)
    metadata = {
        "file_name": path.name,
        "file_type": file_type,
        "sha256": sha256_file(path),
        "extracted_at": utc_now_iso(),
        "block_count": len(blocks),
        "character_count": char_count,
        "blocks_hash": stable_hash(blocks),
    }
    return ExtractionResult(metadata=metadata, blocks=blocks)


def extract_source(path: Path) -> ExtractionResult:
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"暂不支持 {suffix}；支持：{', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    if suffix == ".docx":
        return extract_docx(path)
    if suffix == ".pdf":
        return extract_pdf(path)
    if suffix in {".md", ".markdown"}:
        return extract_markdown(path)
    if suffix == ".txt":
        return extract_txt(path)
    if suffix == ".pptx":
        return extract_pptx(path)
    raise AssertionError("unreachable")


def save_extraction(result: ExtractionResult, workspace: Path) -> dict[str, Any]:
    source_dir = workspace / "source"
    source_dir.mkdir(parents=True, exist_ok=True)
    write_json(source_dir / "source_blocks.json", {"metadata": result.metadata, "blocks": result.blocks})
    lines = [f"# {result.metadata['file_name']}", ""]
    for block in result.blocks:
        location = json.dumps(block["location"], ensure_ascii=False, separators=(",", ":"))
        sections = " > ".join(block.get("section_path", []))
        lines.append(f"## [{block['source_id']}] {sections or block['kind']}")
        lines.append(f"位置：`{location}`")
        lines.append("")
        lines.append(block["text"])
        lines.append("")
    (source_dir / "source_readable.md").write_text("\n".join(lines), encoding="utf-8")
    return result.metadata


def chunk_blocks(blocks: list[dict[str, Any]], max_chars: int = 45000) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for block in blocks:
        block_chars = len(block.get("text", "")) + 200
        if current and current_chars + block_chars > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(block)
        current_chars += block_chars
    if current:
        chunks.append(current)
    return chunks

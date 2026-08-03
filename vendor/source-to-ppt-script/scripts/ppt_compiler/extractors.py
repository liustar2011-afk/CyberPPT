from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import fitz
from docx import Document
from docx.document import Document as _Document
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table, _Cell
from docx.text.paragraph import Paragraph
from pptx import Presentation

from .utils import now_iso, sha256_file, stable_hash, write_json

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
    for pattern in [r"^Heading\s*(\d+)$", r"^标题\s*(\d+)$", r"^Title\s*(\d+)$"]:
        m = re.match(pattern, style, flags=re.I)
        if m:
            return max(1, min(9, int(m.group(1))))
    if style.lower() in {"title", "标题"}:
        return 1
    stripped = text.strip()
    if 0 < len(stripped) <= 50 and re.match(
        r"^(第[一二三四五六七八九十百]+[章节篇部分]|[一二三四五六七八九十]+、|\d+(?:\.\d+){0,3}[、.\s])",
        stripped,
    ):
        dots = re.match(r"^(\d+(?:\.\d+)*)", stripped)
        return min(6, dots.group(1).count(".") + 1 if dots else 2)
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
            blocks.append({
                "source_id": "", "kind": kind, "section_path": [s for s in section_stack if s],
                "text": text, "location": {"paragraph": paragraph_index}, "style": style_name,
            })
        else:
            table_index += 1
            for row_index, row in enumerate(item.rows, start=1):
                cells = [_normalise_text(cell.text) for cell in row.cells]
                collapsed: list[str] = []
                for cell in cells:
                    if cell and (not collapsed or collapsed[-1] != cell):
                        collapsed.append(cell)
                text = " | ".join(collapsed)
                if text:
                    blocks.append({
                        "source_id": "", "kind": "table_row", "section_path": [s for s in section_stack if s],
                        "text": text, "location": {"table": table_index, "row": row_index}, "style": "table",
                    })
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
        sizes = sorted(b[3] for b in page_blocks if b[3] > 0)
        median_size = sizes[len(sizes) // 2] if sizes else 0
        section_stack: list[str] = []
        for block_index, (_, _, text, max_size) in enumerate(page_blocks, start=1):
            is_heading = len(text) <= 70 and bool(median_size) and max_size >= median_size * 1.18
            if is_heading:
                section_stack = [text]
            blocks.append({
                "source_id": "", "kind": "heading" if is_heading else "page_text",
                "section_path": list(section_stack), "text": text,
                "location": {"page": page_index, "block": block_index},
                "style": f"font_size:{max_size:.1f}" if max_size else "pdf_text",
            })
    result = _finalise(path, blocks, "pdf")
    if not blocks:
        result.metadata["warning"] = "PDF未提取到可用文本；可能是扫描件，需要另行OCR或视觉读取。"
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
            blocks.append({
                "source_id": "", "kind": "paragraph", "section_path": [s for s in section_stack if s],
                "text": content, "location": {"line_start": paragraph_start, "line_end": current_line - 1},
                "style": "markdown",
            })
        paragraph_lines = []

    lines = text.splitlines()
    for line_no, line in enumerate(lines, start=1):
        m = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if m:
            flush(line_no)
            level = len(m.group(1))
            heading = _normalise_text(m.group(2))
            section_stack = section_stack[: level - 1]
            while len(section_stack) < level - 1:
                section_stack.append("")
            section_stack.append(heading)
            blocks.append({
                "source_id": "", "kind": "heading", "section_path": [s for s in section_stack if s],
                "text": heading, "location": {"line": line_no}, "style": f"heading_{level}",
            })
            paragraph_start = line_no + 1
        elif not line.strip():
            flush(line_no + 1)
            paragraph_start = line_no + 1
        else:
            if not paragraph_lines:
                paragraph_start = line_no
            paragraph_lines.append(line)
    flush(len(lines) + 1)
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
        blocks.append({
            "source_id": "", "kind": kind, "section_path": [s for s in section_stack if s],
            "text": content, "location": {"block": index}, "style": "plain_text",
        })
    return _finalise(path, blocks, "txt")


def extract_pptx(path: Path) -> ExtractionResult:
    prs = Presentation(path)
    blocks: list[dict[str, Any]] = []
    for slide_index, slide in enumerate(prs.slides, start=1):
        title = ""
        if slide.shapes.title is not None and getattr(slide.shapes.title, "text", ""):
            title = _normalise_text(slide.shapes.title.text)
            if title:
                blocks.append({
                    "source_id": "", "kind": "heading", "section_path": [title], "text": title,
                    "location": {"slide": slide_index, "shape": "title"}, "style": "ppt_title",
                })
        for shape_index, shape in enumerate(slide.shapes, start=1):
            if shape is slide.shapes.title:
                continue
            if getattr(shape, "has_table", False):
                for row_index, row in enumerate(shape.table.rows, start=1):
                    cells = [_normalise_text(cell.text) for cell in row.cells]
                    text = " | ".join(cell for cell in cells if cell)
                    if text:
                        blocks.append({
                            "source_id": "", "kind": "table_row", "section_path": [title] if title else [f"第{slide_index}页"],
                            "text": text, "location": {"slide": slide_index, "shape": shape_index, "row": row_index},
                            "style": "ppt_table",
                        })
                continue
            if hasattr(shape, "text"):
                text = _normalise_text(shape.text)
                if text:
                    blocks.append({
                        "source_id": "", "kind": "slide_text", "section_path": [title] if title else [f"第{slide_index}页"],
                        "text": text, "location": {"slide": slide_index, "shape": shape_index}, "style": "ppt_text",
                    })
        try:
            notes_text = _normalise_text(slide.notes_slide.notes_text_frame.text)
        except Exception:
            notes_text = ""
        if notes_text:
            blocks.append({
                "source_id": "", "kind": "speaker_notes", "section_path": [title] if title else [f"第{slide_index}页"],
                "text": notes_text, "location": {"slide": slide_index, "notes": True}, "style": "ppt_notes",
            })
    return _finalise(path, blocks, "pptx")


def _finalise(path: Path, blocks: list[dict[str, Any]], file_type: str) -> ExtractionResult:
    for index, block in enumerate(blocks, start=1):
        block["source_id"] = f"S{index:05d}"
    metadata = {
        "file_name": path.name, "file_type": file_type, "sha256": sha256_file(path),
        "extracted_at": now_iso(), "block_count": len(blocks),
        "character_count": sum(len(block.get("text", "")) for block in blocks),
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


def _write_readable(path: Path, metadata: dict[str, Any], blocks: list[dict[str, Any]]) -> None:
    lines = ["# 源材料索引", ""]
    for doc in metadata.get("documents", []):
        lines.extend([f"## {doc['document_id']}｜{doc['file_name']}", ""])
        for block in [b for b in blocks if b.get("document_id") == doc["document_id"]]:
            location = json.dumps(block["location"], ensure_ascii=False, separators=(",", ":"))
            sections = " > ".join(block.get("section_path", []))
            lines.append(f"### [{block['source_id']}] {sections or block['kind']}")
            lines.append(f"位置：`{location}`")
            lines.append("")
            lines.append(block.get("text", ""))
            lines.append("")
    path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def chunk_blocks(blocks: list[dict[str, Any]], max_chars: int) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0
    for block in blocks:
        size = len(block.get("text", "")) + 120
        if current and current_chars + size > max_chars:
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(block)
        current_chars += size
    if current:
        chunks.append(current)
    return chunks


def initialise_project(source_paths: list[Path], project_dir: Path, profile_path: Path, force: bool = False) -> dict[str, Any]:
    if project_dir.exists() and any(project_dir.iterdir()):
        if not force:
            raise FileExistsError(f"项目目录非空：{project_dir}；使用 --force 重新初始化。")
        # 项目目录由本工具管理。强制初始化时清理旧的阶段文件、锁和导出物，
        # 避免旧分块或旧锁被误认为属于新的源材料。
        managed_paths = [
            "source", "stages", "reports", "exports", "config",
            "project.json", ".ppt-script-skill-state.json",
        ]
        for rel in managed_paths:
            target = project_dir / rel
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
    project_dir.mkdir(parents=True, exist_ok=True)
    for rel in ["source/original", "source/chunks", "stages/chunks", "reports", "exports", "config"]:
        (project_dir / rel).mkdir(parents=True, exist_ok=True)
    shutil.copy2(profile_path, project_dir / "config/project.yaml")

    all_blocks: list[dict[str, Any]] = []
    documents: list[dict[str, Any]] = []
    for doc_index, source in enumerate(source_paths, start=1):
        source = source.resolve()
        if not source.exists():
            raise FileNotFoundError(source)
        document_id = f"D{doc_index:02d}"
        destination = project_dir / "source/original" / f"{document_id}_{source.name}"
        shutil.copy2(source, destination)
        result = extract_source(destination)
        document_meta = dict(result.metadata)
        document_meta["document_id"] = document_id
        document_meta["original_path"] = destination.relative_to(project_dir).as_posix()
        documents.append(document_meta)
        for block in result.blocks:
            cloned = dict(block)
            cloned["source_id"] = f"{document_id}-{block['source_id']}"
            cloned["document_id"] = document_id
            cloned["file_name"] = source.name
            all_blocks.append(cloned)

    metadata = {
        "created_at": now_iso(), "documents": documents, "document_count": len(documents),
        "block_count": len(all_blocks), "character_count": sum(len(b.get("text", "")) for b in all_blocks),
        "blocks_hash": stable_hash(all_blocks),
    }
    write_json(project_dir / "source/source_blocks.json", {"metadata": metadata, "blocks": all_blocks})
    _write_readable(project_dir / "source/source_readable.md", metadata, all_blocks)

    import yaml
    profile = yaml.safe_load((project_dir / "config/project.yaml").read_text(encoding="utf-8")) or {}
    max_chars = int(profile.get("chunking", {}).get("chunk_character_limit", 36000))
    chunks = chunk_blocks(all_blocks, max_chars=max_chars)
    chunk_entries: list[dict[str, Any]] = []
    for index, chunk in enumerate(chunks, start=1):
        json_path = project_dir / f"source/chunks/chunk_{index:03d}.json"
        md_path = project_dir / f"source/chunks/chunk_{index:03d}.md"
        write_json(json_path, {"chunk_index": index, "chunk_count": len(chunks), "blocks": chunk})
        _write_readable(md_path, {"documents": documents}, chunk)
        chunk_entries.append({
            "chunk_index": index, "json": json_path.relative_to(project_dir).as_posix(),
            "markdown": md_path.relative_to(project_dir).as_posix(),
            "source_ids": [b["source_id"] for b in chunk],
            "character_count": sum(len(b.get("text", "")) for b in chunk),
        })
    metadata["chunk_count"] = len(chunks)
    metadata["chunks"] = chunk_entries
    write_json(project_dir / "source/source_blocks.json", {"metadata": metadata, "blocks": all_blocks})
    write_json(project_dir / "project.json", {
        "format_version": "1.0", "created_at": now_iso(), "profile": "config/project.yaml",
        "source": "source/source_blocks.json", "stages": {},
    })
    return metadata

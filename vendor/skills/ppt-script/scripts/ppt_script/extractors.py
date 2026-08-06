from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_HEADING_MARKER = "【原文标题】"
_HEADING_STYLE_RE = re.compile(r"^(heading|title|标题)", re.IGNORECASE)
_MARKDOWN_HEADING_RE = re.compile(r"(?m)^#{1,6}\s+(.+?)\s*$")
_TAGGED_HEADING_RE = re.compile(re.escape(_HEADING_MARKER) + r"(.+)")


@dataclass(slots=True)
class SourceBundle:
    text: str
    file_names: list[str]
    unsupported_files: list[str]
    low_quality_files: list[str]
    original_titles: list[str]


def extract_original_titles(text: str) -> list[str]:
    """Collect headings the source material already provides, tagged during extraction
    (DOCX heading styles, PPTX slide titles) or written as Markdown headings, so downstream
    stages can reuse the material's own government/SOE-style titles instead of inventing new
    ones from body text."""
    titles: list[str] = []
    seen: set[str] = set()
    for pattern in (_TAGGED_HEADING_RE, _MARKDOWN_HEADING_RE):
        for match in pattern.finditer(text):
            title = match.group(1).strip()
            if title and title not in seen:
                seen.add(title)
                titles.append(title)
    return titles


def _iter_docx_blocks(parent):
    from docx.oxml.table import CT_Tbl
    from docx.oxml.text.paragraph import CT_P
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in parent.element.body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _is_heading_paragraph(paragraph) -> bool:
    style = getattr(paragraph, "style", None)
    name = getattr(style, "name", "") or ""
    return bool(_HEADING_STYLE_RE.match(name.strip()))


def _extract_docx(path: Path) -> str:
    from docx import Document
    from docx.table import Table

    document = Document(path)
    parts: list[str] = []
    for block in _iter_docx_blocks(document):
        if isinstance(block, Table):
            for row in block.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        else:
            text = block.text.strip()
            if not text:
                continue
            parts.append(f"{_HEADING_MARKER}{text}" if _is_heading_paragraph(block) else text)
    return "\n".join(parts)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    presentation = Presentation(path)
    parts: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        parts.append(f"[PPT第{index}页]")
        title_shape = slide.shapes.title
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = shape.text.strip()
                if not text:
                    continue
                is_title = title_shape is not None and shape.shape_id == title_shape.shape_id
                parts.append(f"{_HEADING_MARKER}{text}" if is_title else text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
    return "\n".join(parts)


_PDF_MIN_AVG_CHARS_PER_PAGE = 80
_PDF_MAX_EMPTY_PAGE_RATIO = 0.25


def _extract_pdf(path: Path) -> tuple[str, bool]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    page_texts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        page_texts.append(text)
        if text:
            parts.append(f"[PDF第{index}页]\n{text}")
    page_count = len(page_texts) or 1
    avg_chars = sum(len(text) for text in page_texts) / page_count
    empty_ratio = sum(1 for text in page_texts if not text) / page_count
    ocr_suspect = avg_chars < _PDF_MIN_AVG_CHARS_PER_PAGE or empty_ratio > _PDF_MAX_EMPTY_PAGE_RATIO
    return "\n".join(parts), ocr_suspect


def extract_text(path: str | Path) -> str:
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"File not found: {source}")
    suffix = source.suffix.lower()
    if suffix in {".md", ".markdown", ".txt", ".csv", ".json", ".yaml", ".yml"}:
        return source.read_text(encoding="utf-8-sig")
    if suffix == ".docx":
        return _extract_docx(source)
    if suffix == ".pptx":
        return _extract_pptx(source)
    if suffix == ".pdf":
        text, _ = _extract_pdf(source)
        return text
    raise ValueError(f"Unsupported file type: {suffix or '<none>'}")


def extract_project_sources(project_path: str | Path) -> SourceBundle:
    project = Path(project_path)
    source_dir = project / "source"
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    parts: list[str] = []
    names: list[str] = []
    unsupported: list[str] = []
    low_quality: list[str] = []
    for path in sorted(item for item in source_dir.rglob("*") if item.is_file()):
        relative_name = path.relative_to(source_dir).as_posix()
        if path.suffix.lower() == ".pdf":
            try:
                text, ocr_suspect = _extract_pdf(path)
            except ValueError:
                unsupported.append(relative_name)
                continue
            if ocr_suspect:
                low_quality.append(relative_name)
        else:
            try:
                text = extract_text(path)
            except ValueError:
                unsupported.append(relative_name)
                continue
        names.append(relative_name)
        parts.append(f"[来源文件：{relative_name}]\n{text}")
    full_text = "\n\n".join(parts)
    return SourceBundle(
        text=full_text,
        file_names=names,
        unsupported_files=unsupported,
        low_quality_files=low_quality,
        original_titles=extract_original_titles(full_text),
    )

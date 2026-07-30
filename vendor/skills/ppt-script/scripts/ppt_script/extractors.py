from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class SourceBundle:
    text: str
    file_names: list[str]
    unsupported_files: list[str]


def _extract_docx(path: Path) -> str:
    from docx import Document

    document = Document(path)
    parts = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                parts.append(" | ".join(cells))
    return "\n".join(parts)


def _extract_pptx(path: Path) -> str:
    from pptx import Presentation

    presentation = Presentation(path)
    parts: list[str] = []
    for index, slide in enumerate(presentation.slides, start=1):
        parts.append(f"[PPT第{index}页]")
        for shape in slide.shapes:
            if getattr(shape, "has_text_frame", False):
                text = shape.text.strip()
                if text:
                    parts.append(text)
            if getattr(shape, "has_table", False):
                for row in shape.table.rows:
                    cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if cells:
                        parts.append(" | ".join(cells))
    return "\n".join(parts)


def _extract_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            parts.append(f"[PDF第{index}页]\n{text.strip()}")
    return "\n".join(parts)


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
        return _extract_pdf(source)
    raise ValueError(f"Unsupported file type: {suffix or '<none>'}")


def extract_project_sources(project_path: str | Path) -> SourceBundle:
    project = Path(project_path)
    source_dir = project / "source"
    if not source_dir.exists():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")
    parts: list[str] = []
    names: list[str] = []
    unsupported: list[str] = []
    for path in sorted(item for item in source_dir.iterdir() if item.is_file()):
        try:
            text = extract_text(path)
        except ValueError:
            unsupported.append(path.name)
            continue
        names.append(path.name)
        parts.append(f"[来源文件：{path.name}]\n{text}")
    return SourceBundle(text="\n\n".join(parts), file_names=names, unsupported_files=unsupported)

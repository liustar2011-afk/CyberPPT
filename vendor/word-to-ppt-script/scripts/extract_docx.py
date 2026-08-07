#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

from docx import Document
from docx.document import Document as _Document
from docx.table import Table
from docx.text.paragraph import Paragraph


def iter_block_items(parent: _Document) -> Iterable[Paragraph | Table]:
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag.endswith('}p'):
            yield Paragraph(child, parent)
        elif child.tag.endswith('}tbl'):
            yield Table(child, parent)


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def heading_level(paragraph: Paragraph) -> int | None:
    name = (paragraph.style.name or "").lower()
    m = re.search(r"(?:heading|标题)\s*([1-9])", name)
    if m:
        return int(m.group(1))
    return None


def extract(path: Path) -> str:
    doc = Document(str(path))
    lines = [f"# 规范化源文：{path.name}", ""]
    paragraph_no = 0
    table_no = 0
    for block in iter_block_items(doc):
        if isinstance(block, Paragraph):
            text = clean(block.text)
            if not text:
                continue
            paragraph_no += 1
            sid = f"SRC-P{paragraph_no:04d}"
            level = heading_level(block)
            if level:
                lines.extend([f"{'#' * min(level + 1, 6)} {text}", f"> Source ID: `{sid}`", ""])
            else:
                lines.extend([f"[{sid}] {text}", ""])
        else:
            table_no += 1
            lines.extend([f"## 表格 {table_no}", f"> Source ID: `SRC-T{table_no:04d}`", ""])
            rows = []
            for r_idx, row in enumerate(block.rows, 1):
                values = [clean(cell.text).replace("|", "\\|") for cell in row.cells]
                rows.append((r_idx, values))
            width = max((len(v) for _, v in rows), default=0)
            if width:
                header = [f"列{i}" for i in range(1, width + 1)]
                lines.append("| " + " | ".join(header) + " |")
                lines.append("|" + "---|" * width)
                for r_idx, vals in rows:
                    vals += [""] * (width - len(vals))
                    lines.append("| " + " | ".join(vals) + f" | <!-- SRC-T{table_no:04d}-R{r_idx:03d} -->")
                lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract DOCX into source-ID-normalized Markdown")
    parser.add_argument("source", type=Path)
    parser.add_argument("-o", "--output", type=Path, required=True)
    args = parser.parse_args()
    if not args.source.exists():
        parser.error(f"source not found: {args.source}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(extract(args.source), encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

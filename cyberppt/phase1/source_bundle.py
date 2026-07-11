"""Convert normalized source extracts into stable, groundable source units."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from cyberppt.phase1.artifacts import Phase1Paths


_HEADING_RE = re.compile(r"^#{1,6}\s*(?P<title>.+?)\s*$")
_PAGE_LOCATOR_RE = re.compile(r"\b(?:P|T)\d+\b", re.IGNORECASE)
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9_.])\d+(?:\.\d+)?")


@dataclass(frozen=True)
class SourceUnit:
    unit_id: str
    kind: str
    text: str
    source_path: str
    locator: str
    numbers: tuple[str, ...]


@dataclass(frozen=True)
class SourceChunk:
    chunk_id: str
    unit_ids: tuple[str, ...]
    character_count: int


@dataclass(frozen=True)
class SourceBundle:
    source_path: str
    source_sha256: str
    units: tuple[SourceUnit, ...]
    chunks: tuple[SourceChunk, ...]


def _input_text(source: Path) -> tuple[Path, str]:
    resolved = source.expanduser().resolve()
    if resolved.suffix.lower() == ".json":
        sibling = resolved.with_suffix(".md")
        if sibling.is_file():
            resolved = sibling
        else:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
            return resolved, json.dumps(payload, ensure_ascii=False, indent=2)
    return resolved, resolved.read_text(encoding="utf-8-sig")


def _blocks(text: str) -> list[tuple[int, list[str]]]:
    lines = text.splitlines()
    raw: list[tuple[int, list[str]]] = []
    current: list[str] = []
    start = 1
    for line_number, line in enumerate(lines, start=1):
        if line.strip():
            if not current:
                start = line_number
            current.append(line.rstrip())
        elif current:
            raw.append((start, current))
            current = []
    if current:
        raw.append((start, current))

    merged: list[tuple[int, list[str]]] = []
    index = 0
    while index < len(raw):
        start, block = raw[index]
        if len(block) == 1 and _HEADING_RE.match(block[0]) and index + 1 < len(raw):
            next_start, next_block = raw[index + 1]
            merged.append((start, block + next_block))
            index += 2
            continue
        merged.append((start, block))
        index += 1
    return merged


def _locator(block: list[str], current_heading: str, start_line: int) -> str:
    text = "\n".join(block)
    page = _PAGE_LOCATOR_RE.search(text)
    if page:
        return page.group(0).upper()
    headings = [_HEADING_RE.match(line) for line in block]
    for match in headings:
        if match:
            return match.group("title").strip()
    return current_heading or f"line {start_line}"


def _kind(block: list[str]) -> str:
    table_lines = sum(1 for line in block if "|" in line)
    if table_lines >= 2:
        return "table"
    if block and _HEADING_RE.match(block[0]) and len(block) == 1:
        return "heading"
    return "paragraph"


def _chunks(units: list[SourceUnit], max_chunk_chars: int) -> tuple[SourceChunk, ...]:
    if max_chunk_chars <= 0:
        raise ValueError("max_chunk_chars must be positive")
    chunks: list[SourceChunk] = []
    current_ids: list[str] = []
    current_size = 0
    for unit in units:
        size = len(unit.text)
        if current_ids and current_size + size > max_chunk_chars:
            chunks.append(SourceChunk(f"C{len(chunks) + 1:03d}", tuple(current_ids), current_size))
            current_ids = []
            current_size = 0
        current_ids.append(unit.unit_id)
        current_size += size
    if current_ids:
        chunks.append(SourceChunk(f"C{len(chunks) + 1:03d}", tuple(current_ids), current_size))
    return tuple(chunks)


def build_source_bundle(source: Path, *, max_chunk_chars: int = 40000) -> SourceBundle:
    resolved, text = _input_text(source)
    units: list[SourceUnit] = []
    current_heading = ""
    for index, (start_line, block) in enumerate(_blocks(text), start=1):
        heading = _HEADING_RE.match(block[0]) if block else None
        if heading:
            current_heading = heading.group("title").strip()
        value = "\n".join(block).strip()
        units.append(
            SourceUnit(
                unit_id=f"U{index:04d}",
                kind=_kind(block),
                text=value,
                source_path=str(resolved),
                locator=_locator(block, current_heading, start_line),
                numbers=tuple(_NUMBER_RE.findall(value)),
            )
        )
    source_bytes = resolved.read_bytes()
    return SourceBundle(
        source_path=str(resolved),
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
        units=tuple(units),
        chunks=_chunks(units, max_chunk_chars),
    )


def write_source_bundle(bundle: SourceBundle, paths: Phase1Paths) -> tuple[Path, Path]:
    unit_by_id = {unit.unit_id: unit for unit in bundle.units}
    payload = {
        "schema": "cyberppt.phase1_source_bundle.v1",
        "source_path": bundle.source_path,
        "source_sha256": bundle.source_sha256,
        "units": [asdict(unit) for unit in bundle.units],
        "chunks": [asdict(chunk) for chunk in bundle.chunks],
    }
    paths.source_bundle_json.parent.mkdir(parents=True, exist_ok=True)
    paths.source_bundle_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    markdown: list[str] = ["# Stage 1 Source Bundle", "", f"- source: `{bundle.source_path}`", f"- sha256: `{bundle.source_sha256}`", ""]
    for unit in bundle.units:
        markdown.extend(
            [
                f"## {unit.unit_id} | {unit.kind} | {unit.locator}",
                f"numbers: {', '.join(unit.numbers) or 'none'}",
                "",
                unit.text,
                "",
            ]
        )
    paths.source_bundle_markdown.write_text("\n".join(markdown), encoding="utf-8")

    for chunk in bundle.chunks:
        chunk_payload = {
            "schema": "cyberppt.phase1_source_chunk.v1",
            "chunk_id": chunk.chunk_id,
            "unit_ids": list(chunk.unit_ids),
            "character_count": chunk.character_count,
            "units": [asdict(unit_by_id[unit_id]) for unit_id in chunk.unit_ids],
        }
        (paths.chunks_dir / f"chunk_{int(chunk.chunk_id[1:]):03d}.json").write_text(
            json.dumps(chunk_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return paths.source_bundle_json, paths.source_bundle_markdown

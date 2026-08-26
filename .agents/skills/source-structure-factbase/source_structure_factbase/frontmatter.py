from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FrontMatterResult:
    metadata: dict[str, Any]
    body: str
    body_start_line: int
    warnings: list[dict[str, str]]


def _parse_scalar(raw: str) -> Any:
    value = raw.strip()
    if not value:
        return ""
    if value in {"null", "Null", "NULL", "~"}:
        return None
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith(('"', "'")) and value.endswith(value[0]) and len(value) >= 2:
        if value[0] == '"':
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        return value[1:-1]
    try:
        return int(value)
    except ValueError:
        pass
    try:
        return float(value)
    except ValueError:
        return value


def _fallback_metadata(name: str) -> dict[str, Any]:
    suffix = Path(name).suffix.lower()
    return {
        "source_file": Path(name).name,
        "source_format": suffix,
        "conversion_engine": "unknown",
        "ocr_requested": False,
    }


def parse_front_matter(text: str, fallback_name: str) -> FrontMatterResult:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---":
        return FrontMatterResult(
            metadata=_fallback_metadata(fallback_name),
            body=text,
            body_start_line=1,
            warnings=[{
                "code": "missing_provenance_front_matter",
                "severity": "warning",
                "message": "Markdown has no provenance front matter; fallback source metadata was used.",
            }],
        )

    closing = None
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            closing = index
            break
    if closing is None:
        return FrontMatterResult(
            metadata=_fallback_metadata(fallback_name),
            body=text,
            body_start_line=1,
            warnings=[{
                "code": "unclosed_provenance_front_matter",
                "severity": "warning",
                "message": "Opening provenance front matter delimiter has no closing delimiter; content was treated as source body.",
            }],
        )

    metadata: dict[str, Any] = {}
    for raw_line in lines[1:closing]:
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        if key:
            metadata[key] = _parse_scalar(raw_value)

    body = "".join(lines[closing + 1 :])
    return FrontMatterResult(
        metadata=metadata,
        body=body,
        body_start_line=closing + 2,
        warnings=[],
    )

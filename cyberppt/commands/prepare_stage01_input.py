"""Compile deterministic Stage 01 authoring inputs."""

from __future__ import annotations

import json
from pathlib import Path


def _load(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact root must be an object: {path}")
    return payload


def _records(project: Path) -> dict[str, dict[str, object]]:
    truth = _load(project / "workbench/stages/01-analysis/source-truth.json")
    return {
        str(item.get("id")): item
        for item in truth.get("records", [])
        if isinstance(item, dict) and item.get("id")
    }


def prepare_outline_input(project: Path) -> Path:
    project = project.expanduser().resolve()
    outline = _load(project / "workbench/stages/01-analysis/outline.json")
    records = _records(project)
    lines = ["# Outline authoring input", "", "Use only assigned evidence.", ""]
    for page in outline.get("pages", []):
        if not isinstance(page, dict) or page.get("page_type") != "content":
            continue
        lines += [
            f"## {page.get('page_id')} {page.get('title')}",
            f"- Page job: {page.get('page_job', '')}",
            f"- Business question: {page.get('business_question', '')}",
            f"- New value: {page.get('new_value_vs_previous', '')}",
            f"- Reserved for later: {page.get('reserved_for_later', '')}",
            "- Evidence:",
        ]
        for source_id in page.get("source_refs", []):
            record = records.get(str(source_id), {})
            lines.append(f"  - {source_id} [{record.get('status', '')}]: {record.get('statement', '')}")
        lines.append("")
    output = project / "workbench/stages/01-analysis/outline-authoring-input.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def prepare_page_script_input(project: Path, page_id: str = "") -> Path:
    project = project.expanduser().resolve()
    outline = _load(project / "workbench/stages/01-analysis/outline.json")
    records = _records(project)
    pages = [
        item for item in outline.get("pages", [])
        if isinstance(item, dict)
        and item.get("page_type") == "content"
        and (not page_id or item.get("page_id") == page_id)
    ]
    if page_id and not pages:
        raise ValueError(f"content page not found: {page_id}")
    lines = ["# Page script authoring input", "", "Write full prose first; derive on-screen text from it.", ""]
    for page in pages:
        lines += [
            f"## {page.get('page_id')} {page.get('title')}",
            f"- Page job: {page.get('page_job', '')}",
            f"- Business question: {page.get('business_question', '')}",
            f"- Main message: {page.get('main_message', '')}",
            f"- New value versus previous: {page.get('new_value_vs_previous', '')}",
            f"- Reserved for later: {page.get('reserved_for_later', '')}",
            "- Proof points:",
        ]
        for point in page.get("proof_points", []):
            if isinstance(point, dict):
                refs = ", ".join(str(item) for item in point.get("source_refs", []))
                lines.append(f"  - [{point.get('consumption', 'supporting')}] {point.get('claim', '')} ({refs})")
        lines.append("- Evidence text:")
        for source_id in page.get("source_refs", []):
            lines.append(f"  - {source_id}: {records.get(str(source_id), {}).get('statement', '')}")
        lines.append("")
    suffix = f"-{page_id}" if page_id else ""
    output = project / "workbench/scripts" / f"page-script-authoring-input{suffix}.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output

"""Assemble a clean final manuscript from draft batch scripts."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from cyberppt.script_quality_contract import (
    PAGE_HEADING_RE,
    audit_final_manuscript_form,
    parse_script_markdown,
)

PAGE_START_RE = re.compile(r"^##\s+第(\d+)页[：:]", re.MULTILINE)
DRAFT_NOISE_RE = re.compile(
    r"^(?:"
    r"#\s+.*草稿|"
    r"#\s+第\s*\d+\s*[—\-~～－]+\s*\d+\s*页|"
    r">\s*批次\s*[：:]|"
    r">\s*状态\s*[：:].*草稿|"
    r".*待\s*`?script-audit`?\s*通过后审稿"
    r")"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _extract_pages(text: str) -> dict[int, str]:
    matches = list(PAGE_START_RE.finditer(text))
    pages: dict[int, str] = {}
    for index, match in enumerate(matches):
        number = int(match.group(1))
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end]
        # Drop trailing batch banners after the page body.
        block = re.split(r"\n(?=#\s+第\d+\s*[—\-])", block, maxsplit=1)[0]
        cleaned: list[str] = []
        for line in block.splitlines():
            if DRAFT_NOISE_RE.match(line.strip()):
                continue
            cleaned.append(line)
        pages[number] = "\n".join(cleaned).rstrip() + "\n"
    return pages


def _collect_draft_pages(drafts_dir: Path) -> dict[int, str]:
    if not drafts_dir.exists():
        raise FileNotFoundError(f"drafts directory does not exist: {drafts_dir}")
    pages: dict[int, str] = {}
    sources: dict[int, str] = {}
    for path in sorted(drafts_dir.glob("*.md")):
        extracted = _extract_pages(path.read_text(encoding="utf-8-sig"))
        for number, block in extracted.items():
            pages[number] = block
            sources[number] = str(path)
    if not pages:
        raise ValueError(f"no page headings found under {drafts_dir}")
    return pages


def _merge_missing_enrichments(
    pages: dict[int, str],
    enrichment_source: Path | None,
) -> dict[int, str]:
    if enrichment_source is None:
        return pages
    enrichments = _extract_pages(
        enrichment_source.expanduser().resolve().read_text(encoding="utf-8-sig")
    )
    merged = dict(pages)
    for number, block in pages.items():
        source_block = enrichments.get(number, "")
        visual_line = next(
            (
                line
                for line in source_block.splitlines()
                if line.startswith("- 视觉结构：")
            ),
            "",
        )
        marker = "- 讲解提示："
        if visual_line and "- 视觉结构：" not in block:
            block = (
                block.replace(marker, f"{visual_line}\n{marker}", 1)
                if marker in block
                else block.rstrip() + f"\n{visual_line}\n"
            )
        if "【演讲者备注】" not in block and "【演讲者备注】" in source_block:
            notes = source_block.split("【演讲者备注】", 1)[1].strip()
            block = block.rstrip() + f"\n【演讲者备注】\n\n{notes}\n"
        merged[number] = block
    return merged


def assemble_final_script(
    project: Path,
    drafts_dir: Path | None = None,
    output_path: Path | None = None,
    title: str = "",
    enrichment_source: Path | None = None,
) -> dict[str, object]:
    """Merge draft batches into a clean final manuscript under scripts/final/."""

    project = project.expanduser().resolve()
    if not project.exists():
        raise FileNotFoundError(f"project does not exist: {project}")
    drafts = (
        drafts_dir.expanduser().resolve()
        if drafts_dir is not None
        else project / "workbench" / "scripts" / "drafts"
    )
    output = (
        output_path.expanduser().resolve()
        if output_path is not None
        else project / "workbench" / "scripts" / "final" / "script-final.md"
    )
    pages = _merge_missing_enrichments(
        _collect_draft_pages(drafts),
        enrichment_source,
    )
    numbers = sorted(pages)
    expected = list(range(numbers[0], numbers[0] + len(numbers)))
    if numbers != expected:
        raise ValueError(
            f"assembled pages are not continuous: {numbers}; expected {expected}"
        )

    doc_title = title.strip() or "最终全稿脚本"
    first = numbers[0]
    last = numbers[-1]
    header = (
        f"# {doc_title}\n\n"
        f"> 项目：`{project.name}`\n"
        f"> 页数：{len(numbers)}（p{first:02d}–p{last:02d}）\n"
        f"> 状态：**最终全稿**\n"
        f"> 来源：`workbench/scripts/drafts/` 合稿\n"
        f"> 下一步：`python -m cyberppt script-audit {project} --input {output}`\n\n"
        "---\n\n"
    )
    body = "\n".join(pages[number] for number in numbers)
    text = header + body
    if not text.endswith("\n"):
        text += "\n"

    form_issues = audit_final_manuscript_form(text)
    if form_issues:
        raise ValueError(
            "assembled manuscript still contains draft/batch banners: "
            + "; ".join(form_issues[0].evidence)
        )

    # Ensure parseable before write.
    parse_script_markdown(text)
    if not PAGE_HEADING_RE.search(text):
        raise ValueError("assembled manuscript has no page headings")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8")

    ledger_path = project / "workbench" / "artifact-ledger.json"
    if ledger_path.exists():
        ledger = json.loads(ledger_path.read_text(encoding="utf-8-sig"))
        artifacts = [
            item
            for item in ledger.get("artifacts", [])
            if isinstance(item, dict) and item.get("id") != "script-final"
        ]
        artifacts.append(
            {
                "id": "script-final",
                "stage": "01-analysis",
                "page": None,
                "path": str(output.relative_to(project)).replace("\\", "/"),
                "status": "assembled_awaiting_audit",
                "depends_on": ["workbench/scripts/drafts"],
                "supersedes": [],
                "resume_command": (
                    f"python -m cyberppt script-audit {project} --input {output}"
                ),
                "sha256": _sha256(output),
            }
        )
        ledger["artifacts"] = artifacts
        ledger_path.write_text(
            json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "schema": "cyberppt.assemble_final_script.v1",
        "project": str(project),
        "output": str(output),
        "page_count": len(numbers),
        "first_page": f"p{first:02d}",
        "last_page": f"p{last:02d}",
        "sha256": _sha256(output),
    }

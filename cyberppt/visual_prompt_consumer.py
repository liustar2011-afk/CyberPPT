"""Consume ppt-visual-structure-designer generation modules in production prompts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


VISUAL_STRUCTURE_HEADER = "【视觉结构设计模块｜不上屏】"
VISUAL_STRUCTURE_END = "【视觉结构设计模块结束】"


@dataclass(frozen=True)
class VisualPromptModule:
    page_number: int
    source_path: Path
    source_sha256: str
    page_block_sha256: str
    prompt_text: str


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().lower()


def _section(block: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\s*\n(.*?)(?=^\[[^\n]+\]\s*$|\Z)",
        block,
        flags=re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def load_visual_prompt_module(project: Path, page_number: int) -> VisualPromptModule | None:
    """Load the approved visual-structure handoff for one page, when present.

    The visible Chinese body remains owned by the approved per-page ImageGen
    prompt.  This consumer deliberately imports only page-expression guidance
    from generation-prompts.md.  The selected CyberPPT style is owned by the
    production prompt compiler and is never imported from the visual-structure
    handoff's ``[Style]`` section.
    """

    project = project.expanduser().resolve()
    source_path = project / "visual" / "generation-prompts.md"
    if not source_path.is_file():
        return None
    source = source_path.read_text(encoding="utf-8-sig")
    match = re.search(
        rf"^# Page {page_number}:.*?\n(.*?)(?=^---\s*$|^# Page \d+:|\Z)",
        source,
        flags=re.MULTILINE | re.DOTALL,
    )
    if not match:
        raise ValueError(
            f"visual generation module missing page {page_number}: {source_path}"
        )
    page_block = match.group(1).strip()
    parts: list[str] = []
    for heading in (
        "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
        "[Connector map]",
        "[Text rendering]",
        "[Negative constraints]",
    ):
        content = _section(page_block, heading)
        if content:
            parts.extend([heading, content, ""])
    if not parts:
        raise ValueError(
            f"visual generation module page {page_number} has no consumable sections: {source_path}"
        )
    prompt_text = "\n".join(parts).strip()
    return VisualPromptModule(
        page_number=page_number,
        source_path=source_path,
        source_sha256=_sha256_text(source),
        page_block_sha256=_sha256_text(page_block),
        prompt_text=prompt_text,
    )


def strip_visual_prompt_module(prompt: str) -> str:
    pattern = re.compile(
        rf"\n*{re.escape(VISUAL_STRUCTURE_HEADER)}.*?{re.escape(VISUAL_STRUCTURE_END)}\n*",
        flags=re.DOTALL,
    )
    return pattern.sub("\n\n", prompt).strip()


def append_visual_prompt_module(prompt: str, module: VisualPromptModule | None) -> str:
    base = strip_visual_prompt_module(prompt)
    if module is None:
        return base
    block = "\n".join(
        [
            VISUAL_STRUCTURE_HEADER,
            f"source: {module.source_path.as_posix()}",
            f"page: P{module.page_number:02d}",
            "The following is composition guidance only. Never render its headings, field names, source path, or instruction prose.",
            module.prompt_text,
            VISUAL_STRUCTURE_END,
        ]
    )
    return f"{base.rstrip()}\n\n{block}\n"


def visual_module_metadata(module: VisualPromptModule | None) -> dict[str, object]:
    if module is None:
        return {"consumed": False}
    return {
        "consumed": True,
        "page_number": module.page_number,
        "source_path": str(module.source_path),
        "source_sha256": module.source_sha256,
        "page_block_sha256": module.page_block_sha256,
    }

"""Consume ppt-visual-structure-designer generation modules in production prompts."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path


VISUAL_STRUCTURE_HEADER = "【视觉结构设计模块｜不上屏】"
VISUAL_STRUCTURE_END = "【视觉结构设计模块结束】"
STYLE09_SURFACE_HEADER = "【风格09业务场适配器｜不上屏】"

# Style 09 needs the page's business object to keep dense prose from
# collapsing into a generic table, but it must not inherit a page-specific
# layout recipe (matrix rows, swim lanes, node chains, etc.).  These field
# labels are authored by the visual-structure stage and are deliberately
# filtered by the shared adapter below.
_STYLE09_SEMANTIC_FIELDS = (
    "Semantic focus:",
    "Spatial grammar:",
    "Semantic tags:",
    "Primary structure refs:",
    "Secondary structure refs:",
    "Reading sequence:",
    "Text binding:",
    "Representation freedom:",
    "Industry scene anchor:",
    "business object:",
    "Text integration:",
    "Relationship encoding:",
)

_LAYOUT_BEARING_TEXT_INTEGRATION_RE = re.compile(
    r"(?:位于|置于|放在|上部|下部|顶部|底部|左侧|右侧|居中|结果区|结论区|"
    r"沿.*(?:路径|节点)|贴近.*节点|闭环路径)"
)

_STYLE09_VISUAL_THESIS_FIELD = "Visual thesis:"
_STYLE09_CLOSED_LOOP_INTENT = "Selected visual intent type: closed_loop_operation"

_STYLE09_RELATION_NORMALIZATIONS = (
    ("平台运营闭环", "平台运营关系"),
    ("反馈回路", "运营反馈返回前序环节"),
    ("主链按顺时针推进", "主关系依次发生"),
    ("按顺时针推进", "依次发生"),
    ("反馈线单独回到", "运营反馈返回"),
    ("反馈线回到", "运营反馈返回"),
)

_STYLE09_NEGATIVE_GEOMETRY_CLAUSE_RE = re.compile(
    r"(?:不使用|不要|不得|禁止).*(?:圆环|箭头|网格|泳道|阶段框|节点链)"
)


def _sanitize_style09_semantic_segment(segment: str) -> str:
    """Keep text-object semantics but discard stale placement instructions."""
    if ":" not in segment:
        return segment
    prefix, value = segment.split(":", 1)
    clauses = [part.strip() for part in re.split(r"(?<=[。！？])|，", value) if part.strip()]
    kept: list[str] = []
    for clause in clauses:
        if prefix == "Text integration" and _LAYOUT_BEARING_TEXT_INTEGRATION_RE.search(clause):
            continue
        if _STYLE09_NEGATIVE_GEOMETRY_CLAUSE_RE.search(clause):
            continue
        for source, replacement in _STYLE09_RELATION_NORMALIZATIONS:
            clause = clause.replace(source, replacement)
        kept.append(clause)
    return f"{prefix}: {'，'.join(kept).rstrip('。')}。" if kept else ""


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
    handoff's legacy ``[Style]`` section or its v1.1 ``[Style source]`` reference.
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
        "[Structural guidance]",
        "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
        "[Connector map]",
        "[Text placement]",
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


def append_style09_surface_adapter(
    prompt: str,
    module: VisualPromptModule | None,
) -> str:
    """Carry semantic scene cues into Style 09 without importing a layout recipe.

    The regular visual handoff intentionally contains concrete composition
    directions. Those directions are useful for review, but when they are
    passed verbatim to Style 09 they turn dense pages into equal-weight
    matrices, swim lanes, or step chains. Style 09 therefore consumes only
    the semantic carrier fields and adds a short, generic surface contract.
    The page's business content remains owned by the compiled prompt.
    """

    base = strip_visual_prompt_module(prompt)
    if module is None:
        return base
    lines: list[str] = []
    visual_thesis = ""
    closed_loop_operation = False
    for raw_line in module.prompt_text.splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line:
            continue
        if line.startswith(_STYLE09_VISUAL_THESIS_FIELD):
            visual_thesis = line.split(":", 1)[1].strip().rstrip("。")
        elif line.startswith(_STYLE09_CLOSED_LOOP_INTENT):
            closed_loop_operation = True
        # The visual handoff often packs several labelled facts into one
        # semicolon-separated line (for example, ``business object`` followed
        # by ``placement``). Split first so layout-bearing fields cannot hitch
        # a ride when only the semantic carrier is requested.
        for segment in re.split(r"[;；]", line):
            segment = segment.strip()
            if any(segment.startswith(field) for field in _STYLE09_SEMANTIC_FIELDS):
                segment = _sanitize_style09_semantic_segment(segment)
                if segment:
                    lines.append(f"- {segment}")
    if closed_loop_operation and visual_thesis:
        lines = [
            line
            for line in lines
            if not line.startswith(("- Industry scene anchor:", "- business object:"))
        ]
        lines.insert(
            0,
            "- Dominant semantic carrier: 同一业务对象沿连续状态变化承载业务机制："
            f"{visual_thesis}。",
        )
    block = "\n".join(
        [
            STYLE09_SURFACE_HEADER,
            "以下字段只提供页面业务语义锚点，不上屏；不照抄原页面固定版式。",
            "用一个连续的业务场或具体对象承载文字，让文字附着于对象、边界、动作或结果；关系可用对齐、色调、留白和少量连接线表达。",
            *lines,
            "不要把上述语义字段改造成等宽表格、泳道、步骤卡、连续箭头节点链、图标行或纯信息图。",
            "业务语义字段只保留先后、反馈、约束、汇聚或分支等事实关系，不从字段名称推导具体造型；连接关系保持轻量、从属，不支配页面。",
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

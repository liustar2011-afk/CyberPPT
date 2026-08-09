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
    "Industry scene anchor:",
    "business object:",
    "Text integration:",
    "Relationship encoding:",
)

_LAYOUT_BEARING_TEXT_INTEGRATION_RE = re.compile(
    r"(?:位于|置于|放在|上部|下部|顶部|底部|左侧|右侧|居中|结果区|结论区)"
)


def _sanitize_style09_semantic_segment(segment: str) -> str:
    """Keep text-object semantics but discard stale placement instructions."""
    if not segment.startswith("Text integration:"):
        return segment
    prefix, value = segment.split(":", 1)
    clauses = [part.strip() for part in re.split(r"(?<=[。！？])|，", value) if part.strip()]
    kept = [part for part in clauses if not _LAYOUT_BEARING_TEXT_INTEGRATION_RE.search(part)]
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
    for raw_line in module.prompt_text.splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line:
            continue
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
    block = "\n".join(
        [
            STYLE09_SURFACE_HEADER,
            "仅保留业务语义锚点，不照抄原页面的矩阵、泳道、卡片、节点链或固定版式；这些字段不上屏。",
            "用一个连续的业务场或具体对象承载文字，让文字附着于对象、边界、动作或结果；关系可用对齐、色调、留白和少量连接线表达。",
            *lines,
            "不要把上述语义字段改造成等宽表格、泳道、步骤卡、连续箭头节点链、图标行或纯信息图。",
            "“通道、路径、链、闭环、控制台”等词只表示业务关系，不要具象成整页箭头带、完整圆环、环形节点、规则网格或等宽阶段框；推进和收束用同一对象的状态变化、开放折线路径、短回接线、对齐、色调和留白表达。",
            "基础组件保持克制：先用邻接、对齐、包含、留白和颜色表达关系，只有真实方向无法由空间关系读出时才使用箭头。编号、自然邻接或同一连续基线已表达顺序时，不重复添加逐项箭头；整条流程优先只保留一条主方向线或一个末端箭头。主业务流用深蓝细实线和贴近线端的小型三角箭头头，反馈或复盘最多一条浅灰短虚线；虚线不作装饰节点、不沿页面三边绕行，也不同时承担边框、回流和装饰。每条线必须落在对象外边界，圆点只用于真实接口、汇聚或分支，不得悬空、靠近但不接触、跨越文字。",
            "整页可见边界最多两级：一级业务范围边界、一级必要子组边界；组内项目优先用留白、对齐、浅色底或短分隔线，不逐项完整套框。标签、色块和承载面默认用直角矩形或开放平面色场，同页异形标题条最多一个，不做梯形、六边形、切角、箭头带、徽章、厚底座或多层台阶；低矮平台只在平台承载、分层支撑或汇聚中枢语义明确时使用，且不得兼作页面外框、标题底座和装饰舞台。锁定内容未明确要求时，不添加对勾、警告三角、循环图标、定位针、盾牌或装饰性连续箭头。最多一个主业务场景或主对象、一个辅助证据对象，保持正视、哑光、克制的微立体层次。",
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

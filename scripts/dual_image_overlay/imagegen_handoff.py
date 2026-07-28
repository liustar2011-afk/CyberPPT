#!/usr/bin/env python3
"""Build reviewable ImageGen handoff prompts from approved final scripts.

Before any ImageGen call, CyberPPT must:
1. preserve the approved page meaning and drawable layer;
2. compile plaintext prompts with a tone-only visual contract;
3. save them under workbench/prompts/imagegen/;
4. wait for user modify-or-approve.

Page mission and thesis (页面使命 / 主判断 / 核心判断) are passed before 上屏文字
so the model can understand the page question and organize the visual mainline.
They are context fields, not extra labels to render; the drawable text layer remains 上屏文字.
The default content-first compiler sends the page task, core judgment, full semantic prose,
locked on-screen copy, and factual boundary. It deliberately ignores 视觉结构, visual-intent
routing, and creative-brief layout advice so ImageGen can design the page from the content.
Legacy compilers remain available for comparison and rollback.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cyberppt.commands.script_gate import stage_script
from cyberppt.script_quality_contract import ScriptPage, parse_script_markdown
from scripts.dual_image_overlay.creative_brief import (
    CreativeBrief,
    build_creative_brief,
    render_creative_brief,
)
from scripts.dual_image_overlay.deliverable_prompt import (
    PageBlock,
    assert_deliverable_prompt,
    render_prompt,
)
from scripts.dual_image_overlay.prompt_diagnostics import (
    PagePromptDiagnostics,
    analyze_prompt,
    write_batch_diagnostics,
    write_compiler_comparison,
)
from scripts.dual_image_overlay.style_library import load_style_lock

EVIDENCE_ID_RE = re.compile(r"S\d{3}")
PROMPT_COMPILERS = ("legacy", "creative-brief-v1", "content-first-v1")
DEFAULT_PROMPT_COMPILER = "content-first-v1"
CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT = """【输出要求】
画布尺寸为 2048×1024（2:1）。
【语义理解】
完整覆盖【必须上屏文字】中的信息要点和逻辑关系，模块名称、关键数字、单位和业务术语须准确；不得改变原意、遗漏关键结论或新增事实。
根据页面任务、核心判断、完整内容语义和必须上屏文字，自主决定构图、视觉载体、信息层级和图文组合；并根据本页最重要的业务关系，必须从流程主链、汇聚、分发、闭环、层级、并列、对照等关系形式中选择一种作为主导表达。
【视觉表达】
在表达页面文字段落时，优先使用彩色化、具象化、语义化、场景化的行业插图，将业务对象、动作过程和主导关系转化为可识别的视觉结构。
避免把业务含义处理成圆形图标、图标墙、线性符号、扁平界面组件或等距三维小组件。
场景化插图中的人物、标牌、屏幕文字和数字仅作为环境质感，应采用远景、侧背面、浅景深、低对比或适度虚化处理，不能清晰地出现组织机构名称、人员名称和文件名称。中文字体统一采用微软雅黑或与微软雅黑字形特征接近的现代无衬线黑体，文字清晰且优雅排版，高端平面设计。
不得生成页面标题、副标题、Logo、页脚、页码。"""
CONTENT_FIRST_ONSCREEN_STORY_CONTRACT = """【独立阅读约束｜仅供执行，不上屏】
【必须上屏文字】是已经审定的完整可见信息层，必须全部呈现，不得再次摘要、删减或只保留模块标题与关键词。
【必须上屏文字】中的第一段是正文区结论句，不是页面标题或副标题；应作为正文内容的结论锚点呈现，不得按页面标题样式处理，不得与 PPT 模板层标题争夺视觉层级。
页面应在脱离演讲者讲解时仍可独立阅读，并保留支撑结论所需的事实或数字、解释关系、因果传导以及推论或页面承接。
允许调整换行、分组和文字层级，但不得改变原意、合并掉关键语义或用插图替代必须上屏文字。"""
# Status asides that must not be painted as core on-screen claims.
# Planning decks argue the proposed solution; do not restamp "not yet fact" on every page.
ONSCREEN_ASIDE_RE = re.compile(
    r"[；;，,]?\s*(?:"
    r"不等于[^。；;\n]*|"
    r"并不等于[^。；;\n]*|"
    r"并不等同于[^。；;\n]*|"
    r"不能只看[^。；;\n]*|"
    r"不写成[^。；;\n]*|"
    r"也不等于[^。；;\n]*|"
    r"也不预设[^。；;\n]*|"
    r"分期建议≠[^。；;\n]*|"
    r"缺口清单≠[^。；;\n]*|"
    r"自动化≠[^。；;\n]*|"
    r"稳定接入尚非[^。；;\n]*|"
    r"尚非既成事实[^。；;\n]*|"
    r"算法栈仍待[^。；;\n]*|"
    r"仍待(?:摸底|论证|验证|基线)[^。；;\n]*|"
    r"讨论稿不代替[^。；;\n]*|"
    r"不升格为已批准[^。；;\n]*|"
    r"缺测量与验证前不能写死[^。；;\n]*|"
    r"任一档均非已审定[^。；;\n]*|"
    r"不能直接作最终预算[^。；;\n]*|"
    r"尚未作为完备工程方案[^。；;\n]*"
    r")"
)

VISUAL_INTENT_SIGNALS: dict[str, tuple[tuple[str, int], ...]] = {
    "decision_admission": (
        ("准入", 8),
        ("筛选依据", 8),
        ("如何选定", 7),
        ("首期聚焦", 8),
        ("选择条件", 7),
        ("成熟度条件", 6),
        ("后续纳入", 5),
    ),
    "comparison": (
        ("对比", 7),
        ("比较", 7),
        ("差异", 6),
        ("优劣", 6),
        ("高于", 4),
        ("低于", 4),
        ("相较", 4),
    ),
    "scenario_application": (
        ("重点场景", 6),
        ("业务场景", 5),
        ("应用方向", 7),
        ("应用场景", 7),
        ("推进条件", 4),
        ("业务价值", 3),
    ),
    "multi_semantic_foundation": (
        ("工作基础", 8),
        ("现实基础", 8),
        ("已有基础", 7),
        ("共同基础", 7),
        ("持续性工作基础", 9),
    ),
    "causal": (
        ("为什么", 7),
        ("原因", 7),
        ("导致", 6),
        ("带来", 4),
        ("不匹配", 7),
        ("不足", 5),
        ("变化如何改变", 8),
        ("问题与影响", 6),
    ),
    "closed_loop": (
        ("闭环", 9),
        ("输入、处理、输出", 9),
        ("输入、结果、验证、反馈", 9),
        ("反馈与复盘", 7),
        ("持续校正", 6),
        ("稳定生产能力", 5),
    ),
    "phase": (
        ("分期推进", 9),
        ("分阶段", 8),
        ("建设节奏", 8),
        ("按什么节奏", 8),
        ("当前、近期和中长期", 9),
        ("近期首先", 6),
        ("先开展", 4),
        ("再拓展", 4),
    ),
    "capability_relationship": (
        ("能力协同", 8),
        ("协同支撑", 8),
        ("共同支撑", 7),
        ("能力关系", 8),
        ("能力体系", 7),
        ("能力底座", 7),
        ("能力组成", 8),
        ("由哪些部分组成", 8),
        ("平台稳定承载", 7),
        ("共性能力", 5),
    ),
}

VISUAL_INTENT_PRIORITY = (
    "multi_semantic_foundation",
    "comparison",
    "closed_loop",
    "phase",
    "capability_relationship",
    "decision_admission",
    "scenario_application",
    "causal",
    "judgment_evidence",
)

TEXT_IN_COMPOSITION_RULE = (
    "Treat all required text as calm in-composition panels, annotations, or labels attached "
    "to the dominant visual structure; do not place the complete text layer in a detached "
    "left/right column or top/bottom rail."
)
DETACHED_TEXT_RAIL_AVOID = (
    "a detached full-height text column, text rail, or a separate text zone plus image zone"
)

VISUAL_INTENT_TEMPLATES: dict[str, dict[str, str]] = {
    "decision_admission": {
        "visual_thesis": (
            "Explain why the initial selection is justified and how later items qualify for entry."
        ),
        "decision_relationship": (
            "Selection criteria jointly justify the initial choice; later items remain "
            "behind explicit readiness gates. Treat this as a decision structure, "
            "not an implementation process."
        ),
        "recommended_composition": (
            "Use a weighted decision field: give the selected initial scope dominant visual "
            "weight, bind compact criteria to that choice, and place later scope behind a "
            "secondary gated-entry area."
        ),
        "avoid_on_this_page": (
            "Five equal-weight criterion cards, a generic three-step flow, timeline, "
            "or scenario thumbnail wall."
        ),
    },
    "comparison": {
        "visual_thesis": "Make differences and priorities immediately visible.",
        "decision_relationship": (
            "Compared items share a common dimension; show contrast and priority "
            "without inventing a ranking not supported by the content."
        ),
        "recommended_composition": (
            "Use one aligned comparison field with a shared basis, directly opposed evidence, "
            "and unequal emphasis where the content establishes priority."
        ),
        "avoid_on_this_page": (
            "Unaligned cards, decorative versus symbols, invented scores, or a comparison "
            "without a shared dimension."
        ),
    },
    "scenario_application": {
        "visual_thesis": (
            "Show where the business scenario occurs, what value it creates, "
            "and what conditions enable it."
        ),
        "decision_relationship": (
            "Business context connects application direction, current stage, and entry conditions."
        ),
        "recommended_composition": (
            "Use one integrated real-work scene with business-value and readiness evidence "
            "embedded in the relevant parts of that scene."
        ),
        "avoid_on_this_page": (
            "A product-feature showcase, scenario thumbnail wall, decorative industry photo, "
            "or unrelated technology interface."
        ),
    },
    "multi_semantic_foundation": {
        "visual_thesis": (
            "Show how several concrete work foundations jointly support the page judgment."
        ),
        "decision_relationship": (
            "Distinct foundations reinforce one another and combine into a sustainable working basis."
        ),
        "recommended_composition": (
            "Use one dominant integrated visual carrier for the shared support relationship. "
            "Use images only where they clarify the relationship; their number, placement, and "
            "association with a module are determined by the page visual structure, not by the "
            "count of foundations."
        ),
        "avoid_on_this_page": (
            "One generic office, meeting-room, control-room, or industry image carrying all "
            "meanings; one image per foundation; a row-by-row text-and-photo correspondence; "
            "a separate text zone plus photo zone; equal image cards; or unrelated decorative imagery."
        ),
    },
    "causal": {
        "visual_thesis": (
            "Make the page judgment visible through a clear cause-and-effect argument."
        ),
        "decision_relationship": (
            "Causes or changes lead to a business consequence and explain the need for action."
        ),
        "recommended_composition": (
            "Use one directional cause-to-consequence path, with the business consequence as "
            "the dominant anchor and compact causal evidence attached along the path."
        ),
        "avoid_on_this_page": (
            "A list of unrelated facts, equal cards, or decorative trend arrows."
        ),
    },
    "closed_loop": {
        "visual_thesis": (
            "Show how business inputs become usable results and improve through feedback."
        ),
        "decision_relationship": (
            "Use a closed-loop relationship with explicit input, result, validation, and feedback."
        ),
        "recommended_composition": (
            "Use one integrated operational loop anchored in a real work context, with input, "
            "result, validation, and feedback attached to their places in the loop."
        ),
        "avoid_on_this_page": (
            "A software workflow, lifecycle icon circle, or numbered administration steps."
        ),
    },
    "phase": {
        "visual_thesis": (
            "Show stage progression while preserving the different purpose of each phase."
        ),
        "decision_relationship": (
            "Current, near-term, and later work form a stage progression with explicit "
            "readiness conditions."
        ),
        "recommended_composition": (
            "Use a weighted stage trajectory: give the current or near-term decision primary "
            "weight and place later stages as secondary, conditional progression."
        ),
        "avoid_on_this_page": (
            "An equal-weight timeline, generic roadmap arrows, or milestone decoration."
        ),
    },
    "capability_relationship": {
        "visual_thesis": "Explain how capabilities work together to create business value.",
        "decision_relationship": (
            "Capabilities form a support relationship around the page judgment; do not turn "
            "them into a software stack unless the content explicitly defines one."
        ),
        "recommended_composition": (
            "Use one integrated business-work composition with business value as the dominant "
            "outcome. Weave supporting capabilities into that shared context in unequal roles; do not "
            "assign a separate picture, panel, quadrant, layer, or numbered visual unit to each capability."
        ),
        "avoid_on_this_page": (
            "A generic architecture stack, center-satellite nodes, equal capability cards, "
            "a five-part picture wall, one image per capability, or a software-module diagram."
        ),
    },
    "judgment_evidence": {
        "visual_thesis": "Express the page as one judgment supported by evidence.",
        "decision_relationship": (
            "Supporting modules jointly explain or substantiate the core judgment."
        ),
        "recommended_composition": (
            "Use one dominant judgment anchor with compact, unequal-weight supporting evidence "
            "attached directly to that anchor."
        ),
        "avoid_on_this_page": (
            "An equal card wall, one icon per bullet, or an unrelated decorative scene."
        ),
    },
}

def _clean_onscreen_for_imagegen(text: str) -> str:
    """Keep theme bullets; strip boundary asides that dilute the page mission."""

    cleaned_lines: list[str] = []
    for raw in text.splitlines():
        line = ONSCREEN_ASIDE_RE.sub("", raw)
        line = re.sub(r"[；;]\s*$", "", line.rstrip())
        line = re.sub(r"\s{2,}", " ", line)
        # Drop emptied bullets that only carried an aside.
        if re.fullmatch(r"\s*[-*•]?\s*", line or ""):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def select_page_visual_intent_type(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> str:
    """Select a page relationship without allowing one generic noun to hijack it."""

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no visual intent")
    context = context if isinstance(context, dict) else {}
    explicit = (
        (override or {}).get("visual_intent_type")
        or context.get("visual_intent_type")
        or ""
    ).strip()
    if explicit in VISUAL_INTENT_TEMPLATES:
        return explicit

    signal_text = "\n".join(
        (
            page_mission,
            context.get("business_question", ""),
            context.get("page_job", ""),
            page.main_message,
            "\n".join(page.module_titles),
        )
    )
    # These are field or object names, not page relationships.
    score_text = (
        signal_text.replace("业务应用层", "")
        .replace("平台应用层", "")
        .replace("需求预测", "")
        .replace("负荷需求", "")
    )
    scores = {
        intent_type: sum(
            weight for phrase, weight in signals if phrase in score_text
        )
        for intent_type, signals in VISUAL_INTENT_SIGNALS.items()
    }
    role = context.get("argument_role", "").strip()
    if role == "foundation":
        scores["multi_semantic_foundation"] += 8
    elif role in {"change", "gap", "necessity"}:
        scores["causal"] += 3
    elif role == "implementation" and any(
        phrase in score_text for phrase in ("近期", "阶段", "节奏", "先开展", "再拓展")
    ):
        scores["phase"] += 4

    best_score = max(scores.values(), default=0)
    if best_score < 5:
        return "judgment_evidence"
    for intent_type in VISUAL_INTENT_PRIORITY:
        if scores.get(intent_type) == best_score:
            return intent_type
    return "judgment_evidence"


def build_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
    context: dict[str, str] | None = None,
) -> str:
    """Compile deterministic, non-rendering page-specific composition guidance."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=context,
        override=override,
    )
    values = dict(VISUAL_INTENT_TEMPLATES[relation])
    if isinstance(override, dict):
        for key in values:
            value = override.get(key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
    values["recommended_composition"] = (
        f"{values['recommended_composition']} {TEXT_IN_COMPOSITION_RULE}"
    )
    values["avoid_on_this_page"] = (
        f"{values['avoid_on_this_page']} Avoid {DETACHED_TEXT_RAIL_AVOID}."
    )
    return "\n".join(
        (
            "[Prompt context] Page-specific visual intent "
            "(composition guidance only; do not render field names or instruction text)",
            f"- Selected visual intent type: {relation}",
            f"- Visual thesis: {values['visual_thesis']}",
            f"- Decision relationship: {values['decision_relationship']}",
            f"- Recommended composition: {values['recommended_composition']}",
            f"- Avoid on this page: {values['avoid_on_this_page']}",
        )
    )


@dataclass(frozen=True)
class CompiledPagePrompt:
    prompt: str
    compiler_version: str
    relation: str
    creative_brief: CreativeBrief | None = None
    injected_rule_ids: tuple[str, ...] = ()
    style_selection: dict[str, Any] | None = None

    def build_metadata(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "compiler_version": self.compiler_version,
            "relation": self.relation,
            "injected_rule_ids": list(self.injected_rule_ids),
        }
        if self.creative_brief is not None:
            payload["creative_brief"] = self.creative_brief.to_dict()
        if self.style_selection is not None:
            payload["style_selection"] = dict(self.style_selection)
        return payload


def build_page_creative_brief(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
    context: dict[str, str] | None = None,
) -> CreativeBrief:
    """Build semantic invariants and creative freedom using the existing router."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=context,
        override=override,
    )
    return build_creative_brief(
        relation=relation,
        page_purpose=page_mission or page.main_message,
        core_judgment=page.main_message,
        required_meanings=page.module_titles,
        onscreen_text=_clean_onscreen_for_imagegen(page.onscreen_text),
        override=override,
    )


def content_lock_text(page: ScriptPage, page_mission: str = "") -> str:
    """Build prompt context followed by the drawable 上屏文字 layer."""

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no body ImageGen handoff")
    onscreen = _clean_onscreen_for_imagegen(page.onscreen_text)
    context: list[str] = [
        "[Prompt context] 页面使命 / Page mission（用于理解本页要回答的问题；不要把字段名或说明文字画出来）",
        page_mission.strip() or "未提供页面使命",
        "[Prompt context] 核心判断 / Core judgment（用于组织视觉主线；不要把字段名或说明文字画出来）",
        page.main_message.strip() or "未提供核心判断",
        "上屏文字（需要准确表达的正文文字层）",
        onscreen,
    ]
    return "\n".join(context).strip() + "\n"


def _flatten_markdown_tables(text: str) -> str:
    """Preserve table cell meanings without prescribing a rendered table."""

    output: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if re.fullmatch(r"\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?", line):
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            output.append(" · ".join(cell for cell in cells if cell))
        else:
            output.append(raw)
    return "\n".join(output).strip()


def diagnostic_onscreen_text(
    page: ScriptPage,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
) -> str:
    """Return the text layer the selected compiler is required to preserve."""

    if prompt_compiler == "content-first-v1":
        body = _flatten_markdown_tables(
            _clean_onscreen_for_imagegen(page.onscreen_text)
        )
        return "\n\n".join(
            part for part in (page.onscreen_judgment.strip(), body) if part
        )
    return page.onscreen_text


STYLE_COLOR_LABELS = (
    ("background", "背景"),
    ("title", "主文字"),
    ("body", "正文"),
    ("secondary", "次级文字"),
    ("divider", "线条与分隔"),
    ("accent", "强调色"),
)


def _selected_content_first_style(style_lock: Path) -> dict[str, Any]:
    """Load the selected style without importing its layout or text-density rules."""

    payload = load_style_lock(style_lock)
    style = payload.get("style")
    if not isinstance(style, dict):
        raise ValueError(f"visual style lock has no selected style: {style_lock}")
    name = str(style.get("name") or "").strip()
    colors = style.get("colors")
    if not name or not isinstance(colors, dict) or not colors:
        raise ValueError(
            f"visual style lock must provide style name and colors: {style_lock}"
        )
    return style


def render_content_first_style_contract(style_lock: Path) -> str:
    """Render tone-only style guidance from the project's selected style lock."""

    style = _selected_content_first_style(style_lock)
    colors = style["colors"]
    color_parts = [
        f"{label} {str(colors[key]).strip()}"
        for key, label in STYLE_COLOR_LABELS
        if str(colors.get(key) or "").strip()
    ]
    known_keys = {key for key, _ in STYLE_COLOR_LABELS}
    color_parts.extend(
        f"{key} {str(value).strip()}"
        for key, value in colors.items()
        if key not in known_keys and str(value).strip()
    )
    scenario = str(style.get("scenario") or "").split("；", 1)[0].strip()
    lines = [
        "【视觉风格】",
        (
            f"使用项目已选择的视觉风格「{str(style['name']).strip()}」"
            f"（ID {style.get('id', 'custom')}，{style.get('slug', 'custom')}）。"
        ),
    ]
    if scenario:
        lines.append(f"风格适用语境：{scenario}。")
    lines.extend(
        [
            f"色彩角色：{'；'.join(color_parts)}。",
            (
                "只继承该风格的色彩、材质、线条、排版气质和画面质感；"
                "不得从风格锁引入固定构图、模块数量、文字删减、图片数量、"
                "后期叠字或可编辑文字层规则。"
            ),
            (
                "页面构图和信息组织仍由页面任务、核心判断、完整内容语义、"
                "必须上屏文字与主导业务关系共同决定。"
            ),
        ]
    )
    return "\n".join(lines)


def render_content_first_prompt(
    page: ScriptPage,
    *,
    style_lock: Path,
    page_mission: str = "",
) -> str:
    """Render a complete-content prompt without translating meaning into layout."""

    onscreen = diagnostic_onscreen_text(page, "content-first-v1")
    parts = [
        f"【页面编码】{page.page_id.upper()}｜{page.title or page.page_id}",
        "以上仅用于按页追踪，不得在图中渲染页面编码。",
        "",
        "【页面任务｜仅供理解，不上屏】",
        page_mission.strip() or page.main_message.strip(),
        "",
        "【核心判断｜仅供理解】",
        page.main_message.strip(),
        "",
        "【完整内容语义｜仅供理解，不要求逐字上屏】",
        page.full_prose.strip() or onscreen,
        "",
        "【必须上屏文字】",
        onscreen,
        "",
        CONTENT_FIRST_ONSCREEN_STORY_CONTRACT,
        "",
        "【事实与范围边界｜仅供约束，不上屏】",
        page.boundary.strip() or "不得扩大原文的事实范围或结论强度。",
        "不得新增原文不存在的数字、组织名称、责任主体、事实、结论或口号。",
        "",
        CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT,
        "",
        render_content_first_style_contract(style_lock),
    ]
    return "\n".join(parts).strip() + "\n"


def _page_missions(project: Path) -> dict[str, str]:
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    if not outline_path.is_file():
        return {}
    payload = json.loads(outline_path.read_text(encoding="utf-8-sig"))
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return {}
    return {
        str(item.get("page_id")): str(item.get("business_question") or "").strip()
        for item in pages
        if isinstance(item, dict) and item.get("page_id")
    }


def _page_visual_contexts(project: Path) -> dict[str, dict[str, str]]:
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    if not outline_path.is_file():
        return {}
    payload = json.loads(outline_path.read_text(encoding="utf-8-sig"))
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return {}
    fields = (
        "argument_role",
        "page_job",
        "business_question",
        "visual_intent_type",
    )
    return {
        str(item["page_id"]): {
            field: str(item.get(field) or "").strip()
            for field in fields
            if str(item.get(field) or "").strip()
        }
        for item in pages
        if isinstance(item, dict) and item.get("page_id")
    }


def _page_visual_intent_overrides(project: Path) -> dict[str, dict[str, str]]:
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    if not outline_path.is_file():
        return {}
    payload = json.loads(outline_path.read_text(encoding="utf-8-sig"))
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return {}
    allowed = {
        "visual_intent_type",
        *VISUAL_INTENT_TEMPLATES["judgment_evidence"].keys(),
    }
    result: dict[str, dict[str, str]] = {}
    for item in pages:
        if not isinstance(item, dict) or not item.get("page_id"):
            continue
        raw = item.get("visual_intent")
        if not isinstance(raw, dict):
            continue
        cleaned = {
            key: value.strip()
            for key, value in raw.items()
            if key in allowed and isinstance(value, str) and value.strip()
        }
        if cleaned:
            result[str(item["page_id"])] = cleaned
    return result


def compile_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
) -> CompiledPagePrompt:
    if prompt_compiler not in PROMPT_COMPILERS:
        raise ValueError(
            f"unsupported prompt compiler: {prompt_compiler}; "
            f"choose one of {', '.join(PROMPT_COMPILERS)}"
        )
    if prompt_compiler == "content-first-v1":
        selected_style = _selected_content_first_style(style_lock)
        prompt = render_content_first_prompt(
            page,
            style_lock=style_lock,
            page_mission=page_mission,
        )
        assert_deliverable_prompt(prompt)
        if EVIDENCE_ID_RE.search(prompt):
            raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
        return CompiledPagePrompt(
            prompt=prompt,
            compiler_version=prompt_compiler,
            relation="model_decides_from_complete_content",
            injected_rule_ids=(
                "content.page_task",
                "content.core_judgment",
                "content.full_semantics",
                "content.locked_onscreen",
                "content.independent_reading",
                "fact.source_boundary",
                "style.selected_lock",
                "style.tone_only",
            ),
            style_selection={
                "id": selected_style.get("id"),
                "slug": selected_style.get("slug"),
                "name": selected_style.get("name"),
                "colors": dict(selected_style.get("colors") or {}),
                "style_lock": str(style_lock),
            },
        )

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=visual_context,
        override=visual_intent_override,
    )
    creative_brief: CreativeBrief | None = None
    if prompt_compiler == "creative-brief-v1":
        creative_brief = build_page_creative_brief(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        visual_intent = render_creative_brief(creative_brief)
        injected_rule_ids = (
            "creative.context",
            "creative.freedom_envelope",
            "text.locked_onscreen_exact",
            "text.auxiliary_allowed",
            *(
                f"creative.page_avoid.{index}"
                for index, _ in enumerate(
                    creative_brief.page_specific_avoids,
                    start=1,
                )
            ),
        )
    else:
        visual_intent = build_page_visual_intent(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        injected_rule_ids = ("legacy.visual_intent", "legacy.visual_grammar")
    prompt_text = content_lock_text(page, page_mission=page_mission).rstrip()
    block = PageBlock(
        page_number=int(page.page_id[1:]),
        title=page.title or page.page_id,
        text=prompt_text,
    )
    prompt = render_prompt(
        block,
        style_lock_path=style_lock,
        composition_guidance=visual_intent,
        compiler_version=prompt_compiler,
    )
    assert_deliverable_prompt(prompt)
    if EVIDENCE_ID_RE.search(prompt):
        raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
    for banned in ("完整文字稿", "文字稿取舍说明", "证据映射", "讲解提示", "禁止项"):
        if banned in prompt:
            raise ValueError(f"{page.page_id} ImageGen prompt still contains backend field: {banned}")
    if "Boundary (do not show on slide)" in prompt:
        raise ValueError(f"{page.page_id} ImageGen prompt still contains Boundary block")
    # Field injection form only — style presets may still mention the concept as guidance.
    if "视觉结构：" in prompt or re.search(r"(?m)^-?\s*视觉结构\b", prompt):
        raise ValueError(f"{page.page_id} ImageGen prompt still contains backend field: 视觉结构")
    return CompiledPagePrompt(
        prompt=prompt,
        compiler_version=prompt_compiler,
        relation=relation,
        creative_brief=creative_brief,
        injected_rule_ids=tuple(injected_rule_ids),
    )


def build_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
) -> str:
    """Backward-compatible string API over the versioned prompt compiler."""

    return compile_page_prompt(
        page,
        style_lock,
        page_mission=page_mission,
        visual_context=visual_context,
        visual_intent_override=visual_intent_override,
        prompt_compiler=prompt_compiler,
    ).prompt


def write_chapter_handoff(
    *,
    project: Path,
    script: Path,
    style_lock: Path,
    pages: list[int],
    batch_name: str,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    compare_with: str | None = None,
) -> dict[str, Path]:
    if compare_with is not None and compare_with not in PROMPT_COMPILERS:
        raise ValueError(f"unsupported comparison compiler: {compare_with}")
    document = parse_script_markdown(script.read_text(encoding="utf-8"))
    by_num = {int(page.page_id[1:]): page for page in document.pages}
    missions = _page_missions(project)
    visual_contexts = _page_visual_contexts(project)
    visual_intent_overrides = _page_visual_intent_overrides(project)
    out_dir = project / "workbench" / "prompts" / "imagegen"
    out_dir.mkdir(parents=True, exist_ok=True)

    review_parts: list[str] = [
        f"# ImageGen 送图脚本审阅稿 · {batch_name}",
        "",
        "> 状态：等待用户修改或批准。未经批准不得进入 ImageGen。",
        f"> 源脚本：`{script.as_posix()}`",
        f"> 风格锁定：`{style_lock.as_posix()}`",
        f"> Prompt compiler: `{prompt_compiler}`",
        "",
        "## 编入规则",
        "",
        "- 送入：页面使命、核心判断、上屏文字，以及页面级视觉意图。",
        "- 不送入：边界/Boundary/禁止项、完整文字稿、取舍说明、证据映射、证据编号、视觉结构、讲解提示。",
        "- 页面使命、核心判断与页面级视觉意图只作为理解和构图上下文；不要把字段名或说明文字渲染到画面，正文文字以“上屏文字”为准。",
        "- 封面/目录/章节过渡/封底：不生成正文区 ImageGen，由模板层承载。",
        "",
    ]
    outputs: dict[str, Path] = {}
    content_prompts: list[str] = []
    diagnostics: list[PagePromptDiagnostics] = []
    comparison_diagnostics: list[
        tuple[PagePromptDiagnostics, PagePromptDiagnostics]
    ] = []

    for page_number in pages:
        page = by_num[page_number]
        if page.page_type != "content":
            review_parts.extend(
                [
                    f"## 第{page_number}页：{page.title or page.page_type}",
                    "",
                    f"- 页面类型：`{page.page_type}`",
                    "- 结论：本页不生成正文区 ImageGen；标题/章节字由模板文字层输出。",
                    "",
                ]
            )
            continue

        compiled = compile_page_prompt(
            page,
            style_lock,
            page_mission=missions.get(page.page_id, ""),
            visual_context=visual_contexts.get(page.page_id),
            visual_intent_override=visual_intent_overrides.get(page.page_id),
            prompt_compiler=prompt_compiler,
        )
        prompt = compiled.prompt
        content_prompts.append(prompt)
        selected_diagnostics = PagePromptDiagnostics(
            page_id=page.page_id,
            title=page.title or page.page_id,
            metrics=analyze_prompt(
                prompt,
                onscreen_text=diagnostic_onscreen_text(
                    page,
                    prompt_compiler,
                ),
            ),
            build_metadata=compiled.build_metadata(),
        )
        diagnostics.append(selected_diagnostics)
        if compare_with and compare_with != prompt_compiler:
            comparison = compile_page_prompt(
                page,
                style_lock,
                page_mission=missions.get(page.page_id, ""),
                visual_context=visual_contexts.get(page.page_id),
                visual_intent_override=visual_intent_overrides.get(page.page_id),
                prompt_compiler=compare_with,
            )
            comparison_page = PagePromptDiagnostics(
                page_id=page.page_id,
                title=page.title or page.page_id,
                metrics=analyze_prompt(
                    comparison.prompt,
                    onscreen_text=diagnostic_onscreen_text(
                        page,
                        compare_with,
                    ),
                ),
                build_metadata=comparison.build_metadata(),
            )
            if prompt_compiler == "legacy":
                comparison_diagnostics.append(
                    (selected_diagnostics, comparison_page)
                )
            else:
                comparison_diagnostics.append(
                    (comparison_page, selected_diagnostics)
                )
        draft_source = out_dir / f"_tmp_slide-{page_number:02d}-imagegen.md"
        draft_source.write_text(prompt, encoding="utf-8")
        staged = stage_script(
            project,
            slide=page_number,
            kind="imagegen",
            phase="draft",
            source=draft_source,
            note=f"{batch_name} imagegen handoff draft for review",
        )
        draft_source.unlink(missing_ok=True)
        outputs[page.page_id] = staged
        review_parts.extend([prompt, ""])

    batch_path = out_dir / f"{batch_name}-imagegen-review.md"
    if content_prompts:
        batch_path.write_text("\n".join(review_parts).rstrip() + "\n", encoding="utf-8")
    else:
        batch_path.write_text("\n".join(review_parts).rstrip() + "\n", encoding="utf-8")
    outputs["batch"] = batch_path
    diagnostics_path = out_dir / f"{batch_name}-imagegen-diagnostics.json"
    write_batch_diagnostics(
        diagnostics_path,
        diagnostics,
        batch_name=batch_name,
    )
    outputs["diagnostics"] = diagnostics_path
    if comparison_diagnostics:
        comparison_path = out_dir / f"{batch_name}-imagegen-compiler-comparison.json"
        write_compiler_comparison(
            comparison_path,
            comparison_diagnostics,
            batch_name=batch_name,
        )
        outputs["comparison"] = comparison_path

    gate = project / "workbench" / "stages" / "02-blueprint-dual-image" / f"{batch_name}-imagegen-script-gate.md"
    gate.parent.mkdir(parents=True, exist_ok=True)
    gate.write_text(
        "\n".join(
            [
                f"# ImageGen 送图脚本门禁 · {batch_name}",
                "",
                f"- batch_review: `{batch_path.as_posix()}`",
                "- status: waiting_for_user_modify_or_approve",
                "- rule: 用户批准前不得调用 ImageGen / final-script-pages --production-build",
                "",
                "## 请回复",
                "",
                "1. **批准送图脚本**（可指定页段）→ 将对应页 stage 为 final 并登记 approve-script 后再生图",
                "2. **修改第N页** → 给出改法，返工该页 prompt 后再审",
                "",
            ]
        ),
        encoding="utf-8",
    )
    outputs["gate"] = gate
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--style-lock", type=Path, required=True)
    parser.add_argument("--pages", required=True, help="e.g. 1-7")
    parser.add_argument("--batch-name", default="chapter01")
    parser.add_argument(
        "--prompt-compiler",
        choices=PROMPT_COMPILERS,
        default=DEFAULT_PROMPT_COMPILER,
    )
    parser.add_argument(
        "--compare-with",
        choices=PROMPT_COMPILERS,
    )
    args = parser.parse_args(argv)

    raw = args.pages.strip()
    if "-" in raw and "," not in raw:
        start, end = raw.split("-", 1)
        pages = list(range(int(start), int(end) + 1))
    else:
        pages = [int(part) for part in raw.split(",") if part.strip()]

    outputs = write_chapter_handoff(
        project=args.project.resolve(),
        script=args.script.resolve(),
        style_lock=args.style_lock.resolve(),
        pages=pages,
        batch_name=args.batch_name,
        prompt_compiler=args.prompt_compiler,
        compare_with=args.compare_with,
    )
    print(f"batch_review={outputs['batch']}")
    print(f"diagnostics={outputs['diagnostics']}")
    if "comparison" in outputs:
        print(f"comparison={outputs['comparison']}")
    print(f"gate={outputs['gate']}")
    for key, path in sorted(outputs.items()):
        if key.startswith("p"):
            print(f"{key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

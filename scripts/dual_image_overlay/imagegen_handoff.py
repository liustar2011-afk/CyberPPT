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
The default content-first compiler sends the page task, core judgment, locked on-screen copy,
and a compact page logic contract. Each page remains a standalone ImageGen prompt, while source
prose and repeated design theory stay out of the model context.
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
from cyberppt.script_quality_contract import (
    ScriptPage,
    parse_script_markdown,
    resolve_judgment_mode,
)
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
from scripts.dual_image_overlay.style_library import load_style_lock, resolve_default_style

EVIDENCE_ID_RE = re.compile(r"S\d{3}")
PROMPT_COMPILERS = ("legacy", "creative-brief-v1", "content-first-v1")
DEFAULT_PROMPT_COMPILER = "content-first-v1"
CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT = """【内容与视觉要求｜不上屏】
必须由文字、结构和必要画面共同完整表达【完整上屏内容】中的核心判断、业务对象、逻辑关系、关键限定和正文要点，不得捏造事实、改变判断强度或删除支撑判断成立所必需的内容。
【锁定关键文字】中的每一项都必须逐字准确；数字、单位、专有名词、业务术语和否定边界必须准确。
【完整上屏内容】均需进入 full 图；允许调整换行、文字层级和局部语序，但不得把解释性正文全部替换为场景、图标或抽象视觉隐喻。
不得新增未经页面内容支持的上屏文字；必要的行业场景、业务动作、环境细节和视觉隐喻只能辅助附近文字与业务关系。
以【页面逻辑】组织空间，不使用等权卡片、通用图标流程或逐项配图。
中文使用清晰的现代无衬线黑体。不得生成额外页面标题、Logo、页脚或页码。
【输出要求｜不上屏】
画布尺寸为 2048×1024（2:1）。"""
CONTENT_FIRST_SEMANTIC_ONLY_OUTPUT_CONTRACT = """【内容与视觉要求｜不上屏】
必须由文字、结构和必要画面共同完整表达【完整上屏内容】中的核心判断、业务对象、逻辑关系、关键限定和正文要点，不得捏造事实、改变判断强度或删除支撑判断成立所必需的内容。
数字、单位、专有名词、业务术语和否定边界必须准确；其他说明文字允许在不损失语义的前提下调整语序、合并重复、拆分为场景标签或适度压缩。
【完整上屏内容】均需进入 full 图；允许调整换行、文字层级和局部语序，但不得把解释性正文全部替换为场景、图标或抽象视觉隐喻。
不得新增未经页面内容支持的上屏文字；允许增加不带文字的行业场景、业务动作、环境细节和视觉隐喻，让视觉关系承担解释责任。
以【页面逻辑】组织空间，不使用等权卡片、通用图标流程或逐项配图；先展开业务场景及其关系，再让必要文字附着于场景。
中文使用清晰的现代无衬线黑体。不得生成额外页面标题、Logo、页脚或页码。
【输出要求｜不上屏】
画布尺寸为 2048×1024（2:1）。"""
CONTENT_FIRST_ONSCREEN_STORY_CONTRACT = """【结论句要求｜不上屏】
如【锁定关键文字】含正文结论句，该句是正文结论句，不是页面标题；不得通栏放大或添加标题竖线、横线等装饰。
允许调整换行和文字层级；画面必须参与表达页面逻辑，不得退化为文字排版加装饰图片。"""
CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT = """【结论表达要求｜不上屏】
本页没有要求逐字上屏的正文结论句；不得从【页面任务】【核心判断】或【页面逻辑】中自行抽取整句作为页面标题或通栏结论。
【完整上屏内容】仍须完整表达；用文字层级、业务结构、对象关系和必要画面共同组织核心判断。"""
CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT = """【结论表达要求｜不上屏】
本页没有要求逐字上屏的正文结论句；不得从【页面任务】【核心判断】或【页面逻辑】中自行抽取整句作为页面标题或通栏结论。
【锁定关键文字】中的业务标签和关键事实必须全部上屏；【完整上屏内容】仍须完整表达，用文字层级、业务结构、对象关系和必要画面共同组织核心判断。"""
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
    "boundary_guardrail": (
        ("边界护栏", 10),
        ("职责边界", 9),
        ("不替代", 9),
        ("不承担", 8),
        ("范围边界", 8),
        ("非目标", 7),
    ),
    "hierarchy_support": (
        ("分层支撑", 10),
        ("上下依赖", 9),
        ("支撑底座", 9),
        ("贯穿保障", 8),
        ("需求牵引层", 7),
        ("可信底座", 7),
        ("五层", 5),
    ),
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
    "boundary_guardrail",
    "hierarchy_support",
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
    "boundary_guardrail": {
        "visual_thesis": (
            "Use the relationship between the core capability and its guardrails to prove "
            "that scope and responsibility are clear."
        ),
        "decision_relationship": (
            "The core capability occupies the defined scope, while non-goals and constraints "
            "form a secondary guardrail rather than another peer module."
        ),
        "recommended_composition": (
            "Give the core capability dominant visual weight and compress boundaries into a "
            "peripheral, bottom, or side guardrail that clearly remains subordinate."
        ),
        "avoid_on_this_page": (
            "A fifty-fifty can-versus-cannot comparison, warning-card wall, or boundaries "
            "presented as peer service objects."
        ),
    },
    "hierarchy_support": {
        "visual_thesis": (
            "Use vertical dependency to prove that upper-level business results rely on "
            "lower-level capabilities and shared assurance."
        ),
        "decision_relationship": (
            "Upper-level results depend on lower-level capabilities; shared assurance acts "
            "as a foundation or cross-cutting support, not as a software technology stack."
        ),
        "recommended_composition": (
            "Make the upper-level business result the visual center, organize lower-level "
            "capabilities as unequal support, and treat cross-cutting assurance as a base or guardrail."
        ),
        "avoid_on_this_page": (
            "A software architecture stack, equal-height layer bars, one card per layer, "
            "or an isolated capability inventory."
        ),
    },
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

VISUAL_PROOF_FALLBACKS: dict[str, str] = {
    "boundary_guardrail": "用主体能力与外围护栏的关系证明范围和职责清晰。",
    "hierarchy_support": "用上层业务结果与下层支撑能力的依赖关系证明体系能够成立。",
    "decision_admission": "用选择依据与后续准入条件证明当前决策合理。",
    "comparison": "用共同维度下的差异和主次证明本页判断。",
    "scenario_application": "用真实业务场景、业务价值与进入条件证明应用方向。",
    "multi_semantic_foundation": "用多项现实基础共同支撑本页判断。",
    "causal": "用原因到业务后果的传导关系证明行动必要性。",
    "closed_loop": "用输入、结果、验证与反馈的闭环证明业务能够持续改进。",
    "phase": "用阶段目的与准入条件的递进证明实施节奏。",
    "capability_relationship": "用多项能力共同作用于同一业务结果证明协同关系。",
    "judgment_evidence": "用主判断与支撑证据的直接关系完成证明。",
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
    presentation: PresentationDecision | None = None
    image_locked_text: str = ""
    editable_body_text: str = ""

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
        if self.presentation is not None:
            payload["presentation"] = self.presentation.to_dict()
        if self.image_locked_text:
            payload["image_locked_text"] = self.image_locked_text
        if self.editable_body_text:
            payload["editable_body_text"] = self.editable_body_text
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


ONSCREEN_JUDGMENT_MODES = ("locked", "semantic_only")


def resolve_onscreen_judgment_mode(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    mode = str(
        (visual_context or {}).get("onscreen_judgment_mode")
        or page.onscreen_judgment_mode
    ).strip()
    role = str(
        (visual_context or {}).get("judgment_role")
        or page.judgment_role
    ).strip()
    try:
        return resolve_judgment_mode(mode, role)
    except ValueError as exc:
        raise ValueError(
            f"{page.page_id} has invalid judgment display policy: {exc}"
        ) from exc


def locked_onscreen_text(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    """Return only verbatim-critical visible copy; keep the rest semantically flexible."""

    locked: list[str] = []
    if (
        resolve_onscreen_judgment_mode(page, visual_context) == "locked"
        and page.onscreen_judgment.strip()
    ):
        locked.append(page.onscreen_judgment.strip())
    for title in page.module_titles:
        label = title.strip()
        if label and label not in locked:
            locked.append(label)
    for raw in _clean_onscreen_for_imagegen(page.onscreen_text).splitlines():
        line = raw.strip()
        if not line or line in locked:
            continue
        if re.search(r"\d", line):
            locked.append(line)
    return "\n".join(locked).strip()


MAX_IMAGE_LOCKED_LINES = 7
MAX_IMAGE_LOCKED_LINE_CHARS = 14
MAX_IMAGE_LOCKED_CHARS = 84


def select_image_locked_text(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    """Return short, bitmap-safe text while leaving body copy editable."""

    raw = page.image_locked_text.strip() or locked_onscreen_text(page, visual_context)
    if not raw and not page.field_order and page.title.strip():
        # Older free-form final scripts do not expose structured fields.  Keep
        # their page heading as the minimal safe visible anchor.
        raw = page.title.strip()
    candidates = [line.strip(" -*") for line in raw.splitlines() if line.strip()]
    selected: list[str] = []
    total = 0
    for line in candidates:
        compact = re.sub(r"\s+", "", line)
        if not compact or line in selected:
            continue
        if len(compact) > MAX_IMAGE_LOCKED_LINE_CHARS:
            # Numeric fact lines often carry a long explanatory tail.  Preserve
            # the compact fact as bitmap copy and leave the tail editable.
            if re.search(r"\d", compact):
                shortened = re.split(r"[，,；;。]", line, maxsplit=1)[0].strip()
                if shortened and len(re.sub(r"\s+", "", shortened)) <= MAX_IMAGE_LOCKED_LINE_CHARS:
                    line = shortened
                    compact = re.sub(r"\s+", "", line)
                else:
                    continue
            else:
                continue
        if len(selected) >= MAX_IMAGE_LOCKED_LINES or total + len(compact) > MAX_IMAGE_LOCKED_CHARS:
            continue
        selected.append(line)
        total += len(compact)
    return "\n".join(selected).strip()


def render_presentation_contract(
    page: ScriptPage,
    decision: PresentationDecision,
) -> str:
    if decision.source != "script":
        return ""
    return "\n".join(
        (
            "【人工版式覆盖｜不上屏】",
            f"版式母题：{page.layout_motif.strip() or decision.layout_motif}。",
            f"场景角色：{page.scene_role.strip() or decision.scene_role}。",
            "该覆盖只约束本页表达方式，不得删除完整上屏内容或改变业务关系。",
        )
    )


STYLE_COLOR_LABELS = (
    ("background", "背景"),
    ("title", "主文字"),
    ("body", "正文"),
    ("secondary", "次级文字"),
    ("divider", "线条与分隔"),
    ("accent", "强调色"),
)

# ImageGen must receive the governing Style 09 text-first constraints, not only
# its palette and a short mood signature.  These fields are compact enough to
# preserve the intended presentation language while preventing a stale project
# lock from drifting into scenes, illustrations, or icon treatment as defaults.
CONTENT_FIRST_STYLE_RULE_FIELDS: tuple[str, ...] = (
    "scope_rule",
    "content_visual_rule",
    "icon_rule",
)

LAYOUT_MOTIFS = (
    "control_room_bridge",
    "evidence_landscape",
    "decision_canvas",
    "process_atlas",
    "layered_system",
)
SCENE_ROLES = ("primary_scene", "supporting_evidence", "no_scene")
MOTIF_CANDIDATES: dict[str, tuple[str, str]] = {
    "boundary_guardrail": ("decision_canvas", "evidence_landscape"),
    "decision_admission": ("decision_canvas", "evidence_landscape"),
    "comparison": ("decision_canvas", "evidence_landscape"),
    "hierarchy_support": ("layered_system", "control_room_bridge"),
    "capability_relationship": ("layered_system", "control_room_bridge"),
    "phase": ("process_atlas", "evidence_landscape"),
    "causal": ("process_atlas", "evidence_landscape"),
    "closed_loop": ("control_room_bridge", "process_atlas"),
    "scenario_application": ("control_room_bridge", "process_atlas"),
    "judgment_evidence": ("evidence_landscape", "decision_canvas"),
    "multi_semantic_foundation": ("evidence_landscape", "decision_canvas"),
}
DEFAULT_SCENE_ROLE_BY_MOTIF = {
    "control_room_bridge": "primary_scene",
    "evidence_landscape": "supporting_evidence",
    "decision_canvas": "no_scene",
    "process_atlas": "no_scene",
    "layered_system": "supporting_evidence",
}


@dataclass(frozen=True)
class PresentationDecision:
    """Content-led visual variation decision recorded with every prompt."""

    layout_motif: str
    scene_role: str
    source: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "layout_motif": self.layout_motif,
            "scene_role": self.scene_role,
            "source": self.source,
            "reason": self.reason,
        }


def resolve_presentation_decision(
    page: ScriptPage,
    relation: str,
    prior_decisions: tuple[PresentationDecision, ...] = (),
) -> PresentationDecision:
    """Choose a content-led motif while preventing batch-level repetition."""

    explicit_motif = page.layout_motif.strip()
    explicit_scene = page.scene_role.strip()
    if explicit_motif and explicit_motif not in LAYOUT_MOTIFS:
        raise ValueError(f"{page.page_id} has unsupported 版式母题: {explicit_motif}")
    if explicit_scene and explicit_scene not in SCENE_ROLES:
        raise ValueError(f"{page.page_id} has unsupported 场景角色: {explicit_scene}")

    candidates = MOTIF_CANDIDATES.get(relation, ("evidence_landscape", "decision_canvas"))
    previous_motif = prior_decisions[-1].layout_motif if prior_decisions else ""
    motif = explicit_motif or next(
        (candidate for candidate in candidates if candidate != previous_motif),
        candidates[0],
    )
    scene_role = explicit_scene or DEFAULT_SCENE_ROLE_BY_MOTIF[motif]
    recent_primary_count = sum(
        decision.scene_role == "primary_scene" for decision in prior_decisions[-3:]
    )
    if not explicit_scene and scene_role == "primary_scene" and recent_primary_count >= 2:
        scene_role = "supporting_evidence"
    source = "script" if explicit_motif or explicit_scene else "auto"
    reason = (
        "explicit page presentation override"
        if source == "script"
        else f"{relation} candidates: {', '.join(candidates)}"
    )
    return PresentationDecision(motif, scene_role, source, reason)


def _selected_content_first_style(style_lock: Path) -> dict[str, Any]:
    """Load a selected style with a non-weakenable Style 09 baseline.

    Project locks are snapshots and older Style 09 locks may contain experimental
    scene-first wording.  Preserve their selected palette, but always compile
    Style 09 from the canonical library contract so a historical lock cannot
    silently weaken the text-led, single-medium presentation rules.
    """

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
    if int(style.get("id") or 0) != 9:
        return style
    canonical = resolve_default_style(style_id=9)
    canonical["colors"] = dict(colors)
    return canonical


def render_content_first_style_contract(style_lock: Path) -> str:
    """Render a compact, self-contained style contract from the selected style."""

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
    lines = [
        "【输出与风格｜不上屏】",
        f"适用语境：{str(style.get('scenario') or '').strip()}。",
        f"色彩角色：{'；'.join(color_parts)}。",
    ]
    style_rules = [
        str(style.get(field) or "").strip()
        for field in CONTENT_FIRST_STYLE_RULE_FIELDS
        if str(style.get(field) or "").strip()
    ]
    if style_rules:
        lines.append("风格约定（仅约束视觉表达，不覆盖本页内容与主导关系）：")
        lines.extend(f"- {rule}" for rule in style_rules)
    signature = style.get("imagegen_signature")
    if isinstance(signature, list):
        compact_signature = [
            str(rule).strip()
            for rule in signature
            if isinstance(rule, str) and rule.strip()
        ]
        if compact_signature:
            lines.append("审美签名：")
            lines.extend(f"- {rule}" for rule in compact_signature)
    lines.append("整体呈现现代中文高端政企汇报设计气质，编辑式克制、业务清晰。")
    lines.append("如出现人物，仅使用远景、背影或局部，不出现可识别面孔。")
    return "\n".join(lines)


def render_page_logic_contract(
    page: ScriptPage,
    *,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Render one explicit relationship contract before text and imagery are arranged."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=visual_context,
        override=visual_intent_override,
    )
    values = dict(VISUAL_INTENT_TEMPLATES[relation])
    if isinstance(visual_intent_override, dict):
        for key in values:
            value = visual_intent_override.get(key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
    relation_labels = {
        "boundary_guardrail": "边界护栏",
        "hierarchy_support": "分层支撑",
        "decision_admission": "决策准入",
        "comparison": "对照",
        "scenario_application": "场景应用",
        "multi_semantic_foundation": "共同支撑",
        "causal": "因果传导",
        "closed_loop": "闭环",
        "phase": "阶段递进",
        "capability_relationship": "能力协同",
        "judgment_evidence": "判断—证据",
    }
    contract = "\n".join(
        (
            "【页面逻辑｜不上屏】",
            f"主导关系：{relation_labels[relation]}。",
            "视觉证明："
            + str(
                page.visual_proof
                or (visual_intent_override or {}).get("visual_proof")
                or (visual_context or {}).get("visual_proof")
                or VISUAL_PROOF_FALLBACKS[relation]
            ).strip(),
            f"空间组织：{values['recommended_composition']}",
            f"本页避免：{values['avoid_on_this_page']}",
        )
    )
    return relation, contract


def render_content_first_prompt(
    page: ScriptPage,
    *,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    presentation_decision: PresentationDecision | None = None,
) -> tuple[str, str]:
    """Render a complete-content prompt without translating meaning into layout."""

    # Structured scripts require an explicit conclusion.  Preserve execution
    # compatibility for older free-form final scripts by using their heading as
    # a minimal anchor; their full content remains owned by the template layer.
    if page.page_type == "content" and not page.onscreen_judgment.strip() and page.field_order:
        raise ValueError(
            f"{page.page_id} is missing 上屏结论; repair and reapprove the final "
            "script before compiling an ImageGen prompt"
        )
    judgment_mode = resolve_onscreen_judgment_mode(page, visual_context)
    onscreen = diagnostic_onscreen_text(page, "content-first-v1")
    onscreen_body = _flatten_markdown_tables(
        _clean_onscreen_for_imagegen(page.onscreen_text)
    )
    locked = select_image_locked_text(page, visual_context)
    judgment_for_semantics = page.onscreen_judgment.strip()
    if not judgment_for_semantics and not onscreen_body and not page.main_message.strip():
        judgment_for_semantics = page.title.strip()
    complete_semantics = "\n\n".join(
        part
        for part in (
            judgment_for_semantics,
            onscreen_body,
        )
        if part
    )
    relation, logic_contract = render_page_logic_contract(
        page,
        page_mission=page_mission,
        visual_context=visual_context,
        visual_intent_override=visual_intent_override,
    )
    presentation = presentation_decision or resolve_presentation_decision(
        page,
        relation,
    )
    parts = [
        "【页面任务｜仅供理解，不上屏】",
        page_mission.strip() or page.main_message.strip(),
        "",
        "【核心判断｜仅供理解】",
        page.main_message.strip(),
        "",
        logic_contract,
        "",
        render_presentation_contract(page, presentation),
        "",
        "【完整上屏内容】",
        complete_semantics,
        "",
        (
            CONTENT_FIRST_ONSCREEN_STORY_CONTRACT
            if judgment_mode == "locked"
            else (
                CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT
                if locked
                else CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT
            )
        ),
        "",
        (
            CONTENT_FIRST_FORMAL_OUTPUT_CONTRACT
            if locked
            else CONTENT_FIRST_SEMANTIC_ONLY_OUTPUT_CONTRACT
        ),
        "",
        render_content_first_style_contract(style_lock),
    ]
    if locked:
        semantics_index = parts.index("【完整上屏内容】")
        parts[semantics_index:semantics_index] = [
            "【锁定关键文字】",
            locked,
            "",
        ]
    return relation, "\n".join(parts).strip() + "\n"


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
        "visual_center",
        "visual_proof",
        "visual_intent_type",
        "onscreen_judgment_mode",
        "judgment_role",
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
        "visual_proof",
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
    prior_decisions: tuple[PresentationDecision, ...] = (),
) -> CompiledPagePrompt:
    if prompt_compiler not in PROMPT_COMPILERS:
        raise ValueError(
            f"unsupported prompt compiler: {prompt_compiler}; "
            f"choose one of {', '.join(PROMPT_COMPILERS)}"
        )
    if prompt_compiler == "content-first-v1":
        selected_style = _selected_content_first_style(style_lock)
        relation = select_page_visual_intent_type(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        presentation = resolve_presentation_decision(
            page,
            relation,
            prior_decisions,
        )
        relation, prompt = render_content_first_prompt(
            page,
            style_lock=style_lock,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=visual_intent_override,
            presentation_decision=presentation,
        )
        assert_deliverable_prompt(prompt)
        if EVIDENCE_ID_RE.search(prompt):
            raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
        return CompiledPagePrompt(
            prompt=prompt,
            compiler_version=prompt_compiler,
            relation=relation,
            injected_rule_ids=(
                "content.page_task",
                "content.core_judgment",
                "content.full_semantics",
                "content.page_logic_contract",
                "content.locked_key_copy",
                "content.complete_page_semantics",
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
            presentation=presentation,
            image_locked_text=select_image_locked_text(page, visual_context),
            editable_body_text=page.onscreen_text.strip(),
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
            "text.locked_key_copy_exact",
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

    if prompt_compiler == "content-first-v1":
        compilation_rules = [
            "- 每页独立完整，可直接送入 ImageGen，不依赖批次级公共提示。",
            "- 送入：页面任务、核心判断、精简页面逻辑、锁定关键文字、完整页面语义、短文字视觉规则，以及所选风格的适用语境和配色。",
            "- 不送入：源材料全文、完整事实边界或重复设计理论。",
            "- 不送入：证据编号、讲解提示、文字取舍、图片数量或后期制作规则。",
            "- 页面任务、核心判断和页面逻辑只用于理解与构图；锁定关键文字逐字准确，完整上屏内容均需进入 full 图。",
        ]
    else:
        compilation_rules = [
            "- 送入：页面使命、核心判断、上屏文字，以及页面级视觉意图。",
            "- 不送入：边界/Boundary/禁止项、完整文字稿、取舍说明、证据映射、证据编号、视觉结构、讲解提示。",
            "- 页面使命、核心判断与页面级视觉意图只作为理解和构图上下文；不要把字段名或说明文字渲染到画面，正文文字以“上屏文字”为准。",
        ]

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
        *compilation_rules,
        "- 封面/目录/章节过渡/封底：不生成正文区 ImageGen，由模板层承载。",
        "",
    ]
    outputs: dict[str, Path] = {}
    content_prompts: list[str] = []
    diagnostics: list[PagePromptDiagnostics] = []
    prior_decisions: list[PresentationDecision] = []
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
            prior_decisions=tuple(prior_decisions),
        )
        if compiled.presentation is not None:
            prior_decisions.append(compiled.presentation)
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
                prior_decisions=tuple(prior_decisions[:-1]),
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
        review_parts.extend(
            [
                f"## 第{page_number}页：{page.title or page.page_id}",
                "",
                prompt,
                "",
            ]
        )

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

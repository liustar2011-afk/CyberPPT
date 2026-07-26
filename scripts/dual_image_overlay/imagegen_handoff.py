#!/usr/bin/env python3
"""Build reviewable ImageGen handoff prompts from approved final scripts.

Before any ImageGen call, CyberPPT must:
1. extract only drawable layers from the final script (上屏文字);
2. compile plaintext prompts with the project visual lock;
3. save them under workbench/prompts/imagegen/;
4. wait for user modify-or-approve.

Page mission and thesis (页面使命 / 主判断 / 核心判断) are passed before 上屏文字
so the model can understand the page question and organize the visual mainline.
They are context fields, not extra labels to render; the drawable text layer remains 上屏文字.
Page-specific visual intent is compiled after 上屏文字 and before the global style
contract. It explains the page relationship and composition without adding drawable text.
Boundary / 边界 is authoring + human QA only; do not send invisible boundary prose to ImageGen —
rely on well-authored 上屏文字. 完整文字稿、取舍说明、证据映射、证据编号、视觉结构与讲解提示
must not enter ImageGen prompts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cyberppt.commands.script_gate import stage_script
from cyberppt.script_quality_contract import ScriptPage, parse_script_markdown
from scripts.dual_image_overlay.deliverable_prompt import (
    PageBlock,
    assert_deliverable_prompt,
    render_prompt,
)

EVIDENCE_ID_RE = re.compile(r"S\d{3}")
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

VISUAL_INTENT_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("decision_admission", ("筛选", "选择", "首期", "后续", "准入")),
    ("comparison", ("对比", "比较", "差异", "优劣", "高于", "低于", "相较")),
    ("scenario_application", ("场景", "应用", "应用方向", "推进条件")),
    ("causal", ("问题", "原因", "影响", "需求", "为什么")),
    ("closed_loop", ("输入", "处理", "输出", "反馈", "复盘", "闭环")),
    ("phase", ("当前", "近期", "中长期", "阶段", "分期")),
    (
        "capability_relationship",
        ("能力协同", "协同支撑", "共同支撑", "能力关系", "能力体系", "能力底座"),
    ),
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
            "Give the selected initial scope dominant visual weight; use compact criteria "
            "evidence to support it, and place later scope in a secondary gated-entry area."
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
            "Use an aligned comparison structure with one clear basis, visible differences, "
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
            "Use one integrated real-work context with compact business-value and readiness evidence."
        ),
        "avoid_on_this_page": (
            "A product-feature showcase, scenario thumbnail wall, decorative industry photo, "
            "or unrelated technology interface."
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
            "Use one dominant consequence supported by compact causal evidence."
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
            "Use one integrated operational loop anchored in a real work context."
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
            "Give the current or near-term decision primary weight and later stages secondary weight."
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
            "Use a relationship-led capability composition with business value as the outcome "
            "and supporting capabilities in unequal roles."
        ),
        "avoid_on_this_page": (
            "A generic architecture stack, center-satellite nodes, equal capability cards, "
            "or a software-module diagram."
        ),
    },
    "judgment_evidence": {
        "visual_thesis": "Express the page as one judgment supported by evidence.",
        "decision_relationship": (
            "Supporting modules jointly explain or substantiate the core judgment."
        ),
        "recommended_composition": (
            "Use one dominant judgment area with compact, unequal-weight supporting evidence."
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


def build_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
) -> str:
    """Compile deterministic, non-rendering page-specific composition guidance."""

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no visual intent")
    signal_text = "\n".join(
        (
            page_mission,
            page.main_message,
            "\n".join(page.module_titles),
            page.onscreen_text,
        )
    )
    relation = "judgment_evidence"
    for candidate, signals in VISUAL_INTENT_SIGNALS:
        if any(signal in signal_text for signal in signals):
            relation = candidate
            break
    values = dict(VISUAL_INTENT_TEMPLATES[relation])
    if isinstance(override, dict):
        for key in values:
            value = override.get(key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
    return "\n".join(
        (
            "[Prompt context] Page-specific visual intent "
            "(composition guidance only; do not render field names or instruction text)",
            f"- Visual thesis: {values['visual_thesis']}",
            f"- Decision relationship: {values['decision_relationship']}",
            f"- Recommended composition: {values['recommended_composition']}",
            f"- Avoid on this page: {values['avoid_on_this_page']}",
        )
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


def _page_visual_intent_overrides(project: Path) -> dict[str, dict[str, str]]:
    outline_path = project / "workbench" / "stages" / "01-analysis" / "outline.json"
    if not outline_path.is_file():
        return {}
    payload = json.loads(outline_path.read_text(encoding="utf-8-sig"))
    pages = payload.get("pages") if isinstance(payload, dict) else None
    if not isinstance(pages, list):
        return {}
    allowed = VISUAL_INTENT_TEMPLATES["judgment_evidence"].keys()
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


def build_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_intent_override: dict[str, str] | None = None,
) -> str:
    prompt_text = "\n".join(
        (
            content_lock_text(page, page_mission=page_mission).rstrip(),
            "",
            build_page_visual_intent(
                page,
                page_mission,
                override=visual_intent_override,
            ),
        )
    )
    block = PageBlock(
        page_number=int(page.page_id[1:]),
        title=page.title or page.page_id,
        text=prompt_text,
    )
    prompt = render_prompt(block, style_lock_path=style_lock)
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
    return prompt


def write_chapter_handoff(
    *,
    project: Path,
    script: Path,
    style_lock: Path,
    pages: list[int],
    batch_name: str,
) -> dict[str, Path]:
    document = parse_script_markdown(script.read_text(encoding="utf-8"))
    by_num = {int(page.page_id[1:]): page for page in document.pages}
    missions = _page_missions(project)
    visual_intent_overrides = _page_visual_intent_overrides(project)
    out_dir = project / "workbench" / "prompts" / "imagegen"
    out_dir.mkdir(parents=True, exist_ok=True)

    review_parts: list[str] = [
        f"# ImageGen 送图脚本审阅稿 · {batch_name}",
        "",
        "> 状态：等待用户修改或批准。未经批准不得进入 ImageGen。",
        f"> 源脚本：`{script.as_posix()}`",
        f"> 风格锁定：`{style_lock.as_posix()}`",
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

        prompt = build_page_prompt(
            page,
            style_lock,
            page_mission=missions.get(page.page_id, ""),
            visual_intent_override=visual_intent_overrides.get(page.page_id),
        )
        content_prompts.append(prompt)
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
    )
    print(f"batch_review={outputs['batch']}")
    print(f"gate={outputs['gate']}")
    for key, path in sorted(outputs.items()):
        if key.startswith("p"):
            print(f"{key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

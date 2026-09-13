"""Qualitative PLAN-Critic context and conservative priority findings."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


_SUMMARY_CONNECTOR_RE = re.compile(r"(?:明确|构成|提供|形成|包括|涵盖).{0,28}(?:，|、).{0,40}(?:明确|构成|提供|形成|包括|涵盖)")
_STRUCTURAL_ROLES = {"cover", "agenda", "contents", "chapter", "chapter_divider", "transition", "ending", "closing"}
_GENERIC_MISSION_RE = re.compile(r"^(?:说明|介绍|呈现|梳理|明确)(?:相关|有关|主要)?(?:内容|情况|工作|事项)[。.]?$")

DELIVERY_MODE_LABELS = {"presented": "演讲辅助", "self_read": "独立阅读"}
SINGLE_CORE_GUIDANCE = (
    "一页只表达一项核心内容，两种用途共同遵守。页面问题与使命围绕同一业务主题；"
    "支撑同一主题的多条事实、并列事项或完整流程可以同页，独立主题应拆分。"
    "核心内容无需写成结论；来源没有总判断时保留来源结构。"
)
PAGINATION_GUIDANCE = {
    "presented": "围绕单页核心内容核对讲解负担，突出关键支撑，展开解释由讲解补充；保留影响准确理解的关键条件。复杂主题可按子问题拆分。",
    "self_read": "围绕单页核心内容补足阅读所需上下文、解释与条件；仅合并服务于同一核心内容的信息，独立主题分别分页。复杂主题可按子问题拆分。",
}


def validate_plan_purpose(plan: dict[str, Any]) -> list[str]:
    """Require an explicit purpose and its pagination rationale in current plans."""
    issues = []
    if plan.get("delivery_mode") not in ("presented", "self_read"):
        issues.append("PLAN_DELIVERY_MODE_REQUIRED: 请先向用户明确演讲辅助或独立阅读，并填写 delivery_mode")
    rationale = plan.get("pagination_rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        issues.append("PLAN_PAGINATION_RATIONALE_REQUIRED: 请说明所选用途对应的页面范围及拆分合并理由")
    return issues


def validate_delivery_mode_alignment(final_script: dict[str, Any], plan: dict[str, Any] | None) -> list[str]:
    """Keep explicitly planned purpose through AUTHOR and Stage 02 delivery."""
    plan = plan or {}
    if "delivery_mode" not in plan and plan.get("plan_contract_version") != 2:
        return []  # Historical contracts retain their own delivery policy.
    issues = validate_plan_purpose(plan)
    deck = final_script.get("deck")
    actual = deck.get("delivery_mode") if isinstance(deck, dict) else None
    if actual != plan.get("delivery_mode") or actual not in ("presented", "self_read"):
        issues.append("FINAL_DELIVERY_MODE_MISMATCH: 最终脚本 deck.delivery_mode 必须与已确认规划一致")
    return issues


def plan_critic_priorities(plan: dict[str, Any]) -> list[dict[str, str]]:
    """Return v2 lean pages that need qualitative review; never rewrite prose."""

    pages = [page for page in plan.get("pages") or [] if isinstance(page, dict)]
    content = [page for page in pages if str(page.get("page_role") or "") not in _STRUCTURAL_ROLES]
    findings: list[dict[str, str]] = []
    for page in content:
        page_id = str(page.get("id") or "?")
        logic = str(page.get("logic") or "").strip()
        if _GENERIC_MISSION_RE.fullmatch(logic):
            findings.append({
                "code": "PLAN_MISSION_GENERIC",
                "page_id": page_id,
                "reason": "页面使命缺少具体业务对象，请明确内容范围、页面职责及相邻页分工；无需预写核心判断",
            })
        if _SUMMARY_CONNECTOR_RE.search(logic):
            findings.append({
                "code": "PLAN_LOGIC_COVERAGE_SUMMARY",
                "page_id": page_id,
                "reason": "页面使命疑似串联多个来源事项，需要 Critic 判断是否混合了不同页面问题",
            })
        question = str(page.get("question") or "")
        # Multiple interrogatives and chained missions are review signals only:
        # they can legitimately describe one process or tightly related subject.
        if _SUMMARY_CONNECTOR_RE.search(logic) or len(re.findall(r"[^？?]+[？?]", question)) > 1:
            findings.append({
                "code": "PLAN_SINGLE_CORE_REVIEW",
                "page_id": page_id,
                "reason": "页面问题或使命疑似混合多个主题，请对照来源判断是否服务于同一项核心内容；独立主题应拆分，同一主题的多条支撑可保留。两种用途执行相同原则。",
            })
        if not page.get("source_refs"):
            findings.append({
                "code": "PLAN_PAGE_WITHOUT_EVIDENCE",
                "page_id": page_id,
                "reason": "页面没有来源边界，无法执行来源忠实度审阅",
            })
    for left, right in zip(content, content[1:]):
        shared = set(left.get("source_refs") or []).intersection(right.get("source_refs") or [])
        if shared and plan.get("delivery_mode") == "self_read":
            findings.append({
                "code": "PLAN_SELF_READ_CONTINUITY_REVIEW",
                "page_id": f"{left.get('id') or '?'}->{right.get('id') or '?'}",
                "reason": f"独立阅读相邻页共享来源 {', '.join(sorted(shared))}，请核对各页核心内容及其解释与条件是否完整；仅服务于同一核心内容的信息可考虑合并，共享来源不直接裁定合并",
            })
        similarity = SequenceMatcher(
            None, str(left.get("logic") or ""), str(right.get("logic") or "")
        ).ratio()
        if similarity >= 0.82:
            findings.append({
                "code": "PLAN_ADJACENT_ARGUMENT_REPEAT",
                "page_id": f"{left.get('id') or '?'}->{right.get('id') or '?'}",
                "reason": f"相邻页面使命相似度 {similarity:.0%}，需核对页面边界和分工；相似度不直接裁定合并",
            })
    return findings


def build_plan_critic_context(plan: dict[str, Any]) -> dict[str, Any]:
    """Assemble the one-pass whole-plan review context for a generative Critic."""

    return {
        "communication_goal": plan.get("communication_goal"),
        "delivery_mode": plan.get("delivery_mode"),
        "pagination_rationale": plan.get("pagination_rationale"),
        "single_core_guidance": SINGLE_CORE_GUIDANCE,
        "pagination_guidance": PAGINATION_GUIDANCE.get(str(plan.get("delivery_mode")), "用途待明确，先完成用途提问再确定分页。"),
        "authoring_mode": plan.get("authoring_mode", "faithful"),
        "audience": plan.get("audience"),
        "source_structure_mode": plan.get("source_structure_mode"),
        "pages": [
            {
                key: page.get(key)
                for key in (
                    "id", "title", "question", "logic", "page_role", "source_refs",
                )
            }
            for page in plan.get("pages") or []
            if isinstance(page, dict)
        ],
        "priorities": plan_critic_priorities(plan),
        "review_dimensions": [
            "一页一项核心内容", "用途与分页适配", "页面必要性", "标题与来源力度", "页面问题归属", "使命边界", "相邻重复", "叙事连续性",
        ],
    }


__all__ = ["build_plan_critic_context", "plan_critic_priorities"]

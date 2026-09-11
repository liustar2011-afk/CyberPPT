"""Qualitative PLAN-Critic context and conservative priority findings."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


_SUMMARY_CONNECTOR_RE = re.compile(r"(?:明确|构成|提供|形成|包括|涵盖).{0,28}(?:，|、).{0,40}(?:明确|构成|提供|形成|包括|涵盖)")
_STRUCTURAL_ROLES = {"cover", "agenda", "contents", "chapter", "transition", "ending", "closing"}
_GENERIC_MISSION_RE = re.compile(r"^(?:说明|介绍|呈现|梳理|明确)(?:相关|有关|主要)?(?:内容|情况|工作|事项)[。.]?$")


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
        if not page.get("source_refs"):
            findings.append({
                "code": "PLAN_PAGE_WITHOUT_EVIDENCE",
                "page_id": page_id,
                "reason": "页面没有来源边界，无法执行来源忠实度审阅",
            })
    for left, right in zip(content, content[1:]):
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
            "页面必要性", "标题与来源力度", "页面问题归属", "使命边界", "相邻重复", "叙事连续性",
        ],
    }


__all__ = ["build_plan_critic_context", "plan_critic_priorities"]

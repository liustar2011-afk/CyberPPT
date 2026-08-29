"""Qualitative PLAN-Critic context and conservative priority findings."""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


_SUMMARY_CONNECTOR_RE = re.compile(r"(?:明确|构成|提供|形成|包括|涵盖).{0,28}(?:，|、).{0,40}(?:明确|构成|提供|形成|包括|涵盖)")
_STRUCTURAL_ROLES = {"cover", "agenda", "contents", "chapter", "transition", "ending", "closing"}


def plan_critic_priorities(plan: dict[str, Any]) -> list[dict[str, str]]:
    """Return pages that need qualitative review; findings never rewrite prose."""

    pages = [page for page in plan.get("pages") or [] if isinstance(page, dict)]
    content = [page for page in pages if str(page.get("page_role") or "") not in _STRUCTURAL_ROLES]
    findings: list[dict[str, str]] = []
    for page in content:
        page_id = str(page.get("id") or "?")
        message = str(page.get("message") or "").strip()
        if _SUMMARY_CONNECTOR_RE.search(message):
            findings.append({
                "code": "PLAN_MESSAGE_COVERAGE_SUMMARY",
                "page_id": page_id,
                "reason": "核心判断疑似把页内模块串成来源覆盖摘要，需要 Critic 判断页面的取舍与认知收益",
            })
        if not str(page.get("beat") or "").strip():
            findings.append({
                "code": "PLAN_BEAT_MISSING",
                "page_id": page_id,
                "reason": "页面未声明相对前后页推进的论证节拍",
            })
        if not (page.get("proof") or {}).get("evidence_refs") and not page.get("source_refs"):
            findings.append({
                "code": "PLAN_PAGE_WITHOUT_EVIDENCE",
                "page_id": page_id,
                "reason": "页面没有可见的证据投入，无法判断核心结论是否成立",
            })
    for left, right in zip(content, content[1:]):
        similarity = SequenceMatcher(
            None, str(left.get("message") or ""), str(right.get("message") or "")
        ).ratio()
        if similarity >= 0.82:
            findings.append({
                "code": "PLAN_ADJACENT_ARGUMENT_REPEAT",
                "page_id": f"{left.get('id') or '?'}->{right.get('id') or '?'}",
                "reason": f"相邻核心判断相似度 {similarity:.0%}，需要重写页面边界或合并",
            })
    return findings


def build_plan_critic_context(plan: dict[str, Any]) -> dict[str, Any]:
    """Assemble the one-pass whole-plan review context for a generative Critic."""

    return {
        "thesis": plan.get("thesis"),
        "narrative_design": plan.get("narrative_design"),
        "peak_page_id": (plan.get("narrative_design") or {}).get("peak_page_id"),
        "pages": [
            {
                key: page.get(key)
                for key in (
                    "id", "title", "question", "message", "page_role", "beat",
                    "source_argument_node_ids", "source_refs", "proof", "receives", "next",
                )
            }
            for page in plan.get("pages") or []
            if isinstance(page, dict)
        ],
        "priorities": plan_critic_priorities(plan),
        "review_dimensions": [
            "页面必要性", "核心判断力度", "证据选择", "相邻重复", "叙事连续性", "高潮页",
        ],
    }


__all__ = ["build_plan_critic_context", "plan_critic_priorities"]

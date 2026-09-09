"""Validation contract for the Stage 02 visual thesis.

A visual thesis states what relationship the image must make legible.  It is
not a second copy of the page judgment and it is never synthesized as a
fallback by the compiler.
"""
from __future__ import annotations

from difflib import SequenceMatcher
import re


_RELATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"从.+到"),
    re.compile(r"由.+(?:形成|汇聚|支撑|连接|进入|转化)"),
    re.compile(r"围绕.+(?:形成|展开|连接|组织)"),
    re.compile(r"(?:汇聚|汇入|收敛|连接|支撑|承接|流向|进入|经过|作用于|反馈|回流|映射|对应|依赖|分配|传递|交换|联动|转化|贯穿)"),
    re.compile(r"(?:边界|接口|门控).+(?:连接|控制|约束|进入|输出|交换|关系)"),
    re.compile(r"(?:输入|来源).+(?:处理|服务|能力|结果|输出)"),
    re.compile(r"(?:主体|角色|参与方).+(?:关系|接口|交换|结果|协作|承接)"),
    re.compile(r"\b(?:from|through|into|between|converge|connect|support|flow|feedback|return|map|depend|interface|boundary|exchange|transform|allocate)\b", re.I),
)


def _normalized(text: str) -> str:
    return re.sub(r"[\s，。；：、,.!?！？—–\-（）()【】\[\]‘’“”\"']+", "", str(text or "")).casefold()


def thesis_similarity(visual_thesis: str, core_judgment: str) -> float:
    left = _normalized(visual_thesis)
    right = _normalized(core_judgment)
    if not left or not right:
        return 0.0
    return round(SequenceMatcher(None, left, right).ratio(), 3)


def has_relationship_signal(visual_thesis: str) -> bool:
    text = str(visual_thesis or "").strip()
    return any(pattern.search(text) for pattern in _RELATION_PATTERNS)


def validate_visual_thesis(visual_thesis: object, core_judgment: object) -> str:
    """Validate that the thesis is independent and relational.

    The compiler intentionally does not infer or repair a missing thesis.  A
    failed contract returns upstream to the visual-structure decision step.
    """

    thesis = str(visual_thesis or "").strip()
    judgment = str(core_judgment or "").strip()
    if not thesis:
        raise ValueError(
            "VISUAL_THESIS_REQUIRED: selected candidate must provide a visual_thesis; "
            "the compiler cannot fall back to core_judgment."
        )
    similarity = thesis_similarity(thesis, judgment)
    if judgment and similarity >= 0.90:
        raise ValueError(
            "VISUAL_THESIS_DUPLICATES_CORE_JUDGMENT: visual_thesis must describe the "
            f"relationship the image proves, not repeat the page judgment; similarity={similarity}."
        )
    if not has_relationship_signal(thesis):
        raise ValueError(
            "VISUAL_THESIS_RELATIONSHIP_MISSING: visual_thesis must state a relationship, "
            "path, dependency, convergence, boundary, exchange, transformation, or other "
            "source-supported relational result that can be made visually legible."
        )
    return thesis


__all__ = ["has_relationship_signal", "thesis_similarity", "validate_visual_thesis"]

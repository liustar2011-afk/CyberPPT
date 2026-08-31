"""Shared deterministic text primitives used by Script Engine semantic checks."""
from __future__ import annotations

import re


SEMANTIC_PREDICATES = (
    "已经", "可以", "需要", "应当", "形成", "明确", "承担", "提供", "覆盖",
    "缺少", "不足", "制约", "推动", "建立", "落实", "决定", "负责", "规范",
    "衔接", "承接", "服务", "完成", "保持", "安排", "界定", "匹配", "促进",
    "实现", "贯通", "增加", "提出", "转化", "构成", "支撑", "保障",
    "导致", "滞后", "已有", "校准", "承载", "对应", "建成", "推进",
    "确立", "体现", "规定", "检验", "固化", "纳入", "发布", "启动",
    "扩展", "接入", "帮助", "辅助", "记录", "采用", "补充", "检查",
)

GENERIC_TRANSFORMATION_CLAIM_RE = re.compile(
    r"(?:"
    r"[一二三四五六七八九十\d]+(?:类|项|方面)(?:体系化|系统化|一体化|综合性|整体性)?"
    r"|(?:体系化|系统化|一体化|综合性|整体性)"
    r")"
    r"(?:建设|举措|措施|工作|机制)"
    r".{0,18}(?:推动|促进|支撑|实现|转化(?:为)?|形成|提升)"
    r".{0,18}(?:能力|体系|水平|效能|基础|服务)$"
)


def normalize_item_text(text: str) -> str:
    """Strip whitespace and punctuation for semantic/similarity comparisons."""

    return re.sub(r"[\s、，,。.；;：:！!？?（）()【】\[\]“”\"'—-]", "", str(text or ""))


def has_complete_semantic_predicate(text: str) -> bool:
    """Return whether normalized text contains a predicate with content on both sides."""

    compact = normalize_item_text(text)
    for predicate in SEMANTIC_PREDICATES:
        start = compact.find(predicate)
        if start >= 2 and len(compact) - start - len(predicate) >= 2:
            return True
    return False


__all__ = [
    "GENERIC_TRANSFORMATION_CLAIM_RE",
    "SEMANTIC_PREDICATES",
    "has_complete_semantic_predicate",
    "normalize_item_text",
]

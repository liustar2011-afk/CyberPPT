"""Focused AUTHOR visible-expression and execution audit helpers."""
from __future__ import annotations

from .common import *


_STATUS_PRESERVATION_MARKERS = {
    "规划": ("拟", "将", "应", "计划", "推动", "制定", "形成", "完成", "开展", "目标", "后续", "需"),
    "建议": ("建议", "应", "可", "宜", "鼓励"),
    "待确认": ("亟需", "需要", "仍需", "尚未", "有待", "不足", "差距", "滞后", "要求"),
}


def _status_strength_preserved(status: str, text: str) -> bool:
    """Preserve modality without leaking internal status labels into prose."""

    if not status:
        return True
    markers = _STATUS_PRESERVATION_MARKERS.get(status)
    if markers is None:
        return True
    return any(marker in text for marker in markers)


def _onscreen_module_lines(module: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    text = module.get("text")
    if isinstance(text, str) and text.strip():
        lines.append(text.strip())
    for item in module.get("items") or []:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
    return lines


def _is_lead_like_evidence_item(value: str) -> bool:
    """Identify a proposition-shaped item that can shadow a forbidden lead."""

    return (
        len(_VISIBLE_CHAR_RE.findall(value)) >= _COMPLETE_PROPOSITION_MIN_CHARS
        and bool(_LEAD_LIKE_EVIDENCE_ITEM_RE.search(value))
    )


def _evidence_first_item_hierarchy_issues(
    slide_id: str, module: dict[str, Any]
) -> list[str]:
    """Reject a hidden module lead placed in the first flat evidence item."""

    items = [
        item.strip()
        for item in module.get("items") or []
        if isinstance(item, str) and item.strip()
    ]
    if len(items) < 2 or not _is_lead_like_evidence_item(items[0]):
        return []
    if all(_is_lead_like_evidence_item(item) for item in items[1:]):
        return []
    heading = str(module.get("heading") or "?").strip()
    return [
        f"{slide_id}: onscreen_composition='evidence_first' module '{heading}' "
        "uses a lead-like first item above lighter peer evidence; rewrite every item "
        "as same-granularity source facts, or use selective_lead when the judgment "
        "must remain inside the module"
    ]


def _is_readable_proposition(line: str) -> bool:
    """Return whether a visible line carries a compact, sentence-like proposition."""

    value = str(line or "").strip()
    if not value or re.search(r"[：:]", value):
        return False
    chars = len(_VISIBLE_CHAR_RE.findall(value))
    has_predicate = bool(
        _LEAD_LIKE_EVIDENCE_ITEM_RE.search(value)
        or re.search(
            r"(已有|已形成|已明确|缺少|不清|不健全|滞后|并存|负责|承担|"
            r"体现|保障|贯穿|统筹|纳入|建立|扩大|持续|具备|属于|仍需|"
            r"回应|界定|提升|形成|连接|约束|支撑|控制|沉淀|拓展|深化|"
            r"承载|驱动|贯通|复用|转化|推进|决定|提供|用于|服务|规范|覆盖|"
            r"增加|定位|实现|保持|验证|反映|降低|审核|审定|履行|判断|构成|"
            r"明确|统一|改善|完善|强化|提高|促进|推动|满足|适应|识别|管理|保护|"
            r"扩展|依托|展示|评估|补充|保留|采用|固化|表达|分析|"
            r"主导|实行|贯通|支持|需要|需做到)",
            value,
        )
    )
    return (
        has_predicate
        and _COMPLETE_PROPOSITION_MIN_CHARS <= chars <= _COMPLETE_PROPOSITION_MAX_CHARS
    )


def _onscreen_expression_warnings(
    page: dict[str, Any], slide: dict[str, Any],
) -> list[str]:
    """Advisory checks for a declared sentence-led or mixed visible expression mode."""

    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict) or "expression_mode" not in contract:
        return []
    mode = str(contract.get("expression_mode") or "").strip()
    if mode not in {"sentence_led", "mixed"}:
        return []

    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    if mode == "sentence_led":
        warnings = []
        for module in modules:
            heading = str(module.get("heading") or "?").strip()
            lines = _onscreen_module_lines(module)
            if not any(_is_readable_proposition(line) for line in lines):
                warnings.append(
                    f"module '{heading}': expression_mode='sentence_led' has no readable proposition; "
                    "add one source-grounded sentence with a subject, predicate and terminal punctuation"
                )
        return warnings

    lines = [line for module in modules for line in _onscreen_module_lines(module)]
    if lines and not any(_is_readable_proposition(line) for line in lines):
        return [
            "expression_mode='mixed' contains no readable proposition; "
            "combine compact evidence phrases with at least one source-grounded sentence"
        ]
    return []


_STRUCTURAL_METADATA_PATTERNS = (
    re.compile(r"^目\s*录$"),
    re.compile(r"^工作摘要$"),
    re.compile(r"^[（(]?(?:重构稿\s*)?V\d+(?:\.\d+)*[^。；]*[）)]?$", re.I),
    re.compile(r"^\d{4}年\d{1,2}月(?:\d{1,2}日)?$"),
    re.compile(r"^[一二三四五六七八九十]+、[^。；]{2,40}$"),
    re.compile(r"^附件[一二三四五六七八九十\d]+(?:[：:].*)?$"),
)


def _looks_like_structural_metadata(value: str) -> bool:
    text = re.sub(r"\s+", " ", str(value or "")).strip(" ；;。")
    return bool(text) and any(pattern.fullmatch(text) for pattern in _STRUCTURAL_METADATA_PATTERNS)


def _author_execution_issues(
    delivery_mode: str,
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Fail closed on deterministic assembly signatures that cannot count as AUTHOR."""

    if slide.get("page_type") != "content":
        return []

    issues: list[str] = []
    full_copy = str(slide.get("full_copy") or "").strip()
    metadata_hits: list[str] = []
    for ref in page.get("source_refs") or []:
        item = items.get(ref) if isinstance(ref, str) else None
        if not isinstance(item, dict):
            continue
        source_text = _item_text(item).strip()
        if _looks_like_structural_metadata(source_text) and source_text in full_copy:
            metadata_hits.append(ref)
    if metadata_hits:
        issues.append(
            "AUTHOR_STRUCTURAL_METADATA_LEAK: full_copy contains document front matter, "
            f"TOC entries, or section labels as argument prose: {metadata_hits}"
        )

    semicolon_segments = [part.strip() for part in re.split(r"[；;]", full_copy) if part.strip()]
    if len(semicolon_segments) >= 5 and sum(
        1 for part in semicolon_segments if len(_VISIBLE_CHAR_RE.findall(part)) <= 36
    ) >= 4:
        issues.append(
            "AUTHOR_MECHANICAL_SOURCE_CONCATENATION: full_copy is dominated by short "
            "semicolon-joined source fragments; rewrite it as a coherent argument"
        )

    contract = page.get("onscreen_contract")
    expression_mode = str(contract.get("expression_mode") or "") if isinstance(contract, dict) else ""
    if delivery_mode == "self_read" and expression_mode == "phrase_led":
        for module in slide.get("onscreen") or []:
            if not isinstance(module, dict):
                continue
            heading = str(module.get("heading") or "?").strip()
            for line in _onscreen_module_lines(module):
                if "|" in line:
                    issues.append(
                        f"AUTHOR_ONSCREEN_TABLE_FRAGMENT: module '{heading}' contains a raw table row: {line!r}"
                    )
                    continue
                if _is_readable_proposition(line):
                    continue
                if re.search(r"[：:]", line):
                    _, body = re.split(r"[：:]", line, maxsplit=1)
                    if _is_readable_proposition(body) or len(_VISIBLE_CHAR_RE.findall(body)) >= 12:
                        continue
                issues.append(
                    f"AUTHOR_ONSCREEN_INCOMPLETE_DETAIL: module '{heading}' has a visible "
                    f"detail without a complete business action, relation, or result: {line!r}"
                )
    return issues


__all__ = [
    "_STATUS_PRESERVATION_MARKERS",
    "_STRUCTURAL_METADATA_PATTERNS",
    "_status_strength_preserved",
    "_onscreen_module_lines",
    "_is_lead_like_evidence_item",
    "_evidence_first_item_hierarchy_issues",
    "_is_readable_proposition",
    "_onscreen_expression_warnings",
    "_looks_like_structural_metadata",
    "_author_execution_issues",
]

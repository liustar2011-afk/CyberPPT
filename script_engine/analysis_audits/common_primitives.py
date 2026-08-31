"""Low-level source/evidence primitives shared by staged analysis audits."""
from __future__ import annotations

import re
from typing import Any

from cyberppt.content_route import is_structural_page


CITABLE_KEYS = ("facts", "concepts", "entities", "relations", "arguments", "constraints", "numbers")

SOURCE_CHAPTER_RE = re.compile(r"^S(\d+)(?:\.|$)")

INTERNAL_MARKERS = (
    "内部测算", "内部参考", "内部审批", "内部口径", "仅供内部", "内部使用",
    "内部经营测算", "内部价格", "内部比例",
)

OPTIONALITY_RE = re.compile(r"(可|可以).{0,12}独立(采用|选择|使用).{0,18}(也|并且|同时).{0,18}(逐步|随着).{0,12}(深化|加深|升级)")

INDEPENDENCE_RE = re.compile(r"(独立采用|独立选择|可独立|分别选择|按需选择|任选|自行选择)")

DEEPENING_RE = re.compile(r"(逐步深化|逐步加深|逐级深化|逐步升级|随着.{0,10}(成熟|合作).{0,10}(深化|加深)|由浅入深)")

UNIVERSAL_RE = re.compile(r"(均|全部|所有|每个|各.{0,8}均|都已|均已)")

CRITICAL_GROUP_TERMS = ("长期积累", "已完成", "已具备", "已形成", "已实现", "已建立", "已纳入")

PROGRESSION_RE = re.compile(
    r"(依次递进|逐级递进|单向递进|沿.{0,12}(链条|路径).{0,8}递进|"
    r"起点.{0,30}(进一步|再|随后)|在.{0,20}基础上.{0,20}(进一步|再)|"
    r"进一步加工|从.{0,20}逐步.{0,20}到|由浅入深|投入最低|投入最深|升级到更深)"
)

GAP_RE = re.compile(r"(当前|目前|现有).{0,30}(距离|距).{0,15}目标.{0,20}(很大|较大|明显|较多).{0,8}缺口|距离目标还有.{0,12}缺口")

CHAPTER_PREFIX_RE = re.compile(r"^第[一二三四五六七八九十百\d]+章[\s　]*")

_VISIBLE_CHAR_RE = re.compile(r"[一-鿿A-Za-z0-9]")

_PROPOSITION_END_RE = re.compile(r"[。！？!?]\s*$")

_EXPRESSION_MODES = {"phrase_led", "sentence_led", "mixed"}

_ONSCREEN_COMPOSITION_MODES = {"evidence_first", "selective_lead"}

_EVIDENCE_FIT_VALUES = {"direct", "indirect", "topic_only", "no", "uncertain"}

_EVIDENCE_FIT_VERDICTS = {"keep", "rename", "move", "split", "reject"}

_LEAD_LIKE_EVIDENCE_ITEM_RE = re.compile(
    r"(?:需要|应当|应|须|用于|构成|提供|支撑|形成|明确|保持|覆盖|衔接|检验|"
    r"推动|进入|完成|面向|达到|对应|转化|可(?:以|用于))|"
    r"为.{0,18}(?:提供|形成|支撑|明确|转化)"
)

_COMPLETE_PROPOSITION_MIN_CHARS = 16

_COMPLETE_PROPOSITION_MAX_CHARS = 90

_SECONDARY_RELATION_TYPES = {"influence", "dependency", "feedback", "reference"}


def _normalized_review_text(value: object) -> str:
    return re.sub(r"[^一-鿿A-Za-z0-9]", "", str(value or "")).lower()


def foundation_items_by_id(foundation: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items: dict[str, dict[str, Any]] = {}
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                items[item["id"]] = item
    return items


def _item_text(item: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("statement", "claim", "definition", "context", "strength", "term", "relation", "value", "unit"):
        value = item.get(key)
        if isinstance(value, str):
            parts.append(value)
    parts.extend(
        str(unit.get("text") or "").strip()
        for unit in item.get("semantic_units") or []
        if isinstance(unit, dict) and str(unit.get("text") or "").strip()
    )
    return " ".join(parts)


def effective_visibility(item: dict[str, Any]) -> str:
    text = _item_text(item)
    if any(marker in text for marker in INTERNAL_MARKERS):
        return "internal_only"
    value = item.get("visibility")
    return value if isinstance(value, str) and value else "external_ok"


def _support_items(ids: list[Any], items: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [items[x] for x in ids if isinstance(x, str) and x in items]


def _has_optionality(items: list[dict[str, Any]]) -> bool:
    return any(OPTIONALITY_RE.search(_item_text(item)) for item in items)


def _preserves_optionality(text: str) -> bool:
    return bool(INDEPENDENCE_RE.search(text) and DEEPENING_RE.search(text))


def _group_strength_issue(claim: str, support: list[dict[str, Any]]) -> str | None:
    if not support or not UNIVERSAL_RE.search(claim):
        return None
    for term in CRITICAL_GROUP_TERMS:
        if term not in claim:
            continue
        missing = [item.get("id", "?") for item in support if term not in _item_text(item)]
        if missing:
            return f"universal group claim uses '{term}' but support items {missing} do not all carry that source strength"
    return None


def _page_evidence_ids(page: dict[str, Any]) -> set[str]:
    evidence_ids: set[str] = set()
    proof = page.get("proof") or {}
    if isinstance(proof, dict):
        evidence_ids.update(x for x in (proof.get("evidence_refs") or []) if isinstance(x, str))
        evidence_ids.update(x for x in (proof.get("boundary_refs") or []) if isinstance(x, str))
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        evidence_ids.update(x for x in (analysis_basis.get("supports") or []) if isinstance(x, str))
    onscreen_contract = page.get("onscreen_contract") or {}
    if isinstance(onscreen_contract, dict):
        for module in onscreen_contract.get("modules") or []:
            if isinstance(module, dict):
                evidence_ids.update(
                    x for x in (module.get("evidence_refs") or []) if isinstance(x, str)
                )
    return evidence_ids


def _page_claim_evidence_ids(page: dict[str, Any]) -> set[str]:
    """Return evidence that supports the page judgment outside visible modules."""
    evidence_ids: set[str] = set()
    proof = page.get("proof") or {}
    if isinstance(proof, dict):
        evidence_ids.update(x for x in (proof.get("evidence_refs") or []) if isinstance(x, str))
        evidence_ids.update(x for x in (proof.get("boundary_refs") or []) if isinstance(x, str))
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        evidence_ids.update(x for x in (analysis_basis.get("supports") or []) if isinstance(x, str))
    return evidence_ids


def requires_source_consumption(
    page: dict[str, Any], foundation: dict[str, Any]
) -> bool:
    """Return whether the compiler-owned strict contract applies to a page."""
    return (
        foundation.get("source_consumption_policy") == "required"
        and bool([ref for ref in page.get("source_refs") or [] if isinstance(ref, str) and ref])
        and not is_structural_page(page)
    )


def _source_surface_values(item: dict[str, Any]) -> list[str]:
    values = [str(item.get("statement") or "").strip()]
    values.extend(
        str(unit.get("text") or "").strip()
        for unit in item.get("semantic_units") or []
        if isinstance(unit, dict)
    )
    values.extend(
        str(value).strip()
        for value in item.get("coverage_anchors") or []
        if isinstance(value, str)
    )
    return [value for value in values if value]


def _page_text(page: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "question", "message", "logic", "next", "receives"):
        value = page.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("content", "must_include", "reserved_for_later"):
        for value in page.get(key) or []:
            if isinstance(value, str):
                parts.append(value)
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        for key in ("model", "relation_basis", "confidence"):
            value = analysis_basis.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)


__all__ = [
    "CITABLE_KEYS",
    "SOURCE_CHAPTER_RE",
    "INTERNAL_MARKERS",
    "OPTIONALITY_RE",
    "INDEPENDENCE_RE",
    "DEEPENING_RE",
    "UNIVERSAL_RE",
    "CRITICAL_GROUP_TERMS",
    "PROGRESSION_RE",
    "GAP_RE",
    "CHAPTER_PREFIX_RE",
    "_VISIBLE_CHAR_RE",
    "_PROPOSITION_END_RE",
    "_EXPRESSION_MODES",
    "_ONSCREEN_COMPOSITION_MODES",
    "_EVIDENCE_FIT_VALUES",
    "_EVIDENCE_FIT_VERDICTS",
    "_LEAD_LIKE_EVIDENCE_ITEM_RE",
    "_COMPLETE_PROPOSITION_MIN_CHARS",
    "_COMPLETE_PROPOSITION_MAX_CHARS",
    "_SECONDARY_RELATION_TYPES",
    "_normalized_review_text",
    "foundation_items_by_id",
    "_item_text",
    "effective_visibility",
    "_support_items",
    "_has_optionality",
    "_preserves_optionality",
    "_group_strength_issue",
    "_page_evidence_ids",
    "_page_claim_evidence_ids",
    "requires_source_consumption",
    "_source_surface_values",
    "_page_text",
]

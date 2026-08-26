"""Deterministic audit helpers for source fidelity and analytical inference."""
from __future__ import annotations

import re
from typing import Any

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


def _scope_chapters(source_scope: list[Any]) -> set[int]:
    chapters: set[int] = set()
    for ref in source_scope:
        if isinstance(ref, str):
            match = SOURCE_CHAPTER_RE.match(ref)
            if match:
                chapters.add(int(match.group(1)))
    return chapters


def _page_evidence_ids(page: dict[str, Any]) -> set[str]:
    evidence_ids: set[str] = set()
    proof = page.get("proof") or {}
    if isinstance(proof, dict):
        evidence_ids.update(x for x in (proof.get("evidence_refs") or []) if isinstance(x, str))
        evidence_ids.update(x for x in (proof.get("boundary_refs") or []) if isinstance(x, str))
    analysis_basis = page.get("analysis_basis") or {}
    if isinstance(analysis_basis, dict):
        evidence_ids.update(x for x in (analysis_basis.get("supports") or []) if isinstance(x, str))
    return evidence_ids


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


def _slide_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "subtitle", "mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(key)
        if isinstance(value, str):
            parts.append(value)
    argument = slide.get("argument") or {}
    if isinstance(argument, dict):
        if isinstance(argument.get("pattern"), str):
            parts.append(argument["pattern"])
        parts.extend(x for x in (argument.get("chain") or []) if isinstance(x, str))
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str):
                parts.append(value)
        parts.extend(x for x in (module.get("items") or []) if isinstance(x, str))
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "to", "relation"):
            value = relation.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)


def _source_text_for_refs(source_refs: list[Any], foundation: dict[str, Any]) -> str:
    refs = {x for x in source_refs if isinstance(x, str)}
    parts: list[str] = []
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            if refs.intersection(x for x in (item.get("source_refs") or []) if isinstance(x, str)):
                parts.append(_item_text(item))
    return " ".join(parts)


def _normalize_source_chapter_title(title: str) -> str:
    return CHAPTER_PREFIX_RE.sub("", title).strip(" 　")


def audit_foundation_analysis(foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    known_ids = set(items)

    for key in CITABLE_KEYS:
        for index, item in enumerate(foundation.get(key) or []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id") or f"#{index}"
            text = _item_text(item)
            declared = item.get("visibility")
            if any(marker in text for marker in INTERNAL_MARKERS) and declared == "external_ok":
                issues.append(f"{key}.{index} ({item_id}): source text is explicitly internal ('内部…') but visibility is external_ok")

    for index, relation in enumerate(foundation.get("relations") or []):
        if not isinstance(relation, dict):
            continue
        rel_id = relation.get("id") or f"#{index}"
        support_ids = [x for x in (relation.get("support") or []) if isinstance(x, str)]
        support = _support_items(support_ids, items)
        if relation.get("basis") == "inferred":
            if not support_ids:
                issues.append(f"relations.{index} ({rel_id}): inferred relation requires non-empty support fact IDs")
            unknown = [x for x in support_ids if x not in known_ids]
            if unknown:
                issues.append(f"relations.{index} ({rel_id}): inferred relation cites unknown support IDs {unknown}")
            if not relation.get("confidence"):
                warnings.append(f"relations.{index} ({rel_id}): inferred relation has no confidence level")
        if _has_optionality(support):
            relation_text = _item_text(relation)
            if DEEPENING_RE.search(relation_text) and not INDEPENDENCE_RE.search(relation_text):
                issues.append(f"relations.{index} ({rel_id}): support preserves independent choice + progressive deepening, but relation keeps only the progression")

    for index, argument in enumerate(foundation.get("arguments") or []):
        if not isinstance(argument, dict):
            continue
        arg_id = argument.get("id") or f"#{index}"
        support = _support_items(argument.get("support") or [], items)
        claim = str(argument.get("claim") or "")
        group_issue = _group_strength_issue(claim, support)
        if group_issue:
            issues.append(f"arguments.{index} ({arg_id}): {group_issue}")

    structure = [x for x in (foundation.get("source_structure") or []) if isinstance(x, dict)]
    ids = [x.get("id") for x in structure if x.get("id")]
    if len(ids) != len(set(ids)):
        issues.append("source_structure: duplicate structure IDs")
    orders = [x.get("order") for x in structure if isinstance(x.get("order"), int)]
    if len(orders) != len(set(orders)):
        warnings.append("source_structure: duplicate order values; verify source hierarchy ordering")
    return issues, warnings


def audit_deck_plan(plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    structure = [x for x in (foundation.get("source_structure") or []) if isinstance(x, dict)]
    source_chapters = [
        x.get("id")
        for x in sorted(
            (x for x in structure if x.get("level") == "chapter" and x.get("id")),
            key=lambda x: x.get("order", 0),
        )
    ]
    mode = plan.get("source_structure_mode")
    if source_chapters and not mode:
        warnings.append("source_structure_mode: missing; source-driven plans should declare 'preserve' unless user authorized restructuring")
    if mode == "preserve":
        planned: list[str] = []
        missing = False
        for index, chapter in enumerate(plan.get("chapters") or []):
            if not isinstance(chapter, dict):
                continue
            ids = [x for x in (chapter.get("source_chapter_ids") or []) if isinstance(x, str)]
            if not ids:
                missing = True
            planned.extend(ids)
            if chapter.get("structural_operation") == "user_authorized_cross_chapter":
                issues.append(f"chapters.{index}: cross-chapter operation conflicts with source_structure_mode='preserve'")
        if missing:
            warnings.append("chapters: one or more chapters lack source_chapter_ids, so chapter-order fidelity cannot be audited mechanically")
        elif planned != source_chapters:
            issues.append(f"chapters: source chapter order/content differs from source_structure; expected {source_chapters}, got {planned}")

    audience_scope = plan.get("audience_scope", "unspecified")
    for index, page in enumerate(plan.get("pages") or []):
        if not isinstance(page, dict):
            continue
        page_id = page.get("id") or f"#{index}"
        scope = page.get("source_scope") or []
        chapters = _scope_chapters(scope)
        operation = page.get("structural_operation")
        if len(chapters) > 1 and operation != "user_authorized_cross_chapter":
            issues.append(f"pages.{index} ({page_id}): source_scope crosses chapters {sorted(chapters)} without user_authorized_cross_chapter")

        analysis_basis = page.get("analysis_basis") or {}
        if isinstance(analysis_basis, dict) and analysis_basis.get("relation_basis") == "inferred":
            supports = [x for x in (analysis_basis.get("supports") or []) if isinstance(x, str)]
            if not supports:
                issues.append(f"pages.{index} ({page_id}).analysis_basis: inferred relation requires support IDs")
            unknown = [x for x in supports if x not in items]
            if unknown:
                issues.append(f"pages.{index} ({page_id}).analysis_basis: unknown support IDs {unknown}")

        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)
        internal = [item.get("id", "?") for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            decision = page.get("visibility_decision")
            if decision not in ("internal_only_used_as_hidden_support", "user_approved_exposure"):
                issues.append(f"pages.{index} ({page_id}): external audience uses internal-only evidence {sorted(internal)} without an explicit visibility_decision")

        page_text = _page_text(page)
        if _has_optionality(evidence) and not _preserves_optionality(page_text):
            issues.append(f"pages.{index} ({page_id}): source evidence says modes may be independently selected and progressively deepened; plan must preserve both meanings")

        group_issue = _group_strength_issue(str(page.get("message") or ""), evidence)
        if group_issue:
            issues.append(f"pages.{index} ({page_id}): {group_issue}")

    return issues, warnings


def audit_final_script(final_script: dict[str, Any], plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    pages = {p.get("id"): p for p in (plan.get("pages") or []) if isinstance(p, dict) and isinstance(p.get("id"), str)}
    chapters = {c.get("id"): c for c in (plan.get("chapters") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)}
    structure = {x.get("id"): x for x in (foundation.get("source_structure") or []) if isinstance(x, dict) and isinstance(x.get("id"), str)}
    audience_scope = plan.get("audience_scope", "unspecified")
    preserve_structure = plan.get("source_structure_mode") == "preserve"

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        page = pages.get(slide_id)
        if page is None:
            warnings.append(f"slides.{index} ({slide_id}): no matching deck-plan page; semantic inheritance cannot be audited")
            continue
        final_text = _slide_text(slide)
        plan_text = _page_text(page)
        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)

        plan_model = str((page.get("analysis_basis") or {}).get("model") or "").lower()
        plan_logic = str(page.get("logic") or "")
        plan_is_classification = any(token in plan_model for token in ("classification", "taxonomy", "typology")) or "分类" in plan_logic
        plan_allows_progression = bool(PROGRESSION_RE.search(plan_text) or any(token in plan_model for token in ("progression", "maturity")))
        if plan_is_classification and not plan_allows_progression and PROGRESSION_RE.search(final_text):
            issues.append(f"slides.{index} ({slide_id}): AUTHOR upgraded a classification/taxonomy plan into a progression chain")

        if _has_optionality(evidence) and not _preserves_optionality(final_text):
            issues.append(f"slides.{index} ({slide_id}): final script lost source optionality; it must preserve independent choice and progressive deepening")

        group_issue = _group_strength_issue(str(slide.get("core_message") or ""), evidence)
        if group_issue:
            issues.append(f"slides.{index} ({slide_id}): {group_issue}")

        internal = [item for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            exposed: list[str] = []
            for item in internal:
                item_text = _item_text(item)
                values = [str(item.get("value") or "")]
                for match in re.findall(r"\d+(?:\.\d+)?%?(?:至|-|—)\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%", item_text):
                    values.append(match)
                normalized_final = final_text.replace("至", "-").replace("—", "-")
                if any(value and value.replace("至", "-").replace("—", "-") in normalized_final for value in values):
                    exposed.append(str(item.get("id") or "?"))
            if exposed:
                issues.append(f"slides.{index} ({slide_id}): external final script exposes internal-only evidence {sorted(set(exposed))}")

        if GAP_RE.search(final_text):
            source_text = _source_text_for_refs(page.get("source_refs") or [], foundation)
            if not GAP_RE.search(plan_text) and not GAP_RE.search(source_text):
                issues.append(f"slides.{index} ({slide_id}): final script introduces a current-vs-target gap judgment without a source or plan baseline")

        if preserve_structure and slide.get("page_type") == "chapter":
            chapter_id = slide.get("chapter_id")
            chapter = chapters.get(chapter_id) if isinstance(chapter_id, str) else None
            source_ids = chapter.get("source_chapter_ids") if isinstance(chapter, dict) else None
            if source_ids and len(source_ids) == 1:
                node = structure.get(source_ids[0])
                if isinstance(node, dict) and isinstance(node.get("title"), str):
                    expected = _normalize_source_chapter_title(node["title"])
                    actual = str(slide.get("title") or "").strip()
                    if actual and expected and actual != expected:
                        issues.append(f"slides.{index} ({slide_id}): source_structure_mode='preserve' requires chapter title '{expected}', got '{actual}'")

    return issues, warnings


def validate_source_index_coverage(final_script: dict[str, Any], source_index: dict[str, Any]) -> list[str]:
    refs = source_index.get("refs") or {}
    issues: list[str] = []
    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        for ref in slide.get("source_refs") or []:
            if isinstance(ref, str) and ref and ref not in refs:
                issues.append(f"slides.{index} ({slide_id}).source_refs: '{ref}' is not mapped in source-index.json")
    return issues

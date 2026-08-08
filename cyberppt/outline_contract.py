"""Solution-first outline contracts and deterministic Stage 01 audits."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from cyberppt.argument_flow_contract import audit_argument_flow
from cyberppt.source_argument_model import audit_outline_consumption
from cyberppt.semantic_fidelity import (
    STRONG_RELATIONS,
    audit_relation_shape,
    audit_semantic_strength,
    source_text,
    strong_relation_supported,
)


SOLUTION_MATERIAL_TERMS = (
    "方案",
    "前期研究",
    "立项",
    "可研",
    "政府",
    "央企",
    "国企",
    "协会",
)
METHOD_TERMS = ("原则", "方法", "筛选", "评价维度", "选择标准")
HIGH_RISK_SEMANTIC_TERMS = (
    "才能", "必须", "只有", "决定", "确保", "必然", "缺一不可",
    "不可替代", "核心驱动", "决定性",
)
QUESTION_TERMS = ("什么", "哪些", "如何", "为何", "为什么", "是否", "谁", "何时", "怎样", "多少", "哪")
RELATION_PROMOTION_TERMS = ("协同", "驱动", "导致", "依赖", "实现")
REQUIRED_FIELDS = (
    "schema",
    "material_type",
    "audience",
    "architecture_mode",
    "architecture_reason",
    "source_section_weights",
    "pages",
    "retry",
)


@dataclass(frozen=True)
class AuditIssue:
    code: str
    message: str
    pages: tuple[str, ...] = ()
    retry_strategy: str = "rebuild_outline"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def load_outline(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid outline JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError("outline root must be an object")
    for field in REQUIRED_FIELDS:
        if field not in payload:
            raise ValueError(f"missing required field: {field}")
    if payload.get("schema") not in {"cyberppt.outline.v1", "cyberppt.outline.v2"}:
        raise ValueError("schema must be cyberppt.outline.v1 or cyberppt.outline.v2")
    if not isinstance(payload.get("pages"), list):
        raise ValueError("pages must be an array")
    return payload


def _explicit_consulting_request(outline: dict[str, object]) -> bool:
    return outline.get("user_requested_architecture") is True


def _is_solution_material(material_type: object) -> bool:
    text = str(material_type or "").lower()
    return any(term.lower() in text for term in SOLUTION_MATERIAL_TERMS)


def resolve_architecture_mode(outline: dict[str, object]) -> str:
    requested = str(outline.get("architecture_mode") or "solution")
    if requested not in {"solution", "consulting"}:
        raise ValueError("architecture_mode must be solution or consulting")
    if requested == "consulting" and _is_solution_material(outline.get("material_type")):
        return "consulting" if _explicit_consulting_request(outline) else "solution"
    return requested


def _text(value: object) -> str:
    return re.sub(r"[\s，。；：、,.!?！？—_-]+", "", str(value or "")).casefold()


def _page_id(page: dict[str, object]) -> str:
    return str(page.get("page_id") or f"sequence-{page.get('sequence', '?')}")


def _core_message(page: dict[str, object]) -> str:
    """Read the v2 semantic center while retaining v1 compatibility."""

    return str(page.get("core_message") or page.get("main_message") or "").strip()


def _page_mission(page: dict[str, object]) -> str:
    return str(
        page.get("page_mission")
        or page.get("page_job")
        or page.get("business_question")
        or ""
    ).strip()


def _onscreen_conclusion(page: dict[str, object]) -> str:
    return str(
        page.get("onscreen_conclusion") or page.get("onscreen_judgment") or ""
    ).strip()


def _template_issues(pages: list[dict[str, object]]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    sequences = [page.get("sequence") for page in pages]
    if sequences and sequences != list(range(1, len(pages) + 1)):
        issues.append(
            AuditIssue(
                "TEMPLATE_PAGES_DETACHED",
                "All template and content pages must share one continuous ordered sequence.",
                tuple(_page_id(page) for page in pages),
                "continuous_page_sequence",
            )
        )
    chapter_seen: set[str] = set()
    for page in pages:
        page_type = page.get("page_type")
        chapter_id = str(page.get("chapter_id") or "")
        if page_type == "chapter":
            chapter_seen.add(chapter_id)
            content_fields = (
                page.get("main_message"),
                page.get("business_question"),
                page.get("visual_center"),
                page.get("modules"),
            )
            if any(content_fields):
                issues.append(
                    AuditIssue(
                        "CHAPTER_PAGE_HAS_CONTENT",
                        "Chapter pages may contain only the chapter number and title.",
                        (_page_id(page),),
                        "chapter_page_purity",
                    )
                )
        elif page_type == "content" and chapter_id and chapter_id not in chapter_seen:
            issues.append(
                AuditIssue(
                    "TEMPLATE_PAGES_DETACHED",
                    "Chapter content must follow its chapter page in the same sequence.",
                    (_page_id(page),),
                    "continuous_page_sequence",
                )
            )
    return issues


def _content_issues(pages: list[dict[str, object]]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    content_pages = [page for page in pages if page.get("page_type") == "content"]
    for page in content_pages:
        core = _core_message(page)
        if not _page_mission(page):
            issues.append(AuditIssue("PAGE_MISSION_MISSING", "Every content page must declare its internal editorial mission.", (_page_id(page),), "complete_page_semantic_contract"))
        if not core:
            issues.append(AuditIssue("CORE_MESSAGE_MISSING", "Every content page must state the smallest complete meaning supported by its sources; it may be factual, compositional, relational, procedural, bounded, or judgmental.", (_page_id(page),), "derive_core_message_from_source"))
        if _text(page.get("title")) and _text(page.get("title")) == _text(core):
            issues.append(
                AuditIssue(
                    "TITLE_CLAIM_COLLAPSED",
                    "Use a concise topic title and store the page's complete source-supported meaning in core_message.",
                    (_page_id(page),),
                    "separate_title_and_main_message",
                )
            )
        compact_core = re.sub(r"\s+", "", core)
        if core and (
            re.fullmatch(r"(?:\d+[.、．]|[（(]?[一二三四五六七八九十]+[）)])?[^。；：]{1,18}[。.]?", compact_core)
            or ("|" in core and not re.search(r"[。；：]", core))
        ):
            issues.append(
                AuditIssue(
                    "CORE_MESSAGE_NOT_COMPLETE",
                    "A heading, table label, or short topic phrase is not a complete page meaning; derive the smallest complete source-supported statement.",
                    (_page_id(page),),
                    "derive_complete_core_message",
                )
            )
        modules = page.get("modules") if isinstance(page.get("modules"), list) else []
        method_role = any(isinstance(item, dict) and item.get("role") == "method" for item in modules)
        method_title = any(term in str(page.get("title") or "") for term in METHOD_TERMS)
        if not page.get("source_refs") and len(modules) <= 1 and (method_role or method_title):
            issues.append(
                AuditIssue(
                    "METHOD_PAGE_OVERPROMOTED",
                    "Method-only guidance without independent evidence should be a module, not a core page.",
                    (_page_id(page),),
                    "merge_method_into_business_page",
                )
            )

    for index in range(max(0, len(content_pages) - 2)):
        run = content_pages[index : index + 3]
        questions = {
            _text(page.get("audience_question") or page.get("business_question"))
            for page in run
        }
        visuals = {_text(page.get("visual_center")) for page in run}
        if "" not in questions and len(questions) == 1 and "" not in visuals and len(visuals) == 1:
            issues.append(
                AuditIssue(
                    "ATOMIC_SECTION_SPLIT",
                    "Adjacent pages repeat one business question and visual center; aggregate them into a complete analysis page.",
                    tuple(_page_id(page) for page in run),
                    "aggregate_by_business_question",
                )
            )
            break

    # Page necessity must be an editorial decision about this evidence node, not
    # a boilerplate receipt copied onto every page.  Evidence coverage alone is
    # never sufficient reason to create a standalone slide.
    necessity_groups: dict[str, list[str]] = {}
    for page in content_pages:
        necessity = _text(page.get("page_necessity"))
        if necessity:
            necessity_groups.setdefault(necessity, []).append(_page_id(page))
    for grouped_pages in necessity_groups.values():
        if len(grouped_pages) >= 3:
            issues.append(
                AuditIssue(
                    "PAGE_NECESSITY_BOILERPLATE",
                    "The same page-necessity rationale is reused across multiple pages. Explain the irreducible narrative contribution of each page, or merge supporting detail into its parent page/appendix.",
                    tuple(grouped_pages),
                    "reassess_standalone_page_necessity",
                )
            )
            break

    def ngrams(value: object, size: int = 3) -> set[str]:
        compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", str(value or "")).casefold()
        return {compact[index:index + size] for index in range(max(0, len(compact) - size + 1))}

    for index, left in enumerate(content_pages):
        left_grams = ngrams(_core_message(left))
        if not left_grams:
            continue
        for right in content_pages[index + 1:]:
            right_grams = ngrams(_core_message(right))
            if not right_grams:
                continue
            similarity = len(left_grams & right_grams) / min(len(left_grams), len(right_grams))
            if similarity < 0.72:
                continue
            issues.append(
                AuditIssue(
                    "CORE_MESSAGE_REDUNDANT",
                    "Two pages express substantially the same source meaning even though their evidence records differ; merge them or make their narrative contributions materially distinct.",
                    (_page_id(left), _page_id(right)),
                    "merge_redundant_expression_nodes",
                )
            )
            break
    return issues


def _editorial_control_issues(
    outline: dict[str, object], pages: list[dict[str, object]]
) -> list[AuditIssue]:
    """Audit audience-facing page separation without replacing source semantics."""

    if outline.get("editorial_control_mode") != "required":
        return []
    issues: list[AuditIssue] = []
    question_pages: dict[str, list[str]] = {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = _page_id(page)
        question = str(page.get("audience_question") or "").strip()
        exclusions = page.get("must_not_include")
        split_risk = str(page.get("split_risk") or "").strip()
        split_reason = str(page.get("split_risk_reason") or "").strip()

        if not question:
            issues.append(AuditIssue(
                "AUDIENCE_QUESTION_MISSING",
                "Each content page must state the concrete audience question it answers.",
                (page_id,),
                "define_audience_question",
            ))
        else:
            normalized = _text(question)
            question_pages.setdefault(normalized, []).append(page_id)
            if (
                normalized == _text(_page_mission(page))
                or re.search(r"本页(?:说明|介绍|讲述|回答)", question)
                or not any(term in question for term in QUESTION_TERMS)
            ):
                issues.append(AuditIssue(
                    "AUDIENCE_QUESTION_NOT_CONCRETE",
                    "audience_question must be a real audience question, not a restatement of page_mission or a page-description placeholder.",
                    (page_id,),
                    "rewrite_audience_question",
                ))

        if (
            not isinstance(exclusions, list)
            or not exclusions
            or any(not str(item).strip() for item in exclusions)
        ):
            issues.append(AuditIssue(
                "MUST_NOT_INCLUDE_MISSING",
                "Each content page must name at least one adjacent topic, claim, or detail that must remain outside the page.",
                (page_id,),
                "separate_adjacent_page_scope",
            ))

        if split_risk not in {"low", "medium", "high"}:
            issues.append(AuditIssue(
                "SPLIT_RISK_INVALID",
                "split_risk must be low, medium, or high.",
                (page_id,),
                "assess_page_split_risk",
            ))
        elif split_risk in {"medium", "high"} and not split_reason:
            issues.append(AuditIssue(
                "SPLIT_RISK_REASON_MISSING",
                "Medium or high split risk requires a concrete explanation of the competing question, relation, or visual center.",
                (page_id,),
                "explain_page_split_risk",
            ))
        if split_risk == "high":
            issues.append(AuditIssue(
                "HIGH_SPLIT_RISK_UNRESOLVED",
                "A high-risk page must be split or restructured before the outline can pass.",
                (page_id,),
                "split_overloaded_page",
            ))

    for page_ids in question_pages.values():
        if len(page_ids) >= 3:
            issues.append(AuditIssue(
                "AUDIENCE_QUESTION_REUSED",
                "The same audience question is reused across three or more pages; aggregate them or make each page answer a materially different question.",
                tuple(page_ids),
                "differentiate_audience_questions",
            ))
    return issues


def _semantic_derivation_issues(
    outline: dict[str, object],
    pages: list[dict[str, object]],
    source_truth: dict[str, object] | None,
) -> list[AuditIssue]:
    """Audit the required semantic center and optional visible compression."""

    issues: list[AuditIssue] = []
    records = {
        str(record.get("id") or ""): record
        for record in (source_truth or {}).get("records", [])
        if isinstance(record, dict) and record.get("id")
    }
    require_receipt = (
        outline.get("core_message_derivation_mode") == "required"
        or outline.get("schema") == "cyberppt.outline.v2"
    )
    for page in pages:
        if page.get("page_type") != "content":
            continue
        page_id = _page_id(page)
        main = _core_message(page)
        onscreen = _onscreen_conclusion(page)
        if onscreen and not main:
            issues.append(
                AuditIssue(
                    "ONSCREEN_CONCLUSION_WITHOUT_JUDGMENT",
                    "An on-screen conclusion requires an existing source-derived core message.",
                    (page_id,),
                    "remove_or_derive_judgment",
                )
            )
        if not main:
            continue
        derivation = page.get("core_message_derivation") or page.get("judgment_derivation")
        if require_receipt and not isinstance(derivation, dict):
            issues.append(
                AuditIssue(
                    "CORE_MESSAGE_DERIVATION_MISSING",
                    "Every content page core_message requires a source derivation receipt.",
                    (page_id,),
                    "document_judgment_derivation",
                )
            )
            derivation = {}
        source_refs = [str(ref) for ref in page.get("source_refs", [])]
        receipt_refs = (
            [str(ref) for ref in derivation.get("source_refs", [])]
            if isinstance(derivation, dict)
            else []
        )
        if isinstance(derivation, dict) and require_receipt:
            if not receipt_refs or not set(receipt_refs).issubset(source_refs):
                issues.append(
                    AuditIssue(
                        "JUDGMENT_DERIVATION_INVALID",
                        "Core-message derivation source_refs must be a non-empty subset of page source_refs.",
                        (page_id,),
                        "document_judgment_derivation",
                    )
                )
            if not derivation.get("supporting_statements") or not derivation.get("derivation"):
                issues.append(
                    AuditIssue(
                        "JUDGMENT_DERIVATION_INVALID",
                        "Core-message derivation must state the supporting source text and equal-strength derivation.",
                        (page_id,),
                        "document_judgment_derivation",
                    )
                )
            if derivation.get("introduced_relations") or derivation.get("introduced_modalities"):
                issues.append(
                    AuditIssue(
                        "JUDGMENT_DERIVATION_INTRODUCES_MEANING",
                        "A core message may not introduce relations or modalities absent from the cited material.",
                        (page_id,),
                        "remove_semantic_promotion",
                    )
                )
        evidence_text = source_text(receipt_refs or source_refs, records)
        output_text = "\n".join(part for part in (main, onscreen) if part)
        for fidelity_issue in audit_semantic_strength(output_text, evidence_text):
            issues.append(AuditIssue(fidelity_issue.code, fidelity_issue.message, (page_id,), "remove_semantic_promotion"))
        relations = page.get("content_relations")
        if outline.get("schema") == "cyberppt.outline.v2":
            for relation_issue in audit_relation_shape(relations):
                issues.append(AuditIssue(relation_issue.code, relation_issue.message, (page_id,), "complete_content_relations"))
        if isinstance(relations, list):
            for relation in relations:
                if not isinstance(relation, dict):
                    continue
                relation_name = str(relation.get("relation") or "")
                relation_refs = [str(ref) for ref in relation.get("source_refs", [])]
                relation_evidence = source_text(relation_refs, records)
                if relation_name in STRONG_RELATIONS and not strong_relation_supported(relation_name, relation_evidence):
                    issues.append(AuditIssue("RELATION_STRENGTH_UPGRADED", f"Strong relation {relation_name} is not explicitly supported by its cited sources.", (page_id,), "remove_semantic_promotion"))
    return issues


def _weight_issues(outline: dict[str, object], pages: list[dict[str, object]]) -> list[AuditIssue]:
    targets = outline.get("source_section_weights")
    if not isinstance(targets, dict) or not targets:
        return []
    actual: dict[str, float] = {}
    for page in pages:
        if page.get("page_type") != "content":
            continue
        chapter = str(page.get("chapter_id") or "")
        actual[chapter] = actual.get(chapter, 0.0) + float(page.get("source_weight") or 0.0)
    distorted = [chapter for chapter, target in targets.items() if float(target) - actual.get(str(chapter), 0.0) > 0.20]
    if not distorted:
        return []
    return [
        AuditIssue(
            "SOURCE_WEIGHT_DISTORTED",
            "Core source sections are underrepresented in the planned content pages.",
            tuple(str(item) for item in distorted),
            "rebalance_to_source_weight",
        )
    ]


def _page_source_volume(page: dict[str, object], records: dict[str, dict[str, object]]) -> int:
    """Approximate how much source material a page actually has to draw on.

    Sums the character length of every referenced Source Truth statement
    (main + detail refs). This is a proxy for how much a page *can* say, not
    a proxy for how good the page currently is — a page can under-use
    available material, but it cannot invent material it doesn't have.
    """

    ref_ids: set[str] = set()
    for field in ("source_refs", "detail_refs", "boundary_refs"):
        value = page.get(field)
        if isinstance(value, list):
            ref_ids.update(str(item) for item in value)
    return sum(len(str(records[ref_id].get("statement") or "")) for ref_id in ref_ids if ref_id in records)


def _content_page_density_issues(
    pages: list[dict[str, object]], source_truth: dict[str, object] | None
) -> list[AuditIssue]:
    """Flag runs of consecutive content pages whose source material is thin.

    A single terse page next to normal-density pages is often a deliberate
    beat (a stark decision or transition page) and is left alone. A *run* of
    2+ consecutive same-chapter pages that are all well below the deck's
    typical page volume usually means the source material for that stretch
    was thinner than the page-per-subsection default assumed, and the pages
    should be merged rather than force-padded — merging is the source-
    faithful fix; inventing content to fill a thin page is not.
    """

    if not isinstance(source_truth, dict):
        return []
    raw_records = source_truth.get("records")
    if not isinstance(raw_records, list):
        return []
    records = {
        str(record.get("id")): record
        for record in raw_records
        if isinstance(record, dict) and record.get("id")
    }
    content_pages = sorted(
        (page for page in pages if page.get("page_type") == "content"),
        key=lambda page: page.get("sequence", 0),
    )
    if len(content_pages) < 4:
        # Too few content pages for a stable median; not worth the noise.
        return []
    volumes = [
        (page, _page_source_volume(page, records)) for page in content_pages
    ]
    nonzero = sorted(volume for _, volume in volumes if volume > 0)
    if len(nonzero) < 4:
        return []
    median = nonzero[len(nonzero) // 2]
    threshold = median * 0.45
    if threshold <= 0:
        return []

    issues: list[AuditIssue] = []
    run: list[tuple[dict[str, object], int]] = []

    def _flush() -> None:
        if len(run) < 2:
            run.clear()
            return
        page_ids = tuple(_page_id(page) for page, _ in run)
        volumes_str = "、".join(f"{_page_id(page)}={volume}字" for page, volume in run)
        issues.append(
            AuditIssue(
                "CONTENT_PAGE_DENSITY_LOW",
                (
                    f"{len(run)} consecutive content pages in the same chapter each carry far less "
                    f"source material than the deck's typical page (median {median} chars, threshold "
                    f"{int(threshold)} chars): {volumes_str}. Merge them into fewer, denser pages "
                    "instead of writing a thin standalone page for each source subsection."
                ),
                page_ids,
                "merge_thin_adjacent_pages",
            )
        )
        run.clear()

    prev_chapter = None
    for page, volume in volumes:
        chapter = page.get("chapter_id")
        if chapter != prev_chapter:
            _flush()
        if volume > 0 and volume < threshold:
            run.append((page, volume))
        else:
            _flush()
        prev_chapter = chapter
    _flush()
    return issues


def _document_semantic_issues(
    outline: dict[str, object], source_truth: dict[str, object] | None
) -> list[AuditIssue]:
    """Keep the deck thesis anchored to the source's document identity."""

    if not source_truth or source_truth.get("document_semantics_mode") != "required":
        return []
    expected = source_truth.get("document_semantics")
    actual = outline.get("document_semantics")
    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return [
            AuditIssue(
                "OUTLINE_DOCUMENT_SEMANTICS_MISSING",
                "The outline must inherit the Source Truth document role, report subject, primary thesis, and decision boundary.",
                retry_strategy="anchor_outline_to_document_semantics",
            )
        ]
    fields = ("document_role", "subject_of_report", "primary_thesis", "decision_boundary")
    fields += tuple(
        field
        for field in ("author_purpose", "argument_method", "supporting_basis")
        if field in expected
    )
    if any(str(actual.get(field) or "").strip() != str(expected.get(field) or "").strip() for field in fields):
        return [
            AuditIssue(
                "OUTLINE_DOCUMENT_SEMANTICS_DRIFTED",
                "The outline changes the document role, report subject, primary thesis, or decision boundary established by Source Truth.",
                retry_strategy="anchor_outline_to_document_semantics",
            )
        ]
    if str(outline.get("narrative_thesis") or "").strip() != str(expected.get("primary_thesis") or "").strip():
        return [
            AuditIssue(
                "NARRATIVE_THESIS_DRIFTED",
                "The deck-level narrative thesis must equal the source-grounded primary thesis; document stage or research activity may not replace the subject of report.",
                retry_strategy="anchor_outline_to_document_semantics",
            )
        ]
    return []


def audit_outline(
    outline: dict[str, object],
    source_truth: dict[str, object] | None = None,
    semantic_argument_model: dict[str, object] | None = None,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    if (
        outline.get("architecture_mode") == "consulting"
        and resolve_architecture_mode(outline) == "solution"
    ):
        issues.append(
            AuditIssue(
                "SOLUTION_ARCHITECTURE_REQUIRED",
                "Formal solution material defaults to solution architecture unless the user explicitly requests consulting structure.",
                retry_strategy="switch_to_solution_architecture",
            )
        )
    raw_pages = outline.get("pages")
    pages = [page for page in raw_pages if isinstance(page, dict)] if isinstance(raw_pages, list) else []
    issues.extend(_template_issues(pages))
    issues.extend(_content_issues(pages))
    issues.extend(_editorial_control_issues(outline, pages))
    issues.extend(_weight_issues(outline, pages))
    issues.extend(_content_page_density_issues(pages, source_truth))
    issues.extend(_document_semantic_issues(outline, source_truth))
    issues.extend(_semantic_derivation_issues(outline, pages, source_truth))
    if outline.get("semantic_argument_model_mode") == "required" or semantic_argument_model is not None:
        issues.extend(
            AuditIssue(
                item["code"],
                item["message"],
                (item["node_id"],) if item.get("node_id") else (),
                "rebuild_from_semantic_argument_model",
            )
            for item in audit_outline_consumption(outline, semantic_argument_model)
        )
    if outline.get("argument_contract_mode", "legacy") == "strict":
        if source_truth is None:
            issues.append(
                AuditIssue(
                    "SOURCE_TRUTH_REQUIRED",
                    "Strict outline audits require the authoritative Source Truth artifact.",
                    retry_strategy="reconcile_page_evidence_mapping",
                )
            )
        else:
            issues.extend(
                AuditIssue(
                    issue.code,
                    issue.message,
                    issue.pages,
                    issue.retry_strategy,
                )
                for issue in audit_argument_flow(outline, source_truth)
            )
    return sorted(issues, key=lambda item: ((item.pages or ("",))[0], item.code))


def retry_directive(issues: list[AuditIssue], previous_strategy: str = "") -> dict[str, object]:
    strategies = list(dict.fromkeys(issue.retry_strategy for issue in issues))
    if previous_strategy in strategies:
        strategies = [item for item in strategies if item != previous_strategy] + ["rebuild_from_source_roles"]
    return {
        "required": bool(issues),
        "issue_codes": list(dict.fromkeys(issue.code for issue in issues)),
        "strategies": strategies,
        "instruction": "Change planning direction, rewrite the outline, and submit the next numbered attempt.",
    }

"""Structural Outline audit rules."""

from __future__ import annotations

import re

from cyberppt.outline_audit_shared import AuditIssue, _core_message, _page_id, _page_mission, _text


SOLUTION_MATERIAL_TERMS = (
    "方案", "前期研究", "立项", "可研", "政府", "央企", "国企", "协会",
)
METHOD_TERMS = ("原则", "方法", "筛选", "评价维度", "选择标准")
FORMAL_TITLE_QUESTION_PREFIXES = ("为什么", "为何", "如何", "怎样", "怎么", "是否")
FORMAL_TITLE_SLOGAN_PREFIXES = ("携手", "共创", "赋能", "开启", "引领", "聚势", "筑梦")


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
def _title_style_issues(
    outline: dict[str, object], pages: list[dict[str, object]]
) -> list[AuditIssue]:
    """Enforce plain declarative titles for formal v2 solution materials by default."""

    configured = str(outline.get("title_style_mode") or "").strip()
    mode = configured or (
        "formal_plain"
        if outline.get("schema") == "cyberppt.outline.v2"
        and _is_solution_material(outline.get("material_type"))
        else "legacy"
    )
    if mode not in {"legacy", "formal_plain", "expressive"}:
        return [
            AuditIssue(
                "TITLE_STYLE_MODE_INVALID",
                "title_style_mode must be legacy, formal_plain, or expressive.",
                retry_strategy="select_supported_title_style",
            )
        ]
    if mode == "expressive":
        if outline.get("user_requested_title_style") is not True:
            return [
                AuditIssue(
                    "TITLE_STYLE_OVERRIDE_UNCONFIRMED",
                    "Expressive titles require an explicit user request.",
                    retry_strategy="restore_formal_plain_titles",
                )
            ]
        return []
    if mode != "formal_plain":
        return []

    issues: list[AuditIssue] = []
    for page in pages:
        title = str(page.get("title") or "").strip()
        if not title:
            continue
        dramatic = (
            title.endswith(("?", "？"))
            or title.startswith(FORMAL_TITLE_QUESTION_PREFIXES)
            or title.startswith(FORMAL_TITLE_SLOGAN_PREFIXES)
            or bool(re.match(r"^从.+到.+", title))
            or title.endswith("的完整构成")
        )
        if dramatic:
            issues.append(
                AuditIssue(
                    "FORMAL_TITLE_NOT_PLAIN",
                    "Formal government and enterprise materials default to plain declarative titles that name the business object and topic; avoid questions, slogans, journey rhetoric, and promotional framing.",
                    (_page_id(page),),
                    "rewrite_as_plain_declarative_title",
                )
            )
    return issues


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
    chapter_pages_present = any(page.get("page_type") == "chapter" for page in pages)
    editorial_chapter_ids = {
        _text(page.get("chapter_id"))
        for page in pages
        if page.get("page_type") == "content" and _text(page.get("chapter_id"))
    }
    single_editorial_chapter_without_page = (
        not chapter_pages_present
        and len(editorial_chapter_ids) == 1
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
        elif (
            page_type == "content"
            and chapter_id
            and chapter_id not in chapter_seen
            and not single_editorial_chapter_without_page
        ):
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

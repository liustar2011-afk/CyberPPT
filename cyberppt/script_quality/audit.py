"""Script-quality audit orchestration and communication review assembly."""

from __future__ import annotations

import re
from dataclasses import replace

from .models import (
    ScriptDocument,
    ScriptPage,
    ScriptQualityIssue,
    _issue,
    resolve_judgment_mode,
)
from .onscreen import (
    ONSCREEN_SEMANTIC_COVERAGE_MIN,
    _is_structured_compact_onscreen_layer,
    _necessity_page_closure_issues,
    _onscreen_content_lines,
    _onscreen_flow_language_issues,
    _page_text,
    _subtitle_policy_issues,
    meaningful_char_count,
    onscreen_effective_char_target,
    onscreen_semantic_coverage,
    onscreen_story_roles,
    structured_layer_char_target,
)
from .presentation import (
    COMPLETED_TERMS,
    CONDITIONAL_STATUSES,
    _preflight_semantic_issues,
    _presentation_issues,
)
from .relationships import (
    _page_relationship_continuity_issues,
    _page_relationship_contract_issues,
)
from .source_coverage import (
    _full_prose_paragraph_boundary_issues,
    _full_prose_source_coverage_issues,
    _onscreen_module_provenance_issues,
    _outline_pages,
    _page_content_unit_coverage_issues,
    _projected_table_header_record_ids,
    _source_consumption_issues,
    _truth_records,
    normalized_tokens,
    text_similarity,
)
from .text_rules import (
    PROSE_MIN_CHARS,
    _compact_len,
    _formulaic_transition_issues,
    _narration_boundary_issues,
    _negative_foreground_issues,
    _prohibited_contrast_issues,
    _prose_issues,
)
from .visibility_contract import (
    _argument_chain_visibility_issues,
    _page_logic_contract_issues,
    _onscreen_visibility_contract_issues,
)
from .visual_semantics import _author_visual_semantic_strength_issues

VISIBLE_JUDGMENT_MIN_SIMILARITY = 0.04

# Extreme floor stays an ERROR under independent-reading audits; the former
# 0.22/0.28 bands remain advisory so authors compress via 取舍说明 instead of
# stuffing tokens to chase coverage.
ONSCREEN_SEMANTIC_COVERAGE_TARGET = 0.28


def build_communication_review(
    script: ScriptDocument,
    outline: dict[str, object],
) -> dict[str, object]:
    """Build a deterministic editorial review alongside the structural audit.

    The review reuses the existing Outline and script fields. It deliberately
    marks semantic questions as manual review instead of pretending that a
    lexical rule can decide whether every module shares one business dimension.
    """

    pages_by_id = _outline_pages(outline)
    page_reviews: list[dict[str, object]] = []
    warning_count = 0
    content_count = 0
    mission_count = 0
    lead_match_count = 0
    authoring_field_count = 0
    density_low_count = 0
    for page in script.pages:
        if page.page_type != "content":
            continue
        content_count += 1
        contract = pages_by_id.get(page.page_id, {})
        mission = str(
            contract.get("page_mission")
            or contract.get("page_job")
            or contract.get("business_question")
            or ""
        ).strip()
        if mission:
            mission_count += 1
        lines = _onscreen_content_lines(page.onscreen_text)
        lead = page.onscreen_judgment or (lines[0] if lines else "")
        lead_matches = bool(
            page.main_message
            and lead
            and (
                lead == page.main_message
                or text_similarity(lead, page.main_message)
                >= VISIBLE_JUDGMENT_MIN_SIMILARITY
            )
        )
        if lead_matches:
            lead_match_count += 1
        core_tokens = set(normalized_tokens(page.main_message))
        visible_tokens = set(
            normalized_tokens(
                "\n".join(
                    part
                    for part in (page.onscreen_judgment, page.onscreen_text)
                    if part.strip()
                )
            )
        )
        core_visible_coverage = (
            len(core_tokens & visible_tokens) / len(core_tokens)
            if core_tokens
            else 1.0
        )
        core_message_display_mode = (
            "explicit_judgment"
            if page.onscreen_judgment
            else "lead"
            if lead_matches
            else "integrated"
            if page.main_message and core_visible_coverage >= 0.55
            else "metadata_only_review"
            if page.main_message
            else "not_applicable"
        )
        visible_judgment_precedes_modules = bool(
            page.onscreen_judgment
            and "上屏结论" in page.field_order
            and "上屏文字" in page.field_order
            and page.field_order.index("上屏结论")
            < page.field_order.index("上屏文字")
        )
        visible_judgment_required = bool(
            str(contract.get("onscreen_conclusion") or contract.get("onscreen_judgment") or "").strip()
        )
        authoring_field_only = bool(
            not visible_judgment_required
            and page.visual_structure
            and not lead_matches
        )
        if authoring_field_only:
            authoring_field_count += 1
        findings: list[dict[str, object]] = []
        if not mission:
            findings.append(
                {
                    "code": "MISSING_BUSINESS_QUESTION",
                    "severity": "warning",
                    "message": "Outline does not provide the page mission.",
                    "suggested_action": "Add business_question to the approved Outline.",
                }
            )
        if core_message_display_mode == "metadata_only_review":
            findings.append(
                {
                    "code": "CORE_MESSAGE_AUDIENCE_VISIBILITY_REVIEW",
                    "severity": "warning",
                    "message": "The page's core judgment may remain only in authoring metadata.",
                    "suggested_action": (
                        "If the judgment is indispensable to the audience, express it as an "
                        "on-screen conclusion, lead, relation-bearing module, or closing result. "
                        "Otherwise record in selection notes why the visible relation already "
                        "expresses it or why direct display would overstate the source."
                    ),
                    "evidence": [
                        page.main_message,
                        f"visible_coverage={core_visible_coverage:.3f}",
                    ],
                }
            )
        if (
            outline.get("schema") != "cyberppt.outline.v2"
            and page.main_message
            and not lead_matches
            and not authoring_field_only
        ):
            findings.append(
                {
                    "code": "MAIN_MESSAGE_NOT_FIRST_ONSCREEN_LINE",
                    "severity": "warning",
                    "message": "The page judgment is not the first drawable on-screen line.",
                    "suggested_action": "Put main_message into the first on-screen line before supporting modules.",
                    "evidence": [page.main_message, lead],
                }
            )
        long_modules = [
            title for title in page.module_titles if _compact_len(title) > 24
        ]
        if long_modules:
            findings.append(
                {
                    "code": "MODULE_TITLE_TOO_LONG",
                    "severity": "warning",
                    "message": "One or more module titles are longer than a short phrase.",
                    "suggested_action": "Rewrite module titles as concise labels; keep the judgment in the lead or body.",
                    "evidence": long_modules,
                }
            )
        long_bullets = [line for line in lines if _compact_len(line) > 72]
        if long_bullets:
            findings.append(
                {
                    "code": "ONSCREEN_BULLET_TOO_LONG",
                    "severity": "warning",
                    "message": "One or more on-screen items combine too much information.",
                    "suggested_action": "Split into one judgment, action, or result per item.",
                    "evidence": long_bullets,
                }
            )
        semantic_coverage = onscreen_semantic_coverage(page)
        effective_chars = meaningful_char_count(
            page.onscreen_judgment + page.onscreen_text
        )
        structured_compact_layer = _is_structured_compact_onscreen_layer(
            page,
            visible_story_chars=effective_chars,
        )
        effective_char_target = (
            structured_layer_char_target(page)
            if structured_compact_layer
            else onscreen_effective_char_target(page)
        )
        density_status = (
            "pass" if effective_chars >= effective_char_target else "low"
        )
        if density_status == "low":
            density_low_count += 1
        story_roles = onscreen_story_roles(page)
        if (
            _compact_len(page.full_prose) >= PROSE_MIN_CHARS * 2
            and semantic_coverage < ONSCREEN_SEMANTIC_COVERAGE_MIN
            and not structured_compact_layer
        ):
            findings.append(
                {
                    "code": "ONSCREEN_SEMANTIC_COVERAGE_LOW",
                    "severity": "warning",
                    "message": "On-screen text omits too much meaning from the full prose.",
                    "suggested_action": (
                        "Restore essential facts, explanatory relations, causal links, "
                        "and the page implication."
                    ),
                    "evidence": [
                        f"coverage={semantic_coverage:.3f}",
                        f"min={ONSCREEN_SEMANTIC_COVERAGE_MIN:.3f}",
                    ],
                }
            )
        elif (
            _compact_len(page.full_prose) >= PROSE_MIN_CHARS * 2
            and semantic_coverage < ONSCREEN_SEMANTIC_COVERAGE_TARGET
            and not structured_compact_layer
        ):
            findings.append(
                {
                    "code": "ONSCREEN_SEMANTIC_COVERAGE_BELOW_TARGET",
                    "severity": "warning",
                    "message": "On-screen semantic coverage passes the gate but remains below target.",
                    "suggested_action": (
                        "Restore additional evidence or relationship meaning when the page "
                        "still feels dependent on narration."
                    ),
                    "evidence": [
                        f"coverage={semantic_coverage:.3f}",
                        f"target={ONSCREEN_SEMANTIC_COVERAGE_TARGET:.3f}",
                    ],
                }
            )
        missing_story_roles = [
            role
            for role, present in story_roles.items()
            if not present
        ]
        if page.onscreen_judgment and missing_story_roles:
            findings.append(
                {
                    "code": "ONSCREEN_STORY_NOT_CLOSED",
                    "severity": "warning",
                    "message": "On-screen text lacks one or more structural story roles.",
                    "suggested_action": (
                        "Complete the conclusion-evidence-relation-closure chain without "
                        "adding formulaic transition words."
                    ),
                    "evidence": missing_story_roles,
                }
            )
        warning_count += len(findings)
        page_reviews.append(
            {
                "page_id": page.page_id,
                "sequence": page.sequence,
                "title": page.title,
                "mission": mission,
                "core_message": page.core_message,
                "main_message": page.main_message,
                "onscreen_conclusion": page.onscreen_conclusion,
                "onscreen_judgment": page.onscreen_judgment,
                "visible_judgment_present": bool(page.onscreen_judgment),
                "visible_judgment_aligned": lead_matches,
                "visible_judgment_precedes_modules": (
                    visible_judgment_precedes_modules
                ),
                "lead": lead,
                "lead_matches_main_message": lead_matches,
                "core_message_display_mode": core_message_display_mode,
                "core_message_visible_coverage": round(core_visible_coverage, 3),
                "lead_status": (
                    "pass"
                    if lead_matches
                    else "authoring_field_only"
                    if authoring_field_only
                    else "warning"
                ),
                "module_titles": list(page.module_titles),
                "numeric_lines": [line for line in lines if re.search(r"\d", line)],
                "semantic_coverage": round(semantic_coverage, 3),
                "effective_chars": effective_chars,
                "effective_char_target": effective_char_target,
                "reading_density_status": density_status,
                "story_roles": story_roles,
                "findings": findings,
                "review_questions": {
                    "single_mission": "manual_review",
                    "module_same_dimension": "manual_review",
                    "nonessential_information_removed": "manual_review",
                    "leadership_expandability": (
                        "pass" if page.speaker_notes else "check"
                    ),
                    "visual_expression_ready": (
                        "pass" if page.visual_structure else "check"
                    ),
                },
            }
        )
    return {
        "schema": "cyberppt.communication_review.v1",
        "content_pages": content_count,
        "mission_coverage": mission_count,
        "lead_match_count": lead_match_count,
        "authoring_field_count": authoring_field_count,
        "lead_coverage_count": lead_match_count + authoring_field_count,
        "reading_density_default": "high",
        "reading_density_low_count": density_low_count,
        "warning_count": warning_count,
        "manual_review_required": True,
        "pages": page_reviews,
    }


VISIBLE_JUDGMENT_TERMINAL_PUNCTUATION = "。；，：？！.!?;,:"


SCOPE_TERMS = ("首期", "一期", "建设范围", "交付范围", "投资", "部署方式", "采购")
# “预算”在价格表达、套餐控制和采购口径中是正常业务名词，不能一概
# 视为提前给出实施结论。仅在它与项目/建设/投资实施绑定时触发。
IMPLEMENTATION_TERMS = (
    "实施路线",
    "建设周期",
    "前100天",
    "组织组建",
    "项目预算",
    "建设预算",
    "实施预算",
    "投资预算",
)
# Every signal tuple below is matched with a bare substring test
# (`_has_any`/`term in text`). Keep every entry at least 2 characters and
# specific to the relationship it claims to detect — a single common
# character ("层", "上", "行"...) or a generic connective ("再", "最后")
# will match incidental prose that has nothing to do with the structure
# being checked, silently defeating the check it belongs to. This bit both
# ways: the checker never fires when it should (false pass on a page with
# no real structure) and never fires when content is deliberately padded
# with the bare character to game it. This was found and fixed for
# LAYER_SIGNALS's old bare "层"; keep new entries to the same bar.
COMPOSITION_PRIMITIVES = (
    "贯穿主链",
    "双侧协同",
    "受控边界",
    "分层剖面",
    "汇聚引擎输出",
    "判断证据支撑",
    "非对称对照",
    "机制作用范围",
    "主体泳道",
    "阶段推进",
    "矩阵筛选",
    "闭环回流",
)
# Matched by suffix rather than a fixed vocabulary list, so this generalizes
# past whichever project's engine/mechanism naming happened to be used first.
SPATIAL_SIGNALS = (
    "左",
    "右",
    "上",
    "下",
    "中央",
    "中心",
    "主链",
    "由左向右",
    "由右向左",
    "自上而下",
    "自下而上",
    "贯穿",
    "托举",
    "对照",
    "回流",
    "边界",
    "层级",
    "底座",
)
STRATEGY_ORDER = (
    "mission_restructure",
    "business_prose_first",
    "source_state_rebuild",
    "cross_page_dedup",
    "semantic_diagram_realign",
    "density_recompose",
    "manuscript_form_cleanup",
    "speaker_notes_naturalize",
)

_TERM_HEDGE_LEAD_RE = re.compile(r"(具备|符合|满足|达到)[^。；]{0,12}$")
_TERM_HEDGE_TRAIL_CONDITION_RE = re.compile(r"^[^。；]{0,12}(条件|基础)")
_TERM_HEDGE_TRAIL_NEGATION_RE = re.compile(r"^[^。；]{0,10}(尚未|尚不|待定|暂缓|暂未|仍需|有待|尚待)")


def _unhedged_terms(text: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    """Return the subset of `terms` that appear in `text` without a hedging frame.

    A bare substring match can't distinguish a commitment ("首期建设范围
    包括...") from a hedged readiness/pending statement ("具备开展首期...的
    条件", "建设周期尚未确定"). Only flag a term when at least one of its
    occurrences sits outside both recognized hedge shapes:
    - a "具备/符合/满足/达到 ... 条件/基础" precondition frame around the term;
    - a "尚未/尚不/待定/暂缓/暂未/仍需/有待/尚待" negation immediately after it.
    A term whose every occurrence is hedged this way is not a violation.
    """

    unhedged: list[str] = []
    for term in terms:
        for match in re.finditer(re.escape(term), text):
            before = text[max(0, match.start() - 16) : match.start()]
            after = text[match.end() : match.end() + 16]
            if _TERM_HEDGE_LEAD_RE.search(before) and _TERM_HEDGE_TRAIL_CONDITION_RE.search(after):
                continue
            if _TERM_HEDGE_TRAIL_NEGATION_RE.search(after):
                continue
            unhedged.append(term)
            break
    return tuple(unhedged)


def _unhedged_scope_terms(text: str) -> tuple[str, ...]:
    return _unhedged_terms(text, SCOPE_TERMS)


def _claim_text(page: ScriptPage) -> str:
    return "\n".join(
        (
            page.title,
            page.main_message,
            page.onscreen_judgment,
            page.full_prose,
            page.onscreen_text,
        )
    )


def script_retry_directive(
    issues: list[ScriptQualityIssue],
    previous_strategy: str = "",
) -> dict[str, object]:
    codes = sorted({issue.code for issue in issues})
    # A final-manuscript banner is a path-level contract failure.  It must
    # take precedence over page-content diagnostics so the retry points to
    # the assembly/form-cleanup step first.
    if "FINAL_MANUSCRIPT_DRAFT_BANNER" in codes:
        preferred = "manuscript_form_cleanup"
    elif any(
        code
        in {
            "CONTENT_PROSE_MISSING",
            "CONTENT_PROSE_AFTER_ONSCREEN",
            "CONTENT_PROSE_TOO_THIN",
            "CONTENT_PROSE_EQUALS_ONSCREEN",
            "CONTENT_PROSE_ONSCREEN_GRANULARITY",
            "CONTENT_PROSE_ANALYTICAL_VOICE",
            "CONTENT_BOUNDARY_ASIDE_OVERLOAD",
            "PROHIBITED_NEGATIVE_CONTRAST",
            "NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC",
            "ONSCREEN_BOUNDARY_ASIDE",
            "ONSCREEN_RELATION_META_LABEL",
            "ONSCREEN_COMPOUND_GROUP_HEADING",
            "CONTENT_SELECTION_NOTES_MISSING",
            "CONTENT_SELECTION_NOTES_UNSTRUCTURED",
            "CONTENT_SELECTION_ONSCREEN_MISMATCH",
            "CONTENT_EVIDENCE_MAP_MISSING",
            "PROSE_SOURCE_COVERAGE_GAP",
            "ONSCREEN_DETAIL_PHRASE_TOO_LONG",
            "ONSCREEN_LAYOUT_META_LEAK",
            "ONSCREEN_RELATION_ISOMORPHISM",
            "ONSCREEN_MECHANICAL_LABEL_TEMPLATE",
        }
        for code in codes
    ):
        preferred = "business_prose_first"
    elif any(
        code
        in {
            "SOURCE_STATE_UPGRADED",
            "BOUNDARY_DROPPED",
            "UNRESOLVED_AS_CONFIRMED",
        }
        for code in codes
    ):
        preferred = "source_state_rebuild"
    elif any(
        "DUPLICATE" in code or "REEXPANDED" in code
        for code in codes
    ):
        preferred = "cross_page_dedup"
    elif any(
        code
        in {
            "CONTENT_SPEAKER_NOTES_MISSING",
            "CONTENT_SPEAKER_NOTES_TOO_THIN",
            "SPEAKER_NOTES_SLIDE_META",
            "SPEAKER_NOTES_HOST_META",
            "SPEAKER_NOTES_PLACEHOLDER_PROSE",
            "NARRATION_BOUNDARY_COACHING",
            "NARRATION_INTERNAL_BOUNDARY_LEAK",
        }
        for code in codes
    ):
        preferred = "speaker_notes_naturalize"
    elif any(
        code
        in {
            "PATH_ORDER_SIGNAL_MISSING",
            "LOOP_RETURN_SIGNAL_MISSING",
            "MATRIX_AXES_MISSING",
            "LAYER_HIERARCHY_MISSING",
            "DECLARED_COUNT_MISMATCH",
            "SEMANTIC_DIAGRAM_MISMATCH",
            "VISUAL_STRUCTURE_STYLE_ONLY",
            "VISUAL_STRUCTURE_TOO_THIN",
            "VISUAL_STRUCTURE_CROSSCUT_AS_PEER",
            "VISUAL_STRUCTURE_LAYOUT_RECIPE",
            "VISUAL_STRUCTURE_MULTIPLE_PRIMARY_NARRATIVES",
            "VISUAL_STRUCTURE_MECHANISM_AS_LANE",
            "ONSCREEN_ANTI_PATTERN",
            "PRIMITIVE_ONSCREEN_MISMATCH",
            "ONSCREEN_RELATION_ISOMORPHISM",
            "ONSCREEN_SOURCE_ATOMIZATION",
            "ONSCREEN_GENERIC_RELATION_PLACEHOLDER",
        }
        for code in codes
    ):
        preferred = "semantic_diagram_realign"
    elif any(
        code
        in {
            "CONTENT_PAGE_TOO_SPARSE",
            "CONTENT_PAGE_TOO_FRAGMENTED",
            "MODULE_HIERARCHY_MISSING",
            "ONSCREEN_STORY_DENSITY_LOW",
            "ONSCREEN_SEMANTIC_COVERAGE_LOW",
            "ONSCREEN_STORY_NOT_CLOSED",
        }
        for code in codes
    ):
        preferred = "density_recompose"
    else:
        preferred = "mission_restructure"
    strategy = preferred
    if strategy == previous_strategy:
        index = (STRATEGY_ORDER.index(strategy) + 1) % len(STRATEGY_ORDER)
        strategy = STRATEGY_ORDER[index]
    instruction = (
        "Rewrite only the failed pages using the new strategy; preserve "
        "valid evidence, states, and page contracts."
    )
    if "FINAL_MANUSCRIPT_DRAFT_BANNER" in codes:
        instruction = (
            "Remove every draft/batch banner and the words 草稿/批次 from the "
            "final manuscript (prefer `assemble-final-script`), then re-audit."
        )
    elif any(
        code
        in {
            "PROHIBITED_NEGATIVE_CONTRAST",
            "NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC",
        }
        for code in codes
    ):
        instruction = (
            "Rewrite the failed title and leading script as a direct positive "
            "subject–action–value/result statement. Do not use a rejected "
            "alternative, and keep necessary control conditions subordinate "
            "unless the approved page itself is a direct boundary clarification."
        )
    elif any(
        code.startswith("CONTENT_SPEAKER_NOTES")
        or code
        in {
            "SPEAKER_NOTES_SLIDE_META",
            "SPEAKER_NOTES_HOST_META",
            "SPEAKER_NOTES_PLACEHOLDER_PROSE",
            "NARRATION_BOUNDARY_COACHING",
            "NARRATION_INTERNAL_BOUNDARY_LEAK",
        }
        for code in codes
    ):
        instruction = (
            "Rewrite 讲解提示 and 【演讲者备注】 as direct business narration; "
            "keep internal boundaries and defensive coaching out of both fields."
        )
    return {
        "required": bool(issues),
        "issue_codes": codes,
        "strategy": strategy,
        "instruction": instruction,
    }


def audit_script_quality(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
    *,
    source_units: tuple[dict[str, object], ...] = (),
) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    pages_by_id = _outline_pages(outline)
    records_by_id = _truth_records(source_truth)
    structural_metadata_refs = _projected_table_header_record_ids(
        records_by_id,
        source_units,
    )
    sequences = [page.sequence for page in script.pages]
    outline_sequences = [
        int(page.get("sequence"))
        for page in outline.get("pages", [])
        if isinstance(page, dict) and isinstance(page.get("sequence"), int)
    ]
    outline_page_ids = [
        str(page.get("page_id") or "")
        for page in outline.get("pages", [])
        if isinstance(page, dict) and str(page.get("page_id") or "")
    ]
    follows_approved_outline_sequence = (
        sequences == outline_sequences
        or [page.page_id for page in script.pages] == outline_page_ids
    )
    if (
        sequences != list(range(min(sequences), max(sequences) + 1))
        and not follows_approved_outline_sequence
    ):
        issues.append(
            ScriptQualityIssue(
                "SCRIPT_PAGE_SEQUENCE_GAP",
                "error",
                "Script page numbers must be continuous or exactly follow the approved Outline sequence.",
                tuple(page.page_id for page in script.pages),
                suggested_action=(
                    "Restore the missing page or split the input into "
                    "explicit continuous batches."
                ),
            )
    )
    for page in script.pages:
        issues.extend(_prohibited_contrast_issues(page))
        contract = pages_by_id.get(page.page_id)
        if contract is None:
            issues.extend(_negative_foreground_issues(page, {}))
            issues.append(
                _issue(
                    "SCRIPT_PAGE_NOT_IN_OUTLINE",
                    page,
                    "Script page has no matching Outline contract.",
                    "Add the page to the approved Outline or remove it from the script batch.",
                )
            )
            continue
        issues.extend(_negative_foreground_issues(page, contract))
        expected_type = str(contract.get("page_type") or "")
        if expected_type == "chapter" and (
            page.page_type != "chapter"
            or page.main_message
            or page.full_prose
            or page.selection_notes
            or page.evidence_map
            or page.module_titles
        ):
            issues.append(
                _issue(
                    "CHAPTER_PAGE_HAS_CONTENT",
                    page,
                    "Chapter transition pages may contain only the chapter title.",
                    "Remove the thesis, prose, selection notes, evidence map, modules, methods, and task text from this page.",
                )
            )
        if expected_type == "content":
            issues.extend(_subtitle_policy_issues(page, contract))
            issues.extend(_onscreen_module_provenance_issues(page, contract))
            explicit_judgment_mode = str(
                contract.get("onscreen_judgment_mode") or page.onscreen_judgment_mode
            ).strip()
            judgment_role = str(
                contract.get("judgment_role") or page.judgment_role
            ).strip()
            try:
                judgment_mode = resolve_judgment_mode(
                    explicit_judgment_mode, judgment_role,
                )
            except ValueError as exc:
                issues.append(
                    _issue(
                        "ONSCREEN_JUDGMENT_MODE_INVALID",
                        page,
                        str(exc),
                        "Use locked, semantic_alignment, hidden, or the legacy semantic_only mode.",
                        evidence=tuple(
                            value for value in (explicit_judgment_mode, judgment_role) if value
                        ),
                    )
                )
                judgment_mode = "locked"
            expected_judgment = str(
                contract.get("onscreen_conclusion")
                or contract.get("onscreen_judgment")
                or ""
            ).strip()
            visible_judgment_required = (
                judgment_mode in {"locked", "semantic_alignment"}
                and (bool(expected_judgment) or judgment_mode == "semantic_alignment")
            )
            if (
                not page.source_refs
                or not page.visual_structure
            ):
                issues.append(
                    _issue(
                        "CONTENT_PAGE_FIELDS_MISSING",
                        page,
                        "Content page requires evidence and visual structure; a judgment is optional.",
                        "Restore the missing backend fields before review.",
                    )
                )
            if visible_judgment_required:
                if not page.onscreen_judgment:
                    issues.append(
                        _issue(
                            "ONSCREEN_JUDGMENT_MISSING",
                            page,
                            "Content page requires a visible body-level judgment before supporting modules.",
                            "Add 上屏结论 and make it state the page conclusion in one concise sentence.",
                        )
                    )
                else:
                    if page.onscreen_judgment.endswith(
                        tuple(VISIBLE_JUDGMENT_TERMINAL_PUNCTUATION)
                    ):
                        issues.append(
                            _issue(
                                "ONSCREEN_JUDGMENT_TERMINAL_PUNCTUATION",
                                page,
                                "上屏结论 must not end with standard sentence punctuation.",
                                "Remove the final period, comma, semicolon, colon, question mark, or exclamation mark.",
                                evidence=(page.onscreen_judgment,),
                            )
                        )
                    if (
                        judgment_mode == "locked"
                        and
                        expected_judgment
                        and page.onscreen_judgment != expected_judgment
                    ):
                        issues.append(
                            _issue(
                                "ONSCREEN_JUDGMENT_CONTRACT_MISMATCH",
                                page,
                                "上屏结论 does not match the approved Outline contract.",
                                "Restore the approved onscreen_judgment or revise and re-approve the Outline.",
                                evidence=(
                                    expected_judgment,
                                    page.onscreen_judgment,
                                ),
                            )
                        )
                    judgment_index = (
                        page.field_order.index("上屏结论")
                        if "上屏结论" in page.field_order
                        else -1
                    )
                    onscreen_index = (
                        page.field_order.index("上屏文字")
                        if "上屏文字" in page.field_order
                        else -1
                    )
                    if (
                        judgment_index < 0
                        or onscreen_index < 0
                        or judgment_index > onscreen_index
                    ):
                        issues.append(
                            _issue(
                                "ONSCREEN_JUDGMENT_ORDER_INVALID",
                                page,
                                "上屏结论 must appear before 上屏文字.",
                                "Move 上屏结论 immediately before the supporting 上屏文字 modules.",
                            )
                        )
                    if text_similarity(
                        page.onscreen_judgment,
                        page.main_message,
                    ) < VISIBLE_JUDGMENT_MIN_SIMILARITY:
                        issues.append(
                            _issue(
                                "ONSCREEN_JUDGMENT_MISALIGNED",
                                page,
                                "The visible judgment is not sufficiently aligned with the page main judgment.",
                                "Rewrite 上屏结论 as a concise audience-facing version of 主判断.",
                                evidence=(
                                    page.main_message,
                                    page.onscreen_judgment,
                                ),
                            )
                        )
            elif page.onscreen_judgment:
                issues.append(
                    _issue(
                        "SCRIPT_JUDGMENT_INTRODUCED",
                        page,
                        "The script introduces an on-screen judgment that is absent from the approved Outline.",
                        "Remove the judgment; downstream stages may not manufacture conclusions.",
                        evidence=(page.onscreen_judgment,),
                    )
                )
            expected_refs = tuple(
                str(item)
                for item in contract.get("source_refs", [])
                if item
            )
            expected_boundary_refs = tuple(
                str(item) for item in contract.get("boundary_refs", []) if item
            )
            content_unit_field = (
                "content_units"
                if contract.get("content_units") is not None
                else "proof_points"
            )
            expected_proof_refs = tuple(
                dict.fromkeys(
                    str(source_id)
                    for point in contract.get(content_unit_field, [])
                    if isinstance(point, dict)
                    for source_id in point.get("source_refs", [])
                )
            )
            issues.extend(
                _prose_issues(
                    page,
                    expected_source_refs=expected_proof_refs,
                    # All content pages are reading pages by default.  This density
                    # requirement is deliberately independent from whether the
                    # approved Outline declares an onscreen conclusion.
                    independent_reading_required=page.page_type == "content",
                    strict_reading_density=(
                        outline.get("schema") == "cyberppt.outline.v2"
                    ),
                    contract=contract,
                )
            )
            issues.extend(_source_consumption_issues(page, contract))
            issues.extend(_argument_chain_visibility_issues(page, contract))
            issues.extend(_page_logic_contract_issues(page, contract))
            issues.extend(_onscreen_visibility_contract_issues(page, contract))
            issues.extend(
                _author_visual_semantic_strength_issues(
                    page,
                    contract,
                    records_by_id,
                )
            )
            issues.extend(
                _page_relationship_contract_issues(
                    page,
                    contract,
                    records_by_id,
                )
            )
            issues.extend(
                _full_prose_source_coverage_issues(
                    page,
                    contract,
                    records_by_id,
                    structural_metadata_refs,
                )
            )
            issues.extend(
                _full_prose_paragraph_boundary_issues(
                    page,
                    contract,
                    records_by_id,
                    structural_metadata_refs,
                )
            )
            # `_onscreen_enumeration_loss_issues` is deliberately NOT wired
            # in here. It is a real, tested check (see
            # OnscreenEnumerationLossTests) kept available for opt-in,
            # manual use -- but syntactic item-counting cannot distinguish
            # ordinary compression from a genuine silent business-option
            # drop, and running it on every page flooded real audits with
            # noise (dozens of warnings/page) without a workable precision
            # gain from tuning the threshold or the item-boundary
            # extraction. The actual fix for this failure mode belongs in
            # the authoring step itself (see cyberppt-write-single-page's
            # 压缩为可独立阅读的上屏文字 guidance), not as a blanket audit gate.
            if (
                outline.get("semantic_argument_model_mode") == "required"
                or outline.get("page_content_unit_coverage_mode") == "required"
            ):
                issues.extend(
                    _page_content_unit_coverage_issues(
                        page,
                        contract,
                        structural_metadata_refs,
                    )
                )
            issues.extend(_narration_boundary_issues(page, contract))
            issues.extend(_preflight_semantic_issues(page, contract, records_by_id))
            if outline.get("page_contract_receipt_mode") == "required":
                receipt = page.contract_receipt
                if receipt is None:
                    issues.append(
                        _issue(
                            "PAGE_CONTRACT_RECEIPT_MISSING",
                            page,
                            "Strict content pages must retain the hidden page-contract receipt.",
                            "Generate page-contracts.json beside the final script, or migrate the legacy inline receipt.",
                        )
                    )
                elif receipt.get("_invalid") is True:
                    issues.append(
                        _issue(
                            "PAGE_CONTRACT_RECEIPT_INVALID",
                            page,
                            "The hidden page-contract receipt is not valid JSON.",
                            "Regenerate the receipt from page-script-authoring-input.",
                        )
                    )
                else:
                    canonical_fields = (
                        "page_job",
                        "business_question",
                        "main_message",
                        "new_value_vs_previous",
                        "reserved_for_later",
                        "proof_points",
                        "boundary_refs",
                    )
                    if receipt.get("schema") == "cyberppt.page_contract_receipt.v2":
                        canonical_fields = (
                            "page_mission",
                            "audience_question",
                            "business_question",
                            "must_not_include",
                            "split_risk",
                            "split_risk_reason",
                            "core_message",
                            "onscreen_conclusion",
                            "core_message_derivation",
                            "content_relations",
                            "page_logic_contract",
                            "page_logic_contract_mode",
                            "new_value_vs_previous",
                            "reserved_for_later",
                            "content_units",
                            "boundary_refs",
                        )
                    if (
                        visible_judgment_required
                        and receipt.get("schema")
                        != "cyberppt.page_contract_receipt.v1"
                    ):
                        canonical_fields = (
                            *canonical_fields[:3],
                            "onscreen_judgment",
                            *canonical_fields[3:],
                        )
                    mismatched = tuple(
                        field
                        for field in canonical_fields
                        if receipt.get(field) != contract.get(field)
                    )
                    if (
                        receipt.get("page_id") != page.page_id
                        or (
                            receipt.get("core_message", receipt.get("main_message"))
                            != page.core_message
                        )
                        or mismatched
                    ):
                        issues.append(
                            _issue(
                                "PAGE_CONTRACT_RECEIPT_MISMATCH",
                                page,
                                "The hidden receipt does not match the approved Outline or script judgment.",
                                "Regenerate the page from the current page-script-authoring-input.",
                                evidence=mismatched,
                            )
                        )
                    if (
                        receipt.get("new_value_realized") is not True
                        or receipt.get("reserved_for_later_respected") is not True
                        or (
                            contract.get("audience_question") is not None
                            and receipt.get("audience_question_answered") is not True
                        )
                        or (
                            contract.get("must_not_include") is not None
                            and receipt.get("must_not_include_respected") is not True
                        )
                        or (
                            contract.get("split_risk") is not None
                            and receipt.get("split_risk_resolved") is not True
                        )
                    ):
                        issues.append(
                            _issue(
                                "PAGE_CONTRACT_CONSUMPTION_UNCONFIRMED",
                                page,
                                "The page does not confirm its approved audience question, exclusions, split-risk resolution, new value, and reserved-content discipline.",
                                "Review the page and set each receipt decision to true only after confirmation.",
                            )
                        )
            missing = tuple(
                item for item in expected_refs if item not in page.source_refs
            )
            if missing:
                issues.append(
                    _issue(
                        "SCRIPT_SOURCE_REF_MISSING",
                        page,
                        "Script does not cite all Source IDs assigned by the Outline.",
                        "Restore the assigned Source IDs or revise the approved Outline contract.",
                        missing,
                    )
                )
            if set(page.boundary_source_refs) != set(expected_boundary_refs):
                issues.append(
                    _issue(
                        "SCRIPT_BOUNDARY_REF_MISMATCH",
                        page,
                        "Script boundary evidence must match Outline boundary_refs.",
                        "Keep boundary-only sources under 边界依据 and out of the main evidence map.",
                        evidence=tuple(
                            sorted(
                                set(page.boundary_source_refs)
                                ^ set(expected_boundary_refs)
                            )
                        ),
                    )
                )
        unknown = tuple(
            item for item in page.source_refs if item not in records_by_id
        )
        if unknown:
            issues.append(
                _issue(
                    "SCRIPT_SOURCE_REF_UNKNOWN",
                    page,
                    "Script cites Source IDs that do not resolve in Source Truth.",
                    "Correct the references before script approval.",
                    unknown,
                )
            )
        role = str(contract.get("argument_role") or "")
        claim_text = _claim_text(page)
        if role in {"foundation", "change", "gap", "necessity"}:
            approved_scope_text = "\n".join(
                str(contract.get(field) or "")
                for field in (
                    "title",
                    "page_mission",
                    "audience_question",
                    "core_message",
                    "main_message",
                )
            )
            approved_scope_terms = set(_unhedged_scope_terms(approved_scope_text))
            approved_source_scope_text = "\n".join(
                str(records_by_id.get(source_id, {}).get("statement") or "")
                for source_id in page.source_refs
            )
            approved_scope_terms.update(
                _unhedged_scope_terms(approved_source_scope_text)
            )
            matched = tuple(
                term
                for term in _unhedged_scope_terms(claim_text)
                if term not in approved_scope_terms
            )
            if matched:
                issues.append(
                    _issue(
                        "PREMATURE_SCOPE_CLAIM",
                        page,
                        "Page introduces scope or delivery claims before the scope stage.",
                        "Keep this page within its argument role and move scope claims to the approved scope page.",
                        evidence=matched,
                    )
                )
        if role in {
            "foundation",
            "change",
            "gap",
            "necessity",
            "positioning",
            "solution",
            "scope",
        }:
            matched = _unhedged_terms(claim_text, IMPLEMENTATION_TERMS)
            if matched:
                issues.append(
                    _issue(
                        "PREMATURE_IMPLEMENTATION_CLAIM",
                        page,
                        "Page introduces implementation claims before the implementation stage.",
                        "Move implementation details to pages whose argument role is implementation or assurance.",
                        evidence=matched,
                    )
                )
        conditional_sources = tuple(
            ref
            for ref in page.source_refs
            if any(
                token
                in str(records_by_id.get(ref, {}).get("status") or "")
                for token in CONDITIONAL_STATUSES
            )
        )
        completed = tuple(
            term for term in COMPLETED_TERMS if term in _page_text(page)
        )
        if conditional_sources and completed:
            issues.append(
                _issue(
                    "SOURCE_STATE_UPGRADED",
                    page,
                    "Conditional or proposed evidence is written as completed or formally decided.",
                    "Restore proposed, conditional, pending, or deferred wording from Source Truth.",
                    conditional_sources,
                    completed,
                )
            )
        issues.extend(_necessity_page_closure_issues(page, contract))
        issues.extend(_onscreen_flow_language_issues(page, contract))
        issues.extend(_formulaic_transition_issues(page))
        issues.extend(
            _presentation_issues(
                page,
                contract,
                strict_detail_phrase_length=(
                    outline.get("schema") == "cyberppt.outline.v2"
                ),
            )
        )
    issues.extend(_page_relationship_continuity_issues(script, pages_by_id))
    for left, right in zip(script.pages, script.pages[1:]):
        similarity = text_similarity(left.main_message, right.main_message)
        if left.main_message and right.main_message and similarity >= 0.82:
            issues.append(
                ScriptQualityIssue(
                    "ADJACENT_MAIN_MESSAGE_DUPLICATE",
                    "error",
                    "Adjacent pages repeat substantially the same main judgment.",
                    (left.page_id, right.page_id),
                    evidence=(
                        left.main_message,
                        right.main_message,
                        f"similarity={similarity:.3f}",
                    ),
                    suggested_action=(
                        "Keep the complete argument on one page and make the "
                        "adjacent page advance a different business question."
                    ),
                )
            )
        visible_similarity = text_similarity(
            left.onscreen_judgment,
            right.onscreen_judgment,
        )
        if (
            left.onscreen_judgment
            and right.onscreen_judgment
            and visible_similarity >= 0.82
        ):
            issues.append(
                ScriptQualityIssue(
                    "ADJACENT_ONSCREEN_JUDGMENT_DUPLICATE",
                    "error",
                    "Adjacent pages repeat substantially the same visible judgment.",
                    (left.page_id, right.page_id),
                    evidence=(
                        left.onscreen_judgment,
                        right.onscreen_judgment,
                        f"similarity={visible_similarity:.3f}",
                    ),
                    suggested_action=(
                        "Make the later page advance the chapter argument instead of restating the prior conclusion."
                    ),
                )
            )
    # Stage 01 protects factual traceability, page contracts, and script
    # completeness.  Visual density, module hierarchy, and relation rendering
    # belong to Stage 02, where the actual slide geometry is available.
    stage02_expression_codes = frozenset(
        {
            "ONSCREEN_HEADING_LENGTH_IMBALANCED",
            "ONSCREEN_LINE_TOO_LONG",
            "VISIBLE_NODE_OVERLOAD",
            "VISUAL_STRUCTURE_TOO_THIN",
            "DECLARED_RELATION_NOT_VISIBLE",
            "ONSCREEN_FALSE_RELATION_PARALLEL",
            "ONSCREEN_FLOW_ACTION_MISSING",
            "ONSCREEN_LAYOUT_META_LEAK",
            "ONSCREEN_RELATION_ISOMORPHISM",
            "ONSCREEN_MECHANICAL_LABEL_TEMPLATE",
        }
    )
    issues = [
        replace(issue, severity="warning")
        if issue.code in stage02_expression_codes and issue.severity == "error"
        else issue
        for issue in issues
    ]
    return issues

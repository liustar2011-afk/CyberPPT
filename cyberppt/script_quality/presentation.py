"""Page presentation, visual-structure, and semantic preflight rules."""

from __future__ import annotations

import re

from cyberppt.onscreen_expression import (
    audit_expression_balance,
    resolve_onscreen_expression,
)

from .models import ScriptPage, ScriptQualityIssue, _issue, resolve_judgment_mode
from .onscreen import (
    ANTI_PATTERN_TERMS,
    BUSINESS_LANE_LABEL_RE,
    LAYER_LIKE_INTENT_TYPES,
    LAYER_SIGNALS,
    LOOP_SIGNALS,
    MATRIX_SIGNALS,
    MECHANISM_LANE_LABEL_RE,
    MODULE_CEILING,
    NUMBERED_ORDER_SIGNAL_RE,
    ONSCREEN_CONSTRAINT_DETAIL_TERMS,
    ONSCREEN_DETAIL_PHRASE_ERROR_CHARS,
    ORDER_SIGNALS,
    PATH_LIKE_INTENT_TYPES,
    SEMANTIC_STRUCTURE_SIGNALS,
    STYLE_ONLY_TERMS,
    VISUAL_STRUCTURE_MULTIPLE_PRIMARY_RE,
    _compound_module_heading_hits,
    _constraint_is_declared_subject,
    _declared_count,
    _has_any,
    _mechanical_onscreen_label_pattern_hits,
    _onscreen_backend_meta_hits,
    _onscreen_constraint_module_hits,
    _onscreen_content_lines,
    _onscreen_detail_phrase_overages,
    _onscreen_false_parallel_semantics,
    _onscreen_flat_long_labelled_detail_hits,
    _onscreen_heading_candidates,
    _onscreen_layout_meta_hits,
    _onscreen_markdown_hits,
    _onscreen_module_dimension_consistency_issues,
    _onscreen_parallel_structure_issues,
    _onscreen_redundant_restatement_issues,
    _onscreen_parent_child_role_mismatches,
    _onscreen_relation_meta_hits,
    _onscreen_subordinate_fragments,
    _page_relation_corpus,
    _page_text,
    _visual_module_label,
    _visual_structure_chain_nodes,
    _visual_structure_layout_recipe_hits,
    onscreen_effective_char_target,
)
from .text_rules import (
    NEGATION_TERMS,
    _boundary_aside_hits,
    _compact_len,
    _prohibited_contrast_hits,
)


COMPLETED_TERMS = ("已经建成", "已建成", "已经形成完整", "已完成建设", "正式确定")
CONDITIONAL_STATUSES = ("拟", "建议", "待", "暂缓", "后续验证", "条件成熟")
VISIBLE_CERTAINTY_TERMS = COMPLETED_TERMS + (
    "已经批准",
    "已批准",
    "正式立项",
    "最终确定",
    "将建成",
    "已经实现",
)


def _preflight_semantic_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    explicit_mode = str(
        contract.get("onscreen_judgment_mode") or page.onscreen_judgment_mode
    ).strip()
    judgment_role = str(
        contract.get("judgment_role") or page.judgment_role
    ).strip()
    try:
        judgment_mode = resolve_judgment_mode(explicit_mode, judgment_role)
    except ValueError as exc:
        issues.append(
            _issue(
                "ONSCREEN_JUDGMENT_MODE_INVALID",
                page,
                str(exc),
                "Use a supported judgment_role or explicitly set locked, semantic_alignment, hidden, or legacy semantic_only.",
                evidence=tuple(part for part in (explicit_mode, judgment_role) if part),
                severity="error",
            )
        )
        judgment_mode = "locked"
    approved_judgment = str(contract.get("onscreen_judgment") or "").strip()
    if judgment_mode == "semantic_only" and approved_judgment:
        if not page.onscreen_judgment.strip():
            issues.append(
                _issue(
                    "SEMANTIC_JUDGMENT_LOST",
                    page,
                    "A semantic-only page has no judgment to carry into the complete page semantics.",
                    "Provide the approved judgment even though it is not locked for display.",
                    severity="error",
                )
            )
    constraint_is_subject = _constraint_is_declared_subject(page, contract)
    if not constraint_is_subject:
        module_hits = _onscreen_constraint_module_hits(page)
        detail_hits = tuple(
            term
            for term in ONSCREEN_CONSTRAINT_DETAIL_TERMS
            if term in page.onscreen_text
        )
        if module_hits or len(detail_hits) >= 2:
            issues.append(
                _issue(
                    "OFF_TOPIC_CONSTRAINT_MODULE",
                    page,
                    "A normal topic page promotes boundary or quality constraints into "
                    "visible content even though constraints are not the page subject.",
                    "Remove the constraint module from 上屏文字 and keep it in internal "
                    "boundary controls or the dedicated governance/safety/acceptance page.",
                    evidence=module_hits + detail_hits,
                    severity="error",
                )
            )
    if (
        judgment_mode == "locked"
        and len(re.sub(r"\s+", "", page.onscreen_judgment)) > 34
        and any(
            term in page.onscreen_judgment
            for term in ("定位", "分工", "协同", "边界", "面向", "支撑", "服务")
        )
    ):
        issues.append(
            _issue(
                "ONSCREEN_JUDGMENT_LOCK_REVIEW",
                page,
                "A long relationship or positioning judgment is locked for verbatim display.",
                "Consider semantic_alignment so the judgment can be source-faithfully compressed without becoming a second title.",
                evidence=(page.onscreen_judgment,),
                severity="warning",
            )
        )
    visible = "\n".join((page.main_message, page.onscreen_judgment, page.onscreen_text))
    conditional_sources = tuple(
        ref for ref in page.source_refs
        if any(
            token in str(records_by_id.get(ref, {}).get("status") or "")
            for token in CONDITIONAL_STATUSES
        )
    )
    certainty_hits = tuple(term for term in VISIBLE_CERTAINTY_TERMS if term in visible)
    if conditional_sources and certainty_hits:
        high_risk = any(
            term in visible
            for term in ("投资", "预算", "周期", "立项", "最终范围", "技术路线")
        )
        issues.append(
            _issue(
                "FACT_CERTAINTY_LOST",
                page,
                "Visible page claims upgrade conditional or proposed evidence into a settled fact.",
                "Restore the source qualification in the visible judgment and on-screen copy before ImageGen compilation.",
                source_ids=conditional_sources,
                evidence=certainty_hits,
                severity="error" if high_risk else "warning",
            )
        )
    question = str(contract.get("business_question") or "")
    explicit_questions = len(re.findall(r"[？?]", question))
    dual_marker = any(
        marker in question
        for marker in ("两个问题", "两项独立问题", "分别回答")
    )
    if explicit_questions > 1 or dual_marker:
        issues.append(
            _issue(
                "PAGE_DUAL_MISSION",
                page,
                "The page contract explicitly asks the page to answer more than one independent question.",
                "Return to the Outline: establish one primary question and subordinate the other, or split the page contract.",
                evidence=(question,),
                severity="warning",
            )
        )
    return issues


def _presentation_issues(
    page: ScriptPage,
    contract: dict[str, object] | None = None,
    *,
    strict_detail_phrase_length: bool = False,
) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    full_text = _page_text(page)
    visual = page.visual_structure
    if page.page_type == "content":
        markdown_hits = _onscreen_markdown_hits(page.raw_onscreen_text)
        if markdown_hits:
            issues.append(
                _issue(
                    "ONSCREEN_MARKDOWN_LEAK",
                    page,
                    "Locked on-screen text contains Markdown authoring syntax.",
                    "Emit plain audience-facing text; keep headings, bold markers, and list syntax in the review renderer only.",
                    evidence=markdown_hits,
                )
            )
        onscreen_aside_hits = _boundary_aside_hits(page.onscreen_text)
        if onscreen_aside_hits:
            issues.append(
                _issue(
                    "ONSCREEN_BOUNDARY_ASIDE",
                    page,
                    "On-screen text contains status/boundary asides that interrupt the page mission.",
                    "Keep theme facts/structure on screen; park hedges in 边界 or ImageGen 禁止项.",
                    evidence=onscreen_aside_hits,
                )
            )
        relation_meta_hits = _onscreen_relation_meta_hits(page.onscreen_text)
        if relation_meta_hits:
            issues.append(
                _issue(
                    "ONSCREEN_RELATION_META_LABEL",
                    page,
                    "On-screen text contains backend relationship labels that must stay off-screen.",
                    "Move 业务含义 / 服务关系 / 闭环关系等标签句到完整文字稿或讲解提示；上屏只保留可直接阅读的业务模块文案。",
                    evidence=relation_meta_hits,
                )
            )
        backend_meta_hits = _onscreen_backend_meta_hits(page.onscreen_text)
        if backend_meta_hits:
            issues.append(
                _issue(
                    "ONSCREEN_BACKEND_META_LEAK",
                    page,
                    "On-screen text contains backend/process self-talk that must never reach the reader.",
                    "Remove authoring/verification process narration (待核验／仅后台／逻辑顺序／写作说明 etc.) from 上屏文字; keep it in backend fields or drop it entirely.",
                    evidence=backend_meta_hits,
                )
            )
        hierarchy_role_hits = _onscreen_parent_child_role_mismatches(page.onscreen_text)
        if hierarchy_role_hits:
            issues.append(
                _issue(
                    "ONSCREEN_FALSE_PARENT_CHILD_RELATION",
                    page,
                    "On-screen indentation creates a false parent-child relation across semantic dimensions.",
                    "Nest only true category members. Fold participating actors into the business item's description, or place them under a separate actor group when they must remain visible.",
                    evidence=hierarchy_role_hits,
                )
            )
        subordinate_hits = _onscreen_subordinate_fragments(page.onscreen_text)
        if subordinate_hits:
            issues.append(
                _issue(
                    "ONSCREEN_SUBORDINATE_FRAGMENT",
                    page,
                    "On-screen label detaches a subordinate phrase from the main clause it modifies.",
                    "Remove the authoring label and restore a complete natural sentence; keep 随着/通过/根据/围绕 together with its governing proposition.",
                    evidence=subordinate_hits,
                )
            )
        false_parallel_hits = _onscreen_false_parallel_semantics(page.onscreen_text)
        if false_parallel_hits:
            issues.append(
                _issue(
                    "ONSCREEN_FALSE_PARALLEL_SEMANTICS",
                    page,
                    "Indented siblings mix different argument functions and create a false peer relationship.",
                    "Make siblings answer one classification question, or rewrite attributes, changes, demands, gaps, and responses as an explicit chain or integrated proposition.",
                    evidence=false_parallel_hits,
                )
            )
        layout_meta_hits = _onscreen_layout_meta_hits(page.onscreen_text)
        if layout_meta_hits:
            issues.append(
                _issue(
                    "ONSCREEN_LAYOUT_META_LEAK",
                    page,
                    "On-screen text contains compositor/layout instructions rather than audience-facing copy.",
                    "Move matrix/lane/reading-order/layout instructions to 视觉结构（不上屏） or another backend field; keep only the business labels and short detail phrases in 上屏文字.",
                    evidence=layout_meta_hits,
                )
            )
        detail_phrase_overages = _onscreen_detail_phrase_overages(page.onscreen_text)
        if detail_phrase_overages:
            detail_severity = (
                "error"
                if strict_detail_phrase_length or any(
                    chars > ONSCREEN_DETAIL_PHRASE_ERROR_CHARS
                    for _line, chars in detail_phrase_overages
                )
                else "warning"
            )
            issues.append(
                _issue(
                    "ONSCREEN_DETAIL_PHRASE_TOO_LONG",
                    page,
                    "One or more on-screen detail lines are written as paragraphs instead of short phrases or short sentences.",
                    "If the detail is substantively long, add a source-specific business subheading and place the complete natural detail sentence beneath it. Keep a true summary-to-elaboration relation; never shorten by detaching 随着/通过/根据/围绕 from its main clause.",
                    evidence=tuple(
                        f"{chars}字：{line}"
                        for line, chars in detail_phrase_overages[:8]
                    ),
                    severity=detail_severity,
                )
            )
        mechanical_label_hits = _mechanical_onscreen_label_pattern_hits(page)
        flat_detail_hits = _onscreen_flat_long_labelled_detail_hits(page.onscreen_text)
        if flat_detail_hits:
            issues.append(
                _issue(
                    "ONSCREEN_BUSINESS_DETAIL_HIERARCHY_MISSING",
                    page,
                    "Several long on-screen details are flattened into peer labels without a business-title group.",
                    "Group related propositions under a source-specific business title, then retain each detail as a complete natural sentence. Do not fix this with generic labels such as 需求、措施 or 价值.",
                    evidence=flat_detail_hits,
                )
            )
        if mechanical_label_hits:
            issues.append(
                _issue(
                    "ONSCREEN_MECHANICAL_LABEL_TEMPLATE",
                    page,
                    "On-screen copy uses generic authoring labels instead of business-specific groups and detail labels.",
                    "Replace reusable labels with source-specific business objects, actions, conditions, and results. Keep only labels that tell the reader what this page is actually about.",
                    evidence=mechanical_label_hits,
                )
            )
        issues.extend(_onscreen_parallel_structure_issues(page))
        issues.extend(_onscreen_module_dimension_consistency_issues(page))
        issues.extend(_onscreen_redundant_restatement_issues(page))
        compound_heading_hits = _compound_module_heading_hits(
            _onscreen_heading_candidates(page)
        )
        if compound_heading_hits:
            issues.append(
                _issue(
                    "ONSCREEN_COMPOUND_GROUP_HEADING",
                    page,
                    "An on-screen group heading merges different semantic dimensions as peers.",
                    "Split the dimensions into separate modules, or rewrite the heading as a real parent-child relation whose parent explicitly owns both child dimensions; deleting '两个层面' alone is not a fix.",
                    evidence=compound_heading_hits,
                )
            )
        if visual.strip():
            has_semantic_structure = _has_any(visual, SEMANTIC_STRUCTURE_SIGNALS)
            style_only = _has_any(visual, STYLE_ONLY_TERMS) and not has_semantic_structure
            if style_only:
                issues.append(
                    _issue(
                        "VISUAL_STRUCTURE_STYLE_ONLY",
                        page,
                        "Visual structure only names style adjectives without a business relation.",
                        "Rewrite 视觉结构 with one primary business relation, semantic focus and text ownership; leave style and layout to Stage 02.",
                        evidence=tuple(
                            term for term in STYLE_ONLY_TERMS if term in visual
                        ),
                    )
                )
            elif not has_semantic_structure or _compact_len(visual) < 12:
                issues.append(
                    _issue(
                        "VISUAL_STRUCTURE_TOO_THIN",
                        page,
                        "Visual structure is too thin to hand off the page semantics.",
                        "State one primary business relation, its semantic focus, participating roles or objects, and text ownership without prescribing a layout.",
                        severity="warning",
                    )
                )
            surface = f"{page.onscreen_text}\n{visual}"
            for line in surface.splitlines():
                if not line.strip() or _has_any(line, NEGATION_TERMS):
                    continue
                hits = tuple(
                    term for term in ANTI_PATTERN_TERMS if term.lower() in line.lower()
                )
                if hits:
                    issues.append(
                        _issue(
                            "ONSCREEN_ANTI_PATTERN",
                            page,
                            "On-screen composition uses a high-risk generic layout pattern.",
                            "Replace card-wall / bento / neon dashboard cliches with a business-semantic structure.",
                            evidence=hits,
                            severity="warning",
                        )
                    )
                    break
        issues.extend(_visual_structure_judgment_issues(page))
    # "阅读路径" (reading path/order) is one of the five elements the
    # canonical 视觉结构 template explicitly asks every page to describe
    # (vendor/word-to-ppt-script/templates/10-script-final.md) — it is a
    # layout-reading-order note, not a business/process path claim, so its
    # mere presence must not trigger the same "path visual" requirement as
    # an actual "业务路径"/"贯穿主链" claim would.
    path_like = (
        bool(re.search(r"(?<!阅读)路径", visual))
        or "贯穿主链" in visual
        or "阶段推进" in visual
    )
    if path_like and not (
        any(signal in page.onscreen_text for signal in ORDER_SIGNALS)
        or NUMBERED_ORDER_SIGNAL_RE.search(page.onscreen_text)
    ):
        path_lines = tuple(
            line.strip()
            for line in visual.splitlines()
            if line.strip() and (
                (re.search(r"(?<!阅读)路径", line))
                or "贯穿主链" in line
                or "阶段推进" in line
            )
        )
        issues.append(
            _issue(
                "PATH_ORDER_SIGNAL_MISSING",
                page,
                "Path visual lacks an on-screen order signal.",
                f"Add one of {ORDER_SIGNALS} (or a numbered '01｜…' line) to 上屏文字, "
                "placed on the modules that realize the path line quoted in evidence.",
                evidence=path_lines,
            )
        )
    loop_like = "闭环" in visual or "闭环回流" in visual
    if loop_like and not any(
        signal in full_text for signal in LOOP_SIGNALS
    ):
        issues.append(
            _issue(
                "LOOP_RETURN_SIGNAL_MISSING",
                page,
                "Loop visual lacks an on-screen return or feedback relation.",
                "Name the feedback, review, or correction link on screen.",
            )
        )
    matrix_like = "矩阵" in visual or "矩阵筛选" in visual
    if matrix_like and not any(
        signal in page.onscreen_text for signal in MATRIX_SIGNALS
    ):
        issues.append(
            _issue(
                "MATRIX_AXES_MISSING",
                page,
                "Matrix visual lacks identifiable rows and columns.",
                "Provide the row objects and column dimensions in the on-screen structure.",
            )
        )
    layer_like = (
        "分层" in visual or "架构" in visual or "分层剖面" in visual
    )
    if layer_like and not any(
        signal in full_text for signal in LAYER_SIGNALS
    ):
        issues.append(
            _issue(
                "LAYER_HIERARCHY_MISSING",
                page,
                "Layered visual lacks an explicit hierarchy relation.",
                "Name the layers, support relation, or top-to-bottom reading order.",
            )
        )
    architecture_page = (
        layer_like
        or page.visual_intent_type.strip() in LAYER_LIKE_INTENT_TYPES
        or any(marker in page.title for marker in ("架构", "分层"))
    )
    count = _declared_count(
        page.onscreen_text,
        architecture_page=architecture_page,
    )
    if count is None:
        count = _declared_count(
            page.main_message,
            architecture_page=architecture_page,
        )
        approved_core = str(
            (contract or {}).get("core_message")
            or (contract or {}).get("main_message")
            or ""
        ).strip()
        # A number in the approved semantic judgment may describe an internal
        # business construct rather than the count of peer on-screen groups.
        # Only compare it with module count when the script introduced that
        # count itself; explicit counts in the on-screen layer remain strict.
        if approved_core and page.main_message.strip() == approved_core:
            count = None
    if (
        count is not None
        and page.top_level_module_titles
        and len(page.top_level_module_titles) != count
    ):
        issues.append(
            _issue(
                "DECLARED_COUNT_MISMATCH",
                page,
                (
                    f"Declared count {count} does not match "
                    f"{len(page.top_level_module_titles)} on-screen modules."
                ),
                "Align the declared count and the visible module structure.",
                evidence=(str(count), str(len(page.top_level_module_titles))),
            )
        )
    intent = page.visual_intent_type.strip()
    if page.page_type == "content" and page.top_level_module_titles:
        path_like = intent in PATH_LIKE_INTENT_TYPES or any(
            marker in visual
            for marker in ("贯穿主链", "阶段推进", "路径", "闭环", "回流")
        )
        layer_like_intent = intent in LAYER_LIKE_INTENT_TYPES or any(
            marker in visual for marker in ("分层剖面", "分层", "横向治理")
        )
        has_order = any(signal in page.onscreen_text for signal in ORDER_SIGNALS) or bool(
            NUMBERED_ORDER_SIGNAL_RE.search(page.onscreen_text)
        )
        has_layer = any(signal in page.onscreen_text for signal in LAYER_SIGNALS) or bool(
            re.search(r"(?m)^\s*\*\*\d{2}｜", page.onscreen_text)
        )
        if path_like and len(page.top_level_module_titles) >= 2 and not has_order:
            issues.append(
                _issue(
                    "ONSCREEN_RELATION_ISOMORPHISM",
                    page,
                    "Path-like page relation is not readable from on-screen module order.",
                    "Number modules (01｜…), add →/随之 signals, or change visual_intent_type.",
                    evidence=(intent or visual[:40], *page.top_level_module_titles[:4]),
                    severity="warning",
                )
            )
        if layer_like_intent and len(page.top_level_module_titles) >= 2 and not has_layer:
            issues.append(
                _issue(
                    "ONSCREEN_RELATION_ISOMORPHISM",
                    page,
                    "Layered page relation is not readable from on-screen hierarchy cues.",
                    "Keep numbered layer modules or explicit 层/支撑 signals aligned with 视觉结构.",
                    evidence=(intent or visual[:40], *page.top_level_module_titles[:4]),
                    severity="warning",
                )
            )
    visible_chars = len(re.sub(r"\s+", "", page.onscreen_text))
    if (
        page.page_type == "content"
        and (visible_chars < 30 or len(page.module_titles) < 2)
    ):
        issues.append(
            _issue(
                "CONTENT_PAGE_TOO_SPARSE",
                page,
                "Content page lacks enough evidence-bearing on-screen structure.",
                "Add source-supported modules or merge this page with the adjacent business question.",
                evidence=(
                    f"chars={visible_chars}",
                    f"modules={len(page.module_titles)}",
                ),
            )
        )
    if (
        page.page_type == "content"
        and len(page.top_level_module_titles) > MODULE_CEILING
        and not (
            any(signal in page.onscreen_text for signal in ORDER_SIGNALS)
            or NUMBERED_ORDER_SIGNAL_RE.search(page.onscreen_text)
        )
    ):
        issues.append(
            _issue(
                "MODULE_HIERARCHY_MISSING",
                page,
                "More than five modules are presented without grouping or hierarchy.",
                "Nest closely related items under fewer top-level modules (indented "
                "child bullets don't count toward the ceiling), or add explicit order "
                "signals (①②③, →) if this is genuinely a sequential list.",
            )
        )
    visible_lines = _onscreen_content_lines(page.onscreen_text)
    long_lines = tuple(
        line for line in visible_lines
        if len(re.sub(r"[^\w\u4e00-\u9fff]", "", line)) > 48
    )
    if long_lines:
        issues.append(
            _issue(
                "ONSCREEN_LINE_TOO_LONG",
                page,
                "One or more on-screen lines are too long for a stable visual hierarchy.",
                "Shorten the visible sentence while preserving the evidence needed for this page's declared subject.",
                evidence=long_lines[:3],
                severity="warning",
            )
        )
    target = onscreen_effective_char_target(page)
    if visible_chars > max(320, int(target * 1.35)):
        issues.append(
            _issue(
                "ONSCREEN_TEXT_OVERLOADED",
                page,
                "The visible text substantially exceeds the page's effective reading target.",
                "Compress repeated explanation or move supporting detail to narration; preserve the locked conclusion and evidence.",
                evidence=(f"chars={visible_chars}", f"target={target}"),
                severity="warning",
            )
        )
    numbered_nodes = len(
        re.findall(r"(?m)^\s*(?:[-*]\s*)?(?:[①②③④⑤⑥⑦⑧⑨⑩]|\d+[.、])", page.onscreen_text)
    )
    visible_nodes = max(len(page.top_level_module_titles), numbered_nodes)
    if visible_nodes > MODULE_CEILING:
        issues.append(
            _issue(
                "VISIBLE_NODE_OVERLOAD",
                page,
                "The number of visible primary nodes exceeds the configured page ceiling.",
                "Nest closely related items under fewer top-level modules (indented "
                "child bullets don't count toward the ceiling), or split genuinely "
                "independent conclusions into separate pages. Numbering alone does not "
                "reduce the number of primary nodes.",
                evidence=(f"nodes={visible_nodes}",),
                severity="error" if visible_nodes >= 8 else "warning",
            )
        )
    if page.page_type == "content":
        decision = resolve_onscreen_expression(
            page,
            page_mission=str((contract or {}).get("page_mission") or ""),
            business_relationships=page.content_relations,
            topic_category=str((contract or {}).get("topic_category") or ""),
        )
        for finding in audit_expression_balance(page, decision):
            issues.append(
                _issue(
                    finding.code,
                    page,
                    finding.message,
                    finding.action,
                    evidence=finding.evidence,
                    severity=(
                        finding.severity
                        if decision.source == "explicit"
                        else "warning"
                    ),
                )
            )
    contrast_hits = _prohibited_contrast_hits(
        "\n".join((page.onscreen_judgment, page.onscreen_text))
    )
    if contrast_hits:
        issues.append(
            _issue(
                "ONSCREEN_CONTRASTIVE_TEMPLATE",
                page,
                "Visible copy uses a contrastive or debate-style template.",
                "Rewrite as a definition, condition, capability, or directional judgment.",
                evidence=contrast_hits,
            )
        )
    return issues


def _visual_structure_judgment_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    """Catch visual-structure templates that contradict the page judgment."""

    issues: list[ScriptQualityIssue] = []
    visual = page.visual_structure.strip()
    if page.page_type != "content" or not visual:
        return issues
    visible_result_labels = tuple(
        match.group(1).strip()
        for match in re.finditer(
            r"(?:单独收束|结果区呈现|结论区呈现).{0,12}[“\"]([^”\"]+)[”\"]",
            visual,
        )
        if match.group(1).strip()
    )
    compact_onscreen = re.sub(r"\s+", "", page.onscreen_text)
    unlocked_results = tuple(
        label
        for label in visible_result_labels
        if re.sub(r"\s+", "", label) not in compact_onscreen
    )
    if unlocked_results:
        issues.append(
            _issue(
                "VISUAL_STRUCTURE_UNLOCKED_VISIBLE_TEXT",
                page,
                "Visual structure requests visible result text absent from locked on-screen text.",
                "Add the result once to locked on-screen text, or remove the instruction to render it.",
                evidence=unlocked_results,
            )
        )
    layout_recipe_hits = _visual_structure_layout_recipe_hits(visual)
    if layout_recipe_hits:
        issues.append(
            _issue(
                "VISUAL_STRUCTURE_LAYOUT_RECIPE",
                page,
                "Stage 01 visual structure contains a fixed page-layout recipe.",
                "Keep only the approved business relation, semantic focus, direction and text ownership; leave rows, columns, lanes, positions, containers and carrier selection to the Stage 02 visual-structure designer.",
                evidence=layout_recipe_hits[:8],
            )
        )
    multiple_primary = VISUAL_STRUCTURE_MULTIPLE_PRIMARY_RE.search(visual)
    if multiple_primary:
        issues.append(
            _issue(
                "VISUAL_STRUCTURE_MULTIPLE_PRIMARY_NARRATIVES",
                page,
                "Visual structure introduces another independent process, result chain or summary structure.",
                "Keep one primary business relation and make every secondary relation subordinate to it; do not add a second narrative in the visual handoff.",
                evidence=(multiple_primary.group(0).strip(),),
            )
        )
    corpus = _page_relation_corpus(page)
    nodes = _visual_structure_chain_nodes(visual)

    # 1) Cross-cutting roles peer-staged on → / 、 lists.
    peer_hits: list[str] = []
    for node in nodes:
        bare = _visual_module_label(node)
        patterns = (
            # 「质量与生命周期贯穿主链 / 横向治理贯穿每一层」
            rf"{re.escape(bare)}[^。；;\n]{{0,12}}贯穿",
            rf"{re.escape(bare)}[^。；;\n]{{0,8}}横切",
            rf"横切[^。；;\n]{{0,12}}{re.escape(bare)}",
            # 「贯穿每层的横向治理」— do not use「贯穿主链——模块」structure lead
            rf"贯穿(?!主链)[^。；;\n]{{0,12}}{re.escape(bare)}",
            rf"横向[^。；;\n]{{0,6}}{re.escape(bare)}",
        )
        marked = any(re.search(pattern, corpus) for pattern in patterns)
        # Explicit crosscut clause while also sitting on the main arrow list.
        if re.search(
            rf"[；;][^；;]*{re.escape(bare)}[^；;]*贯穿",
            visual,
        ):
            marked = True
        if marked and (
            "→" in visual.split("；", 1)[0].split(";", 1)[0]
            or visual.startswith("分层剖面")
            or visual.startswith("贯穿主链")
            or visual.startswith("阶段推进")
            or visual.startswith("闭环回流")
        ):
            peer_hits.append(bare)
    if peer_hits:
        issues.append(
            _issue(
                "VISUAL_STRUCTURE_CROSSCUT_AS_PEER",
                page,
                "Visual structure peer-stages a cross-cutting role on the main chain.",
                "Keep the main chain as transformation stages only; write cross-cuts as "
                "「横切：…贯穿主链」instead of another → node or stacked layer.",
                evidence=tuple(dict.fromkeys(peer_hits)),
                severity="warning",
            )
        )

    # 2) Swimlanes peer-stage mechanisms with business chains.
    if "主体泳道" in visual:
        mechanism_hits = tuple(dict.fromkeys(MECHANISM_LANE_LABEL_RE.findall(visual)))
        business_hits = tuple(dict.fromkeys(BUSINESS_LANE_LABEL_RE.findall(visual)))
        if mechanism_hits and business_hits:
            issues.append(
                _issue(
                    "VISUAL_STRUCTURE_MECHANISM_AS_LANE",
                    page,
                    "Swimlane structure peers mechanism modules with business chains.",
                    "Keep the business chains as the primary relation and bind 隔离/降级 as subordinate controls without prescribing lanes.",
                    evidence=business_hits + mechanism_hits,
                    severity="warning",
                )
            )

    return issues

from __future__ import annotations

import re

from .common import _compact_len, normalized_tokens, text_similarity
from .models import ScriptPage, ScriptQualityIssue, _issue
from .onscreen import (
    ONSCREEN_SEMANTIC_COVERAGE_ERROR_FLOOR,
    ONSCREEN_SEMANTIC_COVERAGE_MIN,
    ONSCREEN_SOURCE_ERASURE_PHRASES,
    ONSCREEN_SOURCE_SPECIFICITY_ERROR_FLOOR,
    _constraint_is_declared_subject,
    _generic_onscreen_relation_hits,
    _is_structured_compact_onscreen_layer,
    _mechanical_evidence_bullets,
    _module_heading_colon_hits,
    _nontable_compact_len,
    _onscreen_detail_terminal_punctuation_hits,
    _unlabeled_onscreen_bullets,
    meaningful_char_count,
    onscreen_effective_char_target,
    onscreen_semantic_coverage,
    onscreen_story_roles,
    parse_selection_notes,
    selection_notes_are_structured,
    structured_layer_char_target,
)
from .parsing import _source_refs

SPEAKER_SLIDE_META_RE = re.compile(
    r"(这一页|下一页|上一页|本页我们|本页先|本页把|本页只|看这一页|从这一页)"
)

SPEAKER_HOST_META_RE = re.compile(
    r"(各位同事|先把.{0,18}说清楚|先说明|先谈|先讲规则|"
    r"综合起来|接下来看|到这里收一下|全篇收在|请.{0,12}听|请先记住)"
)

SPEAKER_PRESENTER_CUE_RE = re.compile(
    r"(随后分别(?:说明|介绍|展开)|汇报时|讲解顺序|按.{0,18}(?:调整|安排).{0,12}(?:顺序|讲解|汇报))"
)

SPEAKER_PLACEHOLDER_RE = re.compile(
    r"(原文围绕.{0,36}(?:展开|说明)|"
    r"各项内容共同回答.{0,18}(?:问题|任务)|"
    r"关键对象、作用机制和条件边界)"
)

DEFENSIVE_BOUNDARY_COACHING_RE = re.compile(
    r"(反复区分|避免(?:听众)?.{0,12}(?:误解|听成|当成)|"
    r"不要.{0,12}讲成|不是.{0,8}承诺|不构成.{0,8}承诺|"
    r"防止.{0,12}误解|以免.{0,12}误解)"
)

SPEAKER_NOTES_MIN_CHARS = 60

NEGATION_TERMS = ("不得", "禁止", "避免", "不使用", "不采用", "不做")

PROSE_MIN_CHARS = 80

_ANALYTICAL_VOICE_PATTERNS: tuple[str, ...] = (
    "首先需要确认",
    "而不是直接讨论",
    "而不是直接排",
    "从现有材料看",
    "进入本页",
    "进入建设内容",
    "进入实施路径",
    "需要进一步说明",
    "本页只确认",
    "本页只说明",
    "本页只定位",
    "本页只陈述",
    "本页不评价",
    "本页不给出",
    "本页回答",
    "本页因此",
    "本页把",
    "本页强调",
    "本页将",
    "据此，本页",
)

_PROHIBITED_CONTRAST_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?:并)?不是[^。！？；]{0,100}?(?:，|,)?而(?:是|非|为|在于|应|要|需)"),
    re.compile(r"(?:并)?不在于[^。！？；]{0,100}?(?:，|,)?而在于"),
    re.compile(
        r"(?<![^\s，；。！？：])(?:并)?非"
        r"(?!结构化|公开|必要|接触式|线性|关系型|实时|敏感|现场|标准)"
        r"[^。！？；]{1,100}?(?:，|,)?而(?:是|非|为|在于|应|要|需)"
    ),
    re.compile(r"而(?:非|不是)[^。！？；]{0,100}"),
    re.compile(r"(?:不以|不应|不宜|不要|不再|不只|不止于)[^。！？；]{1,100}?(?:，|,)?而(?:是|非|为|在于|应|要|需)"),
    re.compile(r"与其[^。！？；]{1,100}?不如"),
    re.compile(r"宁可[^。！？；]{1,100}?也不"),
    re.compile(r"既非[^。！？；]{1,100}?(?:也|亦)非"),
)

_PROHIBITED_COLLOQUIAL_PATTERNS: tuple[str, ...] = (
    "大家",
    "咱们",
    "我们先",
    "我们再",
    "我们可以",
    "接下来",
    "先说",
    "再说",
    "最后说",
    "简单来说",
    "说白了",
    "也就是说",
    "就是说",
    "看一下",
    "看一看",
    "这里说的是",
    "这部分要",
    "凭什么",
)

_BOUNDARY_ASIDE_PATTERNS: tuple[str, ...] = (
    "尚非既成事实",
    "不等于",
    "并不等于",
    "并不等同于",
    "不构成已",
    "尚不构成",
    "不代替",
    "不升格",
    "讨论稿不",
    "不能直接作",
    "不能直接转",
    "不能直接写",
    "不能写死",
    "不能提前写",
    "不锁定完整",
    "当前待测算",
    "方法≠",
    "≠生产能力",
    "≠工程承诺",
    "拟建议",
    "尚属建议",
    "建议性安排",
    "表述为拟建议",
    "属拟建议",
    "仅为建议",
)

_NEGATIVE_FOREGROUND_TERMS: tuple[str, ...] = (
    "边界",
    "不足",
    "短板",
    "缺口",
    "断点",
    "瓶颈",
    "痛点",
    "差距",
    "局限",
    "限制",
    "风险",
    "挑战",
    "障碍",
    "隐患",
    "薄弱",
    "缺乏",
    "滞后",
    "失效",
    "故障",
    "异常",
    "冲突",
    "矛盾",
    "不确定",
    "泄露",
    "攻击",
    "威胁",
    "不成熟",
    "不完善",
    "不统一",
    "不清晰",
    "不达标",
    "失衡",
    "不等于",
    "不构成",
    "尚未",
    "未形成",
    "不具备",
    "待定",
    "暂停",
    "停止",
    "终止",
)

_DIRECT_BOUNDARY_ARGUMENT_ROLES = {
    "boundary",
    "admission",
    "security",
    "governance",
    "quality",
    "compliance",
    "risk",
    "assurance",
    # "foundation" pages implement the skill's own documented "需求—供给缺口—
    # 必要性" argument prototype (see argument-and-visual-grammars.md): they
    # must foreground a genuine supply/demand gap to justify why the deck's
    # whole proposal exists. Without this, no wording can pass both this rule
    # and the argument-chain requirement to state the gap.
    "foundation",
}

_DIRECT_BOUNDARY_TOPIC_TERMS = (
    "边界",
    "准入",
    "授权",
    "权属",
    "安全",
    "质量",
    "合规",
    "风险",
    "退出",
    "背景",
    "必要性",
)

_CONDITIONAL_RISK_PHRASES: tuple[str, ...] = (
    "数据风险",
    "风险控制",
    "风险管理",
    "风险评估",
    "风险防控",
)

FORMULAIC_TRANSITION_TERMS = (
    "因此", "由此", "进而", "综上", "综上所述", "基于此", "鉴于此", "所以",
)

def _analytical_voice_hits(prose: str) -> tuple[str, ...]:
    hits = [pattern for pattern in _ANALYTICAL_VOICE_PATTERNS if pattern in prose]
    return tuple(hits)

def _prohibited_contrast_hits(text: str) -> tuple[str, ...]:
    normalized = re.sub(r"\s+", "", text)
    return tuple(
        dict.fromkeys(
            match.group(0)
            for pattern in _PROHIBITED_CONTRAST_PATTERNS
            for match in pattern.finditer(normalized)
        )
    )

def _prohibited_contrast_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    """Reject negative-contrast rhetoric in every authored script field.

    The check stays field-scoped: normalizing whitespace within a field closes
    line-break evasion, while never concatenating neighboring fields avoids a
    false match that crosses two unrelated pieces of page metadata.
    """

    authored_fields = (
        ("页面标题", page.title),
        ("副标题", page.subtitle),
        ("主判断", page.main_message),
        ("完整文字稿", page.full_prose),
        ("文字稿取舍说明", page.selection_notes),
        ("证据映射", page.evidence_map),
        ("上屏结论", page.onscreen_judgment),
        ("上屏文字", page.onscreen_text),
        ("视觉结构", page.visual_structure),
        ("视觉证明", page.visual_proof),
        ("边界", page.boundary),
        ("讲解提示", page.coaching_tip),
        ("演讲者备注", page.speaker_notes),
    )
    evidence = tuple(
        f"{field}：{hit}"
        for field, text in authored_fields
        if text
        for hit in _prohibited_contrast_hits(text)
    )
    if not evidence:
        return []
    if all(
        item.rsplit("：", 1)[-1].strip(" 、") == "边界"
        for item in evidence
        if "：" in item
    ):
        return []
    return [
        _issue(
            "PROHIBITED_NEGATIVE_CONTRAST",
            page,
            "Authored script uses prohibited negative-contrast rhetoric.",
            "Rewrite as a direct positive statement of the subject, action, condition, and result; do not frame the claim through a rejected alternative.",
            evidence=evidence,
        )
    ]

def _is_direct_boundary_clarification(
    page: ScriptPage,
    contract: dict[str, object],
) -> bool:
    """Return whether the approved page itself is a boundary-control topic."""

    role = str(contract.get("argument_role") or "").strip()
    if role not in _DIRECT_BOUNDARY_ARGUMENT_ROLES:
        return False
    approved_theme = "\n".join(
        str(contract.get(field) or "")
        for field in ("title", "topic_category", "page_mission", "audience_question")
    )
    return any(term in approved_theme for term in _DIRECT_BOUNDARY_TOPIC_TERMS)

def _negative_foreground_terms(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for term in _NEGATIVE_FOREGROUND_TERMS:
        if term not in text:
            continue
        if term == "风险":
            residual = text
            for phrase in _CONDITIONAL_RISK_PHRASES:
                residual = residual.replace(phrase, "")
            if term not in residual:
                continue
        hits.append(term)
    return tuple(hits)

def _leading_negative_foreground_terms(text: str) -> tuple[str, ...]:
    """Apply foreground screening to the claim lead, not trailing conditions."""

    lead = re.sub(r"\s+", "", text)[:28]
    return _negative_foreground_terms(lead)

def _opening_negative_foreground_terms(text: str) -> tuple[str, ...]:
    """Find negative framing in a page's opening claim, not later caveats."""

    opening = re.sub(r"\s+", "", text)[:72]
    return _negative_foreground_terms(opening)

def _selected_problem_slots(contract: dict[str, object]) -> set[str]:
    """Return explicit, non-implicit problem slots from an author model choice."""

    selection = contract.get("expression_model_selection")
    mappings = selection.get("source_mapping") if isinstance(selection, dict) else []
    if not isinstance(mappings, list):
        return set()
    return {"complication", "problem", "gap"} & {
        str(item.get("slot") or "")
        for item in mappings
        if isinstance(item, dict) and item.get("implicit") is not True
    }

def _negative_foreground_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Keep non-boundary pages from foregrounding limitations or negatives."""

    if _is_direct_boundary_clarification(page, contract):
        return []

    evidence: list[str] = []
    for field, text in (("页面标题", page.title), ("副标题", page.subtitle)):
        hits = _negative_foreground_terms(text)
        if hits:
            evidence.append(f"{field}：{'、'.join(hits)}")
    for field, text in (("主判断", page.main_message), ("上屏结论", page.onscreen_judgment)):
        hits = _leading_negative_foreground_terms(text)
        if hits:
            evidence.append(f"{field}：{'、'.join(hits)}")
    selected_problem_slots = _selected_problem_slots(contract)
    for heading in page.top_level_module_titles:
        hits = _negative_foreground_terms(heading)
        if hits and not selected_problem_slots:
            evidence.append(f"上屏顶层模块“{heading}”：{'、'.join(hits)}")
    for field, text in (("完整文字稿开头", page.full_prose), ("演讲者备注开头", page.speaker_notes)):
        hits = _opening_negative_foreground_terms(text)
        if hits:
            evidence.append(f"{field}：{'、'.join(hits)}")
    visual_focus = re.findall(
        r"(?:重点呈现|重点|核心|主要|突出|强调|聚焦|围绕)[^。！？；\n]{0,48}",
        page.visual_structure,
    )
    for phrase in visual_focus:
        hits = _negative_foreground_terms(phrase)
        if hits:
            evidence.append(f"视觉结构：{phrase}（{'、'.join(hits)}）")
    if not evidence:
        return []
    return [
        _issue(
            "NEGATIVE_FOREGROUND_OUTSIDE_BOUNDARY_TOPIC",
            page,
            "A non-boundary page foregrounds boundary, insufficiency, or other negative information.",
            "Reframe the title and leading script as a positive subject–action–value/result statement. Preserve necessary controls only as subordinate conditions, not as the page's primary narrative.",
            evidence=tuple(evidence),
        )
    ]

def _prohibited_colloquial_hits(text: str) -> tuple[str, ...]:
    return tuple(pattern for pattern in _PROHIBITED_COLLOQUIAL_PATTERNS if pattern in text)

def _speaker_placeholder_hits(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(match.group(0) for match in SPEAKER_PLACEHOLDER_RE.finditer(text))
    )

def _boundary_aside_hits(text: str) -> tuple[str, ...]:
    hits = [pattern for pattern in _BOUNDARY_ASIDE_PATTERNS if pattern in text]
    return tuple(hits)

def _formulaic_transition_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    """Reject speech-like filler transitions from all authored content layers."""

    if page.page_type != "content":
        return []
    issues: list[ScriptQualityIssue] = []
    for field_name, text in (
        ("完整文字稿", page.full_prose),
        ("上屏文字", page.onscreen_text),
        ("演讲者备注", page.speaker_notes),
    ):
        hits = tuple(term for term in FORMULAIC_TRANSITION_TERMS if term in text)
        if hits:
            issues.append(
                _issue(
                    "FORMULAIC_TRANSITION_PHRASE",
                    page,
                    f"{field_name} uses formulaic discourse transitions instead of a concrete business relation.",
                    "Remove 因此/由此/进而/综上/所以-style filler and let the subject, action, constraint, or result carry the transition.",
                    evidence=(field_name, *hits),
                )
            )
    return issues

def _prose_issues(
    page: ScriptPage,
    *,
    expected_source_refs: tuple[str, ...] = (),
    independent_reading_required: bool = False,
    strict_reading_density: bool = False,
    contract: dict[str, object] | None = None,
) -> list[ScriptQualityIssue]:
    if page.page_type != "content":
        return []
    issues: list[ScriptQualityIssue] = []
    prose = page.full_prose
    prose_chars = _compact_len(prose)
    onscreen_chars = _nontable_compact_len(page.onscreen_text)
    if not prose:
        issues.append(
            _issue(
                "CONTENT_PROSE_MISSING",
                page,
                "Content page must include a full prose draft before on-screen text.",
                "Assemble the page evidence pack and write a short-article narrative first.",
            )
        )
        return issues
    semantic_paragraphs = tuple(
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", prose)
        if paragraph.strip()
    )
    if prose_chars >= 260 and len(semantic_paragraphs) < 2:
        issues.append(
            _issue(
                "CONTENT_PROSE_SEMANTIC_PARAGRAPHS_MISSING",
                page,
                "Long full prose is collapsed into one block instead of semantic paragraphs.",
                "Split 完整文字稿 at argument boundaries such as background, concrete demand, present gap, and page conclusion; do not split mechanically by sentence count.",
                evidence=(f"chars={prose_chars}", f"paragraphs={len(semantic_paragraphs)}"),
            )
        )
    order = list(page.field_order)
    if "完整文字稿" in order and "上屏文字" in order:
        if order.index("完整文字稿") > order.index("上屏文字"):
            issues.append(
                _issue(
                    "CONTENT_PROSE_AFTER_ONSCREEN",
                    page,
                    "Full prose must appear before on-screen text in the page script.",
                    "Move 完整文字稿 above 上屏文字 and rewrite the on-screen layer from the prose.",
                )
            )
    min_chars = max(PROSE_MIN_CHARS, _compact_len(page.main_message) * 2)
    if prose_chars < min_chars:
        issues.append(
            _issue(
                "CONTENT_PROSE_TOO_THIN",
                page,
                "Full prose is too thin to cover the page topic as a short article.",
                "Expand toward the source's main content for this page topic; do not stop at on-screen granularity.",
                evidence=(f"chars={prose_chars}", f"min={min_chars}"),
            )
        )
    if page.onscreen_text and text_similarity(prose, page.onscreen_text) >= 0.90:
        issues.append(
            _issue(
                "CONTENT_PROSE_EQUALS_ONSCREEN",
                page,
                "Full prose is nearly identical to the on-screen bullet layer.",
                "Rewrite as continuous business narrative covering the source topic body; keep bullets only in 上屏文字.",
                evidence=(f"similarity={text_similarity(prose, page.onscreen_text):.3f}",),
            )
        )
    if (
        page.onscreen_text
        and onscreen_chars >= 40
        and prose_chars < int(onscreen_chars * 1.5)
    ):
        # A short source paragraph can be fully preserved while the required
        # independent-reading layer is necessarily close in length.  Treat
        # that ratio as advisory when the page cites every source assigned by
        # the Outline; source-coverage and near-equality checks remain hard
        # gates, so this does not permit a second unsupported interpretation.
        expected = set(expected_source_refs)
        source_complete = bool(expected) and expected.issubset(set(page.source_refs))
        issues.append(
            _issue(
                "CONTENT_PROSE_ONSCREEN_GRANULARITY",
                page,
                "Full prose is not substantially richer than the on-screen layer.",
                "Raise prose to short-article completeness aligned with the source topic body.",
                evidence=(
                    f"prose_chars={prose_chars}",
                    f"onscreen_chars={onscreen_chars}",
                ),
                severity="warning" if source_complete else "error",
            )
        )
    if page.onscreen_text and independent_reading_required:
        visible_story_chars = meaningful_char_count(
            page.onscreen_judgment + page.onscreen_text
        )
        coverage = onscreen_semantic_coverage(page)
        # Formal slides may be independently readable through an explicit
        # information architecture rather than paragraph-length copy.  Accept
        # a compact layer only when it has a real 1-5 module skeleton (one is
        # allowed only as an umbrella with several true children), enough
        # supporting items, meaningful total copy, and no overlong detail.
        # This deliberately rejects the former "four thin lines" loophole.
        structured_compact_layer = _is_structured_compact_onscreen_layer(
            page,
            visible_story_chars=visible_story_chars,
        )
        min_story_chars = (
            structured_layer_char_target(page)
            if structured_compact_layer
            else onscreen_effective_char_target(page)
        )
        logic = (contract or {}).get("page_logic_contract")
        expression = logic.get("onscreen_expression") if isinstance(logic, dict) else None
        expression_driven_layer = (
            isinstance(expression, dict)
            and bool(expression.get("nodes"))
            and bool(expression.get("reading_order"))
        )
        if expression_driven_layer:
            # An author-declared expression graph carries reading order,
            # source-bound object groups, and visible relationship labels.
            # Do not force it back into paragraph density merely to satisfy a
            # generic character target; page-logic validation still verifies
            # every declared text item and relation below.
            min_story_chars = min(min_story_chars, 180)
        source_erasure_hits = tuple(
            phrase
            for phrase in ONSCREEN_SOURCE_ERASURE_PHRASES
            if phrase in page.onscreen_text
        )
        if (
            strict_reading_density
            and structured_compact_layer
            and prose_chars >= PROSE_MIN_CHARS * 2
            and coverage < ONSCREEN_SOURCE_SPECIFICITY_ERROR_FLOOR
            and len(source_erasure_hits) >= 2
        ):
            issues.append(
                _issue(
                    "ONSCREEN_SOURCE_SPECIFICITY_LOW",
                    page,
                    "Compact on-screen copy replaces source-specific business content with generic concepts.",
                    (
                        "Keep the source's named business objects in module titles and retain its "
                        "concrete duties, processed objects, operating actions, participants, and "
                        "collaboration actions in child items. Split or add true source-supported "
                        "short items to stay within 30 characters; never replace distinctive "
                        "business content with generic concepts."
                    ),
                    evidence=(
                        f"coverage={coverage:.3f}",
                        f"floor={ONSCREEN_SOURCE_SPECIFICITY_ERROR_FLOOR:.3f}",
                        *source_erasure_hits,
                    ),
                )
            )
        if visible_story_chars < min_story_chars:
            issues.append(
                _issue(
                    "ONSCREEN_STORY_DENSITY_LOW",
                    page,
                    "On-screen text is too compressed to support independent reading.",
                    (
                        "Rewrite 上屏文字 as a high-information reading layer: retain "
                        "the page subject, source-supported facts, explicit relations, "
                        "and the page implication needed to understand it without "
                        "narration; do not add a formulaic conclusion when the source "
                        "does not provide one."
                    ),
                    evidence=(
                        f"visible_chars={visible_story_chars}",
                        f"min={min_story_chars}",
                    ),
                )
            )
        if (
            prose_chars >= PROSE_MIN_CHARS * 2
            and coverage < ONSCREEN_SEMANTIC_COVERAGE_ERROR_FLOOR
            and not structured_compact_layer
        ):
            issues.append(
                _issue(
                    "ONSCREEN_SEMANTIC_COVERAGE_LOW",
                    page,
                    "Too little of the full prose meaning survives in the on-screen layer.",
                    (
                        "Restore the essential facts, numbers, explanatory relations, "
                        "causal links, and page implication from 完整文字稿 via 必留上屏; "
                        "do not dump the full prose onto the slide."
                    ),
                    evidence=(
                        f"coverage={coverage:.3f}",
                        f"floor={ONSCREEN_SEMANTIC_COVERAGE_ERROR_FLOOR:.3f}",
                    ),
                )
            )
        elif (
            prose_chars >= PROSE_MIN_CHARS * 2
            and coverage < ONSCREEN_SEMANTIC_COVERAGE_MIN
            and not structured_compact_layer
        ):
            issues.append(
                _issue(
                    "ONSCREEN_SEMANTIC_COVERAGE_LOW",
                    page,
                    "On-screen semantic coverage is below the advisory band; prefer relation isomorphism and structured 取舍说明 over token stuffing.",
                    (
                        "Keep the page skeleton in 必留上屏; park mechanism detail in 仅讲解 "
                        "and Source IDs in 仅追溯."
                    ),
                    evidence=(
                        f"coverage={coverage:.3f}",
                        f"min={ONSCREEN_SEMANTIC_COVERAGE_MIN:.3f}",
                    ),
                    severity="warning",
                )
            )
        roles = onscreen_story_roles(page)
        missing_roles = tuple(
            role
            for role, present in roles.items()
            if not present
        )
        # High-density reading is mandatory for content pages, but a visible
        # conclusion remains optional.  Only evaluate the conclusion/evidence/
        # closure chain when the author actually declares an onscreen judgment.
        if page.onscreen_judgment and missing_roles:
            issues.append(
                _issue(
                    "ONSCREEN_STORY_NOT_CLOSED",
                    page,
                    "On-screen text does not form a closed readable argument.",
                    (
                        "Keep the visible conclusion, at least two evidence-bearing lines, "
                        "one explicit business relationship, and a readable closure."
                    ),
                    evidence=missing_roles,
                )
            )
    analytical_hits = _analytical_voice_hits(prose)
    if analytical_hits:
        issues.append(
            _issue(
                "CONTENT_PROSE_ANALYTICAL_VOICE",
                page,
                "Full prose uses analytical meta-narration instead of source-chapter voice.",
                "Rewrite as direct source-topic prose; move page-role asides into 文字稿取舍说明 or 边界.",
                evidence=analytical_hits,
            )
        )
    colloquial_hits = _prohibited_colloquial_hits(prose)
    if colloquial_hits:
        issues.append(
            _issue(
                "PROHIBITED_COLLOQUIAL_MANUSCRIPT",
                page,
                "Manuscript layer uses conversational wording; formal written-document expression is required.",
                "Rewrite as objective written prose: state the subject, relation, condition, and conclusion directly; remove reader-address and spoken transition markers.",
                evidence=colloquial_hits,
            )
        )
    unlabeled_bullets = _unlabeled_onscreen_bullets(page.onscreen_text)
    module_heading_colons = _module_heading_colon_hits(page.onscreen_text)
    if module_heading_colons:
        issues.append(
            _issue(
                "ONSCREEN_MODULE_HEADING_PUNCTUATION",
                page,
                "On-screen module headings must not use the same colon separator as detail lines.",
                "Replace the first module-heading colon with ｜; keep ： only in conclusion-first detail lines.",
                evidence=module_heading_colons,
            )
        )
    if unlabeled_bullets:
        issues.append(
            _issue(
                "ONSCREEN_BULLET_CONCLUSION_MISSING",
                page,
                "On-screen bullets lack conclusion-first labels.",
                "Prefix every parallel item with a concise conclusion label followed by a colon, then provide the supporting detail.",
                evidence=unlabeled_bullets,
            )
        )
    detail_terminal_punctuation = _onscreen_detail_terminal_punctuation_hits(page.onscreen_text)
    if detail_terminal_punctuation:
        issues.append(
            _issue(
                "ONSCREEN_DETAIL_TERMINAL_PUNCTUATION",
                page,
                "On-screen 标签：短语 detail lines must not end with sentence punctuation.",
                "Remove the final period, comma, dunhao, semicolon, colon, question mark, or exclamation mark; "
                "leave 独立边界句 and bare module headings untouched — their trailing 句号 (or its absence) is load-bearing for module parsing.",
                evidence=detail_terminal_punctuation,
            )
        )
    mechanical_evidence = _mechanical_evidence_bullets(page.onscreen_text)
    if mechanical_evidence:
        issues.append(
            _issue(
                "ONSCREEN_SOURCE_ATOMIZATION",
                page,
                "On-screen evidence was mechanically split into numbered source fragments.",
                (
                    "Return to 完整文字稿, select 2–5 complete business points, and "
                    "rewrite each point as a self-contained conclusion-first line; do not "
                    "enumerate punctuation fragments or Source Truth atoms."
                ),
                evidence=mechanical_evidence,
            )
        )
    generic_relations = _generic_onscreen_relation_hits(page.onscreen_text)
    if generic_relations:
        issues.append(
            _issue(
                "ONSCREEN_GENERIC_RELATION_PLACEHOLDER",
                page,
                "On-screen relationship text is a generic placeholder rather than a business relation.",
                (
                    "Name the actual relation carried by the page, such as parallel dimensions, "
                    "input-to-output transformation, layered support, sequence, control, or feedback."
                ),
                evidence=generic_relations,
            )
        )
    boundary_hits = _boundary_aside_hits(prose)
    if boundary_hits:
        issues.append(
            _issue(
                "CONTENT_BOUNDARY_ASIDE_OVERLOAD",
                page,
                "Full prose overuses status/boundary asides instead of arguing the proposed content.",
                "Keep affirmative planning prose; move “不等于/不构成/不代替…” hedges into 边界.",
                evidence=boundary_hits,
            )
        )
    if _compact_len(page.selection_notes) < 12:
        issues.append(
            _issue(
                "CONTENT_SELECTION_NOTES_MISSING",
                page,
                "Content page must state what was deliberately left out or deferred.",
                "Add 文字稿取舍说明 with 必留上屏 / 仅讲解 / 仅追溯.",
            )
        )
    elif not selection_notes_are_structured(page.selection_notes):
        issues.append(
            _issue(
                "CONTENT_SELECTION_NOTES_UNSTRUCTURED",
                page,
                "文字稿取舍说明 must use the three buckets 必留上屏 / 仅讲解 / 仅追溯.",
                (
                    "Rewrite as:\n"
                    "  - 必留上屏：…\n"
                    "  - 仅讲解：…\n"
                    "  - 仅追溯：S### …"
                ),
                severity="warning",
            )
        )
    else:
        parsed = parse_selection_notes(page.selection_notes)
        keep = parsed.get("必留上屏", "")
        compact_onscreen = re.sub(r"\s+", "", page.onscreen_text)
        module_hits = [
            title
            for title in page.module_titles
            if re.sub(r"\s+", "", title) in compact_onscreen
            and re.sub(r"\s+", "", title) in re.sub(r"\s+", "", keep)
        ]
        # The assembly pipeline may intentionally use a generic keep rule
        # ("页面结论、关键事实与模块标题") when module titles are already
        # locked in the adjacent 上屏文字 block. Treat that explicit contract
        # as valid instead of forcing every title to be duplicated in notes.
        # "主判断、关键构成要素和必要边界" is the same kind of declaration
        # under this project's own primary/supporting/boundary content-unit
        # vocabulary (see references/02-source-compilation.md) — it already
        # covers "whatever ended up locked into 上屏文字", the same as
        # "模块标题" does, just phrased in that vocabulary instead.
        generic_keep_rule = any(
            token in keep
            for token in (
                "模块标题",
                "上屏模块",
                "页面结论",
                "关键构成要素",
            )
        )
        if page.module_titles and not module_hits and not generic_keep_rule:
            # Require at least one module title echoed in 必留上屏 so the note
            # is not a free-form essay disconnected from the slide.
            issues.append(
                _issue(
                    "CONTENT_SELECTION_ONSCREEN_MISMATCH",
                    page,
                    "必留上屏 does not name any visible on-screen module.",
                    "List the kept module titles or key phrases that remain in 上屏文字.",
                    evidence=page.module_titles[:4],
                    severity="warning",
                )
            )
        traced = _source_refs(parsed.get("仅追溯", ""))
        if traced and page.evidence_map_refs:
            missing_trace = tuple(
                item for item in traced if item not in page.evidence_map_refs
            )
            if missing_trace:
                issues.append(
                    _issue(
                        "CONTENT_SELECTION_ONSCREEN_MISMATCH",
                        page,
                        "仅追溯 lists Source IDs that are absent from 证据映射.",
                        "Keep 仅追溯 IDs inside this page's evidence map.",
                        evidence=missing_trace,
                        severity="warning",
                    )
                )
    notes = page.speaker_notes.strip()
    if not notes:
        issues.append(
            _issue(
                "CONTENT_SPEAKER_NOTES_MISSING",
                page,
                "Content page must include 【演讲者备注】 for PPT speaker notes.",
                "Add a natural spoken narration block after 讲解提示, consumed by assembly.",
            )
        )
    else:
        if _compact_len(notes) < SPEAKER_NOTES_MIN_CHARS:
            issues.append(
                _issue(
                    "CONTENT_SPEAKER_NOTES_TOO_THIN",
                    page,
                    "Speaker notes are too thin to serve as deliverable narration.",
                    "Write about 1–2 minutes of natural speech covering the page thesis.",
                    evidence=(f"chars={_compact_len(notes)}",),
                )
            )
        note_paragraphs = tuple(
            part.strip() for part in re.split(r"\n\s*\n", notes) if part.strip()
        )
        if _compact_len(notes) > 120 and len(note_paragraphs) < 2:
            issues.append(
                _issue(
                    "SPEAKER_NOTES_UNSEGMENTED",
                    page,
                    "Long speaker notes must be divided into readable semantic paragraphs.",
                    "Use 2-4 paragraphs: judgment first, support or mechanism next, then implication or transition.",
                    evidence=(f"chars={_compact_len(notes)}",),
                )
            )
        incomplete_boundaries = tuple(
            paragraph[-12:]
            for paragraph in note_paragraphs[:-1]
            if not paragraph.endswith(("。", "！", "？"))
        )
        if incomplete_boundaries:
            issues.append(
                _issue(
                    "SPEAKER_NOTES_INCOMPLETE_PARAGRAPH_BOUNDARY",
                    page,
                    "Speaker-note paragraphs must end at complete sentences.",
                    "Move paragraph breaks to after a full stop, question mark, or exclamation mark; never break after a comma or semicolon.",
                    evidence=incomplete_boundaries,
                )
            )
        meta_hits = tuple(
            sorted({match.group(0) for match in SPEAKER_SLIDE_META_RE.finditer(notes)})
        )
        if meta_hits:
            issues.append(
                _issue(
                    "SPEAKER_NOTES_SLIDE_META",
                    page,
                    "Speaker notes use slide-meta coaching instead of natural speech.",
                    "Remove 这一页/下一页/本页我们 and speak the business content aloud.",
                    evidence=meta_hits,
                )
            )
        host_hits = tuple(
            sorted({match.group(0) for match in SPEAKER_HOST_META_RE.finditer(notes)})
        )
        if host_hits:
            issues.append(
                _issue(
                    "SPEAKER_NOTES_HOST_META",
                    page,
                    "Speaker notes use host-style framing instead of formal briefing narration.",
                    "Start with the judgment, then state its support and implication directly.",
                evidence=host_hits,
            )
        )
        presenter_cue_hits = tuple(
            sorted(
                {
                    match.group(0)
                    for match in SPEAKER_PRESENTER_CUE_RE.finditer(notes)
                }
            )
        )
        if presenter_cue_hits:
            issues.append(
                _issue(
                    "SPEAKER_NOTES_PRESENTER_CUE",
                    page,
                    "Speaker notes give presenter instructions instead of adding business narration.",
                    "Replace sequencing or delivery cues with the business meaning, mechanism, evidence, or implication the speaker should explain.",
                    evidence=presenter_cue_hits,
                )
            )
        placeholder_hits = _speaker_placeholder_hits(notes)
        if placeholder_hits:
            issues.append(
                _issue(
                    "SPEAKER_NOTES_PLACEHOLDER_PROSE",
                    page,
                    "Speaker notes repeat the page judgment and append generic placeholder prose.",
                    (
                        "Rewrite the notes as direct business narration derived from the full prose: "
                        "state the facts, relationships, and distinctions that the speaker will actually explain."
                    ),
                    evidence=placeholder_hits,
                )
            )
    return issues

def _narration_boundary_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    if page.page_type != "content":
        return []
    issues: list[ScriptQualityIssue] = []
    coaching_hits = tuple(
        sorted(
            {
                match.group(0)
                for match in DEFENSIVE_BOUNDARY_COACHING_RE.finditer(
                    page.coaching_tip
                )
            }
        )
    )
    note_hits = tuple(
        sorted(
            {
                match.group(0)
                for match in DEFENSIVE_BOUNDARY_COACHING_RE.finditer(
                    page.speaker_notes
                )
            }
        )
    )
    if coaching_hits or note_hits:
        issues.append(
            _issue(
                "NARRATION_BOUNDARY_COACHING",
                page,
                "Coaching tips and speaker notes must not contain defensive "
                "boundary coaching.",
                "State the page's business judgment and support directly; keep "
                "misunderstanding prevention and commitment-state reminders in "
                "internal controls only.",
                evidence=coaching_hits + note_hits,
            )
        )
    constraint_is_subject = _constraint_is_declared_subject(page, contract)
    if (
        not constraint_is_subject
        and page.boundary
        and page.speaker_notes
        and text_similarity(page.boundary, page.speaker_notes) >= 0.12
    ):
        issues.append(
            _issue(
                "NARRATION_INTERNAL_BOUNDARY_LEAK",
                page,
                "Speaker notes repeat an internal boundary that is not the page's "
                "declared business subject.",
                "Remove the internal boundary from speaker notes and narrate the "
                "main judgment, support, and implication.",
                evidence=(page.boundary,),
            )
        )
    return issues

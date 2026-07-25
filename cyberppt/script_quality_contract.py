"""Deterministic PPT script parsing and quality contracts."""

from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata


PAGE_HEADING_RE = re.compile(r"^##\s+第(\d+)页[：:](.+?)\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$")
MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
SOURCE_RE = re.compile(r"S\d{3}")


@dataclass(frozen=True)
class ScriptPage:
    page_id: str
    sequence: int
    heading: str
    page_type: str
    title: str
    main_message: str
    full_prose: str
    selection_notes: str
    evidence_map: str
    evidence_map_refs: tuple[str, ...]
    source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]
    field_order: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScriptDocument:
    pages: tuple[ScriptPage, ...]


@dataclass(frozen=True)
class ScriptQualityIssue:
    code: str
    severity: str
    message: str
    pages: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    suggested_action: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "pages": list(self.pages),
            "source_ids": list(self.source_ids),
            "evidence": list(self.evidence),
            "suggested_action": self.suggested_action,
        }


def _normalize_page_type(value: str) -> str:
    if "章节" in value:
        return "chapter"
    if "封面" in value:
        return "cover"
    if "目录" in value:
        return "contents"
    if "封底" in value:
        return "closing"
    return "content"


def _page_sections(text: str) -> list[tuple[int, str, str]]:
    matches = list(PAGE_HEADING_RE.finditer(text))
    return [
        (
            int(match.group(1)),
            match.group(2).strip(),
            text[
                match.end() : (
                    matches[index + 1].start()
                    if index + 1 < len(matches)
                    else len(text)
                )
            ],
        )
        for index, match in enumerate(matches)
    ]


def _field_blocks(body: str) -> dict[str, str]:
    blocks: dict[str, list[str]] = {}
    active = ""
    for raw_line in body.splitlines():
        match = FIELD_RE.match(raw_line)
        if match:
            active = match.group(1).strip()
            blocks[active] = [match.group(2).strip()]
        elif active:
            blocks[active].append(raw_line.rstrip())
    return {key: "\n".join(lines).strip() for key, lines in blocks.items()}


def _field_order(body: str) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw_line in body.splitlines():
        match = FIELD_RE.match(raw_line)
        if match:
            ordered.append(match.group(1).strip())
    return tuple(ordered)


def parse_script_markdown(text: str) -> ScriptDocument:
    pages: list[ScriptPage] = []
    for sequence, heading, body in _page_sections(text):
        fields = _field_blocks(body)
        onscreen = fields.get("上屏文字", "")
        modules = tuple(
            match.group(1).strip()
            for line in onscreen.splitlines()
            if (match := MODULE_RE.match(line))
        )
        pages.append(
            ScriptPage(
                page_id=f"p{sequence:02d}",
                sequence=sequence,
                heading=heading,
                page_type=_normalize_page_type(fields.get("页面类型", "")),
                title=fields.get("页面标题", heading).strip(),
                main_message=fields.get("主判断", "").strip(),
                full_prose=fields.get("完整文字稿", "").strip(),
                selection_notes=fields.get("文字稿取舍说明", "").strip(),
                evidence_map=fields.get("证据映射", "").strip(),
                evidence_map_refs=tuple(SOURCE_RE.findall(fields.get("证据映射", ""))),
                source_refs=tuple(SOURCE_RE.findall(fields.get("证据", ""))),
                boundary=fields.get("边界", "").strip(),
                visual_structure=fields.get("视觉结构", "").strip(),
                onscreen_text=onscreen,
                module_titles=modules,
                field_order=_field_order(body),
            )
        )
    if not pages:
        raise ValueError("script contains no page headings")
    return ScriptDocument(tuple(pages))


SCOPE_TERMS = ("首期", "一期", "建设范围", "交付范围", "投资", "部署方式", "采购")
IMPLEMENTATION_TERMS = ("实施路线", "建设周期", "前100天", "组织组建", "预算")
COMPLETED_TERMS = ("已经建成", "已建成", "已经形成完整", "已完成建设", "正式确定")
CONDITIONAL_STATUSES = ("拟", "建议", "待", "暂缓", "后续验证", "条件成熟")
COUNT_WORDS = {
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
}
ORDER_SIGNALS = ("①", "②", "③", "④", "⑤", "→", "随后", "再", "最后")
LOOP_SIGNALS = ("回流", "反馈", "复盘", "闭环", "持续校正")
MATRIX_SIGNALS = ("|---", "×", "矩阵", "行", "列")
LAYER_SIGNALS = ("自下而上", "自上而下", "底座", "层", "贯穿")
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
STYLE_ONLY_TERMS = (
    "简洁现代",
    "高级大气",
    "科技感",
    "大气磅礴",
    "高端炫酷",
)
ANTI_PATTERN_TERMS = (
    "六宫格",
    "Bento Grid",
    "Bento",
    "中心圆",
    "等宽卡片",
    "卡片墙",
    "网页后台",
    "数据大屏",
    "紫蓝渐变",
    "霓虹",
)
NEGATION_TERMS = ("不得", "禁止", "避免", "不使用", "不采用", "不做")
STRATEGY_ORDER = (
    "mission_restructure",
    "business_prose_first",
    "source_state_rebuild",
    "cross_page_dedup",
    "semantic_diagram_realign",
    "density_recompose",
)

PROSE_MIN_CHARS = 80


def _dict_items(
    payload: dict[str, object],
    key: str,
) -> list[dict[str, object]]:
    value = payload.get(key)
    return (
        [item for item in value if isinstance(item, dict)]
        if isinstance(value, list)
        else []
    )


def _outline_pages(
    outline: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        str(page.get("page_id")): page
        for page in _dict_items(outline, "pages")
    }


def _truth_records(
    source_truth: dict[str, object],
) -> dict[str, dict[str, object]]:
    return {
        str(record.get("id")): record
        for record in _dict_items(source_truth, "records")
    }


def _page_text(page: ScriptPage) -> str:
    return "\n".join(
        (
            page.title,
            page.main_message,
            page.full_prose,
            page.onscreen_text,
            page.boundary,
        )
    )


def _claim_text(page: ScriptPage) -> str:
    return "\n".join(
        (page.title, page.main_message, page.full_prose, page.onscreen_text)
    )


def _compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def _nontable_compact_len(text: str) -> int:
    lines = [
        line
        for line in text.splitlines()
        if not line.strip().startswith("|")
    ]
    return _compact_len("\n".join(lines))


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

# Status/aside sermons that must not dominate claim layers (prose climax / onscreen).
# Legitimate duty wording like “不替代专业系统” is not listed here.
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


def _analytical_voice_hits(prose: str) -> tuple[str, ...]:
    hits = [pattern for pattern in _ANALYTICAL_VOICE_PATTERNS if pattern in prose]
    return tuple(hits)


def _boundary_aside_hits(text: str) -> tuple[str, ...]:
    hits = [pattern for pattern in _BOUNDARY_ASIDE_PATTERNS if pattern in text]
    return tuple(hits)


def _issue(
    code: str,
    page: ScriptPage,
    message: str,
    action: str,
    source_ids: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
    severity: str = "error",
) -> ScriptQualityIssue:
    if severity not in {"error", "warning"}:
        raise ValueError(f"unsupported severity: {severity}")
    return ScriptQualityIssue(
        code=code,
        severity=severity,
        message=message,
        pages=(page.page_id,),
        source_ids=source_ids,
        evidence=evidence,
        suggested_action=action,
    )


def normalized_tokens(text: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = re.sub(r"S\d{3}", " ", normalized)
    normalized = re.sub(r"[^\w\u4e00-\u9fff]+", " ", normalized)
    compact = "".join(normalized.split())
    if len(compact) < 3:
        return tuple(compact)
    return tuple(
        compact[index : index + 3]
        for index in range(len(compact) - 2)
    )


def text_similarity(left: str, right: str) -> float:
    left_set = set(normalized_tokens(left))
    right_set = set(normalized_tokens(right))
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def script_retry_directive(
    issues: list[ScriptQualityIssue],
    previous_strategy: str = "",
) -> dict[str, object]:
    codes = sorted({issue.code for issue in issues})
    if any(
        code
        in {
            "CONTENT_PROSE_MISSING",
            "CONTENT_PROSE_AFTER_ONSCREEN",
            "CONTENT_PROSE_TOO_THIN",
            "CONTENT_PROSE_EQUALS_ONSCREEN",
            "CONTENT_PROSE_ONSCREEN_GRANULARITY",
            "CONTENT_PROSE_ANALYTICAL_VOICE",
            "CONTENT_BOUNDARY_ASIDE_OVERLOAD",
            "ONSCREEN_BOUNDARY_ASIDE",
            "CONTENT_SELECTION_NOTES_MISSING",
            "CONTENT_EVIDENCE_MAP_MISSING",
            "PROSE_SOURCE_COVERAGE_GAP",
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
            "PATH_ORDER_SIGNAL_MISSING",
            "LOOP_RETURN_SIGNAL_MISSING",
            "MATRIX_AXES_MISSING",
            "LAYER_HIERARCHY_MISSING",
            "DECLARED_COUNT_MISMATCH",
            "SEMANTIC_DIAGRAM_MISMATCH",
            "VISUAL_STRUCTURE_STYLE_ONLY",
            "VISUAL_STRUCTURE_TOO_THIN",
            "ONSCREEN_ANTI_PATTERN",
            "PRIMITIVE_ONSCREEN_MISMATCH",
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
    return {
        "required": bool(issues),
        "issue_codes": codes,
        "strategy": strategy,
        "instruction": (
            "Rewrite only the failed pages using the new strategy; preserve "
            "valid evidence, states, and page contracts."
        ),
    }


def _declared_count(text: str) -> int | None:
    match = re.search(r"([二两三四五六七八])(?:类|项|步|层)", text)
    return COUNT_WORDS.get(match.group(1)) if match else None


def _prose_issues(
    page: ScriptPage,
    *,
    expected_source_refs: tuple[str, ...] = (),
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
                "Add 文字稿取舍说明 in 1-3 sentences covering evidence, topic, and intensity choices.",
            )
        )
    if not page.evidence_map or not page.evidence_map_refs:
        issues.append(
            _issue(
                "CONTENT_EVIDENCE_MAP_MISSING",
                page,
                "Content page must include an evidence map from support points to Source IDs.",
                "Add 证据映射 listing each support point and its Source ID(s).",
            )
        )
    elif expected_source_refs:
        missing = tuple(
            item for item in expected_source_refs if item not in page.evidence_map_refs
        )
        if missing:
            issues.append(
                _issue(
                    "PROSE_SOURCE_COVERAGE_GAP",
                    page,
                    "Evidence map does not cover all Source IDs assigned by the Outline.",
                    "Map every Outline-assigned Source ID to a support point in 证据映射.",
                    missing,
                )
            )
    return issues


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _presentation_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    full_text = _page_text(page)
    visual = page.visual_structure
    if page.page_type == "content":
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
        if visual.strip():
            has_primitive = _has_any(visual, COMPOSITION_PRIMITIVES)
            has_spatial = _has_any(visual, SPATIAL_SIGNALS)
            style_only = _has_any(visual, STYLE_ONLY_TERMS) and not (
                has_primitive or has_spatial
            )
            if style_only:
                issues.append(
                    _issue(
                        "VISUAL_STRUCTURE_STYLE_ONLY",
                        page,
                        "Visual structure only names style adjectives without spatial structure.",
                        "Rewrite 视觉结构 with a composition primitive and center/main-chain direction.",
                        evidence=tuple(
                            term for term in STYLE_ONLY_TERMS if term in visual
                        ),
                    )
                )
            elif not (has_primitive or has_spatial) or _compact_len(visual) < 12:
                issues.append(
                    _issue(
                        "VISUAL_STRUCTURE_TOO_THIN",
                        page,
                        "Visual structure is too thin to guide on-screen composition.",
                        "Name a composition primitive and the visual center or main-chain direction.",
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
            if (
                ("矩阵筛选" in visual or "矩阵" in visual)
                and not _has_any(page.onscreen_text, MATRIX_SIGNALS)
            ):
                issues.append(
                    _issue(
                        "PRIMITIVE_ONSCREEN_MISMATCH",
                        page,
                        "Matrix-oriented visual structure lacks matrix signals on screen.",
                        "Align 上屏文字 with row/column or table structure, or change the primitive.",
                        severity="warning",
                    )
                )
            if (
                ("贯穿主链" in visual or "阶段推进" in visual)
                and not _has_any(page.onscreen_text, ORDER_SIGNALS)
            ):
                issues.append(
                    _issue(
                        "PRIMITIVE_ONSCREEN_MISMATCH",
                        page,
                        "Path/stage visual structure lacks on-screen order signals.",
                        "Add numbered steps, arrows, or sequence words matching the main chain.",
                        severity="warning",
                    )
                )
            if "闭环回流" in visual and not _has_any(
                page.onscreen_text, LOOP_SIGNALS
            ):
                issues.append(
                    _issue(
                        "PRIMITIVE_ONSCREEN_MISMATCH",
                        page,
                        "Loop visual structure lacks on-screen return or feedback relation.",
                        "Name the feedback, review, or correction link on screen.",
                        severity="warning",
                    )
                )
            if "分层剖面" in visual and not _has_any(
                page.onscreen_text, LAYER_SIGNALS
            ):
                issues.append(
                    _issue(
                        "PRIMITIVE_ONSCREEN_MISMATCH",
                        page,
                        "Layered visual structure lacks hierarchy signals on screen.",
                        "Name layers, support relations, or top-to-bottom reading order.",
                        severity="warning",
                    )
                )
    path_like = "路径" in visual or "贯穿主链" in visual or "阶段推进" in visual
    if path_like and not any(
        signal in page.onscreen_text for signal in ORDER_SIGNALS
    ):
        issues.append(
            _issue(
                "PATH_ORDER_SIGNAL_MISSING",
                page,
                "Path visual lacks an on-screen order signal.",
                "Add numbered steps, arrows, or explicit sequence words matching the path.",
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
    count = _declared_count(page.main_message + "\n" + page.onscreen_text)
    if (
        count is not None
        and page.module_titles
        and len(page.module_titles) != count
    ):
        issues.append(
            _issue(
                "DECLARED_COUNT_MISMATCH",
                page,
                (
                    f"Declared count {count} does not match "
                    f"{len(page.module_titles)} on-screen modules."
                ),
                "Align the declared count and the visible module structure.",
                evidence=(str(count), str(len(page.module_titles))),
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
        and len(page.module_titles) > 5
        and not any(
            signal in page.onscreen_text
            for signal in ORDER_SIGNALS + LAYER_SIGNALS
        )
    ):
        issues.append(
            _issue(
                "MODULE_HIERARCHY_MISSING",
                page,
                "More than five modules are presented without grouping or hierarchy.",
                "Group modules under explicit stages or layers, or split independent conclusions.",
            )
        )
    return issues


def audit_script_quality(
    script: ScriptDocument,
    outline: dict[str, object],
    source_truth: dict[str, object],
) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    pages_by_id = _outline_pages(outline)
    records_by_id = _truth_records(source_truth)
    sequences = [page.sequence for page in script.pages]
    if sequences != list(range(min(sequences), max(sequences) + 1)):
        issues.append(
            ScriptQualityIssue(
                "SCRIPT_PAGE_SEQUENCE_GAP",
                "error",
                "Script batch page numbers must be continuous.",
                tuple(page.page_id for page in script.pages),
                suggested_action=(
                    "Restore the missing page or split the input into "
                    "explicit continuous batches."
                ),
            )
        )
    for page in script.pages:
        contract = pages_by_id.get(page.page_id)
        if contract is None:
            issues.append(
                _issue(
                    "SCRIPT_PAGE_NOT_IN_OUTLINE",
                    page,
                    "Script page has no matching Outline contract.",
                    "Add the page to the approved Outline or remove it from the script batch.",
                )
            )
            continue
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
            if (
                not page.main_message
                or not page.source_refs
                or not page.visual_structure
            ):
                issues.append(
                    _issue(
                        "CONTENT_PAGE_FIELDS_MISSING",
                        page,
                        "Content page requires main judgment, evidence, and visual structure.",
                        "Restore the missing backend fields before review.",
                    )
                )
            expected_refs = tuple(
                str(item)
                for item in contract.get("source_refs", [])
                if item
            )
            issues.extend(_prose_issues(page, expected_source_refs=expected_refs))
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
            matched = tuple(
                term for term in SCOPE_TERMS if term in claim_text
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
            matched = tuple(
                term for term in IMPLEMENTATION_TERMS if term in claim_text
            )
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
        issues.extend(_presentation_issues(page))
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
    return issues

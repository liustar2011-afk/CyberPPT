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
    source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]


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
                source_refs=tuple(SOURCE_RE.findall(fields.get("证据", ""))),
                boundary=fields.get("边界", "").strip(),
                visual_structure=fields.get("视觉结构", "").strip(),
                onscreen_text=onscreen,
                module_titles=modules,
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
STRATEGY_ORDER = (
    "mission_restructure",
    "source_state_rebuild",
    "cross_page_dedup",
    "semantic_diagram_realign",
    "density_recompose",
)


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
        (page.title, page.main_message, page.onscreen_text, page.boundary)
    )


def _claim_text(page: ScriptPage) -> str:
    return "\n".join((page.title, page.main_message, page.onscreen_text))


def _issue(
    code: str,
    page: ScriptPage,
    message: str,
    action: str,
    source_ids: tuple[str, ...] = (),
    evidence: tuple[str, ...] = (),
) -> ScriptQualityIssue:
    return ScriptQualityIssue(
        code=code,
        severity="error",
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


def _presentation_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    issues: list[ScriptQualityIssue] = []
    full_text = _page_text(page)
    visual = page.visual_structure
    if "路径" in visual and not any(
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
    if "闭环" in visual and not any(
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
    if "矩阵" in visual and not any(
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
    if ("分层" in visual or "架构" in visual) and not any(
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
            or page.module_titles
        ):
            issues.append(
                _issue(
                    "CHAPTER_PAGE_HAS_CONTENT",
                    page,
                    "Chapter transition pages may contain only the chapter title.",
                    "Remove the thesis, modules, methods, and task text from this page.",
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

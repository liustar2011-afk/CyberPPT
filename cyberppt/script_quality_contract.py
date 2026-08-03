"""Deterministic PPT script parsing and quality contracts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata


PAGE_HEADING_RE = re.compile(r"^##\s+第(\d+)页[：:](.+?)\s*$", re.MULTILINE)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$")
NON_ONSCREEN_VISUAL_HEADING_RE = re.compile(r"^【视觉结构[，,]\s*不上屏】\s*$")
MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
INLINE_MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*(?:\s*[|｜:：].*)?\s*$")
# Source Truth identifiers are historically three digits (for example S015)
# and are four digits in current projects (for example S0410). Match the
# complete identifier so four-digit refs are not truncated to S041 and do not
# produce false UNKNOWN/MISSING source diagnostics.
SOURCE_RE = re.compile(r"S\d{3,4}(?!\d)")
SOURCE_RANGE_RE = re.compile(
    r"S(?P<start>\d{3,4})\s*[—–-]\s*S(?P<end>\d{3,4})"
)
PAGE_CONTRACT_RECEIPT_RE = re.compile(
    r"<!--\s*cyberppt-page-contract\s+(?P<payload>\{.*?\})\s*-->",
    re.S,
)


SPEAKER_SECTION_RE = re.compile(
    r"【(?:演讲者备注|演讲稿|讲稿|备注)】\s*(?P<body>.*)$",
    re.S,
)
SPEAKER_SLIDE_META_RE = re.compile(
    r"(这一页|下一页|上一页|本页我们|本页先|本页把|本页只|看这一页|从这一页)"
)
SPEAKER_HOST_META_RE = re.compile(
    r"(各位同事|先把.{0,18}说清楚|先说明|先谈|先讲规则|"
    r"综合起来|接下来看|到这里收一下|全篇收在|请.{0,12}听|请先记住)"
)
SPEAKER_PLACEHOLDER_RE = re.compile(
    r"(原文围绕.{0,36}(?:展开|说明)|"
    r"各项内容共同回答.{0,18}(?:问题|任务)|"
    r"关键对象、作用机制和条件边界)"
)
NUMBERED_EVIDENCE_BULLET_RE = re.compile(
    r"^\s*-\s*依据(?P<number>\d+)[：:]\s*(?P<body>.*?)\s*$"
)
GENERIC_ONSCREEN_RELATION_RE = re.compile(
    r"(?:业务关系[：:]\s*)?(?:以上|上述)(?:内容|要点|依据)"
    r"(?:共同)?(?:构成|形成|支撑|完成)(?:本节|本页)?(?:完整)?(?:内容|判断|任务)"
)
DEFENSIVE_BOUNDARY_COACHING_RE = re.compile(
    r"(反复区分|避免(?:听众)?.{0,12}(?:误解|听成|当成)|"
    r"不要.{0,12}讲成|不是.{0,8}承诺|不构成.{0,8}承诺|"
    r"防止.{0,12}误解|以免.{0,12}误解)"
)
CONSTRAINT_THEME_TERMS = (
    "范围",
    "边界",
    "准入",
    "安全",
    "质量",
    "治理",
    "合规",
    "风险",
    "审核",
    "权限",
    "保障",
    "部署",
    "高可用",
    "容量",
    "降级",
    "验收",
    "职责",
)
CONSTRAINT_ARGUMENT_ROLES = {
    "scope",
    "boundary",
    "admission",
    "security",
    "governance",
    "quality",
    "compliance",
    "risk",
    "assurance",
    "deployment",
    "capacity",
    "degradation",
    "acceptance",
}
ONSCREEN_CONSTRAINT_MODULE_TERMS = (
    "研究边界",
    "决策边界",
    "研究状态",
    "证据状态",
    "待补证事项",
    "待论证事项",
    "质量边界",
    "质量要求",
    "安全边界",
    "治理边界",
    "合规边界",
    "风险约束",
    "约束条件",
    "准入条件",
)
ONSCREEN_CONSTRAINT_DETAIL_TERMS = (
    "题源保密",
    "个人信息保护",
    "泄露",
    "批量还原",
    "权限隔离",
    "数据隔离",
    "质量分级",
    "人工审核",
    "不得展示",
    "不得开放",
    "不可追溯",
    "模型幻觉",
)
SPEAKER_NOTES_MIN_CHARS = 60
VISIBLE_JUDGMENT_MIN_SIMILARITY = 0.04
VISIBLE_JUDGMENT_TERMINAL_PUNCTUATION = "。；，：？！.!?;,:"
ONSCREEN_JUDGMENT_MODES = ("locked", "semantic_only")
SEMANTIC_ONLY_JUDGMENT_ROLES = {
    "relationship",
    "positioning",
    "boundary",
    "mechanism",
}
LOCKED_JUDGMENT_ROLES = {
    "fact",
    "metric",
    "milestone",
    "acceptance",
    "prohibition",
}


def resolve_judgment_mode(explicit_mode: str = "", judgment_role: str = "") -> str:
    """Resolve display policy from an explicit override, then semantic role."""

    mode = explicit_mode.strip()
    role = judgment_role.strip()
    if mode:
        if mode not in ONSCREEN_JUDGMENT_MODES:
            raise ValueError(f"unsupported onscreen_judgment_mode: {mode}")
        return mode
    if role in SEMANTIC_ONLY_JUDGMENT_ROLES:
        return "semantic_only"
    if role in LOCKED_JUDGMENT_ROLES or not role:
        return "locked"
    raise ValueError(f"unsupported judgment_role: {role}")


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
    boundary_source_refs: tuple[str, ...]
    boundary: str
    visual_structure: str
    onscreen_text: str
    module_titles: tuple[str, ...]
    subtitle: str = ""
    visual_proof: str = ""
    onscreen_judgment: str = ""
    judgment_role: str = ""
    onscreen_judgment_mode: str = ""
    visual_intent_type: str = ""
    visual_carrier: str = ""
    image_locked_text: str = ""
    layout_motif: str = ""
    scene_role: str = ""
    field_order: tuple[str, ...] = ()
    coaching_tip: str = ""
    speaker_notes: str = ""
    contract_receipt: dict[str, object] | None = None

    @property
    def core_message(self) -> str:
        """Canonical v2 semantic center; main_message remains a read alias."""

        return self.main_message

    @property
    def onscreen_conclusion(self) -> str:
        return self.onscreen_judgment

    @property
    def content_relations(self) -> tuple[dict[str, object], ...]:
        receipt = self.contract_receipt or {}
        relations = receipt.get("content_relations")
        if not isinstance(relations, list):
            return ()
        return tuple(item for item in relations if isinstance(item, dict))


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
        if re.match(r"^【(?:演讲者备注|演讲稿|讲稿|备注)】", raw_line.strip()):
            active = ""
            continue
        if NON_ONSCREEN_VISUAL_HEADING_RE.match(raw_line.strip()):
            active = "视觉结构"
            blocks[active] = []
            continue
        match = FIELD_RE.match(raw_line)
        if match:
            active = match.group(1).strip()
            blocks[active] = [match.group(2).strip()]
        elif active:
            blocks[active].append(raw_line.rstrip())
    return {key: "\n".join(lines).strip() for key, lines in blocks.items()}


def _source_refs(text: str) -> tuple[str, ...]:
    """Extract explicit Source IDs and expand inclusive ``Sxxxx—Syyyy`` ranges.

    Authoring inputs and human-readable scripts use ranges to avoid turning the
    evidence field into an unreadable wall of IDs.  The audit contract still
    needs the atomic IDs for exact Outline coverage, so expand ranges at parse
    time while preserving first-seen order and de-duplicating references.
    """

    source_text = text or ""
    ranges = list(SOURCE_RANGE_RE.finditer(source_text))
    events: list[tuple[int, str, object]] = []
    for match in ranges:
        events.append((match.start(), "range", match))
    for match in SOURCE_RE.finditer(source_text):
        if any(item.start() <= match.start() < item.end() for item in ranges):
            continue
        events.append((match.start(), "single", match.group(0)))

    refs: list[str] = []
    for _, kind, value in sorted(events, key=lambda item: item[0]):
        if kind == "single":
            refs.append(str(value))
            continue
        match = value
        assert isinstance(match, re.Match)
        start = int(match.group("start"))
        end = int(match.group("end"))
        if end < start or end - start > 1000:
            continue
        width = max(len(match.group("start")), len(match.group("end")))
        refs.extend(f"S{number:0{width}d}" for number in range(start, end + 1))
    return tuple(dict.fromkeys(refs))


def _field_order(body: str) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw_line in body.splitlines():
        if NON_ONSCREEN_VISUAL_HEADING_RE.match(raw_line.strip()):
            ordered.append("视觉结构")
            continue
        match = FIELD_RE.match(raw_line)
        if match:
            ordered.append(match.group(1).strip())
    return tuple(ordered)


def extract_speaker_notes(body: str) -> str:
    """Prefer 【演讲者备注】 section, then `- 演讲者备注：` field."""

    section = SPEAKER_SECTION_RE.search(body)
    if section:
        return re.sub(r"\n-{3,}\s*$", "", section.group("body").strip()).strip()
    fields = _field_blocks(body)
    return fields.get("演讲者备注", "").strip()


def extract_page_contract_receipt(body: str) -> dict[str, object] | None:
    match = PAGE_CONTRACT_RECEIPT_RE.search(body)
    if not match:
        return None
    try:
        payload = json.loads(match.group("payload"))
    except json.JSONDecodeError:
        return {"_invalid": True}
    return payload if isinstance(payload, dict) else {"_invalid": True}


def _module_title(line: str) -> str | None:
    """Extract a Markdown module title from a standalone or inline heading.

    Reading-oriented scripts commonly use either ``**模块**`` followed by
    bullets or the compact ``**模块**｜正文`` form.  Both represent one
    drawable module; the inline body must remain in the visible text layer.
    """

    match = MODULE_RE.match(line) or INLINE_MODULE_RE.match(line)
    return match.group(1).strip() if match else None


def parse_script_markdown(text: str) -> ScriptDocument:
    pages: list[ScriptPage] = []
    for sequence, heading, body in _page_sections(text):
        fields = _field_blocks(body)
        onscreen = fields.get("上屏文字", "")
        modules = tuple(
            title
            for line in onscreen.splitlines()
            if (title := _module_title(line))
        )
        pages.append(
            ScriptPage(
                page_id=f"p{sequence:02d}",
                sequence=sequence,
                heading=heading,
                page_type=_normalize_page_type(fields.get("页面类型", "")),
                title=fields.get("页面标题", heading).strip(),
                subtitle=fields.get("副标题", "").strip(),
                main_message=(fields.get("核心结论") or fields.get("主判断", "")).strip(),
                full_prose=fields.get("完整文字稿", "").strip(),
                selection_notes=fields.get("文字稿取舍说明", "").strip(),
                evidence_map=fields.get("证据映射", "").strip(),
                evidence_map_refs=_source_refs(fields.get("证据映射", "")),
                source_refs=tuple(
                    dict.fromkeys(
                        list(_source_refs(fields.get("证据", "")))
                        + list(_source_refs(fields.get("边界依据", "")))
                    )
                ),
                boundary_source_refs=_source_refs(fields.get("边界依据", "")),
                boundary=fields.get("边界", "").strip(),
                visual_structure=fields.get("视觉结构", "").strip(),
                onscreen_text=onscreen,
                module_titles=modules,
                visual_proof=fields.get("视觉证明", "").strip(),
                onscreen_judgment=fields.get("上屏结论", "").strip(),
                judgment_role=fields.get("判断角色", "").strip(),
                onscreen_judgment_mode=fields.get("上屏结论模式", "").strip(),
                visual_intent_type=fields.get("视觉意图类型", "").strip(),
                visual_carrier=fields.get("视觉载体", "").strip(),
                image_locked_text=fields.get("生图锁定文字", "").strip(),
                layout_motif=fields.get("版式母题", "").strip(),
                scene_role=fields.get("场景角色", "").strip(),
                field_order=_field_order(body),
                coaching_tip=(
                    fields.get("讲解提示", "")
                    .split("<!--", 1)[0]
                    .split("【", 1)[0]
                    .strip()
                ),
                speaker_notes=extract_speaker_notes(body),
                contract_receipt=extract_page_contract_receipt(body),
            )
        )
    if not pages:
        raise ValueError("script contains no page headings")
    return ScriptDocument(tuple(pages))


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
# Module labels that usually cross-cut / govern a main chain rather than sit as
# an equal → stage. Peer-staging them on a path/layer list is a common error.
CROSSCUT_PEER_LABELS = (
    "横向治理层",
    "横向治理",
    "质量与生命周期",
    "生命周期",
    "统一模型治理",
)
DEPTH_DEFENSE_MARKERS = (
    "纵深防护",
    "五层纵深",
    "纵深",
    "逐层衔接",
    "逐级收紧",
)
MECHANISM_LANE_LABELS = (
    "资源隔离",
    "弹性降级",
    "差异化降级",
)
BUSINESS_LANE_LABELS = (
    "学生实时链路",
    "教师异步队列",
    "在线事务链",
    "异步事件链",
    "离线分析链",
    "实时链路",
    "异步队列",
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
    "manuscript_form_cleanup",
    "speaker_notes_naturalize",
)

PROSE_MIN_CHARS = 80
# Extreme floor stays an ERROR under independent-reading audits; the former
# 0.22/0.28 bands remain advisory so authors compress via 取舍说明 instead of
# stuffing tokens to chase coverage.
ONSCREEN_SEMANTIC_COVERAGE_ERROR_FLOOR = 0.15
ONSCREEN_SEMANTIC_COVERAGE_MIN = 0.22
ONSCREEN_SEMANTIC_COVERAGE_TARGET = 0.28
ONSCREEN_EFFECTIVE_CHARS_MIN = 220
ONSCREEN_EFFECTIVE_CHARS_MAX = 320
ONSCREEN_PROSE_DENSITY_RATIO = 0.50
SELECTION_NOTE_REQUIRED_MARKERS = ("必留上屏", "仅讲解", "仅追溯")
PATH_LIKE_INTENT_TYPES = frozenset(
    {
        "path_chain",
        "closed_loop",
        "phase",
        "causal",
        "crosscutting_chain",
    }
)
LAYER_LIKE_INTENT_TYPES = frozenset(
    {
        "hierarchy_support",
        "capability_relationship",
        "crosscutting_chain",
    }
)
ONSCREEN_STORY_EXPLANATION_SIGNALS = (
    "说明",
    "表明",
    "反映",
    "意味着",
    "对应",
    "取决于",
    "关键是",
    "使",
    "成为",
    "支撑",
    "难以",
    "不足以",
    "并非",
)
ONSCREEN_STORY_IMPLICATION_SIGNALS = (
    "因此",
    "由此",
    "进而",
    "从而",
    "转向",
    "需要",
    "推动",
    "形成",
    "暴露",
    "导致",
    "削弱",
    "放大",
    "共同作用",
    "待建",
    "尚未贯通",
)
ONSCREEN_STORY_RELATION_SIGNALS = (
    *ONSCREEN_STORY_EXPLANATION_SIGNALS,
    *ONSCREEN_STORY_IMPLICATION_SIGNALS,
    "→",
    "先",
    "再",
    "随后",
    "最后",
    "回流",
    "闭环",
    "对照",
    "相比",
    "高于",
    "低于",
    "共同",
    "支撑",
    "依赖",
    "贯通",
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
        (
            page.title,
            page.main_message,
            page.onscreen_judgment,
            page.full_prose,
            page.onscreen_text,
            page.boundary,
        )
    )


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


def _compact_len(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def meaningful_char_count(text: str) -> int:
    """Count visible Chinese, Latin, and numeric characters only."""

    return len(re.findall(r"[\u4e00-\u9fffA-Za-z0-9]", text))


def onscreen_effective_char_target(page: ScriptPage) -> int:
    """Return the adaptive minimum needed for an independently readable page."""

    prose_chars = meaningful_char_count(page.full_prose)
    target = round(prose_chars * ONSCREEN_PROSE_DENSITY_RATIO)
    return min(
        ONSCREEN_EFFECTIVE_CHARS_MAX,
        max(ONSCREEN_EFFECTIVE_CHARS_MIN, target),
    )


def parse_selection_notes(notes: str) -> dict[str, str]:
    """Split 文字稿取舍说明 into 必留上屏 / 仅讲解 / 仅追溯 buckets."""

    text = (notes or "").strip()
    if not text:
        return {}
    parts: dict[str, list[str]] = {marker: [] for marker in SELECTION_NOTE_REQUIRED_MARKERS}
    active = ""
    for raw in text.splitlines():
        line = raw.strip().lstrip("-*• ").strip()
        if not line:
            continue
        matched = ""
        for marker in SELECTION_NOTE_REQUIRED_MARKERS:
            if line.startswith(f"{marker}：") or line.startswith(f"{marker}:"):
                matched = marker
                remainder = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
                active = marker
                if remainder.strip():
                    parts[marker].append(remainder.strip())
                break
        if matched:
            continue
        if active:
            parts[active].append(line)
    return {
        marker: "\n".join(chunks).strip()
        for marker, chunks in parts.items()
        if chunks
    }


def selection_notes_are_structured(notes: str) -> bool:
    parsed = parse_selection_notes(notes)
    return all(marker in parsed and parsed[marker] for marker in SELECTION_NOTE_REQUIRED_MARKERS)


def _nontable_compact_len(text: str) -> int:
    lines = [
        line
        for line in text.splitlines()
        if not line.strip().startswith("|")
    ]
    return _compact_len("\n".join(lines))


def _onscreen_content_lines(text: str) -> tuple[str, ...]:
    """Return drawable on-screen lines without Markdown module headings."""

    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or MODULE_RE.match(line):
            continue
        if line.startswith("-"):
            line = line[1:].strip()
        # Preserve the inline module body while removing Markdown emphasis
        # from the label, e.g. ``**业务标准**｜口径统一``.
        line = re.sub(r"^\*\*(.+?)\*\*(?=\s*[|｜:：])", r"\1", line)
        line = line.strip("* ")
        if line:
            lines.append(line)
    return tuple(lines)


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
        effective_char_target = onscreen_effective_char_target(page)
        density_status = (
            "pass" if effective_chars >= effective_char_target else "low"
        )
        if density_status == "low":
            density_low_count += 1
        story_roles = onscreen_story_roles(page)
        if (
            _compact_len(page.full_prose) >= PROSE_MIN_CHARS * 2
            and semantic_coverage < ONSCREEN_SEMANTIC_COVERAGE_MIN
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

# Contrastive negation of the form “不是……而是……” is prohibited in
# authored slide copy. It usually spends the reader's attention rebutting a
# discarded frame before stating the actual claim. Require the claim and the
# distinction to be written directly instead.
_PROHIBITED_CONTRAST_RE = re.compile(
    r"(?:不是|并非)[^。！？；\n]{0,100}?(?:，|,)?\s*而是"
)

# Conversational scaffolding is unsuitable for the manuscript layer. Keep this
# list deliberately narrow: it targets reader-address and spoken transitions,
# while allowing ordinary formal verbs such as“可以”“需要”和“应当”.
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

# Backend relationship labels must not appear in 上屏文字. They belong in
# 完整文字稿 / 讲解提示 and are forwarded to ImageGen as off-screen semantics.
ONSCREEN_RELATION_META_LABELS: tuple[str, ...] = (
    "业务含义",
    "服务关系",
    "对象关系",
    "协同关系",
    "组件关系",
    "恢复关系",
    "纵向关系",
    "闭环关系",
    "滚动关系",
    "工作流",
    "责任关系",
    "四层贯通",
    "建设关系",
    "分工关系",
    "从业务关系看",
)

_ONSCREEN_RELATION_META_RE = re.compile(
    r"^\s*[-*•]?\s*(?P<label>"
    + "|".join(re.escape(label) for label in ONSCREEN_RELATION_META_LABELS)
    + r")\s*[：:]",
)


def _onscreen_relation_meta_hits(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for raw in text.splitlines():
        match = _ONSCREEN_RELATION_META_RE.match(raw)
        if match:
            hits.append(match.group("label"))
    return tuple(dict.fromkeys(hits))


def _analytical_voice_hits(prose: str) -> tuple[str, ...]:
    hits = [pattern for pattern in _ANALYTICAL_VOICE_PATTERNS if pattern in prose]
    return tuple(hits)


def _prohibited_contrast_hits(text: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(0) for match in _PROHIBITED_CONTRAST_RE.finditer(text)))


def _prohibited_colloquial_hits(text: str) -> tuple[str, ...]:
    return tuple(pattern for pattern in _PROHIBITED_COLLOQUIAL_PATTERNS if pattern in text)


def _unlabeled_onscreen_bullets(text: str) -> tuple[str, ...]:
    hits = []
    for line in text.splitlines():
        stripped = line.strip()
        # A conclusion-first item has a short label immediately after the
        # bullet marker.  A colon buried in the supporting sentence does not
        # satisfy the contract.
        has_prefix = bool(re.match(r"^-\s*[^\s：:，,。；;、]{2,24}[：:]", stripped))
        if stripped.startswith("-") and not has_prefix:
            hits.append(stripped)
    return tuple(hits)


def _mechanical_evidence_bullets(text: str) -> tuple[str, ...]:
    """Detect source-sentence atomization masquerading as authored slide copy."""

    matches = []
    for line in text.splitlines():
        match = NUMBERED_EVIDENCE_BULLET_RE.match(line)
        if match:
            matches.append((line.strip(), match.group("body").strip()))
    if not matches:
        return ()
    fragments = [
        line
        for line, body in matches
        if _compact_len(body) < 12 or body.endswith(("，", "；", ",", ";"))
    ]
    if len(matches) >= 6:
        fragments.extend(line for line, _body in matches)
    return tuple(dict.fromkeys(fragments))


def _speaker_placeholder_hits(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(match.group(0) for match in SPEAKER_PLACEHOLDER_RE.finditer(text))
    )


def _generic_onscreen_relation_hits(text: str) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            match.group(0) for match in GENERIC_ONSCREEN_RELATION_RE.finditer(text)
        )
    )


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


def _source_statement_overlap(statement: str, authored: str, size: int = 4) -> float:
    """Measure factual phrase survival without requiring verbatim prose."""

    def shingles(value: str) -> set[str]:
        compact = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]", "", value or "")
        return {
            compact[index : index + size]
            for index in range(max(0, len(compact) - size + 1))
            if compact[index : index + size]
        }

    source = shingles(statement)
    if not source:
        return 1.0
    return len(source & shingles(authored)) / len(source)


def _source_consumption_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Verify that source-grounded content units reach the authored page.

    ``source_refs`` prove traceability only.  Strict Outline v2 pages also
    carry ``source_statements`` in each content unit; this check requires the
    editorial unit or at least one of its factual anchors to survive in the
    full prose/visible layer.  Supporting units may be compressed, while the
    primary unit remains mandatory.
    """

    evidence_contract = contract.get("source_evidence_contract")
    if not isinstance(evidence_contract, dict) or evidence_contract.get("mode") != "required":
        return []
    raw_units = contract.get("content_units")
    if not isinstance(raw_units, list):
        return []
    expected_unit_ids = {
        str(unit.get("unit_id"))
        for unit in raw_units
        if isinstance(unit, dict)
        and str(unit.get("role") or "") != "boundary"
        and unit.get("unit_id")
    }
    receipt = page.contract_receipt or {}
    declared_unit_ids = receipt.get("consumed_content_unit_ids")
    if not isinstance(declared_unit_ids, list):
        return [
            _issue(
                "CONTENT_UNIT_CONSUMPTION_DECLARATION_MISSING",
                page,
                "The page receipt must declare the content units consumed by the authored page.",
                "Copy the explicit consumes list from the page authoring artifact into the page receipt.",
            )
        ]
    if {str(item) for item in declared_unit_ids} != expected_unit_ids:
        return [
            _issue(
                "CONTENT_UNIT_CONSUMPTION_DECLARATION_MISMATCH",
                page,
                "The page receipt consumes a different set of content units than the approved Outline.",
                "Align the page authoring consumes list with every non-boundary content_unit.unit_id.",
                evidence=tuple(sorted(expected_unit_ids)),
            )
        ]
    contract_units_by_id = {
        str(unit.get("unit_id")): unit
        for unit in evidence_contract.get("units", [])
        if isinstance(unit, dict) and unit.get("unit_id")
    }
    contract_units = {
        tuple(str(item) for item in unit.get("source_refs") or []): unit
        for unit in evidence_contract.get("units", [])
        if isinstance(unit, dict)
    }
    authored = "\n".join(
        (page.full_prose, page.onscreen_text, page.speaker_notes, page.visual_structure)
    )
    issues: list[ScriptQualityIssue] = []
    for unit in raw_units:
        if not isinstance(unit, dict) or str(unit.get("role") or "") == "boundary":
            continue
        statement = str(unit.get("statement") or "")
        evidence_unit = contract_units_by_id.get(str(unit.get("unit_id"))) or contract_units.get(
            tuple(str(item) for item in unit.get("source_refs") or []),
            {},
        )
        source_statements = [
            str(item)
            for item in (
                unit.get("source_statements")
                or evidence_unit.get("source_statements")
                or []
            )
            if str(item).strip()
        ]
        unit_overlap = _source_statement_overlap(statement, authored)
        fact_overlaps = [
            _source_statement_overlap(item, authored)
            for item in source_statements
        ]
        threshold = 0.10 if str(unit.get("role") or "") == "primary" else 0.04
        if unit_overlap < threshold and max(fact_overlaps or [0.0]) < threshold:
            refs = tuple(str(item) for item in unit.get("source_refs") or [])
            issues.append(
                _issue(
                    "SOURCE_FACT_NOT_CONSUMED",
                    page,
                    "Source IDs are present, but the page does not consume the corresponding factual claim.",
                    "Rewrite 完整文字稿 or 上屏文字 from the content unit and its source statements; keep Source IDs as traceability only.",
                    source_ids=refs,
                    evidence=(statement, f"unit_overlap={unit_overlap:.3f}", f"max_fact_overlap={max(fact_overlaps or [0.0]):.3f}"),
                )
            )
    return issues


def onscreen_semantic_coverage(page: ScriptPage) -> float:
    """Measure how much full-prose meaning survives in the drawable text layer."""

    prose_tokens = set(normalized_tokens(page.full_prose))
    if not prose_tokens:
        return 1.0
    visible = "\n".join(
        part
        for part in (page.onscreen_judgment, page.onscreen_text)
        if part.strip()
    )
    visible_tokens = set(normalized_tokens(visible))
    return len(prose_tokens & visible_tokens) / len(prose_tokens)


def onscreen_story_roles(page: ScriptPage) -> dict[str, bool]:
    """Return the minimum roles needed for an independently readable slide."""

    visible = "\n".join(
        part
        for part in (page.onscreen_judgment, page.onscreen_text)
        if part.strip()
    )
    content_lines = _onscreen_content_lines(page.onscreen_text)
    conclusion = bool(page.onscreen_judgment.strip())
    relation = (
        any(signal in visible for signal in ONSCREEN_STORY_RELATION_SIGNALS)
        or onscreen_semantic_coverage(page) >= ONSCREEN_SEMANTIC_COVERAGE_MIN
    )
    return {
        "conclusion": conclusion,
        "evidence": len(content_lines) >= 2,
        "relation": relation,
        "closure": conclusion,
    }


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
            "ONSCREEN_BOUNDARY_ASIDE",
            "ONSCREEN_RELATION_META_LABEL",
            "CONTENT_SELECTION_NOTES_MISSING",
            "CONTENT_SELECTION_NOTES_UNSTRUCTURED",
            "CONTENT_SELECTION_ONSCREEN_MISMATCH",
            "CONTENT_EVIDENCE_MAP_MISSING",
            "PROSE_SOURCE_COVERAGE_GAP",
            "ONSCREEN_RELATION_ISOMORPHISM",
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
            "VISUAL_CENTER_JUDGMENT_MISMATCH",
            "VISUAL_STRUCTURE_PRIMITIVE_MISMATCH",
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


def _declared_count(text: str) -> int | None:
    match = re.search(
        r"([二两三四五六七八])(?:类能力|类任务|类断点|项任务|个模块|步|层)",
        text,
    )
    return COUNT_WORDS.get(match.group(1)) if match else None


def _prose_issues(
    page: ScriptPage,
    *,
    expected_source_refs: tuple[str, ...] = (),
    independent_reading_required: bool = False,
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
        min_story_chars = onscreen_effective_char_target(page)
        coverage = onscreen_semantic_coverage(page)
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
    contrast_hits = _prohibited_contrast_hits(
        "\n".join((prose, page.onscreen_text, page.speaker_notes))
    )
    if contrast_hits:
        issues.append(
            _issue(
                "PROHIBITED_NOT_BUT_CONTRAST",
                page,
                "Authored script uses the prohibited ‘不是……而是……’ contrast pattern.",
                "State the intended claim directly; express distinctions with definitions, parallel clauses, or 前者/后者 wording.",
                evidence=contrast_hits,
            )
        )
    colloquial_hits = _prohibited_colloquial_hits(
        "\n".join((prose, page.speaker_notes))
    )
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
        generic_keep_rule = any(
            token in keep for token in ("模块标题", "上屏模块", "页面结论")
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


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _visual_module_label(value: str) -> str:
    text = re.sub(r"^\s*\d+\s*｜\s*", "", value).strip()
    text = re.sub(r"^[①②③④⑤⑥⑦⑧⑨⑩]+", "", text).strip()
    return text.strip(" 。；;，,")


def _visual_structure_chain_nodes(visual: str) -> tuple[str, ...]:
    """Extract peer nodes from「原语——A → B → C」or「原语——A、B、C」lists."""

    text = visual.strip()
    if "——" in text:
        text = text.split("——", 1)[1]
    text = re.split(r"[；;]", text, maxsplit=1)[0]
    text = re.sub(r"一级模块与上屏文字一致。?", "", text)
    text = re.sub(
        r"^(?:自下而上|自上而下|由外向内|横向并列)?依次呈现",
        "",
        text,
    )
    text = re.sub(r"^(?:自下而上|自上而下|由外向内|横向并列)", "", text)
    text = text.strip(" ：:。")
    if "→" in text:
        parts = [part.strip() for part in text.split("→")]
    else:
        parts = re.split(r"[、，,]", text)
    nodes: list[str] = []
    for part in parts:
        label = _visual_module_label(part)
        label = re.sub(r"^(?:设置|以|把)", "", label)
        label = re.sub(r"(?:为视觉中心|按支撑关系连接)$", "", label)
        label = label.strip(" ：:。")
        if label and label not in nodes and len(label) <= 24:
            nodes.append(label)
    return tuple(nodes)


def _page_relation_corpus(page: ScriptPage) -> str:
    return "\n".join(
        (
            page.main_message,
            page.onscreen_judgment,
            page.full_prose,
            page.speaker_notes,
            page.visual_structure,
        )
    )


def _visual_structure_judgment_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    """Catch visual-structure templates that contradict the page judgment."""

    issues: list[ScriptQualityIssue] = []
    visual = page.visual_structure.strip()
    if page.page_type != "content" or not visual:
        return issues
    corpus = _page_relation_corpus(page)
    judgment = f"{page.main_message}\n{page.onscreen_judgment}".strip()
    nodes = _visual_structure_chain_nodes(visual)

    # 1) Cross-cutting roles peer-staged on → / 、 lists.
    peer_hits: list[str] = []
    for node in nodes:
        bare = _visual_module_label(node)
        is_named_crosscut = any(
            bare == label or bare.endswith(label) or label in bare
            for label in CROSSCUT_PEER_LABELS
        )
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
        if (is_named_crosscut or marked) and (
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

    # 2) Declared visual center conflicts with the governing judgment.
    center_match = re.search(
        r"以(?P<center>[^为，。；;\n]{2,24})为视觉中心",
        visual,
    )
    if center_match and judgment:
        center = center_match.group("center").strip()
        if "统一网关" in judgment and "网关" not in center:
            issues.append(
                _issue(
                    "VISUAL_CENTER_JUDGMENT_MISMATCH",
                    page,
                    "Visual center does not match the gateway-centered judgment.",
                    "Put 统一网关 (or 网关治理) at the visual center when the judgment is gateway-led.",
                    evidence=(center, "统一网关"),
                    severity="warning",
                )
            )
        if re.search(r"三类引擎|分别支撑三类应用|分别支撑三类", judgment) and re.search(
            r"(学生|教师|学校)引擎",
            center,
        ):
            issues.append(
                _issue(
                    "VISUAL_CENTER_JUDGMENT_MISMATCH",
                    page,
                    "Visual center privileges one engine while the judgment treats three engines as peers.",
                    "Use a shared hub (统一治理 / 三类引擎协同) or an equal three-engine field.",
                    evidence=(center,),
                    severity="warning",
                )
            )

    # 3) Primitive conflicts with judgment vocabulary.
    if "受控边界" in visual and _has_any(judgment, DEPTH_DEFENSE_MARKERS):
        depth_hits = tuple(m for m in DEPTH_DEFENSE_MARKERS if m in judgment)[:2]
        issues.append(
            _issue(
                "VISUAL_STRUCTURE_PRIMITIVE_MISMATCH",
                page,
                "Boundary-shell primitive used for a depth-defense judgment.",
                "Prefer 分层剖面 / 纵深主链 for layered defense; reserve 受控边界 for admission shells.",
                evidence=("受控边界", *depth_hits),
                severity="warning",
            )
        )

    # 4) Swimlanes peer-stage mechanisms with business chains.
    if "主体泳道" in visual:
        mechanism_hits = tuple(
            label for label in MECHANISM_LANE_LABELS if label in visual
        )
        business_hits = tuple(
            label for label in BUSINESS_LANE_LABELS if label in visual
        )
        if mechanism_hits and business_hits:
            issues.append(
                _issue(
                    "VISUAL_STRUCTURE_MECHANISM_AS_LANE",
                    page,
                    "Swimlane structure peers mechanism modules with business chains.",
                    "Keep business chains as lanes; attach 隔离/降级 as controls on those lanes.",
                    evidence=business_hits + mechanism_hits,
                    severity="warning",
                )
            )

    return issues


def _constraint_is_declared_subject(
    page: ScriptPage,
    contract: dict[str, object],
) -> bool:
    """Return whether constraints are the core message's primary subject.

    A title or page mission may mention scope while the core meaning remains a
    business design, target, or method.  Such secondary limits must not become a
    peer on-screen module.  Only an explicit constraint role or a constraint in
    the leading clause of the approved core message opts in.
    """

    role = str(contract.get("argument_role") or "").strip().lower()
    if role in CONSTRAINT_ARGUMENT_ROLES:
        return True
    core_message = str(
        contract.get("core_message")
        or contract.get("main_message")
        or page.core_message
        or ""
    ).strip()
    leading_clause = re.split(r"[。；;！？!?]", core_message, maxsplit=1)[0]
    return any(term in leading_clause for term in CONSTRAINT_THEME_TERMS)


def _onscreen_constraint_module_hits(page: ScriptPage) -> tuple[str, ...]:
    """Find explicit constraint modules or labels, not incidental prose mentions."""

    hits: set[str] = set()
    for title in page.module_titles:
        for term in ONSCREEN_CONSTRAINT_MODULE_TERMS:
            if term in title:
                hits.add(term)
    for line in page.onscreen_text.splitlines():
        label = re.sub(r"^\s*[-*]\s*", "", line).strip()
        label = label.strip("* ").strip()
        label = re.sub(r"^\d{1,2}\s*[|｜]\s*", "", label)
        for term in ONSCREEN_CONSTRAINT_MODULE_TERMS:
            if label == term or label.startswith((f"{term}：", f"{term}:")):
                hits.add(term)
    return tuple(sorted(hits))


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
        issues.extend(_visual_structure_judgment_issues(page))
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
    intent = page.visual_intent_type.strip()
    if page.page_type == "content" and page.module_titles:
        path_like = intent in PATH_LIKE_INTENT_TYPES or any(
            marker in visual
            for marker in ("贯穿主链", "阶段推进", "路径", "闭环", "回流")
        )
        layer_like_intent = intent in LAYER_LIKE_INTENT_TYPES or any(
            marker in visual for marker in ("分层剖面", "分层", "横向治理")
        )
        has_order = any(signal in page.onscreen_text for signal in ORDER_SIGNALS) or bool(
            re.search(r"(?m)^\s*\*\*\d{2}｜", page.onscreen_text)
        )
        has_layer = any(signal in page.onscreen_text for signal in LAYER_SIGNALS) or bool(
            re.search(r"(?m)^\s*\*\*\d{2}｜", page.onscreen_text)
        )
        if path_like and len(page.module_titles) >= 2 and not has_order:
            issues.append(
                _issue(
                    "ONSCREEN_RELATION_ISOMORPHISM",
                    page,
                    "Path-like page relation is not readable from on-screen module order.",
                    "Number modules (01｜…), add →/随之 signals, or change visual_intent_type.",
                    evidence=(intent or visual[:40], *page.module_titles[:4]),
                    severity="warning",
                )
            )
        if layer_like_intent and len(page.module_titles) >= 2 and not has_layer:
            issues.append(
                _issue(
                    "ONSCREEN_RELATION_ISOMORPHISM",
                    page,
                    "Layered page relation is not readable from on-screen hierarchy cues.",
                    "Keep numbered layer modules or explicit 层/支撑 signals aligned with 视觉结构.",
                    evidence=(intent or visual[:40], *page.module_titles[:4]),
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
    visible_nodes = max(len(page.module_titles), numbered_nodes)
    grouped = any(signal in page.onscreen_text for signal in LAYER_SIGNALS)
    if visible_nodes > 5 and not grouped:
        issues.append(
            _issue(
                "VISIBLE_NODE_OVERLOAD",
                page,
                "More than five visible primary nodes appear without explicit grouping.",
                "Group the nodes under a small number of stages or layers, or return to the Outline if they answer independent questions.",
                evidence=(f"nodes={visible_nodes}",),
                severity="error" if visible_nodes >= 8 else "warning",
            )
        )
    return issues


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
                "Use a supported judgment_role or explicitly set locked/semantic_only.",
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
                "Consider semantic_only so the judgment governs composition without becoming a second title.",
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


FINAL_BATCH_HEADING_RE = re.compile(
    r"^#\s+第\s*\d+\s*[—\-~～－]+\s*\d+\s*页"
)
FINAL_DRAFT_HEADING_RE = re.compile(r"^#\s+.*草稿")
FINAL_BATCH_META_RE = re.compile(r"^>\s*批次\s*[：:]")
FINAL_DRAFT_STATUS_RE = re.compile(r"^>\s*状态\s*[：:].*草稿")
FINAL_PENDING_AUDIT_RE = re.compile(
    r"待\s*`?script-audit`?\s*通过后审稿"
)


def is_final_script_path(path: Path) -> bool:
    """True when the path is under workbench/scripts/final/."""

    parts = [part.lower() for part in Path(path).parts]
    try:
        scripts_index = parts.index("scripts")
    except ValueError:
        return False
    return scripts_index + 1 < len(parts) and parts[scripts_index + 1] == "final"


def audit_final_manuscript_form(text: str) -> list[ScriptQualityIssue]:
    """Reject draft/batch wording that must not appear in final manuscripts."""

    evidence: list[str] = []
    for index, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        banner_hit = (
            FINAL_DRAFT_HEADING_RE.match(line)
            or FINAL_BATCH_HEADING_RE.match(line)
            or FINAL_BATCH_META_RE.match(line)
            or FINAL_DRAFT_STATUS_RE.match(line)
            or FINAL_PENDING_AUDIT_RE.search(line)
        )
        # Only reject manuscript-state banners. Business prose may legitimately
        # contain terms such as “账单草稿” or “处理批次”.
        if banner_hit:
            evidence.append(f"L{index}:{line[:100]}")
    if not evidence:
        return []
    return [
        ScriptQualityIssue(
            code="FINAL_MANUSCRIPT_DRAFT_BANNER",
            severity="error",
            message=(
                "Final manuscript must not contain draft/batch status banners."
            ),
            pages=(),
            evidence=tuple(evidence[:12]),
            suggested_action=(
                "Run `python -m cyberppt assemble-final-script <project>` or "
                "remove every draft/batch status label before auditing files under "
                "workbench/scripts/final/."
            ),
        )
    ]


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
            expected_judgment = str(
                contract.get("onscreen_conclusion")
                or contract.get("onscreen_judgment")
                or ""
            ).strip()
            visible_judgment_required = bool(expected_judgment)
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
                )
            )
            issues.extend(_source_consumption_issues(page, contract))
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
                            "Copy the cyberppt-page-contract comment from page-script-authoring-input.",
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
    return issues

"""Deterministic PPT script parsing and quality contracts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from cyberppt.paths import repo_path
from cyberppt.onscreen_expression import (
    audit_expression_balance,
    expression_requires_action_headings,
    resolve_onscreen_expression,
)
from cyberppt.semantic_expression_models import load_expression_models

# Fallback values, used only if vendor/skills/ppt-script/config/rules.yaml is
# missing or malformed (e.g. a checkout without the vendor/ skill content, or
# PyYAML unavailable) so this module still works standalone. When the YAML
# loads successfully these are overridden by _load_module_ceiling() below —
# the YAML is the single source of truth; these are not a second copy of the
# policy to keep in sync by hand.
_MODULE_CEILING_FALLBACK = 5
_RULES_YAML_PATH = repo_path("vendor", "skills", "ppt-script", "config", "rules.yaml")


def _load_module_ceiling() -> int:
    """Read page_composition.onscreen_zones.modules.max from rules.yaml.

    This threshold used to be duplicated as a bare literal (``> 5``) at each
    check site, disconnected from vendor/skills/ppt-script/config/rules.yaml's
    documented ``modules.max`` — editing the YAML had no runtime effect, so
    the two could silently drift. Load it once at import time instead.
    """

    try:
        import yaml  # local import: keep PyYAML optional for this module
    except ImportError:
        return _MODULE_CEILING_FALLBACK
    try:
        config = yaml.safe_load(_RULES_YAML_PATH.read_text(encoding="utf-8"))
        value = config["page_composition"]["onscreen_zones"]["modules"]["max"]
        return int(value)
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError):
        return _MODULE_CEILING_FALLBACK


MODULE_CEILING = _load_module_ceiling()


PAGE_HEADING_RE = re.compile(
    r"^##\s+(?:(?:第(\d+)页[：:](.+?)|P(\d+)\s+(.+?)))\s*$",
    re.MULTILINE,
)
FIELD_RE = re.compile(r"^-\s*([^：:\n]+)[：:]\s*(.*)$")
HEADING_FIELD_RE = re.compile(r"^###\s+(.+?)\s*$")
NON_ONSCREEN_VISUAL_HEADING_RE = re.compile(r"^【视觉结构[，,]\s*不上屏】\s*$")

# Current project scripts also use Markdown section headings for the page
# contract fields. Keep the legacy ``- 字段：内容`` parser, but normalize these
# headings so the drawable 上屏文字 block is not silently dropped.
HEADING_FIELD_ALIASES = {
    "完整文字稿": "完整文字稿",
    "完整文字稿段落映射": "完整文字稿段落映射",
    "文字稿取舍说明": "文字稿取舍说明",
    "证据映射": "证据映射",
    "证据": "证据",
    "边界依据": "边界依据",
    "边界": "边界",
    "上屏文字": "上屏文字",
    "上屏结论": "上屏结论",
    "视觉意图类型": "视觉意图类型",
    "视觉证明": "视觉证明",
    # "逻辑骨架" and "视觉意图与生图构图" are legacy heading names some
    # generators use in place of a real 视觉结构 section; both alias onto
    # the canonical field. When a page uses the canonical "视觉结构（不上屏）"
    # heading directly (added to the page-composition contract so a genuine
    # composition field always exists — see generate_script_final.py's
    # 视觉结构 requirement), it must ALSO map onto the same key, or
    # _heading_field_name returns None for it, the heading is invisible as a
    # field boundary, and its content silently merges with whatever field
    # preceded it (observed: 逻辑骨架 + 视觉结构 + the page-contract HTML
    # comment all concatenating into one blob).
    "逻辑骨架": "视觉结构",
    "视觉结构": "视觉结构",
    "视觉意图与生图构图": "视觉结构",
    "演讲者备注": "演讲者备注",
}

# Peer-level page-contract fields.  A ``- label: value`` line inside the
# drawable 上屏文字 block is ambiguous: most such lines are visible module
# copy, while these names start a new backend/contract field.  Keep the list
# explicit so ordinary module labels remain drawable without allowing a
# backend field to be swallowed by 上屏文字.
PAGE_CONTRACT_FIELDS = {
    "页面类型",
    "页面标题",
    "副标题",
    "核心结论",
    "主判断",
    "完整文字稿",
    "完整文字稿段落映射",
    "文字稿取舍说明",
    "证据映射",
    "上屏文字",
    "上屏模块清单",
    "上屏顶层模块清单",
    "上屏结论",
    "判断角色",
    "上屏结论模式",
    "视觉意图类型",
    "视觉载体",
    "生图锁定文字",
    "版式母题",
    "场景角色",
    "视觉证明",
    "证据",
    "边界依据",
    "边界",
    "视觉结构",
    "讲解提示",
    "演讲者备注",
}


def _heading_field_name(raw: str) -> str | None:
    """Map a Markdown page-contract heading to the canonical field name."""

    name = re.sub(r"[（(].*?[）)]\s*$", "", raw.strip()).strip()
    return HEADING_FIELD_ALIASES.get(name)
MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*\s*$")
INLINE_MODULE_RE = re.compile(r"^\s*\*\*(.+?)\*\*(?:\s*[|｜:：].*)?\s*$")
# Source Truth identifiers are historically S015/S0410 and current Stage 01
# projects may use ST003/ST0410. Match both complete forms so a valid formal
# Source Truth ID is not reported as missing merely because its namespace is
# explicit.
SOURCE_RE = re.compile(r"ST?\d{3,4}(?!\d)")
SOURCE_RANGE_RE = re.compile(
    r"(?P<prefix>ST?)?(?P<start>\d{3,4})\s*[—–-]\s*"
    r"(?P<end_prefix>ST?)(?P<end>\d{3,4})"
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
# A mechanically authored page often uses the same editorial buckets and
# generic label sequence regardless of its business topic. Individual words
# such as "判断" or "对象" are legitimate in a specific sentence, so this rule
# intentionally requires the repeated combined pattern rather than banning
# any one word.
GENERIC_ONSCREEN_GROUP_LABELS = frozenset(("关键判断", "业务事实", "运营要点"))
GENERIC_ONSCREEN_DETAIL_LABELS = frozenset(
    ("判断", "事实", "对象", "条件", "动作", "结果", "机制", "衔接", "要求", "依据", "状态", "安排")
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
# ``semantic_only`` remains an ImageGen-facing legacy mode.  The two new
# authoring modes govern Stage 01 script review without changing that consumer.
ONSCREEN_JUDGMENT_MODES = (
    "locked",
    "semantic_only",
    "semantic_alignment",
    "hidden",
)
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
    raw_onscreen_text: str = ""
    top_level_module_titles: tuple[str, ...] = ()
    subtitle: str = ""
    visual_proof: str = ""
    onscreen_judgment: str = ""
    judgment_role: str = ""
    onscreen_judgment_mode: str = ""
    visual_intent_type: str = ""
    visual_carrier: str = ""
    image_locked_text: str = ""
    onscreen_expression_form: str = ""
    layout_motif: str = ""
    scene_role: str = ""
    field_order: tuple[str, ...] = ()
    coaching_tip: str = ""
    speaker_notes: str = ""
    contract_receipt: dict[str, object] | None = None
    prose_paragraph_map: tuple[tuple[tuple[str, ...], str], ...] = ()

    def __post_init__(self) -> None:
        # Callers that predate the top-level/nested distinction (hand-built
        # ScriptPage fixtures, tests) only ever set ``module_titles``. Treat
        # every module as top-level for them, preserving prior behavior.
        # ``parse_script_markdown`` explicitly passes the indentation-aware
        # value, which is the only place this can legitimately differ.
        if not self.top_level_module_titles and self.module_titles:
            object.__setattr__(
                self, "top_level_module_titles", self.module_titles
            )

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
            int(match.group(1) or match.group(3)),
            (match.group(2) or match.group(4)).strip(),
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
        heading_match = HEADING_FIELD_RE.match(raw_line.strip())
        if heading_match:
            heading_field = _heading_field_name(heading_match.group(1))
            if heading_field:
                active = heading_field
                blocks[active] = []
                continue
            # Module headings inside 上屏文字 are content, not a new field;
            # leave ``active`` unchanged so their following bullets remain
            # drawable text, but preserve the heading itself so downstream
            # module-title extraction can retain the reading hierarchy.
            if active == "上屏文字":
                blocks[active].append(raw_line.rstrip())
            continue
        match = FIELD_RE.match(raw_line)
        if match:
            field_name = match.group(1).strip()
            if active == "上屏文字" and field_name not in PAGE_CONTRACT_FIELDS:
                # Module bullets such as ``- 政策牵引：...`` belong to the
                # drawable text layer; they are not peer-level contract fields.
                blocks[active].append(raw_line.rstrip())
                continue
            active = field_name
            blocks[active] = [match.group(2).strip()]
        elif active:
            blocks[active].append(raw_line.rstrip())
    return {key: "\n".join(lines).strip() for key, lines in blocks.items()}


def _source_refs(text: str) -> tuple[str, ...]:
    """Extract explicit Source IDs and expand inclusive S/ST ranges.

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
        prefix = match.group("prefix") or match.group("end_prefix")
        if prefix != match.group("end_prefix"):
            continue
        start = int(match.group("start"))
        end = int(match.group("end"))
        if end < start or end - start > 1000:
            continue
        width = max(len(match.group("start")), len(match.group("end")))
        refs.extend(
            f"{prefix}{number:0{width}d}" for number in range(start, end + 1)
        )
    return tuple(dict.fromkeys(refs))


def _parse_prose_paragraph_map(text: str) -> tuple[tuple[tuple[str, ...], str], ...]:
    """Parse one off-screen provenance entry for each full-prose paragraph."""

    result: list[tuple[tuple[str, ...], str]] = []
    for raw in (text or "").splitlines():
        line = re.sub(r"^\s*(?:[-*]\s*)?", "", raw).strip()
        if not line:
            continue
        refs_text, marker, reason = line.partition("｜合并理由：")
        refs = _source_refs(refs_text)
        if refs:
            result.append((refs, reason.strip() if marker else ""))
    return tuple(result)


def _field_order(body: str) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw_line in body.splitlines():
        if NON_ONSCREEN_VISUAL_HEADING_RE.match(raw_line.strip()):
            ordered.append("视觉结构")
            continue
        heading_match = HEADING_FIELD_RE.match(raw_line.strip())
        if heading_match:
            heading_field = _heading_field_name(heading_match.group(1))
            if heading_field:
                ordered.append(heading_field)
            continue
        match = FIELD_RE.match(raw_line)
        if match:
            field_name = match.group(1).strip()
            if field_name in PAGE_CONTRACT_FIELDS:
                ordered.append(field_name)
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

    # Accept both a bare Markdown heading and the repository's readable
    # ``- **小标题**`` list form.
    candidate = re.sub(r"^\s*-\s+", "", line)
    match = MODULE_RE.match(candidate) or INLINE_MODULE_RE.match(candidate)
    if match:
        return match.group(1).strip()
    # Canonical v3 on-screen text is plain text, not Markdown.  A module is
    # represented as ``label：body`` or as a short standalone group label;
    # indentation carries hierarchy.  Keep legacy Markdown recognition above
    # for migration diagnostics, but do not require it for module extraction.
    plain = candidate.strip()
    if not plain:
        return None
    if "：" in plain or ":" in plain:
        label = re.split(r"[：:]", plain, maxsplit=1)[0].strip()
        return label or None
    if len(plain) <= 28 and not re.search(r"[。；;！？!?]$", plain):
        return plain
    return None


def audience_facing_group_label(label: str) -> str:
    """Remove authoring-only structural markers from a visible group label.

    Labels such as ``第1行｜...`` are layout/debug coordinates, not audience
    copy.  Strip them centrally so every script generator benefits, regardless
    of the source project.
    """

    value = str(label or "").strip()
    value = re.sub(
        r"^第\s*(?:[一二三四五六七八九十]+|\d+|[Xx])\s*行\s*[｜|:]\s*",
        "",
        value,
    )
    value = re.sub(r"(?:一|二|两|三|四|五|六|七|八|九|十|\d+)个层面$", "", value)
    value = re.sub(r"(控制链|权利对象)层面$", r"\1", value)
    if value == "四个维度分别选择":
        value = "交付维度选择"
    return value.strip(" ：:")


def strip_authoring_group_marker(line: str) -> str:
    """Remove authoring-only row markers while preserving line indentation.

    Final scripts may contain layout coordinates such as ``第1行｜...`` or
    ``第X行｜...``.  They are useful to an author but are not audience-facing
    copy and must never be sent to ImageGen as visible text.
    """

    raw = str(line or "")
    match = re.match(r"^(\s*)(.*)$", raw, flags=re.S)
    if not match:
        return raw
    indent, body = match.groups()
    cleaned = audience_facing_group_label(body)
    return indent + cleaned if cleaned != body else raw


def _line_indent(line: str) -> int:
    """Return leading-space indentation for relative module hierarchy."""

    return len(line) - len(line.lstrip(" "))


_ACTOR_LABEL_RE = re.compile(
    r"(?:单位|主体|资源方|需求方|供给方|模型(?:算法)?方|服务方|实施方|运营方|"
    r"合作方|合作伙伴|机构|企业|院所|高校|客户)$"
)
_ACTOR_DUTY_LABEL_RE = re.compile(
    r"(?:合作伙伴|需求单位|资源方|需求方|供给方|模型(?:算法)?方|"
    r"服务方|实施方|运营方|合作方|机构|企业|院所|高校|客户|"
    r"[一-鿿]{1,8}(?:公司|集团|协会|联合会|联))"
)
_ACTOR_PARENT_RE = re.compile(r"(?:参与主体|合作主体|主体类型|参与方|合作伙伴|角色|服务对象)$")
_NON_ACTOR_PARENT_RE = re.compile(r"(?:建设|平台|载体|机制|路径|流程|环节|内容|目标|任务)$")


def _onscreen_parent_child_role_mismatches(text: str) -> tuple[str, ...]:
    """Reject false hierarchy caused by nesting actors under a business item.

    Indentation means an actual parent-child taxonomy. It must not be used as
    a convenient way to retain a second semantic dimension. For example,
    ``协同载体建设`` is one construction item; demand/resource/model/service
    parties are participants in that item, not its child items.
    """

    nodes: list[tuple[str, int]] = []
    for line in text.splitlines():
        title = _module_title(line)
        if title is not None:
            nodes.append((title, _line_indent(line)))
    mismatches: list[str] = []
    for index, (parent, indent) in enumerate(nodes):
        descendants: list[tuple[str, int]] = []
        for title, child_indent in nodes[index + 1 :]:
            if child_indent <= indent:
                break
            descendants.append((title, child_indent))
        direct_indent = min((child_indent for _, child_indent in descendants), default=-1)
        children = [title for title, child_indent in descendants if child_indent == direct_indent]
        direct_actor_children = [child for child in children if _ACTOR_LABEL_RE.search(child)]
        if (
            len(direct_actor_children) >= 2
            and _NON_ACTOR_PARENT_RE.search(parent)
            and not _ACTOR_PARENT_RE.search(parent)
        ):
            mismatches.append(f"{parent} -> {', '.join(direct_actor_children[:4])}")
    return tuple(mismatches)


_SUBORDINATE_DETAIL_RE = re.compile(
    r"^[^：:\n]{1,14}[：:]\s*(?:随着|通过|根据|基于|围绕|面向|依托|在(?:.+?条件下|.+?基础上))"
)
_SEMANTIC_LINE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("attribute", re.compile(r"(?:是|属于|定位为|覆盖|包括|构成)")),
    ("change", re.compile(r"(?:加快|深化|提升|增长|变化|转型|演进)")),
    ("demand", re.compile(r"(?:需要|依赖|要求|关注)")),
    ("gap", re.compile(r"(?:尚未|不足|缺少|分散|不统一|受阻|难以)")),
    ("response", re.compile(r"(?:建立|建设|组织|衔接|支持|形成|降低|补齐)")),
)


def _onscreen_subordinate_fragments(text: str) -> tuple[str, ...]:
    """Find authoring labels followed by a detached subordinate phrase."""

    return tuple(
        line.strip()
        for line in text.splitlines()
        if _SUBORDINATE_DETAIL_RE.search(line.strip())
    )


def _semantic_line_role(text: str) -> str:
    # A construction noun inside an explicit trend (建设加快) is a change,
    # not a response.  Resolve high-signal states before broader action verbs.
    if re.search(r"(?:加快|深化|提升|增长|变化|转型|演进)", text):
        return "change"
    if re.search(r"(?:尚未|不足|缺少|分散|不统一|受阻|难以)", text):
        return "gap"
    hits = [name for name, pattern in _SEMANTIC_LINE_PATTERNS if pattern.search(text)]
    return hits[0] if len(hits) == 1 else ""


def _onscreen_false_parallel_semantics(text: str) -> tuple[str, ...]:
    """Flag sibling lists that mix distinct argument functions.

    Indentation is a semantic assertion.  When three or more direct children
    mix attributes, changes, demands, gaps, or responses, they cannot be
    rendered as one peer list without an explicit relation rewrite.
    """

    lines = text.splitlines()
    nodes = [
        (index, _line_indent(line), _module_title(line) or "")
        for index, line in enumerate(lines)
        if line.strip() and _module_title(line) is not None
    ]
    mismatches: list[str] = []
    for position, (start, indent, parent) in enumerate(nodes):
        end = len(lines)
        for next_start, next_indent, _ in nodes[position + 1 :]:
            if next_indent <= indent:
                end = next_start
                break
        child_lines = [
            line.strip()
            for line in lines[start + 1 : end]
            if line.strip() and _line_indent(line) > indent
        ]
        if len(child_lines) < 3:
            continue
        # A group of named actors remains one semantic dimension even when
        # their distinct duties contain words that also occur in demand or
        # response prose.  Classify the parent-child taxonomy before applying
        # keyword-based argument-role heuristics.
        actor_children = [
            line
            for line in child_lines
            if _ACTOR_DUTY_LABEL_RE.search(re.split(r"[：:]", line, maxsplit=1)[0])
        ]
        if (
            len(actor_children) == len(child_lines)
            and re.search(r"(?:主体|参与方|角色|职责|分工|协同运行)", parent)
        ):
            continue
        # Named alternatives under an explicit option taxonomy (for example,
        # four cooperation methods with their respective applicability
        # conditions) are peers by business type.  Words such as "需要" or
        # "形成" inside the descriptions explain each option; they do not
        # change the siblings into mixed argument roles.
        option_labels = [
            re.split(r"[：:]", line, maxsplit=1)[0].strip()
            for line in child_lines
            if re.search(r"[：:]", line)
        ]
        if (
            len(option_labels) == len(child_lines)
            and len(set(option_labels)) == len(option_labels)
            and all(1 <= len(label) <= 12 for label in option_labels)
            and re.search(r"(?:方式|路径|类型|模式|方案)", parent)
        ):
            continue
        roles = [_semantic_line_role(line) for line in child_lines]
        known = {role for role in roles if role}
        if len(known) >= 2:
            rendered = ", ".join(
                f"{role}:{line}" for role, line in zip(roles, child_lines) if role
            )
            mismatches.append(f"{parent} -> {rendered[:240]}")
    return tuple(mismatches)


def _json_string_list(value: str) -> tuple[str, ...]:
    if not value.strip():
        return ()
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return ()
    if not isinstance(payload, list):
        return ()
    return tuple(str(item).strip() for item in payload if str(item).strip())


def load_page_contract_sidecar(script_path: Path) -> dict[str, dict[str, object]]:
    """Load and verify the page-contract sidecar next to a final script.

    Missing sidecars are allowed for legacy scripts.  A present sidecar is a
    formal binding artifact and therefore fails closed when its script hash or
    shape is invalid.
    """

    script_path = script_path.expanduser().resolve()
    sidecar = script_path.with_name("page-contracts.json")
    if not sidecar.is_file():
        return {}
    payload = json.loads(sidecar.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("schema") != "cyberppt.page_contracts.v1":
        raise ValueError(f"invalid page-contract sidecar: {sidecar}")
    if payload.get("script") != script_path.name:
        raise ValueError(f"page-contract sidecar targets another script: {sidecar}")
    expected_script = hashlib.sha256(script_path.read_bytes()).hexdigest()
    if str(payload.get("script_sha256") or "").casefold() != expected_script.casefold():
        raise ValueError(f"page-contract sidecar is stale for script: {sidecar}")
    raw_pages = payload.get("pages")
    if not isinstance(raw_pages, dict):
        raise ValueError(f"page-contract sidecar pages must be an object: {sidecar}")
    pages: dict[str, dict[str, object]] = {}
    for page_id, receipt in raw_pages.items():
        normalized_page_id = str(page_id)
        if not re.fullmatch(r"p\d{2,}", normalized_page_id):
            raise ValueError(f"invalid page id in page-contract sidecar: {page_id}")
        if not isinstance(receipt, dict):
            raise ValueError(f"invalid receipt for {normalized_page_id}: {sidecar}")
        if receipt.get("page_id") != normalized_page_id:
            raise ValueError(
                f"page-contract receipt id mismatch for {normalized_page_id}: {sidecar}"
            )
        pages[normalized_page_id] = receipt
    return pages


def parse_script_markdown(
    text: str,
    page_contracts: dict[str, dict[str, object]] | None = None,
) -> ScriptDocument:
    pages: list[ScriptPage] = []
    for sequence, heading, body in _page_sections(text):
        fields = _field_blocks(body)
        page_type = _normalize_page_type(fields.get("页面类型", ""))
        onscreen = fields.get("上屏文字", "")
        module_lines: list[tuple[str, int]] = []
        if page_type == "content":
            for line in onscreen.splitlines():
                title = _module_title(line)
                if title is None:
                    continue
                module_lines.append((title, _line_indent(line)))
        modules = tuple(title for title, _ in module_lines)
        # Markdown nested under ``- 上屏文字：`` normally starts with two or
        # four spaces, so absolute column zero is not a valid definition of
        # top level.  The least-indented module on this page is the peer level;
        # only deeper module headings are children.
        base_module_indent = min((indent for _, indent in module_lines), default=0)
        top_level_modules = tuple(
            title for title, indent in module_lines if indent == base_module_indent
        )
        declared_modules = _json_string_list(fields.get("上屏模块清单", ""))
        declared_top_level_modules = _json_string_list(
            fields.get("上屏顶层模块清单", "")
        )
        if declared_modules:
            modules = declared_modules
        if declared_top_level_modules:
            top_level_modules = declared_top_level_modules
        pages.append(
            ScriptPage(
                page_id=f"p{sequence:02d}",
                sequence=sequence,
                heading=heading,
                page_type=page_type,
                title=fields.get("页面标题", heading).strip(),
                subtitle=fields.get("副标题", "").strip(),
                main_message=(
                    fields.get("核心结论")
                    or fields.get("主判断")
                    or fields.get("页面命题", "")
                ).strip(),
                full_prose=fields.get("完整文字稿", "").strip(),
                prose_paragraph_map=_parse_prose_paragraph_map(
                    fields.get("完整文字稿段落映射", "")
                ),
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
                visual_structure=(
                    fields.get("视觉结构", "")
                    .split("<!--", 1)[0]
                    .strip()
                ),
                onscreen_text=onscreen,
                module_titles=modules,
                raw_onscreen_text=onscreen,
                top_level_module_titles=top_level_modules,
                visual_proof=fields.get("视觉证明", "").strip(),
                onscreen_judgment=fields.get("上屏结论", "").strip(),
                judgment_role=fields.get("判断角色", "").strip(),
                onscreen_judgment_mode=fields.get("上屏结论模式", "").strip(),
                visual_intent_type=fields.get("视觉意图类型", "").strip(),
                visual_carrier=fields.get("视觉载体", "").strip(),
                image_locked_text=fields.get("生图锁定文字", "").strip(),
                onscreen_expression_form=fields.get("上屏表达结构", "").strip(),
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
                contract_receipt=(page_contracts or {}).get(f"p{sequence:02d}")
                or extract_page_contract_receipt(body),
            )
        )
    if not pages:
        raise ValueError("script contains no page headings")
    return ScriptDocument(tuple(pages))


def parse_script_path(path: Path) -> ScriptDocument:
    """Parse a script with its verified sidecar, falling back to legacy comments."""

    path = path.expanduser().resolve()
    return parse_script_markdown(
        path.read_text(encoding="utf-8-sig"),
        load_page_contract_sidecar(path),
    )


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
ORDER_SIGNALS = ("①", "②", "③", "④", "⑤", "→", "随后", "依次", "最后一步")
NUMBERED_ORDER_SIGNAL_RE = re.compile(r"(?m)^\s*(?:\*\*)?\d{2}｜")
LOOP_SIGNALS = ("回流", "反馈", "复盘", "闭环", "持续校正")
MATRIX_SIGNALS = ("|---", "×", "矩阵")
LAYER_SIGNALS = ("自下而上", "自上而下", "底座", "贯穿")
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
MECHANISM_LANE_LABEL_RE = re.compile(r"[一-鿿]{1,6}(?:隔离|降级)")
BUSINESS_LANE_LABEL_RE = re.compile(
    r"[一-鿿]{1,8}(?:链路|队列|事务链|事件链|分析链)"
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
SEMANTIC_STRUCTURE_SIGNALS = (
    "主关系",
    "语义焦点",
    "文字归属",
    "支撑",
    "流转",
    "转化",
    "汇聚",
    "分支",
    "依赖",
    "包含",
    "对比",
    "控制",
    "约束",
    "授权",
    "边界",
    "责任",
    "协同",
    "反馈",
    "输入",
    "输出",
    "结果",
    "从属",
)
VISUAL_STRUCTURE_LAYOUT_RECIPE_RES = (
    re.compile(
        r"(?:主视觉|页面|正文区)[^。；;\n]{0,28}"
        r"(?:位于|放在|置于|设置|排列|分为|横跨|占据|占约)"
    ),
    re.compile(
        r"(?:上半部|下半部|顶部|底部|左侧|右侧|中央偏[左右]?|页面中央|"
        r"居中|为视觉中心)"
    ),
    re.compile(
        r"(?:[一二三四五六七八九十\d]+\s*(?:条|行|列|个)?\s*"
        r"(?:横向|纵向)?\s*(?:泳道|卡片|节点|栏|矩阵)|"
        r"(?:横向|纵向)\s*(?:泳道|排列|矩阵|条带|说明条|收束条))"
    ),
    re.compile(r"(?:矩阵筛选|主体泳道|分层剖面|汇聚引擎输出)"),
    re.compile(r"(?:结果区|结论区|说明条|收束条|节奏条|独立横条)"),
    re.compile(
        r"(?:阅读顺序|自左向右扫过|自右向左扫过|自上而下扫过|自下而上扫过)"
    ),
    re.compile(r"(?:左文右图|右文左图|左图右表|左表右图)"),
)
VISUAL_STRUCTURE_MULTIPLE_PRIMARY_RE = re.compile(
    r"(?:第二套|另一套)[^。；;\n]{0,24}(?:流程|主链|结构|结果链|总结链)|"
    r"(?:独立于|脱离)[^。；;\n]{0,24}(?:主关系|主链|业务对象)"
    r"[^。；;\n]{0,16}(?:流程|结果|说明)"
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
ONSCREEN_SOURCE_SPECIFICITY_ERROR_FLOOR = 0.12
ONSCREEN_SEMANTIC_COVERAGE_MIN = 0.22
ONSCREEN_SEMANTIC_COVERAGE_TARGET = 0.28
ONSCREEN_EFFECTIVE_CHARS_MIN = 220
ONSCREEN_SOURCE_ERASURE_PHRASES: tuple[str, ...] = (
    "总体位置",
    "基本方向",
    "必要支撑",
    "相关能力",
    "相关对象",
    "有关事项",
    "开展工作",
    "持续实施",
)
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


def _is_structured_compact_onscreen_layer(
    page: ScriptPage,
    *,
    visible_story_chars: int | None = None,
) -> bool:
    """Return whether concise copy carries an explicit readable hierarchy.

    A single umbrella is valid only because ``module_titles >= 5`` requires
    several subordinate items. Four unrelated short lines therefore cannot
    pass by presenting themselves as structure.
    """

    visible_chars = (
        meaningful_char_count(page.onscreen_judgment + page.onscreen_text)
        if visible_story_chars is None
        else visible_story_chars
    )
    return bool(
        1 <= len(page.top_level_module_titles) <= MODULE_CEILING
        and len(page.module_titles) >= 5
        and visible_chars >= 60
        and not _onscreen_detail_phrase_overages(page.onscreen_text)
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
            60 if structured_compact_layer else onscreen_effective_char_target(page)
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

# Negative-contrast rhetoric spends the reader's attention rebutting a
# discarded frame before stating the actual claim. Formal scripts must state
# the subject, action, condition, and result directly instead. Keep the
# patterns explicit and narrow enough not to treat ordinary terms such as
# “非结构化数据” or “不仅……而且……” as negative contrast.
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

# These terms signal a page whose lead has been framed around a limitation or
# discarded state. They are not prohibited as source-supported conditions in
# ordinary prose; the quality gate only rejects them when they occupy a page's
# foreground positions (title, judgment, or peer on-screen heading).
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
)

# Backend relationship labels must not appear in 上屏文字. They belong in
# 完整文字稿 / 讲解提示 and are forwarded to ImageGen as off-screen semantics.
ONSCREEN_RELATION_META_LABELS: tuple[str, ...] = (
    "业务含义",
    "业务关系",
    "背景关系",
    "层间衔接",
    "共同依据",
    "责任落实",
    "追溯关系",
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


# Backend/process self-talk: the author narrating their own authoring or
# verification process, rather than reader-facing business content. Unlike
# ONSCREEN_RELATION_META_LABELS (a legitimate relationship word used as an
# on-screen module label), these phrases have no legitimate on-screen
# meaning at all — a real reader never needs to see "verify before formal
# citation" or "per this structure" — so a bare substring match anywhere in
# the on-screen text is appropriate here, unlike the hedge-sensitive checks
# elsewhere in this file (SCOPE_TERMS/IMPLEMENTATION_TERMS) where the same
# word can legitimately appear in a non-violating context.
ONSCREEN_BACKEND_META_PHRASES: tuple[str, ...] = (
    "定位关系",
    "共同归属",
    "体系关系",
    "页面作用",
    "结构说明",
    "状态说明",
    "目标属性",
    "正式引用前核验",
    "待核验",
    "须核验",
    "仅后台",
    "逻辑顺序",
    "非并列",
    "阅读路径",
    "内容关系",
    "论证组织",
    "材料把",
    "这里按",
    "按这个结构",
    "供审稿",
    "写作说明",
    "两个层面",
    "三个层面",
    "四个维度分别选择",
    "控制链层面",
    "权利对象层面",
)

# Authoring/layout instructions belong to ``视觉结构（不上屏）`` (or another
# backend field), not to the reader-facing ``上屏文字`` block.  Keep this list
# deliberately narrow: a business label such as ``四种合作方式`` or ``五个
# 环节`` is valid visible copy, while ``四行选择矩阵`` and ``阅读顺序`` are
# instructions to the compositor rather than content for the audience.
ONSCREEN_LAYOUT_META_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:[一二三四五六七八九十百\d]+)\s*行\s*(?:选择)?\s*矩阵(?:表)?\s*$"),
    re.compile(r"^\s*(?:主视觉|视觉中心|阅读顺序|构图说明|版式说明|布局说明)\s*[：:]"),
    re.compile(
        r"^\s*(?:以|采用|按).{0,24}(?:矩阵|泳道|色块|主链|收束条|节点链)"
        r".{0,24}(?:呈现|构成|排列|阅读|收束)"
    ),
    re.compile(r"^\s*第\s*(?:[一二三四五六七八九十百\d]+|[Xx])\s*行\s*[｜|：:]"),
)

# Detail lines should be short phrases or short sentences.  These thresholds
# count meaningful Chinese/Latin/numeric characters in the text after the
# first label separator, so punctuation and a concise label do not hide a
# paragraph.  The advisory band lets the author see the problem early; the
# hard band blocks script approval until the detail is split or shortened.
# Formal on-screen copy is phrase-led by default.  A page may carry several
# short, same-topic items, but no individual labelled detail may become a
# paragraph.  Keep warning and error thresholds identical so >30 chars is a
# blocking authoring defect rather than an advisory that survives to Stage 02.
ONSCREEN_DETAIL_PHRASE_WARNING_CHARS = 30
ONSCREEN_DETAIL_PHRASE_ERROR_CHARS = 60


def _onscreen_backend_meta_hits(text: str) -> tuple[str, ...]:
    return tuple(phrase for phrase in ONSCREEN_BACKEND_META_PHRASES if phrase in text)


def _onscreen_layout_meta_hits(text: str) -> tuple[str, ...]:
    """Return visible lines that are compositor instructions, not slide copy."""

    hits: list[str] = []
    for raw in text.splitlines():
        raw_line = re.sub(r"^[-*+•]\s*", "", raw.strip())
        if re.search(r"^第\s*(?:[一二三四五六七八九十百\d]+|[Xx])\s*行\s*[｜|：:]", raw_line):
            hits.append(raw_line)
        line = strip_authoring_group_marker(raw).strip()
        line = re.sub(r"^[-*+•]\s*", "", line).strip()
        if not line:
            continue
        if any(pattern.search(line) for pattern in ONSCREEN_LAYOUT_META_PATTERNS):
            hits.append(line)
    return tuple(dict.fromkeys(hits))


def _onscreen_detail_phrase_overages(text: str) -> tuple[tuple[str, int], ...]:
    """Return ``(line, body_chars)`` for overlong labelled detail lines.

    Module headings and standalone labels are intentionally ignored.  A line
    becomes a detail candidate only when it contains a label/value separator;
    this keeps the rule focused on the sentence that would otherwise become a
    paragraph inside a card, lane, or matrix cell.
    """

    overages: list[tuple[str, int]] = []
    for raw in text.splitlines():
        raw_indent = len(raw) - len(raw.lstrip(" "))
        had_bullet = bool(re.match(r"^\s*[-*+•]\s+", raw))
        line = strip_authoring_group_marker(raw).strip()
        line = re.sub(r"^[-*+•]\s*", "", line).strip()
        if not line or line.startswith("#") or MODULE_RE.match(line):
            continue
        parts = re.split(r"[：:]", line, maxsplit=1)
        if len(parts) == 2 and parts[1].strip():
            body = parts[1]
        elif raw_indent > 0 or had_bullet:
            # A nested/bulleted line without a label is still a detail line;
            # the author should give it a short functional label rather than
            # hiding a paragraph behind a list marker.
            body = line
        else:
            continue
        body_chars = meaningful_char_count(body)
        if body_chars > ONSCREEN_DETAIL_PHRASE_WARNING_CHARS:
            overages.append((line, body_chars))
    return tuple(overages)


def assert_imagegen_onscreen_readiness(
    document: ScriptDocument,
    page_numbers: set[int],
) -> None:
    """Block ImageGen when a requested page still contains paragraph-like copy."""

    failures: list[str] = []
    for page in document.pages:
        if page.page_type != "content" or int(page.page_id[1:]) not in page_numbers:
            continue
        for line, chars in _onscreen_detail_phrase_overages(page.onscreen_text):
            failures.append(f"{page.page_id.upper()} {chars}字：{line}")
    if failures:
        raise ValueError(
            "requested pages contain paragraph-like on-screen copy; compress each "
            "module into short parallel items before ImageGen:\n" + "\n".join(failures)
        )


# A module heading is a grouping contract, not a bag of nearby nouns.  These
# semantic heads describe different organizing questions and therefore cannot
# be joined as one peer heading unless an explicit parent concept owns both.
_COMPOUND_HEADING_INCOMPATIBLE_HEADS: frozenset[frozenset[str]] = frozenset(
    {
        frozenset(("原则", "方式")),
        frozenset(("等级", "责任")),
        frozenset(("分类", "构成")),
        frozenset(("关系", "比例")),
        frozenset(("对象", "边界")),
    }
)
_COMPOUND_HEADING_HEADS: tuple[str, ...] = (
    "原则", "方式", "等级", "责任", "分类", "构成", "关系", "比例", "对象", "边界"
)
_COMPOUND_PARENT_DOMAINS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("报价", "计价", "收费"), ("服务", "分类", "报价", "价格", "构成", "计价", "费用")),
    (("分配", "分润", "结算"), ("价格", "分配", "比例", "分润", "结算", "收益", "关系")),
)


def _compound_module_heading_hits(titles: tuple[str, ...]) -> tuple[str, ...]:
    """Return headings that merge peer semantic dimensions.

    ``父概念——子维度A与子维度B`` is allowed only when both children belong
    to the parent's business domain.  Without that owning parent, known
    incompatible semantic heads are a blocking compound grouping.
    """
    hits: list[str] = []
    for raw_title in titles:
        title = re.sub(r"^\s*(?:[一二三四五六七八九十]+[、.]|\d+[、.｜|])\s*", "", raw_title).strip()
        parent = ""
        detail = title
        parent_match = re.split(r"\s*(?:——|—|--|：|:)\s*", title, maxsplit=1)
        if len(parent_match) == 2:
            parent, detail = parent_match
        detail = re.sub(r"(?:两个|三个|四个)层面\s*$", "", detail).strip()
        children = [part.strip() for part in re.split(r"[与和及]", detail) if part.strip()]
        if len(children) != 2:
            continue
        heads = {
            head
            for child in children
            for head in _COMPOUND_HEADING_HEADS
            if child.endswith(head)
        }
        incompatible = frozenset(heads) in _COMPOUND_HEADING_INCOMPATIBLE_HEADS
        if not incompatible:
            continue
        if parent:
            parent_owns_children = any(
                any(token in parent for token in parent_terms)
                and all(any(term in child for term in child_terms) for child in children)
                for parent_terms, child_terms in _COMPOUND_PARENT_DOMAINS
            )
            if parent_owns_children:
                continue
        hits.append(raw_title)
    return tuple(dict.fromkeys(hits))


def _onscreen_heading_candidates(page: ScriptPage) -> tuple[str, ...]:
    candidates = list(page.module_titles)
    for raw in page.onscreen_text.splitlines():
        line = re.sub(r"^\s*[-*+]\s*", "", raw).replace("**", "").strip()
        if (
            line
            and len(line) <= 40
            and not re.search(r"[：:。；;！？!?]", line)
        ):
            candidates.append(line)
    return tuple(dict.fromkeys(candidates))


_ONSCREEN_MARKDOWN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("heading", re.compile(r"(?m)^\s*#{1,6}\s+")),
    ("bold", re.compile(r"\*\*[^*\n]+\*\*")),
    ("bullet", re.compile(r"(?m)^\s*[-*+]\s+")),
)


def _onscreen_markdown_hits(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in _ONSCREEN_MARKDOWN_PATTERNS if pattern.search(text))


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
    return tuple(term for term in _NEGATIVE_FOREGROUND_TERMS if term in text)


def _leading_negative_foreground_terms(text: str) -> tuple[str, ...]:
    """Apply foreground screening to the claim lead, not trailing conditions."""

    lead = re.sub(r"\s+", "", text)[:28]
    return _negative_foreground_terms(lead)


def _opening_negative_foreground_terms(text: str) -> tuple[str, ...]:
    """Find negative framing in a page's opening claim, not later caveats."""

    opening = re.sub(r"\s+", "", text)[:72]
    return _negative_foreground_terms(opening)


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


def _prohibited_colloquial_hits(text: str) -> tuple[str, ...]:
    return tuple(pattern for pattern in _PROHIBITED_COLLOQUIAL_PATTERNS if pattern in text)


def _unlabeled_onscreen_bullets(text: str) -> tuple[str, ...]:
    lines = text.splitlines()
    hits = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("-"):
            continue
        # A conclusion-first item has a short label immediately after the
        # bullet marker.  A colon buried in the supporting sentence does not
        # satisfy the contract.
        has_prefix = bool(re.match(r"^-\s*[^\s：:，,。；;、]{2,24}[：:]", stripped))
        if has_prefix:
            continue
        # A bullet with no colon can also be a genuine group heading — a
        # parent whose actual content is its more-indented children just
        # below it, not a leaf that forgot its conclusion label (every node,
        # leaf or group, is its own "- " list item so nesting renders
        # correctly; see generate_script_final.py's _render_item). Only
        # flag it when the next non-blank line is NOT more indented, i.e.
        # it has no children and really is a bare, unlabeled leaf.
        indent = len(line) - len(line.lstrip(" "))
        has_child = False
        for next_line in lines[index + 1 :]:
            if not next_line.strip():
                continue
            has_child = (len(next_line) - len(next_line.lstrip(" "))) > indent
            break
        if not has_child:
            hits.append(stripped)
    return tuple(hits)


def _module_heading_colon_hits(text: str) -> tuple[str, ...]:
    """Find module headings that use the detail-line colon separator.

    On-screen hierarchy reserves ``｜`` for module-title separation while
    ``：`` remains available for conclusion-first detail bullets. Keeping the
    two separators distinct prevents a module heading and its child summary
    from receiving the same visual punctuation weight.
    """

    hits = []
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^###\s+[^：:\n]+[：:]", stripped):
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


def _mechanical_onscreen_label_pattern_hits(page: ScriptPage) -> tuple[str, ...]:
    """Detect reusable authoring labels standing in for business copy."""

    group_hits = tuple(
        title
        for title in page.top_level_module_titles
        if title in GENERIC_ONSCREEN_GROUP_LABELS
    )
    detail_hits: list[str] = []
    for raw in page.onscreen_text.splitlines():
        line = strip_authoring_group_marker(raw).strip()
        match = re.match(r"(?:[-*+•]\s*)?([^：:]{1,12})[：:]", line)
        if match and match.group(1).strip() in GENERIC_ONSCREEN_DETAIL_LABELS:
            detail_hits.append(match.group(1).strip())
    if len(group_hits) >= 2 and len(set(detail_hits)) >= 4:
        return (*group_hits, *tuple(dict.fromkeys(detail_hits)))
    return ()


def _onscreen_flat_long_labelled_detail_hits(text: str) -> tuple[str, ...]:
    """Find long peer labels that need a real business-title parent.

    The check deliberately uses only visible structure: it neither requires a
    title vocabulary nor assumes a target number of modules.  A genuine title
    with indented children has only the title at the least indentation level;
    three long label-value peers do not.
    """

    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return ()
    peer_indent = min(_line_indent(line) for line in lines)
    hits: list[str] = []
    for line in lines:
        if _line_indent(line) != peer_indent:
            continue
        match = re.match(r"\s*[^：:]{1,16}[：:]\s*(.+)", line)
        if match and _compact_len(match.group(1)) > 18:
            hits.append(line.strip())
    return tuple(hits) if len(hits) >= 3 else ()


def _boundary_aside_hits(text: str) -> tuple[str, ...]:
    hits = [pattern for pattern in _BOUNDARY_ASIDE_PATTERNS if pattern in text]
    return tuple(hits)


def _onscreen_parallel_structure_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    """Check that peer items in each visible module share a syntax skeleton.

    This is deliberately a warning: a source-faithful exception may be valid,
    but mixed paragraph/label syntax in one module is usually an authoring
    defect.  The check concerns form only; it never requires identical wording
    and therefore cannot flatten different business responsibilities.
    """

    if page.page_type != "content":
        return []
    lines = page.onscreen_text.splitlines()

    def heading_title(line: str) -> str | None:
        title = _module_title(line)
        if title is None:
            return None
        # Plain ``标签：内容`` lines are visible details, not headings.
        stripped = line.strip()
        if re.search(r"[：:]", stripped) and not stripped.startswith("**"):
            return None
        return title

    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        title = heading_title(line)
        if title is not None:
            headings.append((_line_indent(line), index, title))
    issues: list[ScriptQualityIssue] = []
    for position, (indent, start, title) in enumerate(headings):
        end = len(lines)
        for next_indent, next_index, _ in headings[position + 1 :]:
            if next_indent <= indent:
                end = next_index
                break
        child_lines: list[str] = []
        for line in lines[start + 1 : end]:
            if not line.strip() or heading_title(line) is not None:
                continue
            if _line_indent(line) <= indent:
                continue
            child_lines.append(line.strip().lstrip("- ").strip())
        if len(child_lines) < 3:
            continue
        classes = {
            "label_colon" if re.search(r"[：:]", line) else "phrase"
            for line in child_lines
        }
        if len(classes) > 1:
            issues.append(
                _issue(
                    "ONSCREEN_PARALLEL_STRUCTURE_INCONSISTENT",
                    page,
                    f"Module {title} mixes label-value items with free phrases instead of a parallel syntax.",
                    "Use one peer syntax within the module (prefer 标签：短语); preserve each item's distinct business object, responsibility, or action.",
                    evidence=tuple(child_lines[:6]),
                    severity="warning",
                )
            )
    return issues


def _necessity_page_closure_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Require a necessity page to close the causal chain on screen."""

    topic = str(contract.get("topic_category") or "").strip()
    if page.page_type != "content" or "必要性" not in topic:
        return []
    title = str(contract.get("title") or page.title).strip()
    issues: list[ScriptQualityIssue] = []
    if not re.search(r"必要性|必要|为何|原因", title):
        issues.append(
            _issue(
                "PAGE_TITLE_ARGUMENT_ROLE_MISMATCH",
                page,
                "The approved title describes a narrower demand topic while the page argument role is construction necessity.",
                "Name the page's actual proposition explicitly, preferably with 建设必要性 for formal reporting materials.",
                evidence=(f"title={title}", f"topic_category={topic}"),
            )
        )
    visible_lines = [line.strip() for line in page.onscreen_text.splitlines() if line.strip()]
    tail = "\n".join(visible_lines[max(0, len(visible_lines) * 2 // 3) :])
    if not re.search(r"建设必要性|需要(?:建设|建立)|建立行业级|建设行业级", tail):
        issues.append(
            _issue(
                "ONSCREEN_NECESSITY_CLOSURE_MISSING",
                page,
                "The on-screen chain states background, demand, or gap but does not close on the required construction response.",
                "End the visible chain with the source-supported necessity conclusion; do not stop at a problem inventory or add a generic slogan.",
                evidence=(tail[-180:],),
            )
        )
    return issues


ONSCREEN_FLOW_ACTION_TERMS = (
    "建立", "推动", "带动", "驱动", "形成", "制约", "需要", "组织",
    "连接", "贯通", "衔接", "转化", "输入", "输出", "履行", "交付",
    "反馈", "回流", "支撑", "完善", "梳理", "实施", "运营", "推广",
    "管理", "确认", "授权", "计量", "结算", "验证", "进入", "转入",
)
ONSCREEN_FLOW_HEADING_MAX_CHARS = 24
FORMULAIC_TRANSITION_TERMS = (
    "因此", "由此", "进而", "综上", "综上所述", "基于此", "鉴于此", "所以",
)


def _onscreen_flow_language_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Require action language only for action-grammar expression forms.

    ``visual_intent_type`` says what the picture needs to prove.  It is not a
    title grammar.  The title grammar is selected by the page's resolved
    ``onscreen_expression_form``; this keeps evidence, architecture and
    argument pages from being mechanically rewritten as process pages.
    """

    modules = tuple(item.strip() for item in page.top_level_module_titles if item.strip())
    decision = resolve_onscreen_expression(
        page,
        page_mission=str(contract.get("page_mission") or ""),
        business_relationships=page.content_relations,
        topic_category=str(contract.get("topic_category") or ""),
    )
    if (
        page.page_type != "content"
        or not expression_requires_action_headings(decision.form)
    ):
        return []
    issues: list[ScriptQualityIssue] = []
    action_modules = tuple(
        module
        for module in modules
        if any(term in module for term in ONSCREEN_FLOW_ACTION_TERMS)
    )
    required_actions = max(2, (len(modules) + 1) // 2)
    if len(action_modules) < required_actions:
        missing = tuple(module for module in modules if module not in action_modules)
        issues.append(
            _issue(
                "ONSCREEN_FLOW_ACTION_MISSING",
                page,
                "The visible flow is built from isolated noun phrases instead of business actions or relation predicates.",
                "Rewrite peer headings so they state what changes, drives, constrains, forms, transfers, or results; child items should supply evidence and detail.",
                evidence=missing[:6],
            )
        )
    long_modules = tuple(
        module
        for module in modules
        if meaningful_char_count(module) > ONSCREEN_FLOW_HEADING_MAX_CHARS
    )
    if long_modules:
        issues.append(
            _issue(
                "ONSCREEN_FLOW_HEADING_TOO_LONG",
                page,
                "One or more flow headings over-explain the relation instead of advancing it concisely.",
                "Keep each flow step within 24 meaningful characters; place evidence and qualifications in child items.",
                evidence=long_modules[:6],
            )
        )
    repeated_steps: list[str] = []
    for left, right in zip(modules, modules[1:]):
        left_compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", left)
        right_compact = re.sub(r"[^\w\u4e00-\u9fff]+", "", right)
        overlap = ""
        for width in range(min(12, len(left_compact), len(right_compact)), 3, -1):
            if left_compact.endswith(right_compact[:width]):
                overlap = right_compact[:width]
                break
        if overlap:
            repeated_steps.append(f"{left} → {right}（重复：{overlap}）")
    if repeated_steps:
        issues.append(
            _issue(
                "ONSCREEN_FLOW_STEP_REDUNDANT",
                page,
                "An adjacent flow step repeats the previous step's ending as its opening, making the chain explicit and verbose.",
                "Let the next step advance with a new business subject or predicate; rely on sequence for continuity instead of verbatim relay wording.",
                evidence=tuple(repeated_steps[:4]),
            )
        )
    return issues


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


def _polarity_dropped_terms(statement: str, authored: str) -> tuple[str, ...]:
    """Return source negation markers that vanish from the authored text.

    ``_source_statement_overlap`` scores character-shingle survival and is
    blind to polarity: dropping "不得"/"禁止" from an otherwise long,
    shingle-heavy statement barely moves the overlap ratio, so a rewrite that
    silently inverts a prohibition into its opposite ("不得对外提供" ->
    "对外提供") can still pass as "covered". Flag that gap directly by
    requiring every negation marker present in the source statement to also
    appear in the authored text.
    """

    return tuple(term for term in NEGATION_TERMS if term in statement and term not in authored)


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
        dropped_negations = _polarity_dropped_terms(statement, authored)
        if not dropped_negations:
            for item in source_statements:
                dropped_negations = _polarity_dropped_terms(item, authored)
                if dropped_negations:
                    break
        if dropped_negations:
            refs = tuple(str(item) for item in unit.get("source_refs") or [])
            issues.append(
                _issue(
                    "SOURCE_POLARITY_MISMATCH",
                    page,
                    "The authored page drops a source negation marker, risking an inverted claim.",
                    "Restore the source's prohibition/negation wording (or an equivalent negative statement); do not let a shingle-overlap match hide a polarity flip.",
                    source_ids=refs,
                    evidence=(statement, *dropped_negations),
                )
            )
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


def _full_prose_source_coverage_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    """Require every page-assigned fact to survive in 完整文字稿.

    Evidence identifiers prove provenance, not consumption.  A page may omit
    an assigned record only when the approved Outline declares a specific
    editorial reason in ``intentional_omissions``.
    """

    # ``source_refs`` is the complete evidence inventory, while
    # ``detail_refs`` explicitly marks retained traceability that does not
    # have to be narrated record by record.  Requiring those details in full
    # prose defeats the evidence hierarchy and turns appendices into page
    # copy.  Boundary evidence remains mandatory unless intentionally omitted.
    detail_refs = {str(ref) for ref in (contract.get("detail_refs") or [])}
    expected_refs = tuple(
        dict.fromkeys(
            str(ref)
            for field in ("source_refs", "boundary_refs")
            for ref in (contract.get(field) or [])
            if str(ref).strip() and str(ref) not in detail_refs
        )
    )
    omissions: set[str] = set()
    issues: list[ScriptQualityIssue] = []
    for item in contract.get("intentional_omissions") or []:
        if not isinstance(item, dict):
            issues.append(
                _issue(
                    "FULL_PROSE_OMISSION_INVALID",
                    page,
                    "Outline intentional_omissions entries must be objects.",
                    "Declare source_refs and a specific editorial reason in the approved Outline.",
                )
            )
            continue
        refs = tuple(str(ref) for ref in item.get("source_refs") or [] if str(ref).strip())
        reason = str(item.get("reason") or "").strip()
        if not refs or len(reason) < 8:
            issues.append(
                _issue(
                    "FULL_PROSE_OMISSION_REASON_MISSING",
                    page,
                    "An intentional omission requires source_refs and a specific editorial reason.",
                    "Explain why the source information is deliberately excluded from this page; generic importance labels are insufficient.",
                    source_ids=refs,
                )
            )
            continue
        omissions.update(refs)
    for ref in expected_refs:
        if ref in omissions:
            continue
        record = records_by_id.get(ref)
        if not record:
            continue
        anchors = [str(record.get("statement") or "")]
        anchors.extend(
            str(unit.get("text") or "")
            for unit in record.get("semantic_units") or []
            if isinstance(unit, dict) and str(unit.get("text") or "").strip()
        )
        overlap = max(
            (_source_statement_overlap(anchor, page.full_prose) for anchor in anchors if anchor.strip()),
            default=0.0,
        )
        if overlap < 0.08:
            issues.append(
                _issue(
                    "FULL_PROSE_SOURCE_COVERAGE_GAP",
                    page,
                    "The approved source record is cited but its factual content is absent from 完整文字稿.",
                    "Restore the source-specific fact in 完整文字稿, or record a specific intentional omission in the approved Outline.",
                    source_ids=(ref,),
                    evidence=(str(record.get("statement") or ""), f"overlap={overlap:.3f}"),
                )
            )
        dropped_negations: tuple[str, ...] = ()
        for anchor in anchors:
            if not anchor.strip():
                continue
            dropped_negations = _polarity_dropped_terms(anchor, page.full_prose)
            if dropped_negations:
                break
        if dropped_negations:
            issues.append(
                _issue(
                    "SOURCE_POLARITY_MISMATCH",
                    page,
                    "完整文字稿 drops a source negation marker, risking an inverted claim.",
                    "Restore the source's prohibition/negation wording (or an equivalent negative statement); do not let a shingle-overlap match hide a polarity flip.",
                    source_ids=(ref,),
                    evidence=(str(record.get("statement") or ""), *dropped_negations),
                )
            )
    return issues


def _full_prose_paragraph_boundary_issues(
    page: ScriptPage,
    contract: dict[str, object],
    records_by_id: dict[str, dict[str, object]],
) -> list[ScriptQualityIssue]:
    """Keep source-paragraph reasoning visible in the full-prose layer.

    The rule activates only when a page consumes at least three distinct
    source paragraphs.  It does not prohibit a deliberate merge, but makes
    that editorial choice explicit and checks that the mapped prose paragraph
    actually carries each assigned source record.
    """

    detail_refs = {str(ref) for ref in (contract.get("detail_refs") or [])}
    expected_refs = tuple(
        dict.fromkeys(
            str(ref)
            for field in ("source_refs", "boundary_refs")
            for ref in (contract.get(field) or [])
            if str(ref).strip() and str(ref) not in detail_refs and ref in records_by_id
        )
    )
    groups: dict[tuple[str, ...], list[str]] = {}
    for ref in expected_refs:
        unit_refs = tuple(str(item) for item in records_by_id[ref].get("source_unit_refs") or [] if str(item))
        if not unit_refs:
            continue
        groups.setdefault(unit_refs, []).append(ref)
    if len(groups) < 3:
        return []

    paragraphs = tuple(
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", page.full_prose)
        if paragraph.strip()
    )
    mapping = page.prose_paragraph_map
    if not mapping:
        return [_issue(
            "FULL_PROSE_PARAGRAPH_MAP_MISSING",
            page,
            "This page consumes several source paragraphs but does not record how they map into 完整文字稿 paragraphs.",
            "Add one ‘完整文字稿段落映射’ entry per prose paragraph. Keep source paragraphs separate by default; a combined entry must state 合并理由.",
            source_ids=expected_refs,
        )]
    issues: list[ScriptQualityIssue] = []
    if len(mapping) != len(paragraphs):
        issues.append(_issue(
            "FULL_PROSE_PARAGRAPH_MAP_COUNT_MISMATCH",
            page,
            "The paragraph map and 完整文字稿 have different paragraph counts.",
            "Use one mapping entry for each prose paragraph, in the same order.",
            evidence=(f"map={len(mapping)}", f"prose={len(paragraphs)}"),
        ))
    mapped_refs = tuple(ref for refs, _ in mapping for ref in refs)
    if set(mapped_refs) != set(expected_refs) or len(mapped_refs) != len(set(mapped_refs)):
        issues.append(_issue(
            "FULL_PROSE_PARAGRAPH_MAP_COVERAGE_INVALID",
            page,
            "The paragraph map must cover every non-detail page source once and only once.",
            "Correct the Source Truth IDs in 完整文字稿段落映射; retain details only when the Outline marks them as detail_refs.",
            source_ids=expected_refs,
            evidence=mapped_refs,
        ))
    group_by_ref = {ref: group for group, refs in groups.items() for ref in refs}
    for index, (refs, reason) in enumerate(mapping):
        source_groups = {group_by_ref.get(ref) for ref in refs}
        source_groups.discard(None)
        if len(source_groups) > 1 and len(reason) < 8:
            issues.append(_issue(
                "FULL_PROSE_PARAGRAPH_MERGE_REASON_MISSING",
                page,
                "A full-prose paragraph merges distinct source paragraphs without an editorial reason.",
                "Keep source paragraphs separate by default, or state a concrete 合并理由 explaining the shared argument duty and retained conclusion.",
                source_ids=refs,
            ))
        if index >= len(paragraphs):
            continue
        for ref in refs:
            record = records_by_id.get(ref)
            if not record:
                continue
            statement = str(record.get("statement") or "")
            if statement and _source_statement_overlap(statement, paragraphs[index]) < 0.05:
                issues.append(_issue(
                    "FULL_PROSE_PARAGRAPH_SOURCE_MISMATCH",
                    page,
                    "A mapped source record is not substantively represented in its assigned prose paragraph.",
                    "Move the source-specific fact into the mapped paragraph or correct the paragraph map.",
                    source_ids=(ref,),
                    evidence=(f"paragraph={index + 1}",),
                ))
    return issues


def _page_content_unit_coverage_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Verify atomic page content survives both prose and onscreen compression."""

    issues: list[ScriptQualityIssue] = []
    model_covered_refs, model_issues = _model_slot_coverage_issues(page, contract)
    issues.extend(model_issues)
    units = [
        item for item in (contract.get("content_units") or [])
        if isinstance(item, dict)
    ]
    for unit in units:
        unit_id = str(unit.get("unit_id") or "")
        statement = str(unit.get("statement") or "").strip()
        source_refs = tuple(
            str(item) for item in unit.get("source_refs") or [] if str(item)
        )
        coverage_anchors = tuple(
            str(item).strip() for item in unit.get("coverage_anchors") or []
            if str(item).strip()
        )
        onscreen_anchors = tuple(
            str(item).strip() for item in unit.get("onscreen_anchors") or []
            if str(item).strip()
        )
        if unit.get("full_prose_required") is True:
            hits = tuple(anchor for anchor in coverage_anchors if anchor in page.full_prose)
            required_hits = max(2, (len(coverage_anchors) * 2 + 2) // 3)
            statement_overlap = _source_statement_overlap(statement, page.full_prose)
            # Short anchors prove literal retention where the author keeps the
            # source wording.  A natural professional rewrite can preserve the
            # full meaning without repeating two arbitrary clauses verbatim;
            # high statement overlap is an equivalent proof in that case.
            if (
                len(hits) < required_hits
                and statement_overlap < 0.35
            ) or statement_overlap < 0.12:
                issues.append(_issue(
                    "FULL_PROSE_CONTENT_UNIT_GAP",
                    page,
                    "页面原子内容单元没有完整进入完整文字稿，存在对象、动作、条件或业务特征丢失。",
                    "恢复该内容单元的来源特征；不要用更抽象的概括句替代。",
                    source_ids=source_refs,
                    evidence=(
                        f"unit_id={unit_id}",
                        f"statement={statement}",
                        f"anchor_hits={len(hits)}/{len(coverage_anchors)}",
                        f"overlap={statement_overlap:.3f}",
                    ),
                ))
        if (
            unit.get("onscreen_required") is True
            and not set(source_refs).issubset(model_covered_refs)
        ):
            missing = tuple(
                anchor for anchor in onscreen_anchors
                if anchor not in page.onscreen_text
            )
            if missing:
                issues.append(_issue(
                    "ONSCREEN_CONTENT_UNIT_GAP",
                    page,
                    "提纲指定的重要内容单元没有进入上屏文字，页面视觉表达丢失关键业务特征。",
                    "以短语化、条目化方式恢复 onscreen_anchors；可以压缩句式，不能删除业务对象或关键动作。",
                    source_ids=source_refs,
                    evidence=(f"unit_id={unit_id}", *missing),
                ))
    return issues


def _model_slot_coverage_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> tuple[set[str], list[ScriptQualityIssue]]:
    """Verify visible responsibility for an author-selected expression model.

    The Outline audit has already established that mappings cite only current
    page evidence.  Here we verify that a non-implicit slot is represented in
    the audience layer before exempting its units from literal-anchor checks.
    """

    selection = contract.get("expression_model_selection")
    if not isinstance(selection, dict) or selection.get("fit") != "selected":
        return set(), []
    model = load_expression_models().get(str(selection.get("model_id") or ""))
    if model is None:
        return set(), []
    units = [
        item for item in (contract.get("content_units") or [])
        if isinstance(item, dict)
    ]
    visible = "\n".join(
        part for part in (page.onscreen_judgment, page.onscreen_text) if part.strip()
    )
    covered_refs: set[str] = set()
    issues: list[ScriptQualityIssue] = []
    slot_names = {slot.name for slot in model.slots}
    for mapping in selection.get("source_mapping") or []:
        if not isinstance(mapping, dict) or mapping.get("implicit") is True:
            continue
        slot = str(mapping.get("slot") or "")
        refs = {str(ref) for ref in mapping.get("source_refs") or [] if str(ref)}
        if not refs or slot not in slot_names:
            continue
        missing: set[str] = set()
        for ref in refs:
            matching_units = [
                unit for unit in units
                if ref in {str(value) for value in unit.get("source_refs") or []}
            ]
            if not matching_units:
                missing.add(ref)
                continue
            if any(
                any(
                    anchor and anchor in visible
                    for anchor in unit.get("onscreen_anchors") or []
                )
                or any(
                    _source_statement_overlap(str(anchor), visible, size=3) >= 0.55
                    for anchor in unit.get("onscreen_anchors") or []
                    if str(anchor).strip()
                )
                or _source_statement_overlap(str(unit.get("statement") or ""), visible) >= 0.22
                for unit in matching_units
            ):
                covered_refs.add(ref)
            else:
                missing.add(ref)
        if missing:
            issues.append(_issue(
                "EXPRESSION_MODEL_SLOT_ONSCREEN_MISSING",
                page,
                "作者选定表达模型的槽位没有在可见文字中承担来源表达职责。",
                "恢复该槽位的来源特征或调整作者确认的槽位映射；不要只补审计锚点。",
                source_ids=tuple(sorted(missing)),
                evidence=(f"model={model.model_id}", f"slot={slot}"),
            ))
    return covered_refs, issues


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
    strict_reading_density: bool = False,
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
        min_story_chars = onscreen_effective_char_target(page)
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
        if visible_story_chars < min_story_chars and (
            not structured_compact_layer
        ):
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


def _visual_structure_layout_recipe_hits(visual: str) -> tuple[str, ...]:
    hits: list[str] = []
    for pattern in VISUAL_STRUCTURE_LAYOUT_RECIPE_RES:
        for match in pattern.finditer(visual):
            value = match.group(0).strip()
            if value and value not in hits:
                hits.append(value)
    return tuple(hits)


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
    # CONSTRAINT_THEME_TERMS ("安全", "质量", "风险", "合规", ...) are common
    # business words that can appear as a passing modifier deep in a clause
    # whose actual subject is something else entirely ("平台建设兼顾安全与
    # 效率，形成可持续运营体系" — the clause is about the operating system,
    # not about safety). Restricting the match to the clause's opening
    # window approximates "is this the declared topic" rather than "is this
    # word merely present somewhere in the sentence" — Chinese subject-first
    # clauses put the topic noun near the start.
    topic_window = leading_clause[:10]
    return any(term in topic_window for term in CONSTRAINT_THEME_TERMS)


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
    count = _declared_count(page.onscreen_text)
    if count is None:
        count = _declared_count(page.main_message)
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
                )
            )
            issues.extend(_source_consumption_issues(page, contract))
            issues.extend(
                _full_prose_source_coverage_issues(
                    page,
                    contract,
                    records_by_id,
                )
            )
            issues.extend(
                _full_prose_paragraph_boundary_issues(
                    page,
                    contract,
                    records_by_id,
                )
            )
            if (
                outline.get("semantic_argument_model_mode") == "required"
                or outline.get("page_content_unit_coverage_mode") == "required"
            ):
                issues.extend(_page_content_unit_coverage_issues(page, contract))
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

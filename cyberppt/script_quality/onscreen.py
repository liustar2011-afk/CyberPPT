from __future__ import annotations

import re

from cyberppt.onscreen_expression import (
    expression_requires_action_headings,
    resolve_onscreen_expression,
)
from cyberppt.paths import repo_path

from .common import _compact_len, normalized_tokens
from .models import ScriptDocument, ScriptPage, ScriptQualityIssue, _issue
from .parsing import (
    MODULE_RE,
    _line_indent,
    _module_title,
    _source_refs,
    strip_authoring_group_marker,
)
_MODULE_CEILING_FALLBACK = 5

_RULES_YAML_PATH = repo_path("vendor", "skills", "ppt-script", "config", "rules.yaml")

NUMBERED_EVIDENCE_BULLET_RE = re.compile(
    r"^\s*-\s*依据(?P<number>\d+)[：:]\s*(?P<body>.*?)\s*$"
)

GENERIC_ONSCREEN_RELATION_RE = re.compile(
    r"(?:业务关系[：:]\s*)?(?:以上|上述)(?:内容|要点|依据)"
    r"(?:共同)?(?:构成|形成|支撑|完成)(?:本节|本页)?(?:完整)?(?:内容|判断|任务)"
)

GENERIC_ONSCREEN_GROUP_LABELS = frozenset(("关键判断", "业务事实", "运营要点"))

GENERIC_ONSCREEN_DETAIL_LABELS = frozenset(
    ("判断", "事实", "对象", "条件", "动作", "结果", "机制", "衔接", "要求", "依据", "状态", "安排")
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

_OBJECT_TAXONOMY_PARENT_RE = re.compile(r"(?:对象|资源|成果).*(?:类型|分类)|(?:类型|分类).*(?:对象|资源|成果)")

_TAXONOMY_CROSSCUT_LABEL_RE = re.compile(
    r"(?:使用用途|二次使用|终止处理|留存结算|共同约束|适用范围|授权(?:要求|限制)?|退出(?:处理|安排)?)"
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

ORDER_SIGNALS = ("①", "②", "③", "④", "⑤", "→", "随后", "依次", "最后一步")

NUMBERED_ORDER_SIGNAL_RE = re.compile(r"(?m)^\s*(?:\*\*)?\d{2}｜")

LOOP_SIGNALS = ("回流", "反馈", "复盘", "闭环", "持续校正")

MATRIX_SIGNALS = ("|---", "×", "矩阵")

LAYER_SIGNALS = ("自下而上", "自上而下", "底座", "贯穿")

MECHANISM_LANE_LABEL_RE = re.compile(r"[一-鿿]{1,6}(?:隔离|降级)")

BUSINESS_LANE_LABEL_RE = re.compile(
    r"[一-鿿]{1,8}(?:链路|队列|事务链|事件链|分析链)"
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

ONSCREEN_SEMANTIC_COVERAGE_ERROR_FLOOR = 0.15

ONSCREEN_SOURCE_SPECIFICITY_ERROR_FLOOR = 0.12

ONSCREEN_SEMANTIC_COVERAGE_MIN = 0.22

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

ONSCREEN_LAYOUT_META_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^\s*(?:[一二三四五六七八九十百\d]+)\s*行\s*(?:选择)?\s*矩阵(?:表)?\s*$"),
    re.compile(r"^\s*(?:主视觉|视觉中心|阅读顺序|构图说明|版式说明|布局说明)\s*[：:]"),
    re.compile(
        r"^\s*(?:以|采用|按).{0,24}(?:矩阵|泳道|色块|主链|收束条|节点链)"
        r".{0,24}(?:呈现|构成|排列|阅读|收束)"
    ),
    re.compile(r"^\s*第\s*(?:[一二三四五六七八九十百\d]+|[Xx])\s*行\s*[｜|：:]"),
)

ONSCREEN_DETAIL_PHRASE_WARNING_CHARS = 30

ONSCREEN_DETAIL_PHRASE_ERROR_CHARS = 60

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

_ONSCREEN_MARKDOWN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("heading", re.compile(r"(?m)^\s*#{1,6}\s+")),
    ("bold", re.compile(r"\*\*[^*\n]+\*\*")),
    ("bullet", re.compile(r"(?m)^\s*[-*+]\s+")),
)

ONSCREEN_FLOW_ACTION_TERMS = (
    "建立", "推动", "带动", "驱动", "形成", "制约", "需要", "组织",
    "连接", "贯通", "衔接", "转化", "输入", "输出", "履行", "交付",
    "反馈", "回流", "支撑", "完善", "梳理", "实施", "运营", "推广",
    "管理", "确认", "授权", "计量", "结算", "验证", "进入", "转入",
)

ONSCREEN_FLOW_HEADING_MAX_CHARS = 24

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
        # A rights-object taxonomy may not absorb rules that govern every
        # object or the whole lifecycle.  Such controls need their own
        # crosscutting relation instead of becoming another object type.
        crosscut_labels = [
            label
            for label in option_labels
            if _TAXONOMY_CROSSCUT_LABEL_RE.search(label)
        ]
        if _OBJECT_TAXONOMY_PARENT_RE.search(parent) and crosscut_labels:
            mismatches.append(
                f"{parent} -> crosscut_constraint:{', '.join(crosscut_labels[:4])}"
            )
            continue
        if (
            len(option_labels) == len(child_lines)
            and len(set(option_labels)) == len(option_labels)
            and all(1 <= len(label) <= 12 for label in option_labels)
            and re.search(r"(?:方式|路径|类型|分类|模式|方案)", parent)
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

def _onscreen_relation_meta_hits(text: str) -> tuple[str, ...]:
    hits: list[str] = []
    for raw in text.splitlines():
        match = _ONSCREEN_RELATION_META_RE.match(raw)
        if match:
            hits.append(match.group("label"))
    return tuple(dict.fromkeys(hits))

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

    Module headings and standalone labels are intentionally ignored. A line
    becomes a detail candidate when it contains a label/value separator, is a
    nested item, or is a top-level sentence with terminal punctuation. This
    keeps the rule focused on copy that would otherwise become a paragraph
    inside a card, lane, or matrix cell.
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
        elif re.search(r"[。！？；;]$", line):
            # A top-level sentence is visible body copy, not a module label.
            # Keep its length subject to the same paragraph guard as details.
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

def _onscreen_markdown_hits(text: str) -> tuple[str, ...]:
    return tuple(name for name, pattern in _ONSCREEN_MARKDOWN_PATTERNS if pattern.search(text))

def _subtitle_policy_issues(
    page: ScriptPage,
    contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    """Validate optional subtitle policy without making it a body-text rule."""

    policy = contract.get("subtitle_policy")
    if not isinstance(policy, dict):
        return []
    mode = str(policy.get("mode") or "").strip()
    expected = str(policy.get("subtitle") or "").strip()
    raw_policy_refs = policy.get("source_refs")
    policy_refs = {
        str(value).strip()
        for value in raw_policy_refs
        if str(value).strip()
    } if isinstance(raw_policy_refs, list) else set(_source_refs(str(raw_policy_refs or "")))
    issues: list[ScriptQualityIssue] = []
    if mode not in {"generated", "not_needed", "author_required", "authored"}:
        issues.append(
            _issue(
                "SUBTITLE_POLICY_MODE_INVALID", page,
                "Outline subtitle policy has an unsupported mode.",
                "Use generated, not_needed, author_required, or authored.",
            )
        )
        return issues
    if mode == "generated":
        if not expected or page.subtitle != expected:
            issues.append(
                _issue(
                    "SUBTITLE_POLICY_MISMATCH", page,
                    "Generated subtitle does not match the approved Outline policy.",
                    "Use the generated subtitle or change the Outline policy to authored after review.",
                    evidence=tuple(value for value in (expected, page.subtitle) if value),
                )
            )
        if expected and expected == page.title:
            issues.append(
                _issue(
                    "SUBTITLE_TITLE_REPEAT", page,
                    "Generated subtitle repeats the page title instead of advancing the page judgment.",
                    "Use a short source-grounded relation or set the policy to author_required.",
                    evidence=(expected,),
                )
            )
    if mode in {"not_needed", "author_required"} and page.subtitle:
        issues.append(
            _issue(
                "SUBTITLE_POLICY_MISMATCH", page,
                "Outline policy does not permit a visible subtitle on this page.",
                "Remove the subtitle or mark the approved policy authored with source references.",
                evidence=(page.subtitle,),
            )
        )
    core_message = str(contract.get("core_message") or page.core_message or "").strip()
    if (
        mode == "not_needed"
        and page.onscreen_judgment
        and page.onscreen_judgment == core_message
        and _compact_len(core_message) >= 32
    ):
        issues.append(
            _issue(
                "STRUCTURED_PAGE_LONG_JUDGMENT_ONSCREEN", page,
                "A page marked not_needed puts its long core judgment back into the on-screen body.",
                "Keep the body focused on its approved information structure; generate or author a short subtitle only when the page needs one.",
                evidence=(page.onscreen_judgment,),
            )
        )
    if mode in {"generated", "authored"} and policy_refs and not policy_refs <= set(page.source_refs):
        issues.append(
            _issue(
                "SUBTITLE_UNGROUNDED", page,
                "Subtitle policy cites evidence outside this page's approved source scope.",
                "Restrict subtitle_policy.source_refs to the page's approved evidence.",
                evidence=tuple(sorted(policy_refs - set(page.source_refs))),
            )
        )
    return issues

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

def _declared_count(text: str) -> int | None:
    match = re.search(
        r"([二两三四五六七八])(?:类能力|类任务|类断点|项任务|个模块|步|层)",
        text,
    )
    return COUNT_WORDS.get(match.group(1)) if match else None

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

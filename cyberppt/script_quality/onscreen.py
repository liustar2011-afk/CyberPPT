from __future__ import annotations

import re

from cyberppt.onscreen_expression import (
    expression_requires_action_headings,
    resolve_onscreen_expression,
)
from cyberppt.paths import repo_path
from cyberppt.source_detail_visibility import (
    clean_visible_line,
    functional_group_needs_item_explanations,
    is_bare_business_label,
    source_has_richer_item_detail,
)

from .common import _compact_len, _source_statement_overlap, normalized_tokens, text_similarity
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

# Formal-document ordinals are valid only when their peer sequence is visible
# in the same on-screen group. A lone ``（五）`` usually means a source heading
# number leaked into a re-authored slide module.
ONSCREEN_ORDINAL_RE = re.compile(
    r"^\s*(?:【\s*)?(?P<ordinal>（[一二三四五六七八九十百]+）|[一二三四五六七八九十百]+、|\d+[.)](?=\s))\s*"
)

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

# A screen line may need to carry one complete, source-grounded proposition.
# This ceiling is intentionally far below paragraph density, while avoiding a
# rule that turns every meaningful Chinese sentence into disconnected labels.
ONSCREEN_COMPLETE_PROPOSITION_CHARS = 90

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

ONSCREEN_CLOSING_CONNECTORS = ("需要", "建设", "建立", "衔接", "形成")
ONSCREEN_NECESSITY_CONSTRAINT_TERMS = (
    "难以", "不足", "缺口", "尚未", "制约", "分散", "不能",
)

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

def _onscreen_false_parallel_semantics(
    text: str,
    contract: dict[str, object] | None = None,
) -> tuple[str, ...]:
    """Flag sibling lists that mix distinct argument functions.

    Indentation is a semantic assertion.  When three or more direct children
    mix attributes, changes, demands, gaps, or responses, they cannot be
    rendered as one peer list without an explicit relation rewrite.
    """

    def declared_current_state_peers(child_lines: list[str]) -> bool:
        """Return whether the page contract explicitly authorizes these peers.

        Different state predicates must not become a peer list merely because
        their wording happens to contain familiar status terms.  The approved
        contract needs both a current-state peer set and one visible carrier
        for every child.
        """

        content_units = [
            unit for unit in (contract or {}).get("content_units") or []
            if isinstance(unit, dict)
        ]
        peer_sets: dict[str, set[str]] = {}
        for unit in content_units:
            if str(unit.get("peer_dimension") or "") != "current_state":
                continue
            peer_set = str(unit.get("peer_set_id") or "").strip()
            group = str(unit.get("onscreen_group_id") or "").strip()
            if peer_set and group:
                peer_sets.setdefault(peer_set, set()).add(group)
        if not any(len(groups) >= len(child_lines) for groups in peer_sets.values()):
            return False

        logic = (contract or {}).get("page_logic_contract")
        projections = (
            [
                projection
                for projection in logic.get("onscreen_projection") or []
                if isinstance(projection, dict)
                and str(projection.get("carrier_mode") or "")
                == "integrated_proposition"
            ]
            if isinstance(logic, dict)
            else []
        )
        carriers = [str(projection.get("carrier") or "").strip() for projection in projections]
        return (
            len(carriers) >= len(child_lines)
            and all(any(carrier and carrier in line for carrier in carriers) for line in child_lines)
        )

    def declared_expression_group(child_lines: list[str]) -> bool:
        """Accept only a source-bound expression group, never a guessed chain."""

        logic = (contract or {}).get("page_logic_contract")
        expression = logic.get("onscreen_expression") if isinstance(logic, dict) else None
        if not isinstance(expression, dict):
            return False
        expression_nodes = {
            str(node.get("id") or ""): node
            for node in expression.get("nodes") or []
            if isinstance(node, dict) and str(node.get("id") or "")
        }
        if not expression_nodes:
            return False

        def compact(value: object) -> str:
            return re.sub(r"\s+", "", str(value or ""))

        matched: set[str] = set()
        for line in child_lines:
            compact_line = compact(line)
            line_matches = {
                node_id
                for node_id, node in expression_nodes.items()
                if any(
                    compact(value) and compact(value) in compact_line
                    for value in ([node.get("text")] + list(node.get("items") or []))
                )
            }
            if not line_matches:
                return False
            matched.update(line_matches)
        if len(matched) == 1:
            return str(expression_nodes[next(iter(matched))].get("render") or "") in {
                "statement_stack", "chip_set",
            }
        rendered = "\n".join(child_lines)
        for edge in expression.get("edges") or []:
            if not isinstance(edge, dict):
                continue
            label = compact(edge.get("visible_label"))
            endpoints = {str(edge.get("from") or ""), str(edge.get("to") or "")}
            if label and label in compact(rendered) and endpoints.issubset(matched):
                return True
        return False

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
        descendant_lines = [
            line
            for line in lines[start + 1 : end]
            if line.strip() and _line_indent(line) > indent
        ]
        direct_indent = min(
            (_line_indent(line) for line in descendant_lines),
            default=-1,
        )
        child_lines = [
            line.strip()
            for line in descendant_lines
            if _line_indent(line) == direct_indent
        ]
        if len(child_lines) < 3:
            continue
        if declared_current_state_peers(child_lines):
            continue
        if declared_expression_group(child_lines):
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

# A genuinely hierarchical page (real module/child structure, not four
# unrelated short lines wearing structure as a costume -- see
# _is_structured_compact_onscreen_layer) can carry the same meaning in fewer
# characters than flowing prose, so it earns a discount off the raw
# ONSCREEN_EFFECTIVE_CHARS_MIN/MAX target. It does not earn exemption: a flat
# 60-character floor made the 220-320 target dead code for every page in a
# real deck, because virtually every content page in this project's own
# established convention (①②③ modules with child detail lines) satisfies the
# "structured" test. The discount keeps the structural credit while still
# requiring real content.
STRUCTURED_LAYER_DENSITY_DISCOUNT = 0.7


def structured_layer_char_target(page: ScriptPage) -> int:
    """Return the discounted, still-real density floor for a structured page."""

    return max(60, round(onscreen_effective_char_target(page) * STRUCTURED_LAYER_DENSITY_DISCOUNT))

def _is_structured_compact_onscreen_layer(
    page: ScriptPage,
    *,
    visible_story_chars: int | None = None,
) -> bool:
    """Return whether concise copy carries an explicit readable hierarchy.

    Three or more named business modules can form a readable peer structure,
    including a page that compares three current states and gives one
    integrated landing. Structure depends on real modules, never on splitting
    one thought into five labels.
    """

    visible_chars = (
        meaningful_char_count(page.onscreen_judgment + page.onscreen_text)
        if visible_story_chars is None
        else visible_story_chars
    )
    return bool(
        1 <= len(page.top_level_module_titles) <= MODULE_CEILING
        and len(page.module_titles) >= 3
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
    """Return ``(line, body_chars)`` for paragraph-like visible copy.

    Label-value details remain compact phrases. A complete sentence without a
    label is also valid screen copy when it carries one business proposition
    under a real module (or as the page landing): source fidelity sometimes
    depends on retaining its subject, state, and relationship together. The
    sentence still has a firm ceiling, and unlabeled fragments cannot evade
    the compact-detail rule by dropping terminal punctuation.
    """

    overages: list[tuple[str, int]] = []
    for raw in text.splitlines():
        line = strip_authoring_group_marker(raw).strip()
        line = re.sub(r"^[-*+•]\s*", "", line).strip()
        if not line or line.startswith("#") or MODULE_RE.match(line):
            continue
        parts = re.split(r"[：:]", line, maxsplit=1)
        labelled_detail = len(parts) == 2 and parts[1].strip()
        if labelled_detail:
            body = parts[1]
        else:
            body = line
        body_chars = meaningful_char_count(body)
        if (
            not labelled_detail
            and line.endswith(("。", "！", "？"))
            and body_chars <= ONSCREEN_COMPLETE_PROPOSITION_CHARS
        ):
            continue
        if body_chars > ONSCREEN_DETAIL_PHRASE_WARNING_CHARS:
            overages.append((line, body_chars))
    return tuple(overages)


def _complete_proposition_placement_issues(
    page: ScriptPage,
    contract: dict[str, object] | None = None,
) -> tuple[str, ...]:
    """Find long natural sentences that have no visible semantic carrier.

    A natural sentence is valid only when it elaborates a preceding business
    module or when the page logic explicitly declares it as the integrated
    landing. Terminal punctuation by itself is formatting, not evidence that
    the sentence has a legitimate role in the on-screen argument.
    """

    lines = page.onscreen_text.splitlines()
    logic = (contract or {}).get("page_logic_contract")
    landings = (
        [
            projection
            for projection in logic.get("onscreen_projection") or []
            if isinstance(projection, dict)
            and str(projection.get("carrier_mode") or "") == "integrated_landing"
        ]
        if isinstance(logic, dict)
        else []
    )
    issues: list[str] = []
    for index, raw in enumerate(lines):
        line = strip_authoring_group_marker(raw).strip()
        line = re.sub(r"^[-*+•]\s*", "", line).strip()
        if not line or MODULE_RE.match(line) or re.search(r"[：:]", line):
            continue
        chars = meaningful_char_count(line)
        if (
            chars <= ONSCREEN_DETAIL_PHRASE_WARNING_CHARS
            or chars > ONSCREEN_COMPLETE_PROPOSITION_CHARS
            or not line.endswith(("。", "！", "？"))
        ):
            continue
        indent = _line_indent(raw)
        has_parent_module = any(
            _line_indent(previous) < indent
            and _module_title(previous) is not None
            for previous in lines[:index]
            if previous.strip()
        )
        declared_landing = any(
            (signals := [
                str(value).strip()
                for value in projection.get("onscreen_signals") or []
                if str(value).strip()
            ])
            and all(signal in line for signal in signals)
            for projection in landings
        )
        if not has_parent_module and not declared_landing:
            issues.append(line)
    return tuple(dict.fromkeys(issues))

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
            "requested pages contain paragraph-like on-screen copy; keep one "
            "complete proposition only where it is needed and split the remaining "
            "text into source-grounded business modules before ImageGen:\n"
            + "\n".join(failures)
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

DETAIL_TERMINAL_PUNCTUATION_CHARS = "。；，、：？！.!?;,:"


def _onscreen_detail_terminal_punctuation_hits(text: str) -> tuple[str, ...]:
    """Find label-prefixed detail lines (``标签：短语``) ending with punctuation.

    On-screen detail lines are bullet-style phrases, not manuscript
    sentences; a trailing period/comma/dunhao/etc. reads as an accidental
    carry-over from the full-text draft rather than deliberate slide copy.
    Bare module headings (``①常态质量保障``, ``【组标题】``) and genuine
    独立边界句 are intentionally excluded — neither has a colon, and for the
    latter the trailing 句号 is exactly what keeps ``_module_title`` from
    mis-parsing it as a module label (see parsing.py), so it must stay.
    """

    hits = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not re.match(r"^[^\s：:，,。；;、]{1,28}[：:]", stripped):
            continue
        if stripped.endswith(tuple(DETAIL_TERMINAL_PUNCTUATION_CHARS)):
            hits.append(stripped)
    return tuple(hits)


def _onscreen_orphan_ordinal_hits(
    text: str,
    subtitle: str = "",
) -> tuple[str, ...]:
    """Find lone hierarchy ordinals in visible on-screen fields."""

    hits: list[str] = []
    visible_text = "\n\n".join(
        value for value in (str(text), str(subtitle)) if value.strip()
    )
    groups = (group for group in visible_text.split("\n\n") if group.strip())
    for group in groups:
        ordinal_lines = [
            line.strip()
            for line in group.splitlines()
            if ONSCREEN_ORDINAL_RE.match(line)
        ]
        if len(ordinal_lines) == 1:
            hits.append(ordinal_lines[0])
    return tuple(dict.fromkeys(hits))


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

def _onscreen_module_dimension_consistency_issues(
    page: ScriptPage, contract: dict[str, object] | None = None,
) -> list[ScriptQualityIssue]:
    """Check that peer top-level modules label their details along the same axis.

    Peer modules (e.g. ①②③④ each describing one member of the same
    category) should walk the same set of dimensions in the same order --
    e.g. every module says 服务内容 / 主要用途 / 交付形式, not one module
    switching to 内容形式 or 支撑决策 partway through. Mixed axes make a
    reader reconstruct a different mental model per module instead of
    scanning one shared table, and they are exactly what breaks when an
    author reaches for whatever synonym reads naturally for that one module
    instead of the vocabulary already established by its siblings.

    Only compares modules that (a) sit at the same top-level indent, (b)
    have every child line labelled with 标签：, and (c) share the same
    child count -- a module with a genuinely different number of
    responsibilities is not a same-shape peer, and this check has nothing
    to say about it.
    """

    if page.page_type != "content":
        return []
    contract_mode = str((contract or {}).get("page_consumption_contract_mode") or "legacy")
    structure_mode = str((contract or {}).get("onscreen_structure_contract_mode") or "legacy")
    content_units = [
        unit for unit in (contract or {}).get("content_units") or []
        if isinstance(unit, dict)
    ]
    lines = page.onscreen_text.splitlines()

    def heading_title(line: str) -> str | None:
        title = _module_title(line)
        if title is None:
            return None
        stripped = line.strip()
        if re.search(r"[：:]", stripped) and not stripped.startswith("**"):
            return None
        return title

    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        title = heading_title(line)
        if title is not None:
            headings.append((_line_indent(line), index, title))
    base_indent = min((indent for indent, _, _ in headings), default=0)

    module_labels: dict[str, tuple[str, ...]] = {}
    for position, (indent, start, title) in enumerate(headings):
        if indent != base_indent:
            continue
        end = len(lines)
        for next_indent, next_index, _ in headings[position + 1 :]:
            if next_indent <= indent:
                end = next_index
                break
        labels: list[str] = []
        clean = True
        for line in lines[start + 1 : end]:
            if not line.strip() or heading_title(line) is not None:
                continue
            if _line_indent(line) <= indent:
                continue
            stripped = strip_authoring_group_marker(line).strip().lstrip("- ").strip()
            match = re.match(r"^(.{1,12}?)[：:]", stripped)
            if not match:
                clean = False
                break
            labels.append(match.group(1))
        if clean and labels:
            module_labels[title] = tuple(labels)

    issues: list[ScriptQualityIssue] = []
    comparison_sets: list[set[str]] = []
    if contract_mode == "required":
        def screen_group_id(unit: dict[str, object]) -> str:
            explicit = str(unit.get("onscreen_group_id") or "").strip()
            if structure_mode == "required":
                return explicit
            return explicit or str(unit.get("group_id") or "").strip()

        group_to_title: dict[str, str] = {}
        for part in re.split(r"[；;\n]+", page.evidence_map):
            match = re.match(
                r"\s*([A-Za-z0-9_.-]+)\s*=\s*([^→]+?)\s*→",
                part,
            )
            if match:
                group_to_title[match.group(1)] = match.group(2).strip()
        peer_groups: dict[str, set[str]] = {}
        visible_group_ids = set()
        group_units: dict[str, list[dict[str, object]]] = {}
        missing_structure_units: list[str] = []
        for unit in content_units:
            group_id = screen_group_id(unit)
            peer_set_id = str(unit.get("peer_set_id") or "").strip()
            if (
                structure_mode == "required"
                and str(unit.get("visibility") or "") in {
                    "primary_onscreen", "supporting_onscreen",
                }
                and any(
                    not str(unit.get(field) or "").strip()
                    for field in (
                        "onscreen_group_id",
                        "onscreen_group_kind",
                        "peer_dimension",
                    )
                )
            ):
                missing_structure_units.append(str(unit.get("unit_id") or "unknown"))
            if group_id and str(unit.get("visibility") or "") in {
                "primary_onscreen", "supporting_onscreen",
            }:
                visible_group_ids.add(group_id)
                group_units.setdefault(group_id, []).append(unit)
            if group_id and peer_set_id:
                peer_groups.setdefault(peer_set_id, set()).add(group_id)
        if structure_mode == "required":
            if missing_structure_units:
                issues.append(
                    _issue(
                        "ONSCREEN_GROUP_SEMANTIC_CONTRACT_CONFLICT",
                        page,
                        "Visible content units are missing required screen-group semantics.",
                        "Declare onscreen_group_id, onscreen_group_kind, and peer_dimension before page drafting.",
                        evidence=tuple(missing_structure_units),
                        severity="error",
                    )
                )
            for group_id, units in group_units.items():
                kinds = {
                    str(unit.get("onscreen_group_kind") or "").strip()
                    for unit in units
                    if str(unit.get("onscreen_group_kind") or "").strip()
                }
                dimensions = {
                    str(unit.get("peer_dimension") or "").strip()
                    for unit in units
                    if str(unit.get("peer_dimension") or "").strip()
                }
                missing_fields = sorted({
                    field
                    for unit in units
                    for field in (
                        "onscreen_group_id",
                        "onscreen_group_kind",
                        "peer_dimension",
                    )
                    if not str(unit.get(field) or "").strip()
                })
                if missing_fields or len(kinds) > 1 or len(dimensions) > 1:
                    issues.append(
                        _issue(
                            "ONSCREEN_GROUP_SEMANTIC_CONTRACT_CONFLICT",
                            page,
                            "A required screen group has incomplete or conflicting semantic declarations.",
                            "Repair the page-consumption contract so every visible group has one group kind and one peer dimension.",
                            evidence=(
                                f"{group_id}: missing={missing_fields}; "
                                f"kinds={sorted(kinds)}; dimensions={sorted(dimensions)}",
                            ),
                            severity="error",
                        )
                    )
        missing_mappings = sorted(visible_group_ids - group_to_title.keys())
        if missing_mappings:
            issues.append(
                _issue(
                    "ONSCREEN_GROUP_EVIDENCE_MAPPING_MISSING",
                    page,
                    "Required screen groups are not bound to visible modules in the evidence map.",
                    "Use `onscreen_group_id=模块标题→ST...` in required screen-structure mode; legacy contracts continue to use group_id.",
                    evidence=tuple(missing_mappings),
                    severity="error",
                )
            )
        title_positions = {
            title: index for index, (_, _, title) in enumerate(headings)
        }

        def is_integrated_landing_mapping(group_id: str, title: str) -> bool:
            """Allow a declared page landing to remain a readable sentence.

            A page-level conclusion can carry a many-to-one relation without
            pretending to be a fourth peer module.  The page logic contract
            must explicitly declare that mode and all declared signals must be
            visible in the mapped sentence.
            """

            logic = (contract or {}).get("page_logic_contract")
            compact_title = re.sub(r"\s+", "", title).strip("。！？!?；;")
            compact_onscreen = re.sub(r"\s+", "", page.onscreen_text)
            if not isinstance(logic, dict) or compact_title not in compact_onscreen:
                return False
            for projection in logic.get("onscreen_projection") or []:
                if not isinstance(projection, dict):
                    continue
                if str(projection.get("carrier_mode") or "") != "integrated_landing":
                    continue
                signals = [
                    str(value).strip()
                    for value in projection.get("onscreen_signals") or []
                    if str(value).strip()
                ]
                if signals and all(re.sub(r"\s+", "", signal) in compact_title for signal in signals):
                    return True
            expression = logic.get("onscreen_expression")
            if not isinstance(expression, dict):
                return False
            expression_nodes = {
                str(node.get("id") or ""): node
                for node in expression.get("nodes") or []
                if isinstance(node, dict) and str(node.get("id") or "")
            }
            for node_id, node in expression_nodes.items():
                if str(node.get("render") or "") != "landing":
                    continue
                landing = str(node.get("text") or "").strip()
                if not landing or re.sub(r"\s+", "", landing) not in compact_title:
                    continue
                if any(
                    str(edge.get("to") or "") == node_id
                    and re.sub(r"\s+", "", str(edge.get("visible_label") or "")) in compact_title
                    for edge in expression.get("edges") or []
                    if isinstance(edge, dict)
                ):
                    return True
            return False

        integrated_landings = {
            group_id
            for group_id, title in group_to_title.items()
            if group_id in visible_group_ids
            and is_integrated_landing_mapping(group_id, title)
        }
        missing_modules = sorted(
            f"{group_id}={title}"
            for group_id, title in group_to_title.items()
            if (
                group_id in visible_group_ids
                and group_id not in integrated_landings
                and title not in title_positions
            )
        )
        if missing_modules:
            issues.append(
                _issue(
                    "ONSCREEN_GROUP_MODULE_MISSING",
                    page,
                    "The evidence map binds a required consumption group to a module that is absent from the visible hierarchy.",
                    "Add the declared visible module or correct its group-to-module evidence mapping.",
                    evidence=tuple(missing_modules),
                    severity="error",
                )
            )
        main_chain_groups = []
        for unit in sorted(
            (
                unit for unit in content_units
                if unit.get("topology_role") == "main_chain"
                and isinstance(unit.get("sequence_index"), int)
                and unit.get("sequence_index") > 0
            ),
            key=lambda unit: (unit["sequence_index"], screen_group_id(unit)),
        ):
            group_id = screen_group_id(unit)
            if group_id and group_id not in main_chain_groups:
                main_chain_groups.append(group_id)
        chain_titles = [
            group_to_title[group_id]
            for group_id in main_chain_groups
            if group_id in group_to_title and group_to_title[group_id] in title_positions
        ]
        if len(chain_titles) >= 2:
            positions = [title_positions[title] for title in chain_titles]
            if positions != sorted(positions):
                issues.append(
                    _issue(
                        "ONSCREEN_MAIN_CHAIN_ORDER_MISMATCH",
                        page,
                        "Visible module order conflicts with the explicit page-consumption main chain.",
                        "Reorder the mapped modules to follow sequence_index, or correct the upstream sequence contract.",
                        evidence=tuple(chain_titles),
                        severity="error",
                    )
                )
        for group_ids in peer_groups.values():
            titles = {group_to_title[group_id] for group_id in group_ids if group_id in group_to_title}
            if len(titles) >= 2:
                comparison_sets.append(titles)
        title_to_groups: dict[str, set[str]] = {}
        for group_id, title in group_to_title.items():
            if group_id in visible_group_ids:
                title_to_groups.setdefault(title, set()).add(group_id)
        for title, group_ids in title_to_groups.items():
            if len(group_ids) < 2:
                continue
            if structure_mode == "required":
                issues.append(
                    _issue(
                        "ONSCREEN_GROUP_COALESCE_VIOLATION",
                        page,
                        "Multiple declared screen groups are mapped to one visible module.",
                        "Give each onscreen_group_id its own visible business group; keep evidence-only aggregation in group_id.",
                        evidence=(f"{title}: {', '.join(sorted(group_ids))}",),
                        severity="error",
                    )
                )
            units = [unit for group_id in group_ids for unit in group_units.get(group_id, [])]
            scopes = {str(unit.get("decision_scope") or "") for unit in units}
            relations = {str(unit.get("relation_to_proposition") or "") for unit in units}
            relation_conflict = bool(relations & {"gates", "constrains"}) and bool(
                relations & {"supports", "explains", "contextualizes"}
            )
            if len(scopes) > 1 or relation_conflict:
                issues.append(
                    _issue(
                        "ONSCREEN_CONSUMPTION_ANTI_MERGE_VIOLATION",
                        page,
                        "One visible module merges page-consumption groups with incompatible decision scopes or proposition relations.",
                        "Keep the declared groups in separate modules and preserve their page-level decision roles.",
                        evidence=(f"{title}: {', '.join(sorted(group_ids))}",),
                        severity="error",
                    )
                )
    else:
        comparison_sets.append(set(module_labels))

    for titles in comparison_sets:
        by_shape: dict[int, list[tuple[str, tuple[str, ...]]]] = {}
        for title in titles:
            labels = module_labels.get(title)
            if labels:
                by_shape.setdefault(len(labels), []).append((title, labels))
        for count, entries in by_shape.items():
            if count < 2 or len(entries) < 2:
                continue
            mismatched_positions = [
                index
                for index in range(count)
                if len({labels[index] for _, labels in entries}) > 1
            ]
            if not mismatched_positions:
                continue
            evidence = tuple(
                f"{title}: {' / '.join(labels)}" for title, labels in entries
            )
            issues.append(
                _issue(
                    "ONSCREEN_MODULE_DIMENSION_INCONSISTENT",
                    page,
                    "Peer modules label their details along different dimensions instead of one shared axis.",
                    "Use the same label vocabulary in the same position across declared peer modules.",
                    evidence=evidence,
                    severity="warning",
                )
            )
    return issues


def _onscreen_source_detail_collapsed_to_label_issues(
    page: ScriptPage,
    contract: dict[str, object] | None = None,
) -> list[ScriptQualityIssue]:
    """Reject bare child labels when the source or page role carries payload."""

    if page.page_type != "content":
        return []
    contract = contract or {}
    units = [
        unit
        for unit in contract.get("content_units") or []
        if isinstance(unit, dict)
    ]
    relevant_units = [
        unit
        for unit in units
        if unit.get("onscreen_required") is True
        or str(unit.get("visibility") or "")
        in {"primary_onscreen", "supporting_onscreen"}
    ] or units
    source_statements: list[str] = []
    for unit in relevant_units:
        statement = str(unit.get("statement") or "").strip()
        if statement:
            source_statements.append(statement)
        source_statements.extend(
            str(value).strip()
            for value in unit.get("source_statements") or []
            if str(value).strip()
        )

    nested_contract = contract.get("onscreen_contract")
    nested_contract = nested_contract if isinstance(nested_contract, dict) else {}
    detail_policy = nested_contract.get("detail_policy")
    detail_policy = detail_policy if isinstance(detail_policy, dict) else {}
    label_only_allowed = (
        contract.get("label_only_onscreen_allowed") is True
        or detail_policy.get("label_only_allowed") is True
    )

    raw_lines = [line for line in page.onscreen_text.splitlines() if line.strip()]
    headings = [
        (_line_indent(line), index, _module_title(line))
        for index, line in enumerate(raw_lines)
        if _module_title(line) is not None
    ]
    base_indent = min((indent for indent, _, _ in headings), default=0)
    issues: list[ScriptQualityIssue] = []
    for position, (indent, start, heading) in enumerate(headings):
        if indent != base_indent or heading is None:
            continue
        end = len(raw_lines)
        for next_indent, next_index, _ in headings[position + 1 :]:
            if next_indent <= indent:
                end = next_index
                break
        visible_items = [
            clean_visible_line(line)
            for line in raw_lines[start + 1 : end]
            if _line_indent(line) > indent and clean_visible_line(line)
        ]
        if not visible_items:
            continue
        collapsed = [
            value
            for value in visible_items
            if is_bare_business_label(value)
            and source_has_richer_item_detail(value, source_statements)
        ]
        role_only = functional_group_needs_item_explanations(
            heading,
            visible_items,
            content_load=contract.get("content_load"),
            label_only_allowed=label_only_allowed,
        )
        if not collapsed and not role_only:
            continue
        labels = collapsed or [
            value for value in visible_items if is_bare_business_label(value)
        ]
        issues.append(
            _issue(
                "ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL",
                page,
                "上屏明细把来源已有内容或页面职责压缩成了只有名称的标签，读者无法判断该项承担什么作用。",
                "改为“标签：来源支持的对象、作用、任务或边界”，末尾不加句号。来源仅提供分类名称时，可在提纲中明确 label_only_onscreen_allowed=true。",
                evidence=(f"module={heading}", *labels),
            )
        )
    return issues


def _onscreen_redundant_restatement_issues(page: ScriptPage) -> list[ScriptQualityIssue]:
    """Flag a free-standing on-screen line that just restates other copy.

    A short headline above the modules or a closing line below them is a
    legitimate way to state a page's judgment or a boundary that has no
    natural home inside any single module. It stops being legitimate when
    that line is functionally the same sentence as content already spelled
    out elsewhere on the slide -- either inside a module's own detail lines,
    or in 副标题 (the subtitle already *is* the slide's headline, so a body
    line that echoes it back is pure filler, "正确的废话": not wrong, just
    saying nothing new). A slide should not say the same thing twice just
    because the anchor-coverage check would accept either location for the
    source clause it is chasing.
    """

    if page.page_type != "content":
        return []
    lines = page.onscreen_text.splitlines()

    def heading_title(line: str) -> str | None:
        title = _module_title(line)
        if title is None:
            return None
        stripped = line.strip()
        if re.search(r"[：:]", stripped) and not stripped.startswith("**"):
            return None
        return title

    module_indents = [_line_indent(line) for line in lines if heading_title(line) is not None]
    if not module_indents:
        return []
    base_indent = min(module_indents)

    detail_lines: list[str] = []
    free_lines: list[str] = []
    for raw in lines:
        line = strip_authoring_group_marker(raw).strip()
        if not line:
            continue
        indent = _line_indent(raw)
        if heading_title(raw) is not None and indent <= base_indent:
            continue
        if indent > base_indent:
            detail_lines.append(line)
        elif heading_title(raw) is None:
            free_lines.append(line)
    if not free_lines:
        return []

    detail_corpus = "\n".join(detail_lines)
    subtitle = page.subtitle.strip()
    hits: list[str] = []
    for line in free_lines:
        if len(re.sub(r"\s+", "", line)) < 8:
            continue
        if detail_corpus:
            score = text_similarity(line, detail_corpus)
            if score >= 0.35:
                hits.append(f"{line}（与模块细项重合 overlap={round(score, 2)}）")
                continue
        if subtitle:
            # Asymmetric containment (how much of the short line's own
            # content already sits inside 副标题), not symmetric Jaccard --
            # 副标题 is much longer than a headline fragment, so a symmetric
            # score dilutes to near zero even on a near-verbatim echo.
            score = _source_statement_overlap(line, subtitle)
            if score >= 0.1:
                hits.append(f"{line}（与副标题重合 overlap={round(score, 2)}）")
    if not hits:
        return []
    return [
        _issue(
            "ONSCREEN_REDUNDANT_RESTATEMENT",
            page,
            "A free-standing on-screen line restates content already covered elsewhere on the slide (a module detail or 副标题).",
            "Remove the restated line, or fold its genuinely new part into the module or 副标题 it overlaps with instead of repeating the same content twice.",
            evidence=tuple(hits),
            severity="warning",
        )
    ]


_MODULE_INDEX_SEPARATOR_RE = re.compile(r"\s*(?:→|⇒|⟶|->|—|–)\s*")
_ORDER_ARROW_RE = re.compile(r"(?:→|⇒|⟶|->)")
_EXPLICIT_ORDER_CHAIN_LABEL_RE = re.compile(
    r"^(?:执行链|流程(?:链)?|推进(?:链|路径|流程)|阶段(?:链|路径|流程)|"
    r"时间(?:轴|链|路径)|实施路径)\s*[：:]"
)
_ORDERED_INTENT_TYPES = PATH_LIKE_INTENT_TYPES | frozenset(
    {"decision_admission", "process", "workflow", "timeline"}
)


def _module_index_restatement_lines(page: ScriptPage) -> tuple[str, ...]:
    """Return free-standing lines that merely enumerate visible modules."""

    module_titles = tuple(
        title.strip()
        for title in page.top_level_module_titles
        if title.strip() and not _MODULE_INDEX_SEPARATOR_RE.search(title)
    )
    if len(module_titles) < 3:
        return ()

    def compact(value: str) -> str:
        return re.sub(r"[^\w\u4e00-\u9fff]+", "", value)

    def matches(segment: str, title: str) -> bool:
        left = compact(segment)
        right = compact(title)
        if not left or not right:
            return False
        if left == right:
            return True
        if min(len(left), len(right)) >= 4 and (left in right or right in left):
            return True
        return text_similarity(left, right) >= 0.72

    lines = [line for line in page.onscreen_text.splitlines() if line.strip()]
    base_indent = min((_line_indent(line) for line in lines), default=0)
    hits: list[str] = []
    for raw in lines:
        if _line_indent(raw) != base_indent:
            continue
        line = strip_authoring_group_marker(raw).strip().lstrip("- ").strip()
        segments = tuple(
            segment.strip().rstrip("。；;，,")
            for segment in _MODULE_INDEX_SEPARATOR_RE.split(line)
            if segment.strip().rstrip("。；;，,")
        )
        if len(segments) < 3:
            continue
        unmatched = list(module_titles)
        matched = True
        for segment in segments:
            match_index = next(
                (
                    index
                    for index, title in enumerate(unmatched)
                    if matches(segment, title)
                ),
                None,
            )
            if match_index is None:
                matched = False
                break
            unmatched.pop(match_index)
        if matched:
            hits.append(line)
    return tuple(dict.fromkeys(hits))


def _explicit_order_chain_lines(page: ScriptPage) -> tuple[str, ...]:
    """Return top-level chains that explicitly claim an ordered meaning."""

    lines = [line for line in page.onscreen_text.splitlines() if line.strip()]
    base_indent = min((_line_indent(line) for line in lines), default=0)
    hits: list[str] = []
    for raw in lines:
        if _line_indent(raw) != base_indent:
            continue
        line = strip_authoring_group_marker(raw).strip().lstrip("- ").strip()
        label = _EXPLICIT_ORDER_CHAIN_LABEL_RE.match(line)
        if label is None:
            continue
        if len(_ORDER_ARROW_RE.findall(line[label.end() :])) >= 2:
            hits.append(line)
    return tuple(dict.fromkeys(hits))


def _contract_declares_order(
    page: ScriptPage,
    contract: dict[str, object] | None,
) -> bool:
    payload = contract or {}
    relations = payload.get("content_relations")
    if not isinstance(relations, list) and page.contract_receipt:
        relations = page.contract_receipt.get("content_relations")
    if isinstance(relations, list) and any(
        isinstance(item, dict)
        and str(item.get("relation") or "") in {"precedes", "flows_to"}
        for item in relations
    ):
        return True
    units = payload.get("content_units")
    if isinstance(units, list) and any(
        isinstance(item, dict)
        and isinstance(item.get("sequence_index"), int)
        and int(item["sequence_index"]) > 0
        for item in units
    ):
        return True
    intent = str(
        payload.get("visual_intent_type")
        or payload.get("semantic_intent_type")
        or page.visual_intent_type
        or ""
    ).strip()
    return intent in _ORDERED_INTENT_TYPES


def _onscreen_module_index_issues(
    page: ScriptPage,
    contract: dict[str, object] | None = None,
) -> list[ScriptQualityIssue]:
    """Reject redundant module indexes and ungrounded ordering signals."""

    if page.page_type != "content":
        return []
    module_index_hits = _module_index_restatement_lines(page)
    explicit_order_hits = _explicit_order_chain_lines(page)
    issues: list[ScriptQualityIssue] = []
    if module_index_hits:
        issues.append(
            _issue(
                "ONSCREEN_MODULE_INDEX_RESTATEMENT",
                page,
                "A free-standing on-screen chain merely repeats three or more top-level module titles.",
                "Remove the duplicate index line and let the module headings carry the page structure; retain a relation line only when it adds a distinct source-supported business predicate.",
                evidence=module_index_hits,
                severity="error",
            )
        )
    order_hits = tuple(dict.fromkeys((*module_index_hits, *explicit_order_hits)))
    if order_hits and not _contract_declares_order(page, contract):
        issues.append(
            _issue(
                "ONSCREEN_UNDECLARED_ORDER_SIGNAL",
                page,
                "An arrow or dash chain imposes an order on peer modules without an explicit ordered source contract.",
                "Remove the order signal, or declare source-supported precedes/flows_to relations, positive sequence_index values, or an ordered visual intent in the authoritative page contract.",
                evidence=order_hits,
                severity="error",
            )
        )
    return issues


def _legacy_onscreen_structure_migration_issues(
    page: ScriptPage,
    contract: dict[str, object] | None,
) -> list[ScriptQualityIssue]:
    if page.page_type != "content" or not isinstance(contract, dict):
        return []
    if (
        str(contract.get("page_consumption_contract_mode") or "legacy") != "required"
        or str(contract.get("onscreen_structure_contract_mode") or "legacy") != "legacy"
    ):
        return []
    return [
        _issue(
            "ONSCREEN_STRUCTURE_CONTRACT_LEGACY",
            page,
            "This required page-consumption contract still uses the legacy on-screen structure contract.",
            "Migrate the authoritative page plan by explicitly authoring onscreen_group_id, onscreen_group_kind, and peer_dimension for visible units; add sequence_index only when the source declares a real order.",
            evidence=(
                "page_consumption_contract_mode=required",
                "onscreen_structure_contract_mode=legacy",
            ),
            severity="warning",
        )
    ]


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
    logic = contract.get("page_logic_contract")
    if isinstance(logic, dict) and isinstance(logic.get("onscreen_expression"), dict):
        # Expression IR has already declared which nodes are states, object
        # groups, and visible relation labels.  Do not recast a parallel-state
        # page as a process solely because a generic resolver sees words such
        # as “闭环” in one subordinate relationship.
        return []
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
    if "→" in page.onscreen_text or "->" in page.onscreen_text:
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
    topic = str(contract.get("topic_category") or "")
    if "必要性" in topic:
        has_constraint = any(
            term in module
            for module in modules[:-1]
            for term in ONSCREEN_NECESSITY_CONSTRAINT_TERMS
        )
        closes = any(term in modules[-1] for term in ONSCREEN_CLOSING_CONNECTORS) if modules else False
        if not has_constraint or not closes:
            issues.append(
                _issue(
                    "ONSCREEN_NECESSITY_CHAIN_INCOMPLETE",
                    page,
                    "The necessity modules do not establish both a concrete constraint and a construction response.",
                    "State the constraint with a concrete predicate such as 难以/尚未/不足, then close with the required construction action and its business effect; explicit causal connectives are not required.",
                    evidence=modules,
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

def _declared_count(text: str, *, architecture_page: bool = False) -> int | None:
    pattern = re.compile(
        r"([二两三四五六七八])(?P<unit>类能力|类任务|类断点|项任务|个模块|步|层)"
    )
    for match in pattern.finditer(text):
        if (
            architecture_page
            and match.group("unit") == "层"
            and not re.match(
                r"(?:模块|能力模块|业务模块|架构模块|同级模块|并列模块)",
                text[match.end() :],
            )
        ):
            continue
        return COUNT_WORDS[match.group(1)]
    return None

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

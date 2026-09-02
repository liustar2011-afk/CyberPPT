"""Visual presentation decisions and page-logic contracts for ImageGen handoff."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from cyberppt.script_quality_contract import ScriptPage
from scripts.imagegen_pipeline.deliverable_prompt import _compile_style09_contract
from scripts.imagegen_pipeline.handoff.semantics import resolve_page_visual_intent
from scripts.imagegen_pipeline.handoff.text import _selected_content_first_style
from scripts.imagegen_pipeline.style_library import _strip_style09_registry_meta


STYLE_COLOR_LABELS = (
    ("background", "背景"),
    ("title", "主文字"),
    ("body", "正文"),
    ("secondary", "次级文字"),
    ("divider", "线条与分隔"),
    ("accent", "强调色"),
)

# ImageGen must receive the governing Style 09 text-first constraints, not only
# its palette and a short mood signature.  These fields are compact enough to
# preserve the intended presentation language while preventing a stale project
# lock from drifting into scenes, illustrations, or icon treatment as defaults.
CONTENT_FIRST_STYLE_RULE_FIELDS: tuple[str, ...] = (
    "scope_rule",
    "content_visual_rule",
)

LAYOUT_MOTIFS = (
    "control_room_bridge",
    "evidence_landscape",
    "decision_canvas",
    "process_atlas",
    "layered_system",
)
SCENE_ROLES = ("primary_scene", "supporting_evidence", "no_scene")
VISUAL_MEDIA = (
    "editorial_typographic",
    "editorial_dense",
    "semantic_scene",
    "data_visualization",
    "document_material",
    "spatial_system",
)
MOTIF_CANDIDATES: dict[str, tuple[str, str]] = {
    "boundary_guardrail": ("decision_canvas", "evidence_landscape"),
    "decision_admission": ("decision_canvas", "evidence_landscape"),
    "comparison": ("decision_canvas", "evidence_landscape"),
    "crosscutting_chain": ("control_room_bridge", "layered_system"),
    "hierarchy_support": ("layered_system", "control_room_bridge"),
    "capability_relationship": ("layered_system", "control_room_bridge"),
    "phase": ("process_atlas", "evidence_landscape"),
    "path_chain": ("process_atlas", "control_room_bridge"),
    "causal": ("process_atlas", "evidence_landscape"),
    "closed_loop": ("control_room_bridge", "process_atlas"),
    "scenario_application": ("control_room_bridge", "process_atlas"),
    "judgment_evidence": ("evidence_landscape", "decision_canvas"),
    "multi_semantic_foundation": ("evidence_landscape", "decision_canvas"),
}
DEFAULT_SCENE_ROLE_BY_MOTIF = {
    "control_room_bridge": "supporting_evidence",
    "evidence_landscape": "no_scene",
    "decision_canvas": "no_scene",
    "process_atlas": "no_scene",
    "layered_system": "no_scene",
}

DEFAULT_SCENE_ROLE_BY_RELATION = {
    "scenario_application": "primary_scene",
}


@dataclass(frozen=True)
class PresentationDecision:
    """Content-led visual variation decision recorded with every prompt."""

    layout_motif: str
    scene_role: str
    source: str
    reason: str
    visual_medium: str = "editorial_typographic"

    def to_dict(self) -> dict[str, str]:
        return {
            "layout_motif": self.layout_motif,
            "scene_role": self.scene_role,
            "source": self.source,
            "reason": self.reason,
            "visual_medium": self.visual_medium,
        }


def render_presentation_contract(
    page: ScriptPage,
    decision: PresentationDecision,
) -> str:
    medium_contracts = {
        "editorial_typographic": (
            "采用编辑排版型媒介：以准确中文排版、尺度、位置、间距、对齐、密度和留白表达关系。"
            "只允许一处克制的深蓝形面、局部数据纹理或抽象材料层作为视觉重心。"
            "禁止完整流程、连续节点、逐项连接线、架构层、技术面板、光束、四栏结构和物件隐喻。"
        ),
        "editorial_dense": (
            "采用高密度编辑媒介：完整保留正文、数字、限定条件与业务边界，使用主文、旁注、事实条和层级缩进组织信息。"
            "允许两到三个不等权信息区，但禁止大面积无效留白、单一大色块、四条摘要替代全文、四栏均分、流程图和软件架构图。"
        ),
        "semantic_scene": (
            "采用条件性语义场景媒介：场景必须直接解释不可替代的业务动作或物理环境，"
            "并保持局部、低对比、从属于正文和主关系。"
        ),
        "data_visualization": (
            "采用数据可视化媒介：以可核验的数据关系、直接标注和清晰比较为主体，"
            "不得用装饰插画或技术面板替代数据。"
        ),
        "document_material": (
            "采用克制的文档材料媒介：只呈现与证据类型直接相关的局部纸张、条文或批注关系，"
            "禁止复古档案、牛皮纸、文件柜和怀旧拼贴。"
        ),
        "spatial_system": (
            "采用浅层空间系统媒介：仅表达真实存在的部署、区域或设施关系，"
            "禁止等距三维组件堆叠、科技发光和软件架构图。"
        ),
    }
    lines = [
        (
            "【人工版式覆盖｜不上屏】"
            if decision.source == "script"
            else "【视觉媒介路由｜不上屏】"
        ),
        f"媒介类型：{decision.visual_medium}。",
        medium_contracts[decision.visual_medium],
        f"场景角色：{page.scene_role.strip() or decision.scene_role}。",
    ]
    if decision.source == "script":
        lines.extend(
            (
                f"人工版式母题：{page.layout_motif.strip() or decision.layout_motif}。",
                "人工覆盖不得删除完整上屏内容或改变业务关系。",
            )
        )
    return "\n".join(lines)


def resolve_visual_medium(page: ScriptPage, relation: str) -> str:
    """Choose the page medium independently from palette and layout motif."""

    semantic_text = "\n".join(
        part
        for part in (
            page.title,
            page.main_message,
            page.onscreen_judgment,
            page.onscreen_text,
        )
        if part
    )
    if relation == "scenario_application":
        return "semantic_scene"
    if re.search(r"同比|环比|占比|趋势|增长率|下降率|柱状|折线|散点|分布", semantic_text):
        return "data_visualization"
    if re.search(r"条款|政策原文|批注|公文|合同|证据材料", semantic_text):
        return "document_material"
    if re.search(r"厂区|站房|机房|设备部署|区域部署|物理空间|生产现场", semantic_text):
        return "spatial_system"
    onscreen_size = len(re.sub(r"\s+", "", page.onscreen_text))
    prose_size = len(re.sub(r"\s+", "", page.full_prose))
    if prose_size >= max(480, onscreen_size * 3):
        # Kept for diagnostics / presentation metadata only. Content-first
        # prompts must not promote this into a must-render medium contract.
        return "editorial_dense"
    return "editorial_typographic"


def select_dense_supporting_facts(page: ScriptPage, limit: int = 10) -> tuple[str, ...]:
    """Recover high-value facts from approved full prose for dense editorial pages."""

    if resolve_visual_medium(page, "judgment_evidence") != "editorial_dense":
        return ()
    onscreen_compact = re.sub(r"\s+", "", page.onscreen_text)
    candidates: list[tuple[int, int, str]] = []
    order = 0
    dense_source = "\n".join(part for part in (page.full_prose, page.evidence_map) if part)
    for raw in re.split(r"(?<=[。！？；])\s*|\n+", dense_source):
        sentence = raw.strip(" -*\t\r\n")
        sentence = re.sub(r"→S\d{3}[；;。]?\s*$", "", sentence).strip()
        sentence = re.sub(r"^证据映射：", "", sentence).strip()
        compact = re.sub(r"\s+", "", sentence)
        if not sentence or len(compact) < 16 or len(compact) > 110:
            continue
        if compact in onscreen_compact or compact == re.sub(r"\s+", "", page.main_message):
            continue
        if sentence.startswith(("从业务关系看", "具体来看", "因此", "业务含义")):
            continue
        score = 0
        if re.search(r"\d", sentence):
            score += 3
        if re.search(r"权限|授权|安全等级|有效期|撤销|隔离|受控接口|独立数据库|独立数据空间", sentence):
            score += 6
        if re.search(r"题目|教材|教案|检索|版本|质量|组织标识|行级安全", sentence):
            score += 2
        if score < 3:
            continue
        candidates.append((-score, order, sentence))
        order += 1
    selected: list[str] = []
    selected_keys: set[str] = set()
    for _, _, sentence in sorted(candidates):
        key = re.sub(r"[\s。；;，,]+", "", sentence)
        if key not in selected_keys:
            selected.append(sentence.rstrip("。；;"))
            selected_keys.add(key)
        if len(selected) >= limit:
            break
    return tuple(selected)


def resolve_presentation_decision(
    page: ScriptPage,
    relation: str,
    prior_decisions: tuple[PresentationDecision, ...] = (),
) -> PresentationDecision:
    """Choose a presentation motif from this page's content relationship only."""

    explicit_motif = page.layout_motif.strip()
    explicit_scene = page.scene_role.strip()
    if explicit_motif and explicit_motif not in LAYOUT_MOTIFS:
        raise ValueError(f"{page.page_id} has unsupported 版式母题: {explicit_motif}")
    if explicit_scene and explicit_scene not in SCENE_ROLES:
        raise ValueError(f"{page.page_id} has unsupported 场景角色: {explicit_scene}")

    candidates = MOTIF_CANDIDATES.get(relation, ("evidence_landscape", "decision_canvas"))
    # Kept in the signature for backward compatibility with batch callers. It must
    # not influence the decision: page order and neighboring layouts are not content.
    _ = prior_decisions
    motif = explicit_motif or candidates[0]
    scene_role = explicit_scene or DEFAULT_SCENE_ROLE_BY_RELATION.get(
        relation,
        DEFAULT_SCENE_ROLE_BY_MOTIF[motif],
    )
    source = "script" if explicit_motif or explicit_scene else "auto"
    reason = (
        "explicit page presentation override"
        if source == "script"
        else f"{relation} candidates: {', '.join(candidates)}"
    )
    visual_medium = resolve_visual_medium(page, relation)
    if visual_medium != "semantic_scene" and not explicit_scene:
        scene_role = "no_scene"
    return PresentationDecision(motif, scene_role, source, reason, visual_medium)


def render_content_first_style_contract(
    style_lock: Path,
    *,
    semantic_tags: frozenset[str] | None = None,
) -> str:
    """Render a compact, self-contained style contract from the selected style."""

    style = _selected_content_first_style(style_lock)
    if int(style.get("id") or 0) == 9:
        description = _strip_style09_registry_meta(
            str(style.get("prompt_contract") or "").strip()
        )
        description = _compile_style09_contract(description, semantic_tags)
        lines = [
            "【视觉风格｜不上屏】",
            description,
        ]
        signature = style.get("imagegen_signature")
        if isinstance(signature, list):
            lines.extend(
                str(rule).strip()
                for rule in signature
                if isinstance(rule, str) and rule.strip()
            )
        return "\n".join(line for line in lines if line)
    colors = style["colors"]
    color_parts = [
        f"{label} {str(colors[key]).strip()}"
        for key, label in STYLE_COLOR_LABELS
        if str(colors.get(key) or "").strip()
    ]
    known_keys = {key for key, _ in STYLE_COLOR_LABELS}
    color_parts.extend(
        f"{key} {str(value).strip()}"
        for key, value in colors.items()
        if key not in known_keys and str(value).strip()
    )
    lines = [
        "【视觉风格｜不上屏】",
        f"适用语境：{str(style.get('scenario') or '').strip()}。",
        f"色彩角色：{'；'.join(color_parts)}。",
    ]
    rule_fields = CONTENT_FIRST_STYLE_RULE_FIELDS
    style_rules: list[str] = []
    for field in rule_fields:
        value = str(style.get(field) or "").strip()
        if not value:
            continue
        style_rules.append(
            f"默认文字渲染模式：{value}。"
            if field == "default_text_render_mode"
            else value
        )
    if style_rules:
        lines.append("风格约定（仅约束视觉表达，不覆盖本页内容与主导关系）：")
        lines.extend(f"- {rule}" for rule in style_rules)
    signature = style.get("imagegen_signature")
    if isinstance(signature, list):
        compact_signature = [
            str(rule).strip()
            for rule in signature
            if isinstance(rule, str) and rule.strip()
        ]
        if compact_signature:
            lines.append("审美签名：")
            lines.extend(f"- {rule}" for rule in compact_signature)
    lines.append("整体呈现现代中文高端政企汇报设计气质，编辑式克制、业务清晰。")
    lines.append("如出现人物，仅使用远景、背影或局部，不出现可识别面孔。")
    return "\n".join(lines)


def resolve_visual_center(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
) -> str:
    """Return page-specific visual-center guidance, if any."""

    for source in (
        (visual_intent_override or {}).get("visual_center"),
        (visual_context or {}).get("visual_center"),
        getattr(page, "visual_center", ""),
    ):
        value = str(source or "").strip()
        if value:
            return value
    receipt = page.contract_receipt
    if isinstance(receipt, dict):
        value = str(receipt.get("visual_center") or "").strip()
        if value:
            return value
    return ""


def render_visual_center_contract(
    page: ScriptPage,
    *,
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
) -> str:
    """Visual-center text is authoring metadata only — never inject into ImageGen.

    Drawing how-to (主视觉落点 / 构图落点) must not reach the model. Keep
    ``resolve_visual_center`` for Stage1 / diagnostics.
    """

    return ""


def resolve_visual_carrier(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
) -> str:
    """Return page-specific visual-carrier guidance, if any."""

    for source in (
        (visual_intent_override or {}).get("visual_carrier"),
        (visual_context or {}).get("visual_carrier"),
        page.visual_carrier,
    ):
        value = str(source or "").strip()
        if value:
            return value
    receipt = page.contract_receipt
    if isinstance(receipt, dict):
        value = str(receipt.get("visual_carrier") or "").strip()
        if value:
            return value
    return ""


def render_visual_carrier_contract(
    page: ScriptPage,
    *,
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
) -> str:
    """Visual-carrier text is authoring metadata only — never inject into ImageGen.

    Page scripts may still store ``视觉载体`` for humans; ImageGen must not
    receive drawing recipes, icon bans, or composition bans from this field.
    """

    return ""


def compact_visual_structure_for_logic(visual: str) -> str:
    """Shrink authoring 视觉结构 to one understanding line for ImageGen."""

    text = re.sub(r"\s+", " ", (visual or "")).strip()
    if not text:
        return ""
    text = re.sub(r"[；;]\s*一级模块与上屏文字一致。?\s*$", "", text).strip()
    text = re.sub(r"[；;]\s*$", "", text).strip()
    return text


def _render_onscreen_expression_ir(page: ScriptPage) -> list[str]:
    """Render authored expression semantics without turning them into layout recipes."""

    receipt = page.contract_receipt
    if not isinstance(receipt, dict):
        return []
    expression = receipt.get("onscreen_expression_ir")
    if not isinstance(expression, dict):
        logic = receipt.get("page_logic_contract")
        expression = logic.get("onscreen_expression") if isinstance(logic, dict) else None
    if not isinstance(expression, dict):
        return []
    nodes = [item for item in expression.get("nodes") or [] if isinstance(item, dict)]
    names = {
        str(item.get("id") or ""): f"{item.get('role')}／{item.get('render')}"
        for item in nodes
        if str(item.get("id") or "")
    }
    order = [str(item) for item in expression.get("reading_order") or [] if str(item)]
    lines = [
        f"上屏表达模式：{str(expression.get('pattern') or '').strip()}。",
        "阅读顺序：" + " → ".join(names.get(item, item) for item in order) + "。",
    ]
    edge_lines = []
    for edge in expression.get("edges") or []:
        if not isinstance(edge, dict):
            continue
        label = str(edge.get("visible_label") or "").strip()
        source = names.get(str(edge.get("from") or ""), str(edge.get("from") or ""))
        target = names.get(str(edge.get("to") or ""), str(edge.get("to") or ""))
        if label and source and target:
            edge_lines.append(f"{source} 以“{label}”连接 {target}")
    if edge_lines:
        lines.append("可见关系：" + "；".join(edge_lines) + "。")
    return lines


def render_page_logic_contract(
    page: ScriptPage,
    *,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    include_structure: bool = True,
) -> tuple[str, str, str]:
    """Render relationship type and optional authoring structure metadata.

    Returns ``(relation, intent_source, contract)``.
    The ``结构形态`` field is authoring metadata and may contain concrete layout
    recipes (matrix rows, swim lanes, node chains, etc.).  Style-specific
    compilers can set ``include_structure=False`` to keep only the semantic
    relation and avoid turning a reusable style surface into a page-by-page
    infographic recipe. Business meaning stays in ``页面语义关系`` and the
    on-screen text reference.
    """

    relation, intent_source = resolve_page_visual_intent(
        page,
        page_mission,
        context=visual_context,
        override=visual_intent_override,
    )
    relation_labels = {
        "boundary_guardrail": "边界护栏",
        "crosscutting_chain": "纵向主链与横向贯穿",
        "hierarchy_support": "分层支撑",
        "decision_admission": "决策准入",
        "comparison": "对照",
        "scenario_application": "场景应用",
        "multi_semantic_foundation": "共同支撑",
        "causal": "因果传导",
        "closed_loop": "闭环",
        "phase": "阶段递进",
        "path_chain": "路径转化",
        "capability_relationship": "对象与能力关系",
        "judgment_evidence": "判断—证据",
    }
    lines = [
        "【页面逻辑｜不上屏】",
        f"主导关系：{relation_labels[relation]}。",
    ]
    if page.content_relations:
        drawable_relations = [
            {key: value for key, value in relation_item.items() if key != "source_refs"}
            for relation_item in page.content_relations
        ]
        lines.append("来源关系：" + json.dumps(drawable_relations, ensure_ascii=False, separators=(",", ":")))
    lines.extend(_render_onscreen_expression_ir(page))
    if include_structure:
        structure = compact_visual_structure_for_logic(page.visual_structure)
        if structure:
            lines.append(f"结构形态：{structure}")
    return relation, intent_source, "\n".join(lines)


__all__ = (
    "PresentationDecision",
    "compact_visual_structure_for_logic",
    "render_content_first_style_contract",
    "render_page_logic_contract",
    "render_visual_carrier_contract",
    "render_visual_center_contract",
    "resolve_presentation_decision",
    "resolve_visual_carrier",
    "resolve_visual_center",
    "resolve_visual_medium",
    "select_dense_supporting_facts",
)

#!/usr/bin/env python3
"""Build reviewable ImageGen handoff prompts from approved final scripts.

Before any ImageGen call, CyberPPT must:
1. preserve the approved page meaning and drawable layer;
2. compile plaintext prompts with a tone-only visual contract;
3. save them under workbench/prompts/imagegen/;
4. wait for user modify-or-approve.

Page mission, core meaning, and source-supported content relations are passed before 上屏文字
so the model can understand the page responsibility without inventing an argument.
They are context fields, not extra labels to render; the drawable text layer remains 上屏文字.
The default content-first compiler sends the page task, core judgment, locked on-screen copy,
and a compact page logic contract. Each page remains a standalone ImageGen prompt, while source
prose and repeated design theory stay out of the model context.
Legacy compilers remain available for comparison and rollback.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from cyberppt.commands.script_gate import stage_script
from cyberppt.script_quality_contract import (
    ScriptPage,
    strip_authoring_group_marker,
    parse_script_markdown,
    resolve_judgment_mode,
)
from cyberppt.semantic_intent import (
    SemanticIntentDecision,
    canonicalize_intent,
    resolve_semantic_intent,
    validate_semantic_structure,
)
from cyberppt.composition_resolver import resolve_composition, validate_composition
from cyberppt.visual_carrier_resolver import (
    select_visual_carrier,
    validate_visual_carrier,
)
from scripts.dual_image_overlay.creative_brief import (
    CreativeBrief,
    build_creative_brief,
    render_creative_brief,
)
from scripts.dual_image_overlay.deliverable_prompt import (
    PageBlock,
    _compile_style09_contract,
    _style09_page_semantic_tags,
    assert_deliverable_prompt,
    render_prompt,
)
from scripts.dual_image_overlay.prompt_diagnostics import (
    PagePromptDiagnostics,
    analyze_prompt,
    write_batch_diagnostics,
    write_compiler_comparison,
)
from scripts.dual_image_overlay.style_library import (
    _strip_style09_registry_meta,
    load_style_lock,
    resolve_default_style,
)
from scripts.dual_image_overlay.page_semantics import (
    PageSemanticContext,
    derive_page_semantics,
)
from scripts.dual_image_overlay.prompt_compiler import (
    CompiledPagePrompt,
    DEFAULT_PROMPT_COMPILER,
    DEFAULT_TEXT_RENDER_MODE,
    PROMPT_COMPILERS,
    TEXT_RENDER_MODES,
    validate_prompt_compiler,
    validate_text_render_mode,
)
from scripts.dual_image_overlay.script_parser import (
    load_page_missions,
    load_page_visual_contexts,
    load_page_visual_intent_overrides,
)
from scripts.dual_image_overlay.build_transaction import atomic_write_text, build_lock

EVIDENCE_ID_RE = re.compile(r"S\d{3}")
IMAGEGEN_CANVAS_CONTRACT = """【输出尺寸｜不上屏】
画布尺寸固定为 2048×1024 像素（2:1 横向）。必须按该尺寸与比例构图，不得输出 16:9、4:3、方形或其他比例。"""
IMAGEGEN_CHROME_BAN_CONTRACT = """【模板层禁绘｜不上屏】
正文区图只画业务内容，不绘制页面标题、副标题、页码、页面序号（第N页 / Pxx / Slide N）、Logo、页脚或母版装饰线。
标题与副标题由 PPT 模板文字层承载，不得在图内另起通栏标题区。
【锁定关键文字】【完整上屏内容】中的业务编号与模块名（如 01｜）必须保留；禁止新增与锁定文案无关的序号条、页码章或装饰编号。"""
SEMANTIC_VISUAL_CHROME_CONTRACT = """【模板层禁绘｜不上屏】
正文区图只画业务语义底图，不绘制页面标题、副标题、Logo、页脚、页码、页面序号、母版装饰线或完整正文。正文和事实文字由后续 PPT 可编辑文字层承载。不要把提示词字段名、模块编号、调试信息、伪中文或新增标签画入图片。"""
CONTENT_FIRST_ONSCREEN_STORY_CONTRACT = """【结论句要求｜不上屏】
如【锁定关键文字】含正文结论句，该句是正文结论句，不是页面标题；不得通栏放大或添加标题竖线、横线等装饰。
允许调整换行和文字层级；画面必须参与表达页面逻辑，不得退化为文字排版加装饰图片。"""
CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT = """【核心意思表达要求｜不上屏】
本页没有要求逐字上屏的正文结论句；不得从【页面任务】【核心意思】或【页面逻辑】中自行抽取整句作为页面标题或通栏结论。
【完整上屏内容】仍须完整表达；用文字层级、业务结构、对象关系和必要画面共同组织核心意思。"""
CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT = """【核心意思表达要求｜不上屏】
本页没有要求逐字上屏的正文结论句；不得从【页面任务】【核心意思】或【页面逻辑】中自行抽取整句作为页面标题或通栏结论。
【锁定关键文字】中的业务标签和关键事实必须全部上屏；【完整上屏内容】仍须完整表达，用文字层级、业务结构、对象关系和必要画面共同组织核心意思。"""
CONTENT_FIRST_PAGE_MISSION_LABEL = "页面任务："
CONTENT_FIRST_CORE_MEANING_LABEL = "核心意思："
# Compatibility alias for extensions importing the old constant.
CONTENT_FIRST_CORE_JUDGMENT_LABEL = CONTENT_FIRST_CORE_MEANING_LABEL
SEMANTIC_VISUAL_TEXT_CONTRACT = """【语义视觉模式｜默认不上屏正文】
ImageGen 只负责把页面事实关系转译成有业务含义的场景、对象、动作、空间和结果状态；不要把完整正文逐字排版进图片。正文、数字和主体名称由后续 PPT 可编辑文字层完整承载。允许极少量短标签（0—3 个）贴附在对应对象旁，仅在它能显著帮助识别对象时使用；默认无可读长句、无界面伪文字、无新增标签。"""
SEMANTIC_VISUAL_FACTS_HEADER = "【事实真值锁｜仅供理解，不在图内排版】"
SEMANTIC_VISUAL_BRIEF_HEADER = "【视觉语义参考｜用对象和关系表达，不照抄文字】"
# Status asides that must not be painted as core on-screen claims.
# Planning decks argue the proposed solution; do not restamp "not yet fact" on every page.
ONSCREEN_ASIDE_RE = re.compile(
    r"[；;，,]?\s*(?:"
    r"不等于[^。；;\n]*|"
    r"并不等于[^。；;\n]*|"
    r"并不等同于[^。；;\n]*|"
    r"不能只看[^。；;\n]*|"
    r"不写成[^。；;\n]*|"
    r"也不等于[^。；;\n]*|"
    r"也不预设[^。；;\n]*|"
    r"分期建议≠[^。；;\n]*|"
    r"缺口清单≠[^。；;\n]*|"
    r"自动化≠[^。；;\n]*|"
    r"稳定接入尚非[^。；;\n]*|"
    r"尚非既成事实[^。；;\n]*|"
    r"算法栈仍待[^。；;\n]*|"
    r"仍待(?:摸底|论证|验证|基线)[^。；;\n]*|"
    r"讨论稿不代替[^。；;\n]*|"
    r"不升格为已批准[^。；;\n]*|"
    r"缺测量与验证前不能写死[^。；;\n]*|"
    r"任一档均非已审定[^。；;\n]*|"
    r"不能直接作最终预算[^。；;\n]*|"
    r"尚未作为完备工程方案[^。；;\n]*"
    r")"
)

VISUAL_INTENT_SIGNALS: dict[str, tuple[tuple[str, int], ...]] = {
    "boundary_guardrail": (
        ("边界护栏", 10),
        ("职责边界", 9),
        ("不替代", 9),
        ("不承担", 8),
        ("范围边界", 8),
        ("非目标", 7),
    ),
    "hierarchy_support": (
        ("分层支撑", 10),
        ("上下依赖", 9),
        ("支撑底座", 9),
        ("贯穿保障", 8),
        ("统一托底", 10),
        ("底部设置统一支撑", 10),
        ("高可用支撑", 7),
        ("需求牵引层", 7),
        ("可信底座", 7),
        ("五层", 5),
    ),
    "crosscutting_chain": (
        ("纵向关系", 10),
        ("横向治理贯穿", 10),
        ("横向贯穿", 8),
        ("纵向主链", 8),
        ("贯穿每层", 7),
    ),
    "decision_admission": (
        ("准入", 8),
        ("筛选依据", 8),
        ("如何选定", 7),
        ("首期聚焦", 8),
        ("选择条件", 7),
        ("成熟度条件", 6),
        ("后续纳入", 5),
    ),
    "comparison": (
        ("对比", 7),
        ("比较", 7),
        ("差异", 6),
        ("优劣", 6),
        ("高于", 4),
        ("低于", 4),
        ("相较", 4),
    ),
    "scenario_application": (
        ("重点场景", 6),
        ("业务场景", 5),
        ("应用方向", 7),
        ("应用场景", 7),
        ("推进条件", 4),
        ("业务价值", 3),
    ),
    "multi_semantic_foundation": (
        ("工作基础", 8),
        ("现实基础", 8),
        ("已有基础", 7),
        ("共同基础", 7),
        ("持续性工作基础", 9),
    ),
    "causal": (
        ("为什么", 7),
        ("原因", 7),
        ("导致", 6),
        ("带来", 4),
        ("不匹配", 7),
        ("不足", 5),
        ("变化如何改变", 8),
        ("问题与影响", 6),
    ),
    "closed_loop": (
        ("闭环", 9),
        ("闭环回流", 10),
        ("版本化回流", 8),
        ("回到起点", 9),
        ("输入、处理、输出", 9),
        ("输入、结果、验证、反馈", 9),
        ("反馈与复盘", 7),
        ("持续校正", 6),
        ("稳定生产能力", 5),
        ("工作流：", 7),
        ("效果回收", 7),
        ("四层贯通", 8),
        ("持续迭代", 7),
    ),
    "phase": (
        ("分期推进", 9),
        ("分阶段", 8),
        ("建设节奏", 8),
        ("按什么节奏", 8),
        ("当前、近期和中长期", 9),
        ("近期首先", 6),
        ("先开展", 4),
        ("再拓展", 4),
        ("阶段推进", 9),
    ),
    "path_chain": (
        ("贯穿主链", 12),
        ("转化主链", 10),
        ("业务主链", 9),
        ("路径转化", 9),
        ("先归一", 8),
        ("再由分层", 7),
        ("依次完成", 5),
    ),
    "capability_relationship": (
        ("能力协同", 8),
        ("协同支撑", 8),
        ("双侧协同", 10),
        ("跨系统协同", 9),
        ("统一网关", 7),
        ("领域接口", 6),
        ("共同支撑", 7),
        ("能力关系", 8),
        ("能力体系", 7),
        ("能力底座", 7),
        ("能力组成", 8),
        ("由哪些部分组成", 8),
        ("平台稳定承载", 7),
        ("共性能力", 5),
        ("分工关系", 10),
        ("统一治理连接", 9),
        ("共享知识", 7),
    ),
}

VISUAL_INTENT_PRIORITY = (
    "boundary_guardrail",
    "crosscutting_chain",
    "hierarchy_support",
    "multi_semantic_foundation",
    "comparison",
    "closed_loop",
    "path_chain",
    "phase",
    "capability_relationship",
    "decision_admission",
    "scenario_application",
    "causal",
    "judgment_evidence",
)

# Prefixes taken from the script's 视觉结构 field. When present they outrank
# keyword scoring so authoring labels like「贯穿主链」are not lost.
VISUAL_STRUCTURE_HARD_HINTS: tuple[tuple[str, str], ...] = (
    ("贯穿主链", "path_chain"),
    ("路径转化", "path_chain"),
    ("转化主链", "path_chain"),
    ("闭环回流", "closed_loop"),
    ("分层剖面", "hierarchy_support"),
    ("受控边界", "boundary_guardrail"),
    ("阶段推进", "phase"),
    ("分期推进", "phase"),
    ("非对称对照", "comparison"),
    ("双侧协同", "capability_relationship"),
    ("主体泳道", "hierarchy_support"),
    ("汇聚引擎输出", "capability_relationship"),
    ("判断证据", "judgment_evidence"),
)

_CROSSCUT_HARD_HINT_MARKERS = (
    "横向治理贯穿",
    "横向贯穿",
    "贯穿每层",
    "横切",
    "沿主链贯穿",
    "贯穿式",
)
_CROSSCUT_HARD_HINT_PREFIXES = (
    "贯穿主链",
    "分层剖面",
    "转化主链",
    "路径转化",
)

TEXT_IN_COMPOSITION_RULE = (
    "全部必上屏文字以冷静的场内面板、标注或附着标签组织到主导视觉结构上；"
    "不要把完整文字层放到独立的左右栏或上下导轨。"
)
DETACHED_TEXT_RAIL_AVOID = (
    "独立通高文字栏、文字导轨，或文字区与图片区彼此分离的版式"
)

# Canonical page-logic spatial rules. content-first【页面逻辑】and the legacy
# visual-intent path both read recommended_composition / avoid_on_this_page
# from this single source.
VISUAL_INTENT_TEMPLATES: dict[str, dict[str, str]] = {
    "boundary_guardrail": {
        "visual_thesis": "用主体能力与外围护栏的关系证明范围和职责清晰。",
        "decision_relationship": (
            "核心能力占据既定范围，非目标与约束构成次级护栏，而不是另一组对等模块。"
        ),
        "recommended_composition": (
            "让核心能力占据主要视觉权重，把边界压缩到外围、底部或侧向护栏，并明确保持从属地位。"
        ),
        "avoid_on_this_page": (
            "对半的可做/不可做对照、警告卡墙，或把边界做成与主能力等权的服务对象。"
        ),
    },
    "hierarchy_support": {
        "visual_thesis": "用上层业务结果与下层支撑能力的依赖关系证明体系能够成立。",
        "decision_relationship": (
            "上层结果依赖下层能力；共享保障作为底座或横向支撑，而不是软件技术堆叠。"
        ),
        "recommended_composition": (
            "构建非对称的支撑场域，使上层业务结果、中层控制与横向保障彼此可见依赖。"
            "用叠合、包围、承压、纵深或承托边缘表现支撑；避免居中徽章、同心台座、等高层条或堆叠架构。"
        ),
        "avoid_on_this_page": (
            "软件架构堆叠、等高分层条、一层一卡，或孤立的能力清单。"
        ),
    },
    "crosscutting_chain": {
        "visual_thesis": "用纵向转化主链与横向贯穿能力的共同作用证明体系完整。",
        "decision_relationship": (
            "主模块沿一条方向链发生状态变化，同时有一个共享治理能力横断并约束每个阶段；"
            "两者都不是对等模块清单。"
        ),
        "recommended_composition": (
            "构建一个非对称的双向关系场：让主链在不等权节点上弯折、抬升、收窄、展开或变换材质；"
            "再把横向贯穿力织入同一批节点，形成连续的横断缝、承压线或内嵌带。"
            "每个模块名称与正文只附着一次；关系句放在交汇或状态变化处，不另开摘要栏。"
        ),
        "avoid_on_this_page": (
            "堆叠架构、等权水平分层、矩阵/泳道、一阶段一卡、把横向贯穿力做成第五张对等卡、"
            "重复模块标签，或纵向流程与横向治理拆成两套图。"
        ),
    },
    "decision_admission": {
        "visual_thesis": "用选择依据与后续准入条件证明当前决策合理。",
        "decision_relationship": (
            "选择依据共同支撑初始选择；后续事项留在明确准入门槛之后。把它当作决策结构，"
            "而不是实施流程。"
        ),
        "recommended_composition": (
            "使用有权重的决策场：让已选初始范围占据主视觉，把紧凑依据绑在该选择上，"
            "并把后续范围放到次级准入区。"
        ),
        "avoid_on_this_page": (
            "五个等权依据卡、泛化三步流程、时间线或情景缩略图墙。"
        ),
    },
    "comparison": {
        "visual_thesis": "用共同维度下的差异和主次证明本页判断。",
        "decision_relationship": (
            "对照项共享同一维度；呈现对比与主次，但不发明内容未支持的排序。"
        ),
        "recommended_composition": (
            "使用同一基准下的对齐对照场，直接对置证据，并在内容明确主次处拉开视觉权重。"
        ),
        "avoid_on_this_page": (
            "未对齐的卡片、装饰性 versus 符号、虚构分数，或缺少共同维度的对照。"
        ),
    },
    "scenario_application": {
        "visual_thesis": "用真实业务场景、业务价值与进入条件证明应用方向。",
        "decision_relationship": "业务语境连接应用方向、当前阶段与进入条件。",
        "recommended_composition": (
            "使用一个完整的真实工作场景，把业务价值与准入条件嵌进场景中相关部位。"
        ),
        "avoid_on_this_page": (
            "产品功能陈列、情景缩略图墙、装饰性行业照片，或无关技术界面。"
        ),
    },
    "multi_semantic_foundation": {
        "visual_thesis": "用多项现实基础共同支撑本页判断。",
        "decision_relationship": "不同基础彼此强化，共同构成可持续的工作底座。",
        "recommended_composition": (
            "用一个主导的综合视觉载体表达共同支撑关系。"
            "仅在能澄清关系处使用画面；数量、位置及与模块的对应由页面视觉结构决定，不按基础项数量机械配图。"
        ),
        "avoid_on_this_page": (
            "一张泛化办公/会议室/控制室/行业图承载全部含义；一项基础一张图；"
            "逐行图文对应；文字区与图片区分离；等权图片卡；或无关装饰图。"
        ),
    },
    "causal": {
        "visual_thesis": "用原因到业务后果的传导关系证明行动必要性。",
        "decision_relationship": "原因或变化通向业务后果，并解释为何需要行动。",
        "recommended_composition": (
            "使用一条由因到果的单向路径，以业务后果为主锚点，并把紧凑因果证据附着在路径上。"
        ),
        "avoid_on_this_page": "无关事实罗列、等权卡片或装饰性趋势箭头。",
    },
    "closed_loop": {
        "visual_thesis": "用输入、结果、验证与反馈的闭环证明业务能够持续改进。",
        "decision_relationship": "使用显式输入、结果、校验与反馈的闭环关系。",
        "recommended_composition": (
            "使用一条连续但非圆环的编辑式走势，通过回折、回返、叠合或状态变化让循环可见。"
            "把输入、结果、校验与反馈嵌在走势上不等权的位置，不要做成等距阶段。"
            "闭环关系句或业务含义句放在回返、叠合或汇合处作冷静标注，不另开底部摘要区；避免图标节点闭环。"
        ),
        "avoid_on_this_page": "软件流程图、生命周期图标环，或编号行政管理步骤。",
    },
    "phase": {
        "visual_thesis": "用阶段目的与准入条件的递进证明实施节奏。",
        "decision_relationship": (
            "当前、近期与后续工作构成带明确准入条件的阶段递进。"
        ),
        "recommended_composition": (
            "使用有权重的阶段轨迹：让当前或近期决策占据主权重，后续阶段作为次级、有条件的推进。"
        ),
        "avoid_on_this_page": "等权时间线、泛化路线图箭头或里程碑装饰。",
    },
    "path_chain": {
        "visual_thesis": "用上游输入到下游能力或应用出口的转化路径证明底座如何成立。",
        "decision_relationship": (
            "业务对象沿一条主链发生状态变化；质量、治理或生命周期过程可以横切或承托主链，"
            "但不是价值路径的终端对等节点。"
        ),
        "recommended_composition": (
            "构建一条清晰阅读路径，在接入、归一、服务供给与应用出口处形成不等权节点；"
            "模块名附着在路径的不同节点上；把横切的质量或生命周期工作做成从属缝、带或承托层，"
            "而不是终端对等阶段。"
        ),
        "avoid_on_this_page": (
            "等权编号阶段卡、一模块一图标、把每个上屏模块都画成相继对等节点，"
            "或判断加证据的卡片墙。"
        ),
    },
    "capability_relationship": {
        "visual_thesis": "忠实呈现合同声明的对象、能力及其对应或支撑关系。",
        "decision_relationship": (
            "只呈现来源合同声明的关系；除非内容明确给出，不得补画协同、因果或结果汇聚。"
        ),
        "recommended_composition": (
            "使用一个连续设计的关系场——如非对称缎带、分层地形、导流表面或汇聚网络——"
            "把能力以不等角色嵌在场中。方向、支撑、交换、汇合与反馈由场域本身承载，"
            "不要围绕中心徽章排布模块。共享治理能力表现为横断带、规则面或织入层，"
            "而不是门户、圆环、徽章或独立主物体。不要给每个能力单独配图、面板、象限、分层或编号视觉单元。"
        ),
        "avoid_on_this_page": (
            "泛化架构堆叠、中心辐射节点、等权能力卡、五宫格图墙、一能力一图，或软件模块图。"
        ),
    },
    "judgment_evidence": {
        "visual_thesis": "用主判断与支撑证据的直接关系完成证明。",
        "decision_relationship": "支撑模块共同解释或证明核心判断。",
        "recommended_composition": (
            "根据证据类型及其与判断的关系选择空间组织。"
            "形成一条主次分明的阅读路径；由内容决定位置、尺度、分组和视觉载体，不预设居中主物体。"
        ),
        "avoid_on_this_page": (
            "等权卡片墙、一条一图标、无关装饰场景，或脱离本页内容另选布局骨架。"
        ),
    },
}

VISUAL_PROOF_FALLBACKS: dict[str, str] = {
    "boundary_guardrail": "用主体能力与外围护栏的关系证明范围和职责清晰。",
    "crosscutting_chain": "用纵向转化主链与横向贯穿能力的共同作用证明体系完整。",
    "hierarchy_support": "用上层业务结果与下层支撑能力的依赖关系证明体系能够成立。",
    "decision_admission": "用选择依据与后续准入条件证明当前决策合理。",
    "comparison": "用共同维度下的差异和主次证明本页判断。",
    "scenario_application": "用真实业务场景、业务价值与进入条件证明应用方向。",
    "multi_semantic_foundation": "用多项现实基础共同支撑本页判断。",
    "causal": "用原因到业务后果的传导关系证明行动必要性。",
    "closed_loop": "用输入、结果、验证与反馈的闭环证明业务能够持续改进。",
    "phase": "用阶段目的与准入条件的递进证明实施节奏。",
    "path_chain": "用上游输入到下游能力或应用出口的转化路径证明底座如何成立。",
    "capability_relationship": "按来源合同呈现对象、能力及其对应或支撑关系，不增加协同或结果承诺。",
    "judgment_evidence": "用主判断与支撑证据的直接关系完成证明。",
}

NON_RENDERING_RELATION_LABELS = {
    "服务关系",
    "对象关系",
    "业务含义",
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
}

# These compact relationship statements are semantic input for ImageGen, not
# drawable copy.  They commonly live in the full prose / speaker notes after
# the visible module bullets have been finalized.
#
# Lead phrases always open a relation sentence and are safe trim anchors.
# Structure-label markers are lead only when written as「贯穿主链——…」; the same
# tokens may appear mid-sentence as verbs/objects (「质量与生命周期贯穿主链」)
# and must keep their subject.
PAGE_SEMANTIC_LEAD_PHRASE_MARKERS = (
    "从业务关系看",
    "统一知识对象连接",
)
PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS = (
    "贯穿主链",
    "四层主链",
)
PAGE_SEMANTIC_PHRASE_MARKERS = (
    *PAGE_SEMANTIC_LEAD_PHRASE_MARKERS,
    *PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS,
)
PAGE_SEMANTIC_LABEL_MARKERS = (
    "服务关系",
    "对象关系",
    "业务含义",
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
)
PAGE_SEMANTIC_MARKERS = PAGE_SEMANTIC_PHRASE_MARKERS + PAGE_SEMANTIC_LABEL_MARKERS

# Prefer these over module-enumeration chains when both are present.
BUSINESS_RELATION_MARKERS = (
    "从业务关系看",
    "服务关系",
    "对象关系",
    "业务含义",
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
)

_LABEL_SEMANTIC_RE = re.compile(
    r"(?:^|[\s\-•*])(?:"
    + "|".join(re.escape(label) for label in PAGE_SEMANTIC_LABEL_MARKERS)
    + r")\s*[：:]"
)
_STRUCTURE_LABEL_LEAD_RE = re.compile(
    r"(?P<label>"
    + "|".join(re.escape(marker) for marker in PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS)
    + r")\s*[——―–]"
)
# Authoring note often appended after a visual-structure clause; not semantic.
_AUTHORING_STRUCTURE_TAIL_RE = re.compile(
    r"[；;]\s*一级模块与上屏文字一致。?\s*$"
)


def _has_semantic_marker(text: str) -> bool:
    if any(marker in text for marker in PAGE_SEMANTIC_PHRASE_MARKERS):
        return True
    return bool(_LABEL_SEMANTIC_RE.search(text)) or any(
        text.startswith(f"{label}：") or text.startswith(f"{label}:")
        for label in PAGE_SEMANTIC_LABEL_MARKERS
    )


def _has_business_relation_marker(text: str) -> bool:
    if "从业务关系看" in text:
        return True
    return any(
        re.search(rf"(?:^|[\s\-•*]){re.escape(marker)}\s*[：:]", text)
        or text.startswith(f"{marker}：")
        or text.startswith(f"{marker}:")
        for marker in BUSINESS_RELATION_MARKERS
        if marker != "从业务关系看"
    )

MODULE_CHAIN_MARKERS = (
    "贯穿主链",
    "四层主链",
    "转化主链",
    "业务主链",
)


def _clean_onscreen_for_imagegen(text: str) -> str:
    """Keep theme bullets; strip boundary asides that dilute the page mission."""

    cleaned_lines: list[str] = []
    for raw in text.splitlines():
        # Row numbers/coordinates are authoring metadata, not audience copy.
        # Apply this before every compiler (including content-first) so stale
        # approved prompts cannot reintroduce markers such as ``第X行｜``.
        raw = strip_authoring_group_marker(raw)
        relation_match = re.match(
            r"^\s*[-*•]?\s*(?P<label>[^：:\n]{2,14})[：:]",
            raw,
        )
        if relation_match and relation_match.group("label").strip() in NON_RENDERING_RELATION_LABELS:
            continue
        line = ONSCREEN_ASIDE_RE.sub("", raw)
        line = re.sub(r"[；;]\s*$", "", line.rstrip())
        line = re.sub(r"\s{2,}", " ", line)
        # Drop emptied bullets that only carried an aside.
        if re.fullmatch(r"\s*[-*•]?\s*", line or ""):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def _module_label(title: str) -> str:
    return re.sub(r"^\s*\d+\s*｜\s*", "", title).strip()


def _is_module_enumeration_chain(sentence: str, module_titles: tuple[str, ...]) -> bool:
    """True when a chain sentence mostly restates on-screen module titles."""

    if "→" not in sentence:
        return False
    if not any(marker in sentence for marker in MODULE_CHAIN_MARKERS):
        return False
    labels = [_module_label(title) for title in module_titles if _module_label(title)]
    if len(labels) < 2:
        return False
    hits = sum(1 for label in labels if label in sentence)
    return hits >= max(2, (len(labels) + 1) // 2)


def _normalize_semantic_sentence(value: str) -> str:
    """Collapse whitespace and strip leftover bullets after sentence splits."""

    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"^[\s\-*•·]+", "", text)
    text = re.sub(r"[\s\-*•·]+$", "", text)
    text = text.strip()
    if not text:
        return ""
    text = _AUTHORING_STRUCTURE_TAIL_RE.sub("。", text)
    text = re.sub(r"[；;]。", "。", text)
    text = re.sub(r"。{2,}", "。", text)

    # Whole-source scans can leave module titles before the relation marker.
    # Trim only to true lead anchors — never to mid-sentence structure verbs.
    earliest: int | None = None
    for marker in PAGE_SEMANTIC_LEAD_PHRASE_MARKERS:
        idx = text.find(marker)
        if idx >= 0 and (earliest is None or idx < earliest):
            earliest = idx
    for match in _STRUCTURE_LABEL_LEAD_RE.finditer(text):
        idx = match.start("label")
        if earliest is None or idx < earliest:
            earliest = idx
    for match in re.finditer(
        r"(?:^|[\s\-•*])(?P<label>"
        + "|".join(re.escape(label) for label in PAGE_SEMANTIC_LABEL_MARKERS)
        + r")\s*[：:]",
        text,
    ):
        idx = match.start("label")
        if earliest is None or idx < earliest:
            earliest = idx
    if earliest is not None and earliest > 0:
        text = text[earliest:].strip()
        text = re.sub(r"^[\s\-*•·]+", "", text)
    # Prefer a terminal period over a dangling Chinese semicolon fragment.
    if text.endswith(("；", ";")):
        text = text[:-1].rstrip() + "。"
    return text.strip()


def _is_degenerate_semantic_sentence(sentence: str) -> bool:
    """True when a candidate is only a bare marker / empty after punctuation."""

    stripped = sentence.strip()
    core = re.sub(r"[\s。！？；;：:\-—―–•*·]+", "", stripped)
    if not core:
        return True
    if core in PAGE_SEMANTIC_PHRASE_MARKERS or core in MODULE_CHAIN_MARKERS:
        return True
    bare = re.sub(r"[。！？；;]+$", "", stripped)
    for marker in PAGE_SEMANTIC_STRUCTURE_LABEL_MARKERS:
        if re.fullmatch(re.escape(marker) + r"[——―–\-]*", bare):
            return True
    return False


def _page_semantic_relations(page: ScriptPage) -> str:
    """Extract compact business relations without forwarding source prose.

    The final script keeps the drawable bullets in ``上屏文字`` while the
    connective meaning may remain in ``视觉结构``, full prose, or speaker
    notes.  Preserve only marked relationship sentences so the handoff keeps
    the page's governing logic without leaking the source manuscript.
    Prefer explicit business-relation sentences over module-title chains that
    merely restate the on-screen module order.

    Chinese semicolons often separate clauses inside one labeled relation
    (``责任关系：A；B；C。``) and must not be treated as sentence boundaries;
    only ``。！？`` split candidates.
    """

    candidates: list[str] = []

    def add_sentence(value: str) -> None:
        text = _normalize_semantic_sentence(value)
        if not text or not _has_semantic_marker(text):
            return
        # Keep one compact sentence at a time; source paragraphs can contain
        # detailed evidence that is intentionally not part of the handoff.
        # Do not split on「；」— it is clause punctuation inside labeled relations.
        for sentence in re.split(r"(?<=[。！？])\s*", text):
            sentence = _normalize_semantic_sentence(sentence)
            if (
                sentence
                and _has_semantic_marker(sentence)
                and not _is_degenerate_semantic_sentence(sentence)
                and sentence not in candidates
            ):
                candidates.append(sentence)

    add_sentence(page.visual_structure)
    for source in (page.onscreen_text, page.full_prose, page.speaker_notes):
        for raw in source.splitlines():
            add_sentence(raw)
        # Also inspect prose that is not line-broken at sentence boundaries.
        add_sentence(source)

    if not candidates:
        return ""

    business = [
        sentence
        for sentence in candidates
        if _has_business_relation_marker(sentence)
    ]
    if business:
        structural = [
            sentence
            for sentence in candidates
            if sentence not in business
            and not _is_module_enumeration_chain(sentence, page.module_titles)
        ]
        ordered = business + structural
    else:
        ordered = candidates
    return "\n".join(f"- {sentence}" for sentence in ordered[:4])


def _explicit_visual_intent_type(
    page: ScriptPage,
    context: dict[str, str] | None,
    override: dict[str, str] | None,
) -> str:
    """Resolve an author-declared intent from override, outline, script, or contract."""

    for source in (
        (override or {}).get("visual_intent_type"),
        (context or {}).get("visual_intent_type"),
        page.visual_intent_type,
    ):
        value = str(source or "").strip()
        if value in VISUAL_INTENT_TEMPLATES:
            return value
    receipt = page.contract_receipt
    if isinstance(receipt, dict):
        value = str(receipt.get("visual_intent_type") or "").strip()
        if value in VISUAL_INTENT_TEMPLATES:
            return value
    return ""


def _visual_structure_hard_hint(page: ScriptPage) -> str:
    structure = page.visual_structure.strip()
    if not structure:
        return ""
    corpus = "\n".join(
        (
            structure,
            page.main_message,
            page.full_prose,
            page.speaker_notes,
        )
    )
    # Path/layer primitives with an explicit transverse force are cross-cutting,
    # not a pure path_chain / hierarchy_support stack.
    if structure.startswith(_CROSSCUT_HARD_HINT_PREFIXES) and (
        any(marker in corpus for marker in _CROSSCUT_HARD_HINT_MARKERS)
        or re.search(r"[；;][^；;\n]{0,40}贯穿主链", structure)
        or re.search(r"[；;][^；;\n]{0,20}横切", structure)
        or (
            "横向治理" in structure
            and any(token in corpus for token in ("贯穿", "横向"))
        )
    ):
        return "crosscutting_chain"
    for prefix, intent in VISUAL_STRUCTURE_HARD_HINTS:
        if structure.startswith(prefix):
            return intent
    return ""


def resolve_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Select a page relationship and report how confidently it was chosen.

    Returns ``(intent_type, source)`` where source is one of:
    ``explicit``, ``hint``, ``scored``, or ``fallback``.
    """

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no visual intent")
    context = context if isinstance(context, dict) else {}

    explicit = _explicit_visual_intent_type(page, context, override)
    if explicit:
        return explicit, "explicit"

    # V2 page contracts carry the authoritative source relation. Route from it
    # before consulting page-type or rhetoric heuristics.
    relation_names = {
        str(item.get("relation") or "") for item in page.content_relations
    }
    if relation_names & {"composed_of", "contains", "part_of", "classified_as", "layered_as"}:
        return "hierarchy_support", "contract_relation"
    if relation_names & {"sequence_before", "sequence_after"}:
        return "phase", "contract_relation"
    if relation_names & {"bounded_by"}:
        return "boundary_guardrail", "contract_relation"
    if relation_names & {"corresponds_to", "applies_to", "covers", "provides_to", "supports"}:
        return "capability_relationship", "contract_relation"
    if relation_names & {"causes"}:
        return "causal", "contract_relation"

    hinted = _visual_structure_hard_hint(page)
    if hinted:
        return hinted, "hint"

    relationship_corpus = "\n".join(
        (
            page.onscreen_text,
            page.full_prose,
            page.speaker_notes,
            page.visual_structure,
        )
    )
    relationship_lines = "\n".join(
        line.strip()
        for line in relationship_corpus.splitlines()
        if any(
            marker in line
            for marker in (
                "关系：",
                "工作流：",
                "贯通：",
                "闭环：",
                "回流",
                "反馈",
                "持续迭代",
            )
        )
    )
    signal_text = "\n".join(
        (
            page_mission,
            context.get("business_question", ""),
            context.get("page_job", ""),
            context.get("visual_center", ""),
            page.main_message,
            "\n".join(page.module_titles),
            page.visual_structure,
            relationship_lines,
        )
    )
    # These are field or object names, not page relationships.
    score_text = (
        signal_text.replace("业务应用层", "")
        .replace("平台应用层", "")
        .replace("需求预测", "")
        .replace("负荷需求", "")
    )
    scores = {
        intent_type: sum(
            weight for phrase, weight in signals if phrase in score_text
        )
        for intent_type, signals in VISUAL_INTENT_SIGNALS.items()
    }
    has_primary_chain = any(
        phrase in score_text for phrase in ("纵向关系", "纵向主链")
    )
    has_transverse_force = any(
        phrase in score_text
        for phrase in ("横向治理贯穿", "横向贯穿", "贯穿每层")
    )
    if not (has_primary_chain and has_transverse_force):
        scores["crosscutting_chain"] = 0
    role = context.get("argument_role", "").strip()
    if role == "foundation":
        scores["multi_semantic_foundation"] += 8
    elif role in {"change", "gap", "necessity"}:
        scores["causal"] += 3
    elif role == "implementation" and any(
        phrase in score_text for phrase in ("近期", "阶段", "节奏", "先开展", "再拓展")
    ):
        scores["phase"] += 4

    best_score = max(scores.values(), default=0)
    if best_score < 5:
        return "judgment_evidence", "fallback"
    for intent_type in VISUAL_INTENT_PRIORITY:
        if scores.get(intent_type) == best_score:
            return intent_type, "scored"
    return "judgment_evidence", "fallback"


def select_page_visual_intent_type(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> str:
    """Select a page relationship without allowing one generic noun to hijack it."""

    return resolve_page_visual_intent(
        page,
        page_mission,
        context=context,
        override=override,
    )[0]


def resolve_page_semantic_intent(
    page: ScriptPage,
    page_mission: str,
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
) -> SemanticIntentDecision:
    """Return the canonical semantic decision for shadow migration."""

    context = context if isinstance(context, dict) else {}
    override = override if isinstance(override, dict) else {}
    explicit = str(
        override.get("semantic_intent_type")
        or context.get("semantic_intent_type")
        or ""
    ).strip()
    legacy, _legacy_source = resolve_page_visual_intent(
        page, page_mission, context=context, override=override
    )
    corpus = "\n".join(
        part
        for part in (
            page_mission,
            context.get("business_question", ""),
            context.get("page_job", ""),
            page.core_message,
            page.onscreen_text,
            page.full_prose,
            page.visual_structure,
            page.speaker_notes,
            "\n".join(page.module_titles),
        )
        if part
    )
    return resolve_semantic_intent(
        explicit_intent=explicit,
        legacy_intent=legacy,
        content_relations=page.content_relations,
        corpus=corpus,
    )


def audit_page_semantic_intent(
    page: ScriptPage,
    page_mission: str = "",
    context: dict[str, str] | None = None,
    override: dict[str, str] | None = None,
    prior_carriers: tuple[str, ...] = (),
) -> dict[str, object]:
    """Build one serializable shadow-audit record for a content page."""

    legacy, legacy_source = resolve_page_visual_intent(
        page, page_mission, context=context, override=override
    )
    decision = resolve_page_semantic_intent(
        page, page_mission, context=context, override=override
    )
    composition = resolve_composition(decision)
    carrier = select_visual_carrier(decision, composition, prior_carriers)
    corpus = "\n".join(
        (page.core_message, page.onscreen_text, page.full_prose, page.visual_structure)
    )
    record = decision.to_dict()
    legacy_canonical_intent = canonicalize_intent(legacy)
    structure_issues = (
        *validate_composition(composition),
        *validate_visual_carrier(carrier),
    )
    record.update(
        {
            "page_id": page.page_id,
            "page_title": page.title,
            "legacy_intent": legacy,
            "legacy_source": legacy_source,
            "legacy_compatible_intent": decision.legacy_intent,
            "legacy_matches": legacy == decision.legacy_intent,
            "legacy_canonical_intent": legacy_canonical_intent,
            "semantic_refinement": (
                bool(legacy_canonical_intent)
                and legacy_canonical_intent != decision.primary_intent
            ),
            "composition": composition.to_dict(),
            "visual_carrier": carrier.to_dict(),
            "composition_guidance": (
                f"Use {carrier.selected} as the single dominant carrier occupying about "
                f"{round(composition.dominant_ratio * 100)}% of the body area. "
                f"Organize it as: {composition.spatial_organization}. "
                f"Reading path: {' -> '.join(composition.reading_path)}. "
                f"Encode relations with {', '.join(composition.relationship_encoding)}."
            ),
            "blocking_issues": list(
                (*structure_issues, *validate_semantic_structure(
                    decision,
                    corpus=corpus,
                    content_relations=page.content_relations,
                ))
                if decision.source not in {"fallback", "legacy_hint"}
                else structure_issues
            ),
        }
    )
    return record


def build_page_visual_intent(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
    context: dict[str, str] | None = None,
) -> str:
    """Compile deterministic, non-rendering page-specific composition guidance."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=context,
        override=override,
    )
    values = dict(VISUAL_INTENT_TEMPLATES[relation])
    if isinstance(override, dict):
        for key in values:
            value = override.get(key)
            if isinstance(value, str) and value.strip():
                values[key] = value.strip()
    values["recommended_composition"] = (
        f"{values['recommended_composition']} {TEXT_IN_COMPOSITION_RULE}"
    )
    values["avoid_on_this_page"] = (
        f"{values['avoid_on_this_page']} 避免{DETACHED_TEXT_RAIL_AVOID}。"
    )
    return "\n".join(
        (
            "[Prompt context] Page-specific visual intent "
            "(composition guidance only; do not render field names or instruction text)",
            f"- Selected visual intent type: {relation}",
            f"- Visual thesis: {values['visual_thesis']}",
            f"- Decision relationship: {values['decision_relationship']}",
            f"- Recommended composition: {values['recommended_composition']}",
            f"- Avoid on this page: {values['avoid_on_this_page']}",
        )
    )


def build_page_creative_brief(
    page: ScriptPage,
    page_mission: str,
    override: dict[str, str] | None = None,
    context: dict[str, str] | None = None,
) -> CreativeBrief:
    """Build semantic invariants and creative freedom using the existing router."""

    relation = select_page_visual_intent_type(
        page,
        page_mission,
        context=context,
        override=override,
    )
    return build_creative_brief(
        relation=relation,
        page_purpose=page_mission or page.core_message,
        core_meaning=page.core_message,
        required_meanings=page.module_titles,
        onscreen_text=_clean_onscreen_for_imagegen(page.onscreen_text),
        override=override,
    )


def content_lock_text(page: ScriptPage, page_mission: str = "") -> str:
    """Build prompt context followed by the drawable 上屏文字 layer."""

    if page.page_type != "content":
        raise ValueError(f"page {page.page_id} is {page.page_type}; no body ImageGen handoff")
    onscreen = _clean_onscreen_for_imagegen(page.onscreen_text)
    context: list[str] = [
        "[Prompt context] 页面使命 / Page mission（用于理解本页要回答的问题；不要把字段名或说明文字画出来）",
        page_mission.strip() or "未提供页面使命",
    ]
    context.extend(
        [
            "[Prompt context] 核心意思 / Core meaning（忠实表达；不要把字段名画出来）",
            page.core_message.strip(),
            "[Prompt context] 不得增加源合同未声明的因果、必要性、排他性、协同机制或结果承诺。",
        ]
    )
    context.extend(["上屏文字（需要准确表达的正文文字层）", onscreen])
    return "\n".join(context).strip() + "\n"


def _flatten_markdown_tables(text: str) -> str:
    """Preserve table cell meanings without prescribing a rendered table."""

    output: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if re.fullmatch(r"\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?", line):
            continue
        if line.startswith("|") and line.endswith("|"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            output.append(" · ".join(cell for cell in cells if cell))
        else:
            output.append(raw)
    return "\n".join(output).strip()


def diagnostic_onscreen_text(
    page: ScriptPage,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
) -> str:
    """Return the text layer the selected compiler is required to preserve."""

    if prompt_compiler == "content-first-v1":
        body = _flatten_markdown_tables(
            _clean_onscreen_for_imagegen(page.onscreen_text)
        )
        return "\n\n".join(
            part for part in (page.onscreen_judgment.strip(), body) if part
        )
    return page.onscreen_text


ONSCREEN_JUDGMENT_MODES = ("locked", "semantic_only")


def resolve_onscreen_judgment_mode(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    mode = str(
        (visual_context or {}).get("onscreen_judgment_mode")
        or page.onscreen_judgment_mode
    ).strip()
    role = str(
        (visual_context or {}).get("judgment_role")
        or page.judgment_role
    ).strip()
    try:
        return resolve_judgment_mode(mode, role)
    except ValueError as exc:
        raise ValueError(
            f"{page.page_id} has invalid judgment display policy: {exc}"
        ) from exc


def locked_onscreen_text(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    """Return only verbatim-critical visible copy; keep the rest semantically flexible."""

    locked: list[str] = []
    if (
        resolve_onscreen_judgment_mode(page, visual_context) == "locked"
        and page.onscreen_judgment.strip()
    ):
        locked.append(page.onscreen_judgment.strip())
    for title in page.module_titles:
        label = title.strip()
        if label and label not in locked:
            locked.append(label)
    for raw in _clean_onscreen_for_imagegen(page.onscreen_text).splitlines():
        line = raw.strip()
        if not line or line in locked:
            continue
        relation_label = re.match(
            r"^(?:[-*•]\s*)?([^：:\n]{2,14})[：:]",
            line,
        )
        if relation_label:
            label = relation_label.group(1).strip()
            if (
                label.endswith("关系")
                or label
                in {
                    "工作流",
                    "业务含义",
                    "四层贯通",
                    "页面主线",
                }
            ) and label not in locked:
                locked.append(label)
        if re.search(r"\d", line):
            locked.append(line)
    return "\n".join(locked).strip()


MAX_IMAGE_LOCKED_LINES = 7
MAX_IMAGE_LOCKED_LINE_CHARS = 14
MAX_IMAGE_LOCKED_CHARS = 84


def select_image_locked_text(
    page: ScriptPage,
    visual_context: dict[str, str] | None = None,
) -> str:
    """Return short, bitmap-safe text while leaving body copy editable."""

    raw = page.image_locked_text.strip() or locked_onscreen_text(page, visual_context)
    if not raw and not page.field_order and page.title.strip():
        # Older free-form final scripts do not expose structured fields.  Keep
        # their page heading as the minimal safe visible anchor.
        raw = page.title.strip()
    candidates = [line.strip(" -*") for line in raw.splitlines() if line.strip()]
    selected: list[str] = []
    total = 0
    for line in candidates:
        compact = re.sub(r"\s+", "", line)
        if not compact or line in selected:
            continue
        if len(compact) > MAX_IMAGE_LOCKED_LINE_CHARS:
            # Numeric fact lines often carry a long explanatory tail.  Preserve
            # the compact fact as bitmap copy and leave the tail editable.
            if re.search(r"\d", compact):
                shortened = re.split(r"[，,；;。]", line, maxsplit=1)[0].strip()
                if shortened and len(re.sub(r"\s+", "", shortened)) <= MAX_IMAGE_LOCKED_LINE_CHARS:
                    line = shortened
                    compact = re.sub(r"\s+", "", line)
                else:
                    continue
            else:
                continue
        if len(selected) >= MAX_IMAGE_LOCKED_LINES or total + len(compact) > MAX_IMAGE_LOCKED_CHARS:
            continue
        selected.append(line)
        total += len(compact)
    return "\n".join(selected).strip()


def _semantic_phrase_digest(text: str, *, limit: int = 8) -> list[str]:
    """Turn visible copy into short semantic anchors, never a copy block.

    The digest deliberately splits on Chinese list punctuation and joins the
    resulting terms with slashes. This gives ImageGen concrete business nouns
    and actions without presenting the approved sentence as a bitmap layout
    instruction.
    """

    cleaned = re.sub(r"\*+", "", text or "").strip(" -*")
    if not cleaned:
        return []
    parts = [
        part.strip()
        for part in re.split(r"[，,、；;。:：→—\-]+", cleaned)
        if part.strip()
    ]
    anchors: list[str] = []
    for part in parts:
        part = re.sub(r"\s+", " ", part).strip()
        if not part or part in anchors:
            continue
        # Remove editorial lead-ins while keeping the underlying business term.
        part = re.sub(r"^(?:主要需求是|围绕|包括|适合|采用|形成|客户可以|可以)", "", part).strip()
        if not part:
            continue
        if len(part) > 24:
            part = part[:24].rstrip("，,；;。")
        anchors.append(part)
        if len(anchors) >= limit:
            break
    return anchors


def render_semantic_visual_brief(page: ScriptPage) -> str:
    """Render a compact, non-rendering semantic brief for ImageGen."""

    groups: list[str] = []
    current = "未命名模块"
    title_set = {title.strip() for title in page.module_titles if title.strip()}
    for raw in page.onscreen_text.splitlines():
        line = re.sub(r"\*+", "", raw).strip()
        if not line:
            continue
        if line in title_set:
            current = line
            continue
        if line.startswith(("-", "*", "•")):
            anchors = _semantic_phrase_digest(line, limit=7)
            if anchors:
                groups.append(f"- {current}：" + " / ".join(anchors))
    if not groups:
        anchors = _semantic_phrase_digest(page.onscreen_text, limit=12)
        if anchors:
            groups.append("- 页面业务锚点：" + " / ".join(anchors))
    return "\n".join(groups)


def resolve_text_render_mode(
    style_lock: Path,
    *,
    explicit: str | None = None,
) -> str:
    """Resolve the text/image boundary without changing legacy styles."""

    if explicit:
        return validate_text_render_mode(explicit)
    style = _selected_content_first_style(style_lock)
    configured = str(style.get("default_text_render_mode") or "").strip()
    if configured:
        return validate_text_render_mode(configured)
    return DEFAULT_TEXT_RENDER_MODE


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

STYLE10_SEMANTIC_RULE_FIELDS: tuple[str, ...] = (
    "scope_rule",
    "semantic_structure_rule",
    "scene_layer_rule",
    "semantic_image_rule",
    "factuality_rule",
    "semantic_image_text_rule",
    "content_visual_rule",
    "carrier_router",
    "component_rule",
    "default_text_render_mode",
    "truth_lock",
    "visual_freedom",
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


def _selected_content_first_style(style_lock: Path) -> dict[str, Any]:
    """Load a selected style with a non-weakenable Style 09 baseline.

    Project locks are snapshots and older Style 09 locks may contain experimental
    scene-first wording.  Preserve their selected palette, but always compile
    Style 09 from the canonical library contract so a historical lock cannot
    silently weaken the text-led, single-medium presentation rules.
"""

    payload = load_style_lock(style_lock)
    style = payload.get("style")
    if not isinstance(style, dict):
        raise ValueError(f"visual style lock has no selected style: {style_lock}")
    name = str(style.get("name") or "").strip()
    colors = style.get("colors")
    if not name or not isinstance(colors, dict) or not colors:
        raise ValueError(
            f"visual style lock must provide style name and colors: {style_lock}"
        )
    if int(style.get("id") or 0) != 9:
        return style
    canonical = resolve_default_style(style_id=9)
    canonical["colors"] = dict(colors)
    # Keep the live STYLE09 reference contract refreshed by load_style_lock;
    # only fall back to the bundled JSON contract when the lock has none.
    lock_contract = str(style.get("prompt_contract") or "").strip()
    if lock_contract:
        canonical["prompt_contract"] = lock_contract
    return canonical


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
    rule_fields = (
        STYLE10_SEMANTIC_RULE_FIELDS
        if int(style.get("id") or 0) == 10
        else CONTENT_FIRST_STYLE_RULE_FIELDS
    )
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
    locked on-screen text.
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
    if include_structure:
        structure = compact_visual_structure_for_logic(page.visual_structure)
        if structure:
            lines.append(f"结构形态：{structure}")
    return relation, intent_source, "\n".join(lines)


def render_content_first_prompt(
    page: ScriptPage,
    *,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    presentation_decision: PresentationDecision | None = None,
    semantic_context: PageSemanticContext | None = None,
    semantic_composition_contract: str = "",
    text_render_mode: str = DEFAULT_TEXT_RENDER_MODE,
) -> tuple[str, str]:
    """Render a content-first prompt with an explicit text/image boundary."""

    text_render_mode = validate_text_render_mode(text_render_mode)

    # The core meaning is mandatory semantic context; a visible conclusion is optional.
    judgment_mode = resolve_onscreen_judgment_mode(page, visual_context)
    semantic_visual = text_render_mode in {"semantic_visual", "editable_overlay"}
    onscreen = diagnostic_onscreen_text(page, "content-first-v1")
    onscreen_body = _flatten_markdown_tables(
        _clean_onscreen_for_imagegen(page.onscreen_text)
    )
    locked = select_image_locked_text(page, visual_context)
    judgment_for_semantics = page.onscreen_conclusion.strip()
    core_meaning_for_semantics = page.core_message.strip() or page.title.strip()
    core_in_locked_copy = bool(
        judgment_for_semantics and judgment_for_semantics in locked
    )
    visible_judgment = (
        judgment_for_semantics
        if (
            judgment_mode == "locked"
            and not page.subtitle.strip()
        )
        else ""
    )
    # A subtitle migration is deliberately non-destructive: the approved body
    # copy remains the sole visible ImageGen payload.  The full judgment still
    # guides composition above, but must not be injected into or used to rewrite
    # 上屏文字.
    complete_semantics = (
        onscreen_body
        if page.subtitle.strip()
        else "\n\n".join(
            part
            for part in (
                visible_judgment,
                onscreen_body,
            )
            if part
        )
    )
    style09_semantic_tags = _style09_page_semantic_tags(
        PageBlock(page.sequence, page.title, complete_semantics),
        [line for line in complete_semantics.splitlines() if line.strip()],
    )
    # Style 09 is a shared visual surface, not a page-specific blueprint
    # language.  The final script's ``结构形态`` often contains literal
    # instructions such as "四行矩阵", "泳道" or "顶部五节点".  Passing that
    # authoring field to ImageGen makes those recipes dominate the generic
    # style contract and is the direct cause of the recent P19–P27 card-wall
    # output.  Keep the semantic intent resolver (which still reads the field)
    # but do not forward the layout recipe itself for Style 09.
    selected_style_for_logic = _selected_content_first_style(style_lock)
    style09_surface = int(selected_style_for_logic.get("id") or 0) == 9
    include_authoring_structure = not style09_surface
    if semantic_context is None:
        relation, intent_source, logic_contract = render_page_logic_contract(
            page,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=visual_intent_override,
            include_structure=include_authoring_structure,
        )
        semantic_relations = _page_semantic_relations(page)
    else:
        relation = semantic_context.relation
        intent_source = semantic_context.intent_source
        _, _, logic_contract = render_page_logic_contract(
            page,
            page_mission=page_mission,
            visual_context=semantic_context.visual_context,
            visual_intent_override=semantic_context.visual_intent_override,
            include_structure=include_authoring_structure,
        )
        semantic_relations = semantic_context.semantic_relations
    # Only the Stage 02 relationship-aware path has an audited page context to
    # accompany this compact label.  Keep ordinary direct callers and generic
    # pages free of a synthetic logic block, as they were before the Style 09
    # adapter was added.
    style09_relation_context = style09_surface and bool(
        visual_context
        or (
            semantic_context is not None
            and semantic_context.visual_context
        )
    )
    presentation = presentation_decision or resolve_presentation_decision(
        page,
        relation,
    )
    if semantic_composition_contract:
        # Review mode replaces legacy composition inference. Keeping both would
        # give ImageGen two conflicting structural instructions. The legacy
        # relation remains available in review metadata for human comparison.
        logic_contract = ""
    # Dense medium may still guide typography, but approved facts from full
    # prose must not be re-promoted into a must-onscreen contract. Gaps belong
    # in Stage 01 上屏文字, not in ImageGen recovery.
    # Core meaning is passed separately from optional visible conclusion.
    # Content-first keeps ordinary pages free of the long logic block. Inject
    # it only when the relation is confidently known and is not the low-score
    # judgment_evidence fallback — never force a wrong default into every
    # semantic_only page.
    include_logic_context = bool(
        # Style 09 receives the compact relation label even when the page's
        # authoring metadata does not provide a high-confidence legacy source.
        # The label is semantic context only; the layout recipe is suppressed
        # above, so this cannot recreate a matrix/swim-lane blueprint.
        style09_relation_context
        or (
            relation != "judgment_evidence"
            and (
                intent_source in {"explicit", "hint", "contract_relation"}
                or (
                    intent_source == "scored"
                    and (
                        bool(semantic_relations)
                        or judgment_mode == "semantic_only"
                    )
                )
            )
        )
    )
    presentation_contract = (
        render_presentation_contract(page, presentation)
        if presentation.source == "script"
        else ""
    )
    if semantic_visual:
        semantic_brief = render_semantic_visual_brief(page)
        page_specific_semantics = str(
            (visual_context or {}).get("visual_center") or ""
        ).strip()
        parts = [
            SEMANTIC_VISUAL_TEXT_CONTRACT,
            "",
            SEMANTIC_VISUAL_FACTS_HEADER,
            f"- 页面核心意思：{core_meaning_for_semantics}",
            (
                f"- 页面副标题语义：{page.subtitle.strip()}"
                if page.subtitle.strip()
                else ""
            ),
            (
                f"- 页面任务：{page_mission.strip()}"
                if page_mission.strip()
                else ""
            ),
            (
                f"- 关键事实锚点（仅供校验）：{locked}"
                if locked
                else ""
            ),
            "",
            SEMANTIC_VISUAL_BRIEF_HEADER,
            semantic_brief,
            (
                "【页面专属语义图谱｜仅供理解】\n" + page_specific_semantics
                if page_specific_semantics
                else ""
            ),
            "",
            (
                "【页面语义关系｜仅供理解，不上屏】\n" + semantic_relations
                if semantic_relations
                else ""
            ),
            "",
            logic_contract if include_logic_context else "",
            "",
            presentation_contract,
            "",
            IMAGEGEN_CANVAS_CONTRACT,
            "",
            SEMANTIC_VISUAL_CHROME_CONTRACT,
            "",
            render_content_first_style_contract(
                style_lock,
                semantic_tags=style09_semantic_tags,
            ),
        ]
    else:
        parts = [
            "【完整上屏内容】",
            complete_semantics,
            "",
            (
                CONTENT_FIRST_ONSCREEN_STORY_CONTRACT
                if judgment_mode == "locked"
                else (
                    CONTENT_FIRST_SEMANTIC_ONLY_WITH_LOCKED_STORY_CONTRACT
                    if locked
                    else CONTENT_FIRST_SEMANTIC_ONLY_STORY_CONTRACT
                )
            ),
            "",
            CONTENT_FIRST_PAGE_MISSION_LABEL,
            page_mission.strip() or page.core_message.strip(),
            "",
            CONTENT_FIRST_CORE_MEANING_LABEL,
            core_meaning_for_semantics,
            "",
            (
                "【页面语义关系｜仅供理解，不上屏】\n" + semantic_relations
                if semantic_relations
                else ""
            ),
            "",
            logic_contract if include_logic_context else "",
            "",
            presentation_contract,
            "",
            IMAGEGEN_CANVAS_CONTRACT,
            "",
            IMAGEGEN_CHROME_BAN_CONTRACT,
            "",
            render_content_first_style_contract(
                style_lock,
                semantic_tags=style09_semantic_tags,
            ),
        ]
        if locked:
            semantics_index = parts.index("【完整上屏内容】")
            parts[semantics_index:semantics_index] = [
                "【锁定关键文字】",
                locked,
                "",
            ]
    if semantic_composition_contract:
        # Composition guidance is semantic metadata, never visible copy.
        insert_at = 2 if semantic_visual else 3
        parts[insert_at:insert_at] = [semantic_composition_contract, ""]
    return relation, "\n".join(parts).strip() + "\n"


_page_missions = load_page_missions
_page_visual_contexts = load_page_visual_contexts


def _page_visual_intent_overrides(project: Path) -> dict[str, dict[str, str]]:
    """Compatibility wrapper backed by the shared Stage 01 parser."""

    allowed = {
        "visual_intent_type",
        "semantic_intent_type",
        "visual_proof",
        "visual_carrier",
        *VISUAL_INTENT_TEMPLATES["judgment_evidence"].keys(),
    }
    return load_page_visual_intent_overrides(project, allowed_fields=allowed)


def compile_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    prior_decisions: tuple[PresentationDecision, ...] = (),
    visual_structure_mode: str = "off",
    prior_semantic_carriers: tuple[str, ...] = (),
    text_render_mode: str | None = None,
) -> CompiledPagePrompt:
    prompt_compiler = validate_prompt_compiler(prompt_compiler)
    if visual_structure_mode not in {"off", "review"}:
        raise ValueError("visual_structure_mode must be 'off' or 'review'")
    if visual_structure_mode == "review" and prompt_compiler != "content-first-v1":
        raise ValueError("visual structure review mode requires content-first-v1")
    semantic_context = derive_page_semantics(
        page,
        page_mission=page_mission,
        visual_context=visual_context,
        visual_intent_override=visual_intent_override,
        resolve_intent=resolve_page_visual_intent,
        extract_relations=_page_semantic_relations,
    )
    if prompt_compiler == "content-first-v1":
        selected_style = _selected_content_first_style(style_lock)
        resolved_text_render_mode = resolve_text_render_mode(
            style_lock,
            explicit=text_render_mode,
        )
        relation = semantic_context.relation
        presentation = resolve_presentation_decision(
            page,
            relation,
            prior_decisions,
        )
        semantic_structure: dict[str, object] | None = None
        semantic_composition_contract = ""
        if visual_structure_mode == "review":
            semantic_decision = resolve_page_semantic_intent(
                page,
                page_mission,
                context=visual_context,
                override=visual_intent_override,
            )
            composition = resolve_composition(semantic_decision)
            carrier = select_visual_carrier(
                semantic_decision,
                composition,
                prior_semantic_carriers,
            )
            semantic_structure = {
                "mode": visual_structure_mode,
                "intent": semantic_decision.to_dict(),
                "composition": composition.to_dict(),
                "visual_carrier": carrier.to_dict(),
            }
            semantic_composition_contract = "\n".join(
                (
                    "[Mandatory composition guidance] Apply this layout guidance before placing any on-screen text. Do not render its field names or instruction text.",
                    "[Prompt context] Page-specific visual intent (composition guidance only; do not render field names or instruction text)",
                    f"- Selected visual intent type: {semantic_decision.primary_intent}",
                    f"- Decision relationship: {semantic_decision.primary_intent}",
                    f"- Dominant visual carrier: {carrier.selected}",
                    f"- Recommended composition: {composition.spatial_organization}",
                    f"- Reading path: {' -> '.join(composition.reading_path)}",
                    f"- Relationship encoding: {', '.join(composition.relationship_encoding)}",
                    f"- Required structural elements: {', '.join(composition.required_elements)}",
                    f"- Avoid on this page: {', '.join(composition.avoid)}",
                    "- Keep one visual center. Attach supporting text to its business objects and relation nodes; do not create an independent text wall.",
                )
            )
        relation, prompt = render_content_first_prompt(
            page,
            style_lock=style_lock,
            page_mission=page_mission,
            visual_context=visual_context,
            visual_intent_override=visual_intent_override,
            presentation_decision=presentation,
            semantic_context=semantic_context,
            semantic_composition_contract=semantic_composition_contract,
            text_render_mode=resolved_text_render_mode,
        )
        assert_deliverable_prompt(prompt)
        if EVIDENCE_ID_RE.search(prompt):
            raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
        return CompiledPagePrompt(
            prompt=prompt,
            compiler_version=prompt_compiler,
            relation=relation,
            injected_rule_ids=(
                "content.page_task",
                "content.core_meaning",
                "content.full_semantics",
                "content.page_logic_contract",
                "content.locked_key_copy",
                "content.complete_page_semantics",
                "content.independent_reading",
                "fact.source_boundary",
                "style.selected_lock",
                "style.tone_only",
                *(
                    (
                        "semantic_structure.intent",
                        "semantic_structure.composition",
                        "semantic_structure.carrier",
                    )
                    if visual_structure_mode == "review"
                    else ()
                ),
            ),
            style_selection={
                "id": selected_style.get("id"),
                "slug": selected_style.get("slug"),
                "name": selected_style.get("name"),
                "colors": dict(selected_style.get("colors") or {}),
                "style_lock": str(style_lock),
            },
            presentation=presentation,
            image_locked_text=select_image_locked_text(page, visual_context),
            editable_body_text=page.onscreen_text.strip(),
            semantic_structure=semantic_structure,
            text_render_mode=resolved_text_render_mode,
        )

    relation = semantic_context.relation
    creative_brief: CreativeBrief | None = None
    if prompt_compiler == "creative-brief-v1":
        creative_brief = build_page_creative_brief(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        visual_intent = render_creative_brief(creative_brief)
        injected_rule_ids = (
            "creative.context",
            "creative.freedom_envelope",
            "text.locked_key_copy_exact",
            "text.auxiliary_allowed",
            *(
                f"creative.page_avoid.{index}"
                for index, _ in enumerate(
                    creative_brief.page_specific_avoids,
                    start=1,
                )
            ),
        )
    else:
        visual_intent = build_page_visual_intent(
            page,
            page_mission,
            context=visual_context,
            override=visual_intent_override,
        )
        injected_rule_ids = ("legacy.visual_intent", "legacy.visual_grammar")
    prompt_text = content_lock_text(page, page_mission=page_mission).rstrip()
    block = PageBlock(
        page_number=int(page.page_id[1:]),
        title=page.title or page.page_id,
        text=prompt_text,
    )
    prompt = render_prompt(
        block,
        style_lock_path=style_lock,
        composition_guidance=visual_intent,
        compiler_version=prompt_compiler,
    )
    assert_deliverable_prompt(prompt)
    if EVIDENCE_ID_RE.search(prompt):
        raise ValueError(f"{page.page_id} ImageGen prompt still contains evidence IDs")
    for banned in ("完整文字稿", "文字稿取舍说明", "证据映射", "讲解提示", "禁止项"):
        if banned in prompt:
            raise ValueError(f"{page.page_id} ImageGen prompt still contains backend field: {banned}")
    if "Boundary (do not show on slide)" in prompt:
        raise ValueError(f"{page.page_id} ImageGen prompt still contains Boundary block")
    # Field injection form only — style presets may still mention the concept as guidance.
    if "视觉结构：" in prompt or re.search(r"(?m)^-?\s*视觉结构\b", prompt):
        raise ValueError(f"{page.page_id} ImageGen prompt still contains backend field: 视觉结构")
    return CompiledPagePrompt(
        prompt=prompt,
        compiler_version=prompt_compiler,
        relation=relation,
        creative_brief=creative_brief,
        injected_rule_ids=tuple(injected_rule_ids),
    )


def build_page_prompt(
    page: ScriptPage,
    style_lock: Path,
    page_mission: str = "",
    visual_context: dict[str, str] | None = None,
    visual_intent_override: dict[str, str] | None = None,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    visual_structure_mode: str = "off",
    text_render_mode: str | None = None,
) -> str:
    """Backward-compatible string API over the versioned prompt compiler."""

    return compile_page_prompt(
        page,
        style_lock,
        page_mission=page_mission,
        visual_context=visual_context,
        visual_intent_override=visual_intent_override,
        prompt_compiler=prompt_compiler,
        visual_structure_mode=visual_structure_mode,
        text_render_mode=text_render_mode,
    ).prompt


def write_chapter_handoff(
    *,
    project: Path,
    script: Path,
    style_lock: Path,
    pages: list[int],
    batch_name: str,
    prompt_compiler: str = DEFAULT_PROMPT_COMPILER,
    compare_with: str | None = None,
    visual_structure_mode: str = "off",
    text_render_mode: str | None = None,
) -> dict[str, Path]:
    if compare_with is not None and compare_with not in PROMPT_COMPILERS:
        raise ValueError(f"unsupported comparison compiler: {compare_with}")
    if visual_structure_mode not in {"off", "review"}:
        raise ValueError("visual_structure_mode must be 'off' or 'review'")
    document = parse_script_markdown(script.read_text(encoding="utf-8"))
    by_num = {int(page.page_id[1:]): page for page in document.pages}
    missions = _page_missions(project)
    visual_contexts = _page_visual_contexts(project)
    visual_intent_overrides = _page_visual_intent_overrides(project)
    out_dir = project / "workbench" / "prompts" / "imagegen"
    out_dir.mkdir(parents=True, exist_ok=True)

    if prompt_compiler == "content-first-v1":
        compilation_rules = [
            "- 每页独立完整，可直接送入 ImageGen，不依赖批次级公共提示。",
            "- 送入：页面任务、核心判断、主导关系标签、锁定关键文字、完整上屏与页面语义关系、画布尺寸，以及所选风格的气质与配色。",
            "- 不送入：源材料全文、完整事实边界或重复设计理论。",
            "- 不送入：证据编号、讲解提示、文字取舍、图片数量或后期制作规则。",
            (
                "- 默认不送入视觉载体、视觉中心、空间组织、本页避免、视觉证明等构图指导；本批次已显式开启审阅模式，以下页面仅注入通过结构合同生成的构图模块。"
                if visual_structure_mode == "review"
                else "- 不送入：视觉载体、视觉中心、空间组织、本页避免、视觉证明等任何构图/画法指导。"
            ),
            "- 页面任务、核心判断与主导关系只用于理解业务关系；锁定关键文字逐字准确，完整上屏内容均需进入 full 图。",
        ]
        if visual_structure_mode == "review":
            compilation_rules.extend(
                [
                    "- 已显式启用视觉结构审阅模式：在内容锁定之后加入主导关系、空间组织、阅读路径、载体和退化禁项。",
                    "- 该模式只生成待审阅提示词，不代表视觉结构已获人工批准，也不得自动进入 ImageGen。",
                ]
            )
    else:
        compilation_rules = [
            "- 送入：页面使命、核心判断、上屏文字，以及页面级视觉意图。",
            "- 不送入：边界/Boundary/禁止项、完整文字稿、取舍说明、证据映射、证据编号、视觉结构、讲解提示。",
            "- 页面使命、核心判断与页面级视觉意图只作为理解和构图上下文；不要把字段名或说明文字渲染到画面，正文文字以“上屏文字”为准。",
        ]

    review_parts: list[str] = [
        f"# ImageGen 送图脚本审阅稿 · {batch_name}",
        "",
        "> 状态：等待用户修改或批准。未经批准不得进入 ImageGen。",
        f"> 源脚本：`{script.as_posix()}`",
        f"> 风格锁定：`{style_lock.as_posix()}`",
        f"> Prompt compiler: `{prompt_compiler}`",
        f"> Visual structure mode: `{visual_structure_mode}`",
        f"> Text render mode: `{text_render_mode or 'style default'}`",
        "",
        "## 编入规则",
        "",
        *compilation_rules,
        "- 封面/目录/章节过渡/封底：不生成正文区 ImageGen，由模板层承载。",
        "",
    ]
    outputs: dict[str, Path] = {}
    content_prompts: list[str] = []
    diagnostics: list[PagePromptDiagnostics] = []
    prior_decisions: list[PresentationDecision] = []
    prior_semantic_carriers: list[str] = []
    comparison_diagnostics: list[
        tuple[PagePromptDiagnostics, PagePromptDiagnostics]
    ] = []

    for page_number in pages:
        page = by_num[page_number]
        if page.page_type != "content":
            review_parts.extend(
                [
                    f"## 第{page_number}页：{page.title or page.page_type}",
                    "",
                    f"- 页面类型：`{page.page_type}`",
                    "- 结论：本页不生成正文区 ImageGen；标题/章节字由模板文字层输出。",
                    "",
                ]
            )
            continue

        compiled = compile_page_prompt(
            page,
            style_lock,
            page_mission=missions.get(page.page_id, ""),
            visual_context=visual_contexts.get(page.page_id),
            visual_intent_override=visual_intent_overrides.get(page.page_id),
            prompt_compiler=prompt_compiler,
            prior_decisions=tuple(prior_decisions),
            visual_structure_mode=visual_structure_mode,
            prior_semantic_carriers=tuple(prior_semantic_carriers),
            text_render_mode=text_render_mode,
        )
        if compiled.presentation is not None:
            prior_decisions.append(compiled.presentation)
        if compiled.semantic_structure is not None:
            prior_semantic_carriers.append(
                str(compiled.semantic_structure["visual_carrier"]["selected"])
            )
        prompt = compiled.prompt
        content_prompts.append(prompt)
        selected_diagnostics = PagePromptDiagnostics(
            page_id=page.page_id,
            title=page.title or page.page_id,
            metrics=analyze_prompt(
                prompt,
                onscreen_text=diagnostic_onscreen_text(
                    page,
                    prompt_compiler,
                ),
            ),
            build_metadata=compiled.build_metadata(),
        )
        diagnostics.append(selected_diagnostics)
        if compare_with and compare_with != prompt_compiler:
            comparison = compile_page_prompt(
                page,
                style_lock,
                page_mission=missions.get(page.page_id, ""),
                visual_context=visual_contexts.get(page.page_id),
                visual_intent_override=visual_intent_overrides.get(page.page_id),
                prompt_compiler=compare_with,
                prior_decisions=tuple(prior_decisions[:-1]),
                visual_structure_mode="off",
                text_render_mode=text_render_mode,
            )
            comparison_page = PagePromptDiagnostics(
                page_id=page.page_id,
                title=page.title or page.page_id,
                metrics=analyze_prompt(
                    comparison.prompt,
                    onscreen_text=diagnostic_onscreen_text(
                        page,
                        compare_with,
                    ),
                ),
                build_metadata=comparison.build_metadata(),
            )
            if prompt_compiler == "legacy":
                comparison_diagnostics.append(
                    (selected_diagnostics, comparison_page)
                )
            else:
                comparison_diagnostics.append(
                    (comparison_page, selected_diagnostics)
                )
        draft_source = out_dir / f"_tmp_slide-{page_number:02d}-imagegen.md"
        with build_lock(out_dir, f"{batch_name}-p{page_number:02d}"):
            atomic_write_text(draft_source, prompt)
        staged = stage_script(
            project,
            slide=page_number,
            kind="imagegen",
            phase="draft",
            source=draft_source,
            note=f"{batch_name} imagegen handoff draft for review",
        )
        draft_source.unlink(missing_ok=True)
        outputs[page.page_id] = staged
        review_parts.extend(
            [
                f"## 第{page_number}页：{page.title or page.page_id}",
                "",
                *(
                    [
                        (
                            "- 结构分类对照：现行生产关系 "
                            f"`{compiled.relation}` → 新审阅关系 "
                            f"`{compiled.semantic_structure['intent']['primary_intent']}`；"
                            + (
                                "需人工确认后方可切换。"
                                if compiled.relation
                                != compiled.semantic_structure["intent"]["legacy_intent"]
                                else "兼容映射一致。"
                            )
                        ),
                        "",
                    ]
                    if compiled.semantic_structure is not None
                    else []
                ),
                prompt,
                "",
            ]
        )

    batch_path = out_dir / f"{batch_name}-imagegen-review.md"
    with build_lock(out_dir, f"{batch_name}-batch"):
        atomic_write_text(batch_path, "\n".join(review_parts).rstrip() + "\n")
    outputs["batch"] = batch_path
    diagnostics_path = out_dir / f"{batch_name}-imagegen-diagnostics.json"
    write_batch_diagnostics(
        diagnostics_path,
        diagnostics,
        batch_name=batch_name,
    )
    outputs["diagnostics"] = diagnostics_path
    if comparison_diagnostics:
        comparison_path = out_dir / f"{batch_name}-imagegen-compiler-comparison.json"
        write_compiler_comparison(
            comparison_path,
            comparison_diagnostics,
            batch_name=batch_name,
        )
        outputs["comparison"] = comparison_path

    gate = project / "workbench" / "stages" / "02-blueprint-dual-image" / f"{batch_name}-imagegen-script-gate.md"
    gate.parent.mkdir(parents=True, exist_ok=True)
    with build_lock(gate.parent, f"{batch_name}-gate"):
        atomic_write_text(
            gate,
            "\n".join(
                [
                    f"# ImageGen 送图脚本门禁 · {batch_name}",
                    "",
                    f"- batch_review: `{batch_path.as_posix()}`",
                    "- status: waiting_for_user_modify_or_approve",
                    "- rule: 用户批准前不得调用 ImageGen / final-script-pages --production-build",
                    "",
                    "## 请回复",
                    "",
                    "1. **批准送图脚本**（可指定页段）→ 将对应页 stage 为 final 并登记 approve-script 后再生图",
                    "2. **修改第N页** → 给出改法，返工该页 prompt 后再审",
                    "",
                ]
            ),
        )
    outputs["gate"] = gate
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--style-lock", type=Path, required=True)
    parser.add_argument("--pages", required=True, help="e.g. 1-7")
    parser.add_argument("--batch-name", default="chapter01")
    parser.add_argument(
        "--prompt-compiler",
        choices=PROMPT_COMPILERS,
        default=DEFAULT_PROMPT_COMPILER,
    )
    parser.add_argument(
        "--compare-with",
        choices=PROMPT_COMPILERS,
    )
    parser.add_argument(
        "--visual-structure-mode",
        choices=("off", "review"),
        default="off",
        help="Opt-in semantic composition guidance; review never bypasses approval.",
    )
    parser.add_argument(
        "--text-render-mode",
        choices=TEXT_RENDER_MODES,
        default=None,
        help="Override style default: full_image, semantic_visual, or editable_overlay.",
    )
    args = parser.parse_args(argv)

    raw = args.pages.strip()
    if "-" in raw and "," not in raw:
        start, end = raw.split("-", 1)
        pages = list(range(int(start), int(end) + 1))
    else:
        pages = [int(part) for part in raw.split(",") if part.strip()]

    outputs = write_chapter_handoff(
        project=args.project.resolve(),
        script=args.script.resolve(),
        style_lock=args.style_lock.resolve(),
        pages=pages,
        batch_name=args.batch_name,
        prompt_compiler=args.prompt_compiler,
        compare_with=args.compare_with,
        visual_structure_mode=args.visual_structure_mode,
        text_render_mode=args.text_render_mode,
    )
    print(f"batch_review={outputs['batch']}")
    print(f"diagnostics={outputs['diagnostics']}")
    if "comparison" in outputs:
        print(f"comparison={outputs['comparison']}")
    print(f"gate={outputs['gate']}")
    for key, path in sorted(outputs.items()):
        if key.startswith("p"):
            print(f"{key}={path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

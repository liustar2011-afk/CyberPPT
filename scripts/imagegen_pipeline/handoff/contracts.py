"""Shared ImageGen handoff prompt contracts and matching rules."""

from __future__ import annotations

import re


EVIDENCE_ID_RE = re.compile(r"S\d{3}")
IMAGEGEN_CANVAS_CONTRACT = """【输出尺寸｜不上屏】
最高优先级画布约束：输出必须严格为 2048×1024 像素（2:1）的正文内容区图片；不得输出16:9完整幻灯片。输入参考图只用于视觉风格与构图语言，不得继承参考图的画布比例。不得绘制页面标题、副标题、页码、页面序号、Logo 或页脚；标题/副标题由 PPT 模板文字层承载。"""
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
CONTENT_FIRST_SHARED_PREDICATE_CONTRACT = """【并列语义防发散｜不上屏】
共享谓词、共享限定语、父级说明只保留在原文所属层级，不得自动复制、分配或改写到每个并列子项。除非【完整上屏内容】逐项明确陈述，否则子项只呈现原文已有名称，不得生成“共享谓词 + 子项”的新判断、新标签或新事实。"""
CONTENT_FIRST_VISIBLE_TEXT_WHITELIST_CONTRACT = """【可读文字白名单｜硬约束】
图中所有可读文字只能来自【锁定关键文字】或【完整上屏内容】中的原文字符串。页面任务、核心意思、页面逻辑、视觉结构、语义关系、演讲备注及所有“不上屏”区块只决定构图和对象关系；其中任何词句只要未在上屏白名单中逐字出现，就不得渲染、摘录、改写、缩写或组合成标题、中心结论、标签、按钮、图例、流程节点或总结框。允许用场景、对象、位置、连线、色调和视觉焦点表达这些非上屏语义。"""
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

# 页面关系判断 Skill 与 Stage 02 接入验证

## 结果与职责

当前正式路线为：canonical 内容适配 → 当前主 Agent 关系判断 → content-first-v1 正式提示词 → 原有图片与组装环节。

Skill 只判断来源支持的业务关系及必要阅读约束。当前风格文件和 Image2 负责构图、媒介与视觉效果。实现没有参考项目名称、该页内容、八类资源答案或行业关系映射。测试数据使用独立的通用场景文件，生产代码不读取测试场景。

v4 合同移除强制核心结论、候选比较、机械评分、固定拓扑和宏观区域方案。正文与 fidelity_text 独立；普通正文允许改写。旧 v3 规格继续供历史显式消费路径读取，无法替代当前正式入口需要的 v4 判断。

缺失或陈旧判断时，正式入口通过现有 visual/skill-invocation.md 返回主 Agent 执行待办。主 Agent 读取完整语义、定位关系证据、写入现有 decisions 文件，随后重跑同一生产命令；无新增用户确认。执行者字段属于声明，程序无法鉴定智能体身份或推理真实性，不能把它单独当成执行质量证明。

## 通用场景与语义证据

15 个合成案例覆盖独立职责、分类与组织层级、条件流程、混合关系、机制歧义、来源冲突和无关系。按关系与判断难点组织：并列集合、同义改写、多层归属、跨主体职责、条件与分支、混合关系、时间与因果区分、来源冲突和无关系。包含保持相同主体和动词但改变关系前提的对照。以下记录主 Agent 对完整案例的实际语义判断与排除理由，没有使用自评分。

自动测试消费这些已审阅判断，检查正式提示词与来源绑定；它不独立评定判断正确性，也不代表未见材料的统计准确率。

### parallel

输入：甲组负责采集，乙组负责核验。两组独立开展工作。

判断状态：`supported`。

采用关系：甲组负责采集，乙组负责核验；两组独立开展工作。

依据与排除：两组独立已明示，采集与核验的动词无法单独证明交接。

必要边界：保留两组职责，不增加甲组向乙组交接的流程。

### hierarchy

输入：资源分为设备和人才。设备包括主设备和辅助设备；人才包括技术人员。

判断状态：`supported`。

采用关系：设备与人才是资源的并列分类；主设备和辅助设备归属设备，技术人员归属人才。

依据与排除：包括表达分类归属，同层类别没有上下级职责。

必要边界：保留分类归属与两层明细，不转为管理权限层级。

### flow

输入：申请人提交后，审核员核验；仅核验通过时由管理员发布，未通过退回申请人。

判断状态：`supported`。

采用关系：申请人提交后由审核员核验；通过后管理员发布，未通过退回申请人。

依据与排除：先后、分支条件及各节点主体均有明示依据。

必要边界：通过与未通过属于不同分支，保留三方责任；退回不等于自动重新提交。

### mixed

输入：甲类含A和B，乙类含C。两类并行采集，完成核验后才能共享。

判断状态：`supported`。

采用关系：甲类包含A、B，乙类包含C，两类并行采集。；完成核验是共享的前提。

依据与排除：分类、并行与有条件共享共同存在，不压成单一顺序。

必要边界：保留分类内归属及并行关系，共享条件适用于两类。

### ambiguous

输入：甲系统与乙系统协同，提升服务能力。

判断状态：`ambiguous`。

采用关系：甲系统与乙系统存在协同关系，来源未说明具体机制和方向。

依据与排除：协同词没有提供方向与机制，不能据此画双向数据流或管理层级。

必要边界：保持方向中性，不新增主从、数据交换方向或因果步骤。

未决内容：协同机制、数据方向与两系统职责未说明。

### none

输入：报告日期：2026年9月。

判断状态：`none`。

采用关系：不新增已确定关系。

依据与排除：仅有日期信息，无可表达的实体关系。

### parallel_set

输入：内容分为甲、乙、丙三类，三类分别维护，各自独立更新。

判断状态：`supported`。

采用关系：甲、乙、丙是并列分类，各自独立维护和更新。

依据与排除：来源明确分类及独立更新，没有类别之间的依赖。

必要边界：分类序号不表示先后、优先级或管理关系。

### parallel_paraphrase

输入：甲类的维护和更新独立进行；乙类、丙类亦如此，任一类更新均不以其他类更新完成为前提。

判断状态：`supported`。

采用关系：甲、乙、丙各自维护和更新，相互没有完成前提依赖。

依据与排除：改写后仍明确各类独立，句式改变不改变并列及无前提依赖的含义。

必要边界：保留三类的独立性，不根据叙述先后增加处理流程。

### flow_counterfactual

输入：甲组负责采集，乙组负责核验。甲组提交采集结果后，乙组才开始核验。

判断状态：`supported`。

采用关系：甲组先采集并提交结果，乙组随后开始核验。

依据与排除：与独立职责案例使用相同主体和动作，新增提交前提使顺序获得依据。

必要边界：保留结果提交这一触发条件，不补充退回或复核循环。

### hierarchy_with_shared_responsibility

输入：组织设甲组、乙组。甲组下设第一、第二小组，乙组下设第三小组。任务X由甲组和乙组共同承担。

判断状态：`supported`。

采用关系：甲组与乙组同属该组织；第一、第二小组归属甲组，第三小组归属乙组。；任务X由甲组和乙组共同承担。

依据与排除：组织归属与跨组责任同时存在；只保留树状归属会遗漏任务共担关系。

必要边界：保留归属层级及跨组共担责任，不把共担关系解释为甲组领导乙组。

### mixed_grouping_and_condition

输入：甲类与乙类分别处理。甲类按来源分组，乙类按状态分组；两类均须核验通过后发布。

判断状态：`supported`。

采用关系：甲类与乙类分别处理，分类维度分别为来源和状态。；两类内容发布均以核验通过为前提。

依据与排除：并列类别、各自分组与共同触发条件属于不同关系，不能压缩成单一流程。

必要边界：保留各类不同分组维度及共同发布条件，不把两类处理串联。

### time_without_cause

输入：工厂周一上线监测系统，周三设备停机。停机原因仍在调查。

判断状态：`ambiguous`。

采用关系：监测系统周一上线，设备周三停机。

依据与排除：同一来源明确时间先后且保留原因调查状态，时间关系不承担因果证明。

必要边界：时间先后可以呈现；不能断言系统上线导致停机。

未决内容：停机原因尚未确定。

### cause_explicit

输入：调查确认设备停机由冷却泵故障导致；监测系统周一上线与此次停机无关。

判断状态：`supported`。

采用关系：冷却泵故障导致设备停机。

依据与排除：同样出现系统与停机，调查结论明确支持泵故障因果并排除上线关联。

必要边界：保持调查确认的因果；监测系统上线不得接入停机因果链。

### conflicting_scope

输入：项目概览称所有站点均已接入；同日明细列出东站接入完成、西站尚未接入。两处口径差异未解释。

判断状态：`ambiguous`。

采用关系：不新增已确定关系。

依据与排除：同日同范围的两个状态不相容，不能挑选更便于构图的一条当作事实。

必要边界：保留总述与明细口径冲突，不能呈现全量接入完成或自行猜测范围解释。

未决内容：西站接入状态与全量完成声明冲突，来源未说明哪一处已更新。

### none_minimal

输入：欢迎参加年度交流会。

判断状态：`none`。

采用关系：不新增已确定关系。

依据与排除：只有欢迎语，无实体之间的业务关系；无需制造关系图或结论。

## 真实消费链路

- 15 个案例经真实 canonical intake、build_manifest 和正式编译器生成提示词。测试将旧 derive_page_semantics、resolve_presentation_decision、resolve_composition 替换为一经调用即失败的函数，确认新链路未运行它们。
- 对最终 prompt、落盘 compiled 文档及 manifest 检查采用关系、条件与未决边界确实存在；分析理由、证据定位摘要不进入提示词；不强制生成核心判断。
- 独立子进程调用真实 final-script-pages CLI，包含 production-build、generate-images、dry-run-images 和 image 分支。缺判断时没有发布 manifest；补齐后实际发布 prompt 与 manifest，随后按现有行为停在缺少已审计图片的门禁。
- 同一命令以显式 style lock 续跑，关系身份和输入身份保持一致。修改来源后判断失效，原 manifest 与 prompt 不被替换。
- 关系判断摘要进入现有 visual_spec_sha256 输入身份和逐页 relationship_judgment_sha256。变化时阻止同批次旧图层与页面复用，避免文字 QA 被当成新关系的视觉认可。
- Final Script 1.2 与外部稿继续使用 canonical content_text / full_prose 和独立 fidelity_text；required 与 if_rendered 保持不同含义。

实际输出见 [正式提示词消费样本](./visual-structure-prompt-verification-20260913.md)。该样本仅为验证产物，不作为后续项目的内容或风格权威。

## 参考项目回归

只读来源：[外部讲稿](../projects/中电联八类核心数据资源_20260912/source/external-script.md)。主 Agent 已读取完整讲稿并查看现有 full 图；原始 DOCX 未逐段核对，本次来源校核范围止于讲稿。

保留的读法与依据：

- 八类核心资源及各自明细为分类与归属关系。讲稿以第一类至第八类逐项陈述，编号不承担处理顺序。
- 依托基础设施进行汇聚整合、治理加工、安全可信管控和开放共享。讲稿没有定义这四个动作之间的严格先后或反馈闭环。
- 四类标准化服务输出并列，各有对应服务明细；不把某一服务提升为其他服务的结果。
- 整体资源沉淀—基础设施治理—服务输出链条有讲稿末段明确依据，保留“正在形成”状态；“已经形成八类资源”与“目前可形成服务输出”的力度保持区别。
- 电力业务环节与应用领域作为覆盖范围保留，不补造逐项配对或已实现成效。22年与数据沉淀绑定，1.1PB与当前资源规模绑定。

本次临时回归经正式 facade 编译并核对提示词实际消费上述判断，同时对参考项目所有文件进行前后逐文件摘要对比，通过一致性检查。没有在参考项目运行图片生成或组装，也没有写入或修改其产物。项目专属判断仅记录在本报告中，通用测试和生产实现均不包含该页的预设答案。

## 测试结果与限制

- 聚焦回归：92 passed，包含新关系判断测试、CLI、final-script-pages、模型参数、fidelity intake、输入身份、manifest 复用和生产边界。
- 新测试文件：19 passed；其中15项覆盖通用案例的真实消费，其余检查缺失/过期证据、fidelity、CLI断点及关系变化失效。
- 扩展旧编译器/manifest 回归：42 passed，2 failed。两项失败均依赖旧风格标题“GPT Image 2.5 Artifact Spec 执行版”，当前用户已修改的风格标题为“全页构图优先”。在内存载入 HEAD 版 prompt.py 与 page_manifest.py 再跑这两项，仍为2 failed。未覆盖或回退用户风格改动，未修改这两项断言来消除失败。
- 下游历史图片/组装单元测试对关系判断关卡做隔离桩，以维持各自测试范围；这些用例不计入智能体判断或真实关卡证据。新 CLI 测试没有替换正式关卡。
- Skill quick_validate 通过；git diff --check 通过。

未验证：没有调用 Image2，因此无法证明新的视觉美观度或生成图中的关系落实质量；没有继续 SVG、PPTX 组装或 OfficeCLI 最终渲染。未运行全仓全部测试，未开展独立模型盲测或大样本准确率评估。程序只校验绑定和证据位置，来源是否真正支持判断仍由主 Agent 负责。

观察到原有默认 style lock 每次重新生成会改变文件摘要；本次续跑身份测试使用显式固定 style lock，将风格生成时戳与关系判断身份分开验证。该既有行为本轮未修改。

## 送图脚本审阅停点

Stage 02 Skill 与主流程已加入用户要求的对话停点：生成送图脚本后展示实际全文和文件链接，等待明确确认，再继续生图。通过现有只编译模式实现审阅前停止，不新增程序审批开关或确认文件。

真实 CLI 测试补充验证只编译调用退出码为0、实际送图脚本存在、没有 PNG 或 PPTX 输出；确认后的生产调用仍使用同一批次、输出目录与正式入口。更新后的关系判断测试19项通过。停点由主 Agent 工作流执行，CLI 本身不鉴定对话中的确认。

## 修改文件

- [vendor/skills/ppt-visual-structure-designer/SKILL.md](/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/SKILL.md)
- [vendor/skills/ppt-visual-structure-designer/references/relationship-contract.md](/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/relationship-contract.md)
- [vendor/skills/ppt-visual-structure-designer/agents/openai.yaml](/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/agents/openai.yaml)
- [cyberppt/visual_stage/relationship_judgment.py](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/relationship_judgment.py)
- [cyberppt/stage02_production/preflight.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/preflight.py)
- [cyberppt/stage02_production/manifest_stage.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/manifest_stage.py)
- [cyberppt/stage02_production/page_reuse.py](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/page_reuse.py)
- [scripts/imagegen_pipeline/page_manifest.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/page_manifest.py)
- [scripts/imagegen_pipeline/handoff/prompt.py](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/handoff/prompt.py)
- [.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)
- [docs/CYBERPPT_WORKFLOW.md](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)
- [tests/test_relationship_judgment_v4.py](/Volumes/DOC/CyberPPT/tests/test_relationship_judgment_v4.py)
- [tests/fixtures/relationship_judgment_cases.json](/Volumes/DOC/CyberPPT/tests/fixtures/relationship_judgment_cases.json)
- [tests/test_cli.py](/Volumes/DOC/CyberPPT/tests/test_cli.py)
- [tests/test_final_script_pages.py](/Volumes/DOC/CyberPPT/tests/test_final_script_pages.py)
- [tests/test_stage02_image_model.py](/Volumes/DOC/CyberPPT/tests/test_stage02_image_model.py)

工作区原有的 references/visual-system.md、scripts/image_to_pptx_runtime/template_assembly.py 与 .tmp/ 未作本轮修改。

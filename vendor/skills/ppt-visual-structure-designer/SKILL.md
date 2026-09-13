---
name: ppt-visual-structure-designer
description: Judge source-supported page relationships and necessary visual reading boundaries after Stage 02 content adaptation and before prompt compilation. The main agent preserves full semantics; the current style and Image2 own composition and visual execution.
---

# 页面关系判断

当前主 Agent 执行本 Skill：完整理解页面内容，校核关系依据，提出防止误读所必需的视觉表达约束。普通内容可以改写；具体构图、媒介、空间布局、色彩、字体和视觉效果交给当前风格文件与 Image2。

## 正式入口与执行

CyberPPT 使用 `.venv/bin/python3 -m cyberppt final-script-pages ... --production-build`。
内容适配完成后，入口检查 `visual/visual-design-decisions.json` 的 v4 判断。
缺失或过期时读取入口返回的 `visual/skill-invocation.md`，由主 Agent 完成判断并重跑同一命令，保留页面范围、build_id、输出目录、生图和组装参数。此处属于内部智能体执行待办，无需用户确认。

读取 canonical intake `workbench/stages/02-input/script-intake.json` 中目标页的完整语义、来源信息及必要的相邻页。`content_contract_version: 2` 以顶层 `content_text` 为普通内容入口；Final Script 1.2 的值来自完整 full_copy，外部稿来自适配后的结构化内容或自由正文，1.0/1.1 来自已编写的上屏稿。`full_prose` 在与内容不同的时候提供额外完整背景，必须回读其中的条件与边界。`onscreen_text`、`editable_body_text` 和嵌套正文是兼容别名，不另立内容权威。`delivery_mode` 区分自读与演讲辅助，但两者均须保留关键语义。来源引用可用于回读精确原文；无法获得原文时在 `source_check` 明确本次仅核对讲稿，不能声称已核验原始资料。

`stage02_visual_input` 中旧关键词匹配、评分、fallback topology、expression_constraints 和作者版式提示均不承担关系权威。来源明示的关系及层级注解应结合正文校核；发现冲突时保留不确定性。不得复用旧图、旧提示词或旧 v3 评分作为新关系依据。

## 判断方法

先理解谁在做什么、对象归属、状态、条件和适用范围，再判断哪些关系可由来源支持。为每条采用的关系定位原文证据，并说明证据如何支持该读法。比较可能造成误读的替代解释，仅在确有歧义时记录未决内容。

- 并列类别可以保留共同分类维度和各自下属内容；编号不自动代表顺序、优先级或因果。
- 多层级内容保留实际归属和层级；多主体保留各自职责、行为和边界，不把分类层级转换为管理上下级。
- 流程须有来源支持的先后或触发条件；时间顺序不自动构成因果。来源仅列治理动作时，不补造逐步流水线或反馈闭环。
- 混合关系可同时包含并列、归属和局部流程；不强制整页唯一拓扑、唯一视觉中心或核心结论。
- 歧义可保留明确部分，并限制未证实的连线、方向或层级。无关系输入可采用空关系列表，保留内容本身。

约束只说明必须保留的阅读含义与应避免的错误推断。不得预选卡片、矩阵、金字塔、区域数量、坐标、载体或媒介；不为填字段生成结论、候选或分数。无需为了视觉简洁删除主体、状态、条件和限定。

复用 `constraints` 记录必要的对象归属、数字所指、条件附着、来源主次或等权性，以及容易因精简丢失的责任与状态；在 `analysis` 或 `source_check` 中说明这些约束的正文依据。只保留实际存在的误读风险，无需复制完整稿。`uncertainties` 说明哪些关系仍无法确定，不能把未证实关系画成事实。来源等权时不指定业务优先级；没有单一核心判断时不强行生成结论。平台、机制、架构的表现方式由风格与 Image2 根据这些业务语义选择，不增加强制页面类型、视觉焦点或版式字段。

## 输出与消费

读取 [v4 输出合同](references/relationship-contract.md)，直接写入现有 `visual/visual-design-decisions.json`。程序只验证输入绑定、字段和证据定位，无法证明关系判断正确。主 Agent 必须逐页完成语义复核，并在交付说明中呈现依据、歧义和边界；不得以字段通过或自评分替代。

正式 `content-first-v1` 编译器消费关系陈述、必要约束与未决边界，跳过旧关系猜测和固定构图路由。分析过程、证据引文、来源 ID 与输入哈希仅用于审计，不进入生图文字。独立 `fidelity_text` 决定 `required` 和 `if_rendered` 精确字符串规则，普通内容及证据引用均不升级为逐字锁。

历史 v3 项目仅通过原有显式 legacy 命令原位读取。目录内旧 schema、脚本与其他 references 保留兼容用途；当前正式路线仅使用本 Skill 与 v4 输出合同，禁止把旧合同拼接进 v4。

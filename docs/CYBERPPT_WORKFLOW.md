# CyberPPT 主流程总览

本文件是 CyberPPT 的流程总入口，供 Claude、Codex 及其他协作 Agent 首先阅读。

各阶段 Skill 只负责本阶段的操作细则；`AGENTS.md` 负责仓库级约束。三者发生表述差异时，先以 `AGENTS.md` 的硬性约束为准，再以本文件确定阶段顺序，最后阅读对应 Skill 的详细规则。

## 一、任务入口判断

收到任务后，先按任务类型选择入口：

1. 涉及源材料、Source Truth、语义模型、Outline、page plan、源材料重跑或 Outline 审计：先阅读并调用 `cyberppt-source-foundation`。
2. 只涉及已锁定最终脚本的单页写作：进入 `cyberppt-write-single-page`。
3. 只涉及视觉结构、图片、SVG、ImageGen 或 PPTX QA：可以从对应 Stage 02 Skill 开始，不重复建立 Source Foundation。
4. 涉及旧项目但已有已验证 Foundation 产物：先核对产物状态，再复用；不得因为项目已存在而跳过 `cyberppt-source-foundation`。

正式项目默认使用单人轻量流程。除非用户明确提供 `autonomous_lightweight` 任务合同，不使用自主运行例外。

## 二、唯一正式路线

### Stage 01

`cyberppt-source-foundation` → `business-semantic-understanding` → `ppt-outline-planning` → `cyberppt-handoff` → `cyberppt-write-single-page`

### 全流程

源材料 → Source Foundation → 业务语义理解 → 交流目标 → Outline 与页面计划 → Handoff → 逐页脚本 → 最终全稿 → Stage 02 视觉生产 → PPTX QA 与交付

`compile-outline-draft` 与 `cyberppt-author-stage01-outline` 仅用于旧项目迁移的内部兼容，不是新项目或已验证 Foundation 项目的第二条路线。

## 三、Stage 01 详细步骤

### 1. 建立 Source Foundation

输入源材料，运行源材料解析和语义准备，建立：

- `source.md`
- 结构和事实基础
- `normalized-facts.json`
- `concept-base.json`
- `relation-graph.json`
- `argument-chain.json`
- `semantic-report.json`

主责 Skill：`cyberppt-source-foundation`、`business-semantic-understanding`。

### 2. 形成业务语义理解

围绕业务对象、主体、动作、关系、条件、状态、数字、问题和判断，完成语义归并和论证链整理。事实强度、责任边界和来源归属必须保留。

语义理解完成后运行验证；`semantic-report.json` 必须达到 `status: ok`，才能进入页面规划。

### 3. 提出交流目标

先基于语义结果提出一个忠于源材料的交流目标方向，再交给用户修改或确认。

交流目标中的受众、场景和行动要求，只有得到源材料直接支持时，才可以升级为源事实、源判断或页面结论。

### 4. 规划 Outline 和页面计划

根据已确认的交流目标，形成：

- `deck-brief.json`
- `page-plan.json`
- `ppt-outline.md`
- `outline-report.json`

每个内容页至少明确：

- 一个受众问题
- 一个页面使命
- 一个核心判断
- 一个不可替代价值
- 一条主论证链
- 证据职责
- 不上屏内容
- 后续保留内容
- 拆页风险
- 前后页衔接

主责 Skill：`ppt-outline-planning`。

### 5. 完成 Outline 作者化和审计

机器生成的 Outline 只是候选证据清单。作者必须补充页面使命、判断、论证链、证据取舍和不上屏边界，完成 `author_edited` 状态后，才进入正式 Outline 审计。

审计检查来源、关系、层级和契约底线，不替代作者的页面取舍。

### 6. 执行 Handoff

Outline 审阅通过后，执行 Source Foundation 到 CyberPPT 的兼容投影，生成：

- 投影后的 source units
- `semantic-argument-model.json`
- `source-truth.json`
- CyberPPT Outline
- 人工审阅 Markdown
- `authority-map.json`
- `integration/cyberppt-handoff-report.json`

只有 `projection_validation.status=ok` 时，才可进入页面脚本编写。

主责 Skill：`cyberppt-handoff`。

### 7. 逐页编写内容脚本

以当前项目的 Outline、Source Truth、source units、目标页和相邻页契约为依据，一次处理一张内容页。

页面脚本依次完成：

1. 页面设计简报
2. 主论证链
3. 证据架构
4. 完整文字稿
5. 上屏文字
6. 视觉语法
7. 演讲者备注

主责 Skill：`cyberppt-write-single-page`。

单页 Skill 不负责整套 Outline、不合并最终全稿、不进入 Stage 02、不生成图片或 PPTX。

### 8. 汇总最终全稿

将已完成页面汇总为最终脚本，执行全稿审计，检查来源覆盖、事实强度、页面关系、标题层级、上屏文字、重复表达和脚本契约。

最终脚本通过当前 `script-audit` 后，才可进入 Stage 02。

## 四、Stage 01 的四个人工停点

| 停点 | 必须展示 | 用户反馈后的动作 |
|---|---|---|
| 交流目标 | 基于源材料提出的一个方向 | 修改现有权威方向后继续 |
| 章节和页面提纲 | 章节结构、页面顺序、页面使命和核心判断 | 修改现有权威 Outline 后继续 |
| 页面详细内容 | 目标页完整稿、上屏文字和视觉结构 | 只修改目标页及必要上游契约 |
| 最终全稿 | 全套页面脚本和全稿审计结果 | 等待最终确认，不自行跳过 |

这四个停点发生在对话中，不新增 approval、receipt、attempt、manifest、哈希绑定或平行审阅目录。

## 五、Stage 02 视觉生产步骤

### 1. 最终脚本和页面生产入口

使用已通过 `script-audit` 的最终脚本，进入 `final-script-pages`。页面生产前必须具备通过的 Stage 02 handoff 和视觉结构审计。

### 2. Stage 02 handoff

运行 `prepare-stage02-handoff`，核对当前最终脚本、项目绑定、脚本版本和页面范围。脚本发生变化后，必须重新生成 handoff，不得沿用旧绑定。

### 3. 视觉结构

运行 `prepare-visual-structure`，按视觉结构 Skill 生成视觉决策及其编译产物，再运行视觉结构审计。

视觉结构 Skill 只决定视觉承载、关系表达、空间语法和视觉层级，不重新解释源材料事实，不新增页面结论。

### 4. 选择并锁定视觉风格

风格选择仍然存在，是 Stage 02 的正式前置步骤，发生在最终脚本审计通过后、`final-script-pages` 和 Prompt/Manifest 编译前。

执行要求：

1. 向用户展示可选风格样张并完成确认。
2. 从默认风格 1-8 中选择，或在明确使用扩展风格时选择 9-10。
3. 使用 `--style-id`、`--style-name` 或已有的 JSON `--style-lock` 固化选择。
4. 风格锁必须是 `cyberppt.visual_style_lock.v1` JSON；Markdown 确认文件不能替代风格锁。
5. 后续页面生产、Prompt 编译和图片生成必须消费同一份风格锁，不得临时替换外部预设。

`prepare-visual-structure` 只负责视觉关系、承载方式、空间语法和视觉决策，明确不选择视觉风格。风格选择完成后，才能进入最终页面生产和 Prompt 编译。

### 5. Prompt 和 Manifest

编译每页实际送图提示词和 manifest，并检查以下内容彼此分离：

- 页面完整文字稿
- 可编辑正文
- 图片中的严格上屏文字
- 视觉设计上下文

PNG 文件存在不等于提示词、批次或 QA 成功。必须检查实际落盘的 `prompts/pXX.txt`、manifest 和运行记录。

### 6. 图片生成和 QA

执行图片生成、图片文字检查、尺寸检查、视觉 QA 和批次结果核对。请求尺寸、模型返回尺寸、标准化尺寸和幻灯片画布尺寸必须分别记录。

进入图片转可编辑 PPTX 前，对配图内部的可读文字逐项分类：

- 需要编辑或属于信息表达的文字，清底后必须回写为原生 SVG 文字；
- 作为图形本体一部分且应保持原样的字样，可以随经过核验的局部图片层保留；
- 未分类、清底后未回写或形成空白容器的文字区域，阻断导出。

每页必须在 pairs[*].graphic_text_policy 中声明分类完成状态、文字处理方式和空白容器检查结果。该策略由 Stage 02 Quick 适配器在 PPTX 导出前执行机器门禁。

### 7. PPTX 组装和交付 QA

完成 PPTX 组装后，检查文字可读性、图片质量、版式、溢出、可编辑性、渲染结果和交付状态，并确认配图文字策略 QA 与空白容器门禁通过。所有关键门禁通过后，才能称为完成。

## 六、权威产物与边界

### Source Foundation 权威产物

`normalized-facts.json`、`concept-base.json`、`relation-graph.json`、`argument-chain.json`、`deck-brief.json` 和 `page-plan.json` 是上游权威输入。

### CyberPPT 投影产物

`semantic-argument-model.json`、`source-truth.json` 和 `outline.json` 是下游兼容投影，不得反向成为第二套语义权威。

### 页面脚本权威

最终脚本及其审计结果是 Stage 02 的内容输入。修改脚本后必须重新执行受影响的 handoff、manifest、提示词和 QA 环节。

## 七、禁止事项

- 不从旧项目、旧脚本或隐藏目录复制事实源。
- 不在已验证 Foundation 产物上重新运行旧版语义理解、Source Truth 编译或机械 Outline 编译。
- 不因审计覆盖不足机械增加页面、模块、锚点句或附件字段。
- 不把附件登记、清单、表单和实施明细默认提升为主文页面结论。
- 不把视觉提示词中的设计上下文写成新的业务判断。
- 不以 PNG 存在、命令退出码为零或局部测试通过，替代端到端产物验证。

## 八、完成判定

只有同时满足以下条件，才能对外称为完成：

1. Source Foundation 和语义验证通过。
2. Outline 已完成作者化、审计和人工提纲停点。
3. Handoff 投影验证通过。
4. 页面脚本、最终全稿和 `script-audit` 通过。
5. 风格已由用户确认，并生成有效的 JSON 风格锁。
6. Stage 02 handoff、视觉结构审计和实际提示词检查通过。
7. 图片、PPTX、渲染和交付 QA 通过。
8. 最终回复提交实际产物的绝对路径链接，并明确未验证事项。

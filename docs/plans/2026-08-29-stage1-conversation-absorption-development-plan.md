# Stage 1 构建建议吸收分析与开发方案

> 日期：2026-08-29
> 输入：ChatGPT 对话《Stage1构建建议》及其引用脚本
> 技术判断：`SUPPORT WITH CONDITIONS`
> 适用范围：默认 `script` profile、v2 lean Deck Plan、Final Script、Stage 01 → Stage 02 正式交接

## 1. 结论

对话提出的核心目标值得吸收：Stage 1 应稳定表达页面使命、核心判断、信息关系、严格上屏文字和不可丢失内容；阅读型 PPT 应在脱离讲解时仍可理解；Stage 2 应获得清晰的语义边界和精确文字锁。

落地方式需要服从现行架构：

1. 继续保留三个 Stage 01 权威内容产物：`foundation.json`、`deck-plan.json`、`dist/final-script.md`。
2. v2 lean Deck Plan 只负责章节、页面使命和来源边界，不接收 `Semantic Units`、上屏合同、视觉关系或 Integrity 字段。
3. 页面语义、论证、上屏结构和关系由 AUTHOR 写入 Final Script。
4. 逐行文字 ID、层级、顺序、哈希和关系验证继续由 Stage 02 handoff 派生。
5. 优先补强 AUTHOR 的阅读型写作规则、Critic 离线阅读检查和 Final Script 审计。

本方案不新增 Deck Manifest、页面 AST、确认文件或第四个语义权威。

## 2. 目标、提案与判断

### 2.1 用户目标

- 降低 Stage 2 对长篇自然语言的猜测空间。
- 防止关键上屏文字、数字、关系和条件在视觉生产中丢失。
- 让上屏文字兼顾完整语义、结构化、层级化和短句化。
- 支持可独立阅读的 PPT/PDF。
- 保留 Stage 2 的视觉设计自由度。

### 2.2 对话中的主要实现提案

- 将 Stage 1 成品定义为“页面语义契约”。
- 增加手工 `Semantic Units + Relations + Integrity Contract`。
- 使用 `U1/U2/...` 标识页面对象。
- 将“视觉结构”改为纯语义结构，并限制具体载体与空间词。
- 建立 `Display Copy Contract` 和 `Reading PPT Contract`。
- 采用“语义锚点 → 核心语义 → 必要细项”的三层上屏结构。
- 将完整文字稿和演讲者备注移出 Stage 2 主输入。
- 增加 Deck Manifest。

### 2.3 技术判断

`SUPPORT WITH CONDITIONS`

支持目标和多数写作原则。实现机制应复用 Final Script 与派生 handoff，避免手工 ID、平行合同和新增权威文件。完整文字稿继续作为 Stage 2 的语义上下文；演讲者备注继续保留在交付数据中，同时不进入视觉设计输入。

## 3. 已验证的仓库事实

| 事实 | 证据位置 | 对方案的影响 |
|---|---|---|
| Stage 01 只有三个权威内容产物 | `AGENTS.md`、`docs/CYBERPPT_WORKFLOW.md`、`.agents/skills/cyberppt-script-workflow/SKILL.md` | 禁止增加 Deck Manifest、页面 AST 或平行 Integrity 文件 |
| v2 lean Deck Plan 明确排除 AUTHOR 字段 | `script_engine/analysis_audits/deck_plan.py` 的 `_LEAN_PAGE_AUTHOR_FIELDS` | `content_relations`、`onscreen_contract`、`content_load` 等不得进入 lean Plan |
| Final Script 已具备页面语义合同骨架 | `contracts/final-script.schema.json` | 已有 `mission`、`core_message`、`argument`、`full_copy`、`onscreen`、`visual_thesis`、`relationships`、`speaker_notes`、`source_refs` |
| 阅读模式已进入 Final Script 合同 | `contracts/final-script.schema.json` | `deck.delivery_mode` 已支持 `presented` 与 `self_read` |
| 当前阅读型审计已检查空模块和语义负载 | `script_engine/analysis_audits/final_script.py` 的 `_audit_self_reading_density` | 已有基础，语义完整性检查仍需补强 |
| 上屏文字会派生逐行 ID 和完整性合同 | `cyberppt/content_integrity_contract.py` 的 `build_content_integrity_contract` | 手工 `U1/U2` 会与 `Pxx-Txx` 重复 |
| handoff 已锁定文字、层级、顺序和结构哈希 | `cyberppt/stage02_handoff.py` 的 `_page_record` 与 `_audit_content_integrity` | Integrity 应保持派生合同，不交给 AUTHOR 手工维护 |
| Final Script 的语义关系会进入 Stage 2 | `cyberppt/script_quality/models.py` 的 `content_relations`、`cyberppt/stage02_relationship_adapter.py` | 显式箭头关系已经可被转换为业务关系 |
| Stage 2 会验证关系并解析拓扑 | `cyberppt/stage02_handoff.py` 的 `_page_record` | 关系词表宜保持开放，Stage 2 负责归一化和验证 |
| 完整文字稿被用作视觉语义上下文 | `cyberppt/visual_stage/execution.py` 的 `_write_visual_design_input` | 删除完整文字稿会削弱紧凑上屏文字的语义解释能力 |
| AUTHOR 的视觉说明在 Stage 2 仅具建议权 | `author_visual_notes_authority: advisory_only` | 可收紧 AUTHOR 写法，无需破坏字段兼容性 |

## 4. 反例验证

### 4.1 删除完整文字稿会降低关系验证可靠性

`_page_record` 使用页面使命、核心判断、完整文字稿和上屏文字共同验证语义关系。阅读型上屏文字经过压缩后，条件、主语或背景可能只在完整文字稿中保留。若 Stage 2 只接收上屏短句，关系验证会失去必要上下文，紧凑表达更容易被误判。

结论：完整文字稿继续进入 `semantic_context`，同时严格禁止其进入锁定上屏文字。

### 4.2 手工 `U1/U2` 会产生双重身份体系

当前 handoff 已按上屏顺序生成 `Pxx-Txx`，并绑定父子关系、根节点、顺序和结构哈希。再由 AUTHOR 维护 `U1/U2` 会带来编号漂移、改稿同步和双向映射成本。

结论：AUTHOR 只维护可读的模块层级；机器 ID 继续派生。

### 4.3 将所有关系限制为固定枚举会损失业务语义

不同材料会出现支撑、约束、映射、转化、汇聚、反馈、条件、责任和范围等关系。固定枚举适合拓扑归一化，直接限制 AUTHOR 容易压平业务含义。

结论：AUTHOR 使用清晰的“主体—动作—对象—条件”表达；Stage 2 将其归一为拓扑和视觉约束。

## 5. 建议吸收矩阵

| 对话建议 | 判断 | 吸收方式 | 优先级 |
|---|---|---|---|
| 页面语义契约 | 吸收 | 将现有 Final Script 字段明确解释为 AUTHOR 页面合同 | P0 |
| 语义锚点—核心语义—必要细项 | 吸收 | 写入 AUTHOR 规则和 Critic 检查；允许页面按使命选择两层或三层 | P0 |
| 标题—判断—细项 | 吸收 | `onscreen.heading` 负责定位，`text/items` 承载判断、事实和限定 | P0 |
| 一条文字一个主要判断 | 吸收 | 作为生成与重写原则；审计只诊断清晰的多判断拥塞 | P0 |
| 数字必须带含义 | 吸收 | `self_read` 模式检查孤立数字和数字清单的角色说明 | P1 |
| 清单说明用途 | 吸收 | 检查模块标题、解释句或页面核心判断能否说明清单角色 | P1 |
| 重要关系至少一次文字化 | 有条件吸收 | 页面可用上屏文字或明确的视觉关系句表达；避免强制增加结论框 | P1 |
| 模糊指代控制 | 吸收 | `self_read` 模式增加“上述、相关、这些、其”等诊断，允许同块内明确指代 | P1 |
| 离线阅读测试 | 吸收 | 放入 AUTHOR 的 Critic/Rewrite 语义检查；确定性审计只覆盖可稳定判断的缺陷 | P0 |
| 手工 Semantic Unit ID | 不采纳 | 复用派生 `Pxx-Txx` 与 `content_integrity` | — |
| 手工 Integrity Contract | 不采纳 | 复用精确文字锁、结构哈希和 Stage 2 QA；补强 Stage 1 来源覆盖审计 | — |
| 固定关系枚举 | 部分吸收 | 作为写作参考词表；正式关系字符串保持开放 | P2 |
| “视觉结构”字段改名 | 暂不改名 | 保留解析兼容；规则中限定其表达语义关系和视觉语法，具体载体只有建议权 | P0 |
| 完整文字稿退出 Stage 2 | 不采纳 | 保留为 `semantic_context`，继续与锁定上屏文字隔离 | — |
| 演讲者备注退出视觉设计输入 | 已实现，补测试 | handoff 可保留备注，`visual-design-input.json` 不携带备注 | P1 |
| Deck Manifest | 不采纳 | Deck 级目标、受众、模式和叙事继续存放于现有权威产物 | — |

## 6. 目标架构

```text
foundation.json
    │ 来源事实、关系、边界
    ▼
deck-plan.json（v2 lean）
    │ 章节、页序、问题、使命、source_refs
    ▼
dist/final-script.md
    │ AUTHOR：核心判断、完整论证、完整稿、上屏层级、语义关系、备注
    ▼
Stage 02 handoff（派生）
    │ locked_text_items + content_integrity + verified relationships
    ▼
visual-design-input.json（派生）
    │ 精确文字锁 + 语义上下文 + 关系约束；作者视觉说明仅供参考
    ▼
Stage 02 视觉生产与 QA
```

阅读型 Contract 位于 AUTHOR 规则、Final Script 和 Critic 中；精确文字 Integrity 位于派生 handoff 中。两者各自承担单一职责。

## 7. 开发工作包

### P0：AUTHOR 阅读型写作合同

目标：先提高生成质量，避免由规则式代码代写上屏文字。

修改范围：

- `.agents/skills/cyberppt-script-workflow/SKILL.md`
- `docs/AUTHORING_METHOD.md`
- `docs/CYBERPPT_WORKFLOW.md`

新增规则：

1. AUTHOR 在全稿层声明 `delivery_mode: presented | self_read`。
2. `self_read` 内容页需让静默读者理解讨论对象、核心认识、主要依据和关键关系。
3. 每个复杂模块优先采用“模块标题 + 解释短句 + 必要细项”。
4. 上屏压缩保留对象、动作或判断、数量、条件、范围和结果。
5. 一条可见文字承担一个主要判断；页面组合承担完整论证。
6. 完整稿先形成，随后进行上屏选择、候选表达、定性评审和整页重写。
7. Critic 隐藏备注、完整稿和前后页，仅检查标题与上屏文字。
8. `视觉结构` 只表达关系、阅读顺序、层级、等权、汇聚、反馈和必要强调；具体载体及空间构图留给 Stage 2。

Critic 的离线阅读问题：

- 讨论对象是否明确？
- 核心认识是否明确？
- 模块为何共同出现？
- 主要因果、对应、层级、流程或反馈是否可读？
- 数字代表的业务含义是否明确？
- 是否存在依赖口头解释的标签或指代？
- 条件、范围、时间和责任是否因压缩丢失？

### P1：`self_read` 确定性审计增强

目标：捕获可稳定判定的阅读缺陷，保持 AUTHOR 的生成式主责。

修改范围：

- `script_engine/analysis_audits/final_script.py`
- `script_engine/onscreen_quality.py`
- `tests/script_engine/test_plan_review_and_internal_voice.py`
- 建议新增 `tests/script_engine/test_self_read_contract.py`

建议新增诊断：

| 诊断码 | 条件 | 默认级别 |
|---|---|---|
| `ONSCREEN_SELF_READ_MODULE_EXPLANATION_MISSING` | 复杂模块只有标题和名词细项，来源含有作用、任务或边界 | error |
| `ONSCREEN_SELF_READ_NUMBER_UNLABELED` | 数字作为独立主要单元出现，页面内无业务含义 | error |
| `ONSCREEN_SELF_READ_LIST_PURPOSE_UNCLEAR` | 清单的分类目的、作用或对象范围均不可见 | warning |
| `ONSCREEN_SELF_READ_AMBIGUOUS_REFERENCE` | 跨模块使用模糊指代，块内无明确先行词 | warning |
| `ONSCREEN_SELF_READ_RELATION_IMPLICIT` | Final Script 声明重要关系，可见文本和视觉关系句均未表达 | error |
| `ONSCREEN_SELF_READ_MULTI_CLAIM_LINE` | 一条可见文字承载多个独立动作或结论 | warning |

实现约束：

- 仅对 `delivery_mode=self_read` 的内容页启用。
- 复用 `script_engine.onscreen_quality` 的纯函数，避免复制 strict/legacy 审计逻辑。
- 来源只提供分类名时允许标签式列举。
- 不设置统一字数、行数或卡片数门槛。
- 不根据诊断机械增加模块、结论框或页面。
- 含糊的语义判断保留为 warning，并交给 Critic 复核。

### P1：Stage 02 边界回归保护

目标：验证对话关注的“语义完整、文字不丢、视觉自由”已经由正式交接链实现。

修改范围：

- `tests/test_content_integrity_contract.py`
- `tests/test_stage02_handoff.py`
- `tests/test_stage02_cyberppt_script_adapter.py`
- `tests/test_visual_structure_stage.py`

新增或强化测试：

1. Final Script 上屏层级稳定派生为 `Pxx-Txx`、根节点、父子关系和顺序。
2. 任一上屏文字变化会改变来源哈希；错误层级会改变结构哈希。
3. 显式关系句可进入 `business_relationships`，并经过语义验证。
4. `full_prose` 只进入 `semantic_context`，不会进入 `locked_on_screen_text`。
5. `speaker_notes` 不进入 `visual-design-input.json`。
6. `author_visual_notes_authority` 始终为 `advisory_only`。
7. v2 lean 的 Stage 2 只消费 Final Script，不回读 Deck Plan 的暂定文案。

### P2：关系表达与兼容清理

目标：让“视觉结构”稳定承担 Stage 1 关系表达，同时维持旧脚本兼容。

修改范围：

- `cyberppt/stage02_relationship_adapter.py`
- `cyberppt/script_quality/models.py`
- `tests/test_stage02_directed_relations_regression.py`
- `tests/test_relation_semantics_decoupling.py`

工作内容：

1. 文档提供推荐关系词：并列、顺序、包含、支撑、约束、映射、转化、汇聚、反馈、对应。
2. 保留开放的业务关系字符串和“主体—动作—对象—条件”结构。
3. Stage 2 继续负责拓扑归一化；任何视觉载体推断保持软约束。
4. 保留 `### 视觉结构` 标题兼容；新增脚本采用语义关系优先的写法。

### P2：真实页面回归样本

目标：用对话中的 P07、P11 思路验证阅读型合同，并防止只对合成案例有效。

建议样本：

- P07：五维诊断。验证“短标题 + 完整语义短句”能直接通过。
- P11：七类全景。验证一级模块解释句、二级条目语义和清单目的。
- P04：国家坐标与行业任务。验证数字含义、汇聚关系和 Stage 2 关系转换。
- 另选一套非政策、非标准体系材料，验证规则具备跨领域适用性。

样本只进入测试 fixture 或 benchmark，不成为新的内容权威。

## 8. 验收标准

### 8.1 架构验收

- Stage 01 权威产物仍为三个。
- v2 lean Deck Plan 继续拒绝 AUTHOR 字段。
- 未引入手工语义单元 ID、Deck Manifest、Integrity sidecar 或新确认节点。
- Final Script 仍是 Stage 2 唯一内容输入。

### 8.2 写作验收

- `self_read` 页面只看标题和上屏文字即可回答对象、判断、依据和关系。
- 复杂模块存在可读解释，分类型来源允许保留纯标签。
- 数字、条件、范围、时间、责任和结果不会因压缩丢失。
- 演讲者备注只补充背景、案例、来源说明和自然过渡。
- `presented` 模式不被强制扩写为阅读型密度。

### 8.3 Stage 2 验收

- 每条锁定文字拥有派生 ID，并保持层级、顺序和结构哈希。
- 业务关系经验证后进入视觉设计输入。
- 完整文字稿提供语义上下文，且不进入可见文字锁。
- 演讲者备注不影响视觉构图。
- AUTHOR 的具体视觉设想保持建议权。

### 8.4 测试验收

建议命令：

```bash
.venv/bin/python3 -m pytest tests/script_engine/test_self_read_contract.py -q
.venv/bin/python3 -m pytest tests/test_content_integrity_contract.py tests/test_stage02_cyberppt_script_adapter.py tests/test_stage02_handoff.py -q
.venv/bin/python3 -m pytest tests/test_stage02_directed_relations_regression.py tests/test_relation_semantics_decoupling.py tests/test_visual_structure_stage.py -q
.venv/bin/python3 -m pytest tests/script_engine -q
```

最终需再选一套真实 `self_read` 项目执行：

```text
Foundation 审计 → Deck Plan 审计 → Final Script audit/lint
→ prepare-stage02-handoff → visual design input → visual structure audit
```

## 9. 实施顺序

建议拆成三个独立变更批次：

1. **批次 A：AUTHOR 与 Critic 规则**
   只修改 Skill、流程文档和测试样例，先确认写作合同有效。

2. **批次 B：self_read 审计**
   增加纯函数、诊断码和单元测试；先以 warning 观察误报，再升级证据充分的规则。

3. **批次 C：Stage 2 回归保护**
   优先补测试；只有测试证明当前派生链存在缺口时才修改 handoff 或关系适配器。

每个批次完成后均运行对应定向测试。批次 C 完成后运行 Stage 01 与 Stage 2 的端到端回归。

## 10. 当前工作区风险

分析时工作区已有未提交改动，涉及：

- `cyberppt/stage02_handoff.py`
- `cyberppt/stage02_production/manifest_stage.py`
- `cyberppt/visual_stage/execution.py`
- `cyberppt/visual_stage/prompt_gate.py`
- `script_engine/analysis_audits/deck_plan.py`
- 两个相关测试文件

这些改动正在强化“Stage 2 只消费 Final Script”的边界，与本方案高度相关。正式实施前应先确定这些改动的预期行为和测试基线，随后在其上增量开发，避免覆盖用户工作。

本轮定向验证结果：

- `self_read` 相关测试：`3 passed`。
- Content Integrity、Stage 2 adapter 与 handoff 定向测试：`40 passed, 3 failed`。
- 三项失败均落在当前未提交改动改变的行为上：Deck Plan 边界不再进入 Stage 2、外部脚本哈希不再作为 handoff 门禁、旧 stale digest 测试仍期待失败。

因此，当前代码基线存在测试预期尚未同步的问题。该问题应在批次 A 开始前先完成归口，避免把现存失败误认为本方案引入的回归。

## 11. 待验证项

- 新增语义审计在不同业务领域的误报率。
- “复杂模块”判定能否稳定复用来源丰富度和现有 bare-label helper。
- 模糊指代检查在政策术语、专有名词和短标题场景中的容忍度。
- P07/P11 样本通过后，真实整套阅读效率是否改善。

上述项目在实现前属于未知信息。建议以 fixture、真实项目回归和 Critic 人工复核共同验证。

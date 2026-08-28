# P04 完整文字稿与上屏信息密度不足：代码根因分析

## 一、分析对象

- 项目：`power-data-infrastructure-standard-system-research-20260828-002`
- 目标页：P04《国家部署与先行先试任务形成标准验证依托》
- 问题表现：完整文字稿对来源信息压缩过度；上屏仅保留一个模块和三条概括性短句，无法独立承载国家部署、制度依据、试点任务与标准验证之间的完整关系。
- 分析范围：当前项目的 Foundation、Deck Plan、Final Script，以及 Script Engine 的 Schema、PLAN/AUTHOR 审计、Lint 和 Markdown 渲染代码。
- 本文性质：只读诊断结论，不包含代码修改、脚本改写或 Stage 02 操作。

## 二、结论摘要

P04 信息密度不足由三层因素共同造成：

1. **直接原因：Deck Plan 将 P04 预先收窄为一个 `phrase_led` 模块和三个必现短语。** AUTHOR 在该合同下只能围绕一个模块压缩表达。
2. **系统性根因：来源消费检查停留在 Source Truth 记录级。** P04 的三条记录包含 14 个语义单元，但每条记录只需命中一个 `full_prose_anchor`，整条记录即可被判定为已消费。
3. **放行原因：Schema、Audit 和 Lint 主要检查结构合法、锚点存在、禁用表达和长度上限。** 当前代码缺少语义单元覆盖、完整稿展开充分性、上屏业务关系完整性和完整稿段落重复检查。

源材料解析保留了足够内容；Markdown 渲染器只负责原样输出 Final Script。因此，源材料解析和 Markdown 渲染不构成本次压缩问题的根因。

## 三、P04 当前证据规模与成稿规模

| 指标 | 当前结果 |
|---|---:|
| Foundation 记录 | 3 条：ST0001、ST0002、ST0003 |
| Foundation 原始陈述总量 | 约 1555 字 |
| Foundation 语义单元 | 14 个 |
| Deck Plan 内容模块 | 1 个 |
| Deck Plan 必现上屏信号 | 3 个 |
| Deck Plan 上屏来源记录 | 2 条：ST0001、ST0003 |
| Final Script 完整文字稿 | 约 529 字 |
| Final Script 上屏模块 | 1 个 |
| Final Script 上屏条目 | 3 条 |

Foundation 中三条记录分别承担：

- **ST0001：国家数据基础设施总体部署。** 包含总体架构、四大建设方向、数据全生命周期、2026/2028/2029 三阶段目标、六项配套技术文件及统一目录标识、统一身份登记、统一接口要求。
- **ST0002：能源和可信流通制度依据。** 包含“数据要素×”绿色低碳行动、能源数据分类分级两个维度和三级管理、能源数据安全责任及风险应急、可信数据空间的流通与验证安排。
- **ST0003：中电联先行先试项目依托。** 包含成长级任务书、节点能力建设、四项核心任务、八类重点场景、既有工作基础、中电联双重职责以及可交付、可验证、可运营的阶段性成果要求。

当前完整稿保留了国家建设阶段、部分时间节点、制度文件名称、项目能力和标准验证任务，但出现以下压缩损失：

- 四大建设方向、数据全生命周期环节和六项技术文件均被改写成概括性名称；
- ST0002 的分类维度、管理级别、安全责任、风险应急、可信流通和生态培育等信息未充分展开；
- ST0003 的任务书等级、四项任务、重点场景、既有工作基础、中电联职责和阶段性成果要求未进入页面主论证；
- 完整稿第二段重复出现《能源行业数据分类分级指南（2026年版）》及其作用说明；
- 上屏层只留下“全面实施阶段—国家架构依据—试点验证依托”三个概括信号，缺少主体、对象、具体任务、制度层级和实践承接关系。

## 四、生成与放行链路

```text
Foundation：3 条记录 / 14 个语义单元
        ↓
Deck Plan：1 个模块 + phrase_led + 3 个 required_signals
        ↓
AUTHOR：529 字完整稿 + 1 个模块 / 3 条上屏短句
        ↓
Schema：结构合法
        ↓
audit-final：3 个记录级锚点命中，3 个上屏信号出现
        ↓
lint：未触发禁用表达、结构重复或长度上限
        ↓
render-stage02：原样写入 final-script.md
```

该链路说明，信息压缩发生在 Deck Plan 和 AUTHOR 阶段，审计器负责放行，渲染阶段没有再次删减内容。

## 五、直接原因：P04 Deck Plan 预先收窄

P04 的 Deck Plan 位于：

`script/deck-plan.json:174`

关键合同如下：

- `content` 只有“国家环境与试点依托”一个模块；
- `onscreen_composition.mode = selective_lead`；
- `lead_budget = 1`；
- `expression_mode = phrase_led`；
- `primary_relation.type = none`；
- `required_signals` 只有“全面实施阶段”“国家架构依据”“先行先试标准验证”；
- `onscreen_refs` 只选择 ST0001 和 ST0003，ST0002 无上屏消费职责。

该合同没有为以下内容建立独立上屏职责：

- 国家建设任务及三阶段目标；
- 六项技术文件与“三统一”建设要求；
- 能源行业分类分级、安全管理和可信流通制度；
- 先行先试任务书的能力、任务、场景和成果要求；
- 国家部署经由行业节点建设转化为标准验证的承接机制。

AUTHOR 必须继承 Deck Plan 的模块标题、表达模式和必现信号。因此，当前上屏结果首先属于 PLAN 层的内容架构不足。

## 六、系统性根因：来源消费检查粒度过粗

相关代码：

- `script_engine/analysis_audits/final_script.py:205`
- `script_engine/analysis_audits/common.py:484`

当前 `source_consumption` 以 ST 记录为键：

```json
{
  "source_ref": "ST0001",
  "anchors": [
    "2025年1月，国家发展改革委、国家数据局、工业和信息化部联合印发"
  ]
}
```

审计器的核心判断是：

1. 找到该记录对应的 `full_prose_anchors`；
2. 检查锚点字符串是否出现在 `full_copy`；
3. 检查数字、日期、条件、主体和状态等保护字段是否出现；
4. 锚点及保护字段满足后，将该记录视为已经消费。

这一模型没有继续检查该记录内部的全部 `semantic_units`。ST0001、ST0002、ST0003 分别包含 4、4、6 个语义单元，单个锚点无法证明其余语义单元已经得到表达或明确后置。

因此，记录级来源消费与语义单元级内容完整性之间存在明显粒度错配。

## 七、放行原因一：Final Script Schema 缺少内容充分性约束

相关代码：

- `contracts/final-script.schema.json:97`
- `contracts/final-script.schema.json:179`

当前 Schema 对内容页的要求包括：

- `mission` 非空；
- `core_message` 非空；
- `onscreen` 至少有一个模块；
- 上屏模块必须有非空标题。

当前 Schema 没有要求：

- 内容页必须包含 `full_copy`；
- 完整稿必须达到任何语义覆盖标准；
- 上屏模块必须包含 `text` 或 `items`；
- 上屏必须覆盖多少来源特征；
- 上屏必须形成完整的事实—关系—落点结构。

Schema 因此只能证明 JSON 结构合法，无法判断汇报内容是否充分。

## 八、放行原因二：内容覆盖审计只检查作者预先声明的义务

相关代码：

- `script_engine/analysis_audits/deck_plan.py:45`
- `script_engine/analysis_audits/final_script.py:158`
- `cyberppt/content_route.py:205`

`_audit_authored_content_coverage` 只检查 `content_route.meaning_signals` 是否出现在最终稿中。

当前规则仅在 `risk`、`coordination`、`next_step` 等侧面出现时强制要求 `meaning_signals`。P04 使用 `background` 和 `current`，因此可以不声明任何 `meaning_signals`，内容覆盖审计也就没有可执行的检查对象。

这形成了一个关闭失败条件：

```text
PLAN 没有声明具体内容义务
        ↓
AUTHOR 没有表达这些具体内容
        ↓
AUDIT 因为没有声明义务而无法报错
```

## 九、放行原因三：上屏审计只验证三个必现短语

相关代码：

- `script_engine/analysis_audits/final_script.py:404`

`_audit_authored_onscreen_contract` 主要检查：

- 模块标题是否与 Plan 一致；
- 每个 `required_signal` 是否出现在模块正文；
- 是否包含禁止信号；
- 模块之间是否越界；
- 是否出现错误的关系或角色。

P04 的三个必现信号全部出现，因此一条模块标题加三条短句即可通过。代码没有检查：

- 每条来源记录的关键业务对象是否可见；
- 三条短句是否交代主体、动作、对象和作用；
- 制度依据是否具有层次；
- 先行先试任务是否形成能力—任务—场景—成果的完整链条；
- 上屏内容能否脱离讲解独立回答页面问题。

## 十、放行原因四：Lint 强调长度上限，缺少信息下限

相关代码：

- `script_engine/contracts.py:118`
- `script_engine/contracts.py:319`

Lint 当前覆盖：

- 禁用表达；
- 同一上屏模块内的近重复条目；
- 演讲者备注占位；
- 上屏末尾标点；
- 上屏短语长度上限；
- 标题数量声明与模块数量的提示。

其中上屏细项通常受 30 个有效字符上限约束，完整命题受 90 个有效字符上限约束。代码没有相应的信息充分性下限，也没有完整稿段落级重复检查。

当前 P04 第二段的重复句位于 `full_copy`，不属于同一上屏模块内部的近重复，因此未被现有重复检查捕获。

## 十一、AUTHOR 与代码的责任边界

相关代码：

- `script_engine/cli.py:306`
- `.agents/skills/cyberppt-script-author/SKILL.md:101`
- `.agents/skills/cyberppt-script-author/SKILL.md:148`

`cyberppt-script` CLI 提供 validate、audit、lint、render 等命令，没有自动 AUTHOR 命令。最终内容由语言模型按照 AUTHOR Skill 编写，代码负责结构校验、语义边界审计和渲染。

AUTHOR Skill 已要求：

- 标准或高密度页面使用 2—4 个论证段；
- 先完成充分的完整稿，再压缩上屏；
- 缩写不得删除主体、谓词、状态、条件和业务关系；
- 模块数量应由不同证据和业务含义决定；
- 不能把具体判断压薄为通用标签。

当前 P04 虽然形式上具有三个段落，但第二段存在重复，多个来源特征没有承担明确论证职责。作者执行没有达到 Skill 规定的专业质量；校验器也没有把这一质量要求转化为可执行门禁。

## 十二、137 字反例

为验证代码门禁，构造了一个只在内存中运行的 P04 反例：

- 完整稿缩短到 137 字；
- 仅保留三个来源锚点、受保护日期和状态词；
- 上屏仍为一个模块和三个必现短语。

运行 `audit_final_script` 后得到：

```json
{
  "trial_full_copy_chars": 137,
  "trial_onscreen_items": 3,
  "p04_blocking_issues": [],
  "all_blocking_count": 0,
  "all_warning_count": 0
}
```

该反例证明：当前门禁可以放行“锚点和保护值齐全、实际业务论证严重不足”的页面。

## 十三、渲染器不承担压缩责任

相关代码：

- `script_engine/render.py:40`

`render_stage02_markdown` 的行为是：

- 从 Final Script 读取 `full_copy`；
- 经过交付清洁处理后原样写入“完整文字稿”；
- 从 Final Script 读取 `onscreen`；
- 按模块层级原样写入“上屏文字”。

最终 JSON 中已经只有一个上屏模块和三条短句，Markdown 只是忠实反映该结果。

## 十四、根因优先级

| 优先级 | 根因 | 影响 |
|---|---|---|
| P0 | 来源消费停留在 ST 记录级，未覆盖 semantic unit | 多个具体事实可被一个锚点整体代表 |
| P0 | P04 Plan 只声明一个模块和三个概括信号 | AUTHOR 缺少展开多个业务含义的合同空间 |
| P1 | Final Audit 只检查显式声明义务 | Plan 漏报的内容不会被 Audit 主动发现 |
| P1 | Schema 对完整稿和上屏内容要求过低 | 极薄内容仍可满足结构合法性 |
| P1 | Lint 只有长度上限和局部重复检查 | 过短、信息不足和完整稿重复无法阻断 |
| P2 | AUTHOR Critic 未落实专业质量要求 | 生成稿出现压缩损失和重复句 |

## 十五、建议修复方向

### 1. 建立语义单元级消费合同

将每条 `semantic_unit` 明确标记为：

- `full_copy`：必须进入完整文字稿；
- `onscreen`：必须进入上屏模块；
- `reserved_for_later`：明确交由后续页面承接；
- `trace_only`：仅保留追溯职责；
- `intentional_omission`：给出具体删减理由。

审计器应按语义单元检查消费状态，记录级锚点只作为辅助证据。

### 2. 强化 PLAN 内容职责

对于来源丰富且承担关键论证职责的页面，Plan 应明确：

- 不可省略的业务对象；
- 需要可见的关系；
- 每个模块的问题、证据职责和页面落点；
- 后置内容的具体目标页面；
- `content_load` 及其来源依据。

避免使用机械字数或固定模块数量；以不同业务含义和证据职责决定模块结构。

### 3. 强化 Final Audit

增加以下检查：

- 语义单元消费状态完整；
- P0/P1、责任主体、状态、条件、分类层级和关键任务没有被概括词替代；
- 上屏至少覆盖 Plan 选择的业务对象、动作、关系和落点；
- `content_load: light` 必须有来源稀薄依据；
- Plan 未声明具体义务但来源明显丰富时，输出阻断性问题。

### 4. 增加完整稿重复检查

对 `full_copy` 按句子和段落执行归一化相似度检查，捕获同句重复、近重复和无新增信息的段落。

### 5. 增加回归测试

将本次 137 字 P04 反例写入测试，预期至少触发：

- `FULL_COPY_SEMANTIC_UNIT_GAP`；
- `ONSCREEN_SOURCE_DETAIL_INSUFFICIENT`；
- `CONTENT_LOAD_UNDERDECLARED`；
- 完整稿重复时触发 `FULL_COPY_DUPLICATION`。

## 十六、建议验收标准

代码修复完成后，应同时满足：

1. P04 的 14 个语义单元均有明确消费或后置状态；
2. 单个记录级锚点不能替代该记录全部语义单元；
3. 137 字反例必须被审计阻断；
4. P04 第二段重复句必须被 Lint 识别；
5. 完整稿和上屏可由作者根据证据职责自由组织，不采用统一字数和模块配额；
6. 源材料较薄的页面仍可通过 `content_load: light` 和具体依据保留；
7. 修复不能迫使每个 Word 条目机械映射为一个卡片或模块；
8. Stage 01 审计通过应同时证明来源忠实、语义消费完整和屏幕表达可独立阅读。

## 十七、当前状态

- 已完成代码级只读诊断；
- 已验证 P04 Foundation 内容完整；
- 已定位 Deck Plan、AUTHOR、Schema、Audit、Lint 和 Renderer 的责任边界；
- 已完成 137 字内存反例；
- 尚未修改代码；
- 尚未重写 P04；
- 尚未重新生成或更新 Stage 02 产物。

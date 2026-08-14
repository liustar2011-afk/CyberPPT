# 方案型材料论证顺序语义审计设计

## 目标

在仓库级 PPT 方案流程中增加可确定执行、可回归验证的语义审计，阻止以下问题通过质量闸门：

- Source Truth 记录在同一条证据中混合事实、判断、建议或边界；
- 事实基础页提前承担首期取舍、建设方案或业务闭环等后续结论；
- 页面主判断超出页面使命或所引证据能够支持的范围；
- 依赖环境变化、现实问题或能力缺口的结论在前置命题出现前被提出；
- Source Truth 的页面映射与 Outline 的实际引用不一致。

本设计适用于所有方案型材料，不为单一项目或单一关键词编写特例。

## 设计原则

1. 不依赖关键词封禁。词语只提供风险信号，是否合法由证据角色、页面角色和前置关系共同决定。
2. 保留方案结构自由度。系统不强制所有方案使用同一章节模板，只要求需推导的结论具备明确前置条件。
3. 确定性审计优先。相同输入必须得到相同结果，错误码和重试方向必须可测试。
4. 跨阶段一致。Source Truth、Outline 和后续页面脚本使用同一套论证角色，不允许各阶段自行解释。
5. 审计失败后局部换方向重试，不放弃任务，也不无差别重建全部已通过内容。

## 方案比较与选择

### 方案一：关键词规则

按“首期、建设、升级、闭环”等词语判断是否提前出现。实现成本低，但无法区分同一词语在基础页和范围页中的不同合法性，误报和漏报都会较高。

### 方案二：模型语义复审

使用模型判断页面逻辑。理解能力较强，但输出不完全稳定，难以作为阻断式仓库闸门，也难以建立精确回归测试。

### 方案三：语义契约、确定性审计和轻量词义辅助

为证据和页面显式声明论证角色，以依赖图检查论证顺序；词义辅助只负责发现值得核验的候选。该方案可解释、可测试，并能覆盖不同方案结构。

采用方案三。

## 一、统一论证角色

新增公共论证角色枚举：

| 角色 | 含义 |
|---|---|
| `foundation` | 已存在的业务、数据、组织、制度或技术事实 |
| `change` | 外部环境、业务对象或要求发生的变化 |
| `gap` | 现有方式与新要求之间的不匹配 |
| `necessity` | 为什么需要开展研究或建设 |
| `positioning` | 拟建设能力的性质、对象和总体定位 |
| `solution` | 能力体系、业务闭环、技术或产品方案 |
| `scope` | 首期范围、取舍、边界和分期 |
| `implementation` | 任务、计划、组织和实施路径 |
| `assurance` | 投资、治理、安全、运营和验收保障 |
| `decision` | 待决事项、立项条件和后续决策 |

这些角色表达论证功能，不构成固定章节模板。方案可以省略角色或调整展示顺序，但任何存在依赖关系的结论必须显式声明依赖。

证据命题使用更细的 `claim_role`：

- `fact`
- `change`
- `problem`
- `judgment`
- `recommendation`
- `boundary`
- `unresolved`

页面角色与证据角色之间维护仓库级兼容矩阵。例如 `foundation` 默认允许 `fact`，禁止将 `recommendation` 作为页面主结论；`scope` 可以使用 `fact`、`judgment`、`recommendation` 和 `boundary`。

## 二、Source Truth 契约扩展

每条记录增加：

```json
{
  "claim_role": "fact",
  "semantic_units": [
    {
      "text": "中电联具备推动跨主体数据和业务协同的组织条件",
      "claim_role": "fact"
    }
  ],
  "allowed_page_roles": ["foundation", "necessity", "scope"],
  "forbidden_page_roles": ["solution"],
  "depends_on": []
}
```

### 语义原子性

一条记录可以保留完整原文 `quote`，但其可用于推导的 `statement` 必须是同一性质的原子命题。若一个原文段落同时包含事实和建议，应拆成两条记录，并可共享同一来源定位。

例如原 `S006` 应拆为：

1. `fact`：中电联具备跨主体组织协调条件；
2. `recommendation`：现有基础可支撑首期从全国总盘和定期报告入手。

第二条必须声明对工作基础、环境变化和能力缺口相关证据的依赖，不得映射为基础页主结论。

### Source Truth 新增错误

- `SOURCE_RECORD_MIXED_CLAIMS`
- `SOURCE_FACT_CONTAINS_RECOMMENDATION`
- `SOURCE_DEPENDENCY_MISSING`
- `SOURCE_PAGE_ROLE_INCOMPATIBLE`

现有 `SOURCE_RECORD_COMPOSITE` 继续负责结构完整性，新错误负责语义原子性，二者不得混用。

## 三、Outline 页面契约扩展

每个内容页增加：

```json
{
  "argument_role": "foundation",
  "allowed_claim_roles": ["fact"],
  "prerequisite_pages": [],
  "forbidden_claim_roles": ["recommendation"],
  "chapter_position": "evidence_base"
}
```

其中：

- `argument_role` 是页面在全篇论证中的职责；
- `allowed_claim_roles` 可在仓库默认矩阵基础上收窄，但不能无理由扩大；
- `prerequisite_pages` 指明该页主结论依赖的已出现页面；
- `forbidden_claim_roles` 表达当前页不可承担的结论性质；
- `chapter_position` 为可读标签，不参与核心合法性判定。

模板页不要求上述字段。章节过渡页继续只能包含章序号和章名。

## 四、论证依赖图

新增独立模块 `cyberppt/argument_flow_contract.py`，负责构造并审计有向无环图：

```text
证据记录 → 页面主判断 → 后续页面主判断
```

核心检查：

1. 页面所引证据的 `claim_role` 是否与页面 `argument_role` 兼容；
2. 页面主判断是否超出其证据状态和边界；
3. 所有 `prerequisite_pages` 是否存在且序号小于当前页；
4. 依赖图是否存在环；
5. 需要 `change` 或 `gap` 支撑的 `necessity/solution/scope` 结论是否已建立前置命题；
6. 页面标题、业务问题、主判断和论证角色是否指向同一个页面使命。

新增 Outline 错误：

- `CLAIM_ROLE_EXCEEDS_PAGE_ROLE`
- `PREMATURE_SOLUTION_CLAIM`
- `PREREQUISITE_PAGE_MISSING`
- `PREREQUISITE_PAGE_NOT_EARLIER`
- `ARGUMENT_DEPENDENCY_CYCLE`
- `ARGUMENT_ORDER_INVALID`
- `PAGE_MISSION_MESSAGE_MISMATCH`

“首期”等词语可以触发候选分类检查，但不能单独形成错误。例如它出现在 `scope` 页时合法，出现在只允许事实的 `foundation` 页并作为主结论时才失败。

## 五、跨阶段交叉审计

`outline-audit` 增加 Source Truth 输入并执行以下校验：

1. Outline 中的每个 `source_ref` 必须存在；
2. Source Truth 中某记录的 `page_refs` 与 Outline 实际引用必须一致；
3. 页面主判断使用的证据角色必须符合页面角色；
4. `recommendation`、`boundary` 和 `unresolved` 不得被提升为无条件事实；
5. 证据 `depends_on` 对应的命题必须在当前页或前置页得到覆盖。

新增错误：

- `PAGE_EVIDENCE_MAPPING_MISMATCH`
- `PAGE_SOURCE_ROLE_INCOMPATIBLE`
- `SOURCE_STATUS_UPGRADED`
- `EVIDENCE_PREREQUISITE_UNCOVERED`

为兼容旧项目，迁移期允许显式的 `argument_contract_mode: legacy`。新建正式方案项目默认使用 `strict`；现有项目只有在重新进入 Stage 01 时才要求升级，避免无关历史项目突然全部失败。

## 六、审计集成与重试

Source Truth 审计顺序：

```text
结构合法性 → 语义原子性 → 状态与边界 → 依赖完整性 → 页面角色兼容性
```

Outline 审计顺序：

```text
模板结构 → 页面字段 → Source Truth 交叉映射
→ 页面角色兼容 → 前置关系 → 章内论证顺序
```

错误与重试策略：

| 错误类别 | 重试策略 |
|---|---|
| 混合命题 | `split_semantic_units` |
| 页面结论越权 | `reassign_claim_to_later_page` |
| 前置命题缺失或倒置 | `rebuild_argument_sequence` |
| 页面证据映射不一致 | `reconcile_page_evidence_mapping` |
| 状态被升级 | `restore_source_status_and_boundary` |

重试保留已通过记录和页面，只修改错误涉及的最小子图。连续使用同一策略仍失败时，沿既有机制切换方向，不直接放弃项目。

## 七、命令行接口

推荐接口：

```text
python -m cyberppt source-truth-audit <project> --input <source-truth.json>
python -m cyberppt outline-audit <project> --input <outline.json> --source-truth <source-truth.json>
```

如果未显式传入 `--source-truth`，`outline-audit` 从项目标准路径解析。严格模式下文件不存在即失败；旧项目兼容模式下保留原行为并给出迁移提示。

审计报告增加：

- `argument_contract_mode`
- `checked_source_truth`
- `argument_graph`
- `failed_edges`
- `retry_scope`

## 八、测试设计

### Source Truth

1. 单一事实记录通过；
2. 同一记录混合事实与建议，返回 `SOURCE_RECORD_MIXED_CLAIMS`；
3. `F` 类型承载首期建议，返回 `SOURCE_FACT_CONTAINS_RECOMMENDATION`；
4. 推荐命题缺少依赖，返回 `SOURCE_DEPENDENCY_MISSING`；
5. 同一原文拆为事实和建议两条记录后通过。

### Outline

1. `foundation` 页仅使用事实，通过；
2. `foundation` 页将首期建议作为主结论，返回 `CLAIM_ROLE_EXCEEDS_PAGE_ROLE`；
3. `necessity` 页依赖尚未出现的 `gap` 页，返回 `PREREQUISITE_PAGE_NOT_EARLIER`；
4. “基础 → 变化 → 断点 → 必要性”顺序通过；
5. “首期”出现在 `scope` 页且证据状态为建议，不误报；
6. 依赖形成环，返回 `ARGUMENT_DEPENDENCY_CYCLE`。

### 跨阶段

1. Source Truth 映射 `S004—S006`，Outline 却引用 `S002`，返回 `PAGE_EVIDENCE_MAPPING_MISMATCH`；
2. Outline 引用不存在的记录，失败；
3. `boundary` 被改写为确定事实，返回 `SOURCE_STATUS_UPGRADED`；
4. 修复后的当前项目第一章通过；
5. 未修复的当前项目原始数据稳定失败。

## 九、验收标准

1. 当前项目原始 `S006 + p04` 组合必须被 Source Truth 或 Outline 闸门阻断；
2. 修订后的“既有基础 → 环境变化 → 现实断点 → 研究必要性”必须通过；
3. 合法范围页中的“首期”不得因关键词本身失败；
4. Source Truth 与 Outline 页面映射不一致必须失败；
5. 所有错误均包含具体记录、页面、失败边和可执行重试策略；
6. 新规则不得把方案型架构固化为唯一章节模板；
7. 现有与本功能相关的测试全部通过，仓库其他已知失败不得被错误归因于本次修改。

## 十、非目标

- 不在本次设计中实现通用自然语言推理引擎；
- 不要求模型输出直接决定审计通过或失败；
- 不修改 PPT 视觉生产和 Stage 2 图片生成流程；
- 不按关键词硬编码当前电力项目；
- 不自动重写用户已经确认的页面内容。

# Stage 01 语义规则体系通用重构方案

日期：2026-08-30
状态：开发方案
关联审计：`docs/reviews/stage01-rule-hardcoding-audit-20260830.md`

## 1. 技术判断

结论：`SUPPORT WITH CONDITIONS`

需要从代码层重构当前规则体系。实施条件包括：

1. 保持 `foundation.json`、`deck-plan.json`、`dist/final-script.md` 三个权威
   内容产物，不增加项目级规则回执、审批文件或平行事实源；
2. 保持 PLAN v2 lean，只负责页面使命和来源边界，不把模块文案提前塞回 PLAN；
3. AUTHOR 继续由主 Agent 完成，代码负责提供结构化表达接口和确定性验证；
4. 语义质量中无法确定性证明的部分交给 AUTHOR/Critic 与人工审核，代码不得
   通过扩大关键词表伪造确定性；
5. 先建立新契约和双轨兼容，再删除旧规则，避免一次性改写造成历史项目失效。

## 2. 问题定义

用户期望的系统行为是：

> 任何页面结论、模块结论和可见明细，都能够回答“它来自哪条事实、承担什么
> 论证角色、与父级结论是什么关系、是否保持来源状态与责任边界”。

当前系统只能稳定回答页面级的“用了哪些来源”。它无法稳定回答模块级的
“哪条来源证明哪个结论”。语义审计因此大量依赖最终文案中的词语和字符特征。

## 3. 根因模型

### 3.1 数据契约缺口

Foundation 已经包含 `status`、`semantic_status`、`argument_duty`、
`claim_role`、`claim_origin`、actors、conditions 和 argument relations。
Deck Plan v2 lean 也保留页面级 `source_refs`。

Final Script 的上屏模块目前只有：

- `heading`
- `text`
- `items`

模块没有 claim/evidence provenance。进入最终审计后，Foundation 的结构化语义
无法与具体模块、标题和明细建立确定绑定。

### 3.1.1 已有能力与实际断点

仓库已经具备本方案所需的大部分上游能力，无需重新建设源材料语义解析模型：

- 轻量 `script` profile 的 `prepare-source-context` 已生成稳定 `SU-*` source
  units、来源结构、阅读负载和读取策略；
- `prepare-script-foundation` 已明确要求主 Agent 在 Foundation 中写入
  `semantic_units`、facts、constraints、numbers、argument nodes、inferred
  relations，并绑定稳定 `SU-*` 引用；
- strict/legacy 路线的 Source Truth → Foundation 机械投影已保留
  `status`、`semantic_status`、`argument_duty`、`claim_role`、`claim_origin`、
  actors、conditions、argument nodes 和 argument relations；
- `validate_foundation_detail_atomicity` 已检查复合来源是否被拆成可追溯
  `semantic_units`，并检查来源单元覆盖和明细损失。

实际断点位于 Foundation 下游：

1. Deck Plan v2 lean 有意只保留页面使命和页面级 `source_refs`；
2. Final Script 的 module/item 没有稳定 ID 和 provenance；
3. 最终审计无法把 Foundation 中已存在的 typed semantics 对齐到具体可见单元；
4. 审计转而使用关键词和字符特征重新猜测上游已经理解过的语义。

因此本方案的核心是“恢复和延长既有语义链路”，不新建第二套 Foundation、
Source Truth 或语义模型。

### 3.2 职责错位

确定性审计承担了以下超出能力边界的任务：

- 从动词推断 argument role；
- 从名词推断主体类型；
- 从文本相似度推断证据是否充分；
- 从固定短语推断状态、成熟度、因果和责任；
- 从字符数推断语义是否完整。

这些判断只能产生候选线索，无法形成可靠阻断。

### 3.3 新旧执行面并存

当前至少存在两套语义检查面：

- `script_engine/contracts.py` 与 `script_engine/analysis_audits/*`；
- `cyberppt/script_quality/*`。

两套实现拥有不同词表、阈值、例外和项目残留，造成入口间结果漂移。

### 3.4 事故修复缺少规则治理

历史问题通常通过新增正则、业务词或项目例句处理。规则缺少：

- 适用层级与 profile；
- 规则类型；
- 置信度；
- 阻断理由；
- 责任模块；
- 失效条件；
- 合法反例；
- 跨领域测试。

项目经验因此逐渐变成全局硬编码。

## 4. 目标架构

```text
Foundation typed facts
  │  status / duty / actor / condition / origin / relations
  ▼
Deck Plan v2 lean
  │  page mission + page source boundary
  ▼
AUTHOR Final Script
  │  visible copy + module/item provenance bindings
  ▼
Semantic Contract Auditor
  ├─ structural blockers
  ├─ typed compatibility blockers
  ├─ protected-payload blockers
  └─ heuristic review candidates
  ▼
Critic / Rewrite / Human review
  ▼
Stage 02 locked text
```

架构原则：

1. Foundation 保存来源语义；
2. Deck Plan 保存页面问题、使命和来源边界；
3. AUTHOR 决定页面结论、模块组织和证据取舍；
4. Final Script 同时保存可见文案及其模块级来源关系；
5. 确定性审计验证引用、类型、状态、边界和结构兼容；
6. Critic 判断论证是否充分、表达是否自然、综合判断是否成立；
7. 文本正则只处理格式、泄漏、安全和候选告警。

## 5. Final Script 模块级 Provenance 契约

### 5.1 JSON 表达

建议将 Final Script 合同升级为 `1.1`，内容模块采用以下结构：

```json
{
  "id": "M04-02",
  "heading": "方案拟由统计与数智部电力供需分析处牵头建设",
  "items": [
    {
      "id": "M04-02-I01",
      "text": "该处掌握统计口径和供需分析逻辑"
    }
  ],
  "provenance": {
    "derivation": "direct",
    "claim_refs": ["ST0018"],
    "bindings": [
      {
        "target": "heading",
        "source_refs": ["ST0018"],
        "relation": "expresses"
      },
      {
        "target": "M04-02-I01",
        "source_refs": ["ST0020"],
        "relation": "supports"
      }
    ]
  }
}
```

字段说明：

| 字段 | 责任 |
|---|---|
| `id` | 为模块和明细提供稳定目标，不以文案作为关联键 |
| `derivation` | `direct`、`synthesis`、`relation` 三类作者操作 |
| `claim_refs` | 支撑模块结论的 Foundation 事实 |
| `bindings.target` | 指向 heading、text 或具体 item ID |
| `bindings.source_refs` | 该可见单元使用的事实范围 |
| `bindings.relation` | `expresses`、`supports`、`qualifies`、`implements`、`contrasts`、`sequences` |

AUTHOR 只声明引用与关系。`status`、`argument_duty`、actor、condition、
claim origin 和责任强度由审计器从 Foundation 引用项派生，禁止在 Final Script
重复声明一套可漂移的状态。

### 5.2 Markdown 权威表达

`final-script.md` 仍是人工审核的权威成果。每个内容页增加可读的“模块证据映射”
段落，由 JSON 镜像机械渲染：

```markdown
### 模块证据映射

- M04-02｜direct｜模块结论：ST0018
  - M04-02-I01｜supports｜ST0020
```

该段落不进入上屏锁定文字，不进入 ImageGen 文案，也不新建第四个权威产物。
`check-sync` 必须同时核对可见文案和证据映射。

### 5.3 合同版本与兼容

- `final-script 1.0`：允许读取，语义启发式只产生 legacy warning；
- `final-script 1.1`：新项目默认，内容模块必须具备 provenance；
- Foundation `source_consumption_contract_version=2` 的 strict/legacy 项目必须输出
  Final Script 1.1；
- 迁移工具只能生成空映射骨架，不允许依据关键词自动猜测关系；
- 历史项目需要重新进入 AUTHOR/Critic 才能获得完整 provenance。

## 6. 单一语义审计内核

新增 `script_engine/semantic_contract/`，作为唯一权威语义审计实现：

```text
script_engine/semantic_contract/
  models.py
  foundation_index.py
  provenance.py
  compatibility.py
  protected_payload.py
  diagnostics.py
```

### 6.1 `foundation_index.py`

这是现有 Foundation 数据的只读适配层，不执行语义重建。它复用
`foundation_items_by_id`、现有 argument node/relation 索引和 Source Unit 绑定，
把 facts、concepts、entities、relations、arguments、constraints、numbers 和
argument nodes 暴露为统一 typed records。

输出能力：

- `record(ref)`
- `status(ref)`
- `argument_duty(ref)`
- `actors(ref)`
- `conditions(ref)`
- `claim_origin(ref)`
- `relations_between(refs)`

禁止该适配层依据最终文案关键词补写或修正 status、duty、actor 和 relation。
Foundation 字段缺失时返回 `unknown/review_required`，并把问题路由回 UNDERSTAND。

strict/legacy 的 `_atomic_semantic_profile` 当前仍依据推荐、规划和未来动作关键词
推断部分状态。迁移期应优先复制经过 Source Truth 校验的 typed fields；只有旧
Source Truth 缺少字段时才保留兼容推断，并输出 legacy warning。该兼容推断不能
成为新项目的语义权威。

### 6.2 `provenance.py`

执行纯结构校验：

- module/item ID 唯一；
- target 存在；
- source ref 存在；
- module refs 是 page `source_refs` 的子集；
- 每个可见结论和明细恰好有一个处置；
- `direct` 只允许一个主 claim ref；
- `synthesis` 和 `relation` 至少两个 refs，并声明关系；
- 未绑定文案阻断；
- 跨页取证阻断。

### 6.3 `compatibility.py`

校验结构化角色兼容，不读取业务关键词：

| 目标关系 | 允许的来源角色 | 主要约束 |
|---|---|---|
| `expresses` | 任一单一事实角色 | 可见单元必须保持该事实状态与责任边界 |
| `supports` | premise、support、detail | 不能以 response/recommendation 单独证明 existing premise |
| `qualifies` | boundary、detail、constraint | 只能收窄或解释目标结论 |
| `implements` | response、recommendation | 目标必须是任务、建议或规划类结论 |
| `contrasts` | gap、premise、driver、consequence | 两端必须有独立来源 |
| `sequences` | response、detail 或显式 relation | 必须存在顺序、阶段或触发条件关系 |

兼容矩阵只使用 Foundation 的枚举字段。无法确定时返回 `review_required`，不通过
词语猜测升级为错误。

### 6.4 `protected_payload.py`

从绑定事实中生成保护集合：

- 正式主体；
- 文件名称；
- 数字和日期；
- 状态与模态；
- 责任动作；
- 条件和适用范围；
- 否定、独立选择和边界。

确定性代码只检查精确值、规范化值或显式枚举的保留情况。复杂同义改写进入
Critic review，不使用全局动词表作最终裁决。

### 6.5 `diagnostics.py`

所有问题输出统一结构：

```json
{
  "code": "EVIDENCE_ROLE_INCOMPATIBLE",
  "severity": "blocking",
  "page_id": "P04",
  "module_id": "M04-01",
  "target": "M04-01-I02",
  "claim_refs": ["ST0020"],
  "evidence_refs": ["ST0018"],
  "relation": "supports",
  "reason": "response cannot independently support an existing support claim"
}
```

错误必须指出具体 ID 和结构冲突，禁止只报告某个关键词命中。

## 7. 规则治理模型

新增仓库级规则注册表，仅管理代码规则，不产生项目产物：

```yaml
id: ONSCREEN_MARKDOWN_LEAK
kind: format
scope: final_script.onscreen
profiles: [script, strict, legacy]
severity: blocking
confidence: deterministic
implementation: script_engine.contracts.check_markdown_leak
owner: script_engine
counterexample_tests:
  - tests/rules/test_markdown_leak.py::test_plain_business_text_is_allowed
```

规则类型：

- `schema`
- `binding`
- `format`
- `safety`
- `semantic_contract`
- `semantic_heuristic`
- `project_specific`

治理要求：

1. `semantic_heuristic` 默认只能 warning；
2. `project_specific` 禁止进入默认 profile；
3. blocking 规则必须有确定性依据和至少一个合法反例测试；
4. 所有规则必须声明执行入口和 owner；
5. CI 检查未注册阻断码、重复规则码和孤立规则；
6. 项目经验先进入 benchmark，再决定是否提炼为结构规则。

## 8. 旧规则处置

### 8.1 保留为 blocking

- Schema、ID、引用存在性与范围；
- 哈希、审批、锁定文本和输入输出绑定；
- Markdown、后台元数据和内部指令泄漏；
- 仓库明确禁用的句式；
- 页码、章节顺序、枚举和文件完整性。

### 8.2 降级为 warning

- `_SEMANTIC_PREDICATES`；
- `_SEMANTIC_LINE_PATTERNS`；
- `_RELATION_VISIBILITY_SIGNALS` legacy fallback；
- optionality、progression、gap 的文本正则；
- 字符数、密度、文本相似度、通用动词和主体名词判断。

### 8.3 删除或迁移

- `contracts/banned-phrasing.json` 中的行业业务对象；
- `rules.yaml` 中的项目专用跨页指纹；
- AUTHOR 合同中的真实项目名称和事实性例句；
- relationships、actor、scope 等词表中的历史项目对象；
- 新旧执行面中功能相同、判断不同的重复规则。

## 9. AUTHOR / CRITIC 工作流改造

### AUTHOR

逐页写作时同步完成：

1. 选择模块 claim refs；
2. 选择每个明细的 source refs；
3. 声明明细与模块结论的关系；
4. 选择 direct、synthesis 或 relation；
5. 使用绑定事实的保护信息完成文案；
6. 不创建单独状态文件。

### CRITIC

Critic 按 provenance 回读最小证据范围，检查：

- 引用事实是否真正支持作者结论；
- synthesis 是否建立了来源允许的关系；
- 事实角色是否被改变；
- 现状、目标、建议、责任、条件是否失真；
- 页面之间是否重复使用同一事实而没有新论证角色。

Critic 发现问题后直接重写 Final Script，同步修订 provenance。

### 确定性检查

只在 AUTHOR/Critic 完成后运行，负责验证契约、引用、兼容矩阵、保护信息和交付
同步。它不承担生成式业务判断。

## 10. 实施阶段

### Phase 0：基线和冻结

预计 1 个开发批次。

- 冻结新增全局语义关键词规则；
- 为现有规则生成 registry inventory；
- 建立 8—12 个跨领域历史项目基线；
- 记录各入口当前 issues/warnings，形成差分基线。

退出条件：能够列出每个阻断规则的来源、调用入口和历史命中。

### Phase 1：Final Script 1.1 与 provenance

预计 2—3 个开发批次。

修改：

- `contracts/final-script.schema.json`
- `script_engine/render.py`
- `script_engine/contracts.py`
- `.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`
- `script_engine/cli.py`

新增：

- `script_engine/semantic_contract/models.py`
- `script_engine/semantic_contract/foundation_index.py`
- `script_engine/semantic_contract/provenance.py`
- provenance 单元测试和 JSON/Markdown round-trip 测试。

本阶段直接复用轻量 Foundation 的 `semantic_units`、argument nodes/relations 和
strict/legacy Foundation 的 typed fields，不增加新的源材料解析步骤。

退出条件：新项目缺少模块绑定时 audit-final 失败；绑定能够在 JSON 与 Markdown
之间无损同步；Stage 02 锁定文字不包含 provenance 文本。

### Phase 2：结构化兼容审计

预计 2 个开发批次。

新增 compatibility、protected payload 和统一 diagnostics；把 Final Script 审计
接入单一 semantic contract auditor。

退出条件：用户指出的 P04 错误通过角色不兼容被阻断，改写同义词不改变结果；
合法的“既有能力支持拟议责任主体”能够通过。

### Phase 3：启发式规则隔离

预计 2 个开发批次。

- 删除项目专用全局规则；
- 将语义词表阻断降为 warning；
- 建立 rule registry 与 CI；
- 清理 AUTHOR 合同中的具体项目事实。

退出条件：默认规则中没有客户、行业和项目专名；所有 blocking 规则均可追溯到
Schema、结构关系或明确交付政策。

### Phase 4：新旧审计收敛

预计 2—4 个开发批次。

- `script_engine` 成为唯一语义审计内核；
- `cyberppt.script_quality` 逐步改为适配器；
- legacy 输入投影到统一模型；
- 删除重复实现和漂移测试。

退出条件：同一输入通过所有正式入口得到相同 blocking 结果。

### Phase 5：跨项目回归与默认启用

预计 1—2 个开发批次。

- 对跨领域项目运行差分；
- 统计 false positive、false negative 和 bypass；
- 新项目默认 Final Script 1.1；
- 旧项目保持只读兼容，并提供显式迁移命令。

退出条件：达到第 12 节质量门槛后切换默认路径。

## 11. 测试体系

### 11.1 契约测试

- 未知 ref、越界 ref、重复 ID、缺失 binding；
- direct/synthesis/relation 基数约束；
- JSON/Markdown round trip；
- Stage 02 锁定文本隔离。

### 11.2 角色兼容测试

- premise/support/detail 支撑现状结论；
- response/recommendation 落实目标或建议；
- boundary/constraint 收窄结论；
- 跨状态、跨主体和跨责任的非法绑定；
- 正向与反向关系分别覆盖。

### 11.3 变形测试

同一结构化绑定生成多种同义表达，blocking 结果必须一致。测试至少覆盖：

- 主动/被动语态；
- 同义动词替换；
- 调整语序；
- 省略可合法继承的共同主语；
- 改变标点和分行；
- 中文、英文和混合术语。

### 11.4 跨领域测试

测试集至少包括政策方案、标准体系、产品规划、教育培训、企业经营、技术架构、
科研汇报和合同类材料。通用规则不得包含这些测试项目的专名。

### 11.5 历史问题测试

历史事故只保存为 benchmark 输入和期望结构结果，不把事故原句直接加入全局
禁用词表。

## 12. 发布门槛

默认启用前必须同时满足：

1. 新项目模块 provenance 覆盖率 100%；
2. 所有 visible heading/text/item 均能追溯到 Foundation ref；
3. blocking 语义问题全部引用具体 claim/evidence/relationship ID；
4. 同义改写测试的 blocking 结果一致率 100%；
5. 跨领域合法反例误杀率为 0；
6. 历史高风险案例召回率 100%；
7. 新旧正式入口 blocking 结果一致率 100%；
8. 默认规则中项目专名数量为 0；
9. `check-sync`、audit-final、Stage 02 handoff 和文本锁定测试全部通过；
10. 人工抽检确认完整文字稿没有因 provenance 改造发生内容压缩。

## 13. 风险与控制

| 风险 | 控制措施 |
|---|---|
| AUTHOR 填写错误 provenance | Critic 回读绑定来源；代码检查引用和角色兼容 |
| 元数据增加写作负担 | 使用稳定 module/item ID 和简洁 binding；不重复填写 Foundation 状态 |
| Markdown 审核稿变重 | 映射集中放在每页末尾，不进入上屏和讲稿 |
| 历史项目无法自动迁移 | 允许 1.0 只读；迁移仅生成骨架，关系由 AUTHOR 复核 |
| 结构化字段仍不能证明语义充分 | 保留 Critic 和人工复核；代码输出 review_required |
| 两套审计长期并存 | 为 legacy 设定删除里程碑，新功能只进入统一内核 |

## 14. 明确不采用的方案

### 继续扩充关键词表

同义表达可以绕过，合法表达也会误中，无法建立可证明的模块级证据关系。

### 将完整 AUTHOR 合同重新塞回 Deck Plan

这会破坏 v2 lean 的职责边界，使 PLAN 提前承担文案和模块设计，恢复旧链路的
重复理解与预写作问题。

### 新建第四个项目级语义产物

会增加状态同步、审批绑定和事实源漂移。模块 provenance 应进入 Final Script，
保持三个权威内容产物。

### 完全删除所有正则

格式、安全、元数据泄漏、明确禁用句式和 ID 协议适合确定性处理。需要删除的是
正则对业务语义的最终裁决权。

## 15. 建议首个开发切片

首个切片控制在以下范围：

1. Final Script 1.1 schema；
2. 复用现有 Foundation typed semantics 的只读索引；
3. module/item stable IDs；
4. provenance 的 ref/target/boundary 校验；
5. Markdown 模块证据映射和 `check-sync`；
6. P04 错误与合法反向案例；
7. 不改动 Stage 02 可见文本消费方式；
8. 暂不删除旧规则，仅将相关语义词表结果标记为 legacy warning。

该切片完成后，系统首次具备通用模块级可追溯基础。后续 compatibility matrix
和规则清理可以在可验证的数据契约上继续推进。

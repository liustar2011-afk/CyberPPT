# Stage 01 来源消费与脚本忠实度修复开发计划

## 1. 文档状态

- 日期：2026-08-28
- 状态：已完成（代码与定向回归通过；全套测试的3项环境/既有失败已记录）
- 适用仓库：`D:\CyberPPT`
- 适用范围：正式 Stage 01 `Source Truth → project-foundation → Deck Plan → AUTHOR → Final Script` 路线
- 诊断样本：`projects/power-data-infrastructure-standard-system-research-20260828-001`

## 2. 结论摘要

当前 Source Truth 已保留完整来源事实、语义单元、来源特征锚点、状态和原文定位。正式脚本路线在后续两处失去约束：

1. `project-foundation` 只在 fact item 上投影 `statement`、`source_refs`、`strength` 和少量角色字段，没有继续携带 `semantic_units`、`coverage_anchors`、`conditions`、`source_locator` 等来源忠实度字段。`actors` 和 `numeric_facts` 会分别转成顶层 `entities`、`numbers`，但 fact item 与这些独立对象之间缺少显式绑定。
2. Deck Plan 的 `source_consumption` 被定义为可选合同；PLAN 和 AUTHOR 审计在合同缺失时直接返回空结果。

结果是：页面拥有合法 `source_refs`，完整文字稿和上屏文字仍可把具体来源事实压缩成抽象标签，并且 `audit-plan`、`audit-final` 均可能报告零问题。

本计划在现有 `script_engine` 内修复该问题：保留来源特征、为正式 Source Truth 投影项目启用编译器控制的严格来源消费策略、让 PLAN 和 AUTHOR 在缺少消费合同时失败关闭，并继续允许完整稿与上屏层采用不同的信息密度。

## 3. 已验证事实与提交归因

### 3.1 当前代码与远端状态

- 本地 `main` 与 `origin/main` 一致，ahead/behind 均为 0。
- 当前项目产物生成于 2026-08-28 09:04—09:58，晚于本计划涉及的相关提交。
- 当前项目确实使用了 `0e79b6d` 新增的 `comprehension-brief.json` 和三类关系 `basis`。
- 当前项目关系图包含 14 条 `source`、1 条 `inferred`、0 条 `external`，未引入外部关系。

### 3.2 提交归因

| 提交 | 作用 | 归因判断 |
| --- | --- | --- |
| `0e79b6d` | 允许领域知识和联网核验；增加 `comprehension-brief.json`；在投影边界映射关系 `basis` | 与当前来源消费故障无直接因果 |
| `4a728f6` | 增加状态、语义角色和表格上下文投影；加强语义审阅 | 属于部分补强，未继续投影来源锚点 |
| `ac23549` | 引入 `source_consumption`、完整稿锚点和上屏来源选择 | 将合同定义为可选，并增加缺合同继续放行的兼容测试，是当前静默放行的直接贡献提交 |
| `818dff0` | 8月26日基础快照 | `project-foundation` 丢失来源特征字段的行为已经存在 |
| `2adc208` | 后续模块化与兼容整合 | 原样保留缺合同返回空结果的行为 |

### 3.3 当前可复现行为

- 当前项目25个计划页均有 `source_refs`。
- 25页均没有 `source_consumption`。
- `audit_deck_plan`：0 issues，0 warnings。
- `audit_final_script`：0 issues，0 warnings。
- `tests/test_source_consumption.py` 当前为9项通过，其中一项明确要求“缺少 `source_consumption` 且完整稿完全无关”仍然不报告来源消费错误。

### 3.4 可核查代码证据

| 断言 | 代码证据 |
| --- | --- |
| fact item 未携带 `semantic_units`、`coverage_anchors`、`conditions`、`source_locator` | [`cyberppt/foundation_projection.py:51-125`](../../cyberppt/foundation_projection.py#L51-L125) |
| `actors`、`numeric_facts` 被转成顶层 `entities`、`numbers` | [`cyberppt/foundation_projection.py:102-123`](../../cyberppt/foundation_projection.py#L102-L123) |
| `source_consumption` 已有 Schema，但页面未强制要求该字段 | [`contracts/deck-plan.schema.json:158-207`](../../contracts/deck-plan.schema.json#L158-L207) |
| PLAN 合同缺失时直接返回空问题 | [`script_engine/analysis_audits/common.py:402-410`](../../script_engine/analysis_audits/common.py#L402-L410) |
| AUTHOR 合同缺失或模式不严格时直接返回空问题 | [`script_engine/analysis_audits/final_script.py:205-211`](../../script_engine/analysis_audits/final_script.py#L205-L211) |
| 回归测试要求无关完整稿继续兼容 | [`tests/test_source_consumption.py:93-97`](../../tests/test_source_consumption.py#L93-L97) |
| 结构页常量使用 `cover/contents/chapter/closing` | [`cyberppt/content_route.py:29-71`](../../cyberppt/content_route.py#L29-L71) |
| 旧编译器生成 `cover/agenda/chapter/ending` | [`cyberppt/stage01_compiler.py:1167-1185`](../../cyberppt/stage01_compiler.py#L1167-L1185)、[`cyberppt/stage01_compiler.py:1389-1395`](../../cyberppt/stage01_compiler.py#L1389-L1395) |

开发提交必须先增加能够复现上述行为的失败测试，再修改生产代码。测试名、输入和期望 Issue code 应写清楚，避免仅依赖文档断言。

## 4. 开发目标

### 4.1 必须实现

1. 正式 Source Truth 投影后的 Foundation 保留后续忠实度检查所需的来源字段。
2. 新正式源驱动项目自动进入严格来源消费模式，不能依赖 PLAN 作者主动记得添加模式字段。
3. 严格模式下，带来源的内容页缺少 `source_consumption` 时阻断 AUTHOR。
4. 每条分配给完整稿的来源记录都必须保留来源特征，或在 PLAN 中记录具体删减理由。
5. 上屏只消费 PLAN 选定的代表性来源，不要求所有完整稿事实都进入可见层。
6. 数字、日期、条件、责任主体、状态、分类层级和明确业务对象受到专门保护。
7. 历史 Foundation 在没有严格策略标记时保持兼容。
8. 三个权威内容产物继续保持：`foundation.json`、`deck-plan.json`、`dist/final-script.md`。

### 4.2 不在本次范围

- 不恢复旧 Outline 路线作为新的权威写作入口。
- 不把旧 `content_units` 合同整体复制到 `script_engine`。
- 不新增确认文件、审批回执、attempt、ledger、哈希门或平行运行目录。
- 不强制每条来源记录对应一个上屏模块。
- 不通过固定字数、固定模块数或每页来源数量判断忠实度。
- 不自动改写当前项目的 Deck Plan 或 Final Script。
- 不进入 Stage 02，不处理图片、SVG 或 PPTX。

## 5. 技术方案

### 5.1 目标数据流

```text
source-truth.json
  ├─ statement / semantic_units / coverage_anchors
  ├─ conditions / numeric_facts / status / priority
  └─ source_locator / claim_origin
          │ project-foundation：机械投影
          ▼
foundation.json
  ├─ 完整来源特征
  └─ source_consumption_policy: required
          │ PLAN：页面分配与编辑选择
          ▼
deck-plan.json
  └─ source_consumption
       ├─ detail_refs
       ├─ intentional_omissions
       ├─ full_prose_anchors
       └─ onscreen_refs
          │ AUTHOR：完整论证与可见层压缩
          ▼
final-script.md / final-script.json
  ├─ full_copy：消费全部应保留来源
  └─ onscreen：消费选定代表来源
```

### 5.2 Foundation 严格策略

由 `project-foundation` 在 Source Truth 机械投影时写入：

```json
{
  "source_consumption_policy": "required"
}
```

策略规则：

- `required`：带来源的内容页必须声明并兑现严格来源消费合同。
- 字段缺失：视为历史 Foundation，沿用 `legacy_optional` 行为。
- Deck Plan 无权把 Foundation 的 `required` 降级。
- 该字段属于 `foundation.json` 内部合同，不形成新的权威产物。

选择 Foundation 作为策略承载位置的理由：

- Foundation 由正式投影器生成，能够可靠区分新正式项目与历史手工数据。
- PLAN 作者遗漏字段时，审计仍能根据 Foundation 策略阻断。
- 历史产物无需批量迁移。

### 5.3 Foundation 字段投影

修改 `cyberppt/foundation_projection.py::_project_facts_and_constraints`，在现有字段之外机械复制：

- `atomic_item_id`
- `claim_origin`
- `semantic_units`
- `coverage_anchors`
- `conditions`
- `source_locator`
- `allowed_page_roles`
- `forbidden_page_roles`

`actors` 和 `numeric_facts` 继续以顶层 `entities`、`numbers` 作为唯一规范化表示，不在 fact item 中复制第二份完整对象。新增显式绑定：

- fact item 增加 `entity_refs` 和 `number_refs`；
- entity 增加 `fact_refs`，支持同一主体关联多条事实；
- number 增加 `fact_ref`，明确数字所属来源记录；
- 绑定使用生成后的稳定 ID，禁止依赖 `STxxxx-Nn` 字符串前缀反推关系。

该方案保留现有独立集合消费者，同时恢复“某条事实关联哪些主体和数字”的可审计关系，避免原始字段与规范化字段形成双重语义。

投影要求：

- 只复制 Source Truth 已存在字段。
- 不在投影器中生成新事实、推断新关系或重新拆分原文。
- 数组和对象使用结构复制，避免下游修改污染上游载荷。
- `constraints` 与普通 `facts` 保持相同的来源特征保留能力。
- `entities`、`numbers` 现有独立投影继续保留；新增交叉引用测试验证 fact 与独立对象双向一致。
- 复杂嵌套字段使用深度结构相等断言，禁止只检查 key 存在、数组长度或第一层值。

### 5.4 严格页面判定

在新增来源消费判定前，先完成页面角色词汇核对。当前仓库存在两套实际值：

- `cyberppt/content_route.py`：`cover`、`contents`、`chapter`、`closing`；
- `cyberppt/stage01_compiler.py`：`cover`、`agenda`、`chapter`、`ending`。

旧编译器当前生成的结构页没有 `source_refs`，因此不会立即满足严格判定的全部条件；该反例说明当前诊断项目不会因角色差异直接失败。角色分类仍需在提交2前修复，因为其他生产者可能给结构页保留来源引用，且 `is_structural_page()` 本身会漏认 `agenda/ending`。

前置任务：

1. 盘点所有正式生产者和消费者使用的页面角色值；
2. 在现有页面角色归一化位置建立别名映射：`agenda → contents`、`ending → closing`；
3. 保留 `cover`、`chapter`、`content` 的现有含义；
4. 让 `is_structural_page()` 同时识别两套输入值；
5. 为两套词汇增加参数化测试；
6. 禁止在来源消费模块内部再维护一份结构页集合。

随后新增单一公共判定函数，避免 PLAN 和 AUTHOR 各自维护不同条件：

```python
def requires_source_consumption(
    page: dict[str, Any],
    foundation: dict[str, Any],
) -> bool:
    ...
```

返回 `True` 的条件：

1. `foundation.source_consumption_policy == "required"`；
2. `page.source_refs` 非空；
3. 页面属于内容页。

归一化后的结构页豁免范围：

- `cover`
- `contents`（含输入别名 `agenda`）
- `section`
- `chapter`
- `closing`（含输入别名 `ending`）
- 其他仓库已注册的纯结构角色

`section` 是否为正式页面角色必须在词汇盘点中确认；若仅表示来源结构层级，不得直接加入页面角色集合。结构页判定应复用修复后的现有常量和归一化函数。

### 5.5 Deck Plan 来源消费合同

严格内容页必须声明：

```json
{
  "source_consumption": {
    "mode": "strict",
    "detail_refs": [],
    "intentional_omissions": [],
    "full_prose_anchors": [
      {
        "source_ref": "ST0035",
        "anchors": [
          "2026年7月1日起施行",
          "一般、重要、核心三级分类分级"
        ],
        "minimum_hits": 2
      }
    ],
    "onscreen_refs": ["ST0035"]
  }
}
```

消费集合定义：

```text
完整稿必消费来源
= page.source_refs
- detail_refs
- intentional_omissions.source_refs
```

合同要求：

1. 每条完整稿必消费来源至少有一组 `full_prose_anchors`。
2. 锚点必须来源于该记录的 `statement`、`semantic_units` 或 `coverage_anchors`。
3. 包含数字、日期、条件、职责、状态、分类层级或明确业务对象的记录，应保护相应来源特征。
4. `detail_refs` 只用于结构信息、索引、附件字段和追溯详情。
5. `intentional_omissions` 必须写明具体编辑理由，不能使用“后续再说”“不重要”等泛化说明。
6. `onscreen_refs` 是完整稿必消费来源的代表性子集。
7. `onscreen_refs` 必须映射到 `onscreen_contract.modules[].evidence_refs`。
8. 严格内容页至少选择一条代表性来源进入可见层。
9. 同一引用不能同时出现在 `detail_refs`、`intentional_omissions`、`onscreen_refs` 或互斥锚点类别中。

### 5.6 锚点生成与选择职责

职责分为两层：

#### 编译器职责

- 把 Source Truth 的 `coverage_anchors`、`semantic_units`、数字、条件和状态继续投影到 Foundation。
- 提供可供 PLAN 选择的来源特征。
- 不自动决定某条事实是否应该进入某一页。

#### PLAN 职责

- 根据页面问题、页面使命和来源职责选择完整稿锚点。
- 选择能区分该记录与抽象主题标签的短来源特征。
- 对长记录选择1—3个关键特征，覆盖对象、动作、条件、数字或责任关系。
- 对薄来源记录允许只选择一个锚点。
- 对确实只保留追溯的记录使用 `detail_refs`。
- 对明确不使用的记录使用带具体理由的 `intentional_omissions`。

这种分工可以防止投影器重新解释来源，也能防止 AUTHOR 仅凭宽松重叠阈值证明消费完成。

### 5.7 PLAN 审计改造

涉及：

- `script_engine/analysis_audits/common.py`
- `script_engine/analysis_audits/deck_plan.py`
- `contracts/deck-plan.schema.json`
- `script_engine/plan_review.py`

新增或调整检查：

| Issue code | 触发条件 |
| --- | --- |
| `SOURCE_CONSUMPTION_CONTRACT_MISSING` | 严格内容页缺少 `source_consumption` |
| `SOURCE_CONSUMPTION_MODE_INVALID` | 合同模式不是 `strict` |
| `SOURCE_CONSUMPTION_ANCHOR_MISSING` | 完整稿必消费来源没有锚点合同 |
| `SOURCE_CONSUMPTION_ANCHOR_NOT_SOURCE_GROUNDED` | 锚点无法在对应 Foundation 来源表面中找到 |
| `SOURCE_CONSUMPTION_REF_OUTSIDE_PAGE` | 合同引用不属于 `page.source_refs` |
| `SOURCE_CONSUMPTION_REF_CONFLICT` | 同一引用进入互斥类别 |
| `SOURCE_CONSUMPTION_OMISSION_REASON_MISSING` | 删减缺少具体理由 |
| `SOURCE_CONSUMPTION_ONSCREEN_SELECTION_MISSING` | 严格内容页没有选择代表性上屏来源 |
| `SOURCE_CONSUMPTION_ONSCREEN_MAPPING_MISSING` | 上屏引用没有映射到模块证据 |

`plan_review.py` 的人工审阅稿增加每页来源消费摘要：

- 完整稿必消费来源；
- 追溯详情；
- 明确删减及理由；
- 必须上屏的代表性来源；
- 每条来源的保护锚点。

人工审阅稿只读取 `deck-plan.json`，不生成新的内容权威或确认文件。

### 5.8 AUTHOR 审计改造

涉及：

- `script_engine/analysis_audits/final_script.py`
- `script_engine/analysis_audits/common.py`

调整 `_audit_authored_source_consumption`：

1. 先调用统一的严格页面判定。
2. 严格页面缺合同立即报告阻塞问题。
3. 对完整稿必消费来源逐条验证锚点命中数。
4. 对历史 Foundation 保留现有语义重叠兼容路径。
5. 对严格 Foundation 禁止使用低阈值重叠作为唯一证明。
6. 对数字、日期、条件、责任、状态和分类层级增加专门检查。
7. 对 `onscreen_refs` 验证模块存在、证据映射存在、`required_signals` 实际可见。
8. 完整稿中的其他来源可以保留在讲述层，无须全部复制到上屏。

建议 Issue codes：

| Issue code | 触发条件 |
| --- | --- |
| `FULL_COPY_SOURCE_REF_MISSING` | 应消费来源的具体内容没有进入完整稿 |
| `FULL_COPY_SOURCE_ANCHOR_MISSING` | 锚点命中数不足 |
| `FULL_COPY_NUMBER_OR_DATE_LOST` | 受保护数字或日期消失 |
| `FULL_COPY_CONDITION_LOST` | 来源条件消失或被改成无条件结论 |
| `FULL_COPY_RESPONSIBILITY_LOST` | 责任主体、动作或对象消失 |
| `FULL_COPY_STATUS_STRENGTH_LOST` | 试行、规划、建议、现状等状态被提升或删除 |
| `ONSCREEN_SOURCE_REF_MISSING` | 选定代表来源未进入可见层 |
| `ONSCREEN_REQUIRED_SIGNAL_MISSING` | 模块缺少 PLAN 声明的可见特征 |

## 6. 文件级开发清单

### 6.1 核心代码与合同

| 文件 | 计划改动 |
| --- | --- |
| `cyberppt/foundation_projection.py` | 保留来源忠实度字段；写入严格策略 |
| `cyberppt/content_route.py` | 统一结构页输入别名；让公共结构页判定覆盖两套现有词汇 |
| `cyberppt/cli.py` | 在 `project-foundation --help` 中说明严格模式触发；覆盖历史 Foundation 前输出非交互警告 |
| `contracts/foundation.schema.json` | 声明 `source_consumption_policy` 和新增来源字段 |
| `contracts/deck-plan.schema.json` | 收紧严格合同字段结构；保持历史载荷可解析 |
| `script_engine/analysis_audits/common.py` | 增加统一严格页面判定、来源表面和合同检查 |
| `script_engine/analysis_audits/deck_plan.py` | 在 PLAN Gate 强制严格来源消费 |
| `script_engine/analysis_audits/final_script.py` | 在 AUTHOR Gate 验证完整稿与上屏实际消费 |
| `script_engine/plan_review.py` | 在可读审阅稿中展示消费选择和锚点 |

### 6.2 Skills 与文档

| 文件 | 计划改动 |
| --- | --- |
| `.agents/skills/cyberppt-script-plan/SKILL.md` | 将正式源驱动内容页的消费合同改为必需；明确完整稿和上屏层职责 |
| `.agents/skills/cyberppt-script-author/SKILL.md` | 明确严格合同继承、完整稿消费和代表性上屏规则 |
| `docs/CYBERPPT_WORKFLOW.md` | 补充正式路线中的来源消费门禁和历史兼容边界 |

### 6.3 测试

| 文件 | 计划改动 |
| --- | --- |
| `tests/test_foundation_projection.py` | 验证来源字段和严格策略完整投影 |
| `tests/test_content_route.py` | 参数化验证两套结构页词汇及归一化结果 |
| `tests/test_cli.py` | 验证 CLI 帮助和历史 Foundation 覆盖警告 |
| `tests/test_source_consumption.py` | 重写兼容测试；增加严格 Foundation 缺合同失败用例 |
| `tests/script_engine/test_semantic_guardrails.py` | 增加数字、条件、状态和分类语义保留测试 |
| `tests/script_engine/test_plan_review_and_internal_voice.py` | 验证人工 Review 展示消费摘要 |
| `tests/script_engine/test_v04_source_fidelity.py` | 增加正式路线端到端来源消费回归 |

若测试夹具已经足够表达真实故障，不新增项目目录型测试数据；优先使用最小内存载荷。

## 7. 测试矩阵

### 7.1 Foundation 投影

1. `semantic_units`、`coverage_anchors`、`conditions`、`source_locator` 被完整复制。
2. 空字段保持空数组或缺省约定，不生成伪造值。
3. Source Truth 投影 Foundation 自动写入 `source_consumption_policy: required`。
4. 手工 Foundation 缺少该策略时仍可通过历史 Schema。
5. constraint 类型记录同样保留来源特征。
6. `actors`、`numeric_facts` 继续规范化为 `entities`、`numbers`，fact 与独立对象之间具有可验证的双向引用。
7. 嵌套数组和对象使用完整 `==` 深度结构比较；测试应在第二层对象中放置至少两个字段，确保浅层检查无法误通过。

### 7.2 页面角色归一化

1. `cover`、`contents`、`chapter`、`closing` 被识别为结构页。
2. `agenda` 被归一化为 `contents`。
3. `ending` 被归一化为 `closing`。
4. `content` 不得被识别为结构页。
5. 结构页没有 `source_refs` 时不要求来源消费合同。
6. 结构页保留 `source_refs` 时仍不要求内容页消费合同。
7. PLAN 与 AUTHOR 使用同一个结构页判定结果。

### 7.3 PLAN Gate

1. 严格内容页有 `source_refs` 且缺合同：失败。
2. 严格结构页：豁免。
3. 历史 Foundation 缺策略且页面缺合同：继续兼容。
4. 锚点引用未知来源：失败。
5. 锚点内容不属于对应来源：失败。
6. 同一引用同时被标为详情和删减：失败。
7. 删减理由过短或泛化：失败。
8. 上屏代表来源没有模块映射：失败。
9. 八条完整稿来源只选择两条上屏：通过。

### 7.4 AUTHOR Gate

1. 完整稿与来源完全无关：严格模式失败。
2. 仅出现抽象主题词、没有来源特征：失败。
3. 来源日期被删除：失败。
4. 一般、重要、核心三级分类被压缩成“分类分级”：失败。
5. 安全责任、风险监测、应急处置被压缩成“安全管理”：失败。
6. 可信数据空间建设、场景验证、标准验证、生态培育被压缩成“可信流通”：失败。
7. PLAN 明确列入 `detail_refs` 的追溯详情未进入完整稿：通过。
8. PLAN 有具体删减理由的记录未进入完整稿：通过。
9. 完整稿消费全部来源，上屏只消费代表子集：通过。
10. 薄来源记录命中一个有效锚点：通过。

### 7.5 真实问题回归

以当前P01的来源结构构造最小测试载荷：

- ST0034：绿色低碳具体应用要求；
- ST0035：2026年7月1日、三级分类分级；
- ST0036：安全责任、风险监测、应急处置；
- ST0037：可信数据空间建设、场景验证、标准验证、生态培育。

当前压缩稿应报告相应缺口；恢复来源特征后的版本应通过。

## 8. 验证命令

所有 Python 命令使用仓库虚拟环境：

```powershell
$env:PYTHONPATH=(Get-Location).Path

.venv\Scripts\python.exe -m pytest `
  tests/test_foundation_projection.py `
  tests/test_source_consumption.py `
  tests/script_engine/test_semantic_guardrails.py `
  tests/script_engine/test_plan_review_and_internal_voice.py `
  tests/script_engine/test_v04_source_fidelity.py
```

定向测试通过后运行：

```powershell
$env:PYTHONPATH=(Get-Location).Path
.venv\Scripts\python.exe -m pytest
git diff --check
```

若全套测试存在既有失败，必须记录失败测试、基线状态和与本次修改的关系；禁止修改无关代码掩盖既有失败。

## 9. 开发与提交顺序

### 提交1：Foundation 投影合同

- 修改 Foundation 投影和 Schema。
- 增加字段复制、结构复制、严格策略测试。
- 不修改 PLAN/AUTHOR 行为。

### 提交2：PLAN 严格来源消费门禁

- 增加统一严格页面判定。
- 严格内容页缺合同失败。
- 增加锚点来源合法性、引用冲突、删减理由和上屏映射检查。
- 更新 `plan_review.py`。

### 提交3：AUTHOR 完整稿与上屏消费门禁

- 严格模式采用锚点和受保护特征检查。
- 历史模式保留现有兼容路径。
- 增加P01型回归测试。

### 提交4：Skills、工作流与完整回归

- 更新 PLAN/AUTHOR Skills 和主流程文档。
- 运行定向测试与全套测试。
- 检查新规则没有把所有来源机械推到上屏。

每次提交仅暂存本计划对应代码、合同、测试和文档；不暂存项目生成产物或无关工作区内容。

## 10. 兼容与迁移策略

### 10.1 历史项目

- 历史 `foundation.json` 没有 `source_consumption_policy` 时保持 `legacy_optional`。
- 不批量改写历史 Deck Plan。
- 历史项目再次执行 `project-foundation` 后将进入严格模式，此时必须重新通过 PLAN Gate。
- “重新执行 `project-foundation` 会单向进入严格模式”必须写入 CLI 帮助、工作流文档和迁移说明。
- 当目标文件已存在、且现有 Foundation 没有严格策略字段时，CLI 在覆盖前向 stderr 输出非交互警告，明确说明新文件将进入严格模式并要求重新通过 PLAN Gate；命令保持可脚本化，不增加交互确认。
- 不提供自动降级命令。确需保留历史行为时，应继续使用未重新投影的历史 Foundation，或由用户明确决定迁移。

### 10.2 新项目

- 正式 `project-foundation` 自动写入严格策略。
- PLAN 必须在用户确认前完成每个源驱动内容页的来源消费合同。
- AUTHOR 只消费已经确认的 Deck Plan。

### 10.3 当前诊断项目

代码修复合入后，当前项目需要按以下顺序单独处理：

1. 使用正式 `project-foundation` 重新投影当前 Source Truth；
2. 在现有 `deck-plan.json` 中补充来源消费合同；
3. 运行 `audit-plan` 并展示更新后的 Plan Review；
4. 在现有规划确认节点等待用户确认；
5. 收到确认后再重新 AUTHOR；
6. 运行 `audit-final`，逐页修复来源消费缺口。

该迁移步骤属于代码修复完成后的项目修复任务，本开发计划不自动执行。

## 11. 风险与控制

| 风险 | 控制措施 |
| --- | --- |
| 锚点过长导致照抄原文 | PLAN 选择1—3个短来源特征；完整稿允许自然组织 |
| 锚点过短导致主题词即可通过 | 检查锚点的来源专属性；保护数字、条件、责任和状态 |
| 所有来源被机械推上屏 | `onscreen_refs` 保持代表性子集；完整稿和上屏分别审计 |
| 结构页被误判为内容页 | 复用现有结构角色常量并建立豁免测试 |
| 历史项目突然失败 | Foundation 缺策略时继续兼容 |
| 历史项目无意重投影后进入严格模式 | CLI帮助和工作流明确提示单向触发条件；迁移前先运行只读审计 |
| 两套结构页词汇导致分类漂移 | 在现有公共归一化位置建立别名映射；PLAN/AUTHOR共享同一判定 |
| fact 与 `entities/numbers` 出现双重数据源 | 顶层独立集合保持规范表示；fact只保存引用；增加双向一致性测试 |
| PLAN 用 `detail_refs` 逃避消费 | 限定其适用语义；在 Review 中公开展示；增加滥用测试 |
| PLAN 用泛化删减理由逃避消费 | 拦截短理由和通用占位语；要求具体页面职责解释 |
| Foundation 投影重新解释来源 | 仅复制已有字段；投影测试验证值完全一致 |
| 审计误报影响正常专业改写 | 锚点与语义重叠组合验证；真实改写正反例成对测试 |

## 12. 验收标准

全部满足后方可完成开发：

1. 新正式 Foundation 自动启用严格来源消费策略。
2. 严格内容页缺合同会在 PLAN Gate 阻断。
3. 严格内容页缺合同会在 Final Audit 再次阻断。
4. 当前P01型压缩稿能够稳定报告 ST0034—ST0037 的具体来源缺口。
5. 恢复具体来源特征后的专业改写能够通过。
6. 完整稿可以消费多条来源，上屏只选择代表性子集。
7. 结构页、追溯详情、明确删减和薄来源页面均有通过用例。
8. 历史 Foundation 缺策略时保持兼容。
9. 历史项目重新执行 `project-foundation` 的单向严格模式触发条件已写入 CLI 帮助、工作流和迁移说明。
10. `agenda/contents`、`ending/closing` 两套结构页词汇均通过参数化测试，PLAN 与 AUTHOR 判定一致。
11. fact 与 `entities/numbers` 的引用关系完整，复杂来源字段通过深度结构相等测试。
12. 定向测试全部通过。
13. 全套测试未新增与本次修改有关的失败。
14. `git diff --check` 通过。
15. 未新增第四个权威产物、平行流程或人工确认文件。

## 13. 实施判断

`SUPPORT WITH CONDITIONS`：复用并收紧现有 `source_consumption` 合同，同时从旧 `content_units` 能力中吸收原子来源覆盖思想。实施条件包括编译器控制的严格模式、历史兼容边界、完整稿与上屏分层消费，以及真实项目回归证据。整体迁移旧 Outline 权威路线不在采用范围。

## 14. 实施结果

### 14.1 已落地

- Foundation 投影保留来源忠实度字段，并写入 `source_consumption_policy: required`。
- fact 与顶层 `entities`、`numbers` 建立稳定双向/所属引用，顶层集合继续作为规范化表示。
- `agenda → contents`、`ending → closing` 已进入公共页面角色归一化，PLAN 与 AUTHOR 共享同一结构页判定。
- 严格内容页在 PLAN 缺合同、缺锚点、锚点无来源依据、删减理由无效、上屏选择缺失或映射缺失时失败关闭。
- AUTHOR 逐条验证完整稿锚点，并检查数字/日期、条件、责任主体、状态以及代表性上屏来源。
- 历史 Foundation 缺少策略字段时继续走原有兼容路径。
- `review-plan` 展示完整稿必消费来源、追溯详情、明确删减、代表性上屏来源和保护锚点。
- `project-foundation --help` 与覆盖旧 Foundation 时的 stderr 警告均说明单向严格模式迁移。
- PLAN/AUTHOR Skills 和主流程文档已同步更新。

### 14.2 验证结果

- 计划指定的定向回归：`115 passed`。
- 全套测试：`1519 passed, 8 skipped, 3 failed`，总计1530项。
- 3项全套失败均位于本次修改范围之外：
  - `test_imagegen_handoff_modularization.py` 扫描 Skill 私有虚拟环境时遇到第三方文件 BOM；
  - `test_presentation_qa.py` 的 Unix 路径字面值在 Windows 被规范化；
  - `test_source_to_markdown_runtime.py` 因现存 Skill 私有虚拟环境而未进入测试预期的仓库虚拟环境分派。
- `git diff --check` 通过。
- 未重新生成、修改或删除诊断项目目录；未新增第四个权威产物或平行流程。

# CyberPPT Stage 01 页面消费语义改造实施报告

- 日期：2026-08-26
- 技术判断：`SUPPORT WITH CONDITIONS`
- 依据：`stage01-development-plan-20260825.md`
- 重点项目：`projects/ai_power_training_business_feasibility`
- 重点页面：P04

## 一、实施结论

源材料到页面脚本的治理链已经形成统一的事前合同：页面计划负责逐事实消费语义，Handoff 负责确定性投影，preflight 负责写前拓扑门禁，page lint 负责写后合同核对。Source Truth 继续承载事实固有语义，同一事实能够在不同页面拥有不同页面职责。

新 authoring spec 默认使用 required 模式。历史项目保留 legacy 和 advisory 兼容；兼容状态进入正式验证报告，迁移过程可见、可追踪。

## 二、落地链路

```text
table row trace parent + atomic cell children
                 │
                 ▼
normalized facts + relations + argument diagnostics
                 │
                 ▼
authoring spec / page plan evidence_roles v2
                 │
                 ▼
Handoff exact projection
                 │
                 ▼
outline page_consumption + content_units
                 │
         ┌───────┴────────┐
         ▼                ▼
preflight topology     page lint execution check
```

## 三、关键实现

### 页面计划

- 增加 `page_consumption_contract_mode`：`legacy`、`advisory`、`required`。
- 每条直接事实声明 `page_function`、`relation_to_proposition`、`decision_scope`、`visibility`、`topology_role`、`group_id`、可选 `peer_set_id` 和真实顺序 `sequence_index`。
- required 模式检查一次消费、ID 类型、枚举组合、可见分组、offscreen rationale、高密度全 claim 塌缩和排除字段一致性。
- Markdown 人工稿展示页面消费语义。

### Handoff

- required 模式按页面绑定生成 content unit；同一 Source Truth 记录跨页可获得不同用途和可见层。
- `visibility` 确定 content unit priority：主上屏 P0、辅助上屏和完整稿 P1、备注和追溯 P2。
- Source Truth 不再接收 required 页面 importance 的批量提权。
- `excluded_from_onscreen` 保留 source refs、reason 和 target layer。
- authority map 增加 normalized fact 到 content unit 的页面绑定。

### Preflight

- 删除 P04 专属业务分组词表和专属提示句。
- 输出命题、显式主链、卫星、边界、上下文、分组、peer sets、anti-merge edges、可见性预算和 unresolved contracts。
- 主链边仅来自显式正整数 `sequence_index`。
- required 合同缺失时，`prepare-page-script-input` 返回 `PAGE_CONSUMPTION_CONTRACT_INCOMPLETE`。

### Page lint

- `证据映射` 使用 `group_id=模块标题→ST...` 绑定合同分组和可见模块。
- 模块维度检查只比较同一 `peer_set_id`。
- 检查可见 group 缺失、主链顺序冲突和不同决策范围/命题关系的合并冲突。
- 页面状态分为 `passed`、`passed_with_warnings`、`rewrite_required`。

### 源事实原子性

- 表格行保留 `table_record` trace parent。
- 非空单元格生成稳定 `table_cell_statement` 子 ID，后续 parent ID 序列不受影响。
- semantic validator 提示表格管道残留、复合 statement、table parent 引用和诊断 resolution 缺失。

## 四、P04 实际迁移结果

当前项目采用 `advisory`，P04 已完成 v2 消费记录，其余 12 个内容页保留迁移 warning。正式 Handoff 投影和 CyberPPT runtime outline audit 均已通过。

| 事实 | 页面功能 | 决策范围 | 可见层 | 拓扑 |
|---|---|---|---|---|
| NF-0007 轻量投入、快速验证、成熟放大 | action | current | primary_onscreen | main_chain 1 |
| NF-0008 首期验证安排 | action | current | primary_onscreen | main_chain 2 |
| NF-0009 首期投入边界 | operating_boundary | current | supporting_onscreen | boundary |
| NF-0010 首期验证产出 | output | current | primary_onscreen | main_chain 3 |
| NF-0011 0.5—1.7亿元/年 | value_reference | future_reference | supporting_onscreen | satellite |
| NF-0012 付费交付、复制、核算条件 | gate_condition | future_gate | supporting_onscreen | boundary |
| NF-0013 验证性质管理 | operating_boundary | current | prose_only | boundary |
| NF-0014 小规模收入验证商业闭环 | operating_boundary | current | supporting_onscreen | boundary |
| NF-0015 固定平台和大额采购后置 | deferred_constraint | deferred | prose_only | boundary |

P04 preflight 结果：3 个主链节点、1 个卫星节点、5 个边界节点、1 个上下文节点；主链为“验证原则 → 验证安排 → 验证产出”，长期空间、后续研究门槛、当前经营边界和后置约束保持独立拓扑位置。

## 五、验证结果

- 主链定向测试：88 passed。
- 新增/修改的 script-quality 定向用例通过，包括 peer set、主链顺序和 warning 状态。
- 当前项目 semantic validation：`status=ok`，原子性问题以 migration warnings 呈现。
- 当前项目 Outline validation：`status=ok`；P04 v2 完整，其余 12 页报告 advisory warning。
- 当前项目 Handoff：`projection_validation=ok`。
- CyberPPT runtime outline audit：`passed`。
- 全量回归：1257 passed、4 skipped、33 failed。失败集中在既有 Stage 02 prompt/baseline、final-script-pages fixture、script-quality frozen facade 和未修改的两条旧规则断言；本次主链定向测试无新增失败。

## 六、剩余迁移边界

整套项目切换 required 还需要对其余 12 个内容页逐页完成作者判断，主要工作是确定事实用途、决策范围、可见层、分组和同级集合。批量填充会重新引入页面职责猜测，因此当前提交保留 advisory 状态。每页消费记录审核完成后，将 deck brief 和 page plan 同时切换为 required，再运行 Outline validation、Handoff、preflight 和 page lint。

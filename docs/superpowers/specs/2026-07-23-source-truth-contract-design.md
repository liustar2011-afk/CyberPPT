# Source Truth 合同与审计设计

## 目标

将 Source Truth 从分析人员自由编写的 Markdown 摘要升级为可校验、可重建、可双向追溯的结构化证据底稿。流程必须能够发现证据粒度过粗、关键内容遗漏、定位不精确和事实边界混写，并在审计失败后换方向补抽，而不是直接终止任务。

## 适用范围

本次只建设 Stage 01 的 Source Truth 合同、审计、重试记录和 Markdown 渲染能力，并用新能力扩展电力供需预测预警项目。大纲合同继续由现有 `outline-audit` 管理，不在本次重构其页面结构规则。

## 权威数据与产物

`source-truth.json` 是唯一结构化事实源，采用 `cyberppt.source_truth.v1`。`00-source-analysis.md` 是由结构化底稿生成或同步生成的可读视图，不再承担唯一事实源角色。

Stage 01 产物包括：

- `source-truth.json`：证据记录、源材料盘点、覆盖目标和重试状态；
- `source-truth-audit.json`：当前审计结果、问题代码、覆盖统计和下一次补抽方向；
- `source-truth-attempts/attempt-NN.json`：每次输入与审计快照；
- `00-source-analysis.md`：面向人员阅读的 Source Truth Map；
- `source-truth-escalation.json`：达到最大尝试次数后仍存在缺口时的当前最佳结果和人工决策项。

## 证据记录模型

每一条记录只表达一个可以独立核验的事实、判断、建议、边界或待核事项。

证据类型固定为：

- `F`：源材料陈述的事实或数字；
- `J`：源材料给出的解释、判断或问题识别；
- `R`：源材料提出的建议、拟建内容或行动；
- `B`：条件、限制、排除项、阶段边界；
- `U`：材料明确未定、待摸底、待确认或无法核验的事项。

每条记录必须包含：

- `id`：稳定且唯一的 Source ID；
- `type`：上述五类之一；
- `priority`：`P0`、`P1` 或 `P2`；
- `statement`：不改变原意的准确表述；
- `source_locator`：文件、章节和段落或表格定位；
- `status`：已发生、现状、拟建议、阶段判断、待核等受控状态；
- `conditions`：适用条件、口径、限制或排除项数组；
- `supports`：该证据支持的结论 ID；
- `page_refs`：使用该证据的页面 ID；
- `quote`：可核验的原文摘录；
- `fingerprint`：用于核对摘录与源位置的稳定指纹。

数字型记录还必须独立保存原始值、原始单位、期间和口径。一个表格中的不同指标、责任主体、阶段节点和验收项应分别成行，不得以一条概括记录代替整张表。

## 源材料覆盖模型

合同必须登记所有输入文件及其非空段落数、标题数、表格数，并为以下内容设置覆盖目标：

- 标记为 P0/P1 的关键章节；
- 所有表格及其需独立核验的行或单元；
- 所有关键数字、投资档位、周期节点和人员配置；
- 含“拟、建议、待、暂、条件成熟、进一步确认”等状态边界的表述；
- 场景取舍、首期纳入和暂缓内容；
- 数据责任、验收指标、风险、立项条件。

完整性不以 Source ID 数量作为唯一标准。数量只用于识别异常聚合，最终以覆盖目标、精确定位和原子性审计为准。

## 审计规则

审计输出稳定的问题代码，至少覆盖：

- `SOURCE_RECORD_COMPOSITE`：一条记录混合多个独立事实或多种证据类型；
- `SOURCE_LOCATOR_IMPRECISE`：只有章节级位置，缺少段落、表格或表格行；
- `SOURCE_QUOTE_MISSING`：缺少可核验原文摘录；
- `SOURCE_NUMERIC_FIELDS_MISSING`：数字缺少值、单位、期间或口径；
- `SOURCE_TABLE_COVERAGE_MISSING`：登记表格未被逐项覆盖；
- `SOURCE_BOUNDARY_COVERAGE_MISSING`：关键状态边界未登记；
- `SOURCE_PRIORITY_COVERAGE_MISSING`：P0/P1 覆盖目标存在遗漏；
- `SOURCE_TRACEABILITY_BROKEN`：结论或页面引用不能双向解析；
- `SOURCE_TYPE_STATUS_CONFLICT`：事实、建议、边界或待核状态互相冲突。

审计通过必须同时满足结构合法、关键覆盖完整、定位可复核、引用可解析和类型状态一致。

## 失败重试

审计失败时返回非零状态并写入下一次补抽指令，但不把任务标记为放弃。

默认最多三次：

1. `section_sweep`：按章节和标题补齐遗漏；
2. 若相同问题继续出现，切换为 `structured_fact_sweep`，专项扫描数字、表格、状态词、阶段节点、责任主体和验收项；
3. 再失败则切换为 `traceability_rebuild`，从结论和页面反查证据，并输出当前最佳结果。

达到次数上限后状态为 `user_decision_required`，保留当前 Source Truth、剩余缺口和两到三个处理方向；不得删除已有成果或宣告任务失败。

## Markdown 渲染

渲染结果应包含材料定位、结构理解、Source Truth Map、覆盖统计、冲突与待核事项、页面反向追溯和审计结论。表格中的 Source ID、类型、状态、精确位置、准确表述、条件边界及页面引用直接来自 JSON，不在渲染阶段重新解释证据。

## CLI 与项目脚手架

新增命令：

```text
python -m cyberppt source-truth-audit <project> --input <source-truth.json>
```

命令保存审计记录并生成 Markdown。项目初始化时创建 `source-truth-attempts/`，README 明确 Source Truth 审计先于大纲审计。

## 测试策略

使用测试驱动开发，先验证以下失败行为：

- 复合记录、章节级定位和缺失数字字段会被拒绝；
- 表格、P0/P1 和边界覆盖缺口会产生确定的问题代码；
- 引用不存在的结论或页面会被识别；
-连续失败会切换重试方向，第三次失败保留最佳结果并升级人工决策；
- 合法合同通过并生成 Markdown；
- CLI 注册新命令，项目脚手架创建所需目录并写入流程说明。

最后运行 Source Truth 专项测试、CLI/初始化回归测试和完整测试集。

## 非目标

- 不自动编造源材料没有提供的数字、判断或引用；
- 不用 Source ID 数量替代语义完整性；
- 不在本次引入外部数据库或在线服务；
- 不修改 PPT 页面生成、模板重建和视觉生产流程。

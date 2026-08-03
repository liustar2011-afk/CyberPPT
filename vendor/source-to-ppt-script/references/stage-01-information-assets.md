# 阶段1：信息资产

## 输入

- `source/source_blocks.json`
- `source/source_readable.md` 或当前分块文件
- `config/project.yaml`
- Schema：`references/schemas/information_assets.schema.json`
- 分块Schema：`references/schemas/information_assets_chunk.schema.json`

## 目标

建立稳定的中间语义表示。此阶段禁止分页、禁止写PPT标题、禁止构图。

## 提取规则

1. 一个资产只表达一个最小但完整的语义：事实、判断、政策依据、问题、目标、方案、措施、成效、数据、约束、决策事项、责任、案例或定义。
2. 不把互相独立的多个结论塞进同一资产，也不把一句话拆成失去含义的碎片。
3. `content`忠实概括，不复制大段原文。数字、时间、限定条件、否定条件、安全边界和责任主体必须保留。
4. `source_refs`只能使用源索引中存在的编号。多文档编号形如 `D01-S00001`。
5. `evidence`放最有支撑力的原文要点，避免长段摘抄。
6. `priority=core`只用于决定汇报主线不可缺失的信息，数量应克制。
7. `must_retain=true`适用于：项目定位、核心结论、关键数据、政策依据、需决策事项、责任主体、实施路径及安全合规底线。
8. 重复表述合并并保留全部有效来源；存在口径冲突时分别保留并在`notes`说明。
9. `related_asset_ids`只连接确有逻辑关系的资产；不确定时留空。
10. 资产编号最终连续使用 `A001、A002……`。

## 文档画像

`document`应概括整份材料：

- `title`：材料真实主题，不机械抄文件名。
- `purpose`：材料试图完成的沟通或决策任务。
- `audience`：从材料语境和项目配置判断的主要受众。
- `central_judgment`：整份材料最终要成立的一个核心判断。
- `narrative_threads`：主要论证线程，不是章节标题列表。
- `constraints`：安全、合规、资源、时间、口径等边界。
- `source_characteristics`：材料类型、信息密度、重复和结构特征。

## 分块处理

每个分块单独使用从 `A001` 开始的临时编号，并写入 `assets_chunk_NNN.json`。不要在分块阶段判断整份材料的最终标题、受众和中心判断。运行 `prepare-assets-merge` 后，对`combined_assets.json`进行全局去重、重新排序和连续编号。

## 出口条件

- 所有资产都有有效来源。
- core与must_retain信息没有明显遗漏。
- 没有一个资产混入多个独立任务。
- 没有引入源材料之外的事实、结论或能力。

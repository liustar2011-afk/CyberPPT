# 源材料解析与投影复核

## 复核范围

本次仅检查当前项目《电力领域数据基础设施标准体系建设研究》的源材料解析、语义分类、Source Truth 编译和 Foundation 机械投影，不引用其他项目产物，不进入脚本 AUTHOR 或 Stage 02。

## 修复结果

1. 显式表头与数据行已正确区分。Word 表格首行继续保留在稳定 source map 中，投影器仅在表头状态、表格行号和表头文字全部一致时跳过该元数据行。
2. 表格续行已保留一级类目上下文。A2、A3 等首列为空的记录带有 `table_context.group_label=A 基础通用标准`，并标明上下文来自前一非空首列。
3. 建设原则已归入要求类。NF-0076 至 NF-0081 的 `fact_type` 和 `semantic_role` 均为 `requirement`，投影状态为“建议”。
4. 研究目的与结论已接入 source-chain。研究目的 sec-0005 形成目标节点，结论 sec-0022 形成结论节点，避免实质性事实存在但论证链漏接。
5. 语义状态已分开表达。研究目标标记为“规划”，建设原则标记为“建议”，标准研制动作与三阶段实施路径标记为“规划”，已形成的研究判断和成果表述保留为“现状”，后续行动标记为“规划”。
6. Foundation 已机械保留 `claim_role`、`status`、`semantic_status`、`source_argument_role`、`argument_duty`、规范化事实类型及表格上下文。

## 自问自答复核

### 是否仍有源单元遗漏

答：没有。Source Truth 审计覆盖 104 个源单元，20 个必需目标全部覆盖，未覆盖源单元为 0，未解决核心判断为 0。

### 表格续行是否会丢失一级类目

答：不会。续行只继承同一表格中最近一个非空首列值，并保留 `inherited_previous_nonempty_first_column` 依据；跨表格不会继承。

### 原则、目标、研制方向和实施安排是否仍会被统一压成现状事实

答：不会。投影器结合来源论证角色、事实类型和动作标记生成状态。保守反例仍受保护：缺少建议或行动信号的刚性要求继续作为现有边界，结论中的已完成成果继续作为现有事实。

### 论证链遗漏能否在 Source Truth 编译前发现

答：可以。语义校验新增 `substantive_section_missing_from_source_chain` 阻断项，实质性事实若没有被 source-chain 直接引用，也没有所属章节节点，将在语义校验阶段报错。

### 当前 Deck Plan 能否继续进入 AUTHOR

答：不能。Source Truth 已由 110 条更新为 166 条，现有 Deck Plan 缺少 `evidence_fit_review_mode: strict`，审计已阻断。下一步应基于新 Foundation 重新规划，并在“脚本规划待确认”节点提交人工审核。

## 验证记录

- 定向回归：53 passed，2 skipped
- 扩大回归：230 passed
- Source Truth：166 条记录
- Source Truth 审计：passed
- 源证据交叉审计：passed
- 审计提示：ST0044 与 ST0030 存在一项非阻断优先级叙事提示，建议在重新规划页面时复核优先级
- Deck Plan 审计：failed，原因是严格 evidence-fit 审阅字段缺失；该阻断符合预期

## 流程兼容性提示

`source-foundation-truth` 生成的语义论点模型声明为 `interpretation_contract_mode=projection`，通用 `semantic-check` 当前只接受 `legacy` 或 `strict` 模式，因此会产生模式与字段契约告警。Source Truth 专用审计和源证据交叉审计均已通过。本项属于现有命令契约衔接问题，应在后续工作流整理中单独处理，避免通过补写无来源字段消除告警。

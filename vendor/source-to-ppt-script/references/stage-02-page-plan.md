# 阶段2：页面规划

## 输入

- `stages/01_information_assets.json`，且状态为`current`
- `config/project.yaml`
- Schema：`references/schemas/page_plan.schema.json`
- 拆页规则：`references/page-splitting-rules.md`

## 目标

形成完整叙事主链和页面规划卡。此阶段禁止写最终上屏文案，禁止设计视觉版式。

## 规划规则

1. 页面不是原文章节摘要。围绕汇报对象会提出的问题组织叙事。
2. 每页只有一个`page_mission`、一个`core_judgment`和一种`relationship_type`。
3. `audience_question`必须是本页真正回答的问题，不能写“本页说明什么”等占位语。
4. `source_asset_ids`只能引用有效资产，且应足以支撑核心判断。
5. core或must_retain资产必须进入合适页面；无法分配时显式写入`unassigned_core_asset_ids`，不得静默遗漏。
6. `must_include`写必须表达的语义；`must_not_include`写最容易误混入本页的相邻内容。
7. `page_role`使用具体职能，如“必要性页、总体架构页、运营机制页、实施安排页、收益机制页”。
8. `previous_page_relation`与`next_page_relation`应说明叙事承接，避免“承接前页、引出后页”等空话。
9. 不为凑页数重复资产。页面数量以叙事完整和页面纯度为优先，遵守配置范围。
10. 封面只承载主题；结束页应有明确收束或行动，不自动生成空泛“谢谢”。

## 推荐叙事检查

根据材料实际内容选择，不强套固定章节：

- 背景或形势 → 核心问题 → 必要性/定位 → 总体方案 → 关键机制/场景 → 安全与边界 → 运营与收益 → 实施安排 → 决策或行动。

若材料不具备某一部分，不得为了模板完整而补造。

## 出口条件

- 每页的使命与判断可以用一句话清楚复述。
- 页面之间形成一条可讲述的主链。
- 所有核心资产已分配或明确声明未分配。
- `split_risk=high`页面已拆分或给出充分理由。

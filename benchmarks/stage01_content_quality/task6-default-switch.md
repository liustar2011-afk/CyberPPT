# Task 6 默认切换验证

- 技术判断：`SUPPORT WITH CONDITIONS`
- 结论：尚未毕业
- 当前默认 Deck Plan 合同：v1
- 证据边界：合成样本只验证尺寸路由和合同能力，不计入真实项目数量或内容质量结论。

## 五类验证样本

| 样本 | 证据范围 | 页等价 | 阅读模式 | 结果 |
|---|---|---:|---|---|
| bounded-formal-12-pages | synthetic_boundary_fixture | 12 | direct | 通过 |
| long-single-65-pages | synthetic_boundary_fixture | 65 | long | 通过 |
| three-short-files-over-threshold | synthetic_boundary_fixture | 66 | long | 通过 |
| proposal-assets-numbers-current-facts | contract_coverage_fixture | 18 | direct | 通过 |
| review-without-single-peak | contract_coverage_fixture | 16 | direct | 通过 |

## 真实项目链路

| 项目 | Foundation | Plan | Author | Stage 02 handoff | 说明 |
|---|---|---|---|---|---|
| power-data-infrastructure-standard-system-research-20260828-002 | 通过 | 通过 | 通过 | 通过 | — |
| power-data-infrastructure-standard-system-research-20260828-003 | 通过 | 通过 | 通过 | 未通过 | DECK_PLAN_SCRIPT_DRIFT: p01 title or core judgment differs from final-script.md |

达到 Stage 02 handoff 的真实项目为 1/3。

## 毕业条件

| 条件 | 状态 |
|---|---|
| `five_shape_cases_pass` | 通过 |
| `three_real_projects_reach_handoff` | 未通过 |
| `script_source_artifact_boundary` | 通过 |
| `script_to_strict_size_ratio_at_most_40_percent` | 待补证据 |
| `foundation_human_review_complete` | 待补证据 |
| `dual_profile_recall_non_regression` | 待补证据 |
| `independent_blind_review_wins_three_of_four` | 待补证据 |
| `authoring_fields_reduced_at_least_40_percent` | 通过 |
| `long_selection_reviewed_at_15_to_30_percent` | 待补证据 |

## 已验证的机械边界

- script 来源准备仅创建：`script/.cache/source-index.json`。
- 人工计划字段由 25 降至 13，减少 48%。

## 待补的内容质量证据

- 增加至少两个能通过当前 Stage 02 handoff 的独立真实项目，其中一个用于补足三项目门槛。
- 对同一批材料运行 script/strict 双 profile，记录结构化产物体积、关键数字、责任、条件、边界召回和来源错误。
- 交付 Foundation 人工审核稿，并由独立审阅者确认 long 选区与排除理由。
- 完成 v1/v2 四维盲评；现有 P03/P04 Agent 盲评保留为前置证据，不代替独立人工评审。

当前保持 v1 为生产默认，v2 lean 可继续用于受控验证。满足全部条件后再切换默认。

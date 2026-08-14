# 汇报场景组合矩阵

正式汇报采用四维组合，不再只依赖单一模板：

```yaml
writing_profile: government-soe-formal
report_subtype: special-topic-report
decision_intent: seek-support
audience_level: regulator
project_phase: planning
```

## 一、汇报目的 `decision_intent`

| 配置值 | 中文含义 | 必须强化的内容 |
|---|---|---|
| `inform` | 报告情况 | 事实、进展、问题、安排 |
| `seek-guidance` | 请示指导 | 需要指导的问题、政策依据、落实安排 |
| `seek-decision` | 提请决策 | 决策事项、方案条件、风险影响、决策后安排 |
| `seek-support` | 协调支持 | 支持主体、支持方式、具体事项、支持后成果 |
| `deploy` | 部署工作 | 任务、主体、节点、成果、监督要求 |
| `evaluate` | 检查评估 | 评价依据、证据、问题、整改要求 |
| `accept` | 验收确认 | 任务对应、指标证明、遗留问题、验收意见 |

## 二、受众层级 `audience_level`

| 配置值 | 受众 | 表达重点 |
|---|---|---|
| `central-ministry` | 国家部委 | 政治站位、政策依据、行业价值、试点衔接 |
| `regulator` | 行业主管或监管部门 | 职责定位、行业影响、合规边界、协调事项 |
| `superior-unit` | 上级单位 | 任务承接、责任落实、风险问题、请示事项 |
| `party-committee` | 党委会 | 政治方向、前置程序、三重一大、风险合规 |
| `board` | 董事会 | 公司治理、投资经济性、风险责任、决策事项 |
| `executive-leadership` | 领导班子 | 核心结论、重点任务、责任分工、关键风险 |
| `internal-department` | 内部部门 | 操作要求、协同机制、节点和交付成果 |
| `member-enterprise` | 会员或所属企业 | 参与方式、权责边界、服务价值、工作要求 |
| `external-public` | 外部公开对象 | 公开口径、社会价值、敏感信息控制 |

## 三、项目阶段 `project_phase`

| 配置值 | 阶段 | 推荐状态表达 |
|---|---|---|
| `planning` | 规划研究 | 拟开展、计划推进、探索建立、条件成熟后实施 |
| `proposal` | 立项申报 | 拟建设、建议立项、计划实施、申请支持 |
| `feasibility` | 可行性研究 | 经测算、初步具备、拟分阶段实施、尚需论证 |
| `construction` | 建设实施 | 正在建设、已完成阶段任务、尚待验收 |
| `pilot` | 试点验证 | 开展试点、初步验证、形成样板、仍需完善 |
| `operation` | 运营 | 已投入运行、持续优化、逐步拓展、形成服务 |
| `acceptance` | 验收 | 已完成合同任务、经测试验证、存在遗留事项、提请验收 |

## 四、组合规则

- **章节骨架**由 `report_subtype` 决定。
- **结尾动作和必须回答的问题**由 `decision_intent` 决定。
- **信息深度、政策站位和术语解释程度**由 `audience_level` 决定。
- **时态、成果强度和可使用的状态词**由 `project_phase` 决定。
- 四项配置必须与Source Truth Map一致；配置不能覆盖源材料事实。


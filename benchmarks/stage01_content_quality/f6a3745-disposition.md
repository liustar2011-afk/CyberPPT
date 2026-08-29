# `8726f23e..f6a3745` 增量处置

## 判定基准

`8726f23e` 是来源论点结构基线。`f6a3745` 仅提供失败反例。处置默认
为 `remove`；只有能够脱离该项目并由独立测试证明价值的增量进入
`independently_revalidate`。

| 增量 | 处置 | 落地结果 |
|---|---|---|
| `phrase_led_basis` schema、审计、测试与 Skill 规则 | remove | 已从合同和审计移除，表达模式回到作者/定性 Critic 判断 |
| 可读命题谓词正则与无标点放行 | remove | 已移除；正则不承担可读性证明 |
| 日期型里程碑动作词正则 | remove | 已移除；语义完整由 Onscreen Critic 和真实样本评分判断 |
| evidence-fit 理由模板正则 | remove | 已移除；v2 lean 不要求常规直接证据撰写适配说明 |
| `FULL_COPY_STATUS_STRENGTH_LOST` 弱化 | remove | 已恢复 `8726f23e` 的状态边界保护 |
| protected-term 新硬门禁 | remove | 已移除下游新门禁，避免逐词复制驱动写作 |
| 五步上屏法、silent-reader/ten-second/deletion 硬测试叙述 | replace | 替换为“完整论证→信息选择→双候选→定性比较→整页重写” |
| AUTHOR 生成职责说明 | replace | 保留生成式作者职责，加入 PLAN 回退与候选胜出规则 |
| `semantic_units` 上游原样投影 | independently_revalidate | 暂留兼容能力；仅由 strict/v1 回归消费，不作为 v2 lean 作者合同 |
| Plan Review 展示可选副标题 | independently_revalidate | 保留只读展示，独立测试验证不修改权威输入 |
| 电力真实项目及 QA 报告 | remove | 从能力和测试期望中移除，只作为 before 样本；原项目目录未删除或改写 |

## 新能力边界

- 新能力测试只引用抽取后的页面级 fixture，不把 `f6a3745` 产物作为期望输出。
- 叙事候选直接位于 `deck-plan.json.narrative_design`。
- Plan/Onscreen Critic 的候选、评分与问题清单不落盘为权威状态。
- 机器审计继续承担来源、合同和边界底线；内容质量由真实样本和可读评分证明。

# Script Quality Benchmark

这是可提交、脱敏、确定性的 Deck Plan 质量基线。运行：

```powershell
.\.venv\Scripts\python.exe benchmarks\script_quality\run.py
```

首版包含 10 个短小 fixture，覆盖正式汇报、实施方案、技术架构、分类说明和商务方案。每个 fixture 都声明了 deck 类型、预期阻断 issue、预期 warning 以及反例边界。Benchmark 只消费确定性 `audit_deck_plan`，不调用 Stage 02 生图，因此云端模型波动不会进入单元回归。

指标按稳定 issue code 统计：precision = 命中预期 code / 实际输出 code，recall = 命中预期 code / 预期 code。新增语义规则首期应保持 warning-first，并以 precision 不低于 85% 作为默认启用参考线。

反例包括来源保序、多个并列证据簇、结构页、主题型标题和历史计划缺字段；它们用于防止叙事规则把合法的来源原生结构误判为错误。

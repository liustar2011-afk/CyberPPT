# Relation Grammar 黄金页面优化开发进度

> 开发分支：`agent/relation-grammar-golden-page-20260831`
>
> 维护规则：每完成一个可独立验证的小步骤，立即提交实现，并在本文件追加一条进度记录，写明完成内容、改动文件、实现 commit、测试结果、已发现问题、剩余任务和下一恢复点。

## 总体状态

- 当前阶段：仓库基线盘点
- 总体状态：进行中
- 已完成：开发分支建立；独立进度台账初始化
- 工程边界：不新增 Stage1 authoritative IR；不扩展 Final Script schema；不把 AUTHOR/CRITIQUE 的生成式判断硬编码成低精度 lint
- 下一恢复点：定位 8 类黄金页面、Relation Grammar fixture、semantic topology、Stage2 relation expression 与现有测试

## 任务清单

- [ ] Step 0：仓库基线盘点与映射
- [ ] Batch A：统一黄金页面模板与 Relation Contract
- [ ] Batch B1：Governance 重构
- [ ] Batch B2：Comparison 重构
- [ ] Batch B3：Causal 收紧真实因果
- [ ] Batch C1：Parallel 同层尺度统一
- [ ] Batch C2：Convergence 输入角色优化
- [ ] Batch D1：Flow 增加真实业务交接物
- [ ] Batch D2：Roadmap 增加状态化进入条件与起终点
- [ ] Batch D3：Mapping 修正方向与 Cardinality
- [ ] Batch E：Onscreen 微语法与 Speaker Notes 去重
- [ ] Batch F：统一视觉结构合同
- [ ] Batch G1：Golden Page ↔ fixture 映射
- [ ] Batch G2：Grammar 边界回归测试
- [ ] Batch H：全量验证与收口

## 进度记录

### Step 0.1 — 初始化本轮开发台账

- 状态：完成
- 完成内容：
  - 建立独立开发分支 `agent/relation-grammar-golden-page-20260831`。
  - 新建本进度文件，固定“小步骤、立即提交、立即记录”的恢复机制。
  - 将开发任务拆分到可单独验证的最小步骤。
- 改动文件：
  - `docs/RELATION_GRAMMAR_GOLDEN_PAGE_OPTIMIZATION_PROGRESS.md`
- 实现 commit：本文件初始化提交；后续记录从下一小步骤开始写入精确 SHA
- 测试结果：无代码改动，不适用
- 已发现问题：尚未完成仓库文件映射，不能假设黄金页、fixture 或解析器路径。
- 剩余任务：见“任务清单”。
- 下一恢复点：读取仓库目录与关键入口，形成黄金页 → fixture → topology → Stage2 expression → tests 的现状映射。

# Stage1 作者化写作优化开发进度

> 开发依据：`CyberPPT Stage1 作者化写作优化开发方案（新版）`
>
> 工作方式：按小批次落地；每完成一个批次立即提交；本文件随每个批次同步更新，记录完成内容、验证结果、提交与剩余工作，确保中断后可直接续作。

## 1. 基线与硬边界

- 开发基线：`main`，启动时 HEAD 为 `f2316f83aa9f5735f6780760a63e3189a7426835`。
- 保持 Stage1 三个正式权威产物：`script/foundation.json`、`script/deck-plan.json`、`script/dist/final-script.md`。
- Deck Plan 继续保持 v2 lean，不增加 Relation Units、Argument Topology、Onscreen Contract 等预写字段。
- Final Script 保持现有字段，不新增第四套 Stage1 authoritative IR。
- AUTHOR/CRITIQUE/REWRITE 的操作性作者规则继续集中在 `authoring-contract.md`。
- Stage2 继续消费锁定后的最终 `onscreen`，不承担业务文案重写。
- 确定性代码只做机械底线检查，不替代 AUTHOR 的语义与论证判断。

## 2. 技术判断

结论：`SUPPORT WITH CONDITIONS`。

实施条件：

1. Relation Unit 作为教学层的工作方法，不新增持久化项目字段或独立权威文件。
2. 当前 `authoring-contract.md` 已使用 independent arguments / reasoning unit、claim–argument–evidence chain 表达同一语义职责；为避免同义 ontology 漂移，不强行把 Relation Unit 再固化成第二套正式运行时术语。
3. Authoring grammar 与 machine semantic topology 通过明确映射衔接，不继续增加近义 topology。
4. Golden Examples 作为参考/回归样例，不成为第四套内容规范；保留一个总索引，其余示例独立存放并按需读取。
5. Critic/Lint 新增规则必须可机械判定；需要作者判断的事项保留为生成式 Critic 规则。
6. 每批修改先做最小范围验证，再提交；发现架构冲突时优先收敛而非扩张。

## 3. 批次计划

| 批次 | 优先级 | 范围 | 状态 |
|---|---|---|---|
| 0 | P0 | 建立持续进度台账与开发边界 | 已完成 |
| 1 | P0 | AUTHOR Contract 现状审计：主推理链、Relation Unit 语义职责、Evidence Binding | 已完成（基线已满足，不重复改写） |
| 2 | P0 | AUTHOR Contract 现状审计：Onscreen、Speaker Notes、Critic/Rewrite 最早失败点 | 已完成（基线已满足，不重复改写） |
| 3 | P1 | Golden Examples：建立 8 类关系页面索引并拆出既有 Parallel / Flow | 已完成 |
| 4 | P1 | Golden Examples：补齐 6 类缺失完整样例与作者自检 | 已完成 |
| 5 | P1 | Critic / Script Quality：覆盖审计 + 缺失机械底线 | 已完成 |
| 6 | P1 | Critic / Script Quality：方向关系扁平化、Roadmap completeness 等检查 | 进行中 |
| 7 | P1 | Topology：Authoring grammar ↔ machine semantic topology 映射与一致性 | 待开始 |
| 8 | P2 | Stage1 authoring fixtures：8 类正确案例与典型错误案例 | 待开始 |
| 9 | P2 | 回归测试：Critic/Lint/topology/Stage1→Stage2 结构保持 | 待开始 |
| 10 | P2 | 全量验证、文档收口、剩余兼容性问题清理 | 待开始 |

> 批次允许根据仓库实际结构进一步拆小；任何拆分都必须先更新本表并在提交记录中说明。

## 4. 已完成记录

### Batch 0 — 进度台账初始化

完成：建立进度文件、固化基线和硬边界、拆分小批次。

验证：仓库权限具备 push/admin；未修改运行时代码和作者规则。

提交：`b057bc56972be2e58ac0991cea159524e9f1c75c`。

### Batch 1–2 — P0 AUTHOR Contract 差距审计

结论：当前基线已覆盖新版方案主要 P0 作者方法，不对 71KB 单一运行权威做重复性重写。

已确认：source meaning → `core_message` → independent arguments + evidence → Full Copy → Onscreen；普通模块标题完整判断；relation grammar 与 semantic topology 的现有衔接；Speaker Notes 增量规则；Critic/Rewrite 最早失败点回退。

处理差异：Relation Units 仅作黄金示例教学标签，映射到 Contract 的 independent arguments / reasoning units，不形成 schema 或第二套 ontology。

验证：已核对 `authoring-contract.md` 与 `SKILL.md`；本批不改变 schema、运行时代码或 Stage1→Stage2 handoff。

提交：`624f6f8e1d827f9edf5a0cf3c5c2d7d76f32706b`。

### Batch 3 — 黄金示例索引与既有样例拆分

完成：

- `golden-page-script-example.md` 改为 8 类 Relation Grammar 总索引；
- 拆出 `golden-page-parallel.md` 与 `golden-page-flow.md`；
- 两页统一补齐页面使命、核心结论、主论证链、Argument Topology、Relation Units、Full Copy、Onscreen、视觉结构、Speaker Notes、作者自检；
- 保留原兼容入口，不新增 authoritative artifact。

验证：Parallel 保持同维度并列；Flow 保持真实顺序和 feedback 回写；纯文本均可恢复核心关系。

提交：`82b03204cee5aea82ac25c82c3f7b97e48e9459c`。

### Batch 4 — 补齐六类黄金关系页面

新增：

- `golden-page-causal.md`：变化 → 要求 → 缺口 → 建设结论；
- `golden-page-convergence.md`：多输入独立贡献并汇入共同结果；
- `golden-page-mapping.md`：问题端与响应端一一对应；
- `golden-page-comparison.md`：固定对象、固定评价维度进行比较；
- `golden-page-roadmap.md`：每阶段同时包含进入条件与新增状态；
- `golden-page-governance.md`：主体 → 责任对象 → 控制机制 → 受保护结果。

统一要求：六页均包含核心结论、主论证链、Argument Topology、Relation Units、Full Copy、Onscreen、视觉结构、Speaker Notes、作者自检；Relation Units 继续只作为教学标签。

验证：Causal 不把并列事实伪装为时间顺序；Convergence 不虚构输入间先后；Mapping 两端同时可见；Comparison 始终使用同一对比较对象与统一评价维度；Roadmap 以触发条件和新状态建立演进关系；Governance 将主体、责任、机制和受保护结果绑定。

提交：`33489f0172da1c24764d7cb1b3c14a884b287cc7`。

### Batch 5 — 正式 Final Script lint 覆盖审计与数字对象底线

审计结论：新版方案列出的多数机械检查在当前仓库正式 `script_engine` 链路中已经存在，不重复实现。

现有正式覆盖包括：

- 抽象/名词式模块标题：`ONSCREEN_HEADING_INCOMPLETE`；
- 标题缺少业务对象：`ONSCREEN_HEADING_OBJECT_OMITTED`；
- 父子层级和投影结构：现有 Onscreen / Full Copy contracts；
- 多模块页缺 Evidence 层：`ONSCREEN_EVIDENCE_LAYER_MISSING`；
- 上屏与 Core Message 偏离：`ONSCREEN_CORE_MISALIGNED`；
- 隐藏中间步骤、关系端点不完整：AUTHOR field contract；
- 现有 `cyberppt/script_quality/` 兼容层还包含父子重复、同层级角色混杂、false-parallel、declared relation visibility 等检查。

新增的真实缺口：

- 新建 `script_engine/authoring_quality_contracts.py`；
- 新增 `ONSCREEN_NUMBER_WITHOUT_OBJECT`：只拦截无语义标签的近似纯数字/单位上屏明细，如 `80%`、`30家`、`3项`；
- `覆盖率：80%`、`2026年`、`首批覆盖30家重点单位` 等有对象/合法日期表达保持通过；
- 规则已接入正式 `lint_final_script()`，未落到旧兼容链路；
- 新增 `tests/script_engine/test_stage1_authoring_quality.py` 两组回归用例。

提交链：

- `be2a768cc1928e1e793949a8a97301aa36ee1793`：新增聚焦规则模块；
- `d5277ce7d69fc9337bda5ba492938346fd5485ea`：接入正式 lint；
- `f5a805ac1877f7694c00ae43e79afd138fee5235`：新增回归测试。

验证：代码级调用链与测试用例已落仓；GitHub Actions 状态在本批台账提交后检查，如失败则立即提交修复。

## 5. 当前剩余工作

下一批：Batch 6，先审计正式 argument pattern / topology contracts 对 directed flattening 的现有覆盖，再只补 Roadmap `进入条件/时间信号 + 新状态` 等仍可机械判定的缺口。

随后：Authoring grammar ↔ machine topology 一致性；P2 fixtures 与回归测试；全量验证和收口。

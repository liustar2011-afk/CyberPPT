# CyberPPT 架构收敛实施记录（2026-08-31）

> 分支：`agent/architecture-convergence-20260831`
>
> 目的：按阶段实施架构收敛，每个小阶段独立提交，保证中断后可从最近提交继续。

## 技术判断

结论：`SUPPORT WITH CONDITIONS`

实施原则：

1. 优先修复会影响可复现性、权威边界和恢复语义的问题。
2. Stage 02 已完成较好的 pipeline 分层，保持现有生产路线，不进行推倒重写。
3. Stage 01 的大模块拆分采用行为保持型重构；本轮不把高风险语义改写与结构拆分混在同一提交。
4. 所有兼容迁移均保持单向：旧入口只能适配到新核心，不允许反向 monkey-patch 新核心。
5. 每阶段完成后更新本文档并提交。

## 阶段计划与状态

| 阶段 | 内容 | 状态 | 提交 |
|---|---|---|---|
| 0 | 建立独立分支与实施记录 | 完成 | `8f12875` |
| 1 | 真正冻结 Style 09 resolved contract，并建立运行输入 fingerprint | 进行中 | 见阶段 1 记录 |
| 2 | 统一 Stage 01 Authority Map 与权威命名 | 待实施 | - |
| 3 | Stage 02 正式状态机与 needs-action 语义 | 待实施 | - |
| 4 | 收缩 Stage 02 compatibility facade，去除 monkey-patch 生产依赖 | 待实施 | - |
| 5 | 将主观语义/文风检查从 hard blocker 分级为 warning/critic | 待实施 | - |
| 6 | 修复 Python 包/运行时依赖边界，增加 production extras 与 wheel smoke CI | 待实施 | - |
| 7 | 独立 `input_fingerprint` 与 `run_id/build_id` | 待实施 | - |
| 8 | Stage 01 大模块行为保持型拆分（低风险子域优先） | 待实施 | - |
| 9 | 统一正式 Style 09 路由与 CLI/文档残留 | 待实施 | - |
| 10 | 清理根目录临时文件与仓库治理规则 | 待实施 | - |

## 阶段 1：视觉锁与输入身份

### 1A. Style 09 resolved contract 真冻结

状态：完成。

提交：

- `46c34f8` `fix(style): freeze resolved Style 09 contract in lock`
- `d159005` `test(style): cover frozen Style 09 snapshots`

完成内容：

1. Style 09 只在创建 `visual_style_lock.json` 时读取 `references/visual-system.md` 并解析完整 contract。
2. 锁文件新增 `resolution.mode = frozen_snapshot`、resolved contract SHA-256 与来源记录。
3. `load_style_lock()` 生产消费时只读取锁内快照，不再动态刷新 canonical source。
4. 旧式 Style 09 live lock 因没有冻结 contract 而 fail-closed，要求重新生成锁。
5. 锁内 contract 被修改但 SHA 未同步时直接拒绝。
6. 新增回归测试覆盖快照不刷新、legacy lock 拒绝、篡改检测和新锁快照生成。

待完成：

- 1B：将冻结的 resolved contract SHA 和关键 Stage 02 输入组成 deterministic `input_fingerprint`。
- 1C：Prompt SHA 变化时，已审计 full 图不得因为旧 text audit 继续静默复用。

## 续跑规则

发生中断时：

1. 切换到 `agent/architecture-convergence-20260831`。
2. 查看本文档最后一个“完成”阶段或子阶段。
3. 从下一个阶段继续，不重做已提交阶段。
4. 每个阶段必须同时包含代码/文档变更与对应测试或静态契约检查。

## 重要约束

- 保留“脚本 → 完整图片 → 图转可编辑 PPT”的生产路线。
- 保留 Final Script 作为 Stage 02 唯一跨阶段业务输入。
- 保留 audited full image 作为 editable reconstruction 的视觉权威。
- 保留 SHA-256 provenance、逐页 checkpoint、OfficeCLI 真渲染 QA。
- 不在本轮引入第二套平行工作目录或审批文件体系。

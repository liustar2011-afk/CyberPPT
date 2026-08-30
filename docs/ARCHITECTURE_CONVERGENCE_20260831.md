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
| 1 | 真正冻结 Style 09 resolved contract，并建立运行输入 fingerprint | 完成 | 见阶段 1 记录 |
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

状态：完成。

### 1A. Style 09 resolved contract 真冻结

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

### 1B. Deterministic input fingerprint

提交：

- `bedefa0` `refactor(stage02): model deterministic input identity`
- `742e685` `feat(stage02): derive deterministic input fingerprint`
- `031f90f` `feat(stage02): persist input fingerprint in manifest`
- `408c4da` `feat(stage02): expose input identity in delivery receipts`
- `b960e7e` `test(stage02): cover deterministic input fingerprint`

完成内容：

1. `Stage02BuildContext` 新增 `input_fingerprint` 与 `resolved_style_contract_sha256`。
2. fingerprint 采用稳定 JSON 序列化，纳入脚本快照、Stage 02 intake、视觉规格、style lock、冻结 style contract、页集合、生产/组装模式、ImageGen 模型和质量、prompt enrich、参考图开关、文字审计策略、prompt override 目录摘要及 autonomous contract 摘要。
3. 默认 `build_id` 的摘要部分从 fingerprint 派生，时间戳仍只承担本次运行身份；阶段 7 再完成命名和兼容接口收敛。
4. manifest、build context 与最终 run summary 均持久化 input fingerprint 与相关 SHA，恢复和审计时可直接区分输入身份与运行身份。
5. 新增 deterministic、style contract 变化、assembly mode 变化和显式 build ID 保持等测试。

### 1C. Prompt 变化后的产物失效

提交：

- `3b004a8` `fix(stage02): invalidate reused artifacts when prompt changes`
- `81dc232` `test(stage02): block stale prompt artifact reuse`

完成内容：

1. prior full 图只有在其 `generated_prompt_sha256` 与当前页 `prompt_sha256` 完全一致时才可复用。
2. clean base、graphic text policy、authored SVG 和 Quick checkpoint 与 full 图使用同一页级 Prompt 绑定，不再仅凭“源脚本相同”继承。
3. partial recovery 继续支持保留未重跑页面，但要求 frozen Style contract 一致且 retained full 图存在明确 generated prompt binding。
4. 新增测试覆盖 Prompt 改变时禁止复用、Prompt 不变时允许复用、Style contract 改变时 partial recovery 不继承旧页。

### 阶段 1 验证说明

已新增针对三个子阶段的回归测试。仓库 Actions 当前仅在 `main` push 和 Pull Request 事件触发，独立工作分支本身不会产生 CI run；本阶段完成后创建 Draft PR，使后续每次 push 都由现有 GitHub Actions 执行全量 pytest。

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

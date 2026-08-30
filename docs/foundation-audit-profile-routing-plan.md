# Foundation 审计 profile 路由修复方案

## 目标与结论

目标是让 `strict/legacy` 项目的 `audit-foundation` 执行适用于机械投影 Foundation 的正确质量校验，并继续保留 `script` profile 的来源索引、哈希与 `reading_strategy` 校验。

独立判断结论：`SUPPORT WITH CONDITIONS`。

已验证事实：

- `project_source_truth_to_foundation` 仅机械投影 Source Truth 字段，输出中没有 `reading_strategy`。
- `validate_script_foundation_against_index` 同时校验来源身份、来源哈希、引用单元和 `reading_strategy`，其错误信息也明确限定为 script-profile Foundation。
- 原有 `audit-foundation` 仅因发现同级 `script/.cache/source-index.json` 就调用 script 专属校验，未检查项目 `manifest.yml` 的 `profile`。
- `project_status` 已基于 `manifest.yml` 将严格路径与 script 来源索引校验隔离。

反例已纳入测试：在 `profile: script` 的项目中保留同一份哈希不一致来源索引和缺失 `reading_strategy` 的 Foundation，审计必须失败并报告这两类问题。

## 最小实现

1. 在 `script_engine.cli` 的 `audit-foundation` 入口读取 Foundation 所属项目的 `manifest.yml`。
2. `profile` 为 `strict` 或 `legacy` 时跳过 `validate_script_foundation_against_index`；基础 schema 校验和 Foundation 语义审计继续执行。
3. `profile` 为 `script` 时继续运行来源索引交叉校验。
4. 缺少可识别 manifest 的旧式 standalone Foundation 保留现有行为：只要存在有效 v2 sibling source index，仍执行 script 交叉校验。

该方案修复审计器自身的 profile 路由，不改变调用侧参数，不修改 Source Truth、Foundation、Deck Plan 或最终脚本。

## 验证范围

- 定向 CLI 测试覆盖严格项目跳过 script 专属校验。
- 定向 CLI 测试覆盖 script 项目继续阻断哈希漂移和缺失 `reading_strategy`。
- 对供需预测严格项目实际运行 `audit-foundation`，确认原先两项误报消失。

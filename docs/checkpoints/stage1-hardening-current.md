# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `8 / 子步骤 1`。

### 批次 5：Final Script Source Provenance

- Final Script 内容页强制要求 `source_provenance`。
- 标准 lineage 为：`packet_sha256 + source_refs + unit_ids`。
- `audit-final` 与 `render-stage02` 均验证 Final Script provenance 与当前 Author Preflight 一致性。

### 批次 6：Native-source Fidelity Audit

- Final Script 内容页直接与逐页 exact native source units 做高风险事实一致性校验。
- 覆盖新增数字/日期、数字限定词丢失、明确范围限定词丢失、状态提升、责任强度提升、结论强度提升。
- `audit-final` 与 `render-stage02` 统一使用 `native_source_fidelity_gate_issues()`。
- Stage02 发现事实漂移时返回 `kind=native-source-fidelity`，不写出输出文件。

### 批次 7：Project Status 接入 Stage1 Gate

- `script_engine/project_status.py` 新增正式 `stage1` 状态区，集中输出：
  - `source_index`
  - `foundation`
  - `deck_plan`
  - `author_preflight`
  - `final_script`
  - `final_audit`
- Author Preflight 状态不信任静态 Manifest，而是先重建 current preflight，再校验 Manifest 是否仍代表当前状态。
- `author_preflight.pages` 输出逐页 `gate_status / freshness / exact_source_status / source_refs / unit_ids / issues`。
- 顶层 `stage` 不再允许“无 Preflight 但 Final Script 存在”显示为已就绪。
- 只有 `final_audit_report()` 真正通过后，项目才显示“可进入 Stage02”。
- `tests/script_engine/test_project_status_stage1_gate.py` 已覆盖五类状态：
  1. fresh Preflight：页面 `passed + fresh + exact source available`；
  2. Deck Plan 更新：原 Packet 立即显示 `stale`；
  3. Manifest 缺失：即使当前 Packet 可重新计算为 passed，仍不得放行；
  4. Packet 自身为 `blocked`：逐页明确输出 `gate_status=blocked` 及阻断原因；
  5. Preflight 与 provenance 均合法、但 Final Script 新增原文不存在的数字：`final_audit=failed`，顶层状态明确“不得进入 Stage02”。
- 所有旧 `status` 契约测试已迁移：
  - 无 Source Index / Manifest 时明确显示 Preflight 未通过；
  - lint/advisory 可以继续独立报告，但不能绕过 Stage1 Gate；
  - 旧“脚本文件存在即确定性检查通过”的契约已取消。

### 批次 8 / 子步骤 1：历史失败基线治理

已逐项处理此前 3 个 `main` 基线失败：

1. `FAITHFUL_RELATION_PROMOTED`
   - 规则注册表已明确其为低置信度 `warning`；
   - 测试已迁移为检查 warnings，不再错误要求 blocker。
2. identified onscreen item code-only fixture
   - 原测试使用 `A→B`，与当前 taxonomy-code 合同不一致；
   - 改为正式 taxonomy code 形态 `A1+B2`，继续验证 object item 不会绕过可见文本审计。
3. Style 09 样例尺寸
   - 旧测试固定要求 `(2048, 1024)` / 2:1；
   - 当前正式参考图为 16:9；
   - 新契约改为至少 `1600×900` 且接近 16:9，不再把历史像素尺寸写死为业务契约。

### 最近一次全量 CI

在批次 7 代码落地、旧 status 测试尚未迁移时：

`7 failed, 2238 passed, 8 skipped, 49 subtests passed`

其中：

- 4 项为旧 status 契约；已完成迁移；
- 3 项为上述历史基线；已完成治理。

当前 head 已没有已知未处理失败，并补齐了 blocked page 与 final-audit-failed 两类状态验收用例，等待下一轮 GitHub Actions 全量验证。

## 下一步

批次 `8 / 子步骤 2`：读取当前 head 的全量 CI。

验收目标：

1. Python 3.10 / 3.12 均达到 `0 failed`；
2. OfficeCLI、build package、artifact audit 保持通过；
3. 若出现新失败，继续按“真实实现缺陷 / 过期测试 / 环境依赖”分类处理，不使用无理由 xfail；
4. CI 绿色后进入收口批次：更新 Stage1 工作流文档、最终验收记录和 PR 描述，形成可合并状态。

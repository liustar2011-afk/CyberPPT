# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `6B / 子步骤 1`。

### 批次 5：Final Script Source Provenance

- Final Script 内容页已强制要求 `source_provenance`。
- 标准 lineage 为：`packet_sha256 + source_refs + unit_ids`。
- 新增 `source_provenance_for_page()`，只允许从 passed Author Preflight 页面生成 provenance。
- `audit-final` 与 `render-stage02` 均已验证 Final Script provenance 与当前 Author Preflight 是否一致。
- provenance 不一致时 Stage02 返回 `kind=final-source-provenance` 并拒绝输出。
- 现有正式 examples 和运行链测试已迁移到新契约。

### 批次 6A：Native-source Fidelity Audit

- 新增 `script_engine/native_source_fidelity.py`。
- Final Script 内容页直接与逐页 exact native source units 做高风险事实一致性校验。
- 确定性校验覆盖：新增数字/日期、数字限定词丢失、状态提升、新增责任强度、新增结论强度。
- `audit-final` 与 `render-stage02` 均在 Preflight Gate 和 provenance 通过后执行 Native-source Fidelity Gate。
- Stage02 发现事实漂移时返回 `kind=native-source-fidelity`，不写出输出文件。

### 批次 6B / 子步骤 1：统一门禁与范围限定保全

- 新增共享入口 `native_source_fidelity_gate_issues()`，统一负责加载当前 Page Source Packets、处理 loader issues、执行 Native-source Fidelity Audit。
- `audit-final` 与 `render-stage02` 已统一使用该入口，不再分别装配 Packet 与审计逻辑。
- 新增明确范围限定词保全：`不含 / 首批 / 当前 / 主要 / 部分 / 仅`。
- 采用保守的“限定词 + 原文锚点”匹配，仅当原文锚点在 Final Script 中继续出现但其绑定限定词消失时阻断，避免泛化语义评分。
- 新增 focused tests：
  - `仅面向高校开放` 不得改成 `面向高校开放`；
  - 保留 `仅` 时通过；
  - `不含用户明细数据` 不得改写为无排除边界的表达。

### 最新 CI 诊断

PR #34 最近一次已完成 Python 3.12：`5 failed, 2234 passed, 8 skipped, 49 subtests passed`。

其中 3 项为分支建立前 `main` 已存在问题：

1. `test_mission_and_judgment.py::test_unsupported_core_is_still_checked_against_source`
2. `test_onscreen_object_items.py::test_identified_items_still_detect_bad_hierarchy_and_code_only_mapping`
3. `test_extended_style_9_assets.py::test_style_nine_sample_is_available_and_matches_runtime_registry`

本分支新增的 2 项已完成修复：

1. Stage02 已补齐 Native-source Fidelity Gate。
2. `test_flow_convergence_contracts.py` 已迁移到强制 `source_provenance` 契约。

## 下一步

批次 `6B / 子步骤 2`：读取当前 head 的 GitHub Actions，确认新增门禁和范围限定检查没有引入新的 Stage1 回归。

通过后进入批次 7：`project status` 接入 Stage1 Gate。

计划：

1. `status` 不直接信任持久化 Manifest，而是复用当前 Author Preflight Gate 重新计算结果；
2. 输出项目级 Author Preflight 状态和逐页 `passed / blocked / missing / stale / not_applicable`；
3. 显示每页 freshness、exact source 状态及阻断原因；
4. 将 Stage1 的 source index、Foundation、Deck Plan、Preflight、Final Script、Final Audit 状态集中到一个可机器读取的状态区；
5. 增加 focused status tests，并同步迁移现有 status 契约测试。

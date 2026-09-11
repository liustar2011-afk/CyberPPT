# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `7 / 子步骤 1`。

### 批次 5：Final Script Source Provenance

- Final Script 内容页已强制要求 `source_provenance`。
- 标准 lineage 为：`packet_sha256 + source_refs + unit_ids`。
- `audit-final` 与 `render-stage02` 均验证 Final Script provenance 与当前 Author Preflight 一致性。

### 批次 6：Native-source Fidelity Audit

- Final Script 内容页直接与逐页 exact native source units 做高风险事实一致性校验。
- 覆盖新增数字/日期、数字限定词丢失、明确范围限定词丢失、状态提升、责任强度提升、结论强度提升。
- `audit-final` 与 `render-stage02` 统一使用 `native_source_fidelity_gate_issues()`，不再各自装配审计逻辑。
- Stage02 发现事实漂移时返回 `kind=native-source-fidelity`，不写出输出文件。
- PR #34 已验证本分支新增失败归零：最近一次 Python 3.12 为 `3 failed, 2239 passed, 8 skipped, 49 subtests passed`；剩余 3 项均为分支建立前 `main` 已存在问题。

### 批次 7 / 子步骤 1：Project Status 接入 Stage1 Gate

- `script_engine/project_status.py` 已新增正式 `stage1` 状态区。
- `stage1` 当前集中输出：
  - `source_index`
  - `foundation`
  - `deck_plan`
  - `author_preflight`
  - `final_script`
  - `final_audit`
- Author Preflight 状态不直接信任已持久化 Manifest：
  1. 先基于当前 Deck Plan、Foundation、Source Index 和 Page Source Packets 重建 current preflight；
  2. 再调用 `author_preflight_gate_report()` 校验持久化 Manifest 是否仍代表当前状态。
- `author_preflight.pages` 直接暴露逐页：
  - `gate_status`
  - `freshness`
  - `exact_source_status`
  - `source_refs`
  - `unit_ids`
  - `issues`
- 项目阶段判断已调整：
  - Preflight 未通过时不得显示“确定性检查通过”；
  - Preflight 通过但 Final Script 缺失时显示“待写作最终脚本”；
  - Final Script 存在但最终审计失败时明确标记“不得进入 Stage02”；
  - 只有 `final_audit_report()` 真正通过后，才显示“可进入 Stage02”。
- 新增 `tests/script_engine/test_project_status_stage1_gate.py`，覆盖：
  - fresh Preflight 逐页状态；
  - Deck Plan 变化导致 Packet stale；
  - Packet 仍然 fresh 但 Manifest 缺失时，不允许 status 信任 Packet 并放行。

## 当前已确认的非本分支基线失败

1. `test_mission_and_judgment.py::test_unsupported_core_is_still_checked_against_source`
2. `test_onscreen_object_items.py::test_identified_items_still_detect_bad_hierarchy_and_code_only_mapping`
3. `test_extended_style_9_assets.py::test_style_nine_sample_is_available_and_matches_runtime_registry`

## 下一步

批次 `7 / 子步骤 2`：读取当前 head 的 GitHub Actions，迁移 `status` 旧契约测试并修正本批次暴露的问题。

通过后继续：

1. 完成批次 7：确保 `status` 对 fresh / stale / missing / blocked / final-audit-failed 均有稳定机器可读输出；
2. 进入批次 8：测试与 CI 基线治理，处理剩余 3 个当前 `main` 基线失败，使 PR 恢复真实绿色；
3. 最后更新 Stage1 工作流文档与 PR 验收记录，形成可合并状态。

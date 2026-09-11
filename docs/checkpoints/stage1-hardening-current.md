# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `6A / 子步骤 3`。

### 批次 5：Final Script Source Provenance

- Final Script 内容页已强制要求 `source_provenance`。
- 标准 lineage 为：`packet_sha256 + source_refs + unit_ids`。
- 新增 `source_provenance_for_page()`，只允许从 passed Author Preflight 页面生成 provenance。
- `audit-final` 与 `render-stage02` 均已验证 Final Script provenance 与当前 Author Preflight 是否一致。
- provenance 不一致时 Stage02 返回 `kind=final-source-provenance` 并拒绝输出。
- 现有正式 examples 和运行链测试已迁移到新契约。

### 批次 6A：Native-source Fidelity Audit

- 新增 `script_engine/native_source_fidelity.py`。
- Final Script 内容页现在直接与逐页 exact native source units 做高风险事实一致性校验。
- 当前确定性校验覆盖：
  - 新增数字/日期；
  - 数字限定词丢失；
  - 计划/预计等状态被提升为已完成；
  - 新增必须/应当/不得/严禁等责任强度；
  - 新增“必然/全面/显著”等结论强度。
- `audit-final` 已在 Preflight Gate 和 provenance 通过后执行 Native-source Fidelity Audit。
- `render-stage02` 已补齐同一 Native-source Fidelity Gate；发现事实漂移时返回 `kind=native-source-fidelity`，不写出 Stage02 文件。

### 最新 CI 诊断与本轮修复

PR #34 上一轮 Python 3.12：`5 failed, 2234 passed, 8 skipped, 49 subtests passed`。

其中 3 项为分支建立前 `main` 已存在问题：

1. `test_mission_and_judgment.py::test_unsupported_core_is_still_checked_against_source`
2. `test_onscreen_object_items.py::test_identified_items_still_detect_bad_hierarchy_and_code_only_mapping`
3. `test_extended_style_9_assets.py::test_style_nine_sample_is_available_and_matches_runtime_registry`

本分支新增的 2 项已完成修复：

1. `test_native_source_delivery.py` 暴露 Stage02 尚未实际调用 Native-source Fidelity——已在 `render_stage02_delivery()` 中补齐强制门禁。
2. `test_flow_convergence_contracts.py` 的内容页 schema fixture 缺少强制 `source_provenance`——已迁移到当前正式契约。

本地容器无法解析 `github.com`，因此无法在容器内重新 clone 分支运行 focused pytest；本轮以 PR GitHub Actions 作为正式验证环境。

## 下一步

批次 `6A / 子步骤 4`：读取本轮新 head 的 GitHub Actions。

目标：

1. 确认 Stage1 hardening 自身新增失败归零；
2. 若仅剩上述 3 个 `main` 基线失败，则完成批次 6A；
3. 随后进入批次 6B：扩展 Native-source Fidelity 的限定词、范围与状态保持测试，并统一 audit-final / Stage02 的共享审计入口，减少重复实现；
4. Native-source Fidelity 稳定后进入批次 7：`project status` 接入逐页 Stage1 Gate 状态。

# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `5C / 子步骤 2`。

- Final Script 正式 examples 已补充页面级 `source_provenance` 结构示例。
- 新增 `source_provenance_for_page()`，AUTHOR / 测试只能从 passed Author Preflight 页面投影标准 lineage：`packet_sha256 + source_refs + unit_ids`。
- `audit-final` 已在 Author Preflight Gate 通过后继续执行 `validate_final_source_provenance()`；`render-stage02` 在写出前执行同一校验。
- provenance 不一致时 Stage02 返回 `kind=final-source-provenance` 并拒绝输出文件。
- `tests/script_engine/test_cli.py` 的 render / check-sync 正向 fixture 已改为：先生成真实 Page Source Packet + Author Preflight，再由 `source_provenance_for_page()` 写入 Final Script；不再使用静态示例中的占位 hash 通过运行门禁。
- `tests/script_engine/test_quality_policy_cli_integration.py` 的 render advisory 用例已同步迁移到真实 lineage。
- `tests/script_engine/test_authoring_method.py` 中手工构造、预期 schema 合法的内容页已补齐 `source_provenance`。
- 静态 example 保留规范结构示例作用，运行链测试使用动态真实 packet hash，二者职责已经分开。

## 下一步

批次 `5C / 子步骤 3`：运行 PR #34 新一轮 GitHub Actions。

目标：

1. 确认本轮 provenance 契约新增失败归零；
2. 如仍有 fixture 遗漏，只迁移新增失败对应文件；
3. 若仅剩已确认的 3 个 `main` 基线失败，则 5C 完成；
4. 随后进入批次 6：Native-source Fidelity Audit。
# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `5C / 子步骤 1`。

- Final Script 正式 examples 已补充页面级 `source_provenance` 结构示例。
- 新增 `source_provenance_for_page()`，AUTHOR / 测试只能从 passed Author Preflight 页面投影标准 lineage：`packet_sha256 + source_refs + unit_ids`。
- `audit-final` 已在 Author Preflight Gate 通过后继续执行 `validate_final_source_provenance()`，来源链漂移进入 blocking issues。
- `audit-final` 报告新增 `source_provenance_issues`，来源门禁与原有 semantic audit 分层呈现。
- `render-stage02` 已在 schema 校验后、lint 和 Markdown 写出前强制执行同一 provenance 校验。
- provenance 不一致时 `render-stage02` 返回 `kind=final-source-provenance` 并拒绝输出文件。
- 端到端 Gate fixture 已迁移：Preflight 生成后由 `source_provenance_for_page()` 把真实 packet hash / unit ids 写入 Final Script。
- 新增 Stage02 lineage drift 测试：Final Script 将 `SU-001` 篡改为 `SU-999` 时必须阻断。

## 下一步

批次 `5C / 子步骤 2`：迁移现有 render / audit fixtures 并清理 provenance 契约回归。

计划：

1. `tests/script_engine/test_cli.py` 的 render 正向输入改为动态注入当前 Preflight provenance；
2. `tests/script_engine/test_quality_policy_cli_integration.py` 同步迁移；
3. 读取 PR #34 最新 CI，定位所有因内容页缺 `source_provenance` 引起的新失败；
4. 逐项迁移正式 fixtures / tests，不增加 schema fallback 或自动兜底；
5. 本分支新增失败归零后，5C 完成并进入 Native-source Fidelity Audit。
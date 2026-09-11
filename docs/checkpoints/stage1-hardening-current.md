# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `4C-3`。

- PR #34 第二轮 Python 3.12 CI：`3 failed, 2216 passed, 8 skipped, 49 subtests passed`。
- 首轮由 Stage1 hardening 新契约引起的 10 个回归已全部清零。
- 剩余 3 个失败与本批次无关，均已在分支建立前的 `main` 基线出现对应改动：
  - mission / judgment 来源校验；
  - onscreen object code-context 校验；
  - style 09 sample 尺寸。
- Stage1 hardening 不混改这 3 个基线问题。
- Wheel smoke（Windows / macOS）继续通过。
- `page-source → author-preflight → audit-final / render-stage02` 的硬门禁调用迁移已完成，不保留历史兼容入口。

## 下一步

批次 `5A`：把 resolved source unit lineage 纳入 Author Preflight。

计划：

1. 从每个 fresh Page Source Packet 汇总稳定、去重的 `unit_ids`；
2. Author Preflight 每个内容页写入 `unit_ids`；
3. Manifest Schema 将 `unit_ids` 固化为内容页 provenance 基础字段；
4. persisted Manifest 与当前状态比较时同时校验 `unit_ids`；
5. 增加 focused tests，验证 unit lineage 的稳定性和 stale 检测。

完成 5A 后进入 `5B`：Final Script `source_provenance` 数据契约。
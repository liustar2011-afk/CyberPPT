# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `4C-2 / 子步骤 3`。

- 首轮 CI 已完成诊断：13 个失败中，10 个属于本分支新契约迁移，3 个属于当前 main 基线问题。
- `page-source` CLI 旧状态断言已从 `rewrite_required` 迁移到 `blocked`。
- `script_engine/cli.py` 已拆薄，不通过放宽模块化体积阈值解决回归。
- `tests/script_engine/test_cli.py` 的旧 `render-stage02` 调用已迁移：先构造 fresh Page Source Packet + Author Preflight Manifest，再显式提供 `--plan` / `--foundation`。
- `tests/script_engine/test_quality_policy_cli_integration.py` 的 render 正向用例已同步迁移到同一 Stage1 Gate 契约。
- `tests/script_engine/test_stage01_current_entry_convergence.py` 已拆分语义阻断与 Author Preflight Gate 阻断断言；既有 semantic audit 一致性覆盖保留。
- 未增加无 Gate 的兼容路径。

## 下一步

`4C-3`：读取 PR #34 新一轮 GitHub Actions。

目标：

1. 确认本分支新增的 10 个回归是否已归零；
2. 若出现新的 fixture / contract 问题，继续在本分支修复；
3. 新契约回归清零后进入批次 5：Final Script provenance；
4. 当前 main 已存在的 3 个非本批次失败单独记录，不与 Stage1 hardening 混改。

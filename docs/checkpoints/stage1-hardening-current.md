# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `4C-2 / 子步骤 2`。

- 首轮 CI 已完成诊断：13 个失败中，10 个属于本分支新契约迁移，3 个属于当前 main 基线问题。
- `page-source` CLI 旧状态断言已从 `rewrite_required` 迁移到 `blocked`。
- `script_engine/cli.py` 已拆薄，不通过放宽模块化体积阈值解决回归。
- `tests/script_engine/test_cli.py` 的 5 个旧 `render-stage02` 调用已迁移：先构造 fresh Page Source Packet + Author Preflight Manifest，再显式提供 `--plan` / `--foundation`。
- `tests/script_engine/test_quality_policy_cli_integration.py` 的 render 正向用例已同步迁移到同一 Stage1 Gate 契约。
- 未增加无 Gate 的测试旁路或生产兼容入口。

## 下一步

`4C-2 / 子步骤 3`：迁移 final-audit convergence 测试并重新跑 PR CI。

要求：

1. convergence 测试分别断言 semantic issue 与 Author Preflight Gate issue；
2. 不删除既有语义审计覆盖；
3. CI 重新运行后确认本分支新增失败是否归零；
4. 若仍有新增失败，继续逐项迁移后再进入 provenance 改造。

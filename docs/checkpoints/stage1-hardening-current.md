# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到批次 `4C-2 / 子步骤 1`。

- 首轮 CI 已完成诊断：13 个失败中，10 个属于本分支新契约迁移，3 个属于当前 main 基线问题。
- `tests/script_engine/test_page_source_cli.py` 已从旧 `rewrite_required` 契约迁移到 `blocked`。
- `script_engine/cli.py` 已拆薄，删除不必要的 Author Preflight CLI 包装层和冗余适配代码，不通过放宽模块化体积阈值解决回归。

## 下一步

`4C-2 / 子步骤 2`：迁移所有旧 `render-stage02` 测试调用。

要求：

1. 正向 render 测试必须先构造有效 Stage1 Gate；
2. CLI 调用显式提供 `--plan` 与 `--foundation`；
3. quality-policy render 测试同步迁移；
4. 不增加无 Gate 的兼容路径。

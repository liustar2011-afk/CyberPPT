# Foundation 审计 profile 路由验证记录

日期：2026-08-30

## 执行环境

当前 worktree 未配置独立 `.venv`。已确认仓库共享虚拟环境为 `/Volumes/DOC/CyberPPT/.venv/bin/python3`，版本为 Python 3.11.16。测试执行时将当前 worktree 的 `cyberppt` 与 `script_engine` 包置于该解释器的加载首位，确保运行本次修改的源代码。

## 定向回归

执行范围：

- `tests/script_engine/test_cli.py::test_cli_audit_foundation_routes_sibling_source_index_by_project_profile`
- `tests/test_project_status.py::test_strict_status_ignores_stale_script_source_index`
- `tests/test_foundation_authoring.py::test_source_files_to_authored_foundation_passes_schema_and_sibling_index_audit`

结果：`3 passed in 0.12s`。

其中新增 CLI 回归用同一份具有来源 SHA-256 漂移且缺少 `reading_strategy` 的 Foundation 验证两侧行为：

- `profile: strict`：`audit-foundation` 通过，script 专属来源索引校验未参与。
- `profile: script`：`audit-foundation` 失败，输出继续包含 `sha256 differs` 与 `reading_strategy is required for script-profile Foundation`。

## 相关测试文件

执行：`tests/script_engine/test_cli.py`、`tests/test_project_status.py`、`tests/test_foundation_authoring.py`。

结果：`52 passed in 0.40s`。

## 实际项目复验

对 `/Volumes/DOC/CyberPPT/projects/power-supply-demand-forecast-20260830/script/foundation.json` 执行 `audit-foundation`。

结果：

```json
{
  "kind": "foundation-analysis",
  "status": "passed",
  "issues": [],
  "warnings": []
}
```

本次复验为只读审计。该项目的 Deck Plan 与最终脚本未被修改。

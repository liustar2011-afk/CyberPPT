# 总编方法案例库

本目录保存 `status=approved` 的总编方法案例（`ppt-script.editorial-case.v1`）。

- 只能迁移判断方法、结构原则与反模式。
- 禁止写入当前项目主体、数字、日期、能力状态或 Source ID。
- 由 `context-pack` / `editorial-pack` 通过 `build_editorial_case_context()` 按需加载。
- 新增案例后运行相关单测，并确保 `validate_editorial_case()` 无问题。

# Stage2 Artifact Contract v3 最终验收记录

状态：执行中

验收对象：`feature/stage2-artifact-contract-v3`

基线：`main@7bfdf58cf6cbe0317dc038691433dd797d7d6444`

## 验收口径

1. Stage2 v3 七个 Phase 的正式代码、测试与 schema 均保留在 PR #29。
2. 开发期专用 workflow、patch helper、临时 CI trigger 已清理，不进入正式交付范围。
3. Python 3.10 / 3.12 使用失败测试集合与 Phase 1.1 基线做差分；最终要求 `final_failures - baseline_failures = 0`。
4. Windows / macOS wheel smoke 要求保持通过。
5. OfficeCLI smoke 单独核验运行时环境。若同一 OfficeCLI 二进制与同一 fixture 在 hosted runner 因外部 runtime assembly 缺失失败，且 PR changed files 未涉及 OfficeCLI/runtime 链，则按环境异常留痕，不计为 Stage2 v3 代码回归。

## 已确认事实

- Phase 1.1 基线 Python 3.12：67 failed / 1930 passed / 8 skipped / 49 subtests passed。
- Final Compatibility Step A 修复前：49 failed / 1998 passed / 8 skipped / 49 subtests passed。
- 修复前精确差分：新增失败 2 项；已消除基线失败 20 项；公共基线失败 47 项。
- Copy Contract 最终兼容门禁 run `34415399750`：18 passed。
- Copy Contract 最终业务修复提交：`9a380951`。
- 开发脚手架清理提交：`c143be10`。
- OfficeCLI 基线与当前均为 `1.0.145`，fixture 几何校验均有效；已观测失败发生于 hosted runner 加载 `System.Private.Xml 10.0.0.0` 阶段。

## 下一阶段工作

- 以本文件提交后的最终 branch head 执行标准全量矩阵。
- 下载最终 Python pytest artifact，与 Phase 1.1 基线做集合差分。
- 核对最终 changed files 不再包含开发期脚手架。
- 更新本记录为“已完成”，同步 PR checklist 与最终验收评论，并将 PR 转为 Ready for Review。

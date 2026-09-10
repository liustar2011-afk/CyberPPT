# 47 项历史基线失败治理任务

目标：清零 Stage2 v3 合并后仓库仍存在的 47 项历史 Python 测试失败。

基线：`main@366dc81f65f039efdcf48c87e4d132ab5375f6ba`

治理顺序：
1. Track A｜Style Contract / Runtime Lock / Snapshot：18 项。
2. Track B｜ImageGen Prompt / Handoff / Creative Brief：22 项。
3. Track C｜其余仓库合同与模块化：7 项。

完成标准：Python 3.10/3.12 全量测试 0 failed；Windows/macOS wheel 与 OfficeCLI production render smoke 通过；不回退 Stage2 v3 已合并能力；Ready 前清理临时开发脚手架。

## 完成状态

治理任务已完成，47/47 项历史失败全部清零。

- Python 3.10：2048 passed / 8 skipped / 49 subtests passed / 0 failed。
- Python 3.12：2048 passed / 8 skipped / 49 subtests passed / 0 failed。
- Windows wheel smoke：通过。
- macOS wheel smoke：通过。
- OfficeCLI production render smoke：通过；生产固定版本升级至 `1.0.148`。
- 临时兼容矩阵 workflow 与 patch helper：已清理。
- 正式验收：GitHub Actions `CyberPPT tests` #771 / run `34434176927`，结论 `success`。

全过程记录见：`docs/development/baseline-47-regressions-progress.md`。
最终状态见：`docs/development/baseline-47-regressions-status.md`。

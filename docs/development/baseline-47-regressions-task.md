# 47 项历史基线失败治理任务

目标：清零 Stage2 v3 合并后仓库仍存在的 47 项历史 Python 测试失败。

当前基线：`main@366dc81f65f039efdcf48c87e4d132ab5375f6ba`

当前状态：47 failed / 2000 passed / 8 skipped / 49 subtests passed。

治理顺序：
1. Track A｜Style Contract / Runtime Lock / Snapshot：18 项。
2. Track B｜ImageGen Prompt / Handoff / Creative Brief：22 项。
3. Track C｜其余仓库合同与模块化：7 项。

完成标准：Python 3.10/3.12 全量测试 0 failed；Windows/macOS wheel 与 OfficeCLI smoke 保持通过；不回退 Stage2 v3 已合并能力。

全过程记录见：`docs/development/baseline-47-regressions-progress.md`。

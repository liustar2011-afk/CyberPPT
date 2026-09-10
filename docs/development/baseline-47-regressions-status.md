# Baseline Regression Cleanup Status

基线：`main@366dc81f65f039efdcf48c87e4d132ab5375f6ba`

治理分支：`fix/baseline-47-regressions`

最终状态：47 项历史基线失败已全部清零，正式验收通过。

- [x] Step 0｜冻结 47 项失败基线并建立独立治理分支
- [x] Track A｜Style Contract / Runtime Lock / Snapshot（18/18 已清零）
- [x] Track B｜ImageGen Prompt / Handoff / Creative Brief（22/22 已清零）
- [x] Track C｜其余仓库合同与模块化（7/7 已清零）
- [x] Python 3.10 全量 0 failed（2048 passed / 8 skipped / 49 subtests passed）
- [x] Python 3.12 全量 0 failed（2048 passed / 8 skipped / 49 subtests passed）
- [x] Windows/macOS wheel smoke 通过
- [x] OfficeCLI production render smoke 通过（固定版本 `1.0.148`）
- [x] 临时 patch helper / 专用诊断 workflow 已清理

最终正式验收：GitHub Actions `CyberPPT tests` #771 / run `34434176927`，结论 `success`。

OfficeCLI 收口：兼容矩阵确认 `1.0.143` 的单文件发行包在 PPTX→HTML 路径存在 .NET XML 程序集加载失败；`1.0.148` 通过同一生产命令验证，因此生产 pin 升级至 `1.0.148`，并同步六个平台发行资产 SHA-256 与版本回归断言。CI 未放宽、未跳过真实渲染门禁。

当前剩余历史基线失败：0。PR #30 已满足转 Ready for Review 的技术条件。

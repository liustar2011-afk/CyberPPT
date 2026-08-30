# CyberPPT 架构收敛改造记录

本文件记录 2026-08-31 开始的架构收敛工作。每完成一个小阶段即提交，确保中断后可从已提交状态继续。

## 目标

在保持“源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付”正式路线不变的前提下，收敛权威模型、运行状态、兼容层和可复现性边界。

## 已完成

1. `b64fed0 fix(stage02): freeze visual style lock contract`
2. `67586a0 docs(stage01): define canonical authority map`
3. `6862598 feat(stage02): add explicit build state model`
4. `f57692e feat(stage02): separate input fingerprint from run id`
5. `4b5f225 build: define installation capability boundaries`
6. `5948b6c chore: remove root scratch artifacts`
7. `7042e15 feat(script): classify heuristic quality findings`
8. `ebf2f74 fix(stage02): invalidate stale visual artifacts by input identity`
9. `01a95b2 feat(stage02): return expected continuation states`
10. `8062deb feat(stage02): persist expected action state`
11. `ad4a99e build: package production runtime and resources`

## 阶段 12：Compatibility seam 封口

状态：已完成，待本次提交落盘。

改动：

- 新增冻结 dataclass `LegacyPatchSet`，将历史兼容 patch 点固定为 6 个显式字段。
- `final_script_pages` 不再向 compat 函数传递一长串任意 patch keyword，而是构造一个有限 patch set。
- 保留旧 `sync_legacy_patch_points()` 作为向后兼容 wrapper，已有测试 patch `final_script_pages.run_codex_image/ensure_output_size` 仍可工作。
- 新增回归测试锁定兼容面，防止后续继续向 monkey-patch seam 增加新后端依赖。

说明：这一阶段完成“封口”，尚未完全删除 monkey patch。完全删除需要把六个依赖逐步改成 Stage02RunOptions/Dependency Hooks 的显式依赖注入，并同步迁移旧测试；在完成前不做破坏性切换。

## 后续阶段

1. 六个 compat patch 点逐个迁移为显式 dependency hooks，最终删除 monkey patch wrapper。
2. wheel 环境最小无外网 Stage 01→Stage 02 fixture build。
3. macOS/Windows Office/render 集成 CI。

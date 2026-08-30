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

## 阶段 7：deterministic semantic gate 分级

状态：已完成，待本次提交落盘。

改动：

- 新增 `script_engine.quality_policy`，显式区分 blocker 与 advisory。
- Schema/结构/未知新规则默认 blocker，保持 fail-closed。
- 首批将依赖措辞正则的 `AUTHOR_MISSION_GENERIC`、`AUTHOR_VISUAL_THESIS_NONRELATIONAL`、`AUTHOR_VISUAL_TOPOLOGY_CONFLICT` 定义为 advisory。
- 新增 `docs/SCRIPT_QUALITY_SEVERITY_POLICY.md` 和回归测试。
- 原有 `lint` 主命令暂不改变退出语义；可以先使用 `python -m script_engine.quality_policy <final-script.json>` 观察分级结果，再在覆盖充分后接入主门禁。

## 暂缓：compatibility facade 单向化

当前 `final_script_pages.py -> compat.sync_legacy_patch_points()` 仍承担旧测试/调用的 monkey-patch seam。在未建立完整调用面回归测试前直接删除风险过高，后续先锁定调用者再迁移。

## 后续阶段

1. compatibility facade 调用面测试与单向化。
2. 正式 runtime package 化与 wheel 安装 smoke test。
3. 将 Stage 02 状态模型接入主 orchestrator，逐步减少 expected-action exception。

# CyberPPT 架构收敛改造记录

本文件记录 2026-08-31 开始的架构收敛工作。每完成一个小阶段即提交，确保中断后可从已提交状态继续。

## 目标

在保持“源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付”正式路线不变的前提下，收敛权威模型、运行状态、兼容层和可复现性边界。

## 已完成

1. `b64fed0 fix(stage02): freeze visual style lock contract`
   - Style 09 lock 改为创建时合同快照。
2. `67586a0 docs(stage01): define canonical authority map`
   - 定义 Stage 01/02 唯一可写权威与 projection 边界。
3. `6862598 feat(stage02): add explicit build state model`
   - 增加 Stage 02 正常待办/真实失败状态分类。
4. `f57692e feat(stage02): separate input fingerprint from run id`
   - 分离稳定 input fingerprint 与每次执行 run id。

## 阶段 5：安装与能力边界

状态：已完成，待本次提交落盘。

改动：

- 将 Pillow 从隐式传递依赖提升为直接依赖。
- 增加 `source` extra：`openpyxl` + `markitdown`，与 source extractor 的实际可选能力一致。
- 增加 `dev` extra，CI 统一安装 source + test 能力。
- CI 增加正式 Stage 02 runtime import smoke test。
- 新增 `docs/INSTALLATION_CAPABILITIES.md`，明确当前正式支持形态仍是 repository editable install；暂不虚假宣称 wheel 已能脱离 `scripts/`、`references/`、`assets/` 独立运行。

## 暂缓：compatibility facade 单向化

当前 `final_script_pages.py -> compat.sync_legacy_patch_points()` 仍承担旧测试/调用的 monkey-patch seam。在未建立完整调用面回归测试前直接删除风险过高，后续先锁定调用者再迁移。

## 后续阶段

1. deterministic semantic gate 分级。
2. compatibility facade 调用面测试与单向化。
3. 正式 runtime package 化与 wheel 安装 smoke test。

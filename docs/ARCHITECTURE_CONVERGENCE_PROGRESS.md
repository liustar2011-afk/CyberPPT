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
5. `4b5f225 build: define installation capability boundaries`
   - 明确 repository editable install、直接/可选依赖和 CI runtime import 检查。

## 阶段 6：仓库卫生清理

状态：已完成，待本次提交落盘。

改动：

- 删除根目录 `out.txt`、`tmp_p15_prompt_after.md`、`tmp_source_text.txt` 临时产物。
- `.gitignore` 增加根目录 `/tmp_*` 与 `/out.txt`，避免实验材料重新进入正式代码面。

## 暂缓：compatibility facade 单向化

当前 `final_script_pages.py -> compat.sync_legacy_patch_points()` 仍承担旧测试/调用的 monkey-patch seam。在未建立完整调用面回归测试前直接删除风险过高，后续先锁定调用者再迁移。

## 后续阶段

1. deterministic semantic gate 分级。
2. compatibility facade 调用面测试与单向化。
3. 正式 runtime package 化与 wheel 安装 smoke test。

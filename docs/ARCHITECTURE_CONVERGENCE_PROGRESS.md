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

## 阶段 9：Stage 02 状态模型接入主 orchestrator

状态：已完成，待本次提交落盘。

改动：

- `run_production()` 在 reconstruction 抛错后读取已持久化 manifest 的正式状态模型。
- 只有状态模型确认 `needs_action` 时，才把异常转换成正常的 `Stage02ProductionResult(status=needs_action)`；真实 failure 继续抛出，保持 fail-closed。
- `needs_action` 结果生成 `stage02_needs_action.json`，列出页面、action、preview 等续跑信息。
- 首先覆盖缺 authored SVG、待 Quick visual review 等现有 expected-action 场景，不修改 Quick runtime 本身。

这一步使 Stage 02 开始从“异常驱动工作流”迁移为“状态驱动工作流”，同时保留旧运行时和真实错误语义。

## 暂缓：compatibility facade 单向化

已确认 `tests/test_final_script_pages.py` 直接 patch `cyberppt.commands.final_script_pages.run_codex_image/ensure_output_size`，当前 monkey-patch seam 仍有真实兼容调用。后续删除前必须先迁移这些测试/调用到显式 dependency hooks。

## 后续阶段

1. compatibility facade dependency hooks 与单向化。
2. 正式 runtime package 化与 wheel 安装 smoke test。
3. 将更多 Stage 02 expected-action 写入 artifact ledger/build context，而不是仅写状态回执。

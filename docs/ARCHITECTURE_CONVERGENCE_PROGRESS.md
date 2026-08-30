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

## 阶段 10：Expected action 持久化

状态：已完成，待本次提交落盘。

改动：

- `needs_action` 除了写独立 `stage02_needs_action.json`，同时写回当前 `build_context.json`。
- build context 保存完整 `stage02_state` 和 `artifacts.needs_action.path`。
- 即使会话或 Agent 进程终止，下一次运行也可以直接从 build 目录判断缺哪个 authored SVG、哪一页等待 visual review。
- 新增回归测试验证状态回执与 build context 同步落盘。

## 暂缓：compatibility facade 单向化

已确认 `tests/test_final_script_pages.py` 直接 patch `cyberppt.commands.final_script_pages.run_codex_image/ensure_output_size`，当前 monkey-patch seam 仍有真实兼容调用。后续删除前必须先迁移这些测试/调用到显式 dependency hooks。

## 后续阶段

1. compatibility facade dependency hooks 与单向化。
2. 正式 runtime package 化与 wheel 安装 smoke test。

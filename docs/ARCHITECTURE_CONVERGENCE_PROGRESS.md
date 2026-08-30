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

## 阶段 8：Stage 02 视觉资产精确失效

状态：已完成，待本次提交落盘。

改动：

- 正式 manifest 恢复只在 `input_fingerprint` 完全一致时复用旧 authored SVG、clean base、graphic text policy、Quick checkpoint 和 audited full 图状态。
- audited full 图的文字审计只有在当前 Prompt SHA 与实际生成 Prompt SHA 一致时才允许带入新 manifest。
- partial page recovery 只有在相同 input fingerprint 下才能保留未选中页面，防止 style/visual spec/model 参数变化后把旧页混入新 build。
- 新增回归测试覆盖 fingerprint 改变、Prompt 改变和 partial recovery 三种失效情况。

兼容说明：低层 `_generate_manifest_images` helper 仍保留“直接传入旧 manifest 时可复用 audited full”的历史行为，因为现有测试和旧调用依赖它；正式 `final-script-pages` 主链已经在 manifest 边界阻止 stale prompt/input 复用。

## 暂缓：compatibility facade 单向化

已确认 `tests/test_final_script_pages.py` 直接 patch `cyberppt.commands.final_script_pages.run_codex_image/ensure_output_size`，当前 monkey-patch seam 仍有真实兼容调用。后续删除前必须先迁移这些测试/调用到显式 dependency hooks。

## 后续阶段

1. compatibility facade dependency hooks 与单向化。
2. 正式 runtime package 化与 wheel 安装 smoke test。
3. 将 Stage 02 状态模型接入主 orchestrator，逐步减少 expected-action exception。

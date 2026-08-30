# CyberPPT 架构收敛改造记录

本文件记录 2026-08-31 开始的架构收敛工作。每完成一个小阶段即提交，确保中断后可从已提交状态继续。

## 目标

在保持“源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付”正式路线不变的前提下，收敛权威模型、运行状态、兼容层和可复现性边界。

## 阶段 1：Style Lock 真冻结

状态：已完成。

提交：`b64fed0 fix(stage02): freeze visual style lock contract`

## 阶段 2：Stage 01 Authority Map

状态：已完成。

提交：`67586a0 docs(stage01): define canonical authority map`

权威定义见 `docs/CYBERPPT_AUTHORITY_MAP.md`。

## 阶段 3：Stage 02 正式状态模型

状态：已完成，待本次提交落盘。

改动：

- 新增 `cyberppt.stage02_production.state`，对现有 manifest 做确定性状态分类。
- 明确区分 `needs_image_generation`、`needs_svg_authoring`、`needs_visual_review`、`visual_review_failed`、`page_ready_for_assembly` 与真实 `failed`。
- 缺 authored SVG 和等待 Quick 视觉审核不再需要由上层根据异常文案猜测业务含义；可直接执行：
  `python -m cyberppt.stage02_production.state <page_image_pairs.json>`。
- 新增回归测试，保证“正常待办”不会被分类为 terminal failure。

说明：本阶段先建立兼容现有 manifest 的一等状态模型，不改写现有生产编排异常行为；下一次 Stage 02 编排收敛可直接消费该状态模型，避免一次性大改 Quick runtime。

后续阶段：

1. compatibility facade 单向化，移除内部 monkey patch。
2. deterministic semantic gate 分级。
3. Python 安装边界、extras 与 wheel smoke test。
4. `input_fingerprint` 与 `run_id` 分离。

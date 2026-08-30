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

状态：已完成。
提交：`6862598 feat(stage02): add explicit build state model`

可执行 `python -m cyberppt.stage02_production.state <page_image_pairs.json>` 区分正常待办和真实失败。

## 阶段 4：input_fingerprint 与 run_id 分离

状态：已完成，待本次提交落盘。

改动：

- 新增 `cyberppt.stage02_production.identity`。
- `input_fingerprint` 仅由会影响生产结果的输入构成：脚本/Stage02 intake/visual spec/style lock 哈希、页面集合、production/assembly mode、ImageGen model/quality、prompt enrich 与 prompt edit 策略。
- `build_id` 继续承担每次执行的 run identity；manifest/build context 同时写入 `run_id` 和稳定的 `input_fingerprint`。
- 相同输入在不同时间运行可以拥有不同 run id，但得到相同 input fingerprint；为后续缓存、精确失效和跨 run 对比提供稳定键。

## 暂缓：compatibility facade 单向化

当前 `final_script_pages.py -> compat.sync_legacy_patch_points()` 仍承担旧测试/调用的 monkey-patch seam。在未建立完整调用面回归测试前直接删除风险过高，因此本轮不做破坏性移除。后续先锁定调用者，再迁移为单向参数 adapter。

后续阶段：

1. deterministic semantic gate 分级。
2. Python 安装边界、extras 与 wheel/repository smoke test。
3. compatibility facade 调用面测试与单向化。

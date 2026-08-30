# CyberPPT 架构收敛改造记录

本文件记录 2026-08-31 开始的架构收敛工作。每完成一个小阶段即提交，确保中断后可从已提交状态继续。

## 目标

在保持“源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付”正式路线不变的前提下，收敛权威模型、运行状态、兼容层和可复现性边界。

## 阶段 1：Style Lock 真冻结

状态：已完成。

提交：`b64fed0 fix(stage02): freeze visual style lock contract`

改动：

- Style 09 live visual contract 只在创建 `visual_style_lock.json` 时解析一次。
- `load_style_lock()` 不再从 `references/visual-system.md` 动态刷新 Style 09。
- 新锁写入 `resolved_contract.mode=snapshot`、合同 SHA-256 和 `resolved_contract_is_immutable=true`。
- 新增回归测试，验证旧锁在 `visual-system.md` 变化后仍保持原合同，新建锁能够取得新版本合同。

## 阶段 2：Stage 01 Authority Map

状态：已完成，待本次提交落盘。

改动：

- 新增 `docs/CYBERPPT_AUTHORITY_MAP.md`，明确 Source、Semantic、Foundation、Deck Plan、Final Script、Stage 02 Visual Authority 的唯一修改入口。
- Strict 当前主链统一将 `semantic-argument-model.json` 定义为 whole-document 单一可写语义权威。
- `source-truth.json` 明确为 deterministic projection；Foundation 明确为 PLAN/AUTHOR 合同。
- `normalized-facts / concept-base / relation-graph / argument-chain` 在 deeper source-foundation 路线中保留为受控语义工作产物，但不再描述成与 semantic model 并行的下游可写权威。
- 更新 `cyberppt-source-foundation` Skill，消除旧文案中“同一文件既是 canonical 又是 compatibility projection”的冲突。

后续阶段：

1. Stage 02 正式状态机，区分正常待办与真实失败。
2. compatibility facade 单向化，移除内部 monkey patch。
3. deterministic semantic gate 分级。
4. Python 安装边界、extras 与 wheel smoke test。
5. `input_fingerprint` 与 `run_id` 分离。

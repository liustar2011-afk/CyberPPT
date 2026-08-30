# CyberPPT 架构收敛改造记录

本文件记录 2026-08-31 开始的架构收敛工作。每完成一个小阶段即提交，确保中断后可从已提交状态继续。

## 目标

在保持“源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付”正式路线不变的前提下，收敛权威模型、运行状态、兼容层和可复现性边界。

## 阶段 1：Style Lock 真冻结

状态：已完成，待本次提交落盘。

改动：

- Style 09 的 live visual contract 只在创建 `visual_style_lock.json` 时解析一次。
- `load_style_lock()` 不再从 `references/visual-system.md` 动态刷新 Style 09。
- 新锁写入 `resolved_contract.mode=snapshot`、合同 SHA-256 和 `resolved_contract_is_immutable=true`。
- 新增回归测试，验证旧锁在 `visual-system.md` 变化后仍保持原合同，新建锁能够取得新版本合同。

目的：

- 让 style lock 的文件 SHA 真正代表生产所消费的视觉合同。
- 避免视觉规范变更导致旧 build 在输入身份未变化的情况下产生不同 Prompt。

后续阶段：

1. Stage 01 Authority Map 与权威命名收敛。
2. Stage 02 正式状态机，区分正常待办与真实失败。
3. compatibility facade 单向化，移除内部 monkey patch。
4. deterministic semantic gate 分级。
5. Python 安装边界、extras 与 wheel smoke test。
6. `input_fingerprint` 与 `run_id` 分离。

# CyberPPT 架构收敛恢复点（阶段 66+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_50PLUS.md`。恢复时以 GitHub `main` 的实际 commit 和 workflow 结果为准。

| 阶段 | Commit | 内容 |
|---|---|---|
| 66 | `ced0b7cec3a47bb94eb09f7b68a473e063fd10b6` | 新增 `analysis_audits/final_lean.py`，将 lean Deck Plan 下的 AUTHOR source-consumption、onscreen/full-copy 对齐和 relationship visibility helper 迁入 focused module；`final_script_runtime.py` 将 legacy orchestrator 的同名全局绑定到 focused 实现。首次 CI 暴露 `_RELATIONSHIP_CLAIM_RE` 私有依赖缺失，补齐后恢复兼容。实现提交：`d563c45`、`3baf9a7`、`392658f`、`ced0b7c` |
| 67 | `9f5d2ff80be42620387971483928b9716b79750a` | 新增 `analysis_audits/final_onscreen.py`，迁移 onscreen composition、semantic payload、self-reading density 和 onscreen contract 四类 helper；runtime router 扩展为 authoring/lean/onscreen 三组 focused authority，legacy `audit_final_script` 主循环保持不变。实现提交：`8339530`、`60b6d9e`、`9f5d2ff` |

## 验证记录

- 阶段 66 workflow run `33370286211`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；修复后 source-consumption、protected number/status preservation 和 relationship visibility finding 保持兼容。
- 阶段 67 workflow run `33372782615`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；onscreen composition/density/contract runtime authority 迁移后 finding 与公开 facade 行为保持兼容。

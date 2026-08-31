# CyberPPT 架构收敛恢复点（阶段 66+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_50PLUS.md`。恢复时以 GitHub `main` 的实际 commit 和 workflow 结果为准。

| 阶段 | Commit | 内容 |
|---|---|---|
| 66 | `ced0b7cec3a47bb94eb09f7b68a473e063fd10b6` | 新增 `analysis_audits/final_lean.py`，将 lean Deck Plan 下的 AUTHOR source-consumption、onscreen/full-copy 对齐和 relationship visibility helper 迁入 focused module；`final_script_runtime.py` 将 legacy orchestrator 的同名全局绑定到 focused 实现。首次 CI 暴露 `_RELATIONSHIP_CLAIM_RE` 私有依赖缺失，补齐后恢复兼容。实现提交：`d563c45`、`3baf9a7`、`392658f`、`ced0b7c` |
| 67 | `9f5d2ff80be42620387971483928b9716b79750a` | 新增 `analysis_audits/final_onscreen.py`，迁移 onscreen composition、semantic payload、self-reading density 和 onscreen contract 四类 helper；runtime router 扩展为 authoring/lean/onscreen 三组 focused authority，legacy `audit_final_script` 主循环保持不变。实现提交：`8339530`、`60b6d9e`、`9f5d2ff` |
| 68 | `8a08381cf23463e407801d825367e58023536207` | 新增 `analysis_audits/final_deck.py`，迁移 source text 聚合、章节标题归一化和 whole-deck authoring warnings；runtime router 扩展为 authoring/lean/onscreen/deck 四组 focused helper authority，逐页主审计循环保持不变。实现提交：`42c7134`、`db700ba`、`8a08381` |
| 69 | `3aff0fe2040fbe1904cbfbe004c839f3518d1256` | 新增 `analysis_audits/final_orchestrator.py`，将 `audit_final_script()` 主审计编排迁入 focused orchestrator；runtime facade 将 legacy `audit_final_script` 指向 focused 函数，helper finding 顺序、文案和公开 facade API 保持不变。实现提交：`706249c`、`80493ed`、`3aff0fe` |

## 验证记录

- 阶段 66 workflow run `33370286211`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；修复后 source-consumption、protected number/status preservation 和 relationship visibility finding 保持兼容。
- 阶段 67 workflow run `33372782615`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；onscreen composition/density/contract runtime authority 迁移后 finding 与公开 facade 行为保持兼容。
- 阶段 68 workflow run `33373004033`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；deck-level source aggregation、chapter-title normalization 和 whole-deck warnings 迁出后结果与公开对象身份保持兼容。
- 阶段 69 workflow run `33373253000`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；focused `audit_final_script()` 成为正式 runtime authority 后 finding 顺序、报告语义和 compatibility facade 行为保持兼容。

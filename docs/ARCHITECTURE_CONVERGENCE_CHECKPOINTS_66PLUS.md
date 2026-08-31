# CyberPPT 架构收敛恢复点（阶段 66+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_50PLUS.md`。恢复时以 GitHub `main` 的实际 commit 和 workflow 结果为准。

| 阶段 | Commit | 内容 |
|---|---|---|
| 66 | `ced0b7cec3a47bb94eb09f7b68a473e063fd10b6` | 新增 `analysis_audits/final_lean.py`，将 lean Deck Plan 下的 AUTHOR source-consumption、onscreen/full-copy 对齐和 relationship visibility helper 迁入 focused module；`final_script_runtime.py` 将 legacy orchestrator 的同名全局绑定到 focused 实现。首次 CI 暴露 `_RELATIONSHIP_CLAIM_RE` 私有依赖缺失，补齐后恢复兼容。实现提交：`d563c45`、`3baf9a7`、`392658f`、`ced0b7c` |
| 67 | `9f5d2ff80be42620387971483928b9716b79750a` | 新增 `analysis_audits/final_onscreen.py`，迁移 onscreen composition、semantic payload、self-reading density 和 onscreen contract 四类 helper；runtime router 扩展为 authoring/lean/onscreen 三组 focused authority，legacy `audit_final_script` 主循环保持不变。实现提交：`8339530`、`60b6d9e`、`9f5d2ff` |
| 68 | `8a08381cf23463e407801d825367e58023536207` | 新增 `analysis_audits/final_deck.py`，迁移 source text 聚合、章节标题归一化和 whole-deck authoring warnings；runtime router 扩展为 authoring/lean/onscreen/deck 四组 focused helper authority，逐页主审计循环保持不变。实现提交：`42c7134`、`db700ba`、`8a08381` |
| 69 | `3aff0fe2040fbe1904cbfbe004c839f3518d1256` | 新增 `analysis_audits/final_orchestrator.py`，将 `audit_final_script()` 主审计编排迁入 focused orchestrator；runtime facade 将 legacy `audit_final_script` 指向 focused 函数，helper finding 顺序、文案和公开 facade API 保持不变。实现提交：`706249c`、`80493ed`、`3aff0fe` |
| 70 | `0a2d1df516138b8362d53de832bc2accd0535d4b` | 将约 47.9KB 的 `analysis_audits/final_script.py` 收缩为无函数/类实现的 thin compatibility facade，全部公开 helper 与 `audit_final_script` 直接 re-export focused modules；保留历史私有 `_status_strength_preserved`、状态/结构正则常量与 `_onscreen_surface` 属性，并新增 AST/文件体量门禁禁止重复实现回流。实现提交：`433ae43`、`0a2d1df` |
| 71 | `bc350a7f573e3493be11667986d35caec9e72fa9` | 将 `analysis_audits/final_script_runtime.py` 从动态 rebinding router 收缩为静态显式 re-export facade；移除 focused-module fan-in、`setattr()` 与 `globals()` 修改，只保留历史 runtime import path 兼容，并以 AST 门禁禁止动态路由回流。实现提交：`97c85b8`、`bc350a7` |
| 72 | `4c4f4e65a1e9085a2bf940344de018115dee983e` | 新增 `analysis_audits/common_primitives.py`，迁移 source/evidence 常量、Foundation item 索引、可见性、optionality/group-strength、page evidence refs、source-consumption、source surface 和 page text 等底层 primitives；`common.py` 保留原 `__all__` 并仅自有 4 个高层 contract validator。实现提交：`fa035a0`、`09eee81`、`4c4f4e6` |

## 验证记录

- 阶段 66 workflow run `33370286211`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；修复后 source-consumption、protected number/status preservation 和 relationship visibility finding 保持兼容。
- 阶段 67 workflow run `33372782615`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；onscreen composition/density/contract runtime authority 迁移后 finding 与公开 facade 行为保持兼容。
- 阶段 68 workflow run `33373004033`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；deck-level source aggregation、chapter-title normalization 和 whole-deck warnings 迁出后结果与公开对象身份保持兼容。
- 阶段 69 workflow run `33373253000`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；focused `audit_final_script()` 成为正式 runtime authority 后 finding 顺序、报告语义和 compatibility facade 行为保持兼容。
- 阶段 70 workflow run `33373574401`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；legacy `final_script.py` 清空重复实现后，公开 `__all__`、历史私有属性、direct import 与正式审计行为保持兼容。
- 阶段 71 workflow run `33373849896`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；runtime 动态 rebinding 完全移除后，历史 import path、公开 API 对象身份和正式审计行为保持兼容。
- 阶段 72 workflow run `33374386175`：五个 job 全部 `success`。Linux Python 3.10/3.12 全量 pytest、macOS/Windows wheel smoke 与 OfficeCLI 真实渲染均通过；common primitives 迁出后，所有 `.common import *` 消费者、历史 `common.__all__` 和审计 finding 行为保持兼容。

# CyberPPT 架构收敛恢复点（阶段 50+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_30PLUS.md`。继续执行“每完成一个小阶段立即提交并记录恢复点”。

| 阶段 | Commit | 内容 |
|---|---|---|
| 50 | `bccc2e022c2a3da2c63c1ea5214c4b6dc7a8940f` | 将 banned-phrasing 读取、Final Script 全字段遍历和 `lint_final_script` 组合器迁入 `lint_contracts.py`；主 CLI/quality policy 继续通过 `contracts` facade 调用，AUTHOR/full-copy/onscreen 子检查暂时由旧 `contract_rules.py` 提供。实现提交：`faebb81`、`7765133`、`bccc2e0` |
| 51 | `f8f8b81ef2412106cf6b5a451fac7fdc4d3974b7` | 新增共享 `semantic_text_primitives.py`，并将 mission/argument/visual_thesis/relationships/speaker_notes 的 AUTHOR supporting-field 机械合同迁入 `author_contracts.py`；`lint_contracts` 与 `contracts` facade 已切换到 focused implementation。实现提交：`2612508`、`bc4f33f`、`555980e`、`6f90f91`、`f8f8b81` |
| 52 | `b1812c48ad5f3096c043f0480c95acf31f1ecc9a` | 将 full-copy 段落结构、段首语义完整性和显式并列分支子结论三类检查迁入 `full_copy_contracts.py`，复用共享 semantic text primitives；`lint_contracts` 与 `contracts` facade 已切换到 focused implementation，并以架构测试锁定公共出口。实现提交：`2204cdc`、`9c56549`、`5cdc4d3`、`b1812c4` |
| 53 | `bf016b2065ca0a62e16afa64a5ed80e744bd82ff` | 将 onscreen 标题语义、细项语义、证据层、层级标点、代码自解释和 core_message 可见投影六类检查迁入 `onscreen_contracts.py`，统一复用共享 semantic text primitives；`lint_contracts` 与 `contracts` facade 已切换到 focused implementation，并以架构测试锁定公共出口。实现提交：`eaa179f`、`c33ea96`、`69f9ec2`、`bf016b2` |

## 验证记录

- 阶段 50 workflow run `33362154737`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；`lint_final_script` 调度迁移后 banned-phrasing 命中、severity policy 和 CLI 退出语义保持兼容。
- 阶段 51 workflow run `33362447591`：五个 job 全部 `success`。AUTHOR supporting-field 迁移后全量测试、三平台 wheel smoke 与 OfficeCLI 真实渲染均通过；`AUTHOR_MISSION_GENERIC`、`AUTHOR_VISUAL_THESIS_NONRELATIONAL`、`AUTHOR_VISUAL_TOPOLOGY_CONFLICT` 的 advisory 分类保持原行为。
- 阶段 52 workflow run `33362901587`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；full-copy focused module、lint 调度和 facade 公共导出切换后保持现有 deterministic finding 与退出语义兼容。
- 阶段 53 workflow run `33363190081`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；onscreen focused module、lint 调度和 facade 公共导出切换后保持现有 deterministic finding 与退出语义兼容。

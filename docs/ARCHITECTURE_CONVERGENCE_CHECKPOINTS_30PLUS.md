# CyberPPT 架构收敛恢复点（阶段 30+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_PROGRESS.md`。从阶段 30 起继续保持“每完成一个小阶段立即提交并记录恢复点”。

| 阶段 | Commit | 内容 |
|---|---|---|
| 30 | `7cfe3e75fe84f13f10e3f3465fddab0cf36ae4b3` | 禁止 pytest 重复收集 `_FinalScriptPagesTestsBase`；仅现代 wrapper 收集，保留真实 PNG 局部纠错覆盖 |
| 31 | `706d42d78fef18ebec89558ca9e96adbc179fb54` | Creative-brief 测试从旧精确句迁移到当前 Style09 hierarchy 不变量，并继续验证正文结论约束与 terminal lock 绝对末尾 |
| 32 | `d0adcbe652ac459bf96f31753d381764d4cdc404` | No-visual-structure 测试迁移到当前章节名；Style10 alias 与 Style09 归一为同一 art direction，继续逐项验证结构不受旧调用 ID 影响 |

当前验证基线：阶段 28 workflow run `33341432628` 的 Python 3.12 为 6 failed、1776 passed、8 skipped；其中 Style09 安全规则已由阶段 29 修复，旧纠错基类重复收集已由阶段 30 修复，creative-brief 历史 hierarchy 句由阶段 31 修复，no-visual-structure 两项由阶段 32 修复。

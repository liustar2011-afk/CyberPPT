# CyberPPT 架构收敛恢复点（阶段 30+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_PROGRESS.md`。从阶段 30 起继续保持“每完成一个小阶段立即提交并记录恢复点”。

| 阶段 | Commit | 内容 |
|---|---|---|
| 30 | `7cfe3e75fe84f13f10e3f3465fddab0cf36ae4b3` | 禁止 pytest 重复收集 `_FinalScriptPagesTestsBase`；仅现代 wrapper 收集，保留真实 PNG 局部纠错覆盖 |

当前验证基线：阶段 28 workflow run `33341432628` 的 Python 3.12 为 6 failed、1776 passed、8 skipped；其中 Style09 安全规则已由阶段 29 修复，旧纠错基类重复收集已由阶段 30 修复。

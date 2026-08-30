# CyberPPT 架构收敛恢复点（阶段 30+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_PROGRESS.md`。从阶段 30 起继续保持“每完成一个小阶段立即提交并记录恢复点”。

| 阶段 | Commit | 内容 |
|---|---|---|
| 30 | `7cfe3e75fe84f13f10e3f3465fddab0cf36ae4b3` | 禁止 pytest 重复收集 `_FinalScriptPagesTestsBase`；仅现代 wrapper 收集，保留真实 PNG 局部纠错覆盖 |
| 31 | `706d42d78fef18ebec89558ca9e96adbc179fb54` | Creative-brief 测试从旧精确句迁移到当前 Style09 hierarchy 不变量，并继续验证正文结论约束与 terminal lock 绝对末尾 |
| 32 | `d0adcbe652ac459bf96f31753d381764d4cdc404` | No-visual-structure 测试迁移到当前章节名；Style10 alias 与 Style09 归一为同一 art direction，继续逐项验证结构不受旧调用 ID 影响 |
| 33 | `c61bcf77cbb69988f1568a04b1e7d05549ce424a` | Page-manifest Style09 测试迁移到当前三个合同章节名；保留语义适配、元数据泄漏防护、terminal lock 唯一与 handoff consumed 检查 |
| 34 | `1e1f9e8ad5a810c26da2afa4ec9f10a444e41a87` | 修复 wheel package-data 漏项：纳入 `scripts/image_to_pptx_runtime/pptx_shapes/data/*`，并强化 repo 外 smoke，显式校验 presetShapeDefinitions.xml 与 shape_type_values.txt |

阶段 33 后 workflow run `33341756404` 已确认 Python 3.10/3.12 的 pytest 全绿；Python 3.12 精确结果为 1760 passed、8 skipped、22 warnings、49 subtests passed。该 run 唯一失败发生在 wheel 安装后的 repo 外 smoke：`shape_type_values.txt` 未打包。阶段 34 已针对该精确 FileNotFoundError 修复，并同时纳入同目录的 XML/许可/NOTICE 资源。下一步以阶段 34 后 GitHub Actions 同时通过 pytest、wheel build 和 repo 外 import/resource smoke 为准。

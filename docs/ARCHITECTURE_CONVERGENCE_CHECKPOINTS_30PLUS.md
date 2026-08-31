# CyberPPT 架构收敛恢复点（阶段 30+）

本文件续接 `docs/ARCHITECTURE_CONVERGENCE_PROGRESS.md`。从阶段 30 起继续保持“每完成一个小阶段立即提交并记录恢复点”。

| 阶段 | Commit | 内容 |
|---|---|---|
| 30 | `7cfe3e75fe84f13f10e3f3465fddab0cf36ae4b3` | 禁止 pytest 重复收集 `_FinalScriptPagesTestsBase`；仅现代 wrapper 收集，保留真实 PNG 局部纠错覆盖 |
| 31 | `706d42d78fef18ebec89558ca9e96adbc179fb54` | Creative-brief 测试从旧精确句迁移到当前 Style09 hierarchy 不变量，并继续验证正文结论约束与 terminal lock 绝对末尾 |
| 32 | `d0adcbe652ac459bf96f31753d381764d4cdc404` | No-visual-structure 测试迁移到当前章节名；Style10 alias 与 Style09 归一为同一 art direction，继续逐项验证结构不受旧调用 ID 影响 |
| 33 | `c61bcf77cbb69988f1568a04b1e7d05549ce424a` | Page-manifest Style09 测试迁移到当前三个合同章节名；保留语义适配、元数据泄漏防护、terminal lock 唯一与 handoff consumed 检查 |
| 34 | `1e1f9e8ad5a810c26da2afa4ec9f10a444e41a87` | 修复 wheel package-data 漏项：纳入 `scripts/image_to_pptx_runtime/pptx_shapes/data/*`，并强化 repo 外 smoke，显式校验 presetShapeDefinitions.xml 与 shape_type_values.txt |
| 35 | `fa8370e5260849d54b9f26f2ea0f3be80e85ca73` | 完成 image-to-pptx runtime 数据资源打包：纳入 `pptx_animation_presets.json` 与 `svg_editor/static/*`；repo 外 smoke 新增 203 个原生动画预设加载校验及 SVG Editor 三项静态资源存在性校验 |
| 36 | `2300a0cdb7752617281034ef793652c89aa48e62` | 重写 `references/visual-system.md` 为当前架构说明：Style09 纯白 + 深蓝为正式生产风格，registry snapshot 为唯一执行权威，Style10 仅 legacy alias，历史 Style1–8 仅保留探索/兼容定位 |

## 验证记录

- 阶段 33 后 workflow run `33341756404`：Python 3.10/3.12 pytest 首次全绿；Python 3.12 精确结果为 1760 passed、8 skipped、22 warnings、49 subtests passed。该轮仅 wheel repo 外 smoke 因资源漏包失败。
- 阶段 34 后 workflow run `33342016028`：Python 3.10/3.12 pytest 与 wheel build 全绿；repo 外 smoke 成功越过 preset-shape 数据，随后暴露 `pptx_animation_presets.json` 漏包。
- 阶段 35 后 workflow run `33348212625`：结论 `success`。Python 3.10/3.12 pytest、runtime import、wheel build、离开仓库目录后的 wheel import/resource smoke 全部通过。Stage 02 wheel 已确认可加载 preset-shape 数据、203 个原生动画预设和 SVG Editor 静态资源。
- 阶段 36 只修改说明文档，不改变 registry、Style Lock 或 Prompt bytes；下一步以该提交 CI 保持全绿为前提继续 compatibility seam / quality policy 收敛。

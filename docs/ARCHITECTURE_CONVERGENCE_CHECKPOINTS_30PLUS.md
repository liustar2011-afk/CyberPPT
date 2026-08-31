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
| 37 | `3aaf5cd2b3121ce06064d875ed5b74f77b9b0d60` | 开始拆除 Stage02 monkey-patch seam：新增 `Stage02Dependencies`，`require_generated` 由 orchestrator 显式依赖注入；旧 facade patch 仍通过 dependency object 兼容传入。前置安全提交：`70d34a2`、`c850214` |
| 38 | `ffb96a2626e77775cb6bdf5ebbf4a90710429bde` | Reconstruction build、OfficeCLI render QA、artifact ledger append 三个后端改为显式依赖注入；compat 不再修改 orchestrator/reconstruction/delivery 模块全局。阶段实现提交：`81f0ba9`、`ba52834`、`966d011`、`5d767a3`、`f33f3cd`、`9b38f81` |
| 39 | `84bc433b654b7f4707a9bfe9800b5e0a4e431c9b` | 完成最后两个 ImageGen backend 的显式依赖迁移；`LegacyPatchSet` 六字段仅转换为 `Stage02Dependencies`，不再修改任何生产模块全局。实现提交：`cd11565`、`603aedf`、`3b810cd`、`7438012`；测试夹具迁移：`84bc433` |
| 40 | `fd02d6bff1126493aa1a620c97ff5fa604c33c5a` | 将 Script QA blocker/advisory severity policy 正式接入 `lint`、`status`、`render-stage02`、`check-sync`；仅三类措辞/视觉语法启发式降为 advisory，未知 finding 继续 fail-closed。实现提交：`ec94dc7`、`947e40f`、`f7aad7b`、`fd02d6b`；策略文档更新：`81b3073` |
| 41 | `7a23c8642f076c7c48589d07ef49e6e0fc826413` | 将 full-image visual signature 从 Pillow 已弃用的 `getdata()` 迁移到 Pillow 12 `get_flattened_data()`；不改变视觉签名算法，只清除未来 Pillow 14 升级债务 |
| 42 | `7aba88687273ffc7156bcf62f5e5a5b3f230e0dd` | 删除无人引用但会被 wheel 打包的历史备份 `references/visual-system - 好1.md`；避免旧“默认8风格/象牙白”说明继续形成第二套人工权威 |
| 43 | `0a681f68a74533994b3db161aacf949c2e3fd183` | 现代化 Python 包 license 元数据：build backend 最低版本提升到 `setuptools>=77`，改用 SPDX `license = "MIT"`，移除已弃用 License classifier |

## 验证记录

- 阶段 33 后 workflow run `33341756404`：Python 3.10/3.12 pytest 首次全绿；Python 3.12 精确结果为 1760 passed、8 skipped、22 warnings、49 subtests passed。该轮仅 wheel repo 外 smoke 因资源漏包失败。
- 阶段 34 后 workflow run `33342016028`：Python 3.10/3.12 pytest 与 wheel build 全绿；repo 外 smoke 成功越过 preset-shape 数据，随后暴露 `pptx_animation_presets.json` 漏包。
- 阶段 35 后 workflow run `33348212625`：结论 `success`。Python 3.10/3.12 pytest、runtime import、wheel build、离开仓库目录后的 wheel import/resource smoke 全部通过。Stage 02 wheel 已确认可加载 preset-shape 数据、203 个原生动画预设和 SVG Editor 静态资源。
- 阶段 36 只修改说明文档，不改变 registry、Style Lock 或 Prompt bytes。
- 阶段 37 workflow run `33350861421`：结论 `success`。显式注入 `require_generated` 后，pytest、wheel build、repo 外 smoke 均保持全绿；rhythm gate 顺序测试已迁移为通过 `Stage02Dependencies` 注入。
- 阶段 38 workflow run `33351308499`：结论 `success`。Python 3.10/3.12 pytest、wheel build、repo 外 smoke 全绿。兼容层只剩两个 ImageGen module-global patch 点。
- 阶段 39 workflow run `33353230806`：结论 `success`。Python 3.10/3.12 pytest、wheel build、repo 外 smoke 全绿；六个 historical patch 名仍可兼容识别，但生产代码的 module-global monkey-patch 已清零。
- 阶段 40 workflow run `33353471481`：Python 3.10/3.12 两个 job 均 `success`，pytest、wheel build、repo 外 smoke 全部通过；advisory-only 场景已覆盖 lint/render/check-sync/status，未知 finding 仍验证为 blocker。
- 阶段 41 workflow run `33353616539`：Python 3.10/3.12 两个 job 均 `success`。Python 3.12 精确结果为 `1767 passed, 8 skipped, 2 warnings, 49 subtests passed`；Pillow 弃用警告从 20 条降为 0，剩余 2 条仅为 legacy content-integrity projection 兼容提示。
- 阶段 42 workflow run `33353807515`：Python 3.10/3.12 pytest、wheel build、repo 外 smoke 全部通过；删除历史 visual-system 备份没有任何隐性调用依赖。
- 阶段 43 workflow run `33353897774`：结论 `success`。Python 3.10/3.12 pytest、wheel build、repo 外 smoke 全绿；SPDX license/build backend 元数据可正常构建和安装。

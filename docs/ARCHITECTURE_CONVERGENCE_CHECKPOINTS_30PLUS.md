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
| 44 | `e9d75c6797664901ac4c4452b7716366bb6bfaa1` | 新增真实 OfficeCLI render CI：现场生成一页 PPTX，经生产 `run_officecli_render_qa` 走 OfficeCLI HTML + Playwright/Chromium PNG；修正 wrapper 为 stdout HTML 契约并将锁定版本升级到实测可用 v1.0.145。主要提交：`f154061`、`5e6ec18`、`db002ff`、`b973dfa`、`e9d75c6` |
| 45 | `0f6cddd2eb7781359ee4b9e41fa6563e0bed5afe` | 新增 macOS / Windows 轻量 wheel smoke：构建 wheel、无依赖安装、校验 Style09 registry/palette-09、动画预设、preset-shape、SVG Editor、reference/contract 等 package-data；不重复运行 Linux 1700+ 全量测试 |
| 46 | `793ca20f51b1b4625446e4b4cfca1826ae9af399` | 开始收敛 Script Engine God Module：将原 `contracts.py` 实现原字节迁入 `contract_rules.py`，`contracts.py` 缩为稳定兼容 facade；新增架构测试锁定 facade 不得重新长回业务实现，为后续按 schema/source-trace/AUTHOR/onscreen 子域继续拆分建立边界 |
| 47 | `52214c61bf728b86271d1b61d5a598e717ea44a2` | 将 schema validation 与 source_refs traceability 提升为独立运行时模块 `schema_contracts.py`、`source_trace_contracts.py`；`contracts` facade 已将对应公共函数切换到 focused implementation，其余 AUTHOR/onscreen 规则继续由 `contract_rules.py` 提供。实现提交：`f76057a`、`4337655`、`be78356`、`52214c6` |
| 48 | `41a612e8259d668149af23a3195e4bfe5084776b` | 将 speaker notes 最低长度、显式 peer count、上屏末尾标点、上屏详情长度、outline review 五类机械交付检查抽到 `delivery_contracts.py`；CLI 继续通过 `contracts` facade 使用同名 API。实现提交：`7fc1017`、`1721cf3`、`41a612e` |
| 49 | `8dd74da36a03324424a1ee4e27089e6f9e402048` | 将 `check_onscreen_structure` 与 `check_full_copy_duplication` 抽到 `structural_contracts.py`；主 CLI lint 的结构重复检查已不再依赖 monolithic `contract_rules.py`。实现提交：`d4c9056`、`6dcffcd`、`8dd74da` |

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
- 阶段 44 workflow run `33354689757`：Python 3.10、Python 3.12、`OfficeCLI render smoke` 三个 job 全部 `success`。OfficeCLI v1.0.145 在 Ubuntu hosted runner 上成功解析真实 PPTX、生成 HTML、通过 Chromium 截图输出非空 PNG，生产几何 QA 与渲染 QA 均通过。
- 阶段 45 workflow run `33354899758`：Linux Python3.10/3.12、macOS wheel smoke、Windows wheel smoke、OfficeCLI render smoke 五个 job 全部 `success`；关键 package-data 与路径处理已在三类 OS 上验证。
- 阶段 46 workflow run `33361256556`：Linux Python3.10/3.12 全量 pytest + wheel repo 外 smoke、真实 OfficeCLI render smoke、macOS/Windows wheel smoke全部 `success`；`contracts.py` facade 化未改变任何现有 Script Engine 行为。
- 阶段 47 workflow run `33361499406`：五个 job 全部 `success`。Linux Python3.10/3.12 全量测试与 wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke均通过；schema/source-trace focused implementation 已成为 facade 的运行时出口。
- 阶段 48 workflow run `33361745792`：五个 job 全部 `success`。Linux Python3.10/3.12 全量 pytest、wheel repo 外 smoke、OfficeCLI 真实渲染、macOS/Windows wheel smoke全部通过；机械交付检查切换到 `delivery_contracts.py` 后 CLI 输出与退出语义保持兼容。
- 阶段 49 workflow run `33361974577`：五个 job 全部 `success`。结构重复检查切换到 `structural_contracts.py` 后 Linux 全量测试、三平台 wheel smoke 与 OfficeCLI 真实渲染均保持通过。

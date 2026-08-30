# CyberPPT 架构收敛改造记录

本文件记录 2026-08-31 开始的架构收敛工作。每完成一个小阶段即提交，确保会话、Agent 或本地进程中断后可以从 Git 历史继续。

## 目标

保持“源材料 → 脚本 → 完整图片 → 图转可编辑 PPT → QA 交付”正式路线不变，收敛权威模型、运行状态、兼容层和可复现性边界。

## 已完成阶段与恢复点

| 阶段 | Commit | 内容 |
|---|---|---|
| 1 | `b64fed03162ae26fb474655a4dcdb67813c3482e` | Style 09 lock 改为创建时合同快照，禁止读取旧锁时 live refresh |
| 2 | `67586a09620082cfb1742b749526146a5d0e2d0e` | 建立 Stage 01/02 Authority Map，统一可写权威与 projection 边界 |
| 3 | `6862598eb1314b8ad8fe73edd398542d55649e2a` | 增加 Stage 02 正常待办/真实失败状态模型 |
| 4 | `f57692ec6887e38ae25373af2c206219194b7dc4` | 分离稳定 `input_fingerprint` 与每次执行 `run_id/build_id` |
| 5 | `4b5f225cc8a780003cca95b4997586e7b187e037` | 明确安装能力边界、直接/可选依赖和 CI runtime import smoke |
| 6 | `5948b6c8f2ea5483efe58a9c28035ad2cdbcabe8` | 删除根目录 scratch 产物并增加 ignore 规则 |
| 7 | `7042e158240c39b58c9deba596967cc7b1ee8608` | Script deterministic finding 增加 blocker/advisory severity policy |
| 8 | `ebf2f748e6349255221960e6c78a61dbed1a4ad2` | 正式 manifest 按 input identity + Prompt SHA 精确失效旧视觉资产 |
| 9 | `01a95b299851bdee200229baa0cb2f5aee51fb4e` | 主 orchestrator 将缺 SVG/待审核转换为 `needs_action` 正常结果 |
| 10 | `8062debc4fc7442ac2b77ae19784fb9611a22edf` | `needs_action` 写回 `build_context.json`，中断后可直接恢复 |
| 11 | `ad4a99ef39a82fd0554127d84aab2aa6905b8971` | 正式 runtime/contract/reference/assets 纳入 wheel 包边界并增加 wheel smoke |
| 12 | `2e9cd4e3cac6c213b09b2a2b028c10b8fc613997` | Compatibility seam 封口为固定 6 项 `LegacyPatchSet`，保留旧测试兼容 |
| 13 | `f0cf8a17e8d74034b8e7bdfe0250be60d688ec6a` | CI 在 pytest 失败时持久化完整日志 artifact，便于精确诊断和恢复 |
| 14 | `ed7e1385816cae33454f82e4841192370eb42c1c` | 修正 Pillow 直接依赖版本，恢复 Pillow 12 像素迭代 API |
| 15 | `fa65965d0acaccbb77f545d6994fa54d0e1f3def` | 新 fingerprint 严格失效，同时保留无 fingerprint 历史 manifest 的旧项目恢复兼容 |
| 16 | `45dcf03a38d76d53c37a9d6747d06f31a290680e` | 旧 Style 09 live lock 首次读取时迁移并落盘为 snapshot；新锁和迁移后的锁均永久冻结 |
| 17 | `9690e2f49532a25c79cdfe32baa4a6900d149657` | `projects/AGENTS.md` 与仓库主流程统一：新源材料项目默认 strict/legacy，script 仅显式选择时启用 |
| 18 | `901196a5976f385f108cbc517f2ae817df3cbe2b` | 消除 Style 09 双权威：可执行合同只从 style registry JSON 解析；`visual-system.md` 降为说明性文档，不再覆盖运行时 Prompt |
| 19 | `8d474ea59e999d20f8702aab4def816031d55941` | 首轮清理独立 Style10 测试合同，确认 registry 不再维护第十套视觉定义或 palette-10 |
| 20 | `00dc915017243be307ac0388ecd98d47fd857dcc` | Style Lock snapshot 测试迁移到 registry authority：registry 修订产生新锁版本，说明文档修订不改变可执行合同，legacy lock 仅迁移一次 |
| 21 | `d1c6a6c3a39f2df953062ae06e7865f14bb711b2` | Terminal execution lock 在追加前删除正文中完全相同的硬约束整行，避免重复 Prompt；部分匹配和页面业务句保持不变 |
| 22 | `99a6acb29d2724e849a1e99a5bdb277c6ee2f5ac` | Style09 回归测试从旧 Prompt 逐字快照迁移为 registry/纯白/合同章节/锁 SHA/迁移/终端锁/CLI 等正式不变量 |
| 23 | `ffc500cec29329168e75601a45ac5f6f33ebec3d` | Style09 样张与合同测试彻底脱离 `visual-system.md` 旧复制文本，直接验证 runtime registry；删除人为 Prompt 长度上限 |
| 24 | `4ea6ed5b58ad568cfe0df31863dac455ba45f5dd` | 将 handoff 模块化测试从历史公共面/Style10/逐字 Prompt baseline 改为 facade 与 modular implementation 的行为等价性合同 |
| 25 | `a085e2c0221421b9a7543e2f7c9418dd3ca98741` | Manifest provenance 回归改为 Style09，保留 compiler、Prompt 一致性与 `prompt_sha256` 自描述追溯，不再绑定旧 Style10 |
| 26 | `11bed7543c100e43d8dcf614f62a2e64831889c8` | Style10 从独立视觉风格降为兼容 alias：旧 ID/slug 统一解析到 canonical Style09 snapshot，继续使用同一 Prompt SHA 与 palette-09 |
| 27 | `04f43ed9cd3c0852e60edebff77dd8e5360d3989` | Handoff facade 测试同步 legacy Style10 alias 语义，验证旧入口不会形成第二套视觉权威 |

## 当前结构性结果

### Stage 01

- strict whole-document 单一可写语义权威：`semantic-argument-model.json`。
- `source-truth.json` 是 deterministic projection。
- `script/foundation.json` 是 PLAN/AUTHOR 语义合同。
- `script/deck-plan.json` 负责章节、页序、页面使命和来源范围。
- `script/dist/final-script.md` 是 Stage 02 唯一跨阶段内容权威。
- `projects/AGENTS.md` 不再维护一条相反的默认路线；项目目录规则明确从属于仓库总流程。
- 详细规则见 `docs/CYBERPPT_AUTHORITY_MAP.md`。

### Stage 02

- Style registry `scripts/imagegen_pipeline/style_presets/cyberppt_default_styles.json` 是可执行视觉合同的唯一解析源。
- `references/visual-system.md` 仅作为视觉系统说明与探索文档，不再在运行时覆盖 Style 09 Prompt。
- 新建 Style 09 锁在创建时从 style registry 解析合同并冻结；`resolved_contract.source` 指向 style registry。
- registry 合同修订只影响新建锁；已经是 immutable snapshot 的锁保持原字节不变。
- 历史 pre-snapshot Style 09 锁首次读取时迁移到 style registry 当前合同并冻结，此后不再刷新。
- Style10 不再拥有独立 registry entry、独立 Prompt 或 palette-10；旧 `style_id=10`、`light_tech_business_dense`、`ivory_deep_blue_semantic_scene` 仅作为兼容入口，统一解析为 canonical Style09。
- Style10 alias 锁显式记录 `requested_style_id/name`、`canonical_style_id=9` 和 `legacy_alias=true`，便于追溯旧调用来源；最终 Prompt SHA、reference image 和执行合同仍只有一份。
- Runtime terminal lock 只在 Prompt 绝对末尾保留一份；若同一终端硬约束已作为独立整行出现在正文，会在 reassert 前精确去重，不删除包含额外上下文的页面句子。
- Style09 测试只锁定正式视觉合同的不变量与安全边界，不再把某个历史 Prompt 版本的整段措辞、文档副本或固定字符长度当作 API。
- `imagegen_handoff.py` 兼容 facade 的正式回归标准为：关键符号直接 re-export 模块实现、公共面无重复、旧 Style10 只能归一到 Style09、相同 Style09 输入经 facade 与模块生成完全相同结果。
- `input_fingerprint` 表达输入身份；`run_id/build_id` 表达执行身份。
- 新版 Manifest 恢复必须同时满足相同 input fingerprint 和相同 Prompt SHA。
- 双方都没有 fingerprint 的历史 manifest 进入明确 legacy recovery compatibility；一旦任一侧存在 fingerprint，就必须严格匹配，不允许降级回 legacy。
- Full image 通过审计后仍是 editable reconstruction 的视觉权威。
- `needs_svg_authoring`、`needs_visual_review` 等属于正常 action state，不再等同 terminal failure。
- Action state 写入 manifest、独立回执和 `build_context.json`。

### Script QA

- 高置信 schema/结构/未知 deterministic finding 默认 blocker。
- 首批措辞/视觉语法正则类检查进入 advisory policy，避免作者为了通过 regex 机械堆关系动词。
- 原 `lint` 退出行为暂保持兼容，severity policy 先独立运行再逐步接入主 gate。

### Packaging / CI

- Pillow 12 为直接依赖；XLSX/MarkItDown 能力进入 `source` extra。
- `scripts`、`references`、`contracts`、`assets` 进入 wheel 包边界。
- CI 覆盖 Python 3.10/3.12 pytest、runtime import、wheel build 和离开仓库目录后的 wheel import/resource smoke。
- pytest 输出通过 `tee` 保存，并使用 `actions/upload-artifact@v4` 在成功或失败时均上传 `pytest-log-<python-version>`；`pipefail` 保证日志保存不会吞掉测试失败退出码。

## Compatibility seam 当前状态

现有 `tests/test_final_script_pages.py` 直接 patch `cyberppt.commands.final_script_pages.run_codex_image/ensure_output_size`。本轮没有破坏性删除 monkey patch，而是把兼容入口收敛到 `cyberppt.stage02_production.compat` 并固定为 6 项 `LegacyPatchSet`。后续迁移一个显式 dependency hook 后再删除一个 legacy 字段。

## 尚未完成 / 后续建议

1. 修正局部文字纠错测试夹具：生成合法 PNG 后验证真实 local-edit → enhancement 链。
2. 清理 creative brief、deliverable prompt、page manifest、no-visual-structure 中余下旧 Style09 精确字符串/标题断言。
3. 统一 `references/visual-system.md` 中 Style09 的说明性文字，清除仍残留的象牙白旧说明，并注明 Style10 仅为兼容 alias。
4. 将 6 个 LegacyPatchSet 字段逐个迁移为显式依赖注入，并继续接入 quality policy / wheel fixture / Office 集成 CI。

## 验证状态

- 基线 commit `f52f72553d41c828e10d12c5c4a3a7cb51c78ab4` 在本轮改造开始前，GitHub Actions run `33323661957` 的 Python 3.10/3.12 pytest 已经失败。
- 阶段 17 run `33339954486`：Python 3.12 为 37 failed、1753 passed、8 skipped。
- 阶段 18 run `33340180065`：Python 3.12 为 40 failed、1750 passed、8 skipped。
- 阶段 22 文档 checkpoint run `33340603317`：Python 3.12 为 24 failed、1764 passed、8 skipped。
- 阶段 24 文档 checkpoint run `33340946220`：Python 3.12 为 **9 failed、1751 passed、8 skipped**。剩余 9 项均已定位；阶段 25 已消除 provenance 对 Style10 的绑定，阶段 26 将其他旧 Style10 调用归一到 Style09，阶段 27 同步 handoff facade 测试。
- 阶段 27 之后的 CI 将作为下一轮精确失败清单；在 GitHub Actions 最终 conclusion 变绿前，不视为全量验证完成。

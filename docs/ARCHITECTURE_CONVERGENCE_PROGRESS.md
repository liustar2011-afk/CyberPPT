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
| 17 | 待本次提交 | `projects/AGENTS.md` 与仓库主流程统一：新源材料项目默认 strict/legacy，script 仅显式选择时启用 |

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

- 新建 Style 09 锁在创建时解析当前合同并冻结。
- 历史 pre-snapshot Style 09 锁首次读取时按旧行为解析一次当前合同，写回 `resolved_contract.mode=snapshot` 和迁移标记；此后不再 live refresh。
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

现有 `tests/test_final_script_pages.py` 直接 patch `cyberppt.commands.final_script_pages.run_codex_image/ensure_output_size`。因此本轮没有破坏性删除 monkey patch，而是：

1. 把兼容入口收敛到 `cyberppt.stage02_production.compat`；
2. 固定为 6 项 `LegacyPatchSet`；
3. 保留旧 `sync_legacy_patch_points()` wrapper；
4. 新增测试禁止 patch surface 继续扩张。

下一步应逐个把这 6 项迁移到显式 dependency hooks，迁移一个、删除一个，最终移除 wrapper。

## 尚未完成 / 后续建议

1. 将 6 个 LegacyPatchSet 字段逐个迁移为显式依赖注入；这是剩余的主要架构技术债务。
2. 把 `script_engine.quality_policy` 接入正式 `audit-final/lint` 输出，在回归验证充分后让 advisory 不再影响主阻断结果。
3. 增加 wheel 环境下不调用外网/Office 的最小 Stage 01→Stage 02 fixture build。
4. 增加 macOS/Windows OfficeCLI/render 集成 CI。
5. 继续拆分超大 Stage 01 模块；优先 `source_argument_model.py`、`stage01_compiler.py`、`visual_structure_contract.py`、`script_engine/contracts.py`。拆分必须按领域职责进行，不做单纯文件切割。

## 验证状态

- 基线 commit `f52f72553d41c828e10d12c5c4a3a7cb51c78ab4` 在本轮改造开始前，GitHub Actions run `33323661957` 的 Python 3.10/3.12 pytest 已经失败；因此当前 CI 红色包含仓库既有失败，不能全部归因于本轮。
- 阶段 16 run `33339768029` 的 Python 3.12 日志显示 38 failed、1752 passed、8 skipped；失败已由阶段 13 的 50 项下降。可枚举失败主要集中在已退役 Style10、旧 Style09 prompt 合同、项目默认 profile 漂移以及一个 legacy facade mock 测试。
- 阶段 17 先消除会真实影响 Agent 路由的项目级 profile 冲突；随后再清理已退役 Style10/旧 Style09 测试契约。

# CyberPPT 架构收敛恢复点（阶段 1–29）

本文件归档架构收敛 Stage 1–29 的恢复点。当前状态与后续恢复入口统一见 `docs/ARCHITECTURE_CONVERGENCE_PROGRESS.md`。

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
| 18 | `901196a5976f385f108cbc517f2ae817df3cbe2b` | 消除 Style 09 双权威：可执行合同只从 style registry JSON 解析；`visual-system.md` 降为说明性文档 |
| 19 | `8d474ea59e999d20f8702aab4def816031d55941` | 首轮清理独立 Style10 测试合同，确认 registry 不再维护第十套视觉定义或 palette-10 |
| 20 | `00dc915017243be307ac0388ecd98d47fd857dcc` | Style Lock snapshot 测试迁移到 registry authority，legacy lock 仅迁移一次 |
| 21 | `d1c6a6c3a39f2df953062ae06e7865f14bb711b2` | Terminal execution lock 追加前精确删除正文中完全相同的硬约束整行，避免重复 Prompt |
| 22 | `99a6acb29d2724e849a1e99a5bdb277c6ee2f5ac` | Style09 回归测试从旧 Prompt 逐字快照迁移为正式不变量 |
| 23 | `ffc500cec29329168e75601a45ac5f6f33ebec3d` | Style09 样张与合同测试彻底脱离 `visual-system.md` 旧复制文本并删除人为 Prompt 长度上限 |
| 24 | `4ea6ed5b58ad568cfe0df31863dac455ba45f5dd` | handoff 模块化测试改为 facade 与 modular implementation 的行为等价性合同 |
| 25 | `a085e2c0221421b9a7543e2f7c9418dd3ca98741` | Manifest provenance 回归改为 Style09，保留 compiler、Prompt 一致性与 `prompt_sha256` 追溯 |
| 26 | `11bed7543c100e43d8dcf614f62a2e64831889c8` | Style10 从独立视觉风格降为兼容 alias，旧 ID/slug 统一解析到 canonical Style09 snapshot |
| 27 | `04f43ed9cd3c0852e60edebff77dd8e5360d3989` | Handoff facade 测试同步 legacy Style10 alias 语义 |
| 28 | `1c5adc1f70b3204159fb4d4fd94ba8619d979de4` | 局部文字纠错回归改用真实 PNG，保留完整旧测试集为非收集 base |
| 29 | `df2aa24260c52ed70cd555760cc780b94c947ce0` | Style09 生图安全测试迁移到当前合同：默认无人物/无正脸、组织标识禁绘、辅助语义图少量中文、全页禁箭头、事实忠实与伪中文禁令 |

Stage 30 以后分别见：

- `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_30PLUS.md`
- `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_50PLUS.md`
- `docs/ARCHITECTURE_CONVERGENCE_CHECKPOINTS_66PLUS.md`

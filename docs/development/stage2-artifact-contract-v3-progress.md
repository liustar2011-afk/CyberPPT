# Stage2 Artifact Contract v3 开发台账

开发分支：`feature/stage2-artifact-contract-v3`

本台账用于记录 Stage2 送图脚本优化改造全过程。每完成一个可验证的小步骤，必须同步记录已完成工作、验证结果和下一阶段工作；代码提交信息同时采用相同口径。

## Step 0｜开发基线与实施机制

状态：已完成

已完成工作：
- 以 `main@7bfdf58cf6cbe0317dc038691433dd797d7d6444` 创建独立开发分支。
- 核对 Stage2 现有代码，确认 `VisibleTextBindingSpec` 已实现但在 `build_page_artifact_spec()` 被置空。
- 核对最终 Prompt 链，确认 locked copy 权威与 downstream rewrite/source-material 口径存在冲突。
- 核对 Region Graph、Visual Medium、Text Capacity、Visual Thesis、Stage02 body canvas 和 Prompt validator 的现状。
- 确定采用“每个小步骤独立提交 + 定向 pytest + Draft PR 统一台账”的实施机制。

验证结果：
- 仓库 Issues 功能关闭，因此改用 Draft PR 作为统一过程台账。
- 仓库现有 PR CI 可运行 Ubuntu Python 3.10/3.12 全量测试，并含 macOS / Windows wheel smoke 与 OfficeCLI smoke。

下一阶段工作：
- Step 1.1：新增独立 Copy Contract 领域合同与权威规则测试。

## Step 1.1｜Copy Contract 领域模型

状态：已完成

已完成工作：
- 新增 `cyberppt/copy_contract.py`。
- 建立 `CopyContractSpec`、`LockedCopySpec`、`RewriteableCopySpec`、`ExtraTextPolicySpec`。
- authored visible copy 默认进入 locked copy；仅显式授权的 text_id 才允许进入 rewriteable copy。
- locked copy 强制 `count=1`，并限制 transformation 只能是 line break / grouping / position change 等不改变文案的操作。
- extra text 默认 `allowed=false`、`max_count=0`。
- 新增 `tests/test_copy_contract.py`，覆盖默认锁定、显式改写授权、region ownership、重复 id、权限重叠、非法 transformation、extra text 等规则。

验证结果：
- Copy Contract 领域模型与测试已作为独立提交进入 PR #29。
- 当前全量 CI 仍包含仓库基线既有失败，不能以全量 CI 作为本步骤增量正确性的唯一判据；后续步骤继续采用定向测试 + PR CI 双层验证。

下一阶段工作：
- Step 1.2：恢复 `_visible_text_bindings()` 权威链，将 Copy Contract 接入 `PageArtifactSpec → FinalPromptIR → Renderer → Validator`，并删除 locked copy 的 rewrite/source-material 冲突授权。

## Step 1.2｜Copy Contract 权威链闭环

状态：已完成

已完成工作：
- 恢复 `_visible_text_bindings()`，不再将 authored visible copy 主动降级为空绑定。
- `PageArtifactSpec` 增加 `copy_contract`，并校验 Copy Contract 对全部 visible text binding 的唯一覆盖。
- 将 Region Graph 的 `text_ids` 映射到 Copy Contract，保留每条上屏文字的 macro region ownership。
- `FinalPromptIR` 增加 `copy_contract` 并将 IR 版本升级至 v5。
- Renderer 对 locked copy 使用 `Exact visible text` 合同，每条逐字声明一次；rewriteable copy 仅对显式授权项输出 rewrite goal。
- 删除 Copy Contract 路径中的 blanket `rewrite / merge / shorten / reorder / split / select / replace` 授权。
- extra text 默认在最终 Prompt 中显式禁止。
- Validator 分别校验 exact copy、rewriteable copy、extra text policy，并继续阻止 backend/internal 字段泄漏。
- Debug receipt 增加 Copy Contract sidecar 信息。
- 新增 `tests/test_copy_contract_pipeline.py`，覆盖 locked-only、mixed copy、coverage drift。

验证结果：
- 第一次定向测试发现 `claim_strength` 内部字段会泄漏到 Prompt；未提交半成品。
- 修正为公共表述 `claim strength`，保持 backend leak validator 严格不放宽。
- 第二次执行 `tests/test_copy_contract.py + tests/test_copy_contract_pipeline.py` 全部通过。
- 业务提交：`64a50136a81b6b57b7cc1a4d1ce67ced1a123f0d`（`stage2-v3: close copy contract authority chain`）。
- Phase 1 验收目标已形成代码闭环：locked copy 逐字唯一声明、Region ownership 保留、Copy Contract 路径不存在 blanket rewrite 与 strict lock 并存。

下一阶段工作：
- Phase 2 / Step 2.1：新增 `CompositionStrategy` contract，删除 topology 对 macro axis/geometry 的一对一权威关系；Region Graph 改为消费 composition strategy，并建立同一 topology 至少 3 种合法宏观构图策略的测试。

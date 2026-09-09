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

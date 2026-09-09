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
- Step 1：完成 Copy Contract 最小闭环，恢复 VisibleTextBindingSpec 权威链并消除 strict lock / rewrite 冲突。

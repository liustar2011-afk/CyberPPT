# Stage2 Artifact Contract v3 最终验收记录

状态：已完成

验收对象：`feature/stage2-artifact-contract-v3`

基线：`main@7bfdf58cf6cbe0317dc038691433dd797d7d6444`

最终代码验收 head：`cdcd1527c284926282651f080e7a00e1bb79d970`

标准全量矩阵：run `34415702871`

## 验收口径

1. Stage2 v3 七个 Phase 的正式代码、测试与 schema 均保留在 PR #29。
2. 开发期专用 workflow、patch helper、临时 CI trigger 已清理，不进入正式交付范围。
3. Python 3.10 / 3.12 使用失败测试集合与 Phase 1.1 基线做差分；最终要求 `final_failures - baseline_failures = 0`。
4. Windows / macOS wheel smoke 要求保持通过。
5. OfficeCLI render smoke 要求在最终 hosted runner 上完成 geometry 与 render QA。

## 最终结果

### Python 3.12

- Phase 1.1 基线：67 failed / 1930 passed / 8 skipped / 49 subtests passed。
- 最终结果：47 failed / 2000 passed / 8 skipped / 41 warnings / 49 subtests passed。
- 失败集合差分：`final_failures - baseline_failures = 0`。
- 已消除基线失败：20 项。
- 最终保留的 47 项失败全部属于 Phase 1.1 基线失败集合。

### Python 3.10

- 最终结果：47 failed / 2000 passed / 8 skipped / 41 warnings / 49 subtests passed。
- Python 3.10 与 Python 3.12 的失败测试集合完全一致。
- 未出现 Python 版本分叉导致的 Stage2 v3 新增回归。

### Wheel smoke

- macOS：通过。
- Windows：通过。

### OfficeCLI render smoke

- 最终 run `34415702871`：通过。
- pinned OfficeCLI、deterministic fixture、geometry QA、render QA 均完成。
- 早期出现的 `System.Private.Xml 10.0.0.0` hosted-runner runtime 异常未在最终矩阵复现，确认不构成 Stage2 v3 代码回归。

### Copy Contract 最终兼容门禁

- 专用门禁 run `34415399750`：18 passed。
- 最终业务修复提交：`9a380951`（`fix(stage2): close final copy contract regressions`）。
- authored visible copy 默认逐字锁定；legacy `Source onscreen text` 声明被 validator 拒绝，最终 Prompt 不再存在双重文案权威。

### 开发脚手架清理

- 清理提交：`c143be10`（`chore(stage2): remove temporary compatibility scaffolding`）。
- 已删除开发期专用 workflow、3 个 patch/migration helper 和临时 CI trigger。
- PR 最终 changed files 仅保留业务代码、正式测试、schema、Skill 合同及开发/验收文档。

## 验收结论

Stage2 Artifact Contract v3 增量兼容性验收通过：

- Phase 1—7 均已形成生产代码、正式测试与对应合同闭环；
- 最终 Python 3.10 / 3.12 相对 Phase 1.1 基线的新增失败均为 0；
- Windows / macOS wheel smoke 通过；
- OfficeCLI geometry / render smoke 通过；
- 开发期临时脚手架已从正式 PR diff 清除；
- 仓库全量 Python 仍有 47 项失败，但均属于本开发开始前已存在的 Phase 1.1 基线失败集合，不属于 Stage2 v3 新增回归。

下一阶段工作：进入代码审阅与合并流程。

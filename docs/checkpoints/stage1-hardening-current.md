# Stage1 Hardening 当前检查点

分支：`stage1-hardening`
PR：#34

## 已完成

当前完成到收口批次 `9 / 子步骤 1`。

### 批次 5：Final Script Source Provenance

- Final Script 内容页强制要求 `source_provenance`。
- 标准 page lineage 为：`packet_sha256 + source_refs + unit_ids`。
- Final Script 1.1 同时保留 module / item 级 provenance；页面级 lineage 与模块级 semantic binding 职责分离。
- `audit-final` 与 `render-stage02` 均验证 Final Script provenance 与当前 Author Preflight 一致性。

### 批次 6：Native-source Fidelity Audit

- Final Script 内容页直接与逐页 exact native source units 做高风险事实一致性校验。
- 覆盖新增数字/日期、数字限定词丢失、明确范围限定词丢失、状态提升、责任强度提升、结论强度提升。
- `audit-final` 与 `render-stage02` 统一使用 `native_source_fidelity_gate_issues()`。
- Stage02 发现事实漂移时返回 `kind=native-source-fidelity`，不写出输出文件。

### 批次 7：Project Status 接入 Stage1 Gate

- `script_engine/project_status.py` 新增正式 `stage1` 状态区，集中输出：`source_index / foundation / deck_plan / author_preflight / final_script / final_audit`。
- Author Preflight 状态不信任静态 Manifest，而是先重建 current preflight，再校验 Manifest 是否仍代表当前状态。
- `author_preflight.pages` 输出逐页 `gate_status / freshness / exact_source_status / source_refs / unit_ids / issues`。
- 顶层 `stage` 不再允许“无 Preflight 但 Final Script 存在”显示为已就绪。
- 只有 `final_audit_report()` 真正通过后，项目才显示“可进入 Stage02”。
- focused status tests 已覆盖：fresh / stale / manifest missing / packet blocked / final native fidelity failed。

### 批次 8：测试与 CI 基线治理

此前 3 个历史失败已完成治理：

1. `FAITHFUL_RELATION_PROMOTED` 按现有 rule registry 的低置信度 warning 契约迁移测试；
2. object-item code-only fixture 改为当前 taxonomy code 形态 `A1+B2`；
3. Style 09 样例测试从过期 2:1 固定像素改为当前 16:9 高分辨率合同。

旧 status 测试也全部迁移到新的 Stage1 Gate 契约，不保留“脚本文件存在即可就绪”的兼容行为。

### 代码基线最终验证

GitHub Actions run `34585423986`，代码 head `cea6b706a7b8e6e74f25ea2bde994831777f561b`：

- Python 3.10：`2247 passed, 8 skipped, 42 warnings, 49 subtests passed`，0 failed；
- Python 3.12：`2247 passed, 8 skipped, 42 warnings, 49 subtests passed`，0 failed；
- OfficeCLI render smoke：passed；
- Windows wheel smoke：passed；
- macOS wheel smoke：passed；
- workflow overall：success。

至此，Stage1 hardening 代码层面已经恢复真实绿色基线。

### 收口批次 9 / 子步骤 1：运行合同固化

已新增：

`.agents/skills/cyberppt-script-workflow/references/stage1-faithful-gate-contract.md`

该合同正式固化：

```text
source-index.v2
  → Page Source Packet v2
  → Author Preflight v2
  → AUTHOR
  → Final Script source_provenance
  → Native-source Fidelity Audit
  → Stage02
```

并明确：

- exact source 缺失、部分解析、binding 缺失、Packet stale/invalid 均硬阻断；
- Foundation preview 不得充当 faithful factual fallback；
- 当前 Stage1 faithful route 不再提供“无 v2 source index”的回退路径；
- Final Script 页面 provenance 必须来自当前 passed Author Preflight；
- `render-stage02` 必须重新验证 Preflight、page lineage 与 Native-source Fidelity。

同时更新 `.agents/skills/cyberppt-script-workflow/AGENTS.md`，将该合同设为 AUTHOR / CRITIQUE / REWRITE / Final Audit / Stage02 handoff 的强制阅读入口。

`final-script-provenance-contract.md` 也已改为双层 provenance 合同：

- 页面级 exact-source lineage 证明当前精确来源证据；
- module / item provenance 描述 Final Script 结构化语义归属；
- Native Source Unit 是最终事实权威；Foundation 负责结构化语义索引与绑定。

## 下一步

收口批次 `9 / 子步骤 2`：验证最新文档 head 的 GitHub Actions。

通过后：

1. 生成最终 Stage1 Hardening 验收记录；
2. 更新 PR #34 描述，写清架构变化、硬门禁、测试结果与不再兼容的旧行为；
3. 确认 PR 处于可合并状态，不在未授权情况下自动合并。

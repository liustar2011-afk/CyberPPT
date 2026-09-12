# Stage1 Hardening 当前检查点

状态：**已完成并合并**

主线合并：

- PR #34 `feat(stage1): harden faithful authoring source gate`
- squash merge：`3e4410b58e96ca3eb89d7ab622973488807585e5`
- 后续合同收敛：PR #36 `fix(stage1): converge faithful source-index gate contracts`
- PR #36 squash merge：`40a6abaaa9231d94ff21b90211506f344a4bc3f0`

## 最终执行链

```text
Native Sources
  → Source Index v2
  → Foundation
  → Deck Plan
  → Page Source Packet v2
  → Author Preflight v2
  → AUTHOR
  → Final Script source_provenance
  → Native-source Fidelity Audit
  → Stage02
```

## 最终合同

### 1. Exact Source 硬门禁

- unknown source ref → `blocked`
- Foundation 无 source-unit binding → `blocked`
- exact source 全部无法解析 → `blocked`
- exact source 部分解析 → `blocked`
- Foundation statement / preview 不得作为 faithful factual fallback

### 2. Page Source Packet v2

- schema：`cyberppt.page_source_packet.v2`
- 持久化 `builder_version`、`generated_at`
- 持久化 Deck Plan / Foundation / Source Index 三个 SHA-256 fingerprints
- freshness：`fresh / stale / invalid`
- 任一上游输入变化后旧 Packet 自动失效

### 3. Author Preflight v2

- schema：`cyberppt.author_preflight.v2`
- 页面状态：`passed / blocked / missing / stale / not_applicable`
- 持久化并复核 exact source 状态、source refs、unit ids、packet hash 和问题原因
- `audit-final`、`render-stage02`、project status 均基于当前输入重新验证，不直接信任历史 Manifest

### 4. Final Script 来源血缘

内容页强制携带页面级 `source_provenance`：

```json
{
  "source_provenance": {
    "packet_sha256": "...",
    "source_refs": ["..."],
    "unit_ids": ["..."]
  }
}
```

页面级 exact-source lineage 与 Final Script 1.1 的 module/item provenance 分层存在；两者职责不同，互不替代。

### 5. Native-source Fidelity Audit

`audit-final` 与 `render-stage02` 共用 native-source fidelity gate，当前确定性 blocker 覆盖：

- 新增数字 / 日期
- 数字限定词丢失
- 明确范围限定丢失
- tentative → achieved 状态提升
- 新增必须 / 应当 / 不得 / 严禁等责任强度
- 新增必然 / 全面 / 显著等结论强度

### 6. 不可旁路的 faithful route

默认 `script + faithful` 当前正式路线要求：

1. current `cyberppt.source_index.v2`；
2. fresh Page Source Packet；
3. passed Author Preflight；
4. AUTHOR / targeted edit / whole-deck rewrite；
5. Final Script page provenance；
6. Native-source Fidelity Audit；
7. Stage02 handoff 再验证。

Source Index、Packet 或 Preflight 缺失、陈旧、无效、部分解析或阻断时必须停止。当前 Stage1 faithful route 不提供 no-source-index、Foundation-preview 或 model-memory fallback。

## 运行合同

当前强制入口：

- `.agents/skills/cyberppt-script-workflow/references/stage1-faithful-gate-contract.md`
- `.agents/skills/cyberppt-script-workflow/AGENTS.md`
- `.agents/skills/cyberppt-script-workflow/SKILL.md`
- `.agents/skills/cyberppt-script-workflow/references/final-script-provenance-contract.md`
- 根级 `AGENTS.md`
- `docs/CYBERPPT_WORKFLOW.md`

PR #36 已将仓库级入口、主流程总览与 Script Skill 的旧条件式 “when/if v2 source index exists” 口径全部收敛为上述 hard gate，并新增 repository-wide contract regression guard。

## 最终验证

### PR #34

GitHub Actions `CyberPPT tests` #1034 / run `34586183016`：

- Python 3.10：success
- Python 3.12：`2247 passed, 8 skipped, 42 warnings, 49 subtests passed`
- OfficeCLI render smoke：success
- Windows wheel smoke：success
- macOS wheel smoke：success

合并后 `main` push CI #1035 同样通过。

### PR #36

GitHub Actions `CyberPPT tests` #1046 / run `34671840174`：

- Python 3.10：success
- Python 3.12：`2248 passed, 8 skipped, 42 warnings, 49 subtests passed`
- OfficeCLI production geometry/render smoke：success
- Windows wheel smoke：success
- macOS wheel smoke：success

## 结论

Stage1 hardening 已完成代码实现、Schema、CLI、运行门禁、Final Script provenance、native-source fidelity、project status、Agent/文档执行合同及 CI 回归守卫，并已进入 `main`。

本检查点不再包含待执行事项。后续新增 Stage1 改造应单独建立新的开发任务或检查点，不再沿用 PR #34 的未完成状态。
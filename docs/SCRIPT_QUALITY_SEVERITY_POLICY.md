# Script Engine 质量检查分级

CyberPPT 的确定性检查分为两层，并已接入主 Script Engine 交付边界。

## Blocker

适用于机器能够高置信判断的错误，包括：

- JSON/schema 不合法或必填字段缺失；
- source ref、数字、责任、状态、条件、边界等来源一致性错误；
- 破坏机器合同、无法进入下游的结构错误；
- 上屏结构、交付清洁度、文字长度等已登记硬约束；
- 未登记的新 deterministic finding。未知规则默认 fail closed。

Blocker 会使 `lint`、`render-stage02` 或 `check-sync` 失败，并使项目 `status` 保持在需要修复的阶段。

## Advisory

适用于依赖措辞和表达方式的启发式检查。当前以下规则属于 advisory：

- `AUTHOR_MISSION_GENERIC`
- `AUTHOR_VISUAL_THESIS_NONRELATIONAL`
- `AUTHOR_VISUAL_TOPOLOGY_CONFLICT`

这些检查仍进入 AUTHOR/Critic 评审和质量报告，但不会要求作者为了命中某组关系动词或固定措辞而机械改写业务表达。

## 主命令行为

- `cyberppt-script lint <final-script.json>`：仅 blocker 返回失败；存在 advisory 且无 blocker 时返回 `passed_with_advisories`。
- `cyberppt-script status <project>`：advisory 写入 `final_script.lint_advisories`，不会把项目退回“需要修复”状态。
- `cyberppt-script render-stage02 ...`：advisory 不阻止生成 Stage 02 Markdown；blocker 继续阻止交付。
- `cyberppt-script check-sync ...`：advisory 会出现在报告中，但不会导致同步检查失败。
- `python -m script_engine.quality_policy <final-script.json>`：可单独查看 `blockers` 与 `advisories` 的机器可读报告。

所有命令在进入严重性分流前仍执行原有完整检查集合；严重性策略只决定 finding 是否阻断，不删除、跳过或隐藏检查。

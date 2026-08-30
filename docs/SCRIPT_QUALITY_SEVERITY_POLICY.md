# Script Engine 质量检查分级

CyberPPT 的确定性检查分为两层。

## Blocker

适用于机器能够高置信判断的错误，包括：

- JSON/schema 不合法或必填字段缺失；
- source ref、数字、责任、状态、条件、边界等来源一致性错误；
- 破坏机器合同、无法进入下游的结构错误；
- 未登记的新 deterministic finding。未知规则默认 fail closed。

## Advisory

适用于依赖措辞和表达方式的启发式检查。当前首先将以下规则降为 advisory：

- `AUTHOR_MISSION_GENERIC`
- `AUTHOR_VISUAL_THESIS_NONRELATIONAL`
- `AUTHOR_VISUAL_TOPOLOGY_CONFLICT`

这些检查仍应进入 AUTHOR/Critic 评审，但不能要求作者为了命中某组关系动词而机械改写业务表达。

## 使用

```bash
python -m script_engine.quality_policy path/to/final-script.json
```

返回 `blockers` 与 `advisories`。当前原有 `lint` 命令保持兼容行为；本阶段先建立显式严重性策略，后续在确认回归覆盖后再让主 CLI 直接消费该分级结果。

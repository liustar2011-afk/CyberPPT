# Stage1 Faithful Source Gate Contract

本文件是 Stage 01 来源门禁的运行合同。进入 faithful AUTHOR、CRITIQUE、REWRITE、单页实质修订、全稿审计或 Stage02 交付前必须遵守本合同。

## 1. 权威链

Stage 01 的事实权威按以下顺序单向传递：

```text
Native Source Unit
  → Page Source Packet
  → Foundation
  → Deck Plan
  → Final Script
```

Native Source Unit 是最终事实权威。Foundation 用于结构化理解和索引，Deck Plan 用于页面规划，Final Script 是作者输出。低层产物不得反向证明高层事实。

Page Source Packet 和 Author Preflight Manifest 是确定性运行证据，不构成新的内容权威。

## 2. Page Source Packet v2

每个带 `source_refs` 的内容页在写作或实质重写前必须生成当前 Packet：

```bash
.venv/bin/python3 -m script_engine.cli page-source \
  script/deck-plan.json \
  script/foundation.json \
  <PAGE_ID> \
  --source-index script/.cache/source-index.json \
  --output script/.cache/page-source/<PAGE_ID>.json
```

Packet 必须使用 `cyberppt.page_source_packet.v2`，并携带：

- `builder_version`；
- `generated_at`；
- `deck_plan_sha256`；
- `foundation_sha256`；
- `source_index_sha256`；
- 当前页 Foundation refs；
- 对应 exact source units；
- exact unit 的稳定 `unit_id`。

以下任一情况都必须 `status: blocked`：

- 页面引用未知来源；
- Foundation 条目没有 source-unit 绑定；
- source-unit 无法在当前 `source-index.v2` 中解析；
- source-unit 仅部分解析；
- exact source text 不完整。

Foundation statement、摘要、preview 或模型记忆都不能替代 exact source unit。

## 3. Freshness

Packet 的有效性绑定当前 Deck Plan、Foundation、Source Index 三个 SHA-256 指纹。

状态只有：

- `fresh`：三个输入指纹全部与当前输入一致；
- `stale`：Packet 结构有效，但任一上游输入已改变；
- `invalid`：Packet schema、builder 或必要指纹不合法。

`stale` 和 `invalid` 均不得进入 AUTHOR。

修改以下任一内容后，受影响页面必须重新生成 Packet：

- Deck Plan 页面使命、来源范围或页面结构；
- Foundation 事实、关系、实体、数字或来源绑定；
- Source Index 或原始 source units。

## 4. Author Preflight v2

所有需要来源证据的页面 Packet 准备完毕后，必须生成项目级 Author Preflight：

```bash
.venv/bin/python3 -m script_engine.cli author-preflight \
  script/deck-plan.json \
  script/foundation.json \
  --source-index script/.cache/source-index.json \
  --packet-dir script/.cache/page-source \
  --output script/.cache/author-preflight.json
```

Manifest 使用 `cyberppt.author_preflight.v2`。

逐页状态：

- `passed`：fresh Packet、exact source 完整、来源范围一致；
- `blocked`：Packet 或 exact source 存在硬错误；
- `missing`：该页 Packet 不存在；
- `stale`：Packet 与当前上游输入不一致；
- `not_applicable`：结构页没有来源消费要求。

只有：

```text
summary.overall_status == passed
```

才能进入 AUTHOR。

仅存在可重新计算为 passed 的 Packet 不等于门禁通过；持久化 Manifest 缺失或与当前输入不一致时仍必须阻断。

## 5. AUTHOR 输入规则

faithful AUTHOR 对每个内容页只允许以该页 fresh Packet 的 exact source units 作为精确事实输入。

Foundation 可以辅助：

- 实体标准化；
- 跨页上下文；
- 页面范围理解；
- 结构化索引。

Foundation 不得在 exact source 缺失时作为事实 fallback。

AUTHOR 仍由主 Agent 按 faithful authoring contract 执行；Page Source Packet 和 Author Preflight 只负责确定输入证据和门禁，不负责生成正文。

## 6. Final Script 来源血缘

每个内容页必须携带页面级 `source_provenance`：

```json
{
  "packet_sha256": "<current packet sha256>",
  "source_refs": ["F1"],
  "unit_ids": ["SU-001"]
}
```

该字段必须与当前 passed Author Preflight 中该页记录完全一致。

不得手工复制旧 hash、旧 `unit_ids` 或旧 `source_refs` 使校验通过。Packet 或 Manifest 更新后，Final Script 对应页面的 provenance 必须同步刷新。

Final Script 1.1 的模块级 provenance 继续遵循 `final-script-provenance-contract.md`；页面级 `source_provenance` 负责证明整页来自当前 exact-source gate，两者职责不同且都不能互相替代。

## 7. Final Native-source Fidelity Gate

`audit-final` 在 Preflight 和页面 provenance 通过后，必须直接读取当前 Page Source Packets 的 exact native source units，检查 Final Script 的高风险事实漂移。

当前确定性 blocker 包括：

- 新增来源不存在的数字或日期；
- 删除数字绑定的限定词，如“约”“至少”“不超过”“截至”；
- 删除明确范围限定，如“仅”“不含”“首批”“当前”“主要”“部分”；
- 将“计划/拟/预计/可能/有望”等状态提升为“已完成/已形成/已实现”等既成状态；
- 新增“必须/应当/不得/严禁”等责任强度；
- 新增“必然/全面/显著”等来源不存在的结论强度。

这些检查以 exact native source 为准，不再以 Foundation 摘要替代原文事实权威。

执行：

```bash
.venv/bin/python3 -m script_engine.cli audit-final \
  script/dist/final-script.json \
  script/deck-plan.json \
  script/foundation.json
```

存在 blocker 时 Final Audit 必须失败。

## 8. Stage02 硬门禁

Stage02 Markdown 边界不得只依赖 Final Script schema 或 lint。

正式入口：

```bash
.venv/bin/python3 -m script_engine.cli render-stage02 \
  script/dist/final-script.json \
  --plan script/deck-plan.json \
  --foundation script/foundation.json \
  --output script/dist/final-script.md
```

执行顺序必须是：

```text
Author Preflight Gate
  → Final Script schema
  → page source_provenance
  → Native-source Fidelity Gate
  → lint
  → Stage02 render
```

任一门禁失败都不得写出新的 Stage02 文件。

## 9. Project Status

使用：

```bash
.venv/bin/python3 -m script_engine.cli status <project>
```

`stage1` 状态区必须至少反映：

- Source Index；
- Foundation；
- Deck Plan；
- Author Preflight；
- Final Script；
- Final Audit。

Author Preflight 状态必须基于当前输入重新计算，并同时校验持久化 Manifest，不得只读取历史状态。

逐页至少显示：

- `gate_status`；
- `freshness`；
- `exact_source_status`；
- `source_refs`；
- `unit_ids`；
- `issues`。

只有 Final Audit 真正通过，项目状态才能表示“可进入 Stage02”。

## 10. 禁止旁路

以下做法均不构成 Stage1 完成：

- 只在 Prompt 中写“忠于原文”；
- 只生成 Foundation，不生成 exact Page Source Packet；
- Packet 缺失或 stale 时直接写 Final Script；
- 只运行 lint，不运行 Author Preflight / Final Audit；
- 手工构造 `source_provenance`；
- 直接调用 Stage02 渲染函数绕过 CLI 门禁；
- 因已有旧 Final Script、旧 Packet 或旧 Manifest 而跳过当前输入验证。

Stage1 完成的唯一判定是：当前输入、当前逐页 exact source、当前 Manifest、当前 Final Script lineage 和当前 Final Audit 形成同一条可验证证据链。

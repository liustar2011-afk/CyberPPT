# Final Script Provenance Contract

本文件定义 Final Script 的两层来源血缘：页面级 exact-source lineage 与模块级语义 provenance。两层职责不同，均不得通过关键词匹配、模型记忆或人工补 hash 伪造。

进入 AUTHOR 前同时读取 `stage1-faithful-gate-contract.md`。Native Source Unit 是最终事实权威；Foundation 是结构化语义索引和 authoring context，不得在 exact source 缺失时替代原文。

## 1. 当前版本边界

当前新项目统一输出 Final Script contract `cyberppt.final-script` version `1.1`。

内容页必须同时满足：

1. 页面级 `source_provenance` 与当前 passed Author Preflight 完全一致；
2. 1.1 `onscreen` 模块和 item 使用稳定 ID；
3. 模块级 provenance 覆盖每个可见目标；
4. schema、source lineage、native-source fidelity 和最终审计全部通过。

缺少其中任一项均不得进入 Stage02。

## 2. 页面级 exact-source lineage

每个内容页必须带：

```json
{
  "source_provenance": {
    "packet_sha256": "<current page-source packet sha256>",
    "source_refs": ["F1"],
    "unit_ids": ["SU-001"]
  }
}
```

字段来源只能是当前 `cyberppt.author_preflight.v2` 中该页的 passed 记录：

- `packet_sha256`：当前 Page Source Packet 的稳定 SHA-256；
- `source_refs`：当前 Deck Plan 页面允许使用的来源范围；
- `unit_ids`：本页实际解析得到的 exact native source units。

该层证明“这一页使用的是当前上游输入对应的精确来源证据”。

不得：

- 从旧 Final Script 复制 `packet_sha256`；
- 手工填入并未出现在当前 Preflight 中的 `unit_ids`；
- 为了通过校验而扩大 `source_refs`；
- 在 Packet 或 Manifest 已 stale 后继续沿用旧 provenance。

## 3. 稳定可见内容身份

Final Script 1.1 内容页的每个 `onscreen` module 使用稳定 `id`，以 `M` 开头。每个 authored item 使用自身稳定 `id` 和 `text`。

ID 标识语义输出单元，不标识版式框。语义角色未变化时，修改措辞应保留 ID；拆分、合并或替换为 materially different proposition 时分配新 ID。module / item ID 在单个 Final Script 内必须唯一。

## 4. 模块级 explicit provenance

每个 module 携带 `provenance`：

- `derivation`: `direct`、`synthesis` 或 `relation`；
- `claim_refs`: 授权该模块命题的 Foundation 结构化记录；
- `bindings`: 每个可见 target 的显式绑定。

可见 target 包括：

- module `heading`；
- module `text`；
- 每个 item ID。

每个可见 target 恰有一个 binding。binding 包含 `target`、`source_refs` 和关系类型：

- `expresses`
- `supports`
- `qualifies`
- `implements`
- `contrasts`
- `sequences`

模块级 provenance 用于描述作者输出与结构化 Foundation claims 的语义归属；它不能替代页面级 exact-source lineage，也不能把 Foundation 升级为最终事实权威。

## 5. Derivation 语义

`direct`：一个 Foundation claim 直接授权模块命题，只使用一个 `claim_ref`。

`synthesis`：在不创造新关系的前提下汇总两个或以上兼容 Foundation claims，使用至少两个 `claim_refs`。必须保留其中适用的最弱状态、条件、责任和 claim strength。

`relation`：表达由两个或以上 Foundation claims / relations 授权的关系，使用至少两个 `claim_refs`。faithful 模式下关系方向必须有来源明确支持；analytical 模式只能使用已经批准且 source-supported 的推断关系。

## 6. Evidence scope

每个 module `claim_ref` 和 binding `source_ref` 必须：

1. resolve 到当前 Foundation 中的结构化记录；
2. 位于当前 Final Script slide 的 `source_refs` 范围内；
3. 位于匹配 Deck Plan 页面允许的来源范围内；
4. 不得超出页面级 `source_provenance` 所证明的当前 exact-source lineage。

页面事实真伪最终由当前 Page Source Packet 的 Native Source Units 和 Native-source Fidelity Gate 裁决；Foundation 负责语义索引、归属和结构化 binding。

## 7. JSON / Markdown 同步

JSON Final Script 是结构化 provenance 权威载体。Delivery 可将 module provenance 渲染到审计专用区域：

`### 证据映射（模块级｜不上屏）`

该区域使用 canonical JSON 记录，确保可无歧义还原 module provenance。

证据映射属于 QA metadata，不属于：

- `onscreen` visible copy；
- Stage02 locked text；
- image-generation copy；
- speaker notes；
- audience-facing slide content。

JSON provenance 变化后，旧 Markdown 视为 stale，必须重新 render / check-sync。

## 8. Revision 行为

定向修订、Critic 或 Rewrite 时：

- 语义 ownership 未变化则保留 module / item IDs；
- 可见文字改变 evidence parentage 时同步更新 module bindings；
- 可见 target 被删除时移除其旧 binding；
- 页面 exact-source Packet 改变时刷新页面级 `source_provenance`；
- 不得保留旧 binding 或旧 hash 仅为了让历史审计通过；
- 不得通过 lexical similarity 自动填充 provenance。

## 9. 完成条件

一张内容页只有同时满足以下条件才完成 provenance 闭环：

```text
fresh Page Source Packet
  → passed Author Preflight
  → page source_provenance matches current manifest
  → module/item provenance valid
  → Native-source Fidelity passed
  → Final Audit passed
```

缺少任一环节都必须回到对应上游修复，不允许在下游补写元数据绕过。

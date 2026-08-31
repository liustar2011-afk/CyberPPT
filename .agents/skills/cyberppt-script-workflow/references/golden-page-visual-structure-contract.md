# 黄金页面 Visual Structure Contract

> 适用范围：Relation Grammar 黄金示例的 `视觉结构` 教学表达。
>
> 权威边界：AUTHOR、CRITIQUE、REWRITE 的操作权威仍为 `authoring-contract.md`。本文件不新增 Final Script 字段，不形成新的 Stage1 authoritative IR，不定义新的 Runtime ontology；它只把 AUTHOR Contract 已有的 `visual_thesis / relationships` 方法投影成稳定、可审阅、可回归的示例写法。

## 一、固定五项

每个黄金页的 `视觉结构` 按以下顺序说明五项内容：

1. **视觉对象**：页面需要让读者同时看见哪些业务对象、状态、主体、输入或结果；
2. **关系语义**：这些对象之间的真实业务关系是什么，例如同层并列、业务交接、因果、共同支撑、问题响应、同维度比较、状态跃迁、责任与控制；
3. **方向 / Cardinality**：关系是否有方向，以及 1→1、N→1、1:1、1:N、N:1 等真实基数；无方向关系必须明确写明“无流程方向”；
4. **分组 / 层级**：哪些对象同层、哪些是父子、哪些汇聚到共同节点、哪些条件贴近边；
5. **禁止误读**：指出最容易被错误画成的关系，例如把 Parallel 画成流程、把 Comparison 画成迁移、把 Mapping 画成双向作用。

五项内容属于 `视觉结构` 内部的可读合同，不新增持久化字段。

## 二、原子关系边

需要方向、汇聚、交接、反馈、映射、状态跃迁或责任传递时，在五项之后保留可解析的原子关系边。

推荐写法：

`Source → Target：关系标签｜必要的边级说明`

每条边只承载：

- 一个 Source；
- 一个 Target；
- 一个 connecting action / relationship label；
- 必要时一个交接物、进入条件、回写物或边界说明。

一条边出现第二个 Actor、中间过程、触发条件或结果时，应拆成两条或多条原子边。

## 三、无方向关系的表达

Comparison 和 Parallel 等无流程方向关系不得为了适配箭头解析而虚构方向。

### Comparison

使用固定对象对和共同评价维度：

`比较对象｜对象A vs 对象B：对照比较`

`vs` 表示无流程方向的对照关系，不表示 A 进入 B、A 对应 B 或 A 导致 B。

### Parallel

使用一个共同上位对象和多个同层兄弟：

`统一预测体系：并列分类｜研判范围、周期规则、运行机制`

兄弟单元之间不建立箭头。

## 四、八类 Grammar 的最低关系保真

| Grammar | 视觉对象 | 关系语义 | Direction / Cardinality | 必须保留 |
|---|---|---|---|---|
| Parallel | 共同上位对象 + 同层兄弟 | peer classification | 无方向 | 同一分解维度、兄弟无箭头 |
| Flow | 阶段 + 交接物 + 反馈目标 | sequence + feedback | 主链 1→1 + feedback | 每条正向边的交接物、反馈回写物 |
| Causal | 起因 + 连续后果 | causes | 1→1 chain | 每条边均可解释“因为A，所以B” |
| Convergence | 多个独立输入 + 共同结果 | support convergence | N→1 | 所有输入直接汇入同一结果 |
| Mapping | 问题端 + 响应端 | problem response | 按事实保留 1:1 / 1:N / N:1 | 两端、方向、Cardinality |
| Comparison | 固定对象A/B + 共同评价维度 | comparison | 无流程方向 | 对象固定、维度一致、证据成对 |
| Roadmap | S0…Sn 状态 + 进入条件 | sequence / state transition | S0→S1→… | 前状态、进入条件、新状态 |
| Governance | Actor + Responsibility Object + Control + Outcome | responsibility / control chain | 多 Actor 可汇入共同控制层 | 主体责任不可被控制层替代、结果可检查 |

## 五、Stage2 消费原则

- Stage2 从锁定后的 `视觉结构` 恢复业务关系，不重新创作业务文字。
- 显式 `A → B：关系标签` 优先作为方向关系证据。
- `A vs B：对照比较` 只用于 Comparison，应恢复为 non-directional `comparison` relationship。
- 没有真实方向时不得为了让解析器工作而添加箭头；应增强 adapter 的关系恢复能力。
- 视觉载体、版式、构图、卡片数量和具体形状仍由 Stage2 决定，本合同不锁定版式。

## 六、回归判定

一个黄金页的 Visual Structure Contract 通过时，应同时满足：

1. 只读 `视觉结构` 可以列出主要业务对象；
2. 可以恢复关系类型及方向/无方向；
3. 有方向关系可以恢复 Source、Target 和 connecting action；
4. 可以判断分组与层级，且不会把关系层错误降为平行卡片；
5. 可以指出至少一种禁止误读；
6. Stage2 adapter 能恢复与黄金页 Relation Contract 一致的 semantic relationship；
7. `topology_resolver` 和 `relation_semantics` 能得到预期 semantic topology / reading contract。

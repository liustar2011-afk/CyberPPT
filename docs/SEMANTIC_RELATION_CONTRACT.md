# Stage 02 业务关系契约

## 1. 目的

统一 CyberPPT-Script 与 CyberPPT Stage 02 对“关系”的职责边界，避免把业务语义关系直接等同于视觉拓扑或固定版式。

Stage 02 按三层处理：

1. **Business Semantic Relation**：业务语义真值，说明对象之间是什么业务关系。
2. **Reading / Evidence Constraints**：说明该关系应以并列、映射、收敛、顺序、闭环、分层等何种方式被阅读，并保留可选性、条件和证据强度。
3. **Visual Topology**：视觉结构设计阶段根据前两层选择的空间拓扑。最终 topology 由 `ppt-visual-structure-designer` 负责。

## 2. 统一业务关系词汇

Stage 02 当前 canonical vocabulary：

- `supports`
- `responds_to`
- `corresponds_to`
- `causes`
- `enables`
- `transforms_to`
- `sequence_before`
- `feedback_to`
- `classified_as`
- `composed_of`
- `part_of`
- `layered_as`
- `bounded_by`
- `covers`
- `collaborates_with`
- `provides_to`
- `applies_to`

旧关系词可通过 `cyberppt.semantic_relation_contract.LEGACY_RELATION_ALIASES` 兼容，但新派生关系应优先使用 canonical vocabulary。

## 3. 关系不得直接绑定版式

禁止建立以下类型的一对一硬映射：

- `supports → framework_4`
- `corresponds_to → comparison_2col`
- `classified_as → layered_architecture`

视觉结构应同时考虑：

- relation family；
- subject/object 基数；
- 是否多个证据共同指向一个结果；
- 是否存在真实顺序或反馈；
- 是否存在真实层级依赖；
- 是否存在 `independent_selection`、`optional_progression` 等限定语；
- 页面模块数量与 `expression_constraints`。

## 4. 典型映射边界

### 多项共同支撑一个结论

`supports + many_to_one/shared_target`

- 阅读结构：收敛/证据支撑；
- topology 候选：`conclusion_anchor`；
- 禁止：仅因 `supports` 选择分层架构。

### 问题—响应映射

`responds_to / corresponds_to`

- 阅读结构：`mapped`；
- topology 候选：关系场/映射场；
- 只有存在共同对比维度时才进入 comparison。

### 并列分类

`classified_as`

- 阅读结构：`parallel`；
- topology 候选：`parallel_set`；
- 禁止：自动转为 `layered_architecture` 或 `directed_flow`。

### 真实层级

`layered_as / part_of`

- 存在真实上下层或依赖关系时，可进入 `layered_architecture`。

### 真实流程

`sequence_before`

- 阅读结构：`directed`；
- topology 候选：`directed_flow`；
- 当前表达合同支持 3—6 个步骤。

### 可独立采用 + 可逐步深化

关系记录通过 `semantic_qualifiers` 同时保留：

- `independent_selection`
- `optional_progression`
- 可选的 `non_mandatory_progression`

两层含义并存时，`directed_flow` 不得成为唯一主拓扑，以免把可选择的深化路径误写成强制必经顺序。

## 5. CyberPPT-Script 接入

对于 CyberPPT-Script v0.4+ canonical `final-script.md`：

- 原脚本保持不变；
- Stage 02 优先读取旧 hidden `content_relations`（若存在）；
- 缺失时，由 `stage02_relationship_adapter.py` 从 `### 视觉结构` 的明确关系语句派生 `business_relationships`；
- 真正缺少明确关系时保持为空，由视觉设计门禁处理；
- Stage 02 不要求 Script Engine 为视觉后端额外写入 `business_relationships`。

## 6. 关键实现

- `cyberppt/stage02_relationship_adapter.py`：canonical Markdown → business relations
- `cyberppt/semantic_relation_contract.py`：统一 vocabulary、relation profile、表达/legacy hint
- `cyberppt/onscreen_expression.py`：关系约束 → 阅读结构
- `cyberppt/semantic_intent.py`：关系 profile → canonical semantic intent
- `cyberppt/composition_resolver.py`：semantic intent → 空间语法
- `cyberppt/visual_carrier_resolver.py`：semantic intent → 视觉载体候选
- `vendor/skills/ppt-visual-structure-designer/references/visual-intent-router.md`：最终 topology 选择规则

## 7. 回归样例

长期回归至少覆盖：

- P04：三项压力共同支撑一个结论；
- P05：问题—平台定位映射；
- P16：五类服务并列 taxonomy；
- P25：四类合作模式可独立采用、也可逐步深化；
- P31：六步真实顺序流程。

## 8. 持续验证

仓库通过 `.github/workflows/tests.yml` 在 Python 3.10 与 3.12 上执行完整 `pytest -q`。关系词汇、canonical intent、composition 和 visual carrier 注册表应由回归测试保持同步；新增关系或语义意图时不得只修改单一层级。
